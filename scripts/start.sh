#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.env"

if [ -z "$LITELLM_API_KEY" ]; then
  echo "Error: Update your API key in scripts/.env first."
  exit 1
fi

docker run --rm -it \
  -e LITELLM_API_KEY="$LITELLM_API_KEY" \
  -v "$(pwd):/workspace" \
  -v opencode-data:/root/.local/share/opencode \
  mohammedmhs/opencode-fellow
