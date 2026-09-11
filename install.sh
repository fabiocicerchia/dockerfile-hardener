#!/usr/bin/env bash
set -euo pipefail
# One-line installer for hadofix
# Usage: curl -fsSL https://raw.githubusercontent.com/fabiocicerchia/hadofix/main/install.sh | bash

if command -v pipx &>/dev/null; then
  pipx install git+https://github.com/fabiocicerchia/hadofix
else
  pip install --user git+https://github.com/fabiocicerchia/hadofix
fi
echo "hadofix installed. Run: hadofix --help"
