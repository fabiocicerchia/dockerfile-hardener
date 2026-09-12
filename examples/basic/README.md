# Basic Example

What it shows: a deliberately broken Dockerfile — floating base tag, recommended
apt packages, no list cleanup, an unpinned package, a pipe with no pipefail, no
`USER`, a shell-form `CMD` running a forking process, and an entrypoint script
that never calls `exec`.

## Run

```sh
hadofix examples/basic/Dockerfile
```

You get the diff on stdout and, on stderr, what was fixed and what was left for
you with the reason. Add `--write` to apply it.

Note what hadofix does *not* do here: it refuses to pick a version for the base
image or for `curl`, it will not rewrite `entrypoint.sh`, and it will not
install an init for `gunicorn`. Those are listed instead — the refusals are the
point as much as the fixes.
