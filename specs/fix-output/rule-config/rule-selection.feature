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
