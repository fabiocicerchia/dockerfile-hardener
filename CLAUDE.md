# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repo.

## Project

hadofix is a single-module Python CLI (`hadofix.py`, entry point `main()`)
that **fixes what hadolint finds**. It runs `hadolint --format json` (or reads
that JSON on stdin), rewrites the Dockerfile for the findings whose fix is
mechanical, and lists everything else rather than guessing. The diff goes to
stdout, the report to stderr, and `--write` applies. Tests live in `tests/`,
with one golden case per rule under `tests/golden/`.

hadolint is the engine and its configuration is the configuration: a rule
ignored in `.hadolint.yaml` or by an inline pragma is never fixed. hadofix's
own rules live in the `HF####` namespace so they can never collide with
`DL####`.

## Commands

```sh
# setup: make dev        # editable install with dev deps (pytest, ruff, build)
# test:  make test       # pytest -q
# lint:  make lint       # ruff check .
# run:   hadofix Dockerfile
make help    # Show this help
make setup   # Install the pre-commit hook
make install # Install the package
make dev     # Editable install with dev deps (pytest, ruff, build)
make lint    # Run ruff
make test    # Run tests
make golden  # Regenerate the golden fixtures (needs hadolint on PATH)
make build   # Build sdist and wheel
```

## Tooling

- `make setup` installs the pre-commit hook, and that is the whole of it.
  Don't add a `.githooks/` directory: `core.hooksPath` replaces `.git/hooks/`
  wholesale, so setting it silently stops every pre-commit hook from running.
- Hooks are pinned by commit SHA with the tag in a trailing comment. A tag can
  be moved, a SHA cannot.
- CI runs this same `.pre-commit-config.yaml` through `pre-commit/action`, so
  what passes locally is what gates the pull request.
- `.greenlint.toml` tunes greenlint (rule opt-outs, ignore globs). Ignore
  globs are matched against the path as given, so write them anchored
  (`*/vendor/*`), not bare.

## Conventions

- Match existing style; don't reformat unrelated code.
- Keep fixers idempotent and add a golden case that proves it (see
  `tests/golden/README.md`). Regenerate fixtures with `make golden`, never by
  hand, and read the resulting diff — it is the review.
- A fixer may only act where the fix is unambiguous. Pin from evidence (another
  stage, a copied requirements file, a digest the user asked for); if that means
  refusing, refuse and say what the reader has to decide.
- Every fix writes a `# hadofix(RULE):` comment above its hunk: one or two
  sentences a junior would learn from.
- Update CHANGELOG.md (`## [Unreleased]`), docs/, and examples/ with behavior changes.
- Never commit secrets; CI runs gitleaks. Keep `.env` out of git.
- `tests/golden/` is excluded from the whitespace hooks on purpose: a unified
  diff's blank context line is a line with one space on it, and trimming it
  rewrites the expectation instead of the code.

## Guardrails

- Zero runtime Python dependencies by design — prefer stdlib, don't add deps.
  hadolint is the one external tool, and it is invoked as a subprocess.
- Don't touch generated files or lockfiles by hand.
- Ask before large refactors or destructive operations.

## Releases

Automated by release-please (see `.github/workflows/release.yml`). Conventional
Commits on `main` drive an open release PR that bumps `pyproject.toml` +
`CHANGELOG.md`; merging it tags `vX.Y.Z`, builds, and publishes to PyPI. Never
tag or edit the changelog by hand.
