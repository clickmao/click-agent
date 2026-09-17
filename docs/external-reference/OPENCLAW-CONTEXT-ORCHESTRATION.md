# 外部参照面 · OpenClaw 的「上下文 + 编排」机制（RF0001 采编）

> 采集日 **2026-09-18**；来源 = 官方文档站 `https://docs.openclaw.ai`（另核对镜像 `openclawlab.com/en/docs/...`，内容一致）。
> 本文只采**已发布文档**的事实，**未读 OpenClaw 源码**；机制名/配置键逐字保留，推断项标「推断」。
> 用途：给本仓「上下文编排能力」定外部对照基线（用户令：*关于上下编排能力参考 openclaw，重新阅读一次开发文档*）。
> 采集命令（可复现）：`web_extract https://docs.openclaw.ai/{concepts/context,concepts/system-prompt,compaction,concepts/session,concepts/memory,reference/token-use}`

---

## 0. 本轮重读的**本仓**开发文档（先对本仓，再对外部）

| 本仓文件 | 读到的关键事实 | 对本次对照的作用 |
|---|---|---|
| `docs/plans/RF0001-fable-aligned-development-plan.md`（121 行） | §3 KPI 六项（命中 ≥97% / 新算 prompt / 调用数 / completion / 前端 api / 质量）；§4 在版范围；§7 未闭合 5 条 | 对照的**判据源**；新候选必须落到 §3/§4/§5 |
| `src/agent/context/SessionBaseline.cs`（185 行） | §1..§11 分区常量前缀 + 工作区快照；纪律「按运行变化的材料只允许追加在尾部」；两槽缓存防串味 | 本仓已有「缓存边界」的实现，等价物 |
| `src/agent.modelqueue/PromptCacheKpi.cs` | `CacheUnitTokens=64`；`HitCeiling = (floor(P/64)−1)×64`；97% ⇒ 前缀 ≥4,224 tok（红线在 `PromptCacheRedline`） | 命中率的**算术口径**；压缩候选必须挂在此口径上 |
| `docs/architecture.md` §3.4/§3.5（468–660 行） | 「会话循环系统」+「Token 压缩系统（Summarization Engine）」为**设计描述** | 文档有、代码未接线 ⇒ 见 §2 第 5 行 |
| `src/agent.contextgradient/*`（592 行：`ContextGradientCompressor.cs` 286 + `DriftGuard.cs` + `CompressionBreaker.cs` + `MessageRelevanceScorer.cs` 119） | L0–L3 规则压缩 + 锚词/语义漂移防护 + 熔断 | **只被 `Program.cs:190` 的「压缩底座 audit」与测试消费** ⇒ 未进主链（挂载类缺口） |
| `src/agent/intent/TaskOrchestrator.cs`(512) / `src/agent/registry/TaskPlanExecutor.cs`(691) / `src/agent/r1/PlanExecutor.cs`(146) / `src/agent/subagent/*` | 节点级编排（本地/远端）+ 计划 DSL + 子代理池 | 「上下（主从）编排」的本仓现状面 |
| `src/agent/context/SessionInjectionPlanner.cs` / `LocalSessionCacheLedger.cs`(163) | 会话注入规划 + 本地会话缓存台账 | 运行期装配面 |

---

## 1. 外部机制（OpenClaw，逐条带来源）

