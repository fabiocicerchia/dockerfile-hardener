@domain:runtime-hardening @area:exec-form @from:dockerfile-hardener/hadofix
Feature: Converting commands to exec form
  Lets `docker stop` reach the application by making it PID 1 instead of /bin/sh, but only where the command needs no shell.

  @id:runtime-hardening.exec-form.001 @rule:hadofix.exec-form.rewrite-plain-command @verified @source:hadofix.py#fix_exec_form @test:tests/test_hadofix.py#test_golden
  Scenario Outline: A shell-form command that needs no shell is rewritten in exec form
    Given the final stage ends with `<keyword> <command>` in shell form
    And the command uses no pipe, variable or glob
    When the operator runs hadofix on the Dockerfile
    Then the line becomes `<keyword> <argv>`
    And one `# hadofix(HF1001):` comment above it explains that sh does not forward SIGTERM
    And the report lists <fixed> as fixed

    Examples:
      | keyword    | command                        | argv                                     | fixed          |
      | CMD        | /usr/local/bin/app --port 8080 | ["/usr/local/bin/app", "--port", "8080"] | DL3025, HF1001 |
      | ENTRYPOINT | /usr/local/bin/app             | ["/usr/local/bin/app"]                   | HF1001         |

  @id:runtime-hardening.exec-form.002 @rule:hadofix.exec-form.refuse-when-shell-needed @verified @source:hadofix.py#fix_exec_form @test:tests/test_hadofix.py#test_golden
  Scenario: A command that needs a shell stays in shell form, with the deliberate alternative shown
    Given the final stage ends with `CMD /usr/local/bin/app --port $PORT`
    And hadolint reports DL3025 on it
    When the operator runs hadofix on the Dockerfile
    Then the Dockerfile is not changed
    And the report lists DL3025 and HF1001 under "2 findings left for you"
    And the reason, given once, says the command needs a shell and shows `CMD ["sh", "-c", "…"]`
