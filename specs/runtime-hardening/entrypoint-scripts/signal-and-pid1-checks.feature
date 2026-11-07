@domain:runtime-hardening @area:entrypoint-scripts @from:dockerfile-hardener/hadofix
Feature: Checking that signals reach the application
  Warns operators about containers whose PID 1 will not forward signals or reap orphans, which hadolint has no rule for, without rewriting their scripts or installing an init.

  @id:runtime-hardening.entrypoint-scripts.001 @rule:hadofix.pid1.entrypoint-script-must-exec @verified @source:hadofix.py#_entrypoint_script_finding @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_a_script_copied_with_the_build_context_is_still_found
  Scenario Outline: An entrypoint script from the build context that never calls exec is reported
    Given the build context has `entrypoint.sh`, a shell script with no `exec` line
    And the Dockerfile copies it in with `<copy>`
    And the final stage sets `USER 10001` and has `ENTRYPOINT ["<path>"]`
    When the operator runs hadofix on the Dockerfile
    Then the report lists HF1002 on the ENTRYPOINT line under "left for you"
    And the message says `entrypoint.sh` never calls exec and to end it with `exec "$@"`
    And the Dockerfile is not changed

    Examples:
      | copy                              | path               |
      | COPY entrypoint.sh /entrypoint.sh | /entrypoint.sh     |
      | COPY . /app                       | /app/entrypoint.sh |

  @id:runtime-hardening.entrypoint-scripts.002 @rule:hadofix.pid1.exec-script-is-quiet @verified @source:hadofix.py#_entrypoint_script_finding @test:tests/test_hadofix.py#test_an_entrypoint_script_that_execs_answers_hf1002
  Scenario: An entrypoint script that hands over with exec raises nothing
    Given the build context has `entrypoint.sh` ending in `exec "$@"`
    And the Dockerfile copies it to `/entrypoint.sh`, sets `USER 10001` and has `ENTRYPOINT ["/entrypoint.sh"]`
    When the operator runs hadofix on the Dockerfile
    Then no HF1002 is reported

  @id:runtime-hardening.entrypoint-scripts.003 @rule:hadofix.pid1.forking-process-needs-init @verified @source:hadofix.py#_init_finding @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_an_init_in_the_entrypoint_answers_hf1003
  Scenario Outline: A worker-forking process run without an init is reported, and an init silences it
    Given the final stage runs `CMD ["nginx", "-g", "daemon off;"]`
    And <init_state>
    When the operator runs hadofix on the Dockerfile
    Then <outcome>

    Examples:
      | init_state                               | outcome                                                                                                                      |
      | no ENTRYPOINT names an init              | the report lists HF1003 (info) saying `nginx` forks workers and to put tini or dumb-init in front or use `docker run --init` |
      | the ENTRYPOINT is `["/sbin/tini", "--"]` | no HF1003 is reported                                                                                                        |
