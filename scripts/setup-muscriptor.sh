#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache
exec 8>.cache/muscriptor-setup.lock
flock 8
runtime_hash=$(sha256sum server/requirements-muscriptor.txt scripts/setup-muscriptor.sh | sha256sum | cut -d ' ' -f 1)
saved_hash=$(cat .cache/muscriptor-setup.sha256 2>/dev/null || true)
if [ "$runtime_hash" = "$saved_hash" ] && [ -x .venv-muscriptor/bin/python ] && .venv-muscriptor/bin/python -c 'from muscriptor.transcription_model import TranscriptionModel' >/dev/null 2>&1; then
  exit 0
fi
echo 'Installing the isolated CPU MuScriptor runtime…'
python3 -m venv .venv-muscriptor
.venv-muscriptor/bin/python -m pip install --cache-dir "$PWD/.cache/pip-muscriptor" \
  'torch==2.10.0+cpu' 'torchaudio==2.10.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv-muscriptor/bin/python -m pip install --cache-dir "$PWD/.cache/pip-muscriptor" -r server/requirements-muscriptor.txt
.venv-muscriptor/bin/python -m pip check
.venv-muscriptor/bin/python -c 'from muscriptor.transcription_model import TranscriptionModel'
printf '%s\n' "$runtime_hash" >.cache/muscriptor-setup.sha256
echo 'MuScriptor runtime installed. Model weights download on the first transcription with HF_TOKEN.'
