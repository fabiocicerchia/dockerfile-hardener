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
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

CHANGES: list[tuple[str, str]] = []  # (rule, explanation) collected per run

# Exit codes, sysexits.h style. 1 is the documented --fail-on-changes verdict, so
# errors never reuse it: a CI gate has to tell "not hardened" from "cannot read".
EX_OK = 0
EX_NOT_HARDENED = 1
EX_NOINPUT = 66
EX_NOPERM = 77
EX_IOERR = 74
# Keyed by the OSError subclasses this tool distinguishes; anything else
# falls through to EX_IOERR, so the annotation is the wider type on purpose.
_READ_FAILURE_CODES: dict[type[OSError], int] = {
    FileNotFoundError: EX_NOINPUT,
    PermissionError: EX_NOPERM,
}

# Lines the passes insert. Each is matched verbatim to stay idempotent, so the
# text is a constant rather than a literal repeated at the insertion site.
_READONLY_HINT = "# hardener: run this image with `docker run --read-only` for a read-only rootfs\n"
_HEALTHCHECK_HINT = (
    "# TODO(hardener): add a HEALTHCHECK for the exposed port, e.g.\n"
    "# HEALTHCHECK --interval=30s CMD curl -sf http://127.0.0.1:8080/healthz || exit 1\n"
)
_MULTI_STAGE_HINT = (
    "# hardener: build tooling detected in a single-stage build — consider a\n"
    "# multi-stage build (FROM ... AS builder) so build deps don't ship in the\n"
    "# final image\n"
)

# Packages that only a compile step needs; seeing them in a single-stage build
# is the signal for the multi-stage hint.
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

# Dockerfile instructions the passes look for. Every regex in this module lives
# here; Dockerfile keywords are case-insensitive, so all but _COPY_RE say so.
_UNTAGGED_FROM_RE = re.compile(r"^(FROM\s+)([^\s:@]+)(\s+AS\s+\w+)?\s*$", re.IGNORECASE)
_TAGGED_FROM_RE = re.compile(r"^(FROM\s+)([^\s:@]+):([^\s@]+)(\s+AS\s+\w+)?\s*(#.*)?\n?$", re.IGNORECASE)
_FROM_RE = re.compile(r"^FROM\s+", re.IGNORECASE)
_USER_RE = re.compile(r"^USER\s+", re.IGNORECASE)
_USER_NAME_RE = re.compile(r"^USER\s+(\S+)", re.IGNORECASE)
_ENTRYPOINT_OR_CMD_RE = re.compile(r"^(ENTRYPOINT|CMD)\b", re.IGNORECASE)
_HEALTHCHECK_RE = re.compile(r"^HEALTHCHECK\b", re.IGNORECASE)
_EXPOSE_RE = re.compile(r"^EXPOSE\b", re.IGNORECASE)
_COPY_RE = re.compile(r"^COPY\s+(?!--)")

# Package-manager invocations inside RUN lines.
_APT_INSTALL_RE = re.compile(r"\bapt-get install\b")
_APK_ADD_RE = re.compile(r"\bapk add\b")
_PIP_INSTALL_RE = re.compile(r"\bpip install\b")
_PACKAGE_INSTALL_RE = re.compile(r"\b(?:apt-get|apk)\s+(?:add|install)\b")

# Docker Hub registry v2, the only registry --pin-digests knows how to talk to.
_DOCKER_AUTH_URL = "https://auth.docker.io/token"
_DOCKER_AUTH_SERVICE = "registry.docker.io"
_HTTP_TIMEOUT_SECONDS = 10
_DOCKER_REGISTRY_URL = "https://registry-1.docker.io/v2"


# The two seams the tests swap out. Named so the signatures below say what they
# take rather than `Callable[..., Any]`.
class Fetcher(Protocol):
    """One HTTP GET, as this tool needs it: the body, or None when it failed.

    A Protocol rather than `Callable[..., str | None]`: the ellipsis form says
    nothing about the arguments, so a fake with the wrong signature type-checks
    and then fails at run time.
    """

    def __call__(self, url: str, headers: dict[str, str] | None = None, digest_header: bool = False) -> str | None: ...


Resolver = Callable[[str, str], str | None]
_MANIFEST_ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"


def note(rule: str, explanation: str) -> None:
    """Record that a rule fired, with a human-readable reason."""
    CHANGES.append((rule, explanation))


def pin_latest_base(lines: list[str]) -> list[str]:
    """Tag untagged `FROM` base images with `:latest` and flag them to pin."""
    out: list[str] = []
    for line in lines:
        m = _UNTAGGED_FROM_RE.match(line)
        if m and "scratch" not in m.group(2):
            keyword, image, stage = m.group(1), m.group(2), m.group(3) or ""
            out.append(f"{keyword}{image}:latest{stage}  # TODO: pin a real version\n")
            note(
                "pin-base",
                f"base image `{image}` had no tag — floating latest breaks reproducibility",
            )
        else:
            out.append(line)
    return out


