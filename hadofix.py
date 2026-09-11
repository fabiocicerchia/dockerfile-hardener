#!/usr/bin/env python3
"""hadofix — apply the fixes hadolint asks for.

hadolint is the engine. hadofix runs `hadolint --format json` (or reads that
JSON on stdin), rewrites the Dockerfile for the findings whose fix is
mechanical, and lists everything else instead of guessing at it.

  hadofix Dockerfile                                  # print the diff
  hadofix Dockerfile --write                          # apply it
  hadolint -f json Dockerfile | hadofix Dockerfile --from-json -

Every hunk carries a `# hadofix(RULE):` comment saying why the change is
right, so the diff teaches as well as fixes.
"""

import argparse
import difflib
import json
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Protocol, cast

# Exit codes, sysexits.h style. 1 is the CI verdict "this Dockerfile still has
# findings", so a read failure never reuses it: a gate has to tell "not fixed"
# from "could not look".
EX_OK = 0
EX_FINDINGS = 1
EX_NOINPUT = 66
EX_UNAVAILABLE = 69
EX_IOERR = 74
EX_NOPERM = 77
_READ_FAILURE_CODES: dict[type[OSError], int] = {
    FileNotFoundError: EX_NOINPUT,
    PermissionError: EX_NOPERM,
}

# Rules of our own live in their own namespace. DL#### belongs to hadolint, and
# a collision would make a finding impossible to attribute to the tool that
# raised it — or to look up.
HF_SHELL_FORM = "HF1001"
HF_NO_EXEC = "HF1002"
HF_NO_INIT = "HF1003"
# hadolint's DL3002 only fires on an explicit `USER root`: a Dockerfile that
# simply never sets a USER runs as root and is reported by nobody, so this one
# is ours. Its fix is DL3002's fix.
HF_ROOT_DEFAULT = "HF1004"

# The UID a fixed Dockerfile runs as. A number rather than a name because
# creating an account is distro-specific (adduser, useradd, addgroup -S) and
# hadofix does not guess at the base image's userland.
NONROOT_UID = "10001"

_COMMENT_WIDTH = 79
_COMMENT_PREFIX = "# hadofix"

_FROM_RE = re.compile(r"^(?P<indent>\s*)FROM\s+(?P<ref>\S+)(?:\s+AS\s+(?P<alias>\S+))?\s*$", re.IGNORECASE)
_USER_RE = re.compile(r"^(?P<head>\s*USER\s+)(?P<who>\S+)\s*$", re.IGNORECASE)
_ENTRYPOINT_OR_CMD_RE = re.compile(r"^(?P<indent>\s*)(?P<keyword>ENTRYPOINT|CMD)\s+(?P<args>.+)$", re.IGNORECASE)
_APT_INSTALL_RE = re.compile(r"\b(apt(?:-get)?\s+install)\b")
_EXEC_UNSAFE_RE = re.compile(r"[|&;<>$`*?(){}\[\]\\]")
_SHEBANG_SH_RE = re.compile(r"^#!.*\b(?:ba|a|da|k|z)?sh\b")
_EXEC_CALL_RE = re.compile(r"^\s*exec\s+\S", re.MULTILINE)
_ROOT_USERS = {"root", "0", "root:root", "0:0"}

# Binaries that fork a worker pool: as PID 1 they also inherit every orphaned
# process in the container and are expected to reap it.
_FORKING_BINARIES = (
    "nginx",
    "httpd",
    "apache2",
    "php-fpm",
    "gunicorn",
    "uwsgi",
    "celery",
    "puma",
    "unicorn",
    "passenger",
    "pm2",
)
# Anything here already is an init (or ships one), so the container has a
# reaper and HF1003 has nothing to say.
_INIT_BINARIES = ("tini", "dumb-init", "catatonit", "s6-svscan", "s6-overlay", "supervisord", "runsvdir")

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


Resolver = Callable[[str, str], str | None]


class HadolintError(RuntimeError):
    """hadolint could not be run, or did not answer in JSON."""


@dataclass(frozen=True)
class Finding:
    """One rule violation, in hadolint's shape — our own rules use it too."""

    code: str
    line: int
    level: str
    message: str


@dataclass(frozen=True)
class Instruction:
    """One logical Dockerfile instruction, continuations already joined."""

    keyword: str  # upper-cased; "" for a comment or a blank line
    start: int  # index of the first physical line
    end: int  # index of the last physical line, inclusive
    text: str  # the instruction as one line, `\` continuations folded in


@dataclass(frozen=True)
class Stage:
    """A build stage: its `FROM` and the base image that stage inherits."""

    image: str
    tag: str | None
    digest: str | None
    alias: str | None
    start: int
    end: int  # last physical line of the stage, inclusive


