# hadofix

[![CI](https://github.com/fabiocicerchia/hadofix/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiocicerchia/hadofix/actions/workflows/ci.yml)
[![Security](https://github.com/fabiocicerchia/hadofix/actions/workflows/security.yml/badge.svg)](https://github.com/fabiocicerchia/hadofix/actions/workflows/security.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/fabiocicerchia/hadofix/badge)](https://securityscorecards.dev/viewer/?uri=github.com/fabiocicerchia/hadofix)
[![CI carbon](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/fabiocicerchia/hadofix/gh-pages/badge.json)](.github/workflows/carbon-badge.yml)
[![Release](https://img.shields.io/github/v/release/fabiocicerchia/hadofix)](https://github.com/fabiocicerchia/hadofix/releases)

**hadolint finds it. hadofix fixes it.**

[hadolint](https://github.com/hadolint/hadolint) is *the* Dockerfile linter,
and this is not another one. hadofix runs `hadolint --format json`, rewrites
the Dockerfile for the rules whose fix is mechanical, and lists everything else
rather than guessing at it.

Every hunk it writes carries a comment saying *why*, because a fix you don't
understand is a fix you undo next sprint.

## Example

```console
$ hadofix Dockerfile
--- Dockerfile
+++ Dockerfile (hadofix)
@@ -1,8 +1,19 @@
 FROM python:3.12-slim
-RUN apt-get update && apt-get install -y curl
+# hadofix(DL3015): apt pulls every `Recommends` of every package by default —
+# software nobody in this Dockerfile asked for, shipped in the image and
+# reported by every scanner. The flag installs what is named here and stops.
+# hadofix(DL3009): The cleanup has to run in the same RUN as the install: a
+# later layer can hide the lists but every layer is still in the image, still
+# pushed, still pullable. Same layer, or it is only hidden.
+RUN apt-get update && apt-get install --no-install-recommends -y curl && rm -rf /var/lib/apt/lists/*
 COPY entrypoint.sh /entrypoint.sh
 COPY app /opt/app
 EXPOSE 8000
 USER 10001
 ENTRYPOINT ["/entrypoint.sh"]
-CMD gunicorn --bind 0.0.0.0:8000 app:wsgi
+# hadofix(HF1001): Shell form runs `/bin/sh -c 'gunicorn --bind 0.0.0.0:8000
+# app:wsgi'`, so PID 1 is sh. `docker stop` sends SIGTERM to PID 1, sh does not
+# forward it, and ten seconds later the container is SIGKILLed mid-request.
+# Exec form makes `gunicorn` PID 1 and puts the signal where the shutdown
+# handler is.
+CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:wsgi"]
hadofix: fixed 4 findings in Dockerfile: DL3009, DL3015, DL3025, HF1001
hadofix: 3 findings left for you:
  Dockerfile:2 warning DL3008
      Pin versions in apt get install. Instead of `apt-get install <package>`
      use `apt-get install <package>=<version>`
      → hadofix does not invent versions: nothing in this file pins `curl`.
        `apt-cache policy <package>` inside the base image prints the version
        to write.
  Dockerfile:7 warning HF1002
      `entrypoint.sh` never calls `exec`, so the command it starts is a child
      of the script: PID 1 stays /bin/sh, SIGTERM stops the wrapper and the app
      is killed on the timeout. End the script with `exec "$@"` (or `exec
      <command>`).
  Dockerfile:8 info HF1003
      `gunicorn` forks worker processes, and as PID 1 it also inherits every
      orphan in the container and is expected to reap it — PID 1 gets no
      default signal handlers either. Put an init in front (tini, dumb-init) or
      run the container with `docker run --init`.
hadofix: nothing written — re-run with --write to apply
```

The diff goes to stdout and the report to stderr, so
`hadofix Dockerfile | git apply` and `hadofix Dockerfile --write` are both
ordinary things to do.

## Features

- **hadolint is the engine.** hadofix runs `hadolint --format json` (or reads
  that JSON on stdin), so your `.hadolint.yaml`, `--ignore` flags and inline
  pragmas are the configuration — there is no second rule list to keep in sync.
- **Rewrites the Dockerfile** for the rules whose fix is mechanical: base
  pinning (`DL3006`, `DL3007`), package pinning (`DL3008`, `DL3013`, `DL3018`),
  apt list cleanup (`DL3009`), `--no-install-recommends` (`DL3015`), a non-root
  `USER` (`DL3002`, `DL3066`), `SHELL … -o pipefail` (`DL4006`) and exec-form
  `CMD`/`ENTRYPOINT` (`DL3025`).
- **Every hunk carries a `# hadofix(RULE):` comment** — one or two sentences on
  why the change is right, so the diff is reviewable and the fix survives.
- **Four rules of its own**, namespaced `HF####` so they cannot collide with
  hadolint's: PID 1 and signals (`HF1001`), an entrypoint script that never
  calls `exec` (`HF1002`), a forking process with no init (`HF1003`), and a
  final stage that never leaves root (`HF1004`).
- **Pins from evidence, never invention** — another stage in the same file, a
  requirements file the Dockerfile copies in, or a registry digest you asked
  for with `--resolve-digests`. Where there is none it refuses, and says what
  you have to decide.
- **Idempotent** — fixing a fixed file is a no-op, proved by a golden case per
  rule.
- `--write` to apply; plain `hadofix Dockerfile` is already a CI gate.
- Distinct exit codes for "findings remain" (1) versus a Dockerfile that is
  missing (66), unreadable (74) or permission-denied (77), and a hadolint that
  is not installed (69) — so CI can tell a finding from a broken run.

## How it works

```text
Dockerfile ──► hadolint --format json ──► hadofix ──► unified diff ──► --write
```

- **hadolint decides what is wrong.** Your `.hadolint.yaml`, your `--ignore`
  flags and your inline `# hadolint ignore=` pragmas are the configuration: a
  rule you switched off is never fixed, and hadofix has no rule list of its own
  to keep in sync with yours.
- **hadofix decides what can be repaired without guessing**, repairs it, and
  explains it in the file.
- **Everything else is listed**, with the reason it was left — which is the
  useful half when the reason is "only you know the version you test against".

Already have hadolint output? Pipe it in and hadofix won't run the linter
itself:

```sh
hadolint -f json Dockerfile | hadofix Dockerfile --from-json -
```

## What it fixes

| Rule | hadolint's finding | What hadofix writes |
| --- | --- | --- |
| `DL3006` | base image has no tag | the tag another stage pins, or a digest |
| `DL3007` | base image is `:latest` | as above — `:latest` is never the answer |
| `DL3008` `DL3013` `DL3018` | package is unpinned | the version this repository pins elsewhere |
| `DL3009` | apt lists left behind | `&& rm -rf /var/lib/apt/lists/*`, same `RUN` |
| `DL3015` | apt installs recommended packages | `--no-install-recommends` |
| `DL3002` `DL3066` | last `USER` is root, or is not numeric | `USER 10001` |
| `DL4006` | `RUN` with a pipe and no pipefail | a `SHELL` line with `-o pipefail` above it |
| `DL3025` | `CMD`/`ENTRYPOINT` in shell form | the same command in exec form |

A base image is pinned from another stage in the same file, or from a digest
with `--resolve-digests`; a package from another stage or a `requirements.txt`
the Dockerfile copies in. The `SHELL` line names `/bin/bash`, or `/bin/ash`
when the stage's base is alpine or busybox. Exec form is only written where the
command needs no shell.

Anything else hadolint reports is listed untouched. Adding a rule is one fixer
and one golden test — the bar is that the fix is *unambiguous*, not that it is
common.

## Rules of its own

Three things hadolint has no rule for, plus one it only half covers. They are
reported in hadolint's own shape, in a namespace that cannot collide with
`DL####`:

- **`HF1001` — shell form makes the shell PID 1.** `docker stop` sends SIGTERM
  to `/bin/sh`, which does not forward it, so the app is SIGKILLed on the
  timeout instead of shutting down. **Fixed**, by the same rewrite as `DL3025`:
  that rule flags the form, this one is the consequence.
- **`HF1002` — the entrypoint script never calls `exec`.** The command runs as
  a child of the script, so PID 1 stays the wrapper. **Reported**: where `exec`
  belongs is a decision about the script.
- **`HF1003` — a process that forks workers, with no init.** nginx, gunicorn
  and friends inherit every orphan in the container as PID 1 and are expected
  to reap it, and PID 1 gets no default signal handlers. **Reported**.
- **`HF1004` — the final stage never sets a `USER`.** Everything in the image
  runs as root, and hadolint's `DL3002` only fires on an explicit `USER root`.
  **Fixed**: `USER 10001` before the final command.

## What it refuses to guess at

A fixer that guesses is worse than no fixer: you stop reading its diffs.

- **A version nothing in the repository commits to.** hadofix pins from
  evidence — another stage, a copied requirements file, a registry digest you
  asked for with `--resolve-digests`. It will not pick "the latest one" for
  `curl` or for your base image.
- **A command that needs a shell.** `CMD app --port $PORT` stays in shell form:
  exec form would stop expanding `$PORT`. hadofix says so and shows you
  `CMD ["sh", "-c", "…"]` if a shell is what you meant.
- **Your entrypoint script's control flow** (`HF1002`). Where `exec` belongs is
  a decision about the script, not a text substitution.
- **Installing an init for you** (`HF1003`). tini or dumb-init is a package in
  the image, or `--init` at run time; both are calls hadofix isn't in a
  position to make.
- **A `USER` you already chose.** If the final stage sets one, hadofix leaves
  it alone even when hadolint would rather it were numeric.

## Install

hadofix needs [hadolint](https://github.com/hadolint/hadolint#install) on
`PATH` — it is the engine, not a bundled copy.

```sh
pipx install git+https://github.com/fabiocicerchia/hadofix
```

Or with pip:

```sh
pip install git+https://github.com/fabiocicerchia/hadofix
```

Or the one-line installer:

```sh
curl -fsSL https://raw.githubusercontent.com/fabiocicerchia/hadofix/main/install.sh | bash
```

## Usage

```sh
hadofix Dockerfile                       # print the diff
hadofix Dockerfile --write               # apply it
hadofix Dockerfile --resolve-digests     # let DL3006/DL3007 pin to a Docker Hub digest (needs network)
hadofix Dockerfile --from-json out.json  # use hadolint output you already have (`-` for stdin)
hadofix Dockerfile --hadolint ./hadolint # a hadolint that isn't on PATH
```

As a CI gate, `hadofix Dockerfile` is enough: it exits non-zero while anything
is left, whether that is a fix nobody applied or a finding hadofix refused.

## Exit codes

| Code | Meaning |
| ---- | ---------------------------------------------------------------- |
| 0 | clean — hadolint found nothing, or everything it found was fixed and written |
| 1 | findings remain: some were refused, or the diff was printed and not applied |
| 2 | bad command line (argparse) |
| 66 | the Dockerfile does not exist |
| 69 | hadolint is not installed, or its output could not be read |
| 74 | the Dockerfile exists but could not be read |
| 77 | permission denied |

## Development

`make dev`, then `make test` and `make lint`. `make golden` regenerates the
fixtures in [`tests/golden/`](tests/golden/README.md) — one directory per rule,
holding the Dockerfile, the hadolint JSON for it, and the exact diff and report
hadofix produces. The suite replays the stored JSON, so it runs without
hadolint installed; one end-to-end test drives the real binary and skips when
it is missing.

Run `make setup` once to enable the pre-commit hooks.

## Documentation

Full docs live in [`docs/`](docs/) (also published via mkdocs). Runnable
examples live in [`examples/`](examples/).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). By participating you agree to the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Found a vulnerability? See [SECURITY.md](SECURITY.md) — please don't open a
public issue.

## Support

Need help implementing this? [Get in touch](https://fabiocicerchia.it/contact).

## License

[Apache 2.0](LICENSE) © 2026 Fabio Cicerchia.
