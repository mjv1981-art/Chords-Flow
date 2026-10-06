# BayanFlow web preview on GitHub

Use GitHub Codespaces for a temporary browser-accessible preview. GitHub Pages cannot run the Python metadata/library backend. Codespaces uses your account's included compute/storage allowance and stops serving the preview when the Codespace stops. No AI API key or Windows installation is needed.

1. Open the repository's **bayanflow-web-preview** branch. Choose **Code → Codespaces → Create codespace on bayanflow-web-preview**, using the 2-core machine.
2. Wait for container setup to install dependencies, build the player and start port **8000**.
3. Open **Ports**, then the forwarded address for **8000 / BayanFlow**. To share it publicly, right-click the port and select **Port Visibility → Public**.
4. Paste a YouTube link and click **Определить песню**. Confirm the matching song with **Да, открыть …**. The starter library includes **Sleeping Sun** and **Come Cover Me** by Nightwish.
5. If YouTube does not return the title, enter **Nightwish — Sleeping Sun** (or **Nightwish — Come Cover Me**) in **Песня и исполнитель**, then click **Найти аранжировку** and confirm.
6. Press Play and try the **Am** toggle. The existing B-griff player uses a simplified MIDI arrangement; its key/tempo can differ from the chosen video.

To update an existing Codespace, open **Terminal** and run:

```bash
git pull --ff-only && bash scripts/start-codespace.sh --restart
```

Wait for **BayanFlow is running**, then refresh the app tab. Startup prepares missing dependencies and the build automatically; logs are in `.cache/codespace-server.log`. If an old image reports a Yarn `NO_PUBKEY`, the installer uses signed Debian archives for prerequisites without changing unrelated repository settings.

Unsupported songs offer external searches for chords, MIDI and MusicXML. New sources are not automatically downloaded/imported; they need to be checked and added to the library. Sources and track selections are documented in [SOURCES.md](server/library/SOURCES.md). No model listens to the video, and existing Gemini secrets are unused.

`Dockerfile` and `render.yaml` also support a Render web service. Connect this branch as a Render Blueprint; no API secret is required. The optional `BAYANFLOW_ACCESS_PASSWORD` enables browser Basic authentication (username `bayanflow`) if desired. Render availability and free-plan limits are determined by Render.