@dataclass(frozen=True)
class Outcome:
    """What happened to one finding: fixed with a reason, or left alone with one."""

    finding: Finding
    fixed: bool
    detail: str


# A fixer either rewrites the document and says why, or refuses and says why.
@dataclass(frozen=True)
class Fixed:
    """The document was rewritten; `why` becomes the comment above the hunk.

    A fixer that inserts lines of its own places its comment itself, so the
    explanation stays above the whole hunk rather than inside it, and says so
    with `commented`.
    """

    why: str
    commented: bool = False


@dataclass(frozen=True)
class Skipped:
    """The document was left alone; `why` is what the user has to decide."""

    why: str


def parse_ref(ref: str) -> tuple[str, str | None, str | None]:
    """Split an image reference into (name, tag, digest).

    The tag is separated from the name by the last `:` *in the final path
    segment*, so `registry:5000/app` is a host with a port and not a tag.
    """
    name, _, digest = ref.partition("@")
    head, sep, tail = name.rpartition(":")
    if sep and "/" not in tail:
        return head, tail, digest or None
    return name, None, digest or None


def _instructions(lines: Sequence[str]) -> list[Instruction]:
    """Group physical lines into logical instructions."""
    out: list[Instruction] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            out.append(Instruction("", i, i, stripped))
            i += 1
            continue
        start, more = i, True
        parts: list[str] = []
        while i < len(lines) and more:
            body = lines[i].rstrip("\n")
            # A comment *inside* a continuation is removed before the backslash
            # is honoured, so it neither ends the instruction nor joins it.
            if i != start and body.lstrip().startswith("#"):
                i += 1
                continue
            more = body.rstrip().endswith("\\")
            parts.append((body.rstrip()[:-1] if more else body).strip())
            i += 1
        text = " ".join(p for p in parts if p)
        out.append(Instruction(text.split(maxsplit=1)[0].upper(), start, i - 1, text))
    return out


class Doc:
    """The Dockerfile under repair: its lines, and the edits made to them."""

    def __init__(self, text: str, path: Path, resolver: Resolver | None = None) -> None:
        lines = text.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        self.lines = lines
        self.path = path
        self.resolver = resolver
        # Findings are reported against the file as hadolint saw it, and every
        # fix that inserts a line moves everything under it — including the
        # instruction the *next* finding on the same line points at. This maps
        # each original line to where it lives now, so an anchor stays an
        # anchor no matter what has been inserted above it.
        self._moved = list(range(len(lines)))

    @property
    def text(self) -> str:
        """The document as it now stands."""
        return "".join(self.lines)

    def instructions(self) -> list[Instruction]:
        """Re-parse the current lines. Cheap, and never stale after an edit."""
        return _instructions(self.lines)

    def stages(self) -> list[Stage]:
        """Every build stage, with the base image it starts from."""
        froms = [inst for inst in self.instructions() if inst.keyword == "FROM"]
        out: list[Stage] = []
        for pos, inst in enumerate(froms):
            m = _FROM_RE.match(inst.text)
            if not m:
                continue
            image, tag, digest = parse_ref(m.group("ref"))
            end = froms[pos + 1].start - 1 if pos + 1 < len(froms) else len(self.lines) - 1
            out.append(Stage(image, tag, digest, m.group("alias"), inst.start, end))
        return out

    def stage_of(self, index: int) -> Stage | None:
        """The stage the physical line `index` belongs to."""
        return next((s for s in self.stages() if s.start <= index <= s.end), None)

    def instruction_at(self, index: int) -> Instruction | None:
        """The instruction beginning at physical line `index`."""
        return next((inst for inst in self.instructions() if inst.start == index), None)

    def at(self, original: int) -> int:
        """Where line `original` of the file hadolint read lives now, or -1."""
        return self._moved[original] if 0 <= original < len(self._moved) else -1

    def insert(self, index: int, lines: Sequence[str]) -> None:
        """Insert physical lines above `index`."""
        self.lines[index:index] = lines
        self._moved = [m + len(lines) if m >= index else m for m in self._moved]

    def replace(self, inst: Instruction, lines: Sequence[str]) -> None:
        """Replace every physical line of `inst` with `lines`."""
        delta = len(lines) - (inst.end - inst.start + 1)
        self.lines[inst.start : inst.end + 1] = lines
        self._moved = [m + delta if m > inst.end else inst.start if m > inst.start else m for m in self._moved]

    def target(self, finding: "Finding") -> Instruction | None:
        """The instruction a finding points at, wherever it has moved to."""
        index = self.at(finding.line - 1)
        return self.instruction_at(index) if index >= 0 else None


def _wrap(text: str, initial: str, subsequent: str) -> list[str]:
    """Wrap prose for a terminal without ever splitting a flag or a path."""
    return textwrap.wrap(
        " ".join(text.split()),
        width=_COMMENT_WIDTH,
        initial_indent=initial,
        subsequent_indent=subsequent,
        break_on_hyphens=False,
        break_long_words=False,
    )