def add_no_cache_flags(lines: list[str]) -> list[str]:
    """Add no-cache/no-recommends flags to apt-get, apk, and pip installs."""
    out: list[str] = []
    for line in lines:
        new = line
        if _APT_INSTALL_RE.search(line) and "--no-install-recommends" not in line:
            new = line.replace("apt-get install", "apt-get install --no-install-recommends")
            note("apt-no-recommends", "avoid pulling recommended packages you don't need")
        if _APK_ADD_RE.search(line) and "--no-cache" not in line:
            new = new.replace("apk add", "apk add --no-cache")
            note("apk-no-cache", "skip the apk index cache layer")
        if _PIP_INSTALL_RE.search(line) and "--no-cache-dir" not in line:
            new = new.replace("pip install", "pip install --no-cache-dir")
            note("pip-no-cache", "pip's wheel cache is dead weight in an image")
        out.append(new)
    return out


def add_apt_cleanup(lines: list[str]) -> list[str]:
    """Append apt list cleanup to single-line apt-get install commands."""
    out: list[str] = []
    for line in lines:
        if (
            "apt-get install" in line
            and "rm -rf /var/lib/apt/lists" not in line
            and line.rstrip().endswith("\\") is False
        ):
            stripped = line.rstrip("\n")
            out.append(f"{stripped} && rm -rf /var/lib/apt/lists/*\n")
            note("apt-cleanup", "remove the apt package lists in the same layer")
        else:
            out.append(line)
    return out


def add_nonroot_user(lines: list[str]) -> list[str]:
    """Insert a non-root `USER` before ENTRYPOINT/CMD when none is set."""
    has_user = any(_USER_RE.match(ln) for ln in lines)
    if has_user:
        return lines
    # insert before the final ENTRYPOINT/CMD block
    idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if _ENTRYPOINT_OR_CMD_RE.match(lines[i]):
            idx = i
    lines = [*lines[:idx], "USER 10001  # TODO: create this user in an earlier layer if needed\n", *lines[idx:]]
    note(
        "non-root",
        "containers should not run as root; added USER before ENTRYPOINT/CMD",
    )
    return lines


def copy_chown(lines: list[str]) -> list[str]:
    """Add COPY --chown once a non-root USER is set, and hint at a read-only rootfs."""
    # One variable, because the name and the line it was found on are one
    # fact: guarding the name alone left the index optional for anything that
    # reads it below.
    found: tuple[str, int] | None = None
    for i, ln in enumerate(lines):
        m = _USER_NAME_RE.match(ln)
        if m:
            found = (m.group(1), i)
    if found is None:
        return lines
    user, user_idx = found
    out: list[str] = []
    for i, line in enumerate(lines):
        if i > user_idx and _COPY_RE.match(line):
            prefix, rest = line.split(None, 1)
            out.append(f"{prefix} --chown={user}:{user} {rest}")
            note("copy-chown", f"COPY after USER {user} should own the files it copies")
        else:
            out.append(line)
    if _READONLY_HINT not in out:
        out = [*out[: user_idx + 1], _READONLY_HINT, *out[user_idx + 1 :]]
        note(
            "read-only-rootfs",
            "non-root images are good read-only-rootfs candidates too",
        )
    return out


def add_healthcheck_hint(lines: list[str]) -> list[str]:
    """Suggest a HEALTHCHECK when the image EXPOSEs a port but has none."""
    if any(_HEALTHCHECK_RE.match(ln) for ln in lines):
        return lines
    if any(_EXPOSE_RE.match(ln) for ln in lines):
        lines.append(_HEALTHCHECK_HINT)
        note("healthcheck", "images that EXPOSE a port should define a HEALTHCHECK")
    return lines


def suggest_multi_stage(lines: list[str]) -> list[str]:
    """Hint at a builder stage when a single-stage build installs build-only tooling."""
    if sum(1 for ln in lines if _FROM_RE.match(ln)) != 1:
        return lines
    if _MULTI_STAGE_HINT in "".join(lines):
        return lines
    has_build_deps = any(
        _PACKAGE_INSTALL_RE.search(ln) and any(pkg in ln for pkg in _BUILD_TIME_PACKAGES) for ln in lines
    )
    if not has_build_deps:
        return lines
    note(
        "multi-stage",
        "single-stage build installs compiler/build tooling that could live in a discarded builder stage",
    )
    return [*lines, _MULTI_STAGE_HINT]


PASSES = [
    pin_latest_base,
    add_no_cache_flags,
    add_apt_cleanup,
    add_nonroot_user,
    copy_chown,
    add_healthcheck_hint,
    suggest_multi_stage,
]


