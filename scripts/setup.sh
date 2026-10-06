#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for tool in python3 node npm ffmpeg ffprobe; do
  command -v "$tool" >/dev/null || { echo "Missing prerequisite: $tool" >&2; exit 1; }
done
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir "$PWD/.cache/pip" -r server/requirements.txt
npm ci --cache "$PWD/.cache/npm" --no-audit --no-fund
