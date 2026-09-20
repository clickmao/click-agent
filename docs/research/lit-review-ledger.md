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

## 6. R603 增量（2026-09-21；同轮并轮小步）

### 6.1 检索（本轮 3 式，≤3 上限内；检索间隔 ≥4s；全文抓取 2 篇 = 上限）

| # | 检索式 | 命令面 | 结果 |
|---|---|---|---|
| Q1 | `"execution feedback" repair` | `--max 6 --sort date` | 2 条与修复环同族（下表行 1） |
| Q2 | `verification gate false rejection agent` | `--max 6 --sort date` | 0 条新增采信（与本仓判定卫生同族，去重） |
| Q3 | `"cache-aware" scheduling LLM agent` | `--max 6 --sort date` | 1 条直击本仓**判据形态**（下表行 2） |

### 6.2 台账（8 列，本轮追加 2 行）

| 日期 | 检索式 | 出处(含版本) | 逐字引文(≤2 句) | 机制假设 | 改哪一格 KPI(预期方向) | 单变量轴 + 判据(阈值/可证伪点) | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-21 | `"execution feedback" repair` | arXiv:2609.20455**v1**（2026-09-17；comment/journal-ref 皆空 ⇒ 权威性仅由摘要面支撑，非同行评审） | "existing methods often edit skills directly from failed rollouts without structured routing from an observed failure to an editable location" / "allowing the same structure to support skill selection, attribution-guided repair, and update validation" | 失败回灌的收益取决于**「失败 → 可编辑位置」的结构化路由**与**范围化验证 + 回滚**，而非回灌内容总量 | 质量（J2 修复收敛率）↑；成本（回灌体积）↓ | 轴 = 修复回灌**粒度**（整份产物 vs 按失败用例定位的片段）+ **回滚**（失败则还原上一版）；判据 = `T_定位 ≥ T_整份` ∧ 回滚态下整题全对率不下降 | **候选（须产品放行**：现轴 env 面仅 on/off（R602 §5.3 机检）⇒ 三态须改 `src/`） |
| 2026-09-21 | `"cache-aware" scheduling LLM agent` | arXiv:2609.20804**v1**（2026-09-17；comment: 43 pages；无 journal-ref） | "existing work typically evaluates harnesses as monolithic systems, leaving the effectiveness of individual components unclear. To enable component-level comparisons, we study this question with a lightweight coding harness whose execution loop is fixed while three components are varied: planning, action space, and context management." / "we evaluate 176 matched settings spanning five context-management strategies, four context-window budgets, and targeted ablations of planning and action" | 评测应**固定执行环、只变一个组件**做配对消融；整体式读数无法归因到组件 | 口径（**判据形态**，非直接收益）：本仓判据 v3「同件同题集 + 单变量轴 + 同窗配对」= 该形态的本仓实现 | 轴 = 无（口径支持，零新产品机制）；判据 = 每轮预注册必须写明「本轮唯一自由度」且**同件 sha / 题集 sha / 执行环逐字节不变**（本仓 R602/R603 已按此落盘） | **采信（口径支持，已实施）**：R602/R603 预注册 `single_variable` + 同件 sha 8c3ade04d542 逐字节同 |

- **顺延计数**：本轮 1 项（N4④ `V_int` 分布扩展 —— 器具 `landing_predicate_r593.py` 壁钟 >15min 未完成、零输出 ⇒ 零读数入库、进程已按 pid 清场，挪 R604；**禁静默跳过**）。

采集日：2026-09-21（CST）。引用数：Semantic Scholar 无 key 时 HTTP 429 ⇒ **不可用**（如实写，不编造）。
版本号逐字取自 `export.arxiv.org/api/query?id_list=` 的 `a:id` 字段（含 `v1`）。

### 6.3 本轮器具产出（真值掉线面机检，只读）