def comment_for(code: str, why: str) -> list[str]:
    """Wrap `why` into the comment that rides above the change it explains."""
    return [f"{line}\n" for line in _wrap(why, f"{_COMMENT_PREFIX}({code}): ", "# ")]


# --------------------------------------------------------------------------
# Fixers. Each takes the document and one finding, and either rewrites the
# document (returning the sentence that explains the rewrite) or refuses
# (returning the sentence that says what the reader has to decide).
# --------------------------------------------------------------------------


def fix_base_pin(doc: Doc, finding: Finding) -> Fixed | Skipped:
    """DL3006/DL3007: give `FROM` a reference that cannot move under you."""
    index = doc.at(finding.line - 1)
    m = _FROM_RE.match(doc.lines[index]) if index >= 0 else None
    if m is None:
        return Skipped("the reported line is not a plain FROM instruction")
    image, tag, digest = parse_ref(m.group("ref"))
    if digest is not None:
        return Skipped("already pinned to a digest")
    if any(stage.alias == image for stage in doc.stages()):
        return Skipped(f"`{image}` is a stage in this file, not an image")
    pinned, evidence = _resolve_base(doc, image, tag, index)
    if pinned is None:
        return Skipped(
            f"hadofix does not pick versions: nothing else in this file pins `{image}`. "
            f"Write the tag you actually test against, or pass --resolve-digests to pin "
            f"`{image}:{tag or 'latest'}` to the digest it resolves to right now."
        )
    stage = f" AS {m.group('alias')}" if m.group("alias") else ""
    doc.lines[index] = f"{m.group('indent')}FROM {pinned}{stage}\n"
    return Fixed(
        f"A tag is a label, not a version: whoever owns `{image}` can push new bytes over "
        f"`{tag or 'latest'}` tonight and your next build would pull them without a diff. "
        f"Pinned to `{pinned}` — {evidence}."
    )


def _resolve_base(doc: Doc, image: str, tag: str | None, index: int) -> tuple[str | None, str]:
    """Find a pin for `image` from evidence, never from a guess.

    `index` is the FROM being fixed: a stage is not evidence for itself, and
    `:latest` is not a pin no matter which stage it is written on.
    """
    for stage in doc.stages():
        if stage.start == index or stage.image != image:
            continue
        if stage.digest is None and stage.tag in (None, "latest"):
            continue
        ref = f"{stage.image}:{stage.tag}" if stage.tag else stage.image
        return (f"{ref}@{stage.digest}" if stage.digest else ref, "another stage in this file already pins it")
    if doc.resolver is not None:
        digest = doc.resolver(image, tag or "latest")
        if digest:
            ref = f"{image}:{tag}" if tag else image
            return f"{ref}@{digest}", "a digest names the exact bytes, a tag names whatever was pushed last"
    return None, ""


@dataclass(frozen=True)
class Manager:
    """One package manager, as the version-pinning fixer needs to see it."""

    binaries: tuple[str, ...]
    verb: str
    separator: str
    value_flags: frozenset[str]
    how_to_find: str


APT = Manager(
    binaries=("apt-get", "apt"),
    verb="install",
    separator="=",
    value_flags=frozenset({"-t", "--target-release", "-o", "-c", "--config-file"}),
    how_to_find="`apt-cache policy <package>` inside the base image prints the version to write",
)
APK = Manager(
    binaries=("apk",),
    verb="add",
    separator="=",
    value_flags=frozenset({"-t", "--virtual", "-X", "--repository"}),
    how_to_find="`apk policy <package>` inside the base image prints the version to write",
)
PIP = Manager(
    binaries=("pip", "pip3"),
    verb="install",
    separator="==",
    value_flags=frozenset(
        {"-r", "--requirement", "-c", "--constraint", "-i", "--index-url", "--extra-index-url", "-t", "--target"}
    ),
    how_to_find="`pip index versions <package>` prints what is publishable today, and a lock file pins it for good",
)


def _tokens(text: str) -> list[str]:
    """Shell-split an instruction, or give up quietly on unbalanced quotes."""
    try:
        return shlex.split(text)
    except ValueError:
        return []


def _installed_packages(manager: Manager, text: str) -> list[str]:
    """Every package argument of every `<manager> <verb>` in one instruction."""
    tokens = _tokens(text)
    found: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] in manager.binaries and i + 1 < len(tokens) and tokens[i + 1] == manager.verb:
            i = _collect_packages(manager, tokens, i + 2, found)
            continue
        i += 1
    return found


