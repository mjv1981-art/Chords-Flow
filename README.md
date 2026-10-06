# BayanFlow

Paste a YouTube link, confirm the song, and play a simple arrangement from an existing MIDI score. The library currently contains **Nightwish — Sleeping Sun** and **Nightwish — Come Cover Me**. Source links and attribution are shown before opening the arrangement. The selected video's key and tempo may differ from the library version.

The imported Base44 player retains its sheet music, left/right keyboard styling, audio synthesis, playback controls and **Am** toggle. The right hand uses **B-griff**, viewed from the front with the bellows to its left: inner row 3 = C/E♭/F♯/A, middle row 2 = C♯/E/G/B♭, outer row 1 = D/F/A♭/B. The left hand is Stradella. Saved arrangements stay in this browser.

## Browser preview

Follow [WEB_PREVIEW.md](WEB_PREVIEW.md) for GitHub Codespaces. The complete web app runs on port 8000. No AI API key is needed. The old audio-transcription API is disabled and returns HTTP 410.

1. Paste a YouTube link and click **Определить песню**.
2. The server reads the video title through YouTube oEmbed. If metadata is unavailable, enter the song and artist on the same screen and click **Найти аранжировку**.
3. Confirm the matching song with **Да, открыть …**. The ready arrangement opens immediately without audio analysis or model processing.
4. Press Play, check both keyboards, and try **Am**.

For an unsupported song, the app offers searches for chords, MIDI and MusicXML. These are external search links, not automatic imports. The library can be expanded with checked symbolic sources. A chord chart alone does not supply a timed melody.

## Development

Prerequisites: Node 22+ (24 tested), Python 3.12. FFmpeg and AI credentials are not required for the current flow.

```bash
bash scripts/setup.sh
npm run dev:all
```

Vite uses port 5173 and proxies `/api` to FastAPI on 8000. A built application uses `npm run build`, then:

```bash
.venv/bin/python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Optional `BAYANFLOW_ACCESS_PASSWORD` enables browser Basic authentication with username `bayanflow`. Leave it unset for public access. Existing Gemini secrets are not used by the library flow. Outbound access to `www.youtube.com` is used only for metadata; local library playback and manual song lookup work without it.

## Sources and simplification

See [library provenance and import instructions](server/library/SOURCES.md). Melody notes come from explicitly selected vocal MIDI tracks. The importer removes short ornaments and vocal polyphony, folds octaves, quantizes rhythm and derives simple triads from the written accompaniment. This is an adaptation for practice, not a guarantee of note-perfect agreement with a particular video. The Am toggle transposes minor songs and explicitly adapts major songs to minor as before.

## Checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
.venv/bin/python -m pytest -q
TEST_ORIGIN=http://127.0.0.1:8000 CHROMIUM_PATH=/usr/bin/chromium npm run test:browser
```

The live environment blocks YouTube oEmbed with a network-proxy 403, so automatic title retrieval here is verified with controlled HTTP fixtures. The real unavailable-metadata/manual-name fallback and library endpoints are validated locally. Browser checks cover explicit confirmation, unsupported songs, both imported full arrangements, both keyboard highlights, Am, seek and browser saving. No audio AI requests are made by this flow.

Each cloud task is already isolated. Use the existing checkout; do not create a Git worktree unless explicitly requested.
