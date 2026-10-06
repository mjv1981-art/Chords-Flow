# BayanFlow browser preview on GitHub

GitHub Pages serves static files and cannot run the Python/Gemini transcription backend. Use a **GitHub Codespace** for a temporary, browser-accessible preview. No installation on your computer is needed. Codespaces uses your GitHub account's included compute/storage allowance; it is not permanent, unlimited free hosting. Check remaining usage under GitHub Settings → Billing and licensing before starting, and stop/delete the Codespace when finished.

1. In GitHub, open **Settings → Codespaces → Secrets → New secret**. Name it `GEMINI_API_KEY`, enter your Gemini key securely, and grant access to `mjv1981-art/Chords-Flow`. The secret configured in Codex is not automatically transferred to GitHub. Do not put the key in a repository file or a Pages build variable.
2. Open the repository's **bayanflow-web-preview** branch. Choose **Code → Codespaces → Create codespace on bayanflow-web-preview**. Use the 2-core machine. You can also open the branch-specific Codespaces creation link supplied in chat.
3. Wait for the dev-container setup to finish. It installs Python/Node/FFmpeg dependencies, builds the existing player, and starts the complete app on port **8000**.
4. In the browser editor, open the **Ports** tab (next to Terminal). Find **8000 / BayanFlow**, then use **Open in Browser**. That forwarded HTTPS address runs both the player and backend.
5. To allow everybody to use the preview, right-click port **8000**, select **Port Visibility → Public**, then share its forwarded address. Public access uses your Gemini API quota. Configure your API quota/budget appropriately. The optional `BAYANFLOW_ACCESS_PASSWORD` secret enables browser Basic authentication with username `bayanflow` if you later want a private preview; it is not required.
6. Paste the YouTube link and click **Получить мелодию и аккорды**. After the first playable fragment, **Открыть готовую часть** lets you practice while the rest is processed; the player labels this as a partial arrangement. When processing finishes, the full result opens. Press Play; verify the left/right keyboard highlights. Toggle **Am** and press Play again. If a later fragment fails or the attempt reaches its waiting limit, the ready part remains playable. Submitting the same link again reuses the validated fragments saved under `.cache/transcriptions`. Keep the Codespace running while testing. When it stops, the preview URL stops serving the app.

If the page says transcription is not configured, check that the Codespaces secret is assigned to this repository, then stop and restart the Codespace so the new secret is injected.

If startup failed or reports `.venv/bin/python: No such file or directory`, open **Terminal** in the browser editor and run:

```bash
git pull --ff-only && bash scripts/start-codespace.sh --restart
```

The startup script installs missing prerequisites in Codespaces, creates the Python environment, installs dependencies, and builds the player before starting the server. Wait until it reports that BayanFlow is running, then open port **8000** from **Ports**. Later starts reuse dependencies and the build when they have not changed. The `--restart` option restarts the preview process recorded by the script, so backend updates take effect. If startup still fails, the terminal shows the error; server output is also saved in `.cache/codespace-server.log`.

If the image reports `NO_PUBKEY` for the Yarn repository, pull the latest startup script with the command above. Prerequisite installation uses Debian's official archives and archive signing key, without changing the image's other repository settings.

**Known limitation:** Gemini accepts actual audio, but the tested generated melody was transcribed with incorrect pitches/key. This is a prototype; musical accuracy is not ready for reliable practice. Gemini now receives the YouTube URL directly, avoiding downloads from the hosting server. A live request accepted the screenshot video URL; this does not establish accurate melody/chords or access to every video. Private or restricted videos may remain unavailable.

## Permanent hosting alternative

`Dockerfile` serves the frontend and FastAPI backend together; FFmpeg and Node are included. `render.yaml` defines a Render web service using its free plan, subject to Render availability and plan limits. Connect this GitHub branch as a Render Blueprint and set `GEMINI_API_KEY` securely in Render. The server reads the host's `PORT`. No key is embedded in the image or browser bundle. The public prototype can use your Gemini quota; add the optional `BAYANFLOW_ACCESS_PASSWORD` environment secret to require a browser password. Only one Uvicorn worker is used because transcription jobs currently live in process memory.

The dev-container, scripts, Docker container and blueprint prepare deployment; an actual GitHub Codespace or Render service still needs to be created in your hosting account. Do not describe a published branch as a live site.

Validation in Codex: 25 server checks passed, and the Docker image successfully served the built frontend, JS/CSS assets and API, detected FFmpeg/Node, and respected the hosting PORT. The container runs as a non-root user. The local build used the existing trusted CA bundle through a temporary build secret mount; TLS verification remained enabled and the bundle is not baked into the image. The user has opened the player through their Codespace; the new native-YouTube flow still needs validation in that Codespace after pulling and restarting.