def _collect_packages(manager: Manager, tokens: Sequence[str], start: int, found: list[str]) -> int:
    """Read package arguments until the command ends; return where it ended."""
    i = start
    while i < len(tokens) and tokens[i] not in {"&&", "||", ";", "|", ">", ">>"}:
        token = tokens[i]
        if token in manager.value_flags:
            i += 2
            continue
        # A local path or a URL is not a package name anyone can pin for you.
        if not token.startswith("-") and not token.startswith((".", "/")) and "://" not in token:
            found.append(token)
        i += 1
    return i


def _is_pinned(manager: Manager, token: str) -> bool:
    """Does this package argument already name a version?"""
    if manager is PIP:
        return any(op in token for op in ("==", ">=", "<=", "~=", "!=", "@"))
    return "=" in token


def _known_versions(doc: Doc, manager: Manager) -> dict[str, str]:
    """Versions this Dockerfile already commits to, for the same manager."""
    known: dict[str, str] = {}
    for inst in doc.instructions():
        for token in _installed_packages(manager, inst.text):
            if _is_pinned(manager, token):
                name, _, version = token.partition(manager.separator)
                known.setdefault(name, version)
    if manager is PIP:
        known.update(_requirements_pins(doc))
    return known


def _requirements_pins(doc: Doc) -> dict[str, str]:
    """Pins from a requirements file this Dockerfile copies into the image."""
    pins: dict[str, str] = {}
    for inst in doc.instructions():
        if inst.keyword not in {"COPY", "ADD"} or "--from" in inst.text:
            continue
        for token in _tokens(inst.text)[1:]:
            if not token.endswith(".txt") or token.startswith("-"):
                continue
            candidate = doc.path.parent / token
            if candidate.is_file():
                pins.update(_parse_requirements(_read_text(candidate)))
    return pins


def _parse_requirements(text: str) -> dict[str, str]:
    """`name==version` lines of a requirements file, ignoring everything else."""
    pins: dict[str, str] = {}
    for line in text.splitlines():
        name, sep, version = line.split("#", maxsplit=1)[0].strip().partition("==")
        if sep and version and re.fullmatch(r"[\w.-]+", name):
            pins[name] = version
    return pins


def fix_pin_packages(manager: Manager, doc: Doc, finding: Finding) -> Fixed | Skipped:
    """DL3008/DL3013/DL3018: pin package versions, when the file already knows them."""
    inst = doc.target(finding)
    if inst is None:
        return Skipped("the reported line does not start an instruction")
    unpinned = [p for p in _installed_packages(manager, inst.text) if not _is_pinned(manager, p)]
    known = _known_versions(doc, manager)
    missing = [p for p in unpinned if p not in known]
    if not unpinned:
        return Skipped("no package argument on this line can be pinned")
    if missing:
        names = ", ".join(f"`{p}`" for p in missing)
        return Skipped(f"hadofix does not invent versions: nothing in this file pins {names}. {manager.how_to_find}.")
    for package in unpinned:
        _pin_token(doc, inst, package, f"{package}{manager.separator}{known[package]}")
    return Fixed(
        f"`{manager.binaries[0]} {manager.verb} {unpinned[0]}` installs whatever the index serves the day it runs, "
        f"so the same commit can build two different images. Pinned to the version this repository already "
        f"commits to elsewhere."
    )


def _pin_token(doc: Doc, inst: Instruction, package: str, pinned: str) -> None:
    """Rewrite the first bare occurrence of `package` inside one instruction."""
    pattern = re.compile(rf"(?<![\w./:=-]){re.escape(package)}(?![\w./:=-])")
    for index in range(inst.start, inst.end + 1):
        new, count = pattern.subn(pinned, doc.lines[index], count=1)
        if count:
            doc.lines[index] = new
            return


def fix_nonroot_user(doc: Doc, finding: Finding) -> Fixed | Skipped:
    """DL3002/DL3066/HF1004: leave root behind, without inventing an account."""
    why = (
        f"Root in a container is root on the host kernel: a mounted volume or an escape starts from UID 0. "
        f"{NONROOT_UID} is a UID, not an account — it needs no adduser, and nothing in the image can resolve "
        f"it back to root. Create a real account in an earlier layer if the app needs a home directory."
    )
    index = doc.at(finding.line - 1)
    m = _USER_RE.match(doc.lines[index]) if index >= 0 else None
    if m is not None and m.group("who").lower() in _ROOT_USERS:
        doc.lines[index] = f"{m.group('head')}{NONROOT_UID}\n"
        doc.insert(index, comment_for(finding.code, why))
        return Fixed(why, commented=True)
    if _final_stage_user(doc) is not None:
        return Skipped(
            "the final stage already sets a USER and hadofix will not overrule the one you chose — give that "
            "account a fixed numeric UID of its own if the host has to resolve it"
        )
    doc.insert(_final_command_line(doc), [*comment_for(finding.code, why), f"USER {NONROOT_UID}\n"])
    return Fixed(why, commented=True)