def harden(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Run every hardening pass over `text`; return (hardened_text, changes)."""
    CHANGES.clear()
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    for hardening_pass in PASSES:
        lines = hardening_pass(lines)
    return "".join(lines), list(CHANGES)


def resolve_digest(image: str, tag: str, fetch: Fetcher | None = None) -> str | None:
    """Resolve `image:tag` to a `sha256:...` content digest via the registry API.

    Only handles Docker Hub (unqualified images like `ubuntu` or `library/ubuntu`)
    — images with an explicit registry host are left alone rather than guessing
    at registry-specific auth. Returns None on any failure (offline, rate limit,
    unknown registry) so callers can just skip pinning that line.
    """
    if "/" in image and ("." in image.split("/", maxsplit=1)[0] or ":" in image.split("/", maxsplit=1)[0]):
        return None  # explicit registry host — not Docker Hub, skip
    repo = image if "/" in image else f"library/{image}"
    fetch = fetch or _http_get
    try:
        auth = fetch(f"{_DOCKER_AUTH_URL}?service={_DOCKER_AUTH_SERVICE}&scope=repository:{repo}:pull")
        if auth is None:
            return None  # offline, rate-limited or refused: skip pinning this line
        token = json.loads(auth)["token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": _MANIFEST_ACCEPT,
        }
        return fetch(
            f"{_DOCKER_REGISTRY_URL}/{repo}/manifests/{tag}",
            headers=headers,
            digest_header=True,
        )
    except Exception:
        return None


def _http_get(url: str, headers: dict[str, str] | None = None, digest_header: bool = False) -> str | None:
    """Real network fetch for resolve_digest; swapped out in tests."""
    if not url.startswith("https://"):
        msg = f"refusing to fetch a non-https URL: {url}"
        raise ValueError(msg)
    req = urllib.request.Request(url, headers=headers or {})  # noqa: S310 — scheme checked above
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as resp:  # noqa: S310 — as above
        if digest_header:
            return resp.headers.get("Docker-Content-Digest")
        return resp.read().decode()


def pin_digests(lines: list[str], resolver: Resolver | None = None) -> list[str]:
    """`--pin-digests`: resolve each FROM tag to a digest via a registry client."""
    resolver = resolver or resolve_digest
    out: list[str] = []
    for line in lines:
        m = _TAGGED_FROM_RE.match(line)
        if not m or "@sha256" in line or m.group(2) == "scratch":
            out.append(line)
            continue
        keyword, image, tag, stage = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        digest = resolver(image, tag)
        if not digest:
            out.append(line)
            continue
        out.append(f"{keyword}{image}:{tag}@{digest}{stage}\n")
        note("pin-digest", f"resolved `{image}:{tag}` to a content digest for reproducible pulls")
    return out


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="dockerfile-hardener",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("dockerfile")
    parser.add_argument("--write", action="store_true", help="apply changes in place")
    parser.add_argument("--explain", action="store_true", help="explain every change")
    parser.add_argument("--fail-on-changes", action="store_true", help="CI mode: exit 1 if not hardened")
    parser.add_argument(
        "--pin-digests",
        action="store_true",
        help="resolve FROM tags to a registry digest (Docker Hub only, needs network)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse args, harden the file, print diff, optionally write."""
    args = build_parser().parse_args(argv)

    try:
        original = Path(args.dockerfile).read_text()
    except OSError as err:
        # The tool's own output
        print(f"dockerfile-hardener: {args.dockerfile}: {err.strerror}", file=sys.stderr)  # noqa: T201
        return _READ_FAILURE_CODES.get(type(err), EX_IOERR)
    hardened, changes = harden(original)

    if args.pin_digests:
        hardened = "".join(pin_digests(hardened.splitlines(keepends=True)))
        changes = list(CHANGES)

    if hardened == original:
        print("dockerfile-hardener: already hardened, nothing to do")  # noqa: T201 — the tool's own output
        return EX_OK

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        hardened.splitlines(keepends=True),
        fromfile=args.dockerfile,
        tofile=f"{args.dockerfile} (hardened)",
    )
    sys.stdout.writelines(diff)

    if args.explain:
        print("\nWhy:")  # noqa: T201 — the tool's own output
        for rule, why in dict(changes).items():
            print(f"  [{rule}] {why}")  # noqa: T201 — the tool's own output

    if args.write:
        Path(args.dockerfile).write_text(hardened)
        print(f"\ndockerfile-hardener: wrote {args.dockerfile}")  # noqa: T201 — the tool's own output

    return EX_NOT_HARDENED if args.fail_on_changes else EX_OK


if __name__ == "__main__":
    sys.exit(main())