- 器具：`eval/rover/r603/truthdrop_r603.py`（只读 `precond-<round>.json` 的逐用例两侧 pass/fail 面；零子进程、零远端调用、零产品改动；三态 rc = 0 已算 / 2 器具缺陷 / 3 输入缺失）。
- 四桶定义：S1 两侧过 · S2 我方独败（真值可作 oracle）· **S3 我方过 ∧ 真值败（反相面）** · S4 两侧同败（题面/夹具同难候选）。
- 控制：POS = 取「两侧都过」用例把真值伪改为失败 ⇒ 该窗 S3 必须 +n_prod 且归属全 `L_truth_only`（实测 rows=6=expect）；身份不符（窗集/`failed_cases` 越域）⇒ rc=2；四桶全零 ⇒ rc=2（防退化为恒真门）。
- 读数见 `eval/rover/r603/truthdrop-r603.json`（r602 面已落）。**纪律含义**：codex 真值不得当**硬上限**（J4/J5 的隐含假设）；S3 非零 ⇒ 该类用例只作并列描述，不作「我方收益」证据。

## 7. R604 增量（2026-09-21；同轮并轮小步 · 只读/器具轮）

### 7.1 检索（本轮 3 式 = 上限；检索间隔 ≥4s）

| # | 检索式 | 命令面 | 逐条判（结果数不是判据） |
|---|---|---|---|
| Q1 | `"discriminative" items benchmark` | `--max 6 --sort date` | `Found 202679` ⇒ 检索式**过宽**（`items`/`benchmark` 为高频词，AND 语义下近乎全库）⇒ top6 全为无关（4D 基础模型 / 泼溅液体重建 / 图像上色 / 逆问题基准 / 生态模型 / 机器人蒸馏） |
| Q2 | `agent harness component ablation variance` | `--max 6 --sort date` | `Found 311100` ⇒ 同上过宽；top6 中 2 条已登记（2609.20812 过度宣称 / 2609.20804 harness 组件消融）⇒ **去重**；1 条新面（2609.20822 障碍感知 harness）⇒ 见表 |
| Q3 | `"execution feedback" cost accounting agent` | `--max 6 --sort date` | `Found 321189` ⇒ 过宽；top6 与 Q1/Q2 高度重叠 ⇒ **0 条新增** |

**工具面提示（本轮实测，供后续轮参考，不改脚本）**：`--sort date` 与宽检索式叠加时，返回的是「最新提交」而非「最相关」⇒ **逐条判必须按摘要相关性，不看条数与排序**；带引号的短语**不能**单独承担选择性（Q1 已证）。

### 7.2 台账（8 列，本轮追加 2 行）

| 日期 | 检索式 | 出处(含版本) | 逐字引文(≤2 句) | 机制假设 | 改哪一格 KPI(预期方向) | 单变量轴 + 判据(阈值/可证伪点) | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-21 | `agent harness component ablation variance` | arXiv:2609.20794**v1**（2026-09-17；cs.LG/cs.CE；comment: 32 pages, 10 figures, 21 tables；公开代码 `github.com/neuraloperator/PosteriorBench`；无 journal-ref ⇒ 非同行评审） | "existing evaluations still focus primarily on whether a method can produce a single plausible reconstruction. This is insufficient for ill-posed problems, where multiple solutions may be consistent with the same sparse or noisy observations." / "enabling direct assessment of whether solvers recover the full set of solutions rather than the single best sample" | **欠定/多解问题的评测不能只收「单点期望解」**，否则合法非期望解被系统性判红（= 判据僵硬面） | 质量（判据面：失败归因须先过「解集 oracle」再计我方缺陷；预期方向 = 我方缺陷份额**下降**，若下降则原读数含口径产物） | 轴 = 判据粒度（单点期望 vs **独立实现 oracle 的解集复核**）；判据 = 我方失败例中「合法但非期望解」份额 `<= 0.10` 才可把剩余按能力缺陷计 | **采信（口径支持·已实施）**：本仓已有独立 oracle 复核 —— `eval/rover/r592/landing_predicate_r592.py`（`canon`/`legal_moves`/`probe_grid`，与被测零共享实现）；R593 分桶实测 `A_landing_loose 0.0717` / `B_coldset 0.6595` ⇒ **判据僵硬非主因**（份额已达阈值内），主因仍为冷集构造层 |
| 2026-09-21 | `agent harness component ablation variance` | arXiv:2609.20822**v1**（2026-09-17；cs.RO/cs.AI/cs.CL/cs.CV；comment/journal-ref 皆空 ⇒ 权威性仅由摘要面支撑） | "The agent reasons about the obstacle in its traces, and the prompt already forbids touching it, so neither perception nor instruction is at fault; the fault lies in the planning, where the stated constraint never becomes a priority." / "The agent then plans a route in advance, verifies it, replans when necessary, and only then executes it." | **声明式约束（写在提示词里）不等于承重**；须把约束转成**可执行的前置步骤（先规划→先验证→必要时重规划→再执行）** | 质量（交付面：约束违反率↓）；轮数（前置验证省掉无效整轮） | 轴 = 约束形态（提示词声明 vs **前置结构化校验步骤**）；判据 = 前置校验存在时约束违反率 `== 0`，且**消融臂**（关掉前置校验）违反率 `> 0`（否则前置步骤非承重） | **采信（口径支持·已实施）**：本仓 = `src/agent/r1/R1Pipeline.cs:192`（`probe = PublicSelfCheck ∧ probeSet` 前置回放）→ `src/agent/r1/R1RunResult.cs:12`（`rc=8 / public_probe_unmet` = **非模型自述**的题面公开用例未过）+ `eval/rover/r507pre/exec_precondition.py`（独立物化 + 逐用例判对 = 铁律 11）；消融面的「关掉前置即违反率>0」由 J2 对照档（轴关）承担。**观察边界**：机器人域具体件（route/contact）不可移植，只取机制 |

