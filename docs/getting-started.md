# Getting Started

## Prerequisites

- Python 3.10+
- [`pipx`](https://pipx.pypa.io/) (recommended) or `pip`

## Install

```sh
pipx install .          # from a checkout
# or: pip install dockerfile-hardener
```

## Run

```sh
dockerfile-hardener Dockerfile                  # print the hardening diff
dockerfile-hardener Dockerfile --explain        # diff + why, per change
dockerfile-hardener Dockerfile --write          # apply in place
dockerfile-hardener Dockerfile --fail-on-changes  # CI gate (non-zero if changes)
```

See [`examples/basic/`](https://github.com/fabiocicerchia/dockerfile-hardener/blob/main/examples/basic/README.md) for a runnable example.
