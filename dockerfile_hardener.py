#!/usr/bin/env python3
"""dockerfile-hardener — rewrite a Dockerfile to best practice and show the diff.

Not a linter: it produces the *fixed file* and a unified diff you can apply.

  dockerfile-hardener Dockerfile               # show the diff
  dockerfile-hardener Dockerfile --write       # apply in place
  dockerfile-hardener Dockerfile --explain     # diff + why, per change
"""

import argparse
import difflib
import json
import re
import sys
import urllib.request

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


_READONLY_HINT = (
    "# hardener: run this image with `docker run --read-only` for a "
    "read-only rootfs\n"
)


def copy_chown(lines):
    """Add COPY --chown once a non-root USER is set, and hint at a read-only rootfs."""
    user, user_idx = None, None
    for i, ln in enumerate(lines):
        m = re.match(r"^USER\s+(\S+)", ln, re.I)
        if m:
            user, user_idx = m.group(1), i
    if user is None:
        return lines
    out = []
    for i, line in enumerate(lines):
        if i > user_idx and re.match(r"^COPY\s+(?!--)", line):
            prefix, rest = line.split(None, 1)
            out.append(f"{prefix} --chown={user}:{user} {rest}")
            note("copy-chown", f"COPY after USER {user} should own the files it copies")
        else:
            out.append(line)
    if _READONLY_HINT not in out:
        out = out[: user_idx + 1] + [_READONLY_HINT] + out[user_idx + 1 :]
        note(
            "read-only-rootfs",
            "non-root images are good read-only-rootfs candidates too",
        )
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


_BUILD_TIME_PACKAGES = {
    "build-essential",
    "gcc",
    "g++",
    "make",
    "cmake",
    "python3-dev",
    "libffi-dev",
    "musl-dev",
    "cargo",
    "rustc",
}

_MULTI_STAGE_HINT = (
    "# hardener: build tooling detected in a single-stage build — consider a\n"
    "# multi-stage build (FROM ... AS builder) so build deps don't ship in the\n"
    "# final image\n"
)


def suggest_multi_stage(lines):
    """Hint at a builder stage when a single-stage build installs build-only tooling."""
    if sum(1 for ln in lines if re.match(r"^FROM\s+", ln, re.I)) != 1:
        return lines
    if _MULTI_STAGE_HINT in "".join(lines):
        return lines
    has_build_deps = any(
        re.search(r"\b(?:apt-get|apk)\s+(?:add|install)\b", ln)
        and any(pkg in ln for pkg in _BUILD_TIME_PACKAGES)
        for ln in lines
    )
    if not has_build_deps:
        return lines
    note(
        "multi-stage",
        "single-stage build installs compiler/build tooling that could live in a "
        "discarded builder stage",
    )
    return lines + [_MULTI_STAGE_HINT]


PASSES = [
    pin_latest_base,
    add_no_cache_flags,
    add_apt_cleanup,
    add_nonroot_user,
    copy_chown,
    add_healthcheck_hint,
    suggest_multi_stage,
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


def resolve_digest(image, tag, fetch=None):
    """Resolve `image:tag` to a `sha256:...` content digest via the registry API.

    Only handles Docker Hub (unqualified images like `ubuntu` or `library/ubuntu`)
    — images with an explicit registry host are left alone rather than guessing
    at registry-specific auth. Returns None on any failure (offline, rate limit,
    unknown registry) so callers can just skip pinning that line.
    """
    if "/" in image and ("." in image.split("/")[0] or ":" in image.split("/")[0]):
        return None  # explicit registry host — not Docker Hub, skip
    repo = image if "/" in image else f"library/{image}"
    fetch = fetch or _http_get
    try:
        token = json.loads(
            fetch(
                "https://auth.docker.io/token"
                f"?service=registry.docker.io&scope=repository:{repo}:pull"
            )
        )["token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
        }
        return fetch(
            f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
            headers=headers,
            digest_header=True,
        )
    except Exception:
        return None


def _http_get(url, headers=None, digest_header=False):
    """Real network fetch for resolve_digest; swapped out in tests."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as resp:
        if digest_header:
            return resp.headers.get("Docker-Content-Digest")
        return resp.read().decode()


def pin_digests(lines, resolver=None):
    """`--pin-digests`: resolve each FROM tag to a digest via a registry client."""
    resolver = resolver or resolve_digest
    out = []
    for line in lines:
        m = re.match(r"^(FROM\s+)([^\s:@]+):([^\s@]+)(\s+AS\s+\w+)?\s*(#.*)?\n?$", line, re.I)
        if m and "@sha256" not in line and m.group(2) != "scratch":
            digest = resolver(m.group(2), m.group(3))
            if digest:
                out.append(f"{m.group(1)}{m.group(2)}:{m.group(3)}@{digest}{m.group(4) or ''}\n")
                note(
                    "pin-digest",
                    f"resolved `{m.group(2)}:{m.group(3)}` to a content digest for "
                    "reproducible pulls",
                )
                continue
        out.append(line)
    return out


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
    p.add_argument(
        "--pin-digests",
        action="store_true",
        help="resolve FROM tags to a registry digest (Docker Hub only, needs network)",
    )
    args = p.parse_args(argv)

    with open(args.dockerfile) as fh:
        original = fh.read()
    hardened, changes = harden(original)

    if args.pin_digests:
        hardened = "".join(pin_digests(hardened.splitlines(keepends=True)))
        changes = list(CHANGES)

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