def _final_stage_user(doc: Doc) -> Instruction | None:
    """The USER the final stage ends on, if it sets one at all.

    Only the final stage: a stage does not inherit the USER of the stage
    before it, it inherits the configuration of its own base image.
    """
    stages = doc.stages()
    first = stages[-1].start if stages else 0
    users = [inst for inst in doc.instructions() if inst.keyword == "USER" and inst.start >= first]
    return users[-1] if users else None


def _final_command_line(doc: Doc) -> int:
    """Where a USER has to go: above the last stage's ENTRYPOINT/CMD block."""
    stages = doc.stages()
    first = stages[-1].start if stages else 0
    commands = [
        inst.start for inst in doc.instructions() if inst.keyword in {"ENTRYPOINT", "CMD"} and inst.start >= first
    ]
    return min(commands) if commands else len(doc.lines)


def fix_pipefail(doc: Doc, finding: Finding) -> Fixed | Skipped:
    """DL4006: make a pipeline in a RUN fail where the pipe failed."""
    inst = doc.target(finding)
    if inst is None or inst.keyword != "RUN":
        return Skipped("the reported line does not start a RUN instruction")
    shell = _shell_for(doc, inst.start)
    why = (
        f"A pipeline's exit status is the last command's, so `curl … | tar x` succeeds when curl serves a 404 "
        f"and tar unpacks the error page. pipefail fails the RUN where the pipe failed, and SHELL is how you ask "
        f"for it — here with {shell}, the shell this stage's base image has."
    )
    doc.insert(inst.start, [*comment_for(finding.code, why), f'SHELL ["{shell}", "-o", "pipefail", "-c"]\n'])
    return Fixed(why, commented=True)


def _shell_for(doc: Doc, index: int) -> str:
    """`/bin/ash` on a busybox userland, `/bin/bash` otherwise."""
    stage = doc.stage_of(index)
    base = f"{stage.image}:{stage.tag or ''}" if stage else ""
    return "/bin/ash" if any(flavour in base for flavour in ("alpine", "busybox")) else "/bin/bash"


def fix_apt_lists(doc: Doc, finding: Finding) -> Fixed | Skipped:
    """DL3009: delete the apt lists in the layer that created them."""
    inst = doc.target(finding)
    if inst is None or inst.keyword != "RUN":
        return Skipped("the reported line does not start a RUN instruction")
    cleanup = "rm -rf /var/lib/apt/lists/*"
    if cleanup in inst.text:
        return Skipped("this RUN already cleans the apt lists")
    tail = doc.lines[inst.end].rstrip("\n").rstrip()
    if inst.end > inst.start:
        indent = doc.lines[inst.end][: len(doc.lines[inst.end]) - len(doc.lines[inst.end].lstrip())]
        doc.lines[inst.end] = f"{tail} \\\n"
        doc.insert(inst.end + 1, [f"{indent}&& {cleanup}\n"])
    else:
        doc.lines[inst.end] = f"{tail} && {cleanup}\n"
    return Fixed(
        "The cleanup has to run in the same RUN as the install: a later layer can hide the lists but every "
        "layer is still in the image, still pushed, still pullable. Same layer, or it is only hidden."
    )


def fix_no_install_recommends(doc: Doc, finding: Finding) -> Fixed | Skipped:
    """DL3015: install what the Dockerfile names, and nothing else."""
    inst = doc.target(finding)
    if inst is None or inst.keyword != "RUN":
        return Skipped("the reported line does not start a RUN instruction")
    for index in range(inst.start, inst.end + 1):
        new, count = _APT_INSTALL_RE.subn(r"\1 --no-install-recommends", doc.lines[index], count=1)
        if count:
            doc.lines[index] = new
            return Fixed(
                "apt pulls every `Recommends` of every package by default — software nobody in this Dockerfile "
                "asked for, shipped in the image and reported by every scanner. The flag installs what is named "
                "here and stops."
            )
    return Skipped("could not find the apt-get install on the reported line")


def fix_exec_form(doc: Doc, finding: Finding) -> Fixed | Skipped:
    """DL3025/HF1001: make the app PID 1 instead of the shell that starts it."""
    inst = doc.target(finding)
    m = _ENTRYPOINT_OR_CMD_RE.match(inst.text) if inst else None
    if inst is None or m is None:
        return Skipped("the reported line does not start an ENTRYPOINT or CMD")
    args = m.group("args").strip()
    if args.startswith("["):
        return Skipped("already in exec form")
    if _EXEC_UNSAFE_RE.search(args):
        return Skipped(
            "this command needs a shell (it uses a pipe, a variable or a glob), so exec form would change what "
            'runs. Say it deliberately if you mean it: CMD ["sh", "-c", "…"] — and know that PID 1 is then sh.'
        )
    argv = _tokens(args)
    if not argv:
        return Skipped("could not split this command into arguments")
    keyword = m.group("keyword").upper()
    indent = doc.lines[inst.start][: len(doc.lines[inst.start]) - len(doc.lines[inst.start].lstrip())]
    doc.replace(inst, [f"{indent}{keyword} {json.dumps(argv)}\n"])
    return Fixed(
        f"Shell form runs `/bin/sh -c '{args}'`, so PID 1 is sh. `docker stop` sends SIGTERM to PID 1, sh does "
        f"not forward it, and ten seconds later the container is SIGKILLed mid-request. Exec form makes "
        f"`{argv[0]}` PID 1 and puts the signal where the shutdown handler is."
    )


