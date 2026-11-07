@domain:runtime-hardening @area:non-root-user @from:dockerfile-hardener/hadofix
Feature: Running the image as a non-root user
  Keeps containers from running as UID 0 on the host kernel, without inventing accounts or overruling a user the operator chose.

  @id:runtime-hardening.non-root-user.001 @rule:hadofix.user.root-replaced-by-uid @verified @source:hadofix.py#fix_nonroot_user @test:tests/test_hadofix.py#test_golden
  Scenario: An explicit root user is replaced by UID 10001
    Given the final stage sets `USER root`
    And hadolint reports DL3002 and DL3066 on that line
    When the operator runs hadofix on the Dockerfile
    Then the line becomes `USER 10001` with one `# hadofix(DL3066):` comment above it
    And the report says "fixed 2 findings in Dockerfile: DL3002, DL3066"

  @id:runtime-hardening.non-root-user.002 @rule:hadofix.user.root-by-default-flagged-and-fixed @verified @source:hadofix.py#_root_default_finding @test:tests/test_hadofix.py#test_golden
  Scenario: A final stage that never sets a user is made to run as UID 10001
    Given the final stage sets no USER
    And it ends with `ENTRYPOINT ["/usr/local/bin/app"]`
    When the operator runs hadofix on the Dockerfile
    Then hadofix raises HF1004 even though hadolint reported nothing
    And `USER 10001` is inserted directly above the ENTRYPOINT, with a `# hadofix(HF1004):` comment
    And the report lists HF1004 as fixed

  @id:runtime-hardening.non-root-user.003 @rule:hadofix.user.chosen-user-kept @inferred @source:hadofix.py#fix_nonroot_user
  Scenario: A non-root user the operator chose is never overruled
    Given the final stage sets `USER app`
    And hadolint reports DL3066 because the user is not numeric
    When the operator runs hadofix on the Dockerfile
    Then the USER line is not changed
    And the report lists DL3066 under "left for you"
    And the reason says hadofix will not overrule the chosen USER and suggests giving that account a fixed numeric UID
