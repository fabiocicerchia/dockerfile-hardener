#!/usr/bin/env python3
"""Regenerate the golden fixtures: `make golden`, or run this file.

For every case directory it runs the real hadolint over the case's Dockerfile
and stores the JSON, then lets the test suite write the expected diff and
report from that JSON. Both halves are checked in, so the suite itself never
needs hadolint installed.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

GOLDEN = Path(__file__).parent
CONFIG = GOLDEN / "hadolint.yaml"


def lint(case: Path) -> str:
    """hadolint's JSON for one case, with the path it was given normalised out."""
    hadolint = shutil.which("hadolint")
    if hadolint is None:
        raise SystemExit("hadolint is not on PATH: https://github.com/hadolint/hadolint#install")
    extra = (case / "hadolint.args").read_text().split() if (case / "hadolint.args").is_file() else []
    done = subprocess.run(  # noqa: S603 — a resolved path and a fixed argument list, no shell
        [hadolint, "--config", str(CONFIG), "--format", "json", *extra, str(case / "Dockerfile")],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode > 1:
        raise SystemExit(f"hadolint failed on {case.name}: {done.stderr.strip()}")
    findings = json.loads(done.stdout or "[]")
    for finding in findings:
        finding["file"] = "Dockerfile"
    return json.dumps(findings, indent=2) + "\n"


def main() -> int:
    """Rewrite every `hadolint.json`, then hand over to the suite."""
    for case in sorted(path for path in GOLDEN.iterdir() if path.is_dir()):
        (case / "hadolint.json").write_text(lint(case))
        sys.stdout.write(f"regenerated {case.name}\n")
    sys.stdout.write("now run: HADOFIX_UPDATE_GOLDEN=1 pytest -q\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
