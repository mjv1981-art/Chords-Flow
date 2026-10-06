# BayanFlow

Paste one YouTube video link, extract a simplified melody and chords from its **actual audio**, then practice with the existing accordion player. The imported Base44 player keeps its sheet music, keyboard styling, playback scheduler, tempo/seek controls and reed synthesis. PDF, notation upload, title search and Base44 authentication are removed. Saved songs live in this browser, not in Base44.

The right-hand panel uses **B-griff**, viewed from the front with the bellows to its left: inner row 3 = C/E♭/F♯/A, middle row 2 = C♯/E/G/B♭, outer row 1 = D/F/A♭/B. The existing three visible columns are retained. The left hand is Stradella.

## Test in your browser

Use the GitHub Codespaces setup in [WEB_PREVIEW.md](WEB_PREVIEW.md). It starts the complete player and transcription backend in a browser-accessible environment; no Windows installation is needed. GitHub Pages alone cannot run the backend. A Codespace must be created in your GitHub account before a preview URL exists. The Docker/Render configuration also supports a public web deployment.

## Run locally

Prerequisites: Node 22+ (Node 24 tested), Python 3.12, FFmpeg and ffprobe.

```sh
bash scripts/setup.sh
cp .env.example .env
# Edit .env locally to set GEMINI_API_KEY.
npm run dev:all
```

Vite runs on port 5173 and proxies `/api` to FastAPI on port 8000. `dev:all` starts both and stops the backend when it exits. To run separately:

```sh
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
npm run dev
```

For a built application, run `npm run build`, then the same Uvicorn command. FastAPI serves `dist` and `/api` together. Restart Uvicorn after building so it discovers `dist`. Public browser previews are supported. The optional BAYANFLOW_ACCESS_PASSWORD enables browser Basic authentication with username bayanflow; leave it unset for public access. Jobs still live in process memory, so use one server worker.

### Windows / PowerShell

Install Node LTS, Python 3.12 and FFmpeg. Windows Package Manager can install them:

```powershell
winget install --exact --id OpenJS.NodeJS.LTS
winget install --exact --id Python.Python.3.12
winget install --exact --id Gyan.FFmpeg
```

Close and reopen PowerShell after installation so PATH is refreshed. Extract the current **BayanFlow-test.zip**, open its `BayanFlow` folder, and open PowerShell there. The original Base44 ZIP does not contain these backend changes.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
npm ci
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

In Notepad, fill `GEMINI_API_KEY=` with your own key and save. Keep `GEMINI_MODEL=gemini-3.8-flash`. The key configured in Codex's cloud environment is not automatically available on your Windows computer. `.env` is ignored by Git.

Start the backend in that PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Open a second PowerShell window in the same folder and run:

```powershell
npm run dev
```

Open the local address printed by Vite **on that Windows computer**. Paste `https://www.youtube.com/watch?v=rsotlzr9wNw`, click **Получить мелодию и аккорды**, wait for processing, then press Play. Check both keyboard highlights and toggle **Am**; switching stops playback, so press Play again. A song uses one metadata request and approximately one Gemini request for each 30 seconds. Leave both PowerShell windows open; Ctrl+C stops each service.

If PowerShell blocks `npm.ps1`, use `npm.cmd ci` and `npm.cmd run dev` instead; changing the execution policy is unnecessary. If `ffmpeg` or `ffprobe` is not found, finish installing FFmpeg and reopen the terminals. If Gemini cannot access the video, the app reports that error rather than returning invented music.

## Configure transcription

Set **GEMINI_API_KEY** securely in cloud environment settings, or in the ignored local `.env`. Never put it in a `VITE_` variable, source code, or a browser request. A paid chat subscription is not an API key. The server uses Gemini's `generateContent` endpoint, default `GEMINI_MODEL=gemini-3.8-flash`, with **native YouTube URL input**. Gemini accesses the video's media; the app no longer downloads audio from YouTube. Text models with web search can find existing chord charts, but a chord chart alone does not contain the timed melody needed by this player.

The backend needs outbound access to `generativelanguage.googleapis.com`. It sends only canonical YouTube video URLs to Gemini using `fileData.fileUri`. Public, non-live videos up to 10 minutes are supported. A first request obtains video metadata and duration; subsequent requests use `videoMetadata.startOffset/endOffset` for 30-second clips. Gemini returns timed MIDI melody events and simple harmony. The server validates ranges, monophony, completion and harmony coverage, then converts seconds to a half-beat practice grid. The first musical segment supplies global key, tempo and meter. The existing player builds a simple bass–chord accompaniment. Silent segments produce no accompaniment. There is no fallback melody invented from a title. FFmpeg is still included in the environment for audio diagnostics, but transcription jobs do not require it.

The **Am** toggle derives both hands from the original arrangement every time. Minor songs are transposed chromatically to A minor, preserving rhythm and raised leading tones. Major songs need a mode change: the toggle explicitly labels a simple adaptation to A natural minor, lowering the third, sixth and seventh and adapting diatonic chords. Dominant sevenths are retained. This is an adaptation, not an exact transposition of a major melody.

Transcription is approximate and not a specialist note-perfect music transcription model. Dense metal mixes and vocal/instrument overlap need musical checking. Each song makes one metadata request plus approximately one Gemini request per 30 seconds of audio and consumes API quota. Errors (network, key, quota, incomplete notation, unavailable YouTube video) remain visible; the app does not show a successful result without a valid score.

## Verify

```sh
npm run build
npm run lint
npm run typecheck
npm test
.venv/bin/python -m pytest -q
# With dev:all running and Chromium installed:
CHROMIUM_PATH=/usr/bin/chromium npm run test:browser
```

Browser tests use controlled API fixtures, verify synthesized audio scheduling, both keyboard highlights, Am/reset/seek and browser-local saving. Server tests exercise URL restrictions, native YouTube clip offsets, metadata limits, API audio payloads for diagnostics, timing validation and async job outcomes with a stubbed provider. These do **not** establish musical recognition accuracy.

A live native-YouTube request for `https://www.youtube.com/watch?v=TU64x42AFB8` succeeded and returned a description of its music. The metadata request also returned a title and duration. Two successive 30-second clips returned 80 melody events and 27 chord changes; the assembled score passed timing and harmony validation, including the second clip's relative timestamps. Musical correctness has not been checked by listening. This avoids the yt-dlp download failure seen in Codespaces. Earlier testing with a generated eight-note audio melody returned incorrect pitches and key: musical accuracy remains approximate and needs listening checks. Direct YouTube input does not guarantee accurate notes or access to every video. The current build, lint, typecheck, 6 music tests and 36 server/setup tests passed; the startup/restart helper served the new backend and built player.

Each cloud task is already isolated. Use the existing checkout; do not create a Git worktree unless explicitly requested.