Fixer = Callable[[Doc, Finding], Fixed | Skipped]

FIXERS: dict[str, Fixer] = {
    "DL3006": fix_base_pin,
    "DL3007": fix_base_pin,
    "DL3008": partial(fix_pin_packages, APT),
    "DL3013": partial(fix_pin_packages, PIP),
    "DL3018": partial(fix_pin_packages, APK),
    "DL3002": fix_nonroot_user,
    # DL3066 asks for a numeric user-id, which is what fix_nonroot_user
    # writes: on a `USER root` line the two rules are one defect and get
    # one fix.
    "DL3066": fix_nonroot_user,
    "DL4006": fix_pipefail,
    "DL3009": fix_apt_lists,
    "DL3015": fix_no_install_recommends,
    "DL3025": fix_exec_form,
    HF_SHELL_FORM: fix_exec_form,
    HF_ROOT_DEFAULT: fix_nonroot_user,
}


# --------------------------------------------------------------------------
# Rules of our own. hadolint has no opinion on any of these; they are reported
# in its shape so one list covers every finding.
# --------------------------------------------------------------------------


def own_findings(doc: Doc) -> list[Finding]:
    """The HF#### rules: PID 1, signals, and who reaps the orphans."""
    stages = doc.stages()
    if not stages:
        return []
    final = stages[-1]
    commands = [
        (inst, m)
        for inst in doc.instructions()
        if final.start <= inst.start <= final.end and (m := _ENTRYPOINT_OR_CMD_RE.match(inst.text))
    ]
    out: list[Finding] = []
    for inst, m in commands:
        if not m.group("args").strip().startswith("["):
            out.append(
                Finding(
                    HF_SHELL_FORM,
                    inst.start + 1,
                    "warning",
                    f"Shell-form {m.group('keyword').upper()} makes /bin/sh PID 1, so `docker stop` signals the "
                    f"shell and never reaches the app. Use exec form.",
                )
            )
    out.extend(_entrypoint_script_finding(doc, commands))
    out.extend(_init_finding(doc, commands))
    out.extend(_root_default_finding(doc, commands))
    return out


def _root_default_finding(doc: Doc, commands: Sequence[tuple[Instruction, re.Match[str]]]) -> list[Finding]:
    """HF1004: the final stage never leaves root, so every process in it is UID 0."""
    if _final_stage_user(doc) is not None:
        return []
    stages = doc.stages()
    line = min((inst.start for inst, _m in commands), default=stages[-1].start) + 1
    return [
        Finding(
            HF_ROOT_DEFAULT,
            line,
            "warning",
            "This stage never sets a USER, so everything in the image runs as root — and root in a container "
            "is UID 0 on the host kernel.",
        )
    ]


def _argv_of(match: re.Match[str]) -> list[str]:
    """The arguments of an ENTRYPOINT/CMD, in either form."""
    args = match.group("args").strip()
    if args.startswith("["):
        try:
            parsed: object = json.loads(args)
        except json.JSONDecodeError:
            return []
        return [str(item) for item in cast("list[object]", parsed)] if isinstance(parsed, list) else []
    return _tokens(args)


def _entrypoint_script_finding(doc: Doc, commands: Sequence[tuple[Instruction, re.Match[str]]]) -> list[Finding]:
    """HF1002: an entrypoint script that never hands PID 1 over with `exec`."""
    for inst, m in commands:
        if m.group("keyword").upper() != "ENTRYPOINT":
            continue
        argv = _argv_of(m)
        if not argv:
            continue
        script = _script_in_context(doc, argv[0])
        if script is None:
            continue
        text = _read_text(script)
        if not ((text.startswith("#!") and _SHEBANG_SH_RE.match(text)) or argv[0].endswith(".sh")):
            continue
        if _EXEC_CALL_RE.search(text):
            continue
        return [
            Finding(
                HF_NO_EXEC,
                inst.start + 1,
                "warning",
                f"`{script.name}` never calls `exec`, so the command it starts is a child of the script: PID 1 "
                f"stays /bin/sh, SIGTERM stops the wrapper and the app is killed on the timeout. End the script "
                f'with `exec "$@"` (or `exec <command>`).',
            )
        ]
    return []