| # | 机制 | 事实（逐字要点） | 来源页 |
|---|---|---|---|
| M1 | **显式缓存边界** | 「Large stable content (including Project Context and static Memory Recall instructions) stays **above the internal prompt cache boundary**」；易变段（UI Presentation / Messaging / Runtime / Project Memory facts / delegation mode / elevated level…）「are **appended below that boundary**」；provider 插件可注入 `stablePrefix`（边界之上）/ `dynamicSuffix`（边界之下） | `concepts/system-prompt` |
| M2 | **运行期载体（不破历史前缀）** | `<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>…<<<END_OPENCLAW_INTERNAL_CONTEXT>>>` 承载「该 user 请求的运行时事实」（活跃 exec 会话/子代理/媒体进度）；「Each available capability emits a current snapshot, including `none` when empty, which **supersedes older snapshots**」；exec/子代理事实走**更晚的** Runtime Context carrier「to preserve the conversation-history prefix too」 | `concepts/system-prompt`、`concepts/context` |
| M3 | **上下文记账面** | `/context list`（per-file raw vs injected、截断、skills/tools 体积）、`/context detail`（+ 每工具 schema 大小、每技能条目大小、可压缩消息数）、`/context map`（treemap 图）、`/context json`；「prefers the latest **run-built** system prompt report」，估算只作回退；**不 dump 全文** | `concepts/context` |
| M4 | **预算/上限（字符级 + 窗口比例级）** | `bootstrapMaxChars` 20,000/文件、`bootstrapTotalMaxChars` 60,000 总计；`skills.limits.maxSkillsPromptChars`；`contextLimits.memoryGetMaxChars`/`postCompactionMaxChars`；工具回执上限随窗口 `16000`(<100K) / `32000`(100K+) / `64000`(200K+) 字符，且「single tool result at 30% of the context window」；图像 `imageMaxDimensionPx` 默认 1200 | `reference/token-use`、`concepts/context` |
| M5 | **压缩（compaction）= 持久摘要条目 + 保留尾部** | 旧轮「summarized into a compact entry」，摘要**写入 transcript**；压缩后模型看到 = 摘要 + `firstKeptEntryId` 之后的消息；「keeps assistant tool calls paired with their matching `toolResult` entries…moves the boundary so the pair stays together」；**全文仍留盘**，「Compaction only changes what the model sees on the next turn」 | `compaction`、`reference/session-management-compaction` |
| M6 | **压缩触发与参数** | 自动压缩默开：接近窗口上限 **或** 收到 provider 溢出错误后「compacts and retries」（识别 `request_too_large` / `context length exceeded` / `input exceeds the maximum number of tokens` / `input is too long for the model` / `ollama error: context length exceeded` 等）；`reserveTokens` 默认 16384（嵌入运行安全下限 **20000**）；手动 `/compact` 用 `keepRecentTokens`（默认 20000）作切点预算；`maxActiveTranscriptBytes` 作盘上体量闸 | `compaction`、`reference/session-management-compaction` |
| M7 | **压缩前记忆冲洗（memory flush）** | 阈值前置：监控上下文用量，越过软阈（`softThresholdTokens` 默认 **4000**）「run a silent agentic turn that writes durable state to disk」，`NO_REPLY` 抑制用户可见输出；每压缩周期一次，只对嵌入会话生效，工作区只读则跳过；`sessions.json` 记 `memoryFlushAt` / `compactionCount` | `reference/session-management-compaction` |
| M8 | **记忆分层（注入面 vs 检索面）** | `USER.md`（小预算、会话起加载）/ `MEMORY.md`（durable、会话起加载，超预算**只截断注入副本、盘上不动** + 注入「被截断」通知）/ `memory/YYYY-MM-DD.md`（日注，**不进 bootstrap**，`memory_search`/`memory_get` 按需）/ `DREAMS.md`（人审面）；`dreaming` 后台把短期提升进 `MEMORY.md` | `concepts/memory` |
| M9 | **提示词模式分级** | `promptMode` = `full` / `minimal`（子代理用：省掉记忆提示、模型别名、用户身份、消息面、折叠细节、静默回复段） / `none`（仅身份行）；子代理只注入 `AGENTS.md` | `concepts/system-prompt` |
| M10 | **缓存保温** | 模型参数 `cacheRetention: "long" \| "none"`，配合 `heartbeat: every "55m"` 保持 1h 前缀缓存常热；「`alerts` 代理用 `none` 避免突发通知的缓存写」 | `reference/token-use` |

---

## 2. 逐条对照（本仓现状 = 代码证据）

| 维度 | OpenClaw | 本仓现状（文件/读数） | 判定 |
|---|---|---|---|
| 缓存边界 | M1 显式边界 + provider 两段注入 | `SessionBaseline` §1..§11 恒定前缀 + 尾部追加纪律 + `PrefixSha256Pinned` + `PrefixMinCharsForCache97` 门 + 实测 **97.37%** | **本仓更强**（有量化 KPI 与加厚门）；缺口 = 无「段→寿命→缓存侧」清单机检 |
| 运行期事实 | M2 专用载体块 + 快照取代 + 空则 `none` | 尾部追加 + 前端 `last_item` 快照（R538）；无统一载体块/取代语义 | 可补（低成本） |
| 记账面 | M3 `/context` 四视图 + `/usage` | 仅 `PromptCacheKpi` 计数 + `data/telemetry/host.jsonl` | **缺**（读侧零风险，可先补） |
| 上限 | M4 文件级/总计/工具回执/窗口比例 | 记忆 ≤400 tok、RAG ≤120、里程碑 ≤2（`SessionInjectionPlanner` 侧）；无工具回执字符上限、无窗口比例上限 | 部分缺 |
| 压缩 | M5/M6 阈值触发 + 摘要条目 + 成对边界 + 溢出签名重试 | `ModelCatalogEntry.ContextWindow` 仅字段；`ContextGradientCompressor`(286 行, L0–L3 + DriftGuard)**未进主链**（只被 `Program.cs:190` audit 与测试用）；`architecture.md §3.5` 仅有设计图 | **最大缺口**：设计有、代码未接线、无触发策略 |
| 记忆冲洗 | M7 阈值前置静默写盘 | `AGENTFRAMEWORK_THINK_MEMORY` 开关 + 记忆写入工具；无阈值/无每周期一次语义 | 需先有压缩 |
| 记忆分层 | M8 四层 + 检索优先 | 记忆 ≤400 tok（可注入面）+ RAG ≤120；无日注层、无按需检索工具面 | 部分缺（不影响命中率） |
| 子任务上下文 | M9 `minimal` 白名单 | `IsolatedTaskRunner` 独立会话 + 纪律仅动作环分支注入；无「子任务上下文白名单」机检 | 可补 |
| 缓存保温 | M10 `cacheRetention` + 心跳 | 无；实测**首调用 89.0%**（冷起） | 可直接吃 KPI（见 C4） |

