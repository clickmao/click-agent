# 外部参照面 · ZCode（Z.ai 编码 agent harness）的「上下文装配 / 治理闸 / 用量口径」机制

**性质**：只读源码参照（RF0001 采编面）。**零 `src/` 改动 · 零夹具 · 不占主线轮次**（同 RF0006 口径）。

| 采集事实 | 值 |
|---|---|
| 仓库 | `github.com/zai-org/ZCode`（`Z.ai's coding agent harness`） |
| HEAD | `872ad960de7ec172591f7e1952f7849229f94521`（提交题 `feat: open source`） |
| 采集日 | 2026-09-21（开源日 2026-09-20，距今 1 天） |
| 许可 / 规模 | Apache-2.0 · TypeScript · 包树 7,364 blobs（`packages/` 4,920 + `apps/` 1,493 + `.agents/` 240） · 3,329 stars |
| 取件方式 | **未 clone 全库**（`git clone --depth 1` 300 s 超时）⇒ GitHub `git/trees?recursive=1` + 逐文件 raw（**46 件**）快照于 `/tmp/zcf/`；**行号基于该快照** |
| 未做 | 未编译其 TS、未跑其测试 ⇒ 下列全为**机制假设**，不是对其行为的实测断言 |

## 0. 本轮重读的**本仓**文档与代码（先对本仓，再对外部）

| 本仓 | 读到的事实 | 作用 |
|---|---|---|
| `docs/external-reference/OPENCLAW-CONTEXT-ORCHESTRATION.md` | 上一次外部参照（缓存边界 / 压缩 / 记账面 M1–M10 + 候选 C1–C5） | 本次**沿用同一表格形态**，避免重复采编同族机制 |
| `src/agent/context/SessionBaseline.cs`（185 行）· `SessionInjectionPlanner.cs`（212 行） | §1..§11 恒定前缀 + 工作区快照 + 注入规划 | 对照「段声明契约」的**本仓现状面** |
| `src/agent.modelqueue/PromptCacheKpi.cs:80` | `CacheUnitTokens = 64`（命中率算术口径） | 候选必须挂在此口径上 |
| `src/agent.modelqueue/ActionLoopRunner.cs:15` | `public const int DefaultMaxSteps = 6;`（`:78` 为其消费点） | 对照「不用 tool call 次数做硬停止」 |
| `tools/roundcheck/roundcheck.py:184-365` | `R0_registry / R1_registry_row / R2_commit_unique / R3_evidence_present / R4_pin_matches / R5_doc_shape / R6_commit_hygiene / R7_no_secret_in_commit / R8_readings_backed / R9_staged_hygiene / W1_secret_in_worktree` | 对照「架构治理闸」的**本仓同族件**（形态最接近，故对照最有信息量） |
| `git grep -n "cacheHint\|injectionTarget" -- src tools docs` | **0 命中** | ⇒ 「段→注入目标→缓存寿命」声明形态本仓**确实缺失**（不是遗漏检索） |
| `src/agent.contextgradient/*`（9 件 / 989 行，含 `ContextGradientCompressor` 286 行） | L0–L3 规则压缩 + DriftGuard，**未进主链** | 对照 M8「本地零 LLM 压缩」的落点 |

## 1. 外部机制（ZCode，逐条带来源；行号 = `/tmp/zcf/` 快照）

### A. 上下文装配面（对我们「合理时机插入 + 不破缓存」焦点令）

| # | 机制 | 逐字 / 事实 | 来源 |
|---|---|---|---|
| M1 | **段声明契约** | `ContextSection` 每段带 `source` / `injectionTarget`（`system` \| `meta_user`）/ `cacheHint`（`stable` \| `dynamic`）/ `chars` / `tokens`；构造时 **默认 `injectionTarget="system"`、`cacheHint="dynamic"`**（`builder.ts:66-72`，即「不声明就按易变处理」，安全默认） | `core/src/context/types.ts`、`builder.ts:66-72` |
| M2 | **装配序 = 四象限 + 缓存断点** | 装配恒为 `system/stable`（`cli_prefix` 独占）→ `system/stable`（其余 stable body）→ `system/dynamic`（前置 `\n\n` 左边界）→ `meta_user`（`skills` 等）；**三段各带 `cacheControl: {type:"ephemeral"}`**（`builder.ts:35,235-284`） | `core/src/context/builder.ts` |
| M3 | **前缀白名单闭合** | 提醒来源有 `channel`（`request_prefix` \| `current_turn` \| `tool_result` \| `history_continuity` \| `mid_turn_event` \| `real_user`）× `lifecycle`（`request_prefix` \| `per_current_turn` \| `runtime_local` \| `tool_result` \| `resume_history` \| `mid_turn_event` \| `real_user`）两轴；**只有 `context_prefix` / `skills_listing` 允许进 `request_prefix`**，其余一律走当轮 / 工具回执 / 中途事件 / 冷恢复 | `core/src/system-reminder/source.ts` |
| M4 | **提醒形态 fail-loud** | 正文含嵌套 `<system-reminder>` ⇒ throw；空正文 ⇒ throw；非 provider-visible 来源包壳 ⇒ throw；每条来源带 `evidenceLabel`（`sr.<source>`）、`isMeta`、`providerVisibility` | `core/src/system-reminder/source.ts` |