### 7.3 本轮器具产出（只读/器具轮；零新臂、零远端调用、零产品源码改动）

- **C1 起手闸余量按 r603 实测重派生**：源 `runs/r603/logs/run-samples.jsonl`（n=146, min=2584, max=2869）⇒ `prev_swing_effective=285`（较 r602 源 252 **收紧**）；起手前 3 样本 `ceiling=2577 / spread=0`（同日重采样序列 **2599 → 2577**，随本机负载浮动；两值同判） ⇒ `cap = 2577−2650−60 = −133 < floor 60` ⇒ **`WINDOW_UNOPENABLE`（rc=2，fail-closed 正确行为，承 R590 先例不记缺陷）**；判别力（**纯函数**同态两门槛反判）`basic 2650 → PASS ∧ clause 2710 → GATE_BLOCKED` ⇒ **条款仍严于基础门槛**。**纪律含义**：本轮零真机臂 ⇒ 条款**未真机行使**（未测），且**不得**把「窗口不可开」读成「条款已收紧生效」。读数 `eval/rover/r604/gate-margin-r604.json`。
- **C2 J3 成本判据形态收口（v2）**：v1 形态在 r600/r602/r603 **逐位复现**登记值（`4/4` PASS · `2/3` PASS · `4/3` FAIL，`agree=True`）；v2（合取 a1 池化调用数 ∧ a2 逐窗池化 ∧ b1 单位调用新算 prompt；**无自由参数**）实测：r600 `a1=True, a2 破于 w186, b1 破（734.05 vs 197.35 = 3.72×）`；r602 `a2 破于 w189, b1 破（770.59 vs 247.78 = 3.11×）`；r603 `a2 破于 w191, b1 破（598.50 vs 232.29 = 2.58×）` ⇒ **v2 三轮全判红**。**含义**：v1 的「成本 PASS」是**不完整形态**（只看调用数极值，未看单次调用的新算 prompt）；v2 **不是放宽而是收紧**（把 r600/r602 的 PASS 也翻成红）。两路径交叉校验 `two_path_ok=True`（adapter dump 重算 == kpi-table 数组，逐臂逐列）；控制 `POS 有牙 ∧ NEG 同底 ∧ 非平凡（三轮读数互异）`。**本轮回写边界**：R603 登记的 J3 `FAIL` **原样保留、不翻案**；v2 只作后续轮口径。读数 `eval/rover/r604/j3v2-r604.json`。
- **C3 真值掉线面跨轮 census**：39 窗（r585–r603 的 13 轮 × 3 窗）、4–7 臂/窗；守恒 `10614/10614`；真值失败用例 **13 条**（**全部 `wythoff` 族**）、失败窗次 **57**、涉及 17 窗；头两名 `wythoff#57-hidden`（17 窗 / 12 轮 / 我方通过率 0.5833）与 `wythoff#43-public`（13 窗 / 9 轮 / 0.5）⇒ **T1 成立（真值侧掉线用例）**，但 **T2 = 两侧摆动带**（我方通过率约 0.5–0.58，**不是**「我方稳定通过」）⇒ R603 的「S3 恒为这两条」只说明**反相面的位置集中**，**不能**读成我方在该例上稳定获益；**T3 低区分度窗 = 0**（未触发剔除）。控制 `POS 有牙（+1 窗）/ NEG 身份闸翻红 / 非平凡（13 类非常量）/ 守恒成立`。**口径提示（已入册 §12.6 B）**：本 census 的 S3 = **窗级**（全部产品跑次通过），与 R603 `truthdrop` 的**跑次级** S3 粒度不同 ⇒ 并列，禁互相换算（实测 `r603/w190` 跑次级 S3 非零而窗级为空）。读数 `eval/rover/r604/truthcase-census-r604.json`。
- **C4 入册**：`docs/external-reference-harness.md` **§12.6**（有效窗下限显式二选一 + 两级 S3 口径 + 「真值掉线用例」登记与写法；只做增量，未覆盖既有节）。


