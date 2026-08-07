# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repo.

## Project

dockerfile-hardener is a single-module Python CLI (`dockerfile_hardener.py`,
entry point `main()`) that rewrites a Dockerfile to best practice and prints a
unified diff — it produces the *fixed file*, not lint warnings. Passes are
idempotent (re-hardening a hardened file is a no-op). Tests live in `tests/`.

## Commands

```sh
# setup: make dev        # editable install with dev deps (pytest, ruff, build)
# test:  make test       # pytest -q
# lint:  make lint       # ruff check .
# run:   dockerfile-hardener Dockerfile --explain
make help    # Show this help
make setup   # Install the pre-commit hook
make install # Install the package
make dev     # Editable install with dev deps (pytest, ruff, build)
make lint    # Run ruff
make test    # Run tests
make build   # Build sdist and wheel
```

## Tooling

Shared config — the GitHub workflows, `.pre-commit-config.yaml`,
`.editorconfig`, `.hadolint.yaml`, `SECURITY.md` — comes from
[repo-skeleton](https://github.com/fabiocicerchia/repo-skeleton). Edit it
there, not here; a local edit is drift and the next sync overwrites it.
`check-drift.sh` in that repo reports what has diverged.

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
- Keep passes idempotent and add a test that proves it (see `tests/`).
- Update CHANGELOG.md (`## [Unreleased]`), docs/, and examples/ with behavior changes.
- Never commit secrets; CI runs gitleaks. Keep `.env` out of git.

## Guardrails

- Zero runtime dependencies by design — prefer stdlib, don't add deps.
- Don't touch generated files or lockfiles by hand.
- Ask before large refactors or destructive operations.

## Releases

Automated by release-please (see `.github/workflows/release.yml`). Conventional
Commits on `main` drive an open release PR that bumps `pyproject.toml` +
`CHANGELOG.md`; merging it tags `vX.Y.Z`, builds, and publishes to PyPI. Never
tag or edit the changelog by hand.
