#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache

# Manual startup can overlap dev-container setup. Only one installer may run.
exec 9>.cache/codespace-setup.lock
flock 9

for tool in python3 node npm; do
  if ! command -v "$tool" >/dev/null; then
    echo "Missing $tool. Press F1 in Codespaces, select 'Codespaces: Rebuild Container', and wait for setup to finish." >&2
    exit 1
  fi
done

if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null || ! python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then
  if [ "${CODESPACES:-}" != "true" ]; then
    echo 'Install FFmpeg and Python venv support before starting the preview.' >&2
    exit 1
  fi
  echo 'Installing the browser preview prerequisites…'
  sudo -n apt-get update
  sudo -n apt-get install -y ffmpeg python3-venv
fi

setup_hash=$(sha256sum server/requirements.txt package-lock.json scripts/setup.sh | sha256sum | cut -d ' ' -f 1)
saved_setup=$(cat .cache/codespace-setup.sha256 2>/dev/null || true)
if [ "$setup_hash" != "$saved_setup" ] || [ ! -x .venv/bin/python ] || [ ! -x node_modules/.bin/vite ] || ! .venv/bin/python -c 'import fastapi, uvicorn, httpx, yt_dlp, dotenv' >/dev/null 2>&1; then
  echo 'Preparing BayanFlow dependencies. First startup can take several minutes…'
  bash scripts/setup.sh
  printf '%s\n' "$setup_hash" >.cache/codespace-setup.sha256
fi

build_hash=$({ find src -type f -print0 | sort -z | xargs -0 sha256sum; sha256sum package-lock.json index.html vite.config.js postcss.config.js tailwind.config.js; } | sha256sum | cut -d ' ' -f 1)
saved_build=$(cat .cache/codespace-build.sha256 2>/dev/null || true)
if [ "$build_hash" != "$saved_build" ] || [ ! -f dist/index.html ]; then
  echo 'Building the BayanFlow player…'
  npm run build
  printf '%s\n' "$build_hash" >.cache/codespace-build.sha256
fi
