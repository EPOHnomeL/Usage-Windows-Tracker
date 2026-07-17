#!/usr/bin/env bash
# One-time setup on macOS: create the venv and install dependencies.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt -r requirements-macos.txt

chmod +x start-tracker.command install-startup-macos.sh 2>/dev/null || true

echo
echo "Setup complete."
echo "Start it:            ./start-tracker.command   (or double-click it in Finder)"
echo "Start at login:      ./install-startup-macos.sh"
