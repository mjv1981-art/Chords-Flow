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

## Codex environment access

The secret in this chat's **Environment settings** is separate from a **GitHub Codespaces secret**. To let Codex verify live inference here, add the same read token as `HF_TOKEN` in Environment settings, review/save the prepared model-download domains and scripts, then publish the environment. The required domains include `huggingface.co`, Hugging Face download/CDN hosts and `cloud.cp.jku.at` for optional Beat This weights. Saving configuration does not prove the running environment can reach them.

If you want a public port, use **Ports → right-click 8000 → Port Visibility → Public**, then open its forwarded address. An optional `BAYANFLOW_ACCESS_PASSWORD` restricts browser access (username `bayanflow`).

The secondary **Готовые аранжировки из библиотеки** link still opens the two existing Nightwish MIDI arrangements. Gemini credentials are unused. Runtime logs are `.cache/codespace-server.log`; secrets and model weights stay outside Git.