def _init_finding(doc: Doc, commands: Sequence[tuple[Instruction, re.Match[str]]]) -> list[Finding]:
    """HF1003: a process that forks workers, with nothing in the image to reap them."""
    joined = " ".join(" ".join(_argv_of(m)) for _inst, m in commands)
    if not joined or any(re.search(rf"\b{re.escape(init)}\b", joined) for init in _INIT_BINARIES):
        return []
    forking = next((b for b in _FORKING_BINARIES if re.search(rf"\b{re.escape(b)}\b", joined)), None)
    if forking is None:
        return []
    line = max(inst.start for inst, _m in commands) + 1
    return [
        Finding(
            HF_NO_INIT,
            line,
            "info",
            f"`{forking}` forks worker processes, and as PID 1 it also inherits every orphan in the container "
            f"and is expected to reap it — PID 1 gets no default signal handlers either. Put an init in front "
            f"(tini, dumb-init) or run the container with `docker run --init`.",
        )
    ]


def _script_in_context(doc: Doc, target: str) -> Path | None:
    """Map a path inside the image back to the file the build context copies in."""
    for inst in doc.instructions():
        if inst.keyword not in {"COPY", "ADD"} or "--from" in inst.text:
            continue
        args = [t for t in _tokens(inst.text)[1:] if not t.startswith("--")]
        if len(args) < 2:  # noqa: PLR2004 — a COPY is at least one source and a destination
            continue
        *sources, destination = args
        for source in sources:
            candidate = _map_into_context(source, destination, target)
            if candidate is not None and (doc.path.parent / candidate).is_file():
                return doc.path.parent / candidate
    return None


def _map_into_context(source: str, destination: str, target: str) -> str | None:
    """Where `target` came from, given one `COPY <source> <destination>`."""
    if destination == target:
        return source
    prefix = destination if destination.endswith("/") else f"{destination}/"
    if not target.startswith(prefix):
        return None
    remainder = target[len(prefix) :]
    return source if Path(source).name == remainder else f"{source}/{remainder}"


def _read_text(path: Path) -> str:
    """Read a file from the build context; an unreadable one simply says nothing."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


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
        done = subprocess.run(  # noqa: S603 — a resolved path and a fixed argument list, no shell
            [resolved, "--format", "json", str(dockerfile)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as err:
        msg = f"{binary}: {err.strerror}"
        raise HadolintError(msg) from err
    # hadolint exits 1 when it has findings, which is the normal case here.
    if done.returncode > EX_FINDINGS:
        msg = f"{binary} exited {done.returncode}: {done.stderr.strip() or done.stdout.strip()}"
        raise HadolintError(msg)
    return done.stdout


def parse_findings(payload: str) -> list[Finding]:
    """Read hadolint's JSON. Its shape is the contract between the two tools."""
    try:
        decoded: object = json.loads(payload.strip() or "[]")
    except json.JSONDecodeError as err:
        msg = f"could not read the hadolint JSON: {err}"
        raise HadolintError(msg) from err
    if not isinstance(decoded, list):
        msg = "hadolint JSON should be a list of findings"
        raise HadolintError(msg)
    out: list[Finding] = []
    # json.loads answers `Any`; the casts say what this tool is willing to read
    # and keep the checker honest about everything downstream.
    for item in cast("list[object]", decoded):
        if not isinstance(item, dict):
            continue
        entry = cast("dict[str, object]", item)
        line = entry.get("line", 1)
        out.append(
            Finding(
                code=str(entry.get("code", "?")),
                line=line if isinstance(line, int) else 1,
                level=str(entry.get("level", "warning")),
                message=str(entry.get("message", "")),
            )
        )
    return out


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
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as resp:  # noqa: S310 — as above
        if digest_header:
            return resp.headers.get("Docker-Content-Digest")
        return resp.read().decode()


# --------------------------------------------------------------------------
# Driver.
# --------------------------------------------------------------------------


def fix(doc: Doc, findings: Sequence[Finding]) -> list[Outcome]:
    """Apply every fixable finding, bottom-up, and account for all of them.

    Bottom-up because a fix inserts its explanation above the line it fixes:
    working from the end of the file means every line number still points at
    the instruction hadolint reported it on.
    """
    ordered = sorted(findings, key=lambda f: (f.line, f.code))
    outcomes: dict[Finding, Outcome] = {}
    applied: dict[tuple[int, str], str] = {}
    for finding in reversed(ordered):
        fixer = FIXERS.get(finding.code)
        if fixer is None:
            outcomes[finding] = Outcome(finding, False, "")
            continue
        # Two rules can describe the same defect (DL3025 and HF1001 do). The
        # fix happens once; both findings are answered by it.
        key = (finding.line, getattr(fixer, "func", fixer).__name__)
        if key in applied:
            outcomes[finding] = Outcome(finding, True, applied[key])
            continue
        result = fixer(doc, finding)
        if isinstance(result, Skipped):
            outcomes[finding] = Outcome(finding, False, result.why)
            continue
        # A fixer that inserted lines of its own has already placed the
        # comment above them; everything else gets it above the instruction it
        # just rewrote, wherever earlier fixes have moved that to.
        if not result.commented:
            doc.insert(doc.at(finding.line - 1), comment_for(finding.code, result.why))
        applied[key] = result.why
        outcomes[finding] = Outcome(finding, True, result.why)
    return [outcomes[f] for f in ordered]


