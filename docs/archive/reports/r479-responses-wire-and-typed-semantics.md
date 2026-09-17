# R479 报告：Responses 真实 I/O 数据格式 + 内部精准语义 + 工具声明面单源

- 状态: 已完成
- 轮号: R479（承 R478 `55bc525`）
- 计划: `docs/plans/v0.95.0-r479-responses-wire-and-typed-semantics.md`
- 判据面: `eval/rover/r479/{check_r479.py, verdict-r479.json, prereg_r479.json}`
- 源码: `src/agent.modelqueue/{ResponsesWire.cs, LocalDecisionMap.cs, ActionToolSpec.cs}`
- 单测: `src/agent.tests/ResponsesWireTests.cs`（A–F）
- 台账: `docs/verification-registry.json`（+3 行 r479.*）、`docs/plans/v715_dev_plan.taskplan.json`（+`dev-r479-*`）

## 1. 用户口径 → 落点

| 用户口径（逐字） | 落点 |
|---|---|
| 「不应该是入链 prompt 本身就是结构化的么…用户输入 prompt 是个单独的字段，而不是说你传输过去的是 json 就是结构化语义了」 | `ResponsesWire.BuildRequest`：`instructions`（本地指示/权限类）与 `input[]`（用户输入）**两个独立顶层字段**；输入项 typed，工具结果独立成 `function_call_output` 项，不拼进 user 文本 |
| 「利用好 Responses API 来设计你真实的输入输出数据格式」 | 请求手写 JSON（零反射/AOT）、恒 `store:false`、可选 `prompt_cache_key`/`max_output_tokens`；响应 `JsonDocument` 解析（typed item），usage 未上报 **≠ 0** |
| 「设计自己内部用到的精准语义（校准 llm 返回后本地应该做什么…包括本地 llm 也是）」 | `LocalDecisionMap.FromResponses`：**单一出口**，本地与远端同用；规则只取协议字段、顺序即优先级、越界 fail-closed |

## 2. 真机读数（产品自建请求体字节，脚本不重建不修饰）

| 臂 | HTTP | input | cached | 新算 | out | reasoning | status | item | 判档 |
|---|---|---|---|---|---|---|---|---|---|
| 本地 answer-1 | 200 | 68 | 0 | 68 | 14 | — | completed | message | `Answer` |
| 本地 answer-2 | 200 | 68 | **67** | **1** | 14 | — | completed | message | `Answer` |
| 本地 tool-1 | 200 | 496 | 11 | 485 | 31 | — | completed | **function_call(read_file)** | `RunTools` |
| 远端 answer-1 | 200 | 78 | 0 | 78 | 128 | 111 | **incomplete / max_output_tokens** | reasoning+message | `Retry` |
| 远端 answer-2 | 200 | 78 | 0 | 78 | 128 | 128 | **incomplete / max_output_tokens** | reasoning | `Retry` |

- 本地二次同输入命中 67/68 = **98.5%**（与 R474–R477 的「前缀可控 ⇒ 命中可控」同源）。
- 远端 `reasoning_tokens` 吃满 128 预算 ⇒ `status=incomplete`；产品语义判 `Retry(LengthExhausted)`，与 R478「空正文定因只取协议字段」互证（远端 answer-2 `text_len=0` 且 `reasoning=128`，不再误诊为「推理占满输出预算」式猜测）。
- 本地 3B **原生发出** `function_call: read_file` ⇒ 声明面（`ActionToolSpec`）与执行面（`IWorkspaceActionPort`）可同协议对接。

## 3. 判据与结果

| 项 | 结果 |
|---|---|
| 焦点单测 A–F（含 F1 真机证据回放） | **21/21** |
| 器具 `check_r479.py` | **5/5 PASS**（C1 协议不变量、C2 真机端点、C3 文案单源、C4 声明面单源、C5 usage 未上报≠0） |
| 负控 NC1–NC3 | 用户任务文本混入 `instructions` / `store:true` / BOM ⇒ 判红 |
| 全量测试 | **1490/1490**（R478 的 1469 + 本轮 21） |
| 形式门禁 `VerificationFormTests`+`DevPlanDocRefTests` ×3 | **10/10 ×3 rc=0** |
| 台账 `apply_ledger_r479.py` | `--check` 前置判红（fail-closed 生效）→ `--apply` rc=0（registry 146→149、taskplan 46→47）→ 幂等复跑逐字节相同（`registry_idempotent=yes` / `taskplan_idempotent=yes`） |
| AOT 重发布 | `publish_rc=0` / `il_warnings=0` / `build_errors=0` / 15,363,712 B / sha16 `c8974f6b34dcc7b3` / `--version rc=0` |

## 4. 诚实边界

- **路由器接线未做**：产品默认通道仍是 Chat Completions；本轮交付的是「协议面 + 语义面 + 声明面」，切换属配置/接线动作，未改动默认行为（避免无对照的静默换道）。
- 远端 `cached=0` 两次：与本轮请求体规模（78 token 前缀）有关，**未**断言远端缓存命中能力（大前缀另测见 R479 前序探针 4394→4224 = 96.1%）。
- `previous_response_id` 三家均不可用（本地 llama.cpp 400）⇒ 历史仍由我方全量传，服务端无状态，R474–R477 真值口径不变。
- 入链正文槽位化（权限类本地指示内嵌 + 权限内容压缩）**未落**，列入 R480。

## 5. 下轮候选

1. **R480-A 索引/召回端口**：超多文件系统 + 超大文本的极小内存索引（mmap 只读倒排 + 块级文本 + 增量判脏），并作为动作环第 5 工具暴露；判据 = 规模梯度下的 recall@k 退化上界 / p50-p95 延迟 / 常驻 RSS 上界。
2. **R480-B 入链正文槽位化**：`instructions` 内嵌本地指示与权限压缩、用户输入独立字段的端到端接线。
3. **R480-C 路由器接线 + 同输入 A/B**：`IResponsesApiPort` 两实现，同网格同桩下测真值 tokens / 调用数 / 命中率 / 产物正确率。
