"""docs/ makes promises about the CLI and the module; these hold it to them.

A flag renamed in `build_parser`, an exit code renumbered, or a component
renamed in `hadofix.py` should fail here instead of leaving the docs wrong.
"""

import re
import shlex
from pathlib import Path

import pytest

import hadofix as hadofix_module
from hadofix import EX_FINDINGS, EX_IOERR, EX_NOINPUT, EX_NOPERM, EX_UNAVAILABLE, build_parser

DOCS = Path(__file__).parent.parent / "docs"
GETTING_STARTED = (DOCS / "getting-started.md").read_text()
ARCHITECTURE = (DOCS / "architecture.md").read_text()
COMPONENTS = (
    "Finding",
    "Doc",
    "FIXERS",
    "Fixed",
    "Skipped",
    "Outcome",
    "own_findings",
    "fix",
    "run_hadolint",
    "parse_findings",
    "resolve_digest",
    "render_report",
    "main",
)


def documented_commands() -> list[list[str]]:
    """Every `hadofix ...` invocation in a getting-started code block, comments and pipes dropped."""
    commands = []
    for block in re.findall(r"```(?:sh|yaml)\n(.*?)```", GETTING_STARTED, re.S):
        for line in block.splitlines():
            command = line.split("#", 1)[0].split("|")[-1]
            words = shlex.split(command.removeprefix("- run:"))
            if words and words[0] == "hadofix":
                commands.append(words[1:])
    return commands


def test_getting_started_documents_commands() -> None:
    assert len(documented_commands()) >= 5


@pytest.mark.parametrize("argv", documented_commands(), ids=" ".join)
def test_every_documented_command_parses(argv: list[str]) -> None:
    args = build_parser().parse_args(argv)
    assert args.dockerfile == "Dockerfile"


def test_the_documented_exit_codes_are_the_real_ones() -> None:
    assert '1 means "this Dockerfile still has findings"' in ARCHITECTURE
    assert EX_FINDINGS == 1
    assert "(66/69/74/77)" in ARCHITECTURE
    assert (EX_NOINPUT, EX_UNAVAILABLE, EX_IOERR, EX_NOPERM) == (66, 69, 74, 77)


@pytest.mark.parametrize("name", COMPONENTS)
def test_every_documented_component_exists(name: str) -> None:
    assert f"`{name}" in ARCHITECTURE
    assert hasattr(hadofix_module, name)
