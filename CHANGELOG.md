# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

### Added

- Initial release: 7 idempotent hardening passes (pin base, apt/apk/pip cache
  flags, apt list cleanup, non-root `USER`, `COPY --chown`, HEALTHCHECK hint),
  unified diff output, `--explain`, `--write`, and `--fail-on-changes`.
