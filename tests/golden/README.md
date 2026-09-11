# Golden fixtures

One directory per rule. Each holds the whole conversation between the two
tools, so the suite can replay it without hadolint installed:

- `Dockerfile` — the input, deliberately broken in exactly one way.
- `hadolint.json` — what hadolint reports for it (`hadolint --format json`).
- `expected.diff` — hadofix's stdout: the diff it would apply.
- `expected.report` — hadofix's stderr: what it fixed, and what it left.
- `hadolint.args` — optional extra hadolint flags for this case.

A case whose `expected.diff` is empty is a rule hadofix refuses to guess at;
`expected.report` is where that refusal is recorded.

## Regenerating

After a deliberate change to a fix or to a message:

```sh
make golden   # needs hadolint on PATH
```

That runs [`regenerate.py`](regenerate.py) (hadolint over every case, with
hadolint's own defaults rather than this repository's `.hadolint.yaml`) and
then rewrites the expectations from the suite. Read the resulting diff before
committing it — it *is* the review.

Nothing in here is tidied by the whitespace hooks: a unified diff's context
lines begin with a space, so a blank context line is a line with one space on
it, and trimming it would rewrite the expectation instead of the code.
