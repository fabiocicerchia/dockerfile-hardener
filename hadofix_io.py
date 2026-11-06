"""hadofix's two ways out of the process: the hadolint subprocess and Docker Hub.

Kept apart from the fixers so the rules can change without touching the I/O,
and the I/O without touching the rules.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 — hadolint is the engine; running it is the point
import urllib.request
from pathlib import Path
from typing import Protocol

# hadolint exits 1 when it has findings; anything above that is a failure.
_HADOLINT_FINDINGS_EXIT = 1

# Docker Hub registry v2, the only registry --resolve-digests knows how to talk
# to. Anything with an explicit host is left alone rather than guessing at
# registry-specific auth.
_DOCKER_AUTH_URL = "https://auth.docker.io/token"
_DOCKER_AUTH_SERVICE = "registry.docker.io"
_DOCKER_REGISTRY_URL = "https://registry-1.docker.io/v2"
_MANIFEST_ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"
_HTTP_TIMEOUT_SECONDS = 10


class Fetcher(Protocol):
    """One HTTP GET, as this tool needs it: the body, or None when it failed.

    A Protocol rather than `Callable[..., str | None]`: the ellipsis form says
    nothing about the arguments, so a fake with the wrong signature
    type-checks and then fails at run time.
    """

    def __call__(self, url: str, headers: dict[str, str] | None = None, digest_header: bool = False) -> str | None: ...


class HadolintError(RuntimeError):
    """hadolint could not be run, or did not answer in JSON."""


# --------------------------------------------------------------------------
# hadolint, the engine.
# --------------------------------------------------------------------------


def run_hadolint(binary: str, dockerfile: Path) -> str:
    """Run `hadolint --format json` and hand back its output."""
    resolved = shutil.which(binary)
    if resolved is None:
        msg = (
            f"{binary}: not found. hadolint is the engine hadofix fixes for — install it "
            f"(https://github.com/hadolint/hadolint), or pass its JSON with --from-json."
        )
        raise HadolintError(msg)
    try:
        done = subprocess.run(  # noqa: S603 — a resolved path, a fixed argument list, no shell  # nosec B603
            [resolved, "--format", "json", str(dockerfile)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as err:
        msg = f"{binary}: {err.strerror}"
        raise HadolintError(msg) from err
    # hadolint exits 1 when it has findings, which is the normal case here.
    if done.returncode > _HADOLINT_FINDINGS_EXIT:
        msg = f"{binary} exited {done.returncode}: {done.stderr.strip() or done.stdout.strip()}"
        raise HadolintError(msg)
    return done.stdout


# --------------------------------------------------------------------------
# Docker Hub, for --resolve-digests.
# --------------------------------------------------------------------------


def resolve_digest(image: str, tag: str, fetch: Fetcher | None = None) -> str | None:
    """Resolve `image:tag` to a `sha256:…` digest through the Docker Hub API.

    Only Docker Hub: an image with an explicit registry host is left alone
    rather than guessing at registry-specific auth. Returns None on any failure
    (offline, rate limited, unknown image) so the caller just reports the
    finding instead.
    """
    head = image.split("/", maxsplit=1)[0]
    if "/" in image and ("." in head or ":" in head):
        return None
    repo = image if "/" in image else f"library/{image}"
    fetch = fetch or _http_get
    try:
        auth = fetch(f"{_DOCKER_AUTH_URL}?service={_DOCKER_AUTH_SERVICE}&scope=repository:{repo}:pull")
        if auth is None:
            return None
        token: object = json.loads(auth).get("token")
        if not isinstance(token, str):
            return None
        headers = {"Authorization": f"Bearer {token}", "Accept": _MANIFEST_ACCEPT}
        return fetch(f"{_DOCKER_REGISTRY_URL}/{repo}/manifests/{tag}", headers=headers, digest_header=True)
    # Any failure here means "cannot pin this line", never "crash the run".
    except Exception:
        return None


def _http_get(url: str, headers: dict[str, str] | None = None, digest_header: bool = False) -> str | None:
    """The real network fetch behind resolve_digest; swapped out in tests."""
    if not url.startswith("https://"):
        msg = f"refusing to fetch a non-https URL: {url}"
        raise ValueError(msg)
    req = urllib.request.Request(url, headers=headers or {})  # noqa: S310 — scheme checked above
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as resp:  # noqa: S310 — as above  # nosec B310
        if digest_header:
            return resp.headers.get("Docker-Content-Digest")
        return resp.read().decode()