## 8. R605 增量（2026-09-21；真机臂轮 · 并轮小步）

### 8.1 检索（本轮 3 式 = 上限；检索间隔 ≥4s）

| # | 检索式 | 命令面 | 逐条判（结果数不是判据） |
|---|---|---|---|
| Q1 | `"repair loop" token overhead agents` | `--category cs.CL --max 6 --sort date` | `Found 68596` ⇒ **过宽**；top6 中 2 条**已登记**（2609.20822 / 2609.20804）⇒ 去重；其余 4 条与管线无关（扩散 LM / 视频生成 / 蒸馏 / 机器人记忆）⇒ **0 条新增** |
| Q2 | `"item-level" filtering discriminative power benchmark` | `--max 6 --sort date` | `Found 466571` ⇒ **过宽**；top6 全为 CV/数学面，含 1 条已登记（2609.20794）⇒ **0 条新增** |
| Q3 | `"token budget" trajectory agent evaluation` | `--category cs.SE --max 6 --sort date` | `Found 144610` ⇒ **过宽**；top6 中 3 条已登记（20822 / 20812 / 20804）⇒ 去重；2 条新面（2609.20789 / 2609.20791）⇒ 见表 |

**工具面提示（第三轮复核，仍不改脚本）**：`--sort date` 与宽检索式叠加时返回「最新提交」而非「最相关」；带引号的短语**不能**单独承担选择性（Q1/Q2 已二度证实）⇒ 逐条判必须按摘要相关性。**预算内已用满 3 式 ⇒ 本轮不再追加**（反空转：若下轮仍 0 采信则降频为每 3 轮一次）。

### 8.2 台账（8 列，本轮追加 2 行）

