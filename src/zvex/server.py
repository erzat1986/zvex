"""zvex(声桥) MCP server。

把声桥的 AI 视频译制能力暴露给任意 MCP 客户端(Claude Desktop / Cursor / …):
给一个视频链接,拿回多语种配音成片。全自动——服务端一阶段(识别/翻译)完成后
自动衔接二阶段(配音/合成),不需要人工校正环节。

鉴权走声桥 API Key(网页「账户设置 → API 密钥」创建,zvex- 开头),与网页端
共用同一个账户积分池;提交时按服务端 ffprobe 实测时长预扣,任务失败全额退款。

环境变量:
    ZVEX_API_KEY   必填,形如 zvex-xxxxxxxx
    ZVEX_BASE_URL  可选,默认 https://tts.xalhar.top(自建部署改这里)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

DEFAULT_BASE_URL = "https://tts.xalhar.top"
# 提交接口要等服务端把视频**下载完**才返回，几百 MB 的素材可能好几分钟。
# 2026-09-11 实测：一个 170MB 视频下载超过 120 秒 → 客户端抛异常，而服务端
# 其实已经建单扣费，客户以为失败、实际在跑还扣了钱。放宽到 15 分钟。
_REQUEST_TIMEOUT = 900.0
_CONNECT_TIMEOUT = 15.0
_POLL_INTERVAL = 15.0

# HTTP 状态码 → 给调用方(通常是 LLM)的可执行提示
_STATUS_HINTS = {
    401: "API key is missing, invalid, or revoked. Create a new one at "
         "https://tts.xalhar.top/app/settings (Account → API keys).",
    402: "Not enough credits. Top up at https://tts.xalhar.top/app/recharge.",
    409: "Another job of this account is still running — wait for it to finish "
         "(one concurrent job per account).",
    400: "The request was rejected by the server; see the detail above.",
}

mcp = MCPServer("zvex")

# 工具注解:客户端(Claude/OpenAI 目录)据此判断能否自动批准调用。
# 四个 hint 必须全部显式给布尔值——目录审核要求,缺一个就判不合格。
# 只读查询:不改环境、重复调用无副作用、会访问外部服务。
_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
# 提交译制任务:创建任务并扣费(非破坏性新增),但每次调用都建新单,
# 同参数重复提交会重复扣费 —— 因此不是幂等的。
_SUBMIT = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)


def _api_key() -> str:
    key = os.getenv("ZVEX_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ZVEX_API_KEY is not set. Create a key at "
            "https://tts.xalhar.top/app/settings and pass it via the MCP server env."
        )
    return key


def _base_url() -> str:
    return os.getenv("ZVEX_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_base_url(),
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=httpx.Timeout(_REQUEST_TIMEOUT, connect=_CONNECT_TIMEOUT),
    )


# 服务端返回的是同源相对路径(/uploads/xxx.mp4),调用方(通常是别的机器上的
# LLM)需要能直接点开的绝对 URL。
_ABSOLUTE_KEYS = ("final_video_url", "subtitle_url", "poll")


def _absolutize(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    base = _base_url()
    for key in _ABSOLUTE_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.startswith("/"):
            data[key] = base + value
    return data


def _error_text(resp: httpx.Response) -> str:
    """把 HTTP 错误翻成调用方能据以行动的文本(而不是抛异常中断会话)。"""
    try:
        detail = resp.json().get("detail")
    except Exception:
        detail = resp.text[:300]
    text = f"HTTP {resp.status_code}: {detail}"
    hint = _STATUS_HINTS.get(resp.status_code)
    return f"{text} — {hint}" if hint else text


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool(annotations=_READ_ONLY)
async def estimate_cost(minutes: float, tier: str = "standard") -> str:
    """Estimate the credit cost of dubbing a video and check the credit balance.

    Pricing is a flat 10 credits per minute for every tier (a tier only changes
    which features are available, not the price).

    Args:
        minutes: Video length in minutes (0 < minutes <= 600).
        tier: "fast", "standard" or "professional".

    Returns:
        JSON with credits, current balance and whether the balance is enough.
    """
    async with _client() as client:
        resp = await client.get("/api/v1/estimate", params={"minutes": minutes, "tier": tier})
    if resp.status_code >= 400:
        return _error_text(resp)
    return _dump(resp.json())


@mcp.tool(annotations=_SUBMIT)
async def submit_dubbing_job(
    video_url: str,
    target_language: str = "ru",
    tier: str = "standard",
) -> str:
    """Submit a fully automatic dubbing job: a video URL in, a dubbed video out.

    The server downloads the video, then runs speech recognition, speaker
    separation, translation, voice cloning/TTS and composition — no manual
    review step. Credits are charged up front based on the server-measured
    duration and refunded in full if the job fails.

    The job runs in the background: use get_job_status to poll it, or
    wait_for_job to block until it finishes. Only one job per account may run
    at a time (a second submission returns HTTP 409).

    Args:
        video_url: Publicly reachable http(s) video link (max 500 MB).
        target_language: Dubbing language, e.g. "ru", "en", "es"
            (depends on the deployment's supported set).
        tier: "fast", "standard" or "professional".

    Returns:
        JSON with job_id, run_id, measured duration and the charged credits.
    """
    async with _client() as client:
        resp = await client.post(
            "/api/v1/jobs",
            json={"video_url": video_url, "target_language": target_language, "tier": tier},
        )
    if resp.status_code >= 400:
        return _error_text(resp)
    return _dump(_absolutize(resp.json()))


@mcp.tool(annotations=_READ_ONLY)
async def get_job_status(job_id: int) -> str:
    """Check a dubbing job's status.

    Once the status is "completed" the response also carries the dubbed video
    and subtitle download URLs. "failed" carries the error and means the
    credits were refunded.

    Args:
        job_id: The job_id returned by submit_dubbing_job.

    Returns:
        JSON with status ("processing" / "completed" / "failed" / "cancelled")
        and, for a completed job, final_video_url and subtitle_url.
    """
    async with _client() as client:
        resp = await client.get(f"/api/v1/jobs/{job_id}")
    if resp.status_code >= 400:
        return _error_text(resp)
    return _dump(_absolutize(resp.json()))


@mcp.tool(annotations=_READ_ONLY)
async def wait_for_job(job_id: int, timeout_seconds: int = 1800) -> str:
    """Block until a dubbing job reaches a final state, then return its result.

    Convenience wrapper around get_job_status for callers that just want the
    finished video. Dubbing typically takes a small multiple of the video's own
    length, so keep the timeout generous.

    Args:
        job_id: The job_id returned by submit_dubbing_job.
        timeout_seconds: Give up after this long (default 1800, max 7200).

    Returns:
        JSON with the final status and, when completed, the output URLs.
    """
    timeout_seconds = max(30, min(int(timeout_seconds), 7200))
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last = ""
    async with _client() as client:
        while True:
            resp = await client.get(f"/api/v1/jobs/{job_id}")
            if resp.status_code >= 400:
                return _error_text(resp)
            data = resp.json()
            last = data.get("status", "")
            if last in ("completed", "failed", "cancelled"):
                return _dump(_absolutize(data))
            if asyncio.get_running_loop().time() >= deadline:
                return _dump({
                    "job_id": job_id,
                    "status": last,
                    "note": f"Still {last} after {timeout_seconds}s. "
                            "Call wait_for_job or get_job_status again to keep waiting.",
                })
            await asyncio.sleep(_POLL_INTERVAL)


def main() -> None:
    """Entry point declared in pyproject ([project.scripts])."""
    # stdio 传输下 stdout 是 JSON-RPC 协议通道:任何多余输出都会破坏协议。
    # 显式把日志钉到 stderr,并关掉 httpx 的逐请求输出。
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    mcp.run()


if __name__ == "__main__":
    main()