### B. 用量与压缩面（对我们 tokens / 命中率 KPI）

| # | 机制 | 逐字 / 事实 | 来源 |
|---|---|---|---|
| M5 | **段级用量归因** | 记账模型把每个 contributor（上下文段 / 工具 schema / 技能 / 消息角色）都记 `chars` / `tokens` / `tokenMethod` / **`confidence`** / `tokenizer` / `cacheHint` / `injectionTarget` / `sideEffectScope` ⇒ **成本可下钻到段/工具/技能** | `core/src/runtime/helpers/context-usage-breakdown.ts`、`context-usage.ts` |
| M6 | **压缩阈值口径 + 双口径 token** | `DEFAULT_AUTOCOMPACT_OUTPUT_RESERVE_TOKENS = 32_000`、`PREFLIGHT_… = 21_000`、`MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000`、`AUTOCOMPACT_BUFFER_TOKENS = 13_000`；阈值 = **窗口 − 输出预留 − 缓冲**；`AutoCompactTokenSource = "estimate" \| "provider_usage"`，决策同时携带 `estimatedTokenCount` 与 provider 用量（`policy.ts:9-13,28-45,101-104`） | `core/src/compact/policy.ts` |
| M7 | **压缩决策带枚举 reason + 熔断** | `reason ∈ {disabled, not_enough_messages, circuit_breaker, below_threshold, above_threshold}`；`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` ⇒ 连败即停手（防无限压缩） | `core/src/compact/policy.ts:14` |
| M8 | **microcompact（本地零 LLM 压缩）** | 只对**白名单工具**、按 assistant tool-call 轮成组清除旧回执为 `[Old tool result content cleared]`，**保留最近 5**；触发 `TimeBased`（空闲 >60 min）或 `TokenPressure`；**节省 < 256 tok ⇒ 回滚（不做）**；媒体结果**豁免**；输出结构化 payload（pre/post tokens、cleared/kept toolCallIds、strategy、trigger）+ 枚举 reason（`…below_min_savings/applied`）；纯函数 + 不改入参 | `core/src/compact/microcompact.ts` |

### C. 治理与 I/O 边界面（对我们 roundcheck / 闸族系 / AOT 纪律）

| # | 机制 | 逐字 / 事实 | 来源 |
|---|---|---|---|
| M9 | **单前台槽 + 租约** | 命令队列只有**一个前台执行槽**，后台/排队工作经 `acquireForegroundPromotionLease` 提升；全部命令带 AbortSignal；取消走结构化错误 | `core/src/runtime/methods/runtime-command-queue.ts` |
| M10 | **副作用声明 + 判定三值** | tool 声明 `readOnly` / `destructive` / `sideEffectScope` / `riskLevel` / `alwaysAsk` / `permissionCapabilityGroup`；判定结果 `PermissionDecisionResult{decision: allow\|ask\|deny, allowed, reason, ruleId, riskLevel, sideEffectScope, escalated, mode}` | `core/src/permission/service.ts` |
| M11 | **声明式架构政策 + 规则目录 + 差量 + 基线** | 规则名：`module-dependency` / `deep-import` / `cycle` / `max-file-lines` / `max-contract-lines` / `max-public-methods` / `layer-direction` / **`domain-io`**（domain 层禁 import process/network/fs/timer）/ `expired-exception` / `disable-count`（**新增抑制本身即违规**）；命令 `pnpm architecture:check --changed`（只查改动面）+ `pnpm architecture:context <module-id>`（**受控上下文阅读包**：只读目标契约 + 直接依赖契约 + spec + 测试）；违规基线 `.architecture-baseline.json = {version:1, violations:[]}`（**CI 不自动刷新**，例外必须带过期） | `.agents/skills/architecture-governance/{SKILL.md,references/rule-catalog.md,policy-schema.md,module-contract.md}`、`scripts/architecture/policy.mjs`、根 `AGENTS.md:22-25` |
| M12 | **AGENTS.md 宪法条**（逐字） | ①`长程任务优先：核心 agent loop 默认面向可持续运行的复杂任务设计，不用 tool call 次数做硬停止。资源与安全边界应由 token/context limit 自动 compact、用户取消、权限拒绝、工具超时、输出截断、provider retry 上限等明确条件承担。`（:11）②`单个源文件默认不能超过 400 行`（:12）③`不要随便新增环境变量；新增前必须先在对应功能的 spec 中定义用途、优先级、错误行为和测试覆盖`（:21）④`所有外部副作用必须可被统一观察、审批、取消、重试、排队、审计和测试。业务逻辑只表达意图，不直接触碰外部世界。`（:51）；`所有外部 I/O 都必须收敛到明确的基础设施层或 adapter 中`（:52）⑤`大体积 tool 结果不应直接回灌模型上下文；应落盘或进入 artifact/storage，只返回摘要、预览和可追踪引用。`（:65）⑥`所有任务执行都必须携带可传播的 traceId … 任何异步任务…如果无法关联到 traceId，都视为不可观测行为，应避免引入。`（:74-77） | `apps/zcode-cli/AGENTS.md`、根 `AGENTS.md:10,22-25,35-36` |

