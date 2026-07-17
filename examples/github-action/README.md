# GitHub Action: PR suggestion

What it shows: a workflow that runs dockerfile-hardener on every changed
Dockerfile in a PR and drops a comment with a ```suggestion``` block (apply
with one click in the GitHub UI) plus the full diff for context.

## Run

Copy [`pr-suggestion.yml`](pr-suggestion.yml) into a consuming repo's
`.github/workflows/`. It uses the `gh` CLI already installed on GitHub-hosted
runners, so there's nothing else to install.

This whole-file suggestion is the simple case: it comments once per file with
the entire hardened contents. Line-anchored multi-line suggestions (commenting
on the exact diff hunk) need the GitHub Pull Request Reviews API instead of
`gh pr comment` — add that if per-hunk granularity turns out to matter.
