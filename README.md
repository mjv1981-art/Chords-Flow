# BayanFlow

Paste a YouTube link or upload audio, choose a 30-second or one-minute excerpt, and transcribe it with **MuScriptor**. BayanFlow turns the selected voice/instrument into one beginner melody with simple bass–chord accompaniment. You can also upload MIDI exported by the hosted MuScriptor app; this works without local model credentials. The previous two-song MIDI library remains available through a secondary link.

The imported Base44 player retains its sheet music, left/right keyboard styling, audio synthesis, playback controls and **Am** toggle. The right hand uses **B-griff**, viewed from the front with the bellows to its left: inner row 3 = C/E♭/F♯/A, middle row 2 = C♯/E/G/B♭, outer row 1 = D/F/A♭/B. The left hand is Stradella. Saved arrangements stay in this browser.

## Browser preview

Follow [WEB_PREVIEW.md](WEB_PREVIEW.md) for GitHub Codespaces and exact Hugging Face access instructions. The complete web app runs on port 8000. MIDI import requires no model token. Live audio recognition requires accepting the selected MuScriptor model licence and supplying `HF_TOKEN` securely to the server; Gemini is unused.

1. Paste a link or choose an audio file. Set the excerpt start to a verse with singing and leave **Вокал** selected for the melody.
2. Click **Получить мелодию и аккорды**. Real processing stages and completed five-second model chunks are shown. Cancel stops the child process. After a refresh, **Проверить результат обработки** reconnects to a saved job.
3. Alternatively, choose a `.mid`/`.midi` export, click **Открыть MIDI**, select its voice/lead track, then **Открыть выбранную мелодию**. No inference runs for MIDI imports.
4. Press Play, check both keyboards, and try **Am**. Approximate tempo and arranged accompaniment are labelled in the player.

The secondary library still supports title confirmation and symbolic-source searches. A chord chart alone does not supply a timed melody.

## Development

Prerequisites: Node 22+ (24 tested), Python 3.12, FFmpeg/ffprobe. MuScriptor uses a separate `.venv-muscriptor` with pinned CPU PyTorch, so its dependencies do not replace FastAPI in the player backend.

```bash
bash scripts/setup.sh
bash scripts/setup-muscriptor.sh
npm run dev:all
```

Vite uses port 5173 and proxies `/api` to FastAPI on 8000. A built application uses `npm run build`, then:

```bash
.venv/bin/python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Optional `BAYANFLOW_ACCESS_PASSWORD` enables browser Basic authentication with username `bayanflow`. The default `MUSCRIPTOR_MODEL=small` suits CPU Codespaces; `medium`/`large` require accepting their separate model pages and more resources. Model size can affect quality compared with the hosted demo. `MUSCRIPTOR_THREADS` defaults to 2. The token is server-only, never a `VITE_` variable.

YouTube audio retrieval still depends on YouTube accepting yt-dlp requests. When it refuses access, upload the recording or a MuScriptor MIDI export. Upload limits: audio 50 MB, MIDI 2 MB. One inference runs at a time, with a ten-minute wall-clock limit. Raw audio/process logs are removed when a job ends; job results last up to 24 hours and reusable arrangements up to seven days. Only one Uvicorn worker is supported by the inference-slot controller.

## Sources and simplification

MuScriptor 0.3.0 supplies pitches, onset/offset times and instrument groups. Its optional **Beat This** model estimates rhythm; a lightweight spectral fallback is labelled approximate. The beginner converter removes short ornaments/polyphony, folds octaves, preserves rests, quantizes rhythm and derives triads from the transcribed accompaniment. For a lone melody, chords are explicitly labelled as an arrangement. Irregular tempo and ambiguous meter use a practice grid. The Am toggle behaves as before.

MuScriptor code is MIT; its trained weights are **CC BY-NC 4.0** (non-commercial). See the [official model repository](https://github.com/muscriptor/muscriptor). Model weights are downloaded at runtime, never committed or baked into images. Existing library provenance remains in [SOURCES.md](server/library/SOURCES.md).

The default Docker/Render configuration supports MIDI import and the library. For a host with sufficient memory, build with `--build-arg ENABLE_MUSCRIPTOR=1` and supply `HF_TOKEN` at runtime to enable inference. A small free web-service instance is not a suitable inference host.

## Checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
.venv/bin/python -m pytest -q
TEST_ORIGIN=http://127.0.0.1:8000 CHROMIUM_PATH=/usr/bin/chromium npm run test:browser
```

Validation: 61 Python checks, six music checks, nine browser checks, lint, typecheck and build. MIDI interoperability is tested with synthetic known notes serialized by the real MuScriptor 0.3.0 API. Browser checks include an actual MIDI upload, both keyboards, Am, progress, cancellation and existing library playback. Recognition responses in browser/process tests are controlled fixtures. Live musical recognition remains unverified until the gated weights and YouTube/audio access are available; these tests do not measure pitch accuracy.

Each cloud task is already isolated. Use the existing checkout; do not create a Git worktree unless explicitly requested.