## 2. 逐条对照（本仓现状 = 代码证据）

| 维度 | ZCode | 本仓现状（file:line / 读数） | 判定 |
|---|---|---|---|
| 段契约 | M1/M2 每段带来源+注入目标+缓存寿命，且**默认按易变处理** | `SessionBaseline.cs`(185) §1..§11 恒定前缀 + 「只允许尾部追加」纪律；`git grep -n "cacheHint\|injectionTarget" -- src tools docs` = **0 命中** | **缺声明面**（纪律是文字级，不是可机检的段属性） |
| 缓存断点 | M2 三段 system 各带 `ephemeral` 断点 | `PromptCacheKpi.cs:80` `CacheUnitTokens=64` + 前缀 sha 冻结（`PrefixSha256Pinned`）+ 实测命中 ≥0.97 | 本仓**有量化闸**；缺「断点位置」显式语义 |
| 插入时机 | M3 前缀白名单闭合（只有两来源可进前缀）+ M4 fail-loud | 靠「只允许尾部追加」的纪律 + 人工评审 | **可机检性缺口**：无来源×生命周期矩阵，无 evidenceLabel 计数 |
| 用量口径 | M5 段/工具/技能级归因 + tokenMethod + confidence | 仅 `PromptCacheKpi` 计数 + `data/telemetry/host.jsonl` 打点；口径靠口径令（中继 dump 时间轴 / `v_all` vs `v_incr` / `cache_*`=末次值）人工执行 | **部分缺**（读数有、归因面无） |
| 压缩 | M6/M7/M8 阈值+熔断+本地 microcompact（含「省不够就不动」） | `src/agent.contextgradient/*` 989 行**未进主链**（只被 audit 与测试消费）；无阈值/无熔断/无最小节省阈值 | **最大缺口**（与 OPENCLAW 对照结论一致，未变） |
| 架构闸 | M11 声明式政策 + `--changed` + **基线台账（例外带过期）** + `disable-count` + `domain-io` | `tools/roundcheck/roundcheck.py` R0–R9 + W1：**全树固定规则、无差量、无基线、无过期例外** ⇒ 已知 1 红（`config/base/models.yaml` 的 env 名引用被 R7 扫到）**每轮如实报红** | **同族件、缺三个机制**（差量/基线+过期/抑制计数） |
| 副作用边界 | M10 声明 + 判定带 `ruleId/reason/escalated` | `src/agent.files` = 唯一写盘入口（备份 fail-closed / 竞争不写盘 / 三方合并，R584）但**未接产品路径**；闸族系判定散在调用点 | 方向**同源**（我们已先做唯一入口）；缺「声明缺失即违规」 |
| 队列/串行 | M9 单前台槽 + 租约 | 单 `llama-server` + 2 vCPU，串行靠 `pgrep` 检查 + 人工排轮 | 可补（低成本） |
| trace | M12 traceId 树（>sessionId>turnId>messageId>toolCallId） | 平铺 `request_id`（「调用数按 request_id 去重」） | **口径痛点的正主**：无父子链 ⇒ 重试归属只能靠中继 dump 时间轴人工对齐 |
| 步数边界 | M12① 不用 tool call 次数硬停止 | `ActionLoopRunner.cs:15` `DefaultMaxSteps = 6`（`:78`） | **相反**（我们是硬停止）⇒ 见 §3 不采纳理由 |

## 3. 采纳候选（四元组；**均未实施**）

