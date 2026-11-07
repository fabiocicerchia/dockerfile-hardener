@domain:image-pinning @area:os-package-pin @from:dockerfile-hardener/hadofix
Feature: Pinning package versions
  Makes the same commit build the same packages by pinning apt, apk and pip installs to versions the repository already commits to, and refusing otherwise.

  Background:
    Given hadolint reports an unpinned package install

  @id:image-pinning.os-package-pin.001 @rule:hadofix.package-pin.from-another-stage @verified @source:hadofix.py#fix_pin_packages @test:tests/test_hadofix.py#test_golden
  Scenario Outline: An unpinned package takes the version another instruction already pins
    Given one stage runs `<install> <package>=<version>`
    And another stage runs `<install> <package>` without a version
    When the operator runs hadofix on the Dockerfile
    Then the diff rewrites the unpinned install to `<package>=<version>`
    And the comment above it says the version is the one this repository already commits to elsewhere
    And the report lists <rule> as fixed

    Examples:
      | rule   | install                                    | package | version           |
      | DL3008 | apt-get install --no-install-recommends -y | curl    | 7.88.1-10+deb12u5 |
      | DL3018 | apk add --no-cache                         | curl    | 8.12.1-r1         |

  @id:image-pinning.os-package-pin.002 @rule:hadofix.package-pin.copied-requirements-are-evidence @verified @source:hadofix.py#_requirements_pins @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_a_requirements_file_is_evidence_only_when_it_is_copied_in @test:tests/test_hadofix.py#test_the_pip_pin_comes_from_the_build_context_on_disk
  Scenario: A pip install is pinned from a requirements file the Dockerfile copies in
    Given the build context has `requirements.txt` containing `flask==3.0.3`
    And the Dockerfile copies `requirements.txt` into the image
    And a RUN installs `flask` with pip without a version
    When the operator runs hadofix on the Dockerfile
    Then the diff rewrites the install to `flask==3.0.3`
    And the report lists DL3013 as fixed

  @id:image-pinning.os-package-pin.003 @rule:hadofix.package-pin.refuses-unknown-versions @verified @source:hadofix.py#fix_pin_packages @test:tests/test_hadofix.py#test_a_version_is_taken_from_evidence_never_invented @test:tests/test_hadofix.py#test_a_requirements_file_is_evidence_only_when_it_is_copied_in
  Scenario Outline: A package no evidence pins is left for the operator, with how to find its version
    Given a RUN installs `<package>` with <manager> without a version
    And nothing in the Dockerfile or a copied requirements file pins `<package>`
    When the operator runs hadofix on the Dockerfile
    Then the Dockerfile is not changed
    And the report lists the finding under "left for you"
    And the reason names `<package>` and points to `<hint>` to find the version

    Examples:
      | manager | package | hint                         |
      | apt-get | curl    | apt-cache policy <package>   |
      | pip     | flask   | pip index versions <package> |
