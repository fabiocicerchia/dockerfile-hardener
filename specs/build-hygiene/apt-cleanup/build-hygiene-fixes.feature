@domain:build-hygiene @area:apt-cleanup @from:dockerfile-hardener/hadofix
Feature: Build hygiene fixes
  Gives operators smaller, safer layers by rewriting RUN instructions so pipes fail loudly, apt installs only what is named, and apt lists do not ship in the image.

  @id:build-hygiene.apt-cleanup.001 @rule:hadofix.hygiene.pipefail-shell @verified @source:hadofix.py#fix_pipefail @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_pipefail_picks_the_shell_the_base_image_has
  Scenario Outline: A piped RUN gets a pipefail SHELL that matches the stage's base image
    Given a stage built `FROM <base>` has a RUN with a pipe
    And hadolint reports DL4006 on that RUN
    When the operator runs hadofix on the Dockerfile
    Then a `SHELL ["<shell>", "-o", "pipefail", "-c"]` line is added directly above the RUN
    And a `# hadofix(DL4006):` comment above it explains why

    Examples:
      | base                 | shell     |
      | debian:bookworm-slim | /bin/bash |
      | alpine:3.22          | /bin/ash  |

  @id:build-hygiene.apt-cleanup.002 @rule:hadofix.hygiene.apt-lists-same-layer @verified @source:hadofix.py#fix_apt_lists @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_apt_cleanup_joins_a_multi_line_run
  Scenario Outline: Apt lists are removed in the same RUN that installed them
    Given a RUN installs with apt and does not remove `/var/lib/apt/lists/*`
    And the RUN is <shape>
    And hadolint reports DL3009 on it
    When the operator runs hadofix on the Dockerfile
    Then the RUN ends with `<ending>`
    And the report lists DL3009 as fixed

    Examples:
      | shape                        | ending                                                   |
      | on one line                  | && rm -rf /var/lib/apt/lists/*                           |
      | continued over several lines | a new continuation line `&& rm -rf /var/lib/apt/lists/*` |

  @id:build-hygiene.apt-cleanup.003 @rule:hadofix.hygiene.no-install-recommends @verified @source:hadofix.py#fix_no_install_recommends @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_write_applies_the_diff
  Scenario: An apt install is limited to the packages it names
    Given a RUN runs `apt-get install -y curl=7.88.1-10+deb12u5` without --no-install-recommends
    And hadolint reports DL3015 on it
    When the operator runs hadofix on the Dockerfile
    Then the install becomes `apt-get install --no-install-recommends -y curl=7.88.1-10+deb12u5`
    And a `# hadofix(DL3015):` comment above the RUN explains that Recommends are not installed
