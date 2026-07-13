# Architecture

## Overview

A single module, `dockerfile_hardener.py`, with no runtime dependencies. It
reads a Dockerfile, runs an ordered list of **passes** over its lines, and
prints a unified diff between the original and the hardened result.

## Components

- **Passes** (`PASSES`) — each is a `lines -> lines` function that applies one
  best practice: `pin_latest_base`, `add_no_cache_flags`, `add_apt_cleanup`,
  `add_nonroot_user`, `copy_chown`, `add_healthcheck_hint`.
- **`note(rule, explanation)`** — passes call this to record why a change
  fired; `--explain` prints the collected notes.
- **`harden(text)`** — clears the note buffer, normalizes the trailing
  newline, runs every pass in order, returns `(hardened_text, changes)`.
- **`main(argv)`** — CLI: parse args, harden, print the diff, optionally
  `--write` in place or `--fail-on-changes` for CI.

## Data flow

```
Dockerfile ──► splitlines ──► pass 1 ──► pass 2 ──► … ──► join ──► unified diff
```

## Decisions

- **Fixed file over lint warnings.** hadolint reports problems; this emits the
  corrected file plus reasons.
- **Idempotent passes.** Hardening a hardened file is a no-op — enforced by
  tests. New passes must preserve this.
- **Zero dependencies.** Keeps install trivial (`pipx install`) and the tool
  safe to drop into any CI.
