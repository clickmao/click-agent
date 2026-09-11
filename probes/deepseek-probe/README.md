# deepseek-probe — DeepSeek 内部用例测试探针

click-agent 文档驱动迭代框架的**内部用例测试**工具：在不依赖 NativeAOT 构建的前提下，
用真实 DeepSeek API 验证 `src/agent.modelqueue` 发出的 OpenAI 兼容 chat/completions 请求契约，
并捕获项目 DTO 当前未解析的字段（如推理模型的 `reasoning_content`）。

## 运行

```bash
export DEEPSEEK_API_KEY=sk-xxx        # 仅从环境变量读取, 绝不硬编码
cd probes/deepseek-probe
python3 deepseek_probe.py             # 全用例, JSON 摘要到 stdout
python3 deepseek_probe.py --quiet     # 仅 PASS/FAIL 结论
```

凭据铁律：脚本绝不硬编码 key，输出中的 key 一律脱敏（`sk-7fc…1f6b`）。

## 覆盖用例 (v0.21.1)

| 用例 | 验证点 | 实测结论 |
|---|---|---|
| chat_deepseek_flash | 项目首选模型名即 DeepSeek 真实模型 | ✅ 接受, 返回 `reasoning_content` (推理模型) |
| chat_deepseek_chat | 非推理模型基线 | ✅ 接受, 无 `reasoning_content` |
| chat_deepseek_chat_with_reasoning_effort | 非推理模型收 `reasoning_effort` | ✅ 被接受 (无害忽略) |
| reasoning_effort_levels | deepseek-flash low/high 思考链长度 | ✅ 随档位增长 |
| chat_deepseek_reasoner | 历史推理模型 | 可用性随 DeepSeek 目录变动 |
| user_balance | balance_schemes.deepseek 端点 | ✅ 返回 `balance_infos[].currency=C NY` (注意: 非旧注 USD) |

## 关键发现 (驱动 v0.21.1 改进)

1. **推理模型思考链被丢弃** — 项目首选 `deepseek-flash` 是推理模型, 但
   `OpenAIChatResponseDtos.cs` 未解析 `reasoning_content`, 思考链整段丢失。
   → v0.21.1 已在 `OpenAIChatResponseMessage`/`QueueResponse`/`LLMResponse` 捕获并打 `reasoning_len` 遥测。
2. **余额币种注释错误** — `models.yaml` 旧注 "USD", 实测为 **CNY** (`balance_infos[].total_balance`)。
   → 已校正注释。
3. **限流返回 401 非 429** — DeepSeek 对 chat/completions 速率窗口返回 401,
   项目 `OnTransientFailureAsync` 仅把 429 当可重试限流; 401 被当作鉴权硬失败不重试
   (观察项, 未改动 auth 语义 — 真实 401 须 fail-closed)。探针内置退避重试以规避该窗口。

> 探针内置 1.5s 调用间隔 + 对 401/429/5xx 的指数退避重试, 规避 DeepSeek 对该 IP 的速率窗口。