**核心张力（本次对照最重要的结论）**：M5/M6 的压缩会**重写历史中段** ⇒ 与「恒定前缀 + ≥97% 命中」在算术上**互斥**：压缩点之前的字节若变化，其后所有缓存全部失效。故本仓采纳压缩时必须**缓存对齐**：
1. 压缩只允许发生在**离散边界**（一个 `compaction` 条目），一旦写入即冻结、其后不得再改（等价于「前缀只允许加厚」的推广）；
2. 压缩造成的**冷启动调用单列**（对照现有的「首调用 89.0%」口径），**不计入** 97% 的稳态命中口径；
3. 压缩前后的成本对比必须给**同窗**读数，禁跨轮相减。

---

## 3. 采纳候选（按 KPI 收益/风险排序）

| 候选 | 动作 | KPI 影响 | 前置条件 | 判据（可机检） |
|---|---|---|---|---|
| **C1 缓存对齐压缩** | 给会话循环加压缩：阈值触发（`reserveTokens` 等价项 ≥ 窗口 20% 或收到溢出签名）+ 摘要条目 + 保留尾部（`keepRecentTokens` 等价项）+ 工具调用/结果成对边界 | 长会话从「必崩」变「可续」；稳态命中率不变，冷启动 1 次/压缩周期 | 先接线 `ContextGradientCompressor`（或其替代）到主链；定义压缩条目格式 | 压缩条目写入后字节冻结（sha 断言）；成对边界机检；溢出签名表机检；同窗对照含冷启动单列 |
| **C2 上下文记账面** | `--context-report`：段→字符/token→缓存侧（前缀/尾部）→截断标记→工具 schema 体积；优先用**真跑**报告，估算只作回退 | 直接服务 §3 KPI 表（前缀 6,704 tok 的可解释分解） | 无（读侧重） | 报告与 `PromptCacheKpi` 同源；前缀段合计 == `PrefixChars`；截断标记与实际注入一致 |
| **C3 运行期载体块** | 定义 `<runtime_context>` 载体：快照取代语义、空则显式 `none`、只追加尾部 | 不破命中；减少「易变项混进前缀」的回归风险 | 契约渲染器同步 | 机检：前缀区无运行期事实；载体只在尾部；同一事实两次快照后者胜 |
| **C4 缓存保温** | 空闲超 TTL 前发一次廉价静默调用保前缀热（`cacheRetention` 等价：TTL 内复用） | 直接改善**首调用 89.0%** 的冷起损失 ⇒ 拉高整体命中率 | 需与「静默不打扰」（前端不出现条目事件）合流 | 保温调用零用户可见事件；冷/热两态命中率同题对照（reps≥3） |
| **C5 子任务上下文白名单** | 子任务注入面收窄为白名单（等价 `promptMode=minimal`） | 降新算 prompt（子任务侧） | 现 `IsolatedTaskRunner` 面 | 机检：子任务前缀 ⊂ 白名单段集合 |

**不采纳/顺延**：`/context map` 图形化（无头环境，顺延 RF0002）；`dreaming` 提升与 `DREAMS.md` 人审面（无对应资产，顺延）；`context-engine` 插件槽（本仓单实现足够，v1 不做抽象层——与「可以合并的合并、没用的砍」一致）。

---

## 4. 诚实边界

1. 只读**文档站**，未读 OpenClaw 源码；版本键名可能随其版本漂移（采集日 2026-09-18）。
2. M5/M6 的默认值（`reserveTokens` 16384 / 下限 20000 / `keepRecentTokens` 20000 / `softThresholdTokens` 4000）是**其**取值，本仓须按自身窗口（远端 `deepseek-chat` 目录窗口 + 本地 512 tok 通道）重定，不得照抄。
3. 本仓「压缩」现状判定（未进主链）依据 = 消费点 grep（`Program.cs:190` + tests）；若主链经反射/配置间接消费，本文结论需重核。
4. 本轮**零产品代码改动、零 LLM 调用**：以上均为设计候选，未产生新 KPI 读数；`g1`/codex 对照等未闭合项不受本文影响。
