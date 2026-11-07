@domain:finding-intake @area:stdin-findings @from:dockerfile-hardener/hadofix
Feature: Supplying hadolint findings
  Lets operators who already ran hadolint pipe or point at its JSON instead of having hadofix run the linter again, and refuses JSON it cannot trust.

  @id:finding-intake.stdin-findings.001 @rule:hadofix.intake.json-from-stdin-or-file @verified @source:hadofix.py#_findings_payload @test:tests/test_hadofix.py#test_reads_hadolint_json_from_stdin @test:tests/test_hadofix.py#test_unknown_rules_are_listed_not_guessed_at
  Scenario Outline: hadolint's JSON can be given on stdin or as a file instead of running hadolint
    Given hadolint's JSON reports DL3059 on line 1 of the Dockerfile
    When the operator runs hadofix on the Dockerfile with `--from-json <source>`
    Then hadolint is not run
    And the report lists DL3059 under "left for you"
    And hadofix exits 1

    Examples:
      | source                      |
      | - (the JSON piped on stdin) |
      | hadolint.json               |

  @id:finding-intake.stdin-findings.002 @rule:hadofix.intake.untrusted-json-refused @verified @source:hadofix.py#parse_findings @test:tests/test_hadofix.py#test_unreadable_json_exits_ex_unavailable @questionable
  Scenario Outline: Findings that cannot be read are refused rather than treated as a clean file
    Given <problem>
    When the operator runs hadofix on the Dockerfile with `--from-json hadolint.json`
    Then stderr says "hadofix: <message>"
    And the Dockerfile is not changed
    And hadofix exits 69

    Examples:
      | problem                                          | message                                    |
      | hadolint.json contains `not json`                | could not read the hadolint JSON: …        |
      | hadolint.json contains a JSON object, not a list | hadolint JSON should be a list of findings |
      | hadolint.json does not exist                     | hadolint.json: No such file or directory   |
