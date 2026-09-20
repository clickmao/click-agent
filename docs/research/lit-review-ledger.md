# 文献与最新方案 ⇒ 管线优化候选台账

> 用户令（2026-09-20 逐字）：「更新自检任务，增加查询相关权威论文和最新方案尝试优化agent管线」。
> 本档由能力自检循环**每轮追加**（禁整档回写：用 `io.open(..., 'a')`；改档后必须重算 pin）。
> 一条候选只有在**本仓真机单变量对照**下改动了 KPI，才算「已实施」/「已证伪」；论文本身只提供机制假设。

## 0. 口径与硬闸

- **反幻觉**：每条引用必须带 出处（arXiv ID **含版本** / DOI）+ **逐字引文片段** + 采集日；抓不到原文 ⇒ 记「未取到原文 ⇒ 不采信」。禁凭记忆写论文名/结论，禁把摘要当已证收益。
- **权威性代理（按强度）**：同行评审 venue > 预注册 + 安慰剂对照设计 > 公开代码/可复现 > 纯摘要。
  **引用数在本轮不可用**：试点 6 篇全为近月预印本，OpenAlex `cited_by_count = 0`；Semantic Scholar 无 key ⇒ HTTP 429。故本轮不得以引用量作权威性背书。
- **有效性判据只看本仓真机**：单变量 · 同窗 · reps≥3 · 预注册判据 · 外部真值（codex 同题面）。铁律 10/11。
- **预算**：≤3 检索式/轮、全文抓取 ≤2 篇、单次 ≤120s；arXiv 限流 ⇒ 检索间隔 ≥4s。
- **工具面（试点实测，已修）**：`~/.hermes/skills/research/arxiv/scripts/search_arxiv.py`
  - 缺陷：用 `urllib.parse.quote()`（空格→`%20`）拼 `all:` 检索式 ⇒ arXiv 把短语**拆散**为松散词项，实测 `all:"self-repair"` 返回 **1,289,248** 条无关结果（top 命中有 3D 视觉论文）。
  - 修法：改 `quote_plus()`（空格→`+`）+ 单次超时 15s→40s + 3 次退避重试（4s/8s）。修后同一检索式返回 **24** 条相关结果。
  - **结果数不是判据**：`Found N results` 与相关性无关，必须逐条读标题/摘要判定。

## 1. 台账

### L1【采信·高优先】自修复对照组缺「盲重采样」与「内容无关安慰剂」⇒ R600 机制归因可能被混淆

- 出处：arXiv:2607.26117v1（2026-07-28，cs.SE；预印本 + 公开代码/预注册/run traces）；arXiv:2607.12962v1（2026-07-14，cs.SE，54 页，预注册 + 安慰剂对照）；arXiv:2606.31511v1（2026-06-30，cs.SE，39 页）
- 逐字引文（2607.26117）：
  - "Self-repair - returning a failed program to the model together with its test output and asking for a correction - is a standard component of code agents, and is almost always evaluated against a baseline that does not retry at all."
  - "We argue that this comparison confounds the value of the feedback with the value of the extra attempt."
  - "Blind resampling is the strongest condition below 7B, and remains statistically tied with the best condition at 7B, while consuming 2.5-5.5x fewer tokens"
  - "the informational content of execution feedback adds nothing measurable over the placebo."
  - "when shown its previous attempt, a model reproduces a near-identical program in 33-68% of retries, against 2-14% under blind resampling"（归因：anchoring）
- 逐字引文（2607.12962）: "error content is paired with channel-specific placebos that keep the predeclared scaffold while ablating task-relevant content or deranging the task-error assignment."
- 逐字引文（2606.31511）: "small frozen code models are routinely asked to repair a failed program after seeing their own failing output, usually treated as a retry mechanism."
- 机制假设：**「重试本身（形式）」与「回灌内容（内容）」被混淆**；在小模型（<7B）上，把上一次失败产物再喂回去可能通过 anchoring 压低多样性，反而有害。
- 改哪一格 KPI：**质量（J4 能力面）+ 成本**（论文报告盲重采样省 2.5–5.5× token）。
- 单变量轴 + 判据（下一轮）：在既有跑臂配置上**只加两个对照臂**（零产品改动、不加夹具）——
  ① `BR` 盲重采样臂（同 prompt 重试，不带任何失败信息）；② `P` 安慰剂臂（带**格式相同但内容无关**的块）。
  判据：若 `T(带现状)` 相对 `C(轴关)` 的收益 ≤ `P` ⇒ **R600 的「带现状⇒收敛」归因不成立**，改归因「重试/形式」；若 `T > BR` 且 `T > P` ⇒ 内容有效。**预注册证伪点**：`T ≤ P` 即判 L1 采信→R600 机制归因需撤回。
