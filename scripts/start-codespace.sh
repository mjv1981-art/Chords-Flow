#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache
bash scripts/prepare-codespace.sh
if .venv/bin/python - <<'PY'
import urllib.request, json
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2) as response:
        assert json.load(response).get('status') == 'ok'
    with urllib.request.urlopen('http://127.0.0.1:8000/', timeout=2) as response:
        assert 'BayanFlow' in response.read().decode()
except Exception:
    raise SystemExit(1)
PY
then
  echo 'BayanFlow is already running on port 8000.'
  exit 0
fi
nohup .venv/bin/python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 1 >.cache/codespace-server.log 2>&1 &
echo "$!" >.cache/codespace-server.pid
.venv/bin/python - <<'PY'
import json, time, urllib.request
for _ in range(40):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2) as response:
            data = json.load(response)
            assert data['status'] == 'ok'
            print('BayanFlow is running. Open port 8000 from the Codespaces Ports tab.')
            if not data['transcription_configured']:
                print('Add GEMINI_API_KEY as a GitHub Codespaces secret for this repository, then restart the Codespace.')
            break
    except Exception:
        time.sleep(.25)
else:
    print(open('.cache/codespace-server.log').read()[-3000:])
    raise SystemExit('BayanFlow did not start. The startup error is shown above.')
PY
