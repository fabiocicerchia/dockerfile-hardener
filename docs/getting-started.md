# Getting Started

## Prerequisites

- Python 3.10+
- [hadolint](https://github.com/hadolint/hadolint#install) on `PATH` — it is
  the engine hadofix fixes for, not a bundled copy
- [`pipx`](https://pipx.pypa.io/) (recommended) or `pip`

## Install

```sh
pipx install .          # from a checkout
# or: pip install hadofix
```

## Run

```sh
hadofix Dockerfile                       # print the diff and the report
hadofix Dockerfile --write               # apply it
hadofix Dockerfile --resolve-digests     # pin a base image to a Docker Hub digest
hadolint -f json Dockerfile | hadofix Dockerfile --from-json -
```

The diff goes to stdout, the report to stderr: pipe the first into `git apply`,
read the second.

## In CI

`hadofix Dockerfile` exits non-zero while anything is left — a fix nobody
applied, or a finding hadofix refused to guess at — so it works as a gate with
no extra flag:

```yaml
- run: hadofix Dockerfile
```

To fail only on what hadofix cannot repair, apply the repairs first:

```yaml
- run: hadofix Dockerfile --write
```

## Reading the output

A `# hadofix(RULE):` comment above a hunk says why that change is right. A
finding under "left for you" is one hadofix will not guess at, and the `→` line
says what it would need from you instead — usually a version only you know.

See [`examples/basic/`](https://github.com/fabiocicerchia/hadofix/blob/main/examples/basic/README.md)
for a runnable example.
