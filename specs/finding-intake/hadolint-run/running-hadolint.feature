@domain:finding-intake @area:hadolint-run @from:dockerfile-hardener/hadofix-io
Feature: Running hadolint for findings
  Operators get hadofix's fixes from a real hadolint run, and a clear refusal instead of a silent empty result when hadolint cannot answer.

  Background:
    Given a Dockerfile named "Dockerfile" in the current directory
    And the operator does not pass --from-json

  @id:finding-intake.hadolint-run.001 @rule:finding-intake.hadolint-run.findings-exit-is-a-normal-run @verified @source:hadofix_io.py#run_hadolint @test:tests/test_hadofix.py#test_the_cli_runs_hadolint_and_writes_the_fix @test:tests/test_hadofix.py#test_run_hadolint_asks_a_real_process_for_json
  Scenario: hadolint reporting findings is a normal run, not a failure
    Given hadolint is installed, reports a DL3015 finding for the Dockerfile and exits 1
    And the Dockerfile has nothing else to fix
    When the operator runs hadofix on the Dockerfile with --write
    Then the unified diff adding --no-install-recommends is printed on stdout
    And stderr says "hadofix: fixed 1 finding in Dockerfile: DL3015"
    And the Dockerfile on disk now contains --no-install-recommends
    And hadofix exits 0

  @id:finding-intake.hadolint-run.002 @rule:finding-intake.hadolint-run.unavailable-engine-stops-the-run @verified @source:hadofix_io.py#run_hadolint @test:tests/test_hadofix.py#test_a_missing_hadolint_is_not_a_finding @test:tests/test_hadofix.py#test_run_hadolint_reports_an_engine_failure
  Scenario Outline: hadofix stops with exit 69 when hadolint cannot be run or breaks
    Given <engine state>
    When the operator runs hadofix on the Dockerfile
    Then stderr shows "hadofix: <message>"
    And no diff is printed on stdout
    And the Dockerfile is left unchanged
    And hadofix exits 69

    Examples:
      | engine state                                             | message                                                                                                                                                                     |
      | the hadolint binary named by --hadolint is not installed | hadolint-that-is-not-installed: not found. hadolint is the engine hadofix fixes for — install it (https://github.com/hadolint/hadolint), or pass its JSON with --from-json. |
      | hadolint exits 2 printing "parse error" on stderr        | hadolint exited 2: parse error                                                                                                                                              |
