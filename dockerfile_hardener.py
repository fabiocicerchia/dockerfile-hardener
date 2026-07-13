#!/usr/bin/env python3
"""dockerfile-hardener — rewrite a Dockerfile to best practice and show the diff.

Not a linter: it produces the *fixed file* and a unified diff you can apply.

  dockerfile-hardener Dockerfile               # show the diff
  dockerfile-hardener Dockerfile --write       # apply in place
  dockerfile-hardener Dockerfile --explain     # diff + why, per change
"""

import argparse
import difflib
import re
import sys

CHANGES: list[tuple[str, str]] = []  # (rule, explanation) collected per run


def note(rule, explanation):
    """Record that a rule fired, with a human-readable reason."""
    CHANGES.append((rule, explanation))


def pin_latest_base(lines):
    """Tag untagged `FROM` base images with `:latest` and flag them to pin."""
    out = []
    for line in lines:
        m = re.match(r"^(FROM\s+)([^\s:@]+)(\s+AS\s+\w+)?\s*$", line, re.I)
        if m and "scratch" not in m.group(2):
            out.append(
                f"{m.group(1)}{m.group(2)}:latest{m.group(3) or ''}  # TODO: pin a real version\n"
            )
            note(
                "pin-base",
                f"base image `{m.group(2)}` had no tag — floating latest breaks reproducibility",
            )
        else:
            out.append(line)
    return out


def add_no_cache_flags(lines):
    """Add no-cache/no-recommends flags to apt-get, apk, and pip installs."""
    out = []
    for line in lines:
        new = line
        if (
            re.search(r"\bapt-get install\b", line)
            and "--no-install-recommends" not in line
        ):
            new = line.replace(
                "apt-get install", "apt-get install --no-install-recommends"
            )
            note(
                "apt-no-recommends", "avoid pulling recommended packages you don't need"
            )
        if re.search(r"\bapk add\b", line) and "--no-cache" not in line:
            new = new.replace("apk add", "apk add --no-cache")
            note("apk-no-cache", "skip the apk index cache layer")
        if re.search(r"\bpip install\b", line) and "--no-cache-dir" not in line:
            new = new.replace("pip install", "pip install --no-cache-dir")
            note("pip-no-cache", "pip's wheel cache is dead weight in an image")
        out.append(new)
    return out


def add_apt_cleanup(lines):
    """Append apt list cleanup to single-line apt-get install commands."""
    out = []
    for line in lines:
        if (
            re.search(r"apt-get install", line)
            and "rm -rf /var/lib/apt/lists" not in line
            and line.rstrip().endswith("\\") is False
        ):
            stripped = line.rstrip("\n")
            out.append(f"{stripped} && rm -rf /var/lib/apt/lists/*\n")
            note("apt-cleanup", "remove the apt package lists in the same layer")
        else:
            out.append(line)
    return out


def add_nonroot_user(lines):
    """Insert a non-root `USER` before ENTRYPOINT/CMD when none is set."""
    has_user = any(re.match(r"^USER\s+", ln, re.I) for ln in lines)
    if has_user:
        return lines
    # insert before the final ENTRYPOINT/CMD block
    idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if re.match(r"^(ENTRYPOINT|CMD)\b", lines[i], re.I):
            idx = i
    lines = (
        lines[:idx]
        + ["USER 10001  # TODO: create this user in an earlier layer if needed\n"]
        + lines[idx:]
    )
    note(
        "non-root",
        "containers should not run as root; added USER before ENTRYPOINT/CMD",
    )
    return lines


def copy_chown(lines):
    """Placeholder pass for COPY --chown suggestions (currently a no-op)."""
    out = []
    for line in lines:
        if re.match(r"^COPY\s+(?!--)", line) and "--chown" not in line:
            out.append(line)  # suggestion only when USER exists is complex; keep simple
        else:
            out.append(line)
    return out


def add_healthcheck_hint(lines):
    """Suggest a HEALTHCHECK when the image EXPOSEs a port but has none."""
    if any(re.match(r"^HEALTHCHECK\b", ln, re.I) for ln in lines):
        return lines
    if any(re.match(r"^EXPOSE\b", ln, re.I) for ln in lines):
        lines.append("# TODO(hardener): add a HEALTHCHECK for the exposed port, e.g.\n")
        lines.append(
            "# HEALTHCHECK --interval=30s CMD curl -sf http://127.0.0.1:8080/healthz || exit 1\n"
        )
        note("healthcheck", "images that EXPOSE a port should define a HEALTHCHECK")
    return lines


PASSES = [
    pin_latest_base,
    add_no_cache_flags,
    add_apt_cleanup,
    add_nonroot_user,
    copy_chown,
    add_healthcheck_hint,
]


def harden(text):
    """Run every hardening pass over `text`; return (hardened_text, changes)."""
    CHANGES.clear()
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    for p in PASSES:
        lines = p(lines)
    return "".join(lines), list(CHANGES)


def main(argv=None):
    """CLI entry point: parse args, harden the file, print diff, optionally write."""
    p = argparse.ArgumentParser(
        prog="dockerfile-hardener",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("dockerfile")
    p.add_argument("--write", action="store_true", help="apply changes in place")
    p.add_argument("--explain", action="store_true", help="explain every change")
    p.add_argument(
        "--fail-on-changes", action="store_true", help="CI mode: exit 1 if not hardened"
    )
    args = p.parse_args(argv)

    with open(args.dockerfile) as fh:
        original = fh.read()
    hardened, changes = harden(original)

    if hardened == original:
        print("dockerfile-hardener: already hardened, nothing to do")
        return 0

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        hardened.splitlines(keepends=True),
        fromfile=args.dockerfile,
        tofile=f"{args.dockerfile} (hardened)",
    )
    sys.stdout.writelines(diff)

    if args.explain:
        print("\nWhy:")
        for rule, why in dict(changes).items():
            print(f"  [{rule}] {why}")

    if args.write:
        with open(args.dockerfile, "w") as fh:
            fh.write(hardened)
        print(f"\ndockerfile-hardener: wrote {args.dockerfile}")

    return 1 if args.fail_on_changes else 0


if __name__ == "__main__":
    sys.exit(main())
