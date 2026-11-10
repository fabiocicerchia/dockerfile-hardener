@domain:fix-output @area:cli-exit @from:dockerfile-hardener/hadofix
Feature: Gating CI on hadofix's exit status
  Lets a CI gate tell a Dockerfile that still has findings from a run that could not look at it.

  @id:fix-output.cli-exit.001 @rule:hadofix.cli.exit-status @verified @source:hadofix.py#main @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_missing_file_exits_ex_noinput @test:tests/test_hadofix.py#test_a_missing_hadolint_is_not_a_finding @test:tests/test_hadofix.py#test_the_cli_runs_hadolint_and_writes_the_fix
  Scenario Outline: The exit status says whether the Dockerfile is clean, still has findings, or could not be checked
    Given <state>
    When the operator runs hadofix <options> on the Dockerfile
    Then hadofix exits <code>

    Examples:
      | state                                                 | options                                        | code |
      | nothing is left to fix                                | without options                                | 0    |
      | every finding was fixed                               | with --write                                   | 0    |
      | every finding can be fixed                            | without options (the diff is not applied)      | 1    |
      | a finding is left for the operator                    | with --write                                   | 1    |
      | the Dockerfile does not exist                         | without options                                | 66   |
      | the Dockerfile cannot be read for lack of permission  | without options                                | 77   |
      | the Dockerfile path is a directory                    | without options                                | 74   |
      | the hadolint binary is not installed                  | with --hadolint hadolint-that-is-not-installed | 69   |

  @id:fix-output.cli-exit.002 @rule:hadofix.cli.read-failure-message @verified @source:hadofix.py#main @test:tests/test_hadofix.py#test_missing_file_exits_ex_noinput
  Scenario: A Dockerfile that cannot be read is named on stderr with the reason
    Given no file exists at `/nonexistent/Dockerfile`
    When the operator runs hadofix on `/nonexistent/Dockerfile`
    Then stderr says "hadofix: /nonexistent/Dockerfile: No such file or directory"
    And stdout is empty
