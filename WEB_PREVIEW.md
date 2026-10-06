# BayanFlow browser preview on GitHub

GitHub Pages serves static files and cannot run the Python/FFmpeg YouTube transcription backend. Use a **GitHub Codespace** for a temporary, browser-accessible preview. No installation on your computer is needed. Codespaces uses your GitHub account's included compute/storage allowance; it is not permanent, unlimited free hosting. Check remaining usage under GitHub Settings → Billing and licensing before starting, and stop/delete the Codespace when finished.

1. In GitHub, open **Settings → Codespaces → Secrets → New secret**. Name it `GEMINI_API_KEY`, enter your Gemini key securely, and grant access to `mjv1981-art/Chords-Flow`. The secret configured in Codex is not automatically transferred to GitHub. Do not put the key in a repository file or a Pages build variable.
2. Open the repository's **bayanflow-web-preview** branch. Choose **Code → Codespaces → Create codespace on bayanflow-web-preview**. Use the 2-core machine. You can also open the branch-specific Codespaces creation link supplied in chat.
3. Wait for the dev-container setup to finish. It installs Python/Node/FFmpeg dependencies, builds the existing player, and starts the complete app on port **8000**.
4. In the browser editor, open the **Ports** tab (next to Terminal). Find **8000 / BayanFlow**, then use **Open in Browser**. That forwarded HTTPS address runs both the player and backend.
5. To allow everybody to use the preview, right-click port **8000**, select **Port Visibility → Public**, then share its forwarded address. Public access uses your Gemini API quota. Configure your API quota/budget appropriately. The optional `BAYANFLOW_ACCESS_PASSWORD` secret enables browser Basic authentication with username `bayanflow` if you later want a private preview; it is not required.
6. Paste the YouTube link, click **Получить мелодию и аккорды**, and wait. Press Play; verify the left/right keyboard highlights. Toggle **Am** and press Play again. Keep the Codespace running while testing. When it stops, the preview URL stops serving the app.

If the page says transcription is not configured, check that the Codespaces secret is assigned to this repository, then stop and restart the Codespace so the new secret is injected.

If startup failed or reports `.venv/bin/python: No such file or directory`, open **Terminal** in the browser editor and run:

```bash
git pull --ff-only && bash scripts/start-codespace.sh
```

The startup script installs missing prerequisites in Codespaces, creates the Python environment, installs dependencies, and builds the player before starting the server. Wait until it reports that BayanFlow is running, then open port **8000** from **Ports**. Later starts reuse dependencies and the build when they have not changed. If startup still fails, the terminal shows the error; server output is also saved in `.cache/codespace-server.log`.

**Known limitation:** Gemini accepts actual audio, but the tested generated melody was transcribed with incorrect pitches/key. This is a prototype; musical accuracy is not ready for reliable practice. YouTube can also reject datacenter downloads or require login. A forwarded URL does not establish that a particular video can be downloaded or accurately transcribed.

## Permanent hosting alternative

`Dockerfile` serves the frontend and FastAPI backend together; FFmpeg and Node are included. `render.yaml` defines a Render web service using its free plan, subject to Render availability and plan limits. Connect this GitHub branch as a Render Blueprint and set `GEMINI_API_KEY` securely in Render. The server reads the host's `PORT`. No key is embedded in the image or browser bundle. The public prototype can use your Gemini quota; add the optional `BAYANFLOW_ACCESS_PASSWORD` environment secret to require a browser password. Only one Uvicorn worker is used because transcription jobs currently live in process memory.

The dev-container, scripts, Docker container and blueprint prepare deployment; an actual GitHub Codespace or Render service still needs to be created in your hosting account. Do not describe a published branch as a live site.

Validation in Codex: 25 server checks passed, and the Docker image successfully served the built frontend, JS/CSS assets and API, detected FFmpeg/Node, and respected the hosting PORT. The container runs as a non-root user. The local build used the existing trusted CA bundle through a temporary build secret mount; TLS verification remained enabled and the bundle is not baked into the image. Actual creation of a GitHub Codespace, its forwarded public address and YouTube download from that host remain unverified until your account creates the Codespace.
