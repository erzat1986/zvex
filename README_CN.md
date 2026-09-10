# zvex MCP 服务

把 AI 视频译制能力接进你的 AI 助手：给它一个视频链接，拿回配音成片 —— 支持俄语、英语、西班牙语，**保留原说话人的音色**（按角色做音色克隆）。

由 [zvex（声桥）](https://tts.xalhar.top) 提供。服务端是纯 HTTP 客户端，本地不需要 GPU、不需要下载模型。

## 安装

```bash
uvx zvex                # 免安装直接运行
# 或
uv tool install zvex    # 安装 zvex 命令
# 或
pip install zvex
```

## 获取 API 密钥

1. 打开 <https://tts.xalhar.top> 注册（新账号送 10 分钟免费额度）
2. 进入 **账户设置 → API 密钥**
3. 创建一个，复制 `zvex-` 开头的那串 —— **只显示一次，请立即保存**

任务与网页端共用同一个积分余额，**10 积分 / 分钟**；任务失败或取消**全额退还**。

## 配置到客户端

Claude Desktop（`claude_desktop_config.json`）或 Cursor（`.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "zvex": {
      "command": "uvx",
      "args": ["zvex"],
      "env": {
        "ZVEX_API_KEY": "zvex-你的密钥"
      }
    }
  }
}
```

| 环境变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `ZVEX_API_KEY` | 是 | — | 账户页创建的 `zvex-…` 密钥 |
| `ZVEX_BASE_URL` | 否 | `https://tts.xalhar.top` | 自建部署时改这里 |

## 可用工具

| 工具 | 作用 |
|---|---|
| `estimate_cost(minutes, tier)` | 按时长预估积分消耗，返回当前余额 |
| `submit_dubbing_job(video_url, target_language, tier)` | 提交译制任务，返回任务号 |
| `get_job_status(job_id)` | 查询任务状态；完成时带回成片与字幕链接 |
| `wait_for_job(job_id, timeout_seconds)` | 阻塞等待任务出结果 |

典型用法：

```
帮我把它译制成俄语：https://example.com/episode-01.mp4
  → 助手调用 submit_dubbing_job，再 wait_for_job
  → 返回成片链接
```

## 注意事项

- `video_url` 必须是**公网可访问**的 http(s) 直链，单个不超过 **500MB**
- 目标语言以部署支持集为准（当前 `ru` / `en` / `es`）
- `tier` 取 `fast` / `standard` / `professional`，只决定功能范围，**不改变价格**
- 每个账号同一时间只跑一个任务，重复提交返回 409
- 成片与字幕链接由 zvex 域名提供，**需要在浏览器里登录该站**才能下载

## 常见报错

| 报错 | 原因与处理 |
|---|---|
| `401 API key is missing, invalid, or revoked` | 密钥没配、配错或已被吊销 —— 到设置页核对或重建 |
| `402 Not enough credits` | 积分不足，充值后重试 |
| `409 Another job … still running` | 上一个任务还没结束（单并发限制） |
| `400 … 非公网地址` | 视频链接指向了内网地址，换公网直链 |

详细的接入说明与截图见 <https://tts.xalhar.top/docs/mcp>。

## 开发

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e .
ZVEX_API_KEY=zvex-… .venv/bin/python -m zvex.server
```

## 许可

MIT