- 状态：**候选**（待下一轮真机 A/B；跑臂成本约 ×1.5–2 token，须并入同轮预算）

### L2【采信·口径与机检】前缀连续性 = 成本硬约束；token 数 ≠ 端到端成本

- 出处：arXiv:2606.17016v2（**EMNLP 2026 Findings**，2026-08-28 更新）；arXiv:2607.12161v5（2026-08-12 更新，cs.CL）
- 逐字引文（2606.17016）：
  - "Existing approaches utilize text pruning or dynamic memory eviction to minimize token footprints; however, their unconstrained sequence mutations alter layouts, introducing prefix mismatches and cache invalidation."
  - "This reveals a critical trade-off between text sparsity and prompt cache continuity."
  - "Globally, Ingestion-Aware Compaction acts as a framework harness to stabilize prompt prefixes"
- 逐字引文（2607.12161）: "token count alone does not determine end-to-end inference cost."
- 机制假设：剪枝/驱逐/注入若**改变序列布局**，前缀失配 ⇒ KV 缓存失效 ⇒ 省下的 token 被重算抵消。
- 改哪一格 KPI：**命中率**（恒前缀 ≥97%）+ 成本口径。
- 单变量轴 + 判据：任何「上下文注入 / 精排 / 剪枝」变更 ⇒ 机检**前缀字符数 + sha 必须不变**（`R1Transcript` 已有前缀打点；R580 尾部可变区注入已满足）；成本列继续用 `v_incr` + 命中率，**禁以名义总 token 作成本**。
- 状态：**候选（口径确认 + 机检断言复核）**；与本仓现状一致，作为 R580/精排 KPI 的外部依据。

### L3【采信·判定卫生】同源 oracle：补丁与测试由同一轨迹产出 ⇒ 假信心

- 出处：arXiv:2609.09133v1（2026-09-08，cs.AI/cs.CL/cs.SE，35 页，代码公开 github.com/MSR-Orchard/execcritic）
- 逐字引文："Agent-generated tests can encode incomplete or incorrect behavioral targets; when the same trajectory writes both the patch and the test, their errors can agree and create false confidence."
- 机制假设：失败判定若由**与产物同源的探针**给出，误差相关 ⇒ 判定失效（与本仓「夹具 vs 能力缺陷须**非同源** oracle 判」同构）。
- 改哪一格 KPI：**质量**（避免假绿；也影响 rc 语义收口）。
- 单变量轴 + 判据：失败臂判定必须由**外部 oracle**（题面公开用例 / codex 真值 / 独立探针）给出；若某轮判定只依赖产物自带测试 ⇒ 该窗判 `unreliable`，不计入配对。
- 状态：**候选（判定卫生，随下一轮判据收口一起落地）**

### 观察项（不采信，留档）

| 出处 | 逐字引文 | 为什么不采信 / 何意味 |
|---|---|---|
| arXiv:2606.13126v1 MiniPIC（2026-06-11） | "prefix caching in engines such as vLLM cannot reuse their KV entries unless they share identical prefixes with another request" | 位置无关 KV 复用属**引擎侧**（需控制 KV 布局）；本仓远端 LLM 走 API、本地 llama-server 不可编程 ⇒ 本轮不可落地 |
| arXiv:2605.30574v1（2026-05-28） | "We ask when and what kind of redundancy: at which layers, after how many decoding steps" | 层/步级 KV 冗余探测；需引擎内部可见性，观察项 |
| arXiv:2607.29678v3 TokTier（2026-08-06） | "sessions repeatedly submit a long transcript after a small append, which can shift token boundaries near the end of the prior sequence" | 追加导致**近尾部 token 边界漂移** ⇒ 与 R580 尾部注入同风险面；本轮只作机检提示（前缀内容不变即安全），不新增件 |
| arXiv:2609.16604v1 ExecuCritic（**NeurIPS 33rd**，2026-09-15） | "an entire program is often reduced to one pass or fail bit" | 失败位→细粒度 critic 信号 ⇒ 与本仓「失败回灌补闸数据加强 nlp」同向；需训练/critic 件，超本轮预算，留作 v2 |
| arXiv:2609.11677v1 Ecdysis（2026-09-10） | "Self-evolving runtime harnesses can substantially improve the capabilities of large language model (LLM) agents" | 运行期 harness 自演化 ⇒ 与「运行期自升级、非开发期预制」令同构；机制来源，观察项 |

