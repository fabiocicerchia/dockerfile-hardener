@domain:image-pinning @area:base-image-pin @from:dockerfile-hardener/hadofix
Feature: Pinning base images
  Gives operators base images that cannot change under them between builds, pinned only from evidence they already have or asked for.

  Background:
    Given hadolint reports an untagged or :latest base image (DL3006 or DL3007)

  @id:image-pinning.base-image-pin.001 @rule:hadofix.base-pin.from-another-stage @verified @source:hadofix.py#fix_base_pin @test:tests/test_hadofix.py#test_golden
  Scenario Outline: A floating base image takes the pin another stage already uses
    Given the Dockerfile has a stage built `FROM <pinned>`
    And a later stage is built `FROM <floating>`
    When the operator runs hadofix on the Dockerfile
    Then the diff rewrites the later stage to `FROM <pinned>`
    And a `# hadofix(<rule>):` comment above it says the pin came from another stage in this file
    And the report lists <rule> as fixed

    Examples:
      | rule   | pinned           | floating      |
      | DL3006 | node:26.1-alpine | node          |
      | DL3007 | python:3.12-slim | python:latest |

  @id:image-pinning.base-image-pin.002 @rule:hadofix.base-pin.refuses-without-evidence @verified @source:hadofix.py#fix_base_pin @test:tests/test_hadofix.py#test_golden @test:tests/test_hadofix.py#test_a_stage_is_never_evidence_for_itself @test:tests/test_hadofix.py#test_the_base_pin_uses_the_resolver_only_when_the_file_has_no_answer
  Scenario: A base image with no pin anywhere in the file is left for the operator
    Given no other stage pins the image `ubuntu`
    And the Dockerfile is built `FROM ubuntu`
    And the operator did not ask for digest resolution
    When the operator runs hadofix on the Dockerfile
    Then the Dockerfile is not changed
    And the report lists DL3006 under "left for you"
    And the reason says hadofix does not pick versions and suggests writing the tested tag or passing --resolve-digests to pin `ubuntu:latest`
