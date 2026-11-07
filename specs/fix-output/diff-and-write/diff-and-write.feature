@domain:fix-output @area:diff-and-write @from:dockerfile-hardener/hadofix
Feature: Reviewing and applying fixes
  Lets operators review every change as a commented unified diff before anything touches their Dockerfile, and apply it with one flag.

  Background:
    Given hadolint reports DL3015 on a Dockerfile hadofix can fix

  @id:fix-output.diff-and-write.001 @rule:hadofix.output.diff-without-write @verified @source:hadofix.py#main @test:tests/test_hadofix.py#test_nothing_is_written_without_write @test:tests/test_hadofix.py#test_golden
  Scenario: Without --write the fix is only shown, never applied
    When the operator runs hadofix on the Dockerfile
    Then stdout carries a unified diff from `Dockerfile` to `Dockerfile (hadofix)`
    And the Dockerfile on disk is unchanged
    And the report ends with "nothing written — re-run with --write to apply"

  @id:fix-output.diff-and-write.002 @rule:hadofix.output.write-applies @verified @source:hadofix.py#main @test:tests/test_hadofix.py#test_write_applies_the_diff @test:tests/test_hadofix.py#test_the_cli_runs_hadolint_and_writes_the_fix
  Scenario: With --write the fix is applied in place and the diff is still shown
    When the operator runs hadofix on the Dockerfile with --write
    Then the Dockerfile on disk contains `--no-install-recommends`
    And stdout still carries the diff
    And the report says "wrote Dockerfile"

  @id:fix-output.diff-and-write.003 @rule:hadofix.output.every-hunk-explained @verified @source:hadofix.py#comment_for @test:tests/test_hadofix.py#test_golden
  Scenario: Every change carries a comment naming the rule and why the fix is right
    When the operator runs hadofix on the Dockerfile
    Then directly above the rewritten RUN is a comment beginning `# hadofix(DL3015):`
    And the comment is wrapped at 79 columns, with continuation lines starting `# `

  @id:fix-output.diff-and-write.004 @rule:hadofix.output.idempotent @verified @source:hadofix.py#own_findings @test:tests/test_hadofix.py#test_our_own_rules_are_idempotent @test:tests/test_hadofix.py#test_the_cli_runs_hadolint_and_writes_the_fix @test:tests/test_hadofix.py#test_hadolint_drives_one_pass_to_clean
  Scenario: Fixing an already-fixed Dockerfile changes nothing
    Given the operator has already applied hadofix's fixes with --write
    And hadolint now reports nothing
    When the operator runs hadofix on the Dockerfile with --write again
    Then stdout is empty
    And the Dockerfile on disk is byte-for-byte the same
