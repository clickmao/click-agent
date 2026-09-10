# 本地 LLM 推理 worker 化评估 (v0.20.1 P4-b, R344)

> 背景: v0.20.0 已将 **bge 嵌入** 独立进程化 (manager/worker, 卸载=kill worker)。用户动因原文:
> "将 llm 服务写成单独进程, 以免新 CLI 重新加载 LLM 到显存内" — "LLM" 不止 bge, 还包含本地推理模型 (qwen 等 gguf)。
> 本评估回答: 推理也 worker 化需要解决什么, 建议怎么分期。

## 1. 现状代码事实

| 组件 | 位置 | 加载时机 | 说明 |
|---|---|---|---|
| LocalLlamaCaller | `src/agent.modelqueue/` | CLI 进程内, 首次调用 | LLamaSharp 推理 (gguf) |
| LocalInferenceAdapter | `src/agent/extensions/ServiceCollectionExtensions.cs` L248+ | DI 构建 | `IsAvailable=false` → 诚实降级 (不伪造) |
| AGENTFRAMEWORK_LOCAL_DISABLED=1 | 环境变量 | — | 批测禁用本地模型 (XL 无此变量则 EXIT 124 历史) |
| BgeEmbedder | llamalocal | 惰性 + 双检锁 | 已被 v0.20.0 worker 化 (embed 协议) |

## 2. 与 bge 的关键差异 (决定不能照抄)

| 维度 | bge embed (已落地) | LLM 推理 |
|---|---|---|
| 请求/响应 | 单次请求-响应 (无状态) | **流式逐 token** (CLI 增量渲染) |
| 会话状态 | 无 | **KV cache / 多轮上下文** (复用=性能关键) |
| 单请求成本 | ms 级 | 秒~分钟级 |
| 并发 | embed 串行门即可 | 需会话隔离/队列 |
| 内存 | ~150MB | GB 级 (卸载更值得, 也更痛) |
| 卸载后再加载 | 秒级 | 十秒~分钟级 (lazy 代价高) |

## 3. 方案设计 (建议分期)

### 一期: 无状态补全 (最小闭环)
- 协议扩展: `{"op":"complete","messages":[...],"max_tokens":N}` → 响应 **NDJSON 流**
  `{"delta":"..."}` × N → `{"done":true,"tokens":K}` (或 `{"error":...}`)
- manager 透传 (行级代理改造为流式转发: 逐行读→逐行写 ✓ 现有结构可扩展)
- 客户端: `RemoteLlmClient` (非 ITextEmbedder 接口; 对应现有本地推理调用点)
- 会话连续性: **不做** (每请求携带完整上下文; KV 不复用) — 换来实现简单 + 无状态安全
- 收益: CLI 进程免加载推理模型 (GB 级); 多 CLI 共享一份
- 代价: 每请求重复 prefill (上下文越长越慢) → 对短上下文场景可接受

### 二期: 会话化 (条件触发)
- 协议加 `sessionId`; worker 端 `ConcurrentDictionary<sessionId, LLamaContext>` + LRU 上限 + 空闲过期
- 需解决: 会话所有权 (CLI 崩溃 → 会话回收)、多 CLI 会话隔离、context 大小上限
- 触发条件: 一期上线后实测 prefill 重复成本占比高 (> 30% 总时长) 才做

### 卸载策略 (与 bge 不同, 更保守)
- 推理模型内存远大于 bge → 卸载收益大; 但重载慢 → 阈值/空闲窗应更宽
- 建议: 复用 manager 判定, 但 env 分档: `..._INFER_MEM_FLOOR_MB` (默认更大, 如 2048) + 空闲窗可选
- 用户钦定语义 ("不按时间, 仅资源紧张 ∧ 无 CLI 实例") 同样适用; 推理 worker 可与 embed worker 分离或共存 (共 worker 分 op)

## 4. 风险与未知 (诚实标注)

1. **流式协议与 agent.io 关系**: 现有 IO 通道 (SharedMemoryChannel/SocketChannel) 是前端侧协议; 推理流走 llm-service UDS 内部协议 — 二者不冲突但需明确边界 (待确认)
2. **token 统计/KPI 打点归属**: 推理在 worker 进程, 打点回传方式未定 (可随流末 `{"done":true,"tokens":K}` 回传)
3. **AOT**: LLamaSharp 推理链已在 AOT 下验收 (本地模型 smoke), worker 侧同样发布形态 → 风险低
4. **批测规则冲突**: 批测 `AGENTFRAMEWORK_LOCAL_DISABLED=1` 禁本地模型 — 推理 worker 化不影响批测口径 (默认 remote 也需显式 opt-in)
5. **多模型**: 不同任务用不同 gguf → 当前 manager 单 worker 单模型假设需扩展 (按 model 键管理)

## 5. 结论

- **建议**: 一期 (无状态流式补全) 可在用户确认后实施; 二期 (会话化) 待实测数据触发
- **前置**: 用户对"流式协议形态""卸载阈值分档""是否与 embed 共用 worker"三个决策点确认
- **不做**: 不修改现有本地推理默认路径 (opt-in 原则; 与 P4-a 一致)
