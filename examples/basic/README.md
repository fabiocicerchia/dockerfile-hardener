# Basic Example

What it shows: hardening a deliberately-bad Dockerfile (floating base tag,
recommended apt packages, no cleanup, root user, exposed port with no
healthcheck) into a best-practice one.

## Run

```sh
dockerfile-hardener examples/basic/Dockerfile --explain
```

You'll get a unified diff plus a reason for each change. Add `--write` to apply
it in place.
