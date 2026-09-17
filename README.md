# zvex MCP server

AI video dubbing as an MCP tool: hand it a video URL, get back a fully dubbed
video in Russian, English or Spanish — keeping the original speakers' voices
through per-speaker voice cloning.

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
| `submit_dubbing_job(video_url, target_language, tier)` | Queue a dubbing job, returns `job_id` |
| `get_job_status(job_id)` | Poll once; final states carry the output URLs |
| `wait_for_job(job_id, timeout_seconds)` | Block until the job finishes |

Typical flow:

```
submit_dubbing_job("https://example.com/episode-01.mp4", target_language="ru")
  → {"job_id": 42, "credits_cost": 240, "duration_sec": 1441.0, …}
wait_for_job(42)
  → {"status": "completed", "final_video_url": "…", "subtitle_url": "…"}
```

### Notes

- `video_url` must be a publicly reachable `http(s)` link, up to 500 MB.
- `target_language` depends on the deployment (`ru`, `en`, `es` on the hosted
  service).
- `tier` is `fast`, `standard` or `professional` — it selects which features
  are available, not the price.
- One job per account runs at a time; a second submission returns HTTP 409.
- Output links are served from the zvex domain and require being signed
  in there.

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
