# Architecture

## Overview

A single module, `dockerfile_hardener.py`, with no runtime dependencies. It
reads a Dockerfile, runs an ordered list of **passes** over its lines, and
prints a unified diff between the original and the hardened result.

## Components

- **Definitions** — the module opens with the tables everything else reads:
  the `EX_*` exit codes, the hint lines the passes insert, the build-time
  package set, the compiled `_*_RE` Dockerfile patterns, and the Docker Hub
  registry endpoints. No regex is compiled anywhere else.
- **Passes** (`PASSES`) — each is a `lines -> lines` function that applies one
  best practice: `pin_latest_base`, `add_no_cache_flags`, `add_apt_cleanup`,
  `add_nonroot_user`, `copy_chown`, `add_healthcheck_hint`,
  `suggest_multi_stage`.
- **`note(rule, explanation)`** — passes call this to record why a change
  fired; `--explain` prints the collected notes.
- **`harden(text)`** — clears the note buffer, normalizes the trailing
  newline, runs every pass in order, returns `(hardened_text, changes)`.
- **`resolve_digest` / `pin_digests`** — the opt-in `--pin-digests` path.
  `pin_digests` takes an injectable `resolver`, so the registry call is the
  only part that touches the network and the tests never do.
- **`build_parser()` / `main(argv)`** — CLI: parse args, harden, print the
  diff, optionally `--write` in place or `--fail-on-changes` for CI. `main`
  returns an exit code from the `EX_*` table rather than raising.

## Data flow

```text
Dockerfile ──► splitlines ──► pass 1 ──► pass 2 ──► … ──► join ──► unified diff
```

## Decisions

- **Fixed file over lint warnings.** hadolint reports problems; this emits the
  corrected file plus reasons.
- **Idempotent passes.** Hardening a hardened file is a no-op — enforced by
  tests. New passes must preserve this.
- **Zero dependencies.** Keeps install trivial (`pipx install`) and the tool
  safe to drop into any CI.
- **One module.** `dockerfile_hardener.py` is the whole tool and is packaged
  as `py-modules`; data tables live in it as module constants rather than in a
  `data/` directory a single-module wheel would not ship.
- **Exit codes are a contract.** 1 is reserved for the `--fail-on-changes`
  verdict, so failures use sysexits codes (66/74/77) and a CI gate can tell
  "not hardened" from "cannot read".
