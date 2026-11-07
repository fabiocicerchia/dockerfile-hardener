@domain:fix-output @area:report @from:dockerfile-hardener/hadofix
Feature: Reporting what was fixed and what is left
  Tells operators on stderr which findings were fixed and, for every one that was not, what they have to decide.

  @id:fix-output.report.001 @rule:hadofix.report.fixed-summary @verified @source:hadofix.py#render_report @test:tests/test_hadofix.py#test_golden
  Scenario: Fixed findings are summarised in one line with their rule codes
    Given hadofix fixes DL3002 and DL3066 in the Dockerfile
    When the operator runs hadofix on the Dockerfile
    Then stderr says "hadofix: fixed 2 findings in Dockerfile: DL3002, DL3066"

  @id:fix-output.report.002 @rule:hadofix.report.unfixable-listed-untouched @verified @source:hadofix.py#fix @test:tests/test_hadofix.py#test_unknown_rules_are_listed_not_guessed_at
  Scenario: Findings hadofix cannot fix are listed with hadolint's message, never guessed at
    Given hadolint reports DL3011 "Valid UNIX ports" on line 1
    And hadofix has no fix for DL3011
    When the operator runs hadofix on the Dockerfile
    Then stdout is empty
    And stderr lists "Dockerfile:1 error DL3011" under "1 finding left for you" with hadolint's message beneath it

  @id:fix-output.report.003 @rule:hadofix.report.clean-file @verified @source:hadofix.py#render_report @test:tests/test_hadofix.py#test_golden
  Scenario: A Dockerfile with no findings is reported as having nothing to fix
    Given hadolint reports nothing for a digest-pinned Dockerfile that runs as UID 10001 in exec form
    When the operator runs hadofix on the Dockerfile
    Then stdout is empty
    And stderr says "hadofix: hadolint found nothing to fix in Dockerfile"