| 日期 | 检索式 | 出处(含版本) | 逐字引文(≤2 句) | 机制假设 | 改哪一格 KPI(预期方向) | 单变量轴 + 判据(阈值/可证伪点) | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-21 | `"token budget" trajectory agent evaluation` | arXiv:2609.20789**v1**（2026-09-17；cs.GT/cs.IT；comment: 13 pages. Lean 4 formalization: `github.com/zrobertson466920/mutual-evaluation`；无 journal-ref ⇒ **非同行评审**；权威性代理 = **公开形式化代码** > 纯预印本） | "The critic chooses a finite-valued rule that induces an evaluation score on joint report laws." / "implementations are shown that produce unbiased Pearson and Shannon information scores without requiring peers, a ground-truth reference, or likelihood-ratio estimation."（附限定："One runtime restriction is that the number of required replicas is random and can depend on the critic rule."） | 无真值参照时，用**同任务独立复本**（replication-loop）的「类型一致」回报即可给出无偏的相互评价 ⇒ 「自报成功」与「外部真值」之间还可插一层**复本一致性** | 质量（判据面）：把「同题同臂 k 次独立复本的整题全对率一致性」作为**自判可靠性上界**（本仓现有 Q1 假信心率 + codex 真值两个面，缺这一格） | 轴 = 复本数 k（同题同臂 k 次独立会话，k∈{1,3}）；判据 = k=3 的「复本间不一致率」与 Q1 假信心率**同号且不一致率 ≤ 假信心率** ⇒ 复本面足够；**先落分布、禁预建阈值** | **候选（分布先行）**：本仓现状 = `eval/rover/r605/checks_r605.py::Q1_false_confidence`（rc0 ∧ 外部未满分 **1/18**；反向 7 例）；R605 尚未构造复本臂 ⇒ 触发条件 = 用户放行新臂面 |
| 2026-09-21 | `"token budget" trajectory agent evaluation` | arXiv:2609.20791**v1**（2026-09-17；cs.RO；comment: 8 pages, 2 figures；无 journal-ref ⇒ 非同行评审） | "Existing approaches often rely on pre-designed completion signal checkers that are hard to obtain in real-world execution." / "their decision boundaries are not inherently aligned with task completion criteria" | **阶段推进/完成判定**应由独立检查器判（可学），不靠策略自述与本域手工写死的完成信号 | 轮数（`steps_executed`：误推进 ⇒ 返工轮）＋质量（阶段已过而目标未达成） | 轴 = 阶段推进判据形态（写死顶层流程 vs 独立检查器产出的结构化完成信号）；判据 = 误推进率 `== 0` ∧ **消融臂**（关掉检查器）该率 `> 0`（否则检查器非承重） | **观测项**（机器人域具体件不可移植，只取机制；引入检查器属**新组件 ⇒ 须用户放行**，本轮不动） |

### 8.3 本轮器具面产出（与主线同轮，零新增夹具语义）

- **候选④ W_floor 落到判据器 + 零回归**：有效窗 ∈{0,1} ⇒ `NO_RESOLUTION`；回放 11 轮 ⇒ 翻号 **3**（全 `不达→NO_RESOLUTION`：r591/r597/r599，皆有效窗 ≤1），`NO_RESOLUTION→PASS` **0**、`PASS→任何` **0** ⇒ **纯标签语义收口、非阈值改动**。读数 `eval/rover/r605/wfloor-regression-r605.json`（rc=0）。
- **候选⑤ LD 冻结名单**（`wythoff#43-public` / `wythoff#57-hidden`）只作诊断列 `v3_ex_LD`=[0, −4, 0]，**不作判据、不进 rc**；控制 POS（空名单 ≡ v3）/ NEG（未知 id 拒）/ 非平凡 三件齐。读数 `verdict-r605.json::LD_low_discrimination`。
- **候选② J3 v2 首次在新窗集行使**：a1（池化 21 vs 19）/ a2（w193 10 vs 5）/ b1（665.81 vs 287.89 = 2.31×）**三条全破** ⇒ 形态收口后**仍不达标**（与 R604 三轮全红同号）。读数 `verdict-r605.json::J3_cost`。
- **候选⑥ 起手前清场**：按 pid 收口会话端 LSP 子进程（R604 反事实栏预测 249MB，实测 **+177MB**）⇒ 起手闸 A1/A2 PASS、窗口可开。
- **V_int 第六窗集（顺延项回执）**：`landing_predicate_r593.py --rounds r605 --codex-too` **已完成**（rc=2）：21/21 跑次、oracle 一致、控制 OK/POS/NEG 落点唯一（新粒度 has_teeth=True / 旧粒度 False）、守恒 True；agent 桶 {B_coldset 48 / A_landing_loose 27 / D_delivery_or_shape 9 / A_selection_order 3}（D 子桶 D1 5 / D3 4）、codex 桶 {}（3 跑次全过）；`v_int_hist` agent {0:14, 3:1, 29:1, 32:1, 118:1} / codex {0:3}；层 agent {(c) 12, (b) 4, (a) 2} / codex {(c) 3}。**rc=2 两项 False 均为测量层**：① 零回归=False = 已知单窗集 scope 伪影（同器具对历史全集复算 match=True）；② 只读=False = **两个不可区分的候选因**：**（a）本侧**在器具运行期间并发跑了 `dotnet test`（器具以 `src/` 树 sha 前后比对作只读判据 ⇒ 构建写 `src/*/obj|bin` 即破）；**（b）对侧写者在飞** —— `.git/ROUND_CLAIM` = `R606 … 2026-09-21T04:31:28`，且工作区有**未提交** `src/` 改动（`R1Options.cs` + `R1ProbeRepairBudgetTests.cs`，共 +59/−4）⇒ 同一判据被破。快照树 `-newermt 04:26` 改动文件数 = **0** ⇒ **被测面（r605 快照）未被改**；两因不可区分（禁单选归因）。**纪律含义**：违反的是本侧的「批测/单测/build 三者互斥」，不是器具；R606 在无并发构建条件下重跑取纯净读数。读数 `eval/rover/r605/vint-r605.json` + 日志 `vint-r605.log`。