| 候选 | 动作 | KPI 影响 | 前置条件 | 判据（可机检） |
|---|---|---|---|---|
| **C1 段声明契约 + 前缀白名单** | 给 `SessionBaseline`/`SessionInjectionPlanner` 的每段加 `{source, injectionTarget, cacheHint, chars, tokens}`；前缀只允许白名单来源；默认按易变处理 | ⑥ 恒前缀 ≥0.97 不破的前提下，为「精排/插入」提供**安全落点** | 首轮**只声明+打点、不重排**；冻结前缀 sha 不动 | 同窗对照 `v_all`/`v_incr` 不降 ∧ 前缀 sha 不变 ∧ 每条插入带 `evidenceLabel` 且可在遥测按面计数 |
| **C2 段级用量归因面** | `--context-report` 等价物：段→chars/tokens→缓存侧→截断标记→工具 schema 体积；优先真跑报告，估算作回退 | ⑤ tokens 可解释分解（前缀 15,291 chars 的逐段账） | 无（只读） | 段合计 == `PrefixChars`；`tokenMethod` 与 confidence 每行必带；负控 = 人为改一段 ⇒ 报告与 sha 同步变 |
| **C3 压缩落主链（阈值+熔断+最小节省阈值）** | 接线 `src/agent.contextgradient/*`：阈值 = 窗口 − 输出预留 − 缓冲；连败 3 次熔断；白名单工具 + 保留最近 N + **节省低于阈值就不动** | 长会话可续；稳态 tokens 不升 | 先有 C2 记账面 | 压缩条目 sha 冻结；成对边界机检；`reason=below_min_savings` 路径可复现（省不够⇒字节不变） |
| **C4 roundcheck 加差量 + 基线 + 过期例外** | `--changed` 只扫本轮面；违例基线台账（CI 不自动刷新）；例外必须带过期轮号；新增抑制即违规 | 形式门禁可**如实**消化已知 1 红（进基线+带过期），不凑绿 | 无 | 负控：人为加一条违规 ⇒ 红；入基线 ⇒ 只在 baseline 单列、rc 不变；过期未清 ⇒ 红 |
| **C5 工具副作用域声明 + 大回执落盘** | 工具/端口声明 `sideEffectScope`/`readOnly`/幂等；回执超阈值 ⇒ 落 artifact + 摘要 + 引用句柄 | 闸族判定可机检；tokens 降（大回执不进上下文） | 与 `agent.files` 唯一写盘入口合流 | 声明缺失 = 违规（不得默认 `none`）；超阈回执必带 artifact 句柄 |
| **C6 traceId 树** | 统一父子链（trace > session > turn > message > toolCall）；无法关联 ⇒ 视为不可观测 | ⑤ 调用/命中率口径可信 —— 直接治「`transcript.calls` 低估重试」 | 与中继 dump 时间轴对齐 | 重试/子会话归属可机检；孤儿 span 数 == 0 |

## 4. 不采纳 / 暂不采纳（带理由）

| 项 | 理由 |
|---|---|
| M12①「不用 tool call 次数做硬停止」立即改 | `ActionLoopRunner.cs:15` 的 6 步硬边界是**已验收**的；当前步数中位 7（未恶化）且本机 3.6 GiB / 2 vCPU。先改会把无界循环风险引入 = 预防性机制轮（违主线纪律）。**留候选，须先有 C3 的资源闸 + C6 的观测面** |
| M12② 单文件 ≤400 行 | 属结构性重构（`IndustrialAgentV2.cs` 远超）；「不许新增夹具和额外开发」令下不做，登记候选 |
| `knip` / `dep:refs` | Node 生态工具，不引入（语言无关令）；只取「导出引用查询」理念入候选 |
| `meta_user` 具体 tag 名 / `DESIGN.md` UI 规范 / provider 权限细节 | 本仓无 UI 主体、runtime 不同 ⇒ 不搬 |
| microcompact 的 `TimeBased`（空闲 60 min）触发 | 本仓无「空闲会话」稳态，先只取 `TokenPressure` 支 |

## 5. 诚实边界

1. **只读源码参照**：未 clone 全库（超时），按 raw 逐件取 **46 件**于 `/tmp/zcf/`；**行号基于快照**，未编译其 TS、未跑其测试 ⇒ 全部为**机制假设**，不可当实测结论引用。
2. **零实施**：本轮未改任何 `src/`、未新增夹具、未跑真机 ⇒ **没有任何 KPI 读数被移动**（文献环令：候选须真机改 KPI 才算实施）。
3. **同仓并发**：本轮检测到**兄弟轮 R615 在飞**（`$HOME/.agentframework/harness/runs/r615/` 在跑 + `src/agent/r1/*`、`src/agent/contract/StructuredPrompt.cs` 等工作区改动在飞）⇒ 按「同仓并发纪律」**未写共享台账（`docs/research/lit-review-ledger.md` 正被对侧修改）、未提交**。
4. **待补一步**（R615 收口后执行）：①`docs/research/lit-review-ledger.md` 追加 R6xx 增量（采集日 / 检索面 = 仓库源码非 arXiv / 采信 6 条 / 反空转计数 / 代码证据）；②`git add -- docs/external-reference/ZCODE-AGENT-HARNESS.md docs/research/lit-review-ledger.md && git commit`（逐名，禁 `-A`；`PUSH_PAUSED` 在位，不 push）。