def _plural(count: int) -> str:
    """`1 finding`, `2 findings` — the report is read by people."""
    return f"{count} finding" if count == 1 else f"{count} findings"


def render_report(path: Path, outcomes: Sequence[Outcome], wrote: bool, changed: bool) -> str:
    """The human half of the output: what was fixed, and what is left."""
    fixed = [o for o in outcomes if o.fixed]
    left = [o for o in outcomes if not o.fixed]
    out: list[str] = []
    if fixed:
        codes = ", ".join(sorted({o.finding.code for o in fixed}))
        out.append(f"hadofix: fixed {_plural(len(fixed))} in {path}: {codes}")
    if left:
        out.append(f"hadofix: {_plural(len(left))} left for you:")
        said: set[tuple[int, str]] = set()
        for outcome in sorted(left, key=lambda o: (o.finding.line, o.finding.code)):
            f = outcome.finding
            out.append(f"  {path}:{f.line} {f.level} {f.code}")
            out.extend(_wrap(f.message, " " * 6, " " * 6))
            # Two rules can refuse for the same reason on the same line (DL3025
            # and HF1001 do): both are worth listing, the reason once.
            if outcome.detail and (f.line, outcome.detail) not in said:
                said.add((f.line, outcome.detail))
                out.extend(_wrap(outcome.detail, "      \u2192 ", " " * 8))
    if not outcomes:
        out.append(f"hadofix: hadolint found nothing to fix in {path}")
    if changed:
        out.append(f"hadofix: wrote {path}" if wrote else "hadofix: nothing written — re-run with --write to apply")
    return "".join(f"{line}\n" for line in out)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="hadofix",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("dockerfile")
    parser.add_argument("--write", action="store_true", help="apply the diff in place")
    parser.add_argument(
        "--from-json",
        metavar="PATH",
        help="read hadolint --format json from PATH (`-` for stdin) instead of running hadolint",
    )
    parser.add_argument("--hadolint", default="hadolint", metavar="BIN", help="hadolint binary to run")
    parser.add_argument(
        "--resolve-digests",
        action="store_true",
        help="let DL3006/DL3007 pin a base image to a Docker Hub digest (needs network)",
    )
    return parser


def _findings_payload(args: argparse.Namespace, path: Path) -> str:
    """hadolint's JSON, from stdin, from a file, or from hadolint itself."""
    source = cast("str | None", args.from_json)
    if source is None:
        return run_hadolint(cast("str", args.hadolint), path)
    if source == "-":
        return sys.stdin.read()
    try:
        return Path(source).read_text()
    except OSError as err:
        msg = f"{source}: {err.strerror}"
        raise HadolintError(msg) from err


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: lint, fix what is mechanical, report the rest."""
    args = build_parser().parse_args(argv)
    path = Path(cast("str", args.dockerfile))
    try:
        original = path.read_text()
    except OSError as err:
        sys.stderr.write(f"hadofix: {path}: {err.strerror}\n")
        return _READ_FAILURE_CODES.get(type(err), EX_IOERR)
    try:
        findings = parse_findings(_findings_payload(args, path))
    except HadolintError as err:
        sys.stderr.write(f"hadofix: {err}\n")
        return EX_UNAVAILABLE

    doc = Doc(original, path, resolver=resolve_digest if args.resolve_digests else None)
    outcomes = fix(doc, [*findings, *own_findings(doc)])
    changed = doc.text != original
    if changed:
        sys.stdout.writelines(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                doc.text.splitlines(keepends=True),
                fromfile=str(path),
                tofile=f"{path} (hadofix)",
            )
        )
    if changed and args.write:
        path.write_text(doc.text)
    sys.stderr.write(render_report(path, outcomes, wrote=bool(args.write), changed=changed))
    # A CI gate wants one question answered: is this Dockerfile clean now?
    # Anything hadofix refused to fix says no, and so does a diff nobody applied.
    unresolved = any(not o.fixed for o in outcomes) or (changed and not args.write)
    return EX_FINDINGS if unresolved else EX_OK


if __name__ == "__main__":
    sys.exit(main())