## 9. R607 增量（2026-09-21；盘点+打点轮 · 零产品改动 · 主线 = RF0004.0）

### 9.1 检索（本轮 2 式，≤3 上限内；间隔 ≥4s）

| # | 检索式 | 说明 |
|---|---|---|
| Q1 | `"tool call orchestration" agent`（cat cs.CL, sort=submittedDate, max 5） | 命中 10,476 条；逐条读标题/摘要后取 1 条相关 |
| Q2 | `"structured action space" "tool calling" agent`（cat cs.CL, sort=submittedDate, max 5） | 命中 12,156 条；top 命与 Q1 重叠 ⇒ 只作交叉确认，不新增条目 |

**结果数不是判据**：Q1/Q2 的 `Found N results` 与相关性无关（去引号式检索会命中上万条）；本轮采信仅凭逐条读摘要。
**权威性代理（逐条写明）**：2609.20804v1 = **纯预印本**（arXiv comment 仅 "43 pages"、无 journal-ref、无 DOI、无同行评审 venue）；未取到公开代码仓链接 ⇒ 按「纯预印本」档，**只作机制来源，不得当收益证据**。
**引用数不可用**：Semantic Scholar 无 key ⇒ HTTP 429；OpenAlex 对近月预印本 `cited_by_count = 0` ⇒ 本轮**如实记「引用数不可用」**，不以引用量作权威性背书。
**全文抓取**：0 篇（本轮只读 API 逐字摘要；未抓 PDF ⇒ 不宣称已读全文）。

### 9.2 台账（8 列，本轮追加 1 行）

| 日期 | 检索式 | 出处（含版本） | 逐字引文（≤2 句） | 机制假设 | 改哪一格 KPI（预期方向） | 单变量轴 + 判据（阈值/可证伪点） | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-21 | `"tool call orchestration" agent` | arXiv:2609.20804v1（2026-09-17 · cs.AI/cs.CL/cs.LG/cs.SE · 预印本） | "To enable component-level comparisons, we study this question with a lightweight coding harness whose execution loop is fixed while three components are varied: planning, action space, and context management." / "Predefined tools improve performance for models with weaker bash proficiency, whereas bash-capable models can operate effectively with a bash-only interface and achieve substantially lower cost, especially on command-line-centric tasks." | **动作空间粒度是可单变量消融的轴**：固定执行环，只换「工具面粒度」（预定义工具集 ↔ 纯命令行面）⇒ 成本随模型能力而反转 | ②执行面（调用数按 request_id 去重）+ ⑤tokens（预期：粒度变粗 ⇒ 调用数↓、completion↓；质量持平） | 轴 = 动作空间粒度（两侧同一执行环，唯一差异 = 工具声明面）；判据 = 同窗 reps≥3：调用数 ≤ 旧臂 50% ∧ 质量（整题全对）≥ 旧臂 ∧ 恒前缀 ≥97% ∧ 打点面治疗>0/对照==0（**先证变量可生效**，否则 VOID） | **候选**（未实施：需先过 RF0004.2 R610–R612 的前置 = 编排面打点落地，见 §9.3） |

### 9.3 本轮与本仓现状的代码证据对照（有代码行 ≠ 生效）

