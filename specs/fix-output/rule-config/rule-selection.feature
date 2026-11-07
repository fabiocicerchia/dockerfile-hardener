@domain:fix-output @area:rule-config @from:dockerfile-hardener/hadofix
Feature: Letting hadolint decide what gets fixed
  Keeps hadolint's configuration as the single rule list operators maintain, so a rule they switched off is never fixed.

  @id:fix-output.rule-config.001 @rule:hadofix.rules.only-reported-findings-fixed @verified @source:hadofix.py#fix @test:tests/test_hadofix.py#test_our_own_rules_are_idempotent
  Scenario: A hadolint rule that hadolint did not report is never fixed
    Given the Dockerfile has an apt install without --no-install-recommends, sets `USER 10001` and uses exec form
    And hadolint reports no findings for it, for example because DL3015 is ignored in .hadolint.yaml
    When the operator runs hadofix on the Dockerfile
    Then stdout is empty
    And the Dockerfile is not changed

  @id:fix-output.rule-config.002 @rule:hadofix.rules.own-rules-not-switchable @inferred @source:hadofix.py#own_findings @questionable
  Scenario: hadofix's own HF rules apply whatever hadolint is configured to ignore
    Given the final stage never sets a USER
    And the operator's hadolint configuration ignores every rule, so hadolint reports nothing
    When the operator runs hadofix on the Dockerfile
    Then hadofix still raises HF1004
    And the diff inserts `USER 10001` above the final command

  @id:fix-output.rule-config.003 @rule:hadofix.rules.one-defect-one-fix @verified @source:hadofix.py#fix @test:tests/test_hadofix.py#test_golden
  Scenario: Two rules that describe the same defect on one line are fixed once
    Given hadolint reports DL3025 on `CMD /usr/local/bin/app --port 8080`
    And hadofix raises HF1001 on the same line
    When the operator runs hadofix on the Dockerfile
    Then the diff contains a single exec-form rewrite with a single comment
    And the report counts both DL3025 and HF1001 as fixed
