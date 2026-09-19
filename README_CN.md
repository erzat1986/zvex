# zvex MCP 服务

[![M8ven Score](https://m8ven.ai/badge/mcp/erzat1986-zvex-1tz743)](https://m8ven.ai/mcp/erzat1986-zvex-1tz743)

把 AI 视频译制能力接进你的 AI 助手：给它一个视频链接或本地文件，拿回配音成片 —— 支持俄语、英语、西班牙语，**保留原说话人的音色**（按角色做音色克隆）。

由 [zvex（声桥）](https://zvex.cn) 提供。服务端是纯 HTTP 客户端，本地不需要 GPU、不需要下载模型。

## 安装

```bash
uvx zvex                # 免安装直接运行
# 或
uv tool install zvex    # 安装 zvex 命令
# 或
pip install zvex
```

## 获取 API 密钥

1. 打开 <https://zvex.cn> 注册（新账号送 10 分钟免费额度）
2. 进入 **账户设置 → API 密钥**
3. 创建一个，复制 `zvex-` 开头的那串 —— **只显示一次，请立即保存**

任务与网页端共用同一个积分余额，**10 积分 / 分钟**；任务失败或取消**全额退还**。充值支持**微信支付、支付宝、PayPal**。

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
| `ZVEX_BASE_URL` | 否 | `https://zvex.cn` | 自建部署时改这里 |

## 可用工具

| 工具 | 作用 |
|---|---|
| `estimate_cost(minutes, tier)` | 按时长预估积分消耗，返回当前余额 |
| `upload_video(file_path)` | 上传本地视频文件，返回 `file_id` |
| `submit_dubbing_job(video_url, target_language, tier, file_id)` | 提交译制任务，返回任务号 |
| `get_job_status(job_id)` | 查询任务状态；完成时带回成片与字幕链接 |
| `wait_for_job(job_id, timeout_seconds)` | 阻塞等待任务出结果 |

典型用法 —— 公网链接：

```
帮我把它译制成俄语：https://example.com/episode-01.mp4
  → 助手调用 submit_dubbing_job，再 wait_for_job
  → 返回成片链接
```

典型用法 —— 本地文件（不需要公网地址）：

```
译制一下 /home/me/clip.mov
  → 助手调用 upload_video 拿到 file_id
  → submit_dubbing_job(file_id=…) 再 wait_for_job
  → 返回成片链接
```

## 注意事项

- `submit_dubbing_job` 的 `video_url` 与 `file_id` **二选一**，必须给且只能给一个
- `video_url` 必须是**公网可访问**的 http(s) 直链，单个不超过 **500MB**
- `upload_video` 会把文件传到服务端（上限 500MB）；上传后的副本会保留，同一个 `file_id` 可重复用于多次提交
- 目标语言以部署支持集为准（当前 `ru` / `en` / `es`）
- `tier` 取 `fast` / `standard` / `professional`，只决定功能范围，**不改变价格**
- 每个账号同一时间只跑一个任务，重复提交返回 409
- 成片与字幕链接是**带签名的限时链接**（约 24 小时有效），无需登录即可下载；过期后重新查一次任务即可拿到新链接

## 常见报错

| 报错 | 原因与处理 |
|---|---|
| `401 API key is missing, invalid, or revoked` | 密钥没配、配错或已被吊销 —— 到设置页核对或重建 |
| `402 Not enough credits` | 积分不足，充值后重试 |
| `409 Another job … still running` | 上一个任务还没结束（单并发限制） |
| `400 … 非公网地址` | 视频链接指向了内网地址，换公网直链 |

详细的接入说明与截图见 <https://zvex.cn/docs/mcp>。

## MCP 不提供专家模式，需要完整专家模式请到 zvex.cn

MCP 侧提供的是**全自动**通路：给一个视频链接，直接拿回成片，中间没有人工校正环节。
这是有意为之——LLM 客户端既听不了波形，也判断不了一句台词配得好不好。

**专家模式没有做成 MCP 工具。** 想体验完整的专家模式，请前往
[zvex.cn](https://zvex.cn)，在订单里点「校正」进入
`/expert/{run_id}` 页面。

专家模式里能做什么、为什么值得去一趟：

| 能力 | 解决什么问题 |
|---|---|
| **逐段精修** | 每一段的原文、译文、起止时间都能改 —— 自动流程负责把大意做对，专家模式负责把细节做对 |
| **波形时间轴** | 拖拽色块边界改时间，点行跳转播放，右键与相邻同说话人段合并 / 拆分。断句拆开、碎句合并，不用碰任何文本文件 |
| **改完原文重译** | 修好原文后只重译这一段，不必整单重跑 |
| **逐段配音开关** | 取消勾选「配音」即保留该段原声。歌曲、画面文字、克隆音色扛不住的台词，靠它兜住 |
| **说话人 / 性别校正** | 修正聚错的说话人和判错的性别；TTS 环节会**尊重人工选择**，不再自动覆盖 |
| **情绪标签** | 逐段标 平静 / 开心 / 生气 / 悲伤 / 低语 / 激动 / 沉稳，TTS 语调跟着走 |
| **术语预学习** | 先抽取人名与专业词，保证整集译名一致 |
| **混音控制** | 配音音量、背景音乐音量、配音语速、跨说话人间隔、字幕字号与位置，按片子调而不是吃默认值 |
| **字幕清除** | 模糊 / delogo / 黑条遮挡原片硬字幕，避免中译双语字幕叠字 |
| **可选重功能** | ASD 说话人识别、Face Clustering 物理身份聚类、跨剧集 `voice_bank` 音色复用（连载短剧） |
| **安全复核闸门** | 低置信片段（疑似说话人错配、唱歌二次验证、BGM 判定存疑）会被标出并**阻止生成**，直到你处理；自动通路则会直接放行 |

一句话：MCP 是「我只要成片」的通路；网页版专家模式是修掉机器判断不了的那 5% 的地方。
建议先用 MCP 跑自动流程，结果需要人耳把关时，再到网页版打开同一笔订单。

## 支付宝 AI 付智能体：零注册直连

如果你的智能体接入了**支付宝 AI 付**（A2M 402 协议，如 OpenClaw 类客户端），可以完全跳过注册和充值，按次自动结算：

| 资源 | 端点 | 计价 |
|---|---|---|
| 多语种文本翻译 | `POST https://zvex.cn/a2m/v1/translate` | ¥0.1 / 次 |
| AI 视频配音 | `POST https://zvex.cn/a2m/v1/dubbing` | ¥1 / 分钟（最低 ¥2，按实测时长动态计费） |

流程：无凭证调用 → `402` + `Payment-Needed` 签名账单 → 智能体经支付宝 AI 付付款 → 携带 `Payment-Proof` 重试 → 交付资源。配音为异步任务，凭 `out_trade_no` 轮询 `/a2m/v1/dubbing/status/{out_trade_no}` 获取成片。

两个服务均已上架支付宝 AI 付服务市场（搜索"声桥"或"zvex"）。协议细节见 <https://zvex.cn/docs/mcp>。普通 MCP 客户端（不支持 402 协议的）请继续使用上方的 API 密钥方式。

## 开发

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e .
ZVEX_API_KEY=zvex-… .venv/bin/python -m zvex.server
```

## 许可

MIT