| 面 | 代码事实（现盘） | 判据 |
|---|---|---|
| 多轮工具编排 | `src/agent/modelqueue/ModelQueueAdapter.cs:154`（`_actionPort != null && ActionLoopRunner.IsEnabled()` ⇒ 进旧动作环）；`ActionLoopRunner.cs` **Emit 数 = 0**（`grep -c "Emit(" ⇒ 0`） | 编排面**无专用打点** ⇒ 论文的「动作空间粒度」轴在本仓**当前不可机检**（打点缺失）⇒ 该候选的前置 = 先落编排面打点（RF0004.2） |
| 生成类 | `src/agent.modelqueue/TaskKindHint.cs` 五档（General/ContextCompression/KeywordTagging/TendencyAnalysis/IntentClassification），**无 Generation** | 论文的「component 消融」范式要求被消融件有独立可选档 ⇒ 生成档不存在 ⇒ RF0004.3 前置成立 |
| 开放域识别 | `src/agent/IndustrialAgentV2.cs:1862`（`nlp_shape`，现读数 19/27572 行） | 唯一**已在现盘可区分**的面（本轮真机行使对象） |

**候选实施状态**：`候选`（未实施）——按 skill `external-reference-adoption`，实施一律走单变量真机对照（同窗 / reps≥3 / 预注册判据），**论文只提供机制假设**。
**顺延计数**：本轮文献小步**未顺延**（2 式检索 + 台账追加均在本轮完成）。

## 10. R608 增量（2026-09-21；RF0004.1 出口落地轮 · 真机臂 · 单变量 = `AGENTFRAMEWORK_RECOGNITION_VERDICT`）

### 10.1 检索（3 式 = 预算硬上界已用满；3/3 零结果）

| 日期 | 检索式 | 出处（含版本） | 逐字引文（≤2 句） | 机制假设 | 改哪一格 KPI（预期方向） | 单变量轴 + 判据（阈值/可证伪点） | 状态 |
|---|---|---|---|---|---|---|---|
| 2026-09-21 | `"selective prediction abstention"` --category cs.CL --max 6 --sort date | 未取到（检索式 0 结果） | — | — | — | — | 未取到原文 ⇒ 不采信 |
| 2026-09-21 | `"open-domain intent recognition"` --category cs.CL --max 6 --sort date | 未取到（检索式 0 结果） | — | — | — | — | 未取到原文 ⇒ 不采信 |
| 2026-09-21 | `"abstention calibration LLM agent"` --category cs.CL --max 6 --sort date | 未取到（检索式 0 结果） | — | — | — | — | 未取到原文 ⇒ 不采信 |

**本轮统计**：采信 0 / 候选 0 / 证伪 0 / **顺延 0**（检索式已跑满 3 式，属「0 结果」非「预算被吃满而顺延」）。
**器具观察（一行，如实）**：带引号短语 ∧ `--category cs.CL` 组合 3/3 零结果；按预算硬上界本轮**未追加**复核，下轮换检索形态（去 category / 换短语）后再核 —— 未取到原文一律不采信（反幻觉硬闸）。

### 10.2 本仓现状代码证据对照（RF0004.1 出口**落地后**·有代码行 ≠ 生效）

| 面 | 代码事实（现盘） | 判据 |
|---|---|---|
| 开放域识别出口 | `src/agent.nlp/RecognitionVerdict.cs`（22 行，`{label|abstain,evidence}` 值类型）+ `src/agent.nlp/RecognitionOutlet.cs`（45 行，只读渲染器 + `IsEnabled()`）+ 发射点 `src/agent/IndustrialAgentV2.cs:1880`（`nlp_shape` 之后，开关缺省 on） | 真机：治疗 3/3 跑次覆盖 **2/2 轮**（abstain 1/1/1），对照 3/3 跑次 **0 事件** ⇒ 该面**已接线且可消融**（非孤岛） |
| 出口判据面（下一轮） | 同上（`recognition_verdict` 逐轮一行） | abstain 率首读基线 = **0.5**（3/6 轮，无阈值：R609 出口闸判据面） |

### 10.3 连续 0 采信计数

R607 = 采信 1（arXiv:2609.20804v1 组件级消融口径等）⇒ **本 R608 = 连续 0 采信第 1 轮**（反空转阈值：连续 3 轮 0 采信 ⇒ 检索降频为每 3 轮一次并登记）。
**候选实施状态**：无新候选（本轮 0 采信）⇒ 无实施义务；RF0004.1 出口落地本身是上轮（R607 盘点）缺口的直接实施，非文献候选实施。

