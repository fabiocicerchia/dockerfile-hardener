# GitHub Action: PR suggestion

What it shows: a workflow that runs hadofix on every changed Dockerfile in a PR
and drops a comment with a ```suggestion``` block (apply with one click in the
GitHub UI) plus the report of what hadofix refused to guess at.

## Run

Copy [`pr-suggestion.yml`](pr-suggestion.yml) into a consuming repo's
`.github/workflows/`. It installs hadolint (hadofix's engine) and uses the `gh`
CLI already present on GitHub-hosted runners.

This whole-file suggestion is the simple case: it comments once per file with
the entire fixed contents. Line-anchored multi-line suggestions (commenting on
the exact diff hunk) need the GitHub Pull Request Reviews API instead of
`gh pr comment` — add that if per-hunk granularity turns out to matter.