## 2. 采信候选的代码证据对照（file:line）

- L1 相关（逐行核对过）：`src/agent/r1/R1Options.cs:35`（`bool ArtifactCarryoverEnabled = true`）；`src/agent/r1/R1Pipeline.cs:321`（轴开 ⇒ `ArtifactCarryover.Render(SandboxRoot, steps)`）；`src/agent/r1/ArtifactCarryover.cs:21`（`public static class ArtifactCarryover`）；打点 `src/agent/r1/R1RunResult.cs:38-39`（`ArtifactCarryoverRounds` / `ArtifactCarryoverChars`）+ `src/agent/r1/R1Transcript.cs:66-67,101-103`（`artifact_carryover_rounds/chars/enabled`）。
  ⇒ L1 只需在**既有跑臂配置**（`eval/rover/r600/run_r600.sh` 的臂 T/C/C1 + `judge_r600.py` 判据）上加 `BR`/`P` 两臂；产品代码零改动。
- L2 相关：`src/agent/r1/SupplementBlock.cs:14`（尾部可变区块）；`src/agent/r1/SupplementInbox.cs:28`（补充注入）；**已有前缀打点** `src/agent/r1/R1Pipeline.cs:40`（`prefixChars != StructuredPrompt.PrefixChars || prefixSha != ...Pinned` ⇒ fail-closed）+ `src/agent/r1/R1Transcript.cs:28-29`（`prefix_chars` / `prefix_sha256`）+ KPI 档 `docs/evidence/RF0001/KPI.md` §5（第 64 行）。⇒ L2 的机检断言本仓**已存在主链消费点**，只需在跑轮判据里显式化。
- L3 相关：`src/agent/r1/PublicExampleProbe.cs` / `PublicExampleExtractor.cs:19`（`public static class PublicExampleExtractor`）—— 题面公开用例 = 非自产 oracle。

## 3. 下一轮动作（候选队列，按主线纪律保守排序）

1. **L1**（零产品改动）：下一轮真机 A/B 加 `BR`(盲重采样) / `P`(内容无关安慰剂) 两臂；预注册判据 `T ≤ P ⇒ R600 归因撤回`。预算：跑臂 token ×1.5–2，并入同轮。
2. **L3**：判定卫生复核（每一窗的失败判定来源必须非同源），随 rc 语义收口一起落。
3. **L2**：把「前缀字符数 + sha 不变」写成机检断言（改档案时必须重算 pin）。
4. 观察项待放行/预算：ExecuCritic（细粒度 critic 回补）、Ecdysis（运行期 harness 自演化）。

## 4. 试点统计（2026-09-20）

- 检索式 3 条（`"prompt cache"`+cs.CL / `"self-repair"`+cs.SE / `"execution feedback"`+cs.SE）；命中 15 / 24 / 120 条。
- 逐条读判：采信 **3**（L1/L2/L3）· 观察 **5** · 证伪 **0** · 未取到原文 **0** · 静默跳过 **0**。
- 工具面缺陷 **1**（`quote()`/超时/无限流退避）⇒ 已修 skill 脚本，并把修后的命令形态写进自检作业定义。


## 5. R602 增量（2026-09-20 第 2 段；同轮并轮小步）

### 5.1 检索（本轮 2 式，≤3 上限内；检索间隔 ≥4s）

| # | 检索式 | 命令面 | 逐条读判 |
|---|---|---|---|
| Q1 | `"blind resampling"` | `--category cs.SE --max 6 --sort date` | 1 条直击本仓修复环（见下表行 1） |
| Q2 | `"feedback ablation" placebo` | `--max 6 --sort date` | 0 条新增采信（与 Q1 行 1 同族，去重） |

