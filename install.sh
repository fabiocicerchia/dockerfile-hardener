#!/usr/bin/env bash
set -euo pipefail
# One-line installer for dockerfile-hardener
# Usage: curl -fsSL https://raw.githubusercontent.com/fabiocicerchia/dockerfile-hardener/main/install.sh | bash

if command -v pipx &>/dev/null; then
  pipx install git+https://github.com/fabiocicerchia/dockerfile-hardener
else
  pip install --user git+https://github.com/fabiocicerchia/dockerfile-hardener
fi
echo "dockerfile-hardener installed. Run: dockerfile-hardener --help"
