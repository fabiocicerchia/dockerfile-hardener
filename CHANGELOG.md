# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0 (2026-07-29)


### Features

* add --pin-digests to resolve FROM tags to a registry digest ([fd7c18f](https://github.com/fabiocicerchia/dockerfile-hardener/commit/fd7c18f3230e9469e9b0f33cfe5f83d4dbae223f))
* add GitHub Action posting hardening suggestions on PRs ([547fe14](https://github.com/fabiocicerchia/dockerfile-hardener/commit/547fe1474617683819a1bd70db283702f69f3c08))
* add install.sh one-liner installer ([e09f637](https://github.com/fabiocicerchia/dockerfile-hardener/commit/e09f63743e381251651c6f20390884171fdcd829))
* implement COPY --chown and read-only rootfs advice ([a0c9655](https://github.com/fabiocicerchia/dockerfile-hardener/commit/a0c9655cbd1130286649b29c777866b037afd0fb))
* suggest a multi-stage build when build tooling ships in a single stage ([c603903](https://github.com/fabiocicerchia/dockerfile-hardener/commit/c603903ffe3862cad5fe9f02f1d61d2812c42522))


### Bug Fixes

* restore executable bit, document intentional blind except, drop unused var ([#15](https://github.com/fabiocicerchia/dockerfile-hardener/issues/15)) ([2d842d3](https://github.com/fabiocicerchia/dockerfile-hardener/commit/2d842d330223ac5a91a8e96f201fccf1fa8afc93))


### Documentation

* add GitHub Pages site, trim completed roadmap items from README ([43296ef](https://github.com/fabiocicerchia/dockerfile-hardener/commit/43296ef7104a43407fcceb4e45c6515769d23505))
* add missing README badges ([69b8680](https://github.com/fabiocicerchia/dockerfile-hardener/commit/69b86808d3b65e3c32deed156a4374b2a14ac113))
* remove the broken FOSSA badge ([216ad06](https://github.com/fabiocicerchia/dockerfile-hardener/commit/216ad060eb51cef2a0355642e0d6c8dd8a59ceba))

## [Unreleased]

## [0.1.0]

### Added

- Initial release: 7 idempotent hardening passes (pin base, apt/apk/pip cache
  flags, apt list cleanup, non-root `USER`, `COPY --chown`, HEALTHCHECK hint),
  unified diff output, `--explain`, `--write`, and `--fail-on-changes`.
