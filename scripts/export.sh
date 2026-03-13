#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.env"

docker run --rm -it \
  -v "$(pwd):/workspace" \
  -v opencode-data:/root/.local/share/opencode \
  mohammedmhs/opencode-fellow \
  python3 /workspace/scripts/export_sessions.py
