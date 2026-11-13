# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v1.0.1...v2.0.0) (2026-11-13)


### ⚠ BREAKING CHANGES

* drop Python 3.10, which reached end of life ([#155](https://github.com/fabiocicerchia/dockerfile-hardener/issues/155))

### Features

* drop Python 3.10, which reached end of life ([#155](https://github.com/fabiocicerchia/dockerfile-hardener/issues/155)) ([703ba65](https://github.com/fabiocicerchia/dockerfile-hardener/commit/703ba653b2142980f5d0dda5ac002b9234c4697c))


### Bug Fixes

* 3 issues found by code-atlas (ci that cannot fail) ([#152](https://github.com/fabiocicerchia/dockerfile-hardener/issues/152)) ([8e8ef63](https://github.com/fabiocicerchia/dockerfile-hardener/commit/8e8ef63147cca4138563aa5156a3bc478802d12e))
* 3 issues found by code-atlas (code design) ([#154](https://github.com/fabiocicerchia/dockerfile-hardener/issues/154)) ([7b05c8c](https://github.com/fabiocicerchia/dockerfile-hardener/commit/7b05c8c7610a1f7e29e5a4d6ba18a1a5ff07c243))
* 9 issues found by code-atlas (test suites) ([#156](https://github.com/fabiocicerchia/dockerfile-hardener/issues/156)) ([f6933de](https://github.com/fabiocicerchia/dockerfile-hardener/commit/f6933de0e6a6c03fd2228fedf50cc1f800871ed4))
* **ci:** stop typos flagging commit SHAs in CHANGELOG.md ([#167](https://github.com/fabiocicerchia/dockerfile-hardener/issues/167)) ([8ae5f4e](https://github.com/fabiocicerchia/dockerfile-hardener/commit/8ae5f4e90c01dda8005d98bf158d9b83f9662cf6))
* Update 3 dependencies in pyproject.toml ([#153](https://github.com/fabiocicerchia/dockerfile-hardener/issues/153)) ([2958924](https://github.com/fabiocicerchia/dockerfile-hardener/commit/2958924c3b9e2eb940ce2dcea59908803a1473df))

## [1.0.1](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v1.0.0...v1.0.1) (2026-09-20)


### Bug Fixes

* **ci:** keep actions: read on the job that uploads sarif ([#112](https://github.com/fabiocicerchia/dockerfile-hardener/issues/112)) ([7610a68](https://github.com/fabiocicerchia/dockerfile-hardener/commit/7610a685c866a1cb6f61264bfda13c418a6f10cb))

## [1.0.0](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.3.2...v1.0.0) (2026-09-12)


### ⚠ BREAKING CHANGES

* the package, the module and the command are now hadofix; the repository is renamed to match. The old passes are gone along with --explain, --fail-on-changes and --pin-digests (now --resolve-digests), and hadolint is required on PATH.

### Features

* rewrite as hadofix, a fixer on top of hadolint ([#95](https://github.com/fabiocicerchia/dockerfile-hardener/issues/95)) ([a5a73dc](https://github.com/fabiocicerchia/dockerfile-hardener/commit/a5a73dc158ef213731ad3696dc05585962fa6636))


### Documentation

* add a Features section to the README ([#96](https://github.com/fabiocicerchia/dockerfile-hardener/issues/96)) ([6e40532](https://github.com/fabiocicerchia/dockerfile-hardener/commit/6e40532daf90306e5d5941a042dbea21b1a14057))

## [0.3.2](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.3.1...v0.3.2) (2026-09-11)


### Bug Fixes

* **release:** let the release PR carry a token that isn't GITHUB_TOKEN ([#93](https://github.com/fabiocicerchia/dockerfile-hardener/issues/93)) ([e0d0ee4](https://github.com/fabiocicerchia/dockerfile-hardener/commit/e0d0ee4c5dc9ef5a660230c8fa515ecc3573a8b1))

## [0.3.1](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.3.0...v0.3.1) (2026-09-09)


### Bug Fixes

* put every hint on its own line, not after the instruction ([#88](https://github.com/fabiocicerchia/dockerfile-hardener/issues/88)) ([b7b0f00](https://github.com/fabiocicerchia/dockerfile-hardener/commit/b7b0f0086696d91914452e944f626619e007a35f))

## [0.3.0](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.2.1...v0.3.0) (2026-09-09)


### Features

* flag a floating base tag and a build-arg secret ([#85](https://github.com/fabiocicerchia/dockerfile-hardener/issues/85)) ([7018aca](https://github.com/fabiocicerchia/dockerfile-hardener/commit/7018acaa6b967f2462e0e562387c21f382c7b4b3))
* **packaging:** ship a man page with the wheel ([#86](https://github.com/fabiocicerchia/dockerfile-hardener/issues/86)) ([30febf8](https://github.com/fabiocicerchia/dockerfile-hardener/commit/30febf8344dd200cb0722561d59a56350bd9185c))


### Bug Fixes

* **ci:** pin the editorconfig-checker binary version ([#69](https://github.com/fabiocicerchia/dockerfile-hardener/issues/69)) ([7455368](https://github.com/fabiocicerchia/dockerfile-hardener/commit/745536827b001de020bad2d9665d3a3e0c8f8e28))
* stop the HEALTHCHECK hint re-appending on every run ([#77](https://github.com/fabiocicerchia/dockerfile-hardener/issues/77)) ([80d9399](https://github.com/fabiocicerchia/dockerfile-hardener/commit/80d9399c40a45676e74f95fdce7f8624a60129ea))

## [0.2.1](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.2.0...v0.2.1) (2026-08-29)

### Bug Fixes

- unblock quality and clear the Scorecard pinned-dependencies finding ([#56](https://github.com/fabiocicerchia/dockerfile-hardener/issues/56)) ([d2c791d](https://github.com/fabiocicerchia/dockerfile-hardener/commit/d2c791d785f65ddb8023d94ba5f8913c6b232dae))

## [0.2.0](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.1.2...v0.2.0) (2026-08-25)

### Features

- **docs:** build the docs site in Actions and drop Read the Docs ([#48](https://github.com/fabiocicerchia/dockerfile-hardener/issues/48)) ([40b508b](https://github.com/fabiocicerchia/dockerfile-hardener/commit/40b508b15586864ef8702f8e0ddf69ecfd60b082))

### Bug Fixes

- **ci:** compute the next release PR after the draft is published ([#45](https://github.com/fabiocicerchia/dockerfile-hardener/issues/45)) ([4026ccb](https://github.com/fabiocicerchia/dockerfile-hardener/commit/4026ccbb7a07aa71800128dd489afc990adfa2fb))

## [0.1.2](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.1.1...v0.1.2) (2026-08-13)

### Bug Fixes

- security and code-quality findings ([#35](https://github.com/fabiocicerchia/dockerfile-hardener/issues/35)) ([50458ab](https://github.com/fabiocicerchia/dockerfile-hardener/commit/50458abe8368b207b556e34c55656b3ed6f0f497))

## [0.1.1](https://github.com/fabiocicerchia/dockerfile-hardener/compare/v0.1.0...v0.1.1) (2026-08-06)

### Bug Fixes

- **pre-commit:** stop check-yaml failing on Helm templates and multi-doc manifests ([fc4e51c](https://github.com/fabiocicerchia/dockerfile-hardener/commit/fc4e51c80dfefb6f5a3109178a5dee41b4254d06))
- **security:** skip the SARIF upload on private repos ([6ae76e3](https://github.com/fabiocicerchia/dockerfile-hardener/commit/6ae76e396f45f57700bcf13b870c30a341155d59))

## [Unreleased]

### Fixed

- The HEALTHCHECK hint is idempotent again: it no longer re-appends its
  `# TODO(hardener)` comment on every run, so `--fail-on-changes` goes green
  for an already-hardened image that `EXPOSE`s a port.

## [0.1.0]

### Added

- Initial release: 7 idempotent hardening passes (pin base, apt/apk/pip cache
  flags, apt list cleanup, non-root `USER`, `COPY --chown`, HEALTHCHECK hint),
  unified diff output, `--explain`, `--write`, and `--fail-on-changes`.
