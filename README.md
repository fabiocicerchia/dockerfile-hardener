# dockerfile-hardener

[![CI](https://github.com/fabiocicerchia/dockerfile-hardener/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiocicerchia/dockerfile-hardener/actions/workflows/ci.yml)
[![Security](https://github.com/fabiocicerchia/dockerfile-hardener/actions/workflows/security.yml/badge.svg)](https://github.com/fabiocicerchia/dockerfile-hardener/actions/workflows/security.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/fabiocicerchia/dockerfile-hardener/badge)](https://securityscorecards.dev/viewer/?uri=github.com/fabiocicerchia/dockerfile-hardener)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Ffabiocicerchia%2Fdockerfile-hardener.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Ffabiocicerchia%2Fdockerfile-hardener?ref=badge_shield)
[![Release](https://img.shields.io/github/v/release/fabiocicerchia/dockerfile-hardener)](https://github.com/fabiocicerchia/dockerfile-hardener/releases)

Rewrites Dockerfiles to best practice **as a suggested diff, not lint
warnings**. hadolint tells you what's wrong; this hands you the fixed file.

```console
$ dockerfile-hardener Dockerfile --explain
--- Dockerfile
+++ Dockerfile (hardened)
-FROM ubuntu
+FROM ubuntu:latest  # TODO: pin a real version
-RUN apt-get update && apt-get install -y curl
+RUN apt-get update && apt-get install --no-install-recommends -y curl && rm -rf /var/lib/apt/lists/*
+USER 10001  # TODO: create this user in an earlier layer if needed
 ENTRYPOINT ["app"]

Why:
  [pin-base] base image `ubuntu` had no tag — floating latest breaks reproducibility
  [apt-no-recommends] avoid pulling recommended packages you don't need
  ...
```

## Passes (v0.1)

pin untagged bases · `--no-install-recommends` · `apk --no-cache` ·
`pip --no-cache-dir` · apt list cleanup in-layer · non-root `USER` ·
HEALTHCHECK hint when a port is exposed. All passes are **idempotent**
(hardening a hardened file is a no-op — tested).

## Install

```sh
pipx install git+https://github.com/fabiocicerchia/dockerfile-hardener
```

Or with pip:

```sh
pip install git+https://github.com/fabiocicerchia/dockerfile-hardener
```

Or the one-line installer:

```sh
curl -fsSL https://raw.githubusercontent.com/fabiocicerchia/dockerfile-hardener/main/install.sh | bash
```

## Usage

```sh
pipx install .
dockerfile-hardener Dockerfile                # print the diff
dockerfile-hardener Dockerfile --write        # apply
dockerfile-hardener Dockerfile --fail-on-changes   # CI gate
dockerfile-hardener Dockerfile --pin-digests       # resolve FROM tags to a digest (Docker Hub, needs network)
```

## Development

`make dev` then `make test` / `make lint`. Run `make setup` once to enable the
gitleaks pre-commit hook.

## Documentation

Full docs live in [`docs/`](docs/) (also published via mkdocs). Runnable
examples live in [`examples/`](examples/).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Found a vulnerability? See [SECURITY.md](SECURITY.md) — please don't open a
public issue.

## License

[Apache 2.0](LICENSE) © 2026 Fabio Cicerchia.