### 5.2 台账（8 列，本轮追加 2 行）

| 日期 | 检索式 | 出处(含版本) | 逐字引文(≤2 句) | 机制假设 | 改哪一格 KPI(预期方向) | 单变量轴 + 判据(阈值/可证伪点) | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-20 | `"blind resampling"` | arXiv:2609.00854**v1**（2026-09-01；comment/journal-ref 皆空 ⇒ 权威性仅由「预注册 + 安慰剂对照 + 488 例/4 模型」支撑，非同行评审） | "We separate these explanations with three arms applied to the same failed candidate: blind whole-solution resampling, spectrum-based localization followed by suspect-span infilling, and same-length infilling at a disjoint random code span." / "among the 177 candidates localizable from a strong suite, localized infilling loses decisively to blind resampling at a matched attempt" | 「定位后精准改」未必优于「盲重采样」；**同长度、无关跨度**的安慰剂臂是分离「定位有用」与「改得小」的必要对照 | 质量（修复收敛率）↑；轮数（盲臂 1 调用 vs 定位臂 2 调用）↓ | 轴 = 修复策略（盲重采样/定位内填/安慰剂内填）；判据 = 修复后整题全对率 `T_盲 ≥ T_定位` ∧ `T_盲 ≥ T_安慰剂` ⇒ 否则「定位」非承重 | **被本轮 L1 机检阻挡**：本仓该轴 env 面仅 **2 态**（on/off）⇒ 第 3 臂无法由配置构造；台账 §3.1「零产品改动」经机检**证伪**（见 5.3） |
| 2026-09-20 | `"feedback ablation" placebo` | arXiv:2609.20812**v1**（2026-09-17；comment: 7 figures, 6 tables） | "An agent overclaims when its final response contradicts information in its context. This definition requires no inference about intent and is independent of task success." / "agents do not read all the files they were asked to review in 67.9\% of runs" | 「产物自报达成 ∧ 外部真值未达成」可**机检**（= 本仓 `rc==0 ∧ 外部用例未全过`），且定义不依赖意图推断 ⇒ 可作独立 KPI 列 | 质量（overclaim 率**独立成列**，禁并入正确率；预期方向 ↓） | 轴 = 判定卫生（自报/外部真值冲突计数）；判据 = 冲突率 `== 0`（可证伪点：任一跑次 rc=0 而外部用例 < 全 即翻红） | **采信（已实施）**：`eval/rover/r602/checks_r602.py` Q1 字段已落盘；本轮实测 `den=18 / rate=0.0 / conflicts=0` |

采集日：2026-09-20（CST）。引用数：Semantic Scholar 无 key 时 HTTP 429 ⇒ **不可用**（如实写，不编造）。
两个版本号均为**逐字取自** `export.arxiv.org/api/query?id_list=` 的 `a:id` 字段（含 `v1`）。

### 5.3 L1「零产品改动」声称被机检证伪（本轮器具产出，非耳闻）

- 器具：`eval/rover/r602/l1_axis_probe_r602.py`（**只读**，零远端调用，零产品改动）。
- 读数：`{"rc": 0, "axis_states": 2, "controls": {"determinism": true, "POS_multi_valued_recognized": true, "NEG_perturbation_flips_to_multi": true}, "verdict": false}`
- 语义：从 `src/agent/r1/R1Options.cs` 派生该轴的**可取值集** = `{on(缺省), off}`（布尔 + 否定串白名单形态）⇒ `BR`(盲重采样) / `P`(安慰剂) **不是该轴的取值**，必须新造机制（= 产品代码改动）。
- 三控制（器具有牙）：① 同输入两次取值集**逐位相同**（确定性）；② 同文件里 int+区间轴（`AGENTFRAMEWORK_R1_MAX_REPAIR`）被识别为**多值**（正控 ⇒ 提取器不恒 2）；③ 对布尔块的**扰动副本**（追加两串）立刻翻成多值（负控 ⇒ 判据非恒真）。
- **收窄（证伪即收窄，不硬凑）**：台账 §3.1 的「L1 零产品改动可加两臂」判为**不可行**；L1 现状降级为**观测项**，重开条件 = 产品侧放行「修复策略」轴（三态）否则不做。
