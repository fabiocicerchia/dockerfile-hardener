@domain:image-pinning @area:digest-lookup @from:dockerfile-hardener/hadofix-io
Feature: Pinning base images to Docker Hub digests
  Operators who opt in with --resolve-digests get untagged or :latest Docker Hub base images pinned to the digest the registry serves now, and nothing is looked up otherwise.

  Background:
    Given no other stage in the Dockerfile pins the base image

  @id:image-pinning.digest-lookup.001 @rule:image-pinning.digest-lookup.network-only-on-opt-in @verified @source:hadofix.py#main @test:tests/test_hadofix.py#test_the_base_pin_uses_the_resolver_only_when_the_file_has_no_answer @test:tests/test_hadofix.py#test_a_stage_is_never_evidence_for_itself
  Scenario: Base images are pinned to a registry digest only when the operator asks for it
    Given the Dockerfile starts with "FROM ubuntu"
    And hadolint reports DL3006 on that line
    When the operator runs hadofix on the Dockerfile without --resolve-digests
    Then the FROM line is left unchanged
    And the report lists DL3006 under "left for you", suggesting to write the tag tested against or pass --resolve-digests to pin `ubuntu:latest`

  @id:image-pinning.digest-lookup.002 @rule:image-pinning.digest-lookup.pins-docker-hub-digest @verified @source:hadofix_io.py#resolve_digest @test:tests/test_hadofix.py#test_resolve_digest_uses_the_injected_fetch @test:tests/test_hadofix.py#test_the_base_pin_uses_the_resolver_only_when_the_file_has_no_answer @questionable
  Scenario Outline: An unpinned Docker Hub base image is pinned to the digest Docker Hub serves for its tag
    Given the Dockerfile starts with "FROM <written>"
    And hadolint reports <rule> on that line
    And Docker Hub serves digest sha256:cccc…cccc for <looked up>
    When the operator runs hadofix on the Dockerfile with --resolve-digests
    Then the FROM line becomes "FROM <pinned>"
    And a # hadofix(<rule>) comment explains that a digest names the exact bytes while a tag names whatever was pushed last

    Examples:
      | written       | rule   | looked up             | pinned                         |
      | ubuntu        | DL3006 | library/ubuntu:latest | ubuntu@sha256:cccc…cccc        |
      | alpine:latest | DL3007 | library/alpine:latest | alpine:latest@sha256:cccc…cccc |
      | acme/api      | DL3006 | acme/api:latest       | acme/api@sha256:cccc…cccc      |

  @id:image-pinning.digest-lookup.003 @rule:image-pinning.digest-lookup.other-registries-never-queried @verified @source:hadofix_io.py#resolve_digest @test:tests/test_hadofix.py#test_resolve_digest_returns_none_for_a_qualified_registry
  Scenario Outline: Base images from registries other than Docker Hub are never looked up
    Given the Dockerfile starts with "FROM <image>:latest"
    And hadolint reports DL3007 on that line
    When the operator runs hadofix on the Dockerfile with --resolve-digests
    Then no request is sent for <image>
    And the FROM line is left unchanged
    And the report lists DL3007 under "left for you"

    Examples:
      | image                         |
      | ghcr.io/acme/api              |
      | registry.example.com/acme/api |
      | localhost:5000/api            |

  @id:image-pinning.digest-lookup.004 @rule:image-pinning.digest-lookup.failed-lookup-leaves-finding @inferred @source:hadofix_io.py#resolve_digest @questionable
  Scenario Outline: A failed digest lookup leaves the finding for the reader instead of failing the run
    Given the Dockerfile starts with "FROM ubuntu"
    And hadolint reports DL3006 on that line
    And Docker Hub <failure>
    When the operator runs hadofix on the Dockerfile with --resolve-digests
    Then the FROM line is left unchanged
    And the report lists DL3006 under "left for you"
    And the run still applies and reports every other fix

    Examples:
      | failure                        |
      | cannot be reached (offline)    |
      | rate-limits the request        |
      | does not know the image or tag |
      | answers without a digest       |
