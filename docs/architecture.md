# Architecture

## Overview

A single module, `hadofix.py`, with no runtime dependencies and one external
tool: hadolint. hadolint says what is wrong with a Dockerfile; hadofix decides
which of those findings it can repair without guessing, repairs them, and
prints a unified diff.

```text
Dockerfile ─┐
            ├─► hadolint --format json ─► findings ─┐
--from-json ┘                                       ├─► fixers ─► diff ─► --write
                          hadofix's own rules ──────┘
```

## Components

- **Definitions** — the module opens with the tables everything else reads:
  the `EX_*` exit codes, the `HF####` rule namespace, the compiled Dockerfile
  patterns, the package-manager descriptions, and the Docker Hub endpoints. No
  regex is compiled anywhere else.
- **`Finding`** — one rule violation in hadolint's shape (`code`, `line`,
  `level`, `message`). hadofix's own rules produce the same record, so one list
  and one report cover both.
- **`Doc`** — the Dockerfile under repair: its physical lines, the logical
  instructions parsed out of them (continuations folded, comments inside a
  continuation dropped), the stages, and — the part that matters — a map from
  each original line number to where that line lives *now*. Findings are
  reported against the file hadolint read, and every insertion moves everything
  below it, including the instruction the next finding on the same line points
  at.
- **Fixers** (`FIXERS`) — one function per rule, `(Doc, Finding) -> Fixed |
  Skipped`. `Fixed` carries the sentence that becomes the `# hadofix(RULE):`
  comment above the hunk; `Skipped` carries the sentence that says what the
  reader has to decide. Several rules can share a fixer: `DL3025` and `HF1001`
  describe the same defect, `DL3002`, `DL3066` and `HF1004` share one answer.
- **`own_findings(doc)`** — the `HF####` rules, computed from the document
  rather than from hadolint: shell-form `ENTRYPOINT`/`CMD`, an entrypoint
  script with no `exec`, a forking process with no init, and a final stage that
  never leaves root.
- **`fix(doc, findings)`** — applies every fixable finding bottom-up and
  returns one `Outcome` per finding, so nothing is silently dropped.
- **`run_hadolint` / `parse_findings`** — the engine seam. `--from-json`
  replaces the subprocess with a file or stdin, which is also how the test
  suite runs without hadolint installed.
- **`resolve_digest`** — the opt-in `--resolve-digests` path, and the only code
  that touches the network. It takes an injectable fetcher, so the tests never
  do.
- **`render_report` / `main`** — diff on stdout, report on stderr, an exit code
  from the `EX_*` table rather than an exception.

## Decisions

- **hadolint is the engine.** No second rule list to drift from yours: your
  `.hadolint.yaml`, `--ignore` flags and inline pragmas decide what is even
  considered. hadofix only ever answers findings it was handed.
- **Evidence, never invention.** A version is taken from another stage, a
  copied requirements file, or a registry digest you asked for. Everything else
  is reported with the reason it was refused.
- **Every hunk explains itself.** The comment is part of the fix: it is what
  makes the diff reviewable and what stops the change being undone next sprint.
- **Rules of our own are namespaced.** `HF####` cannot collide with `DL####`,
  so every finding can be attributed to the tool that raised it.
- **Idempotent by construction.** A fixed finding is not reported again, and
  the `HF####` rules recompute themselves from the rewritten file — tested for
  every golden case.
- **Zero Python dependencies.** Keeps install trivial and the tool safe to drop
  into any CI that already has hadolint.
- **Exit codes are a contract.** 1 means "this Dockerfile still has findings",
  so a read failure or a missing hadolint uses a sysexits code (66/69/74/77)
  and a gate can tell "not fixed" from "could not look".
