# BayanFlow with MuScriptor in GitHub Codespaces

Use your existing browser Codespace. No application needs to run on Windows. Codespaces serves port **8000** while the Codespace is running; its compute/storage allowance follows your GitHub plan. GitHub Pages cannot execute transcription jobs.

## Update the app

In the Codespace editor, click **Terminal** and run:

```bash
git pull --ff-only && bash scripts/start-codespace.sh --restart
```

First startup installs an isolated CPU MuScriptor runtime, the player backend and the frontend. Wait for **BayanFlow is running**, then refresh the port-8000 app tab. Existing B-griff keyboards, synthesis, controls and the Am toggle are preserved.

## Play a MuScriptor export immediately

This path needs no Hugging Face token in BayanFlow.

1. Open [MuScriptor](https://muscriptor.kyutai.org), transcribe the desired recording, and download its **MIDI** export.
2. In BayanFlow, click **Или аудиофайл / MIDI из MuScriptor** and select that `.mid`/`.midi` file.
3. Click **Открыть MIDI**. If there are multiple tracks, select **voice** or the desired lead instrument under **Дорожка мелодии**.
4. Click **Открыть выбранную мелодию**, then Play. Try **Am** to transpose/adapt the arrangement.

## Enable automatic transcription in the Codespace

1. Sign in or create a free account at [Hugging Face](https://huggingface.co/join).
2. Open [MuScriptor small](https://huggingface.co/MuScriptor/muscriptor-small) and accept its access terms/licence. The weights allow non-commercial use. Access is granted automatically according to the official documentation.
3. Open [Hugging Face tokens](https://huggingface.co/settings/tokens), choose **Create new token**, select **Read** access, name it `BayanFlow`, and create it. A fine-grained token must allow reading the gated repositories you have accepted.
4. Open [GitHub Codespaces settings](https://github.com/settings/codespaces). Under **Secrets**, click **New secret**. Set **Name** to `HF_TOKEN`, paste the token in **Value**, and grant repository access to **mjv1981-art/Chords-Flow**. Click **Add secret**. Never commit the token or paste it into chat.
5. Stop and reopen the existing Codespace: press **F1**, choose **Codespaces: Stop Current Codespace**, then reopen it from [your Codespaces list](https://github.com/codespaces). A terminal/server restart alone does not inject a newly created Codespaces secret.
6. In Terminal, run the update/start command above if needed. Verify token presence without displaying its value:

   ```bash
   if [ -n "${HF_TOKEN:-}" ]; then echo "HF_TOKEN is available"; else echo "HF_TOKEN is missing"; fi
   ```

7. Refresh BayanFlow. Paste the YouTube link or choose an audio file. Set **Начало, секунды** to the start of a sung verse, leave **30 секунд** and **Вокал**, then click **Получить мелодию и аккорды**.

First inference downloads and caches model weights. Subsequent jobs reuse them. CPU speed and small-model accuracy can differ from MuScriptor's hosted service. `MUSCRIPTOR_MODEL=medium` or `large` selects a larger model only after accepting that model's separate Hugging Face page and providing adequate resources.

YouTube sometimes refuses cloud downloads. If BayanFlow reports that YouTube did not provide audio, choose an audio file or the MIDI-export path. Files are limited to 50 MB for audio and 2 MB for MIDI. Job progress is real; **Отменить** stops processing. **Проверить результат обработки** restores a pending job after refreshing. The server limits jobs to one at a time and ten minutes.

## Test authenticated YouTube access

This is an administrator setup test for `youtube_bot_check`, not a task for each song or each user. Cookies may still be rejected from Codespaces. The [official yt-dlp guidance](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies) warns that automated account use can cause restrictions; use a separate account. The export is a login credential: do not send it through chat, commit it, or upload it through BayanFlow's music-file input.

1. In the Codespace Terminal run `git pull --ff-only` and then `mkdir -p private && chmod 700 private`. The `private` folder is excluded from Git and is not served by the app.
2. In normal desktop **Google Chrome**, install [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc), the extension linked in yt-dlp's official FAQ. In Chrome's **Extensions → Manage extensions**, open its **Details** and enable **Allow in Incognito**.
3. Press **Ctrl+Shift+N**. In that private window open YouTube and sign in with the separate account. In the same tab open `https://www.youtube.com/robots.txt`; keep this as the only incognito tab.
4. Open the extension and export cookies for the current site in **Netscape/cookies.txt** format. Export only `youtube.com`, not all sites. Close the incognito window afterward, as recommended by yt-dlp to avoid session rotation.
5. Rename the downloaded file **youtube-cookies.txt**. In the Codespace's left **Explorer**, right-click the **private** folder, select **Upload…**, and select that file. Do not open or paste its contents.
6. In Terminal run:

   ```bash
   .venv/bin/python scripts/configure-youtube-cookies.py && bash scripts/start-codespace.sh --restart
   ```

   The helper validates an unexpired YouTube login, removes cookies for other sites, restricts file permissions, and sets the cookie-file path in the ignored `.env` while preserving other settings. This configures login but does not prove YouTube accepts it. A full Codespace restart is unnecessary for this file-based setting.
7. Refresh BayanFlow and retry the same video. If access is still blocked, report the visible error only. Cookies expire; repeat the export/upload/helper steps to refresh them. To disable this test, delete `private/youtube-cookies.txt`, remove `YOUTUBE_COOKIES_FILE` from `.env`, and restart the app.

## Codex environment access

The secret in this chat's **Environment settings** is separate from a **GitHub Codespaces secret**. To let Codex verify live inference here, add the same read token as `HF_TOKEN` in Environment settings, review/save the prepared model-download domains and scripts, then publish the environment. The required domains include `huggingface.co`, Hugging Face download/CDN hosts and `cloud.cp.jku.at` for optional Beat This weights. Saving configuration does not prove the running environment can reach them.

If you want a public port, use **Ports → right-click 8000 → Port Visibility → Public**, then open its forwarded address. An optional `BAYANFLOW_ACCESS_PASSWORD` restricts browser access (username `bayanflow`).

The secondary **Готовые аранжировки из библиотеки** link still opens the two existing Nightwish MIDI arrangements. Gemini credentials are unused. Runtime logs are `.cache/codespace-server.log`; secrets and model weights stay outside Git.
