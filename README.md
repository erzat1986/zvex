# zvex MCP server

[![M8ven Score](https://m8ven.ai/badge/mcp/erzat1986-zvex-1tz743)](https://m8ven.ai/mcp/erzat1986-zvex-1tz743)

AI video dubbing as an MCP tool: hand it a video URL or a local file, get back
a fully dubbed video in Russian, English or Spanish — keeping the original
speakers' voices through per-speaker voice cloning.

Powered by [zvex (声桥)](https://tts.xalhar.top).

The server is a thin stdio client over zvex's HTTP API, so it runs
anywhere Python does — no GPU, no local models.

## Install

```bash
uvx zvex                # run it without installing anything
# or
uv tool install zvex    # install the `zvex` command
# or
pip install zvex
```

(Working from a source checkout instead? Use `uv tool install ./mcp/zvex`.)

## Get an API key

1. Sign in at <https://tts.xalhar.top>
2. Open **Account → API keys** and create one
3. Copy the `zvex-…` value — it is shown **only once**

Jobs are billed from the same credit balance as the web app, at a flat
**10 credits per minute** of video. A failed job is refunded in full.
Top-up supports **WeChat Pay, Alipay and PayPal**.

## Configure your MCP client

Claude Desktop (`claude_desktop_config.json`) or Cursor (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "zvex": {
      "command": "uvx",
      "args": ["zvex"],
      "env": {
        "ZVEX_API_KEY": "zvex-your-key-here"
      }
    }
  }
}
```

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `ZVEX_API_KEY` | yes | — | `zvex-…` key from the account page |
| `ZVEX_BASE_URL` | no | `https://tts.xalhar.top` | API base URL (self-hosted deployments) |

## Tools

| Tool | Purpose |
|---|---|
| `estimate_cost(minutes, tier)` | Credit cost and current balance |
| `upload_video(file_path)` | Upload a local file, returns a `file_id` |
| `submit_dubbing_job(video_url, target_language, tier, file_id)` | Queue a dubbing job, returns `job_id` |
| `get_job_status(job_id)` | Poll once; final states carry the output URLs |
| `wait_for_job(job_id, timeout_seconds)` | Block until the job finishes |

Typical flow — public URL:

```
submit_dubbing_job(video_url="https://example.com/episode-01.mp4", target_language="ru")
  → {"job_id": 42, "credits_cost": 240, "duration_sec": 1441.0, …}
wait_for_job(42)
  → {"status": "completed", "final_video_url": "…", "subtitle_url": "…"}
```

Typical flow — local file (no public URL needed):

```
upload_video("/home/me/clip.mov")
  → {"file_id": "a1b2c3d4e5f60718", "duration_sec": 92.4, …}
submit_dubbing_job(file_id="a1b2c3d4e5f60718", target_language="ru")
  → {"job_id": 43, …}
```

### Notes

- `submit_dubbing_job` takes **exactly one** of `video_url` or `file_id`.
- `video_url` must be a publicly reachable `http(s)` link, up to 500 MB.
- `upload_video` sends the file to the server (up to 500 MB); the uploaded
  copy persists, so one upload can back several submissions.
- `target_language` depends on the deployment (`ru`, `en`, `es` on the hosted
  service).
- `tier` is `fast`, `standard` or `professional` — it selects which features
  are available, not the price.
- One job per account runs at a time; a second submission returns HTTP 409.
- Output links are signed, time-limited URLs (valid ~24 h) — they download
  without signing in. Re-poll the job to get a fresh link once one expires.

## No expert mode over MCP — use the web app for that

The MCP tools are the **fully automatic** path: you hand over a video URL and
get back a finished dub, with no review step in between. That is deliberate —
an LLM client has no way to listen to a waveform or judge whether a line landed.

**Expert mode is not exposed as an MCP tool.** For the full expert mode, go to
[tts.xalhar.top](https://tts.xalhar.top) and open an order's **Review** page
(`/expert/{run_id}`).

What you get there, and why it is worth the trip:

| Capability | What it fixes |
|---|---|
| **Segment-by-segment editing** | Edit the source text, the translation, and the start/end timing of every segment — the automatic pass gets the gist right, this gets the details right. |
| **Waveform timeline** | Drag region borders to re-time a line, click a row to jump-play it, right-click to merge or split. Split a run-on sentence or merge two fragments without touching a text file. |
| **Re-translate after editing** | Fix the source line, then re-translate just that segment — no need to rerun the whole job. |
| **Per-segment dub on/off** | Untick "Dub" to keep a segment's original voice. Essential for songs, on-screen text, or a line the clone cannot carry. |
| **Speaker & gender correction** | Fix mis-clustered speakers and wrong gender assignments; the TTS gate respects your manual choice instead of re-deriving it. |
| **Emotion labels** | Tag a segment calm / happy / angry / sad / whisper / excited / steady — the TTS intonation follows it. |
| **Terminology pre-learning** | Extract names and jargon from the script first, so they translate consistently across the whole episode. |
| **Mixing controls** | Dubbing volume, background-music level, dubbing speed, cross-speaker gap, subtitle font size and position — tuned per job instead of accepting the defaults. |
| **Subtitle removal** | Blur or delogo burned-in source subtitles (or mask them with a bar) so you don't end up with double subtitles. |
| **Optional heavy features** | Active-speaker detection, face clustering and cross-episode `voice_bank` reuse for serials. |
| **Safety review gate** | Low-confidence segments (possible speaker mismatch, singing, uncertain BGM) are flagged and **block** video generation until you resolve them — the automatic path would have shipped them silently. |

In short: MCP is the "just give me the video" path; the web app's expert mode is
where you fix the 5% that a machine cannot judge. Run the automatic pass over
MCP first, then open the same order in the web app whenever the result needs a
human ear.

## Alipay AI Pay agents (zero sign-up)

If your agent is wired into **Alipay AI Pay** (the A2M 402 protocol —
OpenClaw-style clients), you can skip sign-up and top-up entirely and pay
per call:

| Resource | Endpoint | Pricing |
|---|---|---|
| Text translation | `POST https://tts.xalhar.top/a2m/v1/translate` | ¥0.1 / call |
| Video dubbing | `POST https://tts.xalhar.top/a2m/v1/dubbing` | ¥1 / minute (min ¥2, billed on measured duration) |

Flow: call without credentials → `402` + `Payment-Needed` signed bill →
pay via Alipay AI Pay → retry with `Payment-Proof` → resource delivered.
Dubbing is asynchronous; poll `/a2m/v1/dubbing/status/{out_trade_no}` for
the finished video and subtitles.

Both services are live on the Alipay AI Pay service bazaar (search
"声桥" or "zvex"). Protocol details: <https://tts.xalhar.top/docs/mcp>.
Regular MCP clients without 402 support should use the API-key path above.

## Development

```bash
uv venv --python 3.11 .venv-test
uv pip install --python .venv-test/bin/python -e .
ZVEX_API_KEY=zvex-… .venv-test/bin/python -m zvex.server
```
