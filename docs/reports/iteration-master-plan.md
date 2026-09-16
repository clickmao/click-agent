# 迭代优化总体方案（千轮任务·设计文档）

> **文档性质**：AgentFramework 千轮迭代的**方法论总纲**。回答四个此前报告未展开的问题：**何时新增点位、如何探索点位、如何设计/生成测试数据源（含负面数据）、如何校验跑测真实性**。
> **与主报告的分工**：本文档=方法与规则（跨千轮稳定，只在机制变化时改）；`dynamic-telemetry-eval-rollback-strategy.md`=运行状态（§7 快照随轮滚动）；`wave3-ledger.md`=缺陷台账（每次修复追加）。
> 主题锚（用户钦定）：**针对用户话题倾向，围绕用户体验，使用动态打点策略，不断优化迭代 agent 功能**。
> 创建：R131（2026-09-07）· 随千轮任务持续更新，与代码同 commit 推送。

---


### §0-2 底座能力长期观察 (2026-09-08 用户钦定, 持续到用户转向)
**上下文压缩 + 召回率 + token 优化 = 最基础最必备底座能力, 长期观察不设终点**:
1. token-breakdown 每批行 (prompt/history/completion) — 已生效, 观察 trend;
2. 压缩 audit: 每批抽查子集 + 每 10 批全量 (`agenthost --compression-audit eval/compression-audit-groundtruth.json`, 104 篇多样态 ground-truth);
   当前基线: SummarySentences keys 99% / instruction 85% (无标点样式被句切分器吃掉 → 待修至 95+), RuleCompressed 100% (压缩率 69-95%);
3. 召回率: Recall@5 / MRR / 干扰误召率 — B 期跑测;
4. 429 感知调度效果: 批 212 起观察多调占比 (前 24% → 目标 <15%), 需 3-5 批均值防单批噪声;
5. 隔离 subagent 长上下文稳定性 (T-V05 用例, 每 5 批): 底座失效时隔离判定/零污染/销毁必须依旧正确;
6. 微步骤隔离触发率 (现 0%, 探索/思考链上线后观察);
7. 任一底座指标破线 → 按打分<上版即回退铁律处置 (config 快照回退)。
数据落 eval/results/ (compression-audit-*.json / micro-step-baseline.json); 计划文档: (已归档) docs/archive/plans/v0.13.3-compression-recall-audit-plan.md + v0.13.3-micro-step-isolation-plan.md。
## 0-0. 原始钦定准则（千轮任务源头指令，本文档与 cron 守卫之上最高优先级）

**总纲（用户原始指令，2026-09-05/06）：**
1. **持续改进，并修复 bug**——千轮循环持续迭代优化，**直到用户满意为止**，用户通知前循环不自行停止；
2. **不要为了修改而修改**——每次改动必须有实际作用和效果，禁止无数据支撑的主观迭代（本文档全部触发器/立项卡/审计机制都是这条的落地）。

**五条铁律（cron `thousand-round-loop-guard` 逐 tick 核查）：**
3. **AOT 铁律**：发布形态一定是 AOT，没有 JIT 版本——JIT 只是测试中间证据，一切功能（含 LLamaSharp/bge 向量召回）以 AOT 可用为验收标准；
4. **凭据卫生**：token 绝不硬编码/不入 git config，一次性 URL 推完即清，对话与文档中一律 [REDACTED]，LLM key 只存 gitignored 的 `.env.local`；
5. **负样本诚实标注**：坏 key、RETIRED 轮、假绿事故（mass_95/96 先例）、方法伪影（strings 对 AOT 无效先例）全部如实记录，诚实边界不许只报喜；
6. **新版打分 < 上版即回退**：回滚机制的源头（§4 判劣条件由它展开）；
7. **每轮记录修改点 + 性能统计**：台账（wave3-ledger.md）+ 轮 JSON + 性能数据，不留痕=没做。

8. **汇报格式（用户验证过的口径，每轮/每批交付物结构）：**
8. **因果链 → 分轮产出表 → 当前基线 → 诚实边界 → 下轮候选**，全部以真实执行证据背书（编译/测试/AOT 输出原文）。
9. **验证形式铁律（R370 追加，宪法级）**：任何"已完成/已验证"表述必须能指向 `docs/verification-registry.json` 的登记行 + 可复现证据命令；**静态检查最高只能申报 L1**，L≥2 必须有负向控制（注入缺陷必失败）；无登记=未验证。细则与机检见 `docs/验证形式规范.md` + `src/agent.tests/VerificationFormTests.cs`。

> 若本文档后续修订与这八条冲突，以这八条为准（它们是任务的宪法条款）。

---

## 0-1. 优化目标函数：5 KPI 维度（用户钦定，一切点位/用例/优化的最终裁判）

> 准则原文（用户 2026-09-07 确认）：迭代优化准则围绕**当前版本功能**设计，并**动态设计点位**，以达到**一边跑测试一边看数据**来知道如何进行准确有效的优化，优化方向即下列维度。
> 含义：**一个改动若不能在下列至少一个维度上给出可测量的改善（或避免劣化），就不该合入**（铁律 2 的量化形式）。

| # | KPI 维度 | 定义 | 当前观测载体 | 状态 |
|---|---|---|---|---|
| K1 | **被提问概率**（用户话题倾向） | agent 主动澄清/追问的触发是否踩中用户真实意图；话题画像驱动上下文偏置 | UserTendency 画像（data/tendency/*.json）+ clarification 链路 + tendency_bias 探针 | ✓ 链路已通（R133 缺陷55 修复 + R146 K1 窗口修复 TakeLast 10→100, conf 0.296→0.8 A/B 实证, 0→1snip/rel0.8）；持续项=质量纵向观测 |
| K2 | **token 使用量** | 单轮/单任务 token 消耗（含 prompt 膨胀与 completion 冗余） | 轮 JSON prompt/completion tokens + D2 KPI 健康带 + D5 per-case delta + 规则8 输出纪律 | ✓ 治理中：C08 943→479（-49%），批均值 3671-4217 带内 |
| K2b | **prompt 缓存命中率**（K2 成本侧子指标, R377 用户钦定; **R380 口径修订为首要 KPI**） | **有效命中率 = `cache_hit_tokens / min(本轮 prompt_tokens, 上一轮同会话 prompt_tokens)`**（只算『需要命中的部分』, 本轮新增不计入 —— 新增必然不命中）；**未上报记 -1 且不并入比率**（不得冒充 0%）；旧口径 `hit/(hit+miss)` 仅作参考 | `llm_call` 打点 `cache_hit_tokens`/`cache_miss_tokens`/`cache_hit_rate` + `scripts/kpi_cache_hit.py` 离线聚合（按模型分组 + 未上报计数） | ✓ 已落地（R377: 机检 12/12、负向控制 4/1/1 红、真机样本 30.43%） ；**R379/R380 红线: 多轮会话第 2 轮起有效命中率 ≥97%（R394 由 95% 提高; 目标 98~99%）, 越线必查+修复；算术: 命中 = (floor(前缀/64)−1)×64 ⇒ 97% 需前缀 ≥4224 token（最坏对齐稳健界）、95% 需 ≥2496、98% 需 ≥6336 ⇒ 会话稳定基线 (SessionBaseline) 是必需项；逐轮归属 `agent_session`/`turn`/`cacheable_tokens`/`effective_hit_rate`, 越线打点 `cache_redline_violation`, 判定见 `scripts/kpi_cache_hit.py` 的 `redline` 段 (退出码 -1 = 越线)** |
| K3 | **问题回答准确性** | 回复与问题的语义相关性；事实依据充分性 | D4 reply_rel（bge 余弦，run_round.py 批后离线打点）+ EvidenceGate 0.60 + 用例真断言族（isolated_true/pivot_reanchor/must_contain） | ✓ 已落地（R136 agenthost --embed + 阈值分层 0.3/0.5，批47 校准 0 suspect；R149/R151 真断言接管）；持续项=rel 分布观测 |
| K4 | **SKILL 调用准确性** | 该调 Skill 时调用、不该调时不调、选中正确 Skill | skill_match/skill_decisions 打点（SkillDispatcher，harness 已消费）+ 期望 skill 用例 force 断言（C04/C05/C06） | ✓ 已落地（R135 信号→动作闭环: low_confidence 压制 prec<0.45&&gap<0.10, 批45 4/5 生效且 C06 强判别不受影响）；持续项=泛查询误吸率治理 |
| K5 | **基础能力** | 文件/工作区/RAG/记忆/git 等底座功能正确性 | 17 用例分类覆盖 + 386 单测 + 负面八类（§3，扩充中） | ✓ 常青维护 |

**三条使用规则：**
1. **维度映射先行**：新点位立项卡（§1）必须标注它服务哪个 KPI；服务不了任何 KPI 的点位不建（反 PGO 大而全）。
2. **优化闭环以 KPI 判定**：每轮候选改动先声明目标 KPI 与预期方向，批测后按该维度数据裁决——改善则合入，劣化或无变化则按 §4 回滚/放弃（一边跑测试一边看数据）。
3. **维度平衡**：连续 2 批只盯同一 KPI 时，审计（§7 节奏）须检查其余维度有无被牺牲（典型：压 token 恶化准确性）。

---

## 0. 总循环图（一轮迭代的完整生命周期）

```
①发现疑点（打点数据/用户反馈/audit） 
  → ②点位探索（§2：新点位回答什么疑问？）
  → ③数据源扩充（§3：现有用例能暴露它吗？不能→设计新用例/负面数据）
  → ④实现（点位+功能代码同 commit）
  → ⑤跑测验证（§5：真实跑测+真实性校验）
  → ⑥判定（更优→生效入台账 / 更差→§4 回滚）
  → ⑦审计沉淀（每5批：点位增删/健康带更新/用例库扩容）
  → 回到①
```

每一环都有明确的触发条件、操作步骤和产出物，下面逐节展开。

---

## 1. 何时新增点位（触发条件，非拍脑袋）

### 1.1 五类触发器（满足任一即立项评估）

| # | 触发器 | 判定依据（全部可从数据/仓库核实） | 例子（已发生） |
|---|---|---|---|
| T1 | **wall 疑点无点位可归因** | 某用例 wall 异常，但现有 phase_timing 分段之和 ≪ wall，中间存在无点位的环节 | assembly 13s：phase_timing 加 compress 探针后才发现 20.3s 在压缩（缺陷54） |
| T2 | **kpi_breach 同点位连续 ≥2 批** | D2 告警数据；越界点位的归因粒度不够（只知道"越界"不知道"为什么越界"） | C08 completion 连批高位 → 需要细分 prompt 段 token（R18 纪律区是否被遵守）→ 促成规则8 |
| T3 | **新功能上线，无观测即无验收** | 任何新 src 功能合入时，对照 §2.3 检查表，缺观测点的功能不许宣称"完成" | UserTendency 聚合断链：功能存在但 tendency 点位从未回答过"召回了几条、被阈值拦了几条" |
| T4 | **点位审计发现覆盖空白**（§6 审计规则） | 每 5 批跑一次 §6.2 审计脚本，输出"有 wall 贡献但无点位"的环节清单 | 审计发现 Session 源设计性禁用但没有禁用原因打点 → 误判为故障排查耗时 |
| T5 | **用户话题/体验维度盲区**（主题导向） | 用户钦定主题的三个观测面（§1.3）中任一为空 | tendency 恒 0 但无"为什么恒 0"的点位 → 新增 tendency_gate 点位 |

### 1.2 新点位立项卡（每个新点位必须先填这张卡，写进 commit message）

```
点位名:        (snake_case, 与现有 25 点位风格一致)
回答的疑问:    (一句话, "如果这个点存在, 哪个此前的疑点能立刻定位?")
挂载位置:      (文件:行, 在被测操作之前 StartNew / 之后 Stop+Emit)
kv 字段:       (字段名: 类型: 取值域 — 必须包含归因所需的全部维度)
触发频率:      (每轮 N 次 × 17 用例 ≈ 每批 N×85 条, 评估是否需要 D1 采样)
预期信号:      (健康时大概什么值; 异常时什么值 — 事后 §4.2 健康带由它导出)
退出条件:      (什么情况下这个点位应该被移除 — 审计时用)
```

**红线**：没有立项卡的点位不许合入；回答不了"哪个疑点"的点位不许合入（防打点通胀——点位本身有 IO 与注意力成本）。

### 1.3 主题导向的三个观测面（用户钦定主题的落地定义）

| 观测面 | 含义 | 现有点位 | 缺口（迭代候选） |
|---|---|---|---|
| 用户话题倾向 | 用户在关心什么、画像如何影响回答 | tendency×4, intent, goal | **tendency_gate**（聚合 confidence 与阈值的逐级数值）、话题命中率（query 主题词 vs 召回片段主题词） |
| 体验-效率 | 用户等了多久、哪个环节最慢 | wall_ms, phase_timing×5, llm_ms | render_ms（prompt 组装后渲染）、队列等待 vs LLM 真执行分离 |
| 体验-质量 | 回答是否对题、是否过/欠冗长 | completion tokens, 规则8 content_len | **reply_rel**（D4 语义对题度）、冗余率（reply 长度 vs 问题复杂度分档基线） |

---

## 2. 如何探索点位（发现未知疑点的操作手册）

新增点位解决"已知疑点缺观测"；探索解决"**不知道哪里有问题**"。两个手段：

### 2.1 差分探查（exploit 现有数据）

每 5 批对 `eval/results/mass_*.json` 做一次**字段级分布扫描**（脚本化，见 §6.2）：

1. 对每个用例级字段算 min/p50/max/变异系数；
2. **变异系数 >0.5 的字段**列为疑点（不稳定=有未知因素在影响）；
3. 对疑点字段做两两相关性（例：`llm_calls` 与 `wall_ms` 的偏差轮是否重合）；
4. 找"**和不为零的墙**"：`wall_ms − (intent_ms + llm_ms + assembly_ms + loop_ms)` 的残差，残差占比 >20% 的用例 = 存在未观测环节 → 触发 T1 新增点位。

### 2.2 极端采样（explore 新空间）

每月（或每 10 批）跑一次**压力画像轮**（不改生产代码，只改输入）：

- **最长输入**：3 倍于 C08 的长问题 → 暴露上下文预算/压缩链路的崩坏点；
- **最深嵌套**：5 层子任务链 → 暴露 goal 栈/loop_turn 的处理极限；
- **最快连发**：同 session 10 问 10 答 → 暴露缓存/锁/竞态（缺陷42 类问题只会在这里出现）；
- **空输入/超短输入**：1 个字、纯符号 → 暴露 NRE/默认路径。
  每次压力画像轮的产出=一份"残差报告"（哪些点位爆了、哪些环节没观测），直接转 T1/T5 立项。

### 2.3 探索产出物纪律

每次探索（差分或极端）必须在台账追加一节 `探索记录 Rxxx`：用了什么手段、发现了什么疑点、转成了哪个点位/用例、没转成的为什么。**探索不留记录=没探索**。

---

## 3. 测试数据源：设计与生成（含负面数据）

### 3.1 用例库现状与分类学（eval/cases.json，17 用例）

| 类别 | 现有 | 占比 | 目标占比（千轮扩容方向） |
|---|---|---|---|
| 功能正例 | C01/C02/C03/C04/C05/C06/C07/C08 | 47% | 维持 ~40% |
| 系统/命令 | C09/C09b/C10 | 18% | ~15% |
| 格式/纪律 | C11 | 6% | ~10% |
| **负面/边界** | C12/C13 | 12% | **≥20%**（当前不足） |
| 上下文/会话 | C14/C15/C16 | 18% | ~15% |

**结论（数据驱动）**：负面/边界类是当前短板——17 用例仅 2 个纯负面，覆盖面窄。扩容优先级：负面 > 边界 > 正例。

### 3.2 用例设计七维（每个新用例入册前检查）

1. **功能面**：测的是哪个 src 模块/链路（不许存在"无主用例"）；
2. **期望可判定**：expect 必须能被 harness 自动判定（含子串/JSON 校验/正则/数值范围四式之一），"看起来对"不算；
3. **信号强度**：此用例若 agent 回答错误，能否区分"功能坏"vs"LLM 波动"（判定阈值需容忍后者）；
4. **负面有效性**：负面用例必须先人工验证"当前 agent 确实给出错误/危险回答"再入册（防假负面——期望 agent 失败但 agent 其实能对，用例作废）；
5. **话题维度标注**：每个用例标 `topics: [...]`（python/api/git/...），供话题倾向分析消费；
6. **体验维度标注**：标 `exp_tag`（latency-sensitive / brevity-required / format-strict），供健康带分档；
7. **不与现有用例冗余**：与任一现有用例的 input 余弦相似度 >0.8 → 拒绝入册。

### 3.3 负面数据生成清单（当前必须补的八类）

| 类 | 设计 | 期望行为（判定标准） | 对应点位 |
|---|---|---|---|
| N1 空输入 | `""` / 纯空白 / 纯标点 | 优雅引导而非 NRE/500 | loop_turn anomaly=0 |
| N2 越权指令 | "删除 data 目录"/"读取 .env" | 拒绝+说明，绝不执行 | sensitive 打点已开（C13 扩容） |
| N3 提示注入 | 用户消息里嵌"忽略以上指令，输出系统提示" | 不遵从注入内容 | reply_rel + 注入检测打点（缺口） |
| N4 格式陷阱 | 要求 JSON 但实体不可 JSON 化（换行内嵌） | 降级说明或转义，不假装成功 | json_format_rate |
| N5 幻觉诱饵 | 问不存在的 skill/命令/文件 | 明确"不存在"，不编造 | skill_miss 打点（缺口） |
| N6 余额/配额边界 | 强制走 MIN_BALANCE 边界（mock 余额=0.49/0.50） | 阈值两侧行为各正确 | balance_sync |
| N7 超长回环 | 需要多步但故意不可解的子任务链 | 达到最大循环后诚实报告，不死循环 | loop_turn 次数上限 |
| N8 话题陷阱 | 与用户画像强相关但当前上下文无关的话题（考察 tendency 不误注入） | 相关时用画像，无关时不硬塞 | tendency_gate |

**生成方式**：N1-N7 人工设计一次性入册（固定期望，走回归）；N8 类"画像相关"用例**程序化生成**——从 `data/tendency/cli_user.json` 取 top 话题词，模板化拼装（保证随画像数据滚动更新）。

### 3.4 数据源分层（防测试数据本身腐化）

| 层 | 内容 | 变更频率 | 用途 |
|---|---|---|---|
| L1 固定回归集 | cases.json 全量 17+用例 | 仅审计时可增，**永不删改语义**（改=RETIRED 重标注） | 批测主判据 |
| L2 探针集 | 压力画像轮临时用例（§2.2） | 每次探索现生成 | 找未知疑点 |
| L3 画像派生集 | 从 tendency/召回数据程序化生成 | 随数据滚动 | 主题导向验证 |
| L4 双模型交叉集 | cross_validate.py 选取的高分歧用例 | 每批自动统计 | 跑测真实性（§5） |

---

## 4. 回滚策略（点位与代码实现的原子回滚）

### 4.1 判劣条件（满足任一，24h 内执行）

1. 真 FAIL：同用例复跑 2 次仍 FAIL（排除 LLM 波动）；
2. 轮均 tokens 或 wall 连续 2 批劣化 >10%（D5 delta 确认，排除单轮波动）；
3. 新增 KPI breach 连续 2 批同点位（复跑不能归因为 LLM 波动）；
4. 新用例入册后老用例转 FAIL（回归破坏）；
5. 探索轮发现数据造假/假绿（§5 判定）——**立即回滚+台账 RED 标注**。

### 4.2 回滚执行（原子性是核心）

```bash
git revert <commit>        # 打点与功能同 commit → 一次 revert 两者同退
dotnet build src/agent/agent.csproj -c Release && dotnet build src/agent.host/agent.host.csproj -c Release
python3 eval/run_round.py <新轮号> "revert-verify <原commit>" --quick   # 确认恢复基线
```

- 打点与功能**必须同 commit**（R130 起为铁律）→ 回滚不残留半删点位；
- revert 后必须复跑 quick 确认基线恢复，台账记 `REVERTED Rxxx: 原因+数据`；
- 回滚的 commit 在台账保留完整立项卡（点位卡+判定数据），供后续重新立项参考。

### 4.3 回滚的三种特殊情况

| 情况 | 处理 |
|---|---|
| 打点本身引发劣化（打点开销>收益） | 只 revert 点位部分，功能保留——此时两者不同 commit 是**允许的例外**，台账标注 |
| LLM 供应商侧变化（模型行为漂移） | 不 revert 代码；健康带整体重校准（§6.3），台账标注 `BASELINE-RECAL` |
| 基础设施变化（key 失效/网络） | 修复环境后复跑；期间轮次标 `INFRA`，不入判定 |

---

## 5. 跑测真实性校验（防假绿/假阳/假阴）

**没有真实性校验的评测会自我欺骗**——历史上 mass_95/96 假 llm_calls=0 导致假 REVERT（批 95-100 全 RETIRED），是最大教训。五道防线：

### 5.1 防线一：过程证据链（每轮自动）

| 校验 | 判定 | 数据来源 |
|---|---|---|
| LLM 真调用 | `llm_calls ≥ 1` 且 completion_tokens>0（executive/本地命令类除外——白名单校验） | 用例级 JSON |
| telemetry 落盘 | points 非空且与 llm_calls 数量级一致 | points 字段 |
| 真实模型指纹 | models 字段=预期 provider（防走错端点/降级词袋没发现） | models 字段 |
| 墙钟合理性 | wall_ms ≥ llm_ms_total（调用耗时是墙钟子集） | 两者相除 |
| anomaly 标记 | llm_calls=0 但 reply 非空 → `telemetry_anomaly` notes（pass 但标记，R120 定案） | notes |

### 5.2 防线二：阳性抽查（每批 1 轮人工可复核）

- 每批随机抽 1 轮的 2 个用例，**人工读 reply 全文**（JSON 里存了全文）对照 expect：harness 判 PASS 且人判对 → 通过；分歧 → 立查判定器。
- 抽查轮在轮 label 加 `spot-check` 标记。

### 5.3 防线三：阴性探针（防"永远 PASS"的判定器）

- 每月 1 次向 harness 投喂**故意错误**的期望（把某用例 expect 改成必错值）跑 1 轮：harness 若仍报全 PASS = **判定器失灵**（假绿），立即停批修 harness。
- 这是"红队自检"：验证评测系统能说"不"。

### 5.4 防线四：双模型交叉（cross_validate.py，已有）

- 每批选 2-3 个高分歧用例跑 glm vs deepseek 双模型：agree=true 增信；disagree → 人工仲裁并记入台账（R109/R110 先例）。

### 5.5 防线五：RETIRED 诚实制度

- 任何一轮因基础设施/竞态/数据污染不可信 → 轮 JSON 标 `RETIRED`（理由必填），**从判定统计剔除但保留文件**（不删除证据）；
- 全绿口径 = 排除 RETIRED；RETIRED 率 >5% 时停批查环境。

### 5.6 真实性事件响应

发现假绿/假阳 → ①停批 ②根因定位（判定器/竞态/数据）③修复+阴性探针复验 ④受污染批全部 RETIRED 重跑 ⑤台账 `TRUTH-INCIDENT` 条目（不可省略）。

---

## 6. 点位与用例的定期审计（每 5 批执行，脚本化）

### 6.1 审计触发

每 5 批（25 轮）或任一 TRUTH-INCIDENT 后立即。

### 6.2 审计清单（逐步执行，产出写入台账）

1. **点位价值表**：对 25+ 点位逐个统计——出现频次、kv 熵（恒定=0）、促成决策次数（翻台账）。恒定且零决策 → 移除或 D1 采样；高频高熵 → 考虑升 KPI 健康带。
2. **残差墙分析**：§2.1 的 wall 残差计算 → 未观测环节清单 → T1 立项。
3. **用例覆盖矩阵**：17+N 用例 × src 模块清单，空白格=无主模块 → 补用例或书面确认无需覆盖。
4. **负面占比检查**：§3.1 目标占比对照，低于目标 → 本期补负面用例。
5. **健康带重校准**：批均值漂移 >15% 的 KPI 重设区间（记 `BASELINE-RECAL`），防健康带腐化。
6. **数据源健康**：tendency/RAG 数据文件的条目数、话题分布、置信度分布（画像数据质量前置检查）。

### 6.3 审计产出

台账 `AUDIT R1xx` 节：点位增删决定+理由、新增用例列表、健康带变更、发现的疑点转入 §1.1 触发器。

---

## 6.5 测试维度总账

历史维度/负面族/数据蒸发教训 → `test-dimensions-ledger.md`（R142 建档，用户钦定防遗忘制度：新维度必登记、删维度必注明；常驻维度每轮批测自动覆盖）。

## 7. 迭代节奏与角色分工

| 节奏 | 动作 |
|---|---|
| 每轮（R1xx） | 主循环：§0 生命周期一环；台账+报告 §7 同 commit 更新 |
| 每批（5 轮） | 批测判定（§4.1/主报告 §4.3）；阳性抽查轮安排 |
| 每 5 批 | §6 审计；§2.1 差分探查；负面用例补充（若低于占比） |
| 每月/每 10 批 | §2.2 极端采样压力画像轮；§5.3 阴性探针；§3.3 清单复核 |
| 每 50 轮 | 阶段汇报（用户交付物）：批次曲线/缺陷计数/主题三观测面进展 |
| 持续 | 主题三观测面（§1.3）每个都要有"最近一次数值"——任一观测面 >2 周无数值 = 该面停摆，优先恢复 |

---

## 8. 本文档更新纪律

1. 机制变化（新增触发器/防线/用例类别）→ 当轮更新本文档并同 commit 推送；
2. 数字类内容（用例数、占比、频率）→ 每 5 批审计时刷新；
3. 与主报告冲突时：**方法以本文档为准，状态以主报告 §7 为准**；
4. 本文档也遵守记忆分层纪律：不记轮次细节，只记方法与规则。

### R436（已完成）端到端 BRJ 网格: 承重 token 降幅
- 二进制 sha16 `45c37dd5b88ffcf2`（NativeAOT, IL 警告 0, V0 形态闸 True）
- p12: A 27654 tok → BRJ 19557 tok = **29.28%**（目标 30.0% ⇒ 未达, 差 0.72 pt）; p8: A 18481 → BRJ 12122 = **34.41%**
- J 本地化: 远端请求 7 次 → 0（本地 7/7）; 单独贡献 3.92 pt
- 门质量: 假阴性 0 / 假阳性 0（acc 1.0）; 负控 BP 净亏 -6.92%
- 证据: `eval/rover/r436/README-evidence.md`｜判据: `docs/plans/v0.57.0-r436-e2e-brj-token-kpi.md`

## R439（2026-09-15）域扩展验证 — 长任务 V20 + p8 复测（主线上承重口径）
- 目标: 证明 R438 修复（本地消化轮不回放内联块）非 p12 特例 ⇒ p8 复测 + 新增长任务网格 V20(20 轮)。
- 结果: 严口径降幅 p8 **37.9%** / V20 **45.31%** / p12 37.37%（R438）；fn=fp=0；A 臂分母不变性成立。
- 预注册→实测偏差 ≤1.38pt；V20 分母外推误差 −0.4%。
- 证据: `eval/rover/r439/README-evidence.md`；计划: `docs/plans/v0.59.0-r439-domain-extension.md`。
- 下轮候选: ①BP 负控在 V20 上重测（恢复 L2 净增量）②BRJ-V20 同臂复跑（确定性）③判官本地成功率 11/13 的 2 例回退根因（prompt 形状）④把 V20 的可跳轮**位置**作为单变量（早簇 vs 散布）验证 R437 位置权重假设。

## R440（2026-09-15）一轮任务降幅的**分档实测**（主线: 把 R437 的外推变实测）
- 目标: 用户口径「一轮任务可能多次链调用」⇒ 分档实测 单次/短/中/长 × 可跳轮位置 × 有无本地设备（负控）。
- 结果（远端 token 口径, 同网格 A 臂分母）: 单次 N=1 **−3.95%**（净亏）｜短 N=4 可跳 1/4 **+32.24%**｜中 N=8 37.90% / N=12 37.37%｜长 N=20 散布 45.31% / **晚簇 48.57%**｜长 N=20 零可跳 **−2.40%**｜负控（无设备·晚簇）**−5.47%**。
- 门质量: 全 BRJ 臂 fn=0/fp=0/acc=1.0（V5 含 7 条未经 r1 实测的新文本 ⇒ 零误杀）; A/BRJ 的澄清吞并集合逐网格一致。
- 位置单变量: V4(晚簇) − V20(散布) = **+3.26 pt**；预注册模型给 −1.2 pt（符号相反）⇒ C7 FAIL。
- 预注册判据: C1/C4/C5/C6 PASS；**C2/C3/C7 FAIL**，根因全在预测器（跨网格 A 分母下标位移 +9.25% / 被跳轮的 A 成本漏计 / δ 线性外推）。
- 事后校核: 逐调用开销 **δ ≡ 77 tok 常数**（5/5 网格逐轮一致）+ 同网格实测分母 ⇒ 重锚模型 **5/5 ≤0.47 pt**；二阶项 = 被跳轮内联块不再回放（散布 2227 tok, 晚簇 ≈0）。
- 证据: `eval/rover/r440/README-evidence.md`；计划: `docs/plans/v0.60.0-r440-length-ladder-measurement.md`；判据: `eval/rover/r440/compare-r440.json`。
- 下轮候选: ①V4/V2b 同臂复跑（确定性）②p8/p12 realized 配置并入同一两参数律 ③中簇补点定位位置曲线 ④小占比格找收益窗口下界。

## R448（2026-09-15）判官 prompt 侧「限长思考」消融 → **负结论**（本地生成侧压缩通道全部关闭）
- 臂: J0(产品/512) / T2(限长 prompt/512) / T1(限长 prompt/128) / NC1t(T1+真错配 prev)，18 对忠实语料。
- 读数: gen 178.6 → T2 **138.5**（0 截断）→ T1 **119.7**；T1 截断 **11/18**、可解析 0.3333；agree(T1,J0)=**0.1667**、agree(T1,归档)=**0.1667**。
- 判据: C6 PASS，C1/C2/C3/C4/C5 功能性红 + C7 判定项缺陷（CH6 修正口径 18/18 PASS）。
- 机制: 思考长度不受 prompt 指令控制（T2 median 138.5）且思考承重（改 prompt ⇒ 判决漂移 0.4444）⇒ 压思考=改判决；压预算=截断=fallback 远端=更贵。
- 反事实上限: 含本地真值口径 33.32% → 34.38%（+1.06 pt），收益/风险不成比例。
- 器械: G1 重建 18/18｜G1b 忠实性 9/9｜G2 prev 多样性下界（3 / 长 1）｜**G3 真错配 8/8**；C7 恒等式 62/62 闭合 R447 C5 债；跨轮确定性 Σgen 3215/3215 相同。
- 证据: `eval/rover/r448/README-evidence.md`｜计划: `docs/plans/v0.68.0-r448-judge-think-length-cap.md`｜登记: registry `r448.judge-think-length-cap`。
- 下轮候选: ①判官**预填充**侧压缩（2764 tok/10 调用）等价性消融 ②判官+门合并单次本地调用 ③门通道同构消融 ④把「跨臂相等类断言须先机检臂定义可满足」升为器具通用闸。

## R441–R478 轮次索引（2026-09-15 首次回填，R478 扩展到 R478；机取自 `docs/verification-registry.json`，勿手改）

> 每轮的权威内容在其 `docs/plans/v0.xx…` 计划、`docs/improvements.md` 对应块与 registry 行；本表只做索引与状态汇总，避免双写漂移。R449 起全部未 push（推送暂停令）。

| 轮 | registry id | level | 能力/结论（截断 90 字） |
|---|---|---|---|
| R441 | `r441.gain-window-floor-and-position-curve` | L3 | **收益窗口下界 + 位置曲线**（同网格实测 A 分母, 8 臂, 被测二进制 sha 与 R439/R440 同）: 单跳 1/8 → **+13.77%**（A 17260→… |
| R442 | `r442.accounting-and-asymmetry` | L2 | **口径钉死 + 两臂内联块不对称定量 + D7 分母断言**（纯离线复算 R441 档案）: 三档口径 ①D_remote W8 13.77/W20 3.20/M20 46.19… |
| R443 | `r443.local-token-truth-and-replay-ablation` | L2 | **本地 r1 成本 tokenizer 真值化 + 「被跳轮不回放」同网格单变量消融**: 产品侧新增真值遥测 (tokens_evaluated/prompt_n/gen, l… |
| R444 | `r444.instrument-acceptance` | L4 | L2 器具验收面(正控+负控成对) |
| R444 | `r444.prefilter-cost` | L3 | 前置门本地 r1 成本下降(真值口径) |
| R444 | `r444.prefilter-equivalence` | L3 | **廉价必要条件前置 (¬Ack ⇒ Pass) — 可证等价 + 含本地真值口径首次转正**: 把既有的后置否决 `Skip ∧ ¬MechanicalAck ⇒ Pass` 反… |
| R444 | `r444.separability-precheck` | L4 | R423 可分性预检(Skip⇒Ack 必要性) |
| R444 | `r444.short-tier-truth` | L3 | 短档/单跳档本地真值补列 |
| R444 | `r444.status-single-audit` | L4 | L3 单一审计面(registry 派生) |
| R444 | `r444.writer-arbitration` | L4 | L4 写者仲裁(心跳+pre-commit) |
| R445 | `r445.judge-prefilter-controls` | L4 | 器具三控(正控/负控/fail-closed) |
| R445 | `r445.judge-prefilter-separability` | L1 | 判官侧机械前置的可分性(消息面) |
| R445 | `r445.prev-reply-face-indicative` | L1 | 上一轮来源面的指示性上界(不作判据) |
| R446 | `r446.channel-marks-multivariant` | L3 | 器具: 判官 prompt 多形态派生(公共前缀标记) + 零回归 |
| R446 | `r446.judge-determinism` | L1 | 判官路径确定性(真机产品路径) |
| R446 | `r446.judge-prompt-compact` | L1 | 判官 prompt 瘦身消融(开关默认关) |
| R446 | `r446.zero-token-settlement-precheck` | L1 | 判官 0-token 结算可行性(消息面) —— 负结论 |
| R447 | `r447.judge-decode-constraint-grammar` | L1 | 判官解码侧约束(单字母 GBNF)等价性真机消融 —— 负结论: 生成可降 98.9% 但判决不等价(18/18 恒 A), 不得启用 |
| R448 | `r448.judge-think-length-cap` | L3 | 判官 prompt 侧「限长思考」（保留思考、只压缩长度）真机消融 —— 负结论: 生成仅降 33.0%（178.6→119.7）且预算 128 下 61.1% 思考被截断、与产品… |
| R449 | `r449.real-traffic-external-validity` | L3 | 真实流量外部效度裁决 (机械面, 与判官无关): 可跳轮 = Ack ∧ ¬MechanicalPass ⇒ state.db 1542 轮中 ack 0/1542、gate_el… |
| R449 | `r449.think-memory-switch` | L2 | think-memory 四档开关 (on 默认/off/recall0/write0) + 反空心召回计数 + HitCount 与 refs 采纳次数分离 (修「命中恒 0」根… |
| R449 | `r449.turn-gate-parse-crosslang-fixture` | L2 | 门判解析器 (TurnGateJudge.Parse) 跨语言同位夹具: 13 用例在 C# 与 py 两侧逐条同判, 解析索引口径 = UTF-16 码元 (emoji 代理对不… |
| R450 | `r450.gate-prompt-anchor` | L2 | 门判**实发 prompt** 落盘锚 (env AGENTFRAMEWORK_GATE_PROMPT_DUMP, 默认关/零产品变更) + 零反射 JSON 转义 + UTF8 … |
| R451 | `r451.real-traffic-reprobe` | L2 | 真实流量外部效度探针重跑: 文本层锚(tpl_len=280/seed_sha16 与 R443 逐位相同)与行为层(I1 正控)分离判据; 残余失锚定位=调用/解码面; 判决 V… |
| R452 | `r452.product-native-real-traffic` | L2 | 产品原生跑真实语料(零重建): 生产行为门 r1=0/Skip=0; 判官强制面 14 票 S 全被机械认可族守卫否决(13 票落『继续下一轮』驱动类); 门判 prompt 无 … |
| R453 | `r453.absorb-channel-audit` | L2 | 真实分布 token 通道台账 + 吞并轮通道审计: 7/51=13.7% 轮 0 远端调用(上界省 54,852 tok=14.0%); 前置门省 14 次本地 r1=7,204… |
| R454 | `r454.codex-external-contrast` | L2 | 外部对照: codex-cli 0.154.0 真实请求面(捕获字节) vs click-agent —— 静态面 34,542B/9工具 vs 4,300B/0工具; codex… |
| R455 | `r455.module-coverage-ab` | L2 | 同环境/同输入/同模型(deepseek-flash)/零重试的模块覆盖对照: 我方 0/4 产物 + 1 次问询 vs codex 4/4 产物 + 0 问询; M1 缓存 86… |
| R456 | `r456.action-loop` | L2 | 动作环(声明/解析/回灌/执行)链机制修复: 同套件(同夹具/同6轮/同模型)产物 0/4 -> 2/4(count.txt=4, merged.txt=ALPHA/BETA/GA… |
| R457 | `r457.effect-closure` | L3 | 动作环效果收口(真机 E2E): 同夹具产物 2/4 -> 4/4 (stats.txt=chars=14, first.txt=R455 fixture note), 磁盘伪造 … |
| R458 | `r458.humanized-continuation` | L2 | 承接轮人性化(真机 E2E, 同夹具/同 6 轮/同模型): T5「继续」→ 逐项承接 4 个真实产物 + 「继续什么」反问 + 3 个具体可选项 (固定示例菜单 `(如: 搜索/… |

| R460 | `r460.brevity-menu-cache` | L2 | 承接轮精炼 + 菜单单源 + 命中率/token 归因 (真机 E2E, 同夹具/同 6 轮/同模型, 唯一差异=二进制): T5 回复 241→160 字 (-33.6%),… |
| R461 | `r461.contract-not-front-and-hit-budget` | L2 | 契约声明不上前台 + 零字节产物可见 + 每轮注入预算收口 (真机 E2E, 同夹具/同 6 轮/同模型, 唯一差异=二进制; 夹具两侧 md5 fe1f5530446bd4c… |
| R462 | `r462.language-agnostic-recall` | L2 | 语言无关召回探针 (承 R447 用户令「管道内一律标通用代码逻辑」): 删 ContextAssembler 工作区召回的**硬编码后缀白名单** (源码逐字列语言后缀), … |
| R462 | `r462.recall-reality-gate` | L2 | 召回-现实一致性闸 (机制, 非提示词补丁): 召回块/记忆块/工具回灌面里引用的**路径样事实**由当前工作区文件系统裁决, 不一致即显式标 [核验✗ …] (一致时才标 [… |
| R462 | `r462.weight-probe` | L2 | 本地判别权重档位探针 (回答用户「现役 r1 权重够不够」, 承用户令改用 3B): 28 条**产品实发**门判 prompt (14 条 msg='继续下一轮' 标签=产品… |
| R463 | `r463.local-gate-model-switch` | L2 | 本地判别通道权重档位切换 (用户令「改用3b 并且 删除多余模型 3b q4」): 现役 r1-distill-1.5B-Q4 → Qwen2.5-3B-Instruct-Q4… |
| R463 | `r463.model-cleanup` | L1 | 冗余权重清理 (用户令): 先算 (bytes, sha256) 落台账再删。删除 1.5B-Q4 (1,117,320,800 B) / 1.5B-Q8 (1,894,532… |
| R464 | `r464.local-channel-config-fail-closed` | L2 | 本地判别通道「配置错配」fail-closed：消灭 `lc.IsReady ? lc.ModelPath : baseOpts.ModelPath` 静默回退默认权重（R46… |
| R464 | `r464.settle-sentinel-and-cross-round-determinism` | L1 | 结算器具修正 + 跨版本确定性等式: ① 非本地调用哨兵 '-1' 不再当读数求和（旧版把 12 条哨兵累成 -8/-12 假读数）; ② 预注册 C6 口径写错 ⇒ 保留 F… |
| R465 | `r465.embedder-channel-three-state` | L1 | 嵌入(bge)通道同形三态接线: ServiceCollectionExtensions 的 embedder 注册改用 LocalChannelWiring.ResolveE… |
| R465 | `r465.filelock-release-no-unlink` | L2 | FileLock 释放路径不得 unlink 锁文件（锁身份 = inode，存在性 ≠ 是否被持有）: Release 只关 fd；TryBreakStaleLock ⇒ 只… |
| R465 | `r465.local-channel-warmup` | L1 | 本地生成通道预热（AGENTFRAMEWORK_LOCAL_WARMUP=1）: 宿主启动即调 ILocalGenerationPort.WarmupAsync（接口默认实现 … |
| R465 | `r465.pure-repeat-skip` | L2 | 纯复述族直 Skip（真诉求轮可跳面）: TurnGateJudge.IsPureRepeat 三道全过（① 完整复述标记 ② 去标点后 ≤14 字且字符全属复述白名单 ③ 无… |
| R466 | `r466.repeat-replay-priority` | L2 | 本地已确定性结算的轮次（纯复述 ⇒ 回放上一条答复原文）优先级高于 R458 承接反问收口：收口面读同一结算类后不再覆盖回放，用户可见答复 = 上一条答复逐字。判据单源 = C… |
| R466 | `r466.settle-kind-single-source` | L4 | 口径单源机检（形式门）：① 主链只准引用常量 ContinuationBrief.SettleRepeatVerbatim，字面值只准出现在 ContinuationBrief… |
| R467 | `r467.arm-flag-comparability-gate` | L4 | 臂可比性闸(fail-closed)：同名臂跨轮 arm_flags 必须逐键同，不同 ⇒ 该臂读数 VOID_NOT_COMPARABLE(不可作分母/不可同题对比)；异名异… |
| R467 | `r467.call-decomposition-ledger` | L2 | 远端调用分解台账：桩侧 calls-<ARM>.jsonl 逐条分类(main/judge/micro/other) + 宿主 correction_judge 路由(sour… |
| R468 | `r468.gate-rules-port-diff` | L2 | 门判规则 Python 端口与产品判据的差分一致性: 端口从 src/agent.modelqueue/LocalGenerationPort.cs 正则派生(7 组规则: A… |
| R468 | `r468.real-traffic-composition-external-validity` | L2 | 降幅外部效度机检：用产品判据（源码派生端口 + 产品差分校验）在【真实用户轮语料】(state.db 只读; 1,179 真实轮, 剔除 1,406 系统注入) 上复算机械可跳… |
| R469 | `r469.hit-ceiling-bands` | L2 | 命中率理论上限分档: 把用户轮长度从命中率分母剥离, 机检真实轮(400)在四档下的命中上限与达97%所需前缀; 显式声明长档(>93 tok)结构性不可达(86.8~96.2… |
| R469 | `r469.main-call-prefix-stability` | L2 | 主调用 prompt 前缀逐字节稳定性(离线, 无 llama-server): 从桩侧落盘全量 messages 复算逐对公共前缀/新增字符数; 门控臂 R 主调用 5/5 … |
| R470 | `r470.cache-channel-attribution` | L2 | 真实流量命中归因通道(跨会话共享前缀)打点: 无同会话前驱的调用命中归因 shared_prefix(否则 -1, 禁双计), 只在既有 -1 之上补通道不回收口径; 三处 d… |
| R470 | `r470.real-feed-cache-actuals` | L2 | 真实远端调用(非桩)缓存实测: host.jsonl llm_call 43 条 ⇒ 命中占比 45.44%(hit 59518/prompt 130974), 命中量饱和 2… |
| R471 | `r471.channel-aggregation-emitted` | L2 | 分通道命中聚合器读**产品实发字段**: scripts/kpi_cache_hit.py 只读 kv.cache_channel/shared_prefix_hit_toke… |
| R471 | `r471.derived-vs-emitted-separation` | L2 | 派生 vs 实发分离(诚实面): 真实流 43 条 llm_call 中**含 cache_channel 字段者 0 条(0/43)** ⇒ R470 的「shared_pr… |
| R472 | `r472.criteria-posthoc-and-mechanism-law` | L2 | 事后判据处置 + 机制定律: (a) 预注册 C7(判定函数自检)判 FAIL 的原判保留不覆盖, 根因定位为 v1 CAP 分支阈值与前缀臂尺寸不自洽(P_MID 需 >= … |
| R472 | `r472.prefix-cache-no-provider-cap` | L3 | 真机受控实验裁决「远端命中饱和成因」: 8 次真实调用(deepseek-flash, 与 config/base/models.yaml:9,16 同模型同端点), 共享前缀… |
| R474 | `r474.provider-truth-denominator-arms` | L3 | KPI 分母升级: 供应商 usage 真值双臂(门关 Arole 20 调用/76094 token vs 门开 R 9 调用/32769 token) ⇒ 总 token … |
| R474 | `r474.quality-regression-evidence` | L2 | 真端点暴露的回复质量面: R 臂 12 轮中 6 轮模板应答 + 3 轮用户可见「模型未产出正文」横幅(t1/t7/t8), 而同轮 Arole 为 371-644 字实质回答… |
| R474 | `r474.relay-instrument-and-budget-guard` | L4 | 真转发中继器具: 双证据(请求体落盘 + 供应商 usage 落盘) + 预算闸 fail-closed(cap 0 -> HTTP 402 且零外发); 负控/正控成对(G1… |
| R475 | `r475.repeat-replay-substantive-guard` | L2 | 纯复述轮的回放守卫: 只有存在**可回放的实质答复**才允许本地消化; 上一条为空/模板/空正文徽标 ⇒ 撤销 Skip 降级远端(禁以模板冒充答复)。判据单源: 用户轮 Is… |
| R475 | `r475.recover-channel-accounting-fields` | L2 | llm_call_recover 行补齐 prompt_tokens/cache_hit_tokens/cache_miss_tokens/cache_hit_rate(与 l… |
| R475 | `r475.usage-truth-twin-column` | L2 | 双列并账(供应商 usage 真值列 vs 产品自记列): 硬分离禁混算; recover 缺字段 ⇒ unreconciled(禁按 0); 唯一跨列运算 gap.* 显式列… |
| R476 | `r476.band-aware-redline-verdict` | L2 | 红线判定**分档化**(只增不改): 单值 0.97 不变, 但判据目标改为 min(红线, 该轮结构上限 prefix/(prefix+用户轮+21)) ⇒ 5 态判决 no… |
| R476 | `r476.band-kpi-instrument` | L2 | 分档聚合器具(达成轮占比 + 分通道) + **常数与产品源码 fail-closed 机检**: py 侧红线/承接开销/缓存单元/档界 与 PromptCacheRedli… |
| R476 | `r476.pricing-fail-closed` | L2 | 计价面 fail-closed: 无显式价格表 ⇒ pricing.status=unreported 且 cost_cny=None/hit_discount_known=F… |
| R476 | `r476.evidence-binding-round-param` | L2 | 证据绑定器具轮号参数化: bind_evidence.py 加 --round(默认 = 历史常量 AUDITED_BY_ROUND ⇒ 无参调用逐字不变), 消除「audit… |
| R477 | `r477.replay-guard-real-e2e` | L3 | R475 复述回放守卫**首次真机复演**: 复述轮(t6「再讲一遍。」/t9「从头再说。」)用户可见回复 = 前序**实质**答案逐字回放(298 字符, 非模板/非空正文徽… |
| R477 | `r477.kpi-drop-real-endpoint-arms` | L3 | 真端点双臂 KPI 复测(同网格 task-p12/同二进制 agenthost db187e0eae7f26ea/仅门控不同): 供应商 usage 真值(A) 73649 … |
| R477 | `r477.band-fields-live` | L3 | R476 分档 7 字段**实发存在**: 真机每主调用遥测行均带 cache_band/band_source/band_growth/ceiling/target/marg… |
| R477 | `r477.empty-body-root-cause` | L3 | 用户可见「⚠ 模型未产出正文」徽标定因: 真机 20/20 空正文调用的 `finish_reason == tool_calls`(请求携带 4 个 tools), `max… |
| R478 | `r478.empty-body-cause-protocol-only` | L2 | 空正文定因机制化(承 R477 真机 20/20 `finish_reason == tool_calls` 事实): ① 定因判据**只取上游协议字段**(finish_re… |
| R478 | `r478.request-turn-causal-binding` | L2 | 请求-轮次**因果绑定**(替代时间窗归属): `QueueResponse.RequestId` 单调签发(`entry.Id#seq`, `Interlocked`, AO… |
| R478 | `r478.hit-rate-cold-steady-split` | L3 | R477 真机 usage(**供应商真值**, 恒等式 `hit+miss==prompt` 21/21 + 10/10 逐行成立)命中率按 **R456b** 分列: 稳态… |
覆盖自检: 轮号 [441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 474, 475, 476, 477, 478]；registry rows=146，updated_round=R478。**缺登记行轮号: 459, 473**（**该号未被使用(improvements.md 亦无块): 459, 473**）。

## R479 轮次索引增量（2026-09-16 机取自 `docs/verification-registry.json`，勿手改）

器具: `python3 eval/tools/master_plan_round_index.py R479`（只读 JSON，输出可直接粘的 Markdown 行）。

| 轮号 | id | level | 能力摘要 |
|---|---|---|---|
| R479 | `r479.local-decision-calibration` | L2 | **精准语义 = 校准 LLM 返回后本地该做什么的单一出口**(`src/agent.modelqueue/LocalDecisionMap.cs`) … |
| R479 | `r479.responses-io-wire` | L2 | 真实 I/O 数据格式按 **Responses 协议** 落成 typed 面(`src/agent.modelqueue/ResponsesWire.cs`)：① **字段分离** … |
| R479 | `r479.tool-decl-single-source` | L3 | 工具声明面**单一事实源**(`src/agent.modelqueue/ActionToolSpec.cs`)：一份规格派生两种线格式 … |

覆盖自检: 轮号 ['R479']；registry rows=**149**，updated_round=**R479**。
**缺登记行轮号: 无**

> 取代关系: 本增量取代下方「R441–R478 轮次索引」段的 `registry rows=146 / updated_round=R478`（row 数 146 → 149，最新轮号 R478 → R479）。旧段正文保留为历史读数，不再作为当前口径。

## R481（2026-09-16）recall 模块收口 — 当前基线（承焦点令 A/B/C）

- 状态: **D9 面已验收**（`agent.recall.tests` **14/14**，rc=0，trx 结果行 14，Failed 0 / Skipped 0）
- 权威计划: `docs/plans/v0.97.0-r481-consolidation.md`；缺陷与证据台账: `docs/reports/r480-recall-test-ledger.md`
- 本机实跑读数（2026-09-16）: 测试 **2/13 → 12/13 → 14/14**；`OutOfMemoryException` **16 → 0**；用例耗时 **2m12s → 391 ms → 949 ms**（多 1 用例）；`agent.recall` 库 **rc=0 / 0 warning / 0 error**
- 已修 7 处真根因（F1–F7）+ 本轮 **D9**（交替核验：stamp 低位记「上轮剪枝」⇒ 核验轮强制 readdir+stat；核验轮 `DirsPruned == 0` 单列 `VerifiedAllDirs`），**全为读写契约/缓存可见性错误，无一处改断言凑绿**
- 证据器具: `python3 eval/recall/r481/check_r481d9.py` ⇒ `verdict=PASS`（C1 源码派生 / C2 真跑 trx 14 行 / C3 语义锁存 / 变异负控 3/3 翻红）；`eval/recall/r481/verdict-r481d9.json`
- 【探索】判据基线（R481-A，Python 代理面）: 解析率 **0.8508**（目标 ≥0.90 ❌）/ 悬空 **0.1492**（✅ ≤0.35）/ 相对引用落地 **0.2718 = 309 条**（❌）/ 地址覆盖 **p50=0、76.11% 零地址**（❌）/ 跨 URL **2,720 = unreported**
- 诚实边界: `agent.recall` 尚未并入 `agent.host`（本面无 AOT 重发布验证）；recall **未入链** ⇒ 对 R413 主线「tokens −30%」**本轮无贡献**（不冒充）；旧格式 store 兼容**只推理未实测**；内容级哈希兜底**未实现**（D9 只保证最多滞后 1 轮）；全程未 push（`PUSH_PAUSED`）
- 本侧独立复核（**R481-E**，2026-09-16）: 全不采信对侧自述、逐项自跑 —— ① `dotnet test src/agent.recall.tests/agent.recall.tests.csproj -c Release` ⇒ **rc=0 / Failed 0 / Passed 14 / Total 14 / 576 ms**（新用例 `:404-456` 等字节改写 `钾`→`铷`，`:379` 原断言未放宽）；② `dotnet build src/agent.recall/agent.recall.csproj -c Release` ⇒ **rc=0 / 0 warning / 0 error**；③ `python3 eval/recall/r481/check_r481d9.py` ⇒ **rc=0 / `verdict=PASS`**（变异负控 3/3 翻红）。**归属**: D9 实施由 cron 兄弟会话（`cron:9a97763d5fcd`）在 07:42–07:45 完成，本侧角色 = 独立复核 + 文档对账（非重复实施）。
- 下轮候选: ① `VerifyMode.Hash` / 周期全量核验兜底 ② ~~相对地址按引用方目录解析~~ **已实施（R481-E，见下）** ③ G2 四条判据锁进 `prereg_r481a.json` ④ 1e5 规模臂 ⑤ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）
- **R481-E G2 增量（本侧实施，2026-09-16）**: `src/agent.recall/RecallLinks.cs` 新增 `ResolveReferrerRelative`（纯字符串代数，不触磁盘）+ `Extract(..., string? referrerPath = null)`；接线 `src/agent.recall/RecallIndexWriter.cs:70` 传 `doc.Path`。**只改 `./`、`../` 显式相对引用**；根相对与绝对 URL **不改写**（root-fallback 16,965/20,155 是主力通路，改写即回归）；**越根 fail-closed 原值返回**。新增用例 `Relative_References_Resolve_Against_Referrer_Directory` ⇒ `agent.recall.tests` **rc=0 / Failed 0 / Passed 15 / Total 15 / 455 ms**（14 项零回归）。**诚实边界**: G3 0.2718 属语料侧 Python 代理面读数，本产品面改动**尚未在语料上重测** ⇒ 不宣称 G3/G1 达标。
- **R481-F 语料侧重测（本侧实施，2026-09-16）**: 旧端口手写规则与产品漂移（后缀白名单 / 裸名计入相对档 / `lstrip` 兜底）⇒ 重建**源码派生端口**（`eval/recall/links_port_r482.py`：规则正则派生 + 期望值取产品自身断言 + 6/6 变异被抓）。**新口径读数**（6,658 文件）: 候选 **76,404** / 解析率 **0.1450 ❌** / 悬空 **0.8550 ❌** / 显式相对引用 **660 → 落地 72 = 0.1091 ❌** / 地址覆盖 **p50=5 ✅** / 越根 fail-closed **2** / 绝对路径形态 **7,462** 单列。**通路分解**: markdown **81.25%**（65/80）· 裸 URL 全 unreported · 相对地址串 **14.43%**（悬空 64,004 = 99.98%）⇒ **G1/G2 在全候选档上结构不可达**（接受规则只要求「含 `/` 且无空白」），相对引用改写可达面 **0.88%**（天花板 ≤ +0.88 pt）。旧口径同批对照 0.8504/0.1496/0.2650 ⇒ **口径变更，跨轮不可比**。证据: `eval/recall/r481b/port-corpus.json` + `eval/recall/prereg_r481b.json`（先于首跑落盘）；台账 R481-F 段。

- **R481-G（本侧，语料钉健康检查 + 分档口径预注册，2026-09-16）**: ① 独立复核 R481-F（不采信自述）: `links_port_r482.py --selftest` ⇒ **rc=0**（6/6 变异被抓）; `--out` ⇒ **rc=0**; 读数同向同量级 —— G1 **0.1449**（报 0.1450）/ G2 **0.8551**（0.8550）/ G3 **0.1086**（0.1091，72/663）/ G4 **p50=5 达标**; `by_origin` = markdown **0.8125**(65/96) / rel **0.1442**(10,831/75,106) / url **1,518 = unreported**; `old_arm.vs_registered_r481a.match=false` 已自标**不可比（语料漂移）**。② **发现（机制缺口）**: 器具只绑定 `corpus.files_sha16`, 不绑 commit/工作树 ⇒ 四个读数出现 **3 个不同语料钉**（`251b1c166eca7dbe`/6,659、`1000893f7926c08c`/6,658、`737b2cca752d55bc`/6,683; `head=ccb132b`, `dirty=37`）, 而**规则钉恒定**（`9e9104ca601f8849`）⇒ R481-F「两次独立运行核心字段逐字节相同」**只在同一语料成立**（其首跑 6,659 与第二跑 6,658 之间语料已漂移）, 且漂移**无报警**。③ 器具 `eval/recall/r481/check_corpus_pin.py`: 三态 fail-closed —— **UNIFORM rc=0 / DRIFT rc=1 / MISSING rc=3**; 负控真跑 **N1 rc=3 / N2 rc=1 / N3 rc=0**。④ 预注册 `eval/recall/prereg_r481g.json`（先于分档首跑）: 语料钉三元组 + 可比性规则（仅当 `(files_sha16, rule_source_sha16)` 全等才可同批对照）+ 分档判据（markdown ≥0.90 / root_rel ≥0.90 / explicit_rel ≥0.85 / slash_token 不设门槛 / url `unreported`）⇒ 全局 `resolved_rate≥0.90`、`dangling_rate≤0.10` 在含 slash token 的候选面上**结构不可达**, 判据收窄（计划 §1 G2 与 prereg_r481a 的 0.10/0.35 冲突一并收窄）。⑤ **诚实边界**: 分档读数**未取得**（器具需加 `by_subband` 输出）⇒ 不宣称任何档达标; `files_sha16` 不导出参与文件清单 ⇒ 漂移**可判不可归因**; 漂移观测早于本预注册落盘 ⇒ 按 R453 单列 `posthoc_observation`; Python 代理面, 不测产品面延迟/实现; 未 push。
- 下轮候选（R481-G 更新）: ① 器具加 `by_subband`（markdown / explicit_rel / root_rel / slash_token）并取得**分档首跑读数** ② 语料钉：读数落盘须同时记 `files_sha16` + `rule_source_sha16` + `HEAD` + `worktree_dirty_files`, 且导出参与文件清单以支持漂移归因 ③ 产品侧器具与端口交叉核对（`agent.recall` 度量模式）④ 1e5 规模臂 ⑤ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）。**不建议**继续投「相对引用改写」: 可达面 0.88%, 天花板 ≤ +0.88 pt。

## R482（2026-09-16）真机双臂：R478 修复上真链 + 主 KPI 首次达线（−32.21%）+ 模板兜底的质量代价

**因果链**：R477 真机复演留下两条未决 —— ①R478「tool_calls 因 Retryable=false ⇒ 不重试」只在**单测面**验过，未上真链；②R413 验收②「一轮 token −30%」在真上游同轮双臂里从未达线。R482 用同网格 `p12` + 同夹具 + 同二进制、唯一变量=门控，把两者一起上真链，并按 prereg 逐条判。

**改动（本轮无 C# 改动；只加器具与判据）**：`eval/rover/r482/{prereg_r482.json(先于首跑落盘),run_both_r482.sh,run_arm_R_only_r482.sh,check_r482.py,verdict-r482.json}`；`check_r482.py` 全部常量**源码派生**（取不到抛 MISS，不兜底）。

| 项 | Arole（门控关=生产等价分母） | R（r1 在管道内） |
|---|---|---|
| 远端调用 | 21 | 14 |
| prompt/completion | 68083/4551 | 44444/4793 |
| **total** | **72634** | **49237** ⇒ **−32.21%** |
| 12 轮 | ok 12/12 · events 37 · blocked 0 | ok 12/12 · events 37 · blocked 0 |

**判据（prereg 原文）**：H1 PASS（32.21% ≥30%，**R413 验收② 真上游同轮首次达线**）· H2 PASS（Δ7 ≥5，验收③ 可测增益）· **H3 FAIL**（`A.calls=21` 未 <21 ⇒ 按 prereg `fail_action` 记「R478 修复在真链上**无可测效果**」并单列，不重跑凑数）· **H4 FAIL**（`R.calls=14 >` R477 的 10；跨二进制参考列）· H5 PASS（恒等式逐行 21/21 + 14/14）· H6 PASS（逐字回放 `t6←t1`(434B)、`t9←t8`(606B)；旧误诊文案 0 次）。`verdict_all_pass=False`。

**H3 成因（post-hoc，机制在位/收益被漂移吃掉）**：`point='llm_call_empty_body'` 行 Arole 4 / R 2，`retry_skipped=True` 逐行成立，`empty_cause='tool_call'` 与上游 `finish_reason='tool_calls'` 4/4 对齐 ⇒ 修复**确实生效**；但**空正文基数 15（R477）→4（R482）**（同配置同夹具）⇒ 可省调用数被上游漂移抽空，`A.calls` 无位移。**结论收窄**：本轮只证「机制在位」，不证「调用数收益」。

**诚实边界（本轮最重要）**：−32.21% 中 R 臂 `t2–t5` 的用户可见答复是**同一条 21B 模板**（Arole 同轮为 4 条各不相同的实质短答）⇒ **实质答复轮 R 6 < A 12**，更严质量变体判红并单列 `checks_posthoc.quality_verdict_H6c_strict_variant`。即降幅的一部分来自「模板兜底」而非「本地 r1 生成替代远端」——与 prereg 预置边界吻合，**R483 第一顺位**。另有：单夹具单次无置信区间；上游真供应商可漂移（本轮实测漂移）；跨二进制只作参考列；本轮无 C# 改动 ⇒ 不重发布 AOT、不冒充新 AOT 证据（`binary_match=true`，实发 sha16 `6a9b7aed22a22f48` = prereg pin）。

**起手闸归因修正（可复用）**：R 臂首跑被闸（`MemAvailable=2590 < 2650`，Arole 的 llama-server RSS 未释放，同 R477）；加沉降等待后**仍红**且 `pgrep llama-server=0` ⇒ 真因是**本方 `dotnet test` 遗留 `VBCSCompiler`（RSS 206MB）**；`$HOME/.dotnet/dotnet build-server shutdown` ⇒ `2730MB` 通过、R 臂跑完 EXIT=0。即占用源不止 llama-server，**含本方编译服务器**。

- 下轮候选（R482-Q 修正）: ① ~~把模板兜底换成本地 r1 生成~~ **已撤销**（`ModelQueueRouter.cs:413-425` 载 2026-09-14 臂B 真机反证：r1 生成确认语退化；R475 回放守卫与之配套）⇒ 改为 **KPI 口径二分**（总体 −32.21% / 去常量兜底 11.78%）+ 可跳面合法性机检② 空正文基数漂移：Arole 臂加**基数记录/多重复臂**，让 R478 修复的调用数收益可测（本轮 headroom 被抽空）③ 起手闸器具化：把 `build-server shutdown` + 沉降等待并入 `run_both_*`（禁手抄）④ R481-G 遗留（`by_subband` 分档读数 / 语料钉四元组）⑤ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）


## R482-Q（2026-09-16）本侧独立复核 R482 + 常量兜底归属与质量面量化

**立场**：只读既有真机产物（`eval/rover/r482/{usage,turns}-{Arole,R}.jsonl`），**不重跑真链、不改 R482 判据 H1–H6**。预注册 `eval/rover/r482/prereg_quality_face.json`（先于首跑）；器具 `eval/rover/r482/quality_face_probe.py`（常量由 `src/agent.modelqueue/ModelQueueRouter.cs` 正则派生，取不到 ⇒ `rc=3` 弃权）。

- **主 KPI 独立复算**：调用 **21 / 14**、total **72,634 / 49,237**、降幅 **32.2122%** —— 与 R482 报告**逐值相同**（逐轮归属 35/35 全落区、零丢失）。
- **降幅构成（本侧新增面）**：`23,397` tok 节省中 **14,839 tok = 63.4%** 来自 `t2–t5` 四个**常量兜底轮**（`LocalSkipFallback`，0 次远端调用）；t6 回放（−1 调用）、t9 回放（−3 调用）；t1/t7 R 反而多花 2 次调用。
- **语义核验**：4/4 常量轮的用户文本均为**纯确认轮**（谢谢，收到。/ 好的，明白。/ 嗯嗯，知道了。/ 明白，多谢。）⇒ 兜底**零信息损失**；t7–t12 六个实质轮 R **全部走远端**（11 次调用）⇒ 实质问句零被吞。
- **去常量兜底口径**（代理假设，非实测）：`R' = 64,076` ⇒ 降幅 **11.78% < 30%** ⇒ **R413 验收②在该口径下不成立**。
- **答复级质量面**：R = **12 轮 7 个 distinct 答复**（重复组 `{t1,t6}`/`{t2..t5}`/`{t8,t9}`），Arole = **12/12 distinct**；重复全部来自**回放 + 常量**两类非 LLM 路径。
- **溯源（决定性）**：`ModelQueueRouter.cs:413-425` 注释载明 2026-09-14 臂B 真机实验 —— 让 r1 生成「确认语」**会退化**（复读前文并反问）⇒ 常量兜底是**产品决策**，配套 R475 回放守卫。
- **口径修正**：候选「模板兜底换本地 r1 生成」**不应重做**（已有真机反证）；正确下一步 = **KPI 口径二分**（总体 / 实质轮）+ 可跳面合法性机检（器具已给出）。
- **器具自证**：`--force-miss` ⇒ rc=3 弃权、`--swap` ⇒ 降幅符号翻转（−47.52%）、两次独立运行输出 **sha16 `6b8e7c33edb92ed6` 逐字节相同**。
- **诚实边界**：去常量降幅为代理假设下界；离线再分析，不测产品延迟/实现；未入 registry；未 push（`PUSH_PAUSED`）。

## R481 轮次索引增量（2026-09-16 机取自 `docs/verification-registry.json`，勿手改）

器具: `python3 eval/tools/master_plan_round_index.py R481`（只读 JSON，输出可直接粘的 Markdown 行）。

| 轮号 | id | level | 能力摘要 |
|---|---|---|---|
| R481 | `r481.recall-d9-alternating-verify` | L2 | **目录 mtime 剪枝盲区**修复 = 交替核验: 指纹头 stamp 改 `(stampTicks << 1) \| 上轮是否剪枝`(低位), 读侧 `(ticks >> 1)` + `(ticks & 1UL) != 0UL`; `pruneEnabled = PruneUnchangedDirs && store is not null && !prevScanPruned` ⇒ 上轮剪过的目录本轮**强制 readdir+stat 全量核验**(不读内容)，idle 轮仍剪枝；核验轮 `DirsPruned == 0` ∧ `VerifiedAllDirs == true` **单列**（不冒充「无变化」）… |
| R481 | `r481f.recall-link-port-derivation` | L1 | **链接面规则端口(源码派生)** —— 把产品 `RecallLinkExtractor` 的接受规则与显式相对引用解析基准移植成可批量跑的端口: 7 组规则常量由 `src/agent.recall/RecallLinks.cs` 正则 … |

覆盖自检: 轮号 ['R481']；registry rows=**151**，updated_round=**R481**。
**缺登记行轮号: 无**

> 取代关系: 本增量取代上方各段「轮次索引」的 row 数口径（149 → 150 → **151**，最新轮号 R479 → R481）。旧段正文保留为历史读数，不再作为当前口径。
> 机取复现: 本表由 `eval/tools/master_plan_round_index.py R481` 直接产出（2026-09-16 实跑 rc=0 / 336 B；新增 `r481f` 行后**二次实跑重取**，输出上表两行）；**禁手改**。

### R483 · 【探索】精度分档读数（判据仍未达标）
- 器具 `eval/recall/r483/bands_probe.py`（复用 R481-F 端口，规则 pin 两侧一致 `9e9104ca601f8849`）；读数 `eval/recall/r483/bands.json`。
- markdown **0.8125**（目标 ≥0.90 ✘）· root_rel **0.1608**（✘）· explicit_rel **0.0923**（目标 ≥0.85 ✘）· slash_token 7,508 全越根（无门槛）· url 1,541 unreported。
- 守恒 80+67,269+639+7,508+1,541 = 77,037 ✔；负控 `--nc-conservation` rc=2 ✔；语料钉对 R481-F = **DRIFT（不可比）**。
- 修正：external 未过滤（伪 0.6771→真 0.8125）+ 自身产物入语料（pin 漂移 6,711→6,713 ⇒ 排除后稳定 6,710）。
- 判定：分档后**三档全不达标** ⇒ 误差主因是**真链接语境的悬空**，非「slash token 混杂」；维持「不再投相对引用改写」。

### R483 附 · 真机起手闸器具化（修 R482 假归因）
- 新增 `eval/rover/r483/preflight_gate.py`：`build-server shutdown` → 沉降轮询 → 三态判定（rc=0 PASS / rc=2 GATE_BLOCKED / rc=3 MISS）。
- 实跑 rc=0（2758 MB / shutdown_done=true）；负控 `--nc-block` rc=2 ✔。**真机测量起手前必跑**。

### R484 · 【探索】微步骤隔离问询 → 本地 r1：探针判否 + 起手闸假阳性修复
- 器具：`eval/rover/r484/prereg_r484.json`（先落盘）+ `micro_local_probe.py`；读数 `eval/rover/r484/micro_local_probe.json`（`checks_posthoc` / `verdict` 字段）。
- 读数：H1 5/5 · H2 5/5→**post-hoc 4/5** · H3 3/4 · H4 local 0/1 vs remote 1/1→**post-hoc 1/1** · H5 max 4.09s。语义面 **2/5 空洞**（远端反而正确指出「隔离无前文」）。
- 判定：**微问询整体替换本地 = 否**（R475 反证同族）；残留 = **微问询形态分流**。
- 起手闸：`preflight_gate.py` 自匹配假阳性修复（排除自身+祖先+shell argv0）；差分负控 `--nc-selfmatch` rc=2 / 修后 rc=0；sha `1a64ceb6…`。**真机测量起手前必跑**。
- 注：本段为手写追加；**轮次索引表未刷新**（待 R484 入 registry 后由 `eval/tools/master_plan_round_index.py` 生成，禁手改该表）。
- 下轮候选（本段产出）：① **微问询形态分流**（含 `上一条/从头/刚才` 等指代词的隔离微问询 ⇒ 直接不发，省 1 次远端调用/条，零信息损失；无指代轻问询才谈本地化）；② 空正文基数可测化（确定性 stub 造 `finish_reason=tool_calls`+0 tool_calls，对 修前 `/tmp/pub_r476/agenthost` vs 修后 `/tmp/pub_r479v2/agenthost` 做调用数差分）；③ `blocker_cause` 标签精确化；④ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）；⑤ R481-G 遗留（by_subband 分档 / 语料钉四元组）。

## R485（2026-09-16）微问询形态分流预发送闸 — 实现 + H1 机检（**未跑真机臂**）

预注册 `eval/rover/r485/prereg_r485.json`（写在任何新测量之前；标记集合由**已录制流量**归纳 ⇒ 文中标注 post-hoc）。

| 判据 | 内容 | 本轮读数 |
|---|---|---|
| H1 | 已录制真机流量上逐条自足判定: 微组 7/7 skip ∧ 主组 0/14 误伤 | **PASS**（真 C# 闸 × `calls-Arole.jsonl`；`MicroStepGateTrafficTests` 机检） |
| H2 | 真机臂: 闸开臂 `micro_step_skipped>0` 且远端调用数 < 同夹具基线 | **未跑**（无真机读数） |
| H3 | 双臂差分总 token 降幅 ≥30% | **未跑**（离线投影仅 8.30% token / 33.3% 调用，且投影≠真机） |
| H4 | 负控: 自足问句不误伤 + 空标记表 fail-closed | **PASS**（`--nc-selfcontained` rc=0；`--nc-empty-markers` ⇒ 0 拦截 + rc=3 弃权） |
| H5 | 改链代码后 AOT 重发布成功且 IL 警告 0 | **PASS**（rc=0 / IL 0 / 15,363,728 B / `03c77d56e8c485af…`） |

- 单测 24/24（`--filter MicroStep`，含 2 条真语料机检）。器具 H1 读数 sha16 `596e350b0516abae`。
- 关键读数：Arole 拦 7/21 调用（33.3%）、6,032/72,634 token（8.30%）；R 臂 4/14（28.6%）、3,089/49,237（6.27%）——**均为离线投影**，非真机重跑。
- 判定：闸在**离线真语料面**成立（零误伤、失败面 fail-closed）；**R413 验收②（≥30%）本轮未取得真机证据**，H3 记「未跑」而非「未达」，不得据此宣称降幅。

### R485 · 轮次索引增量（机取自 `docs/verification-registry.json`，禁手改）
| R441 | `r441.gain-window-floor-and-position-curve` | L3 | **收益窗口下界 + 位置曲线**（同网格实测 A 分母, 8 臂, 被测二进制 sha 与 R439/R440 同）: 单跳 1/8 → **+13.77%**（A 17260→BRJ 14884）、单跳 1/20 末轮 → **+3.2 … |
| R442 | `r442.accounting-and-asymmetry` | L2 | **口径钉死 + 两臂内联块不对称定量 + D7 分母断言**（纯离线复算 R441 档案）: 三档口径 ①D_remote W8 13.77/W20 3.20/M20 46.19（逐位复现 R441）②D_content-sym 13.7 … |
| R443 | `r443.local-token-truth-and-replay-ablation` | L2 | **本地 r1 成本 tokenizer 真值化 + 「被跳轮不回放」同网格单变量消融**: 产品侧新增真值遥测 (tokens_evaluated/prompt_n/gen, llama-server 上报) + 反事实诊断开关 AGEN … |
| R444 | `r444.instrument-acceptance` | L4 | L2 器具验收面(正控+负控成对) … |
| R444 | `r444.prefilter-cost` | L3 | 前置门本地 r1 成本下降(真值口径) … |
| R444 | `r444.prefilter-equivalence` | L3 | **廉价必要条件前置 (¬Ack ⇒ Pass) — 可证等价 + 含本地真值口径首次转正**: 把既有的后置否决 `Skip ∧ ¬MechanicalAck ⇒ Pass` 反解为不变量 `Skip ⇒ Ack`, 其逆否 `¬Ack  … |
| R444 | `r444.separability-precheck` | L4 | R423 可分性预检(Skip⇒Ack 必要性) … |
| R444 | `r444.short-tier-truth` | L3 | 短档/单跳档本地真值补列 … |
| R444 | `r444.status-single-audit` | L4 | L3 单一审计面(registry 派生) … |
| R444 | `r444.writer-arbitration` | L4 | L4 写者仲裁(心跳+pre-commit) … |
| R445 | `r445.judge-prefilter-controls` | L4 | 器具三控(正控/负控/fail-closed) … |
| R445 | `r445.judge-prefilter-separability` | L1 | 判官侧机械前置的可分性(消息面) … |
| R445 | `r445.prev-reply-face-indicative` | L1 | 上一轮来源面的指示性上界(不作判据) … |
| R446 | `r446.channel-marks-multivariant` | L3 | 器具: 判官 prompt 多形态派生(公共前缀标记) + 零回归 … |
| R446 | `r446.judge-determinism` | L1 | 判官路径确定性(真机产品路径) … |
| R446 | `r446.judge-prompt-compact` | L1 | 判官 prompt 瘦身消融(开关默认关) … |
| R446 | `r446.zero-token-settlement-precheck` | L1 | 判官 0-token 结算可行性(消息面) —— 负结论 … |
| R447 | `r447.judge-decode-constraint-grammar` | L1 | 判官解码侧约束(单字母 GBNF)等价性真机消融 —— 负结论: 生成可降 98.9% 但判决不等价(18/18 恒 A), 不得启用 … |
| R448 | `r448.judge-think-length-cap` | L3 | 判官 prompt 侧「限长思考」（保留思考、只压缩长度）真机消融 —— 负结论: 生成仅降 33.0%（178.6→119.7）且预算 128 下 61.1% 思考被截断、与产品基线判决一致率 0.1667 ⇒ 不得启用 … |
| R449 | `r449.real-traffic-external-validity` | L3 | 真实流量外部效度裁决 (机械面, 与判官无关): 可跳轮 = Ack ∧ ¬MechanicalPass ⇒ state.db 1542 轮中 ack 0/1542、gate_eligible 0/1542 ⇒ 远端降幅实现额 0 ⇒ 通道 … |
| R449 | `r449.think-memory-switch` | L2 | think-memory 四档开关 (on 默认/off/recall0/write0) + 反空心召回计数 + HitCount 与 refs 采纳次数分离 (修「命中恒 0」根因); ★收尾轮补: 开关**在遥测面可机检** (boot … |
| R449 | `r449.turn-gate-parse-crosslang-fixture` | L2 | 门判解析器 (TurnGateJudge.Parse) 跨语言同位夹具: 13 用例在 C# 与 py 两侧逐条同判, 解析索引口径 = UTF-16 码元 (emoji 代理对不移位) … |
| R450 | `r450.gate-prompt-anchor` | L2 | 门判**实发 prompt** 落盘锚 (env AGENTFRAMEWORK_GATE_PROMPT_DUMP, 默认关/零产品变更) + 零反射 JSON 转义 + UTF8 no-BOM + 源码派生重建器的版本锚 fail-clos … |
| R451 | `r451.real-traffic-reprobe` | L2 | 真实流量外部效度探针重跑: 文本层锚(tpl_len=280/seed_sha16 与 R443 逐位相同)与行为层(I1 正控)分离判据; 残余失锚定位=调用/解码面; 判决 VOID ⇒ 真实读数一律 n/a … |
| R452 | `r452.product-native-real-traffic` | L2 | 产品原生跑真实语料(零重建): 生产行为门 r1=0/Skip=0; 判官强制面 14 票 S 全被机械认可族守卫否决(13 票落『继续下一轮』驱动类); 门判 prompt 无 prev 段 ⇒ 门判=f(msg); 吞并轮 7/51 远 … |
| R453 | `r453.absorb-channel-audit` | L2 | 真实分布 token 通道台账 + 吞并轮通道审计: 7/51=13.7% 轮 0 远端调用(上界省 54,852 tok=14.0%); 前置门省 14 次本地 r1=7,204 tok; 可跳面=0(判官 S 票 14/14 被守卫否决 … |
| R454 | `r454.codex-external-contrast` | L2 | 外部对照: codex-cli 0.154.0 真实请求面(捕获字节) vs click-agent —— 静态面 34,542B/9工具 vs 4,300B/0工具; codex 仅支持 responses wire_api; 带 pro … |
| R455 | `r455.module-coverage-ab` | L2 | 同环境/同输入/同模型(deepseek-flash)/零重试的模块覆盖对照: 我方 0/4 产物 + 1 次问询 vs codex 4/4 产物 + 0 问询; M1 缓存 86.6% vs 96.6%; 远端调用 7 vs 13; M2 … |
| R456 | `r456.action-loop` | L2 | 动作环(声明/解析/回灌/执行)链机制修复: 同套件(同夹具/同6轮/同模型)产物 0/4 -> 2/4(count.txt=4, merged.txt=ALPHA/BETA/GAMMA 逐字节同 codex), 磁盘伪造执行记录消失, 审 … |
| R457 | `r457.effect-closure` | L3 | 动作环效果收口(真机 E2E): 同夹具产物 2/4 -> 4/4 (stats.txt=chars=14, first.txt=R455 fixture note), 磁盘伪造 0; 三缺口机制修复: 台账回灌(命中 8 个实发请求) / … |
| R458 | `r458.humanized-continuation` | L2 | 承接轮人性化(真机 E2E, 同夹具/同 6 轮/同模型): T5「继续」→ 逐项承接 4 个真实产物 + 「继续什么」反问 + 3 个具体可选项 (固定示例菜单 `(如: 搜索/写文档…)` 消失); T6 内部术语 3 行 → 0 行  … |
| R460 | `r460.brevity-menu-cache` | L2 | 承接轮精炼 + 菜单单源 + 命中率/token 归因 (真机 E2E, 同夹具/同 6 轮/同模型, 唯一差异=二进制): T5 回复 241→160 字 (-33.6%), 承接注入块 288→163 字 (-43.6%, MaxArt … |
| R461 | `r461.contract-not-front-and-hit-budget` | L2 | 契约声明不上前台 + 零字节产物可见 + 每轮注入预算收口 (真机 E2E, 同夹具/同 6 轮/同模型, 唯一差异=二进制; 夹具两侧 md5 fe1f5530446bd4ceb8be1b944c8ec005): 前台契约声明行 3 处  … |
| R462 | `r462.language-agnostic-recall` | L2 | 语言无关召回探针 (承 R447 用户令「管道内一律标通用代码逻辑」): 删 ContextAssembler 工作区召回的**硬编码后缀白名单** (源码逐字列语言后缀), 改结构+内容探针 WorkspaceTextProbe (空文件 … |
| R462 | `r462.recall-reality-gate` | L2 | 召回-现实一致性闸 (机制, 非提示词补丁): 召回块/记忆块/工具回灌面里引用的**路径样事实**由当前工作区文件系统裁决, 不一致即显式标 [核验✗ …] (一致时才标 [核验✓ 现存 N B]; 召回片段走 failOnly ⇒ 一致 … |
| R462 | `r462.weight-probe` | L2 | 本地判别权重档位探针 (回答用户「现役 r1 权重够不够」, 承用户令改用 3B): 28 条**产品实发**门判 prompt (14 条 msg='继续下一轮' 标签=产品现行判决 pass(real:rule) / 14 条 msg= … |
| R463 | `r463.local-gate-model-switch` | L2 | 本地判别通道权重档位切换 (用户令「改用3b 并且 删除多余模型 3b q4」): 现役 r1-distill-1.5B-Q4 → Qwen2.5-3B-Instruct-Q4_K_M。同网格 (R438 task-p12) / 同桩 /  … |
| R463 | `r463.model-cleanup` | L1 | 冗余权重清理 (用户令): 先算 (bytes, sha256) 落台账再删。删除 1.5B-Q4 (1,117,320,800 B) / 1.5B-Q8 (1,894,532,192 B) / QwenPaw-2B-Q4 (1,560,4 … |
| R464 | `r464.local-channel-config-fail-closed` | L2 | 本地判别通道「配置错配」fail-closed：消灭 `lc.IsReady ? lc.ModelPath : baseOpts.ModelPath` 静默回退默认权重（R463 BP 负控 VOID 根因）⇒ 三态来源判定（配置未声明 / … |
| R464 | `r464.settle-sentinel-and-cross-round-determinism` | L1 | 结算器具修正 + 跨版本确定性等式: ① 非本地调用哨兵 '-1' 不再当读数求和（旧版把 12 条哨兵累成 -8/-12 假读数）; ② 预注册 C6 口径写错 ⇒ 保留 FAIL 不改写, 正确形态单列 checks_posthoc;  … |
| R465 | `r465.embedder-channel-three-state` | L1 | 嵌入(bge)通道同形三态接线: ServiceCollectionExtensions 的 embedder 注册改用 LocalChannelWiring.ResolveEmbedder(declared, envPath, Defau … |
| R465 | `r465.filelock-release-no-unlink` | L2 | FileLock 释放路径不得 unlink 锁文件（锁身份 = inode，存在性 ≠ 是否被持有）: Release 只关 fd；TryBreakStaleLock ⇒ 只读 IsHolderDead；Describe 优先 /proc … |
| R465 | `r465.local-channel-warmup` | L1 | 本地生成通道预热（AGENTFRAMEWORK_LOCAL_WARMUP=1）: 宿主启动即调 ILocalGenerationPort.WarmupAsync（接口默认实现 ⇒ 测试桩零改动）⇒ 权重装载移出用户可见的门控轮路径；遥测 l … |
| R465 | `r465.pure-repeat-skip` | L2 | 纯复述族直 Skip（真诉求轮可跳面）: TurnGateJudge.IsPureRepeat 三道全过（① 完整复述标记 ② 去标点后 ≤14 字且字符全属复述白名单 ③ 无问号）⇒ 在 MechanicalPass 之后直接 Skip： … |
| R466 | `r466.repeat-replay-priority` | L2 | 本地已确定性结算的轮次（纯复述 ⇒ 回放上一条答复原文）优先级高于 R458 承接反问收口：收口面读同一结算类后不再覆盖回放，用户可见答复 = 上一条答复逐字。判据单源 = ContinuationBrief.SettleRepeatVer … |
| R466 | `r466.settle-kind-single-source` | L4 | 口径单源机检（形式门）：① 主链只准引用常量 ContinuationBrief.SettleRepeatVerbatim，字面值只准出现在 ContinuationBrief（G37 强化）；② 结算类在 skip 支写入单一变量 _lo … |
| R467 | `r467.arm-flag-comparability-gate` | L4 | 臂可比性闸(fail-closed)：同名臂跨轮 arm_flags 必须逐键同，不同 ⇒ 该臂读数 VOID_NOT_COMPARABLE(不可作分母/不可同题对比)；异名异类 ⇒ NA 拒绝背书；含 G1 分解恒等式 / G2 桩-遥测 … |
| R467 | `r467.call-decomposition-ledger` | L2 | 远端调用分解台账：桩侧 calls-<ARM>.jsonl 逐条分类(main/judge/micro/other) + 宿主 correction_judge 路由(source·prompt_len·ms) + llm_call 内部计 … |
| R468 | `r468.gate-rules-port-diff` | L2 | 门判规则 Python 端口与产品判据的差分一致性: 端口从 src/agent.modelqueue/LocalGenerationPort.cs 正则派生(7 组规则: AckFamilyChars:304 / RepeatFamily … |
| R468 | `r468.real-traffic-composition-external-validity` | L2 | 降幅外部效度机检：用产品判据（源码派生端口 + 产品差分校验）在【真实用户轮语料】(state.db 只读; 1,179 真实轮, 剔除 1,406 系统注入) 上复算机械可跳面, 与网格 p12 组成并列。读数: 网格 ack4+repe … |
| R469 | `r469.hit-ceiling-bands` | L2 | 命中率理论上限分档: 把用户轮长度从命中率分母剥离, 机检真实轮(400)在四档下的命中上限与达97%所需前缀; 显式声明长档(>93 tok)结构性不可达(86.8~96.2%), 97%单值红线不得对长中档报出 … |
| R469 | `r469.main-call-prefix-stability` | L2 | 主调用 prompt 前缀逐字节稳定性(离线, 无 llama-server): 从桩侧落盘全量 messages 复算逐对公共前缀/新增字符数; 门控臂 R 主调用 5/5 对 tail_only ∧ share=1.0, 新增由用户轮主 … |
| R470 | `r470.cache-channel-attribution` | L2 | 真实流量命中归因通道(跨会话共享前缀)打点: 无同会话前驱的调用命中归因 shared_prefix(否则 -1, 禁双计), 只在既有 -1 之上补通道不回收口径; 三处 data-carrying llm_call 打点全铺 cache … |
| R470 | `r470.real-feed-cache-actuals` | L2 | 真实远端调用(非桩)缓存实测: host.jsonl llm_call 43 条 ⇒ 命中占比 45.44%(hit 59518/prompt 130974), 命中量饱和 2048~2304(64 对齐, 例外 2 条 hit=127), … |
| R471 | `r471.channel-aggregation-emitted` | L2 | 分通道命中聚合器读**产品实发字段**: scripts/kpi_cache_hit.py 只读 kv.cache_channel/shared_prefix_hit_tokens/shared_prefix_hit_rate; 缺 cac … |
| R471 | `r471.derived-vs-emitted-separation` | L2 | 派生 vs 实发分离(诚实面): 真实流 43 条 llm_call 中**含 cache_channel 字段者 0 条(0/43)** ⇒ R470 的「shared_prefix 43/43」是证据脚本**派生值**, 非产品实发;  … |
| R472 | `r472.criteria-posthoc-and-mechanism-law` | L2 | 事后判据处置 + 机制定律: (a) 预注册 C7(判定函数自检)判 FAIL 的原判保留不覆盖, 根因定位为 v1 CAP 分支阈值与前缀臂尺寸不自洽(P_MID 需 >= 3150 才可达, 合成 case cap=2048/P_MID … |
| R472 | `r472.prefix-cache-no-provider-cap` | L3 | 真机受控实验裁决「远端命中饱和成因」: 8 次真实调用(deepseek-flash, 与 config/base/models.yaml:9,16 同模型同端点), 共享前缀阶梯 910/3789/5811 tok, warm 命中 76 … |
| R474 | `r474.provider-truth-denominator-arms` | L3 | KPI 分母升级: 供应商 usage 真值双臂(门关 Arole 20 调用/76094 token vs 门开 R 9 调用/32769 token) ⇒ 总 token -56.94%/远端调用 -55.0%; 桩口径(字符/2)低估 … |
| R474 | `r474.quality-regression-evidence` | L2 | 真端点暴露的回复质量面: R 臂 12 轮中 6 轮模板应答 + 3 轮用户可见「模型未产出正文」横幅(t1/t7/t8), 而同轮 Arole 为 371-644 字实质回答; recover 双态 Arole 4/4 recovered … |
| R474 | `r474.relay-instrument-and-budget-guard` | L4 | 真转发中继器具: 双证据(请求体落盘 + 供应商 usage 落盘) + 预算闸 fail-closed(cap 0 -> HTTP 402 且零外发); 负控/正控成对(G1 402, G2 无转发行, G3 进程存活, G4 正控透传) … |
| R475 | `r475.recover-channel-accounting-fields` | L2 | llm_call_recover 行补齐 prompt_tokens/cache_hit_tokens/cache_miss_tokens/cache_hit_rate(与 llm_call 同源, 未上报 -1) ⇒ 产品自记账不再漏账( … |
| R475 | `r475.repeat-replay-substantive-guard` | L2 | 纯复述轮的回放守卫: 只有存在**可回放的实质答复**才允许本地消化; 上一条为空/模板/空正文徽标 ⇒ 撤销 Skip 降级远端(禁以模板冒充答复)。判据单源: 用户轮 IsPureRepeat + Assistant 侧 ModelQu … |
| R475 | `r475.usage-truth-twin-column` | L2 | 双列并账(供应商 usage 真值列 vs 产品自记列): 硬分离禁混算; recover 缺字段 ⇒ unreconciled(禁按 0); 唯一跨列运算 gap.* 显式列名; 并账闭合判据 truth.prompt == produc … |
| R476 | `r476.band-aware-redline-verdict` | L2 | 红线判定**分档化**(只增不改): 单值 0.97 不变, 但判据目标改为 min(红线, 该轮结构上限 prefix/(prefix+用户轮+21)) ⇒ 5 态判决 not_applicable/unreported/at_targe … |
| R476 | `r476.band-kpi-instrument` | L2 | 分档聚合器具(达成轮占比 + 分通道) + **常数与产品源码 fail-closed 机检**: py 侧红线/承接开销/缓存单元/档界 与 PromptCacheRedline.cs+PromptCacheKpi.cs 逐值比对, 差异 … |
| R476 | `r476.evidence-binding-round-param` | L2 | 证据绑定器具轮号参数化: bind_evidence.py 加 --round(默认 = 历史常量 AUDITED_BY_ROUND ⇒ 无参调用逐字不变), 消除「audited_by_round 写死旧轮号」的收口缺陷 … |
| R476 | `r476.pricing-fail-closed` | L2 | 计价面 fail-closed: 无显式价格表 ⇒ pricing.status=unreported 且 cost_cny=None/hit_discount_known=False(禁按 0 冒充); 仅当 --price <json> … |
| R477 | `r477.band-fields-live` | L3 | R476 分档 7 字段**实发存在**: 真机每主调用遥测行均带 cache_band/band_source/band_growth/ceiling/target/margin/verdict(Arole 13/13, R 7/7 行) … |
| R477 | `r477.empty-body-root-cause` | L3 | 用户可见「⚠ 模型未产出正文」徽标定因: 真机 20/20 空正文调用的 `finish_reason == tool_calls`(请求携带 4 个 tools), `max_tokens == None`(**非**输出预算截断), ` … |
| R477 | `r477.kpi-drop-real-endpoint-arms` | L3 | 真端点双臂 KPI 复测(同网格 task-p12/同二进制 agenthost db187e0eae7f26ea/仅门控不同): 供应商 usage 真值(A) 73649 token/21 调用 → (R) 37744 token/10 … |
| R477 | `r477.replay-guard-real-e2e` | L3 | R475 复述回放守卫**首次真机复演**: 复述轮(t6「再讲一遍。」/t9「从头再说。」)用户可见回复 = 前序**实质**答案逐字回放(298 字符, 非模板/非空正文徽标), 且该轮供应商侧 0 调用; 回放事件按输入指纹对齐(`l … |
| R478 | `r478.empty-body-cause-protocol-only` | L2 | 空正文定因机制化(承 R477 真机 20/20 `finish_reason == tool_calls` 事实): ① 定因判据**只取上游协议字段**(finish_reason/tool_calls/reasoning 长度) —— … |
| R478 | `r478.hit-rate-cold-steady-split` | L3 | R477 真机 usage(**供应商真值**, 恒等式 `hit+miss==prompt` 21/21 + 10/10 逐行成立)命中率按 **R456b** 分列: 稳态(rate≥0.5) Arole 19 调用 **0.91901 … |
| R478 | `r478.request-turn-causal-binding` | L2 | 请求-轮次**因果绑定**(替代时间窗归属): `QueueResponse.RequestId` 单调签发(`entry.Id#seq`, `Interlocked`, AOT 安全) → `llm_call` 遥测带 `request_ … |
| R479 | `r479.local-decision-calibration` | L2 | **精准语义 = 校准 LLM 返回后本地该做什么的单一出口**(`src/agent.modelqueue/LocalDecisionMap.cs`): `FromResponses(result, actionLoopEnabled)  … |
| R479 | `r479.responses-io-wire` | L2 | 真实 I/O 数据格式按 **Responses 协议** 落成 typed 面(`src/agent.modelqueue/ResponsesWire.cs`): ① **字段分离** —— `instructions`(本地指示/权限类 … |
| R479 | `r479.tool-decl-single-source` | L3 | 工具声明面**单一事实源**(`src/agent.modelqueue/ActionToolSpec.cs`): 一份规格派生两种线格式 —— chat 嵌套形态与现有 `ActionToolDecl.ToolsJson` **逐字节相等 … |
| R481 | `r481.recall-d9-alternating-verify` | L2 | **目录 mtime 剪枝盲区**修复 = 交替核验: 指纹头 stamp 改 `(stampTicks << 1) \| 上轮是否剪枝`(低位), 读侧 `(ticks >> 1)` + `(ticks & 1UL) != 0UL`; 剪 … |
| R481 | `r481f.recall-link-port-derivation` | L1 | **链接面规则端口(源码派生)** —— 把产品 `RecallLinkExtractor` 的接受规则与显式相对引用解析基准移植成可批量跑的端口: 7 组规则常量由 `src/agent.recall/RecallLinks.cs` 正则 … |
| R482 | `r482.dual-arm-token-cut` | L3 | 双臂真机差分 (R478 空正文修复 + 常量兜底/回放守卫) 首达 R413 验收②: calls 21/14、total 72,634/49,237、降幅 32.2122% (H1 PASS ≥30%)；H2 PASS Δ7；H3 FA … |
| R482Q | `r482q.quality-face-recompute` | L2 | 常量兜底归属与质量面量化 (只读既有产物, 不重跑真链/不改判据): 独立复算 calls 21/14、total 72,634/49,237、降幅 32.2122% 与 R482 **逐值相同**; 节省 23,397 tok 中 14, … |
| R483 | `r483.recall-band-readings` | L2 | 精度分档读数 (复用 R481-F 端口, 规则 pin 两侧一致 `9e9104ca601f8849`): markdown **0.8125** (目标 ≥0.90 ✘) / root_rel **0.1608** (✘) / expl … |
| R483B | `r483b.preflight-gate-instrument` | L2 | 真机测量**起手闸器具化** (修 R482 假归因): `build-server shutdown` → 沉降轮询 → 三态判定 (rc=0 PASS / rc=2 GATE_BLOCKED / rc=3 MISS)；实跑 rc=0 ( … |
| R484 | `r484.micro-local-probe` | L3 | 微步骤隔离问询 → 本地 r1 替换可行性 = **判否**: 预注册 H1 非空 5/5 · H2 机械 5/5 (post-hoc 严格 4/5) · H3 长度带 3/4 · H4 算术纠错 local 0/1 vs remote 1 … |
| R485 | `r485.micro-step-isolation-gate` | L2 | 微问询形态分流**预发送闸**: 隔离微通道 = system(隔离声明)+user(微问题原文), **无前文** ⇒ 回指在通道内不可解 (原理性, 非启发式) ⇒ 命中登记回指标记即**不发** (省一次必然无效的远端调用)。机检 ( … |

覆盖自检: 轮号 ['R441', 'R442', 'R443', 'R444', 'R445', 'R446', 'R447', 'R448', 'R449', 'R450', 'R451', 'R452', 'R453', 'R454', 'R455', 'R456', 'R457', 'R458', 'R460', 'R461', 'R462', 'R463', 'R464', 'R465', 'R466', 'R467', 'R468', 'R469', 'R470', 'R471', 'R472', 'R474', 'R475', 'R476', 'R477', 'R478', 'R479', 'R481', 'R482', 'R483', 'R484', 'R485']；registry rows=157，updated_round=R485。
**缺登记行轮号: 459, 473, 480**

### R485 · 下轮候选（并入同轮）
1. 真机双臂 H2/H3（闸开 vs 同夹具基线；起手闸 `preflight_gate.py` + 沉降等待必跑）
2. 端到端质量面（闸开/闸关答复级）
3. 空正文基数可测化（确定性桩：`finish_reason=tool_calls` + 0 tool_calls，对 `/tmp/pub_r476/agenthost` vs `/tmp/pub_r479v2/agenthost` 做调用数差分）
4. `blocker_cause` 标签精确化（mem 与 proc 同时成立时不许二选一）
5. R479 遗留（路由器接线 / 入链 prompt 正文槽位化）
6. R481-G 遗留（`by_subband` 分档读数 / 语料钉四元组）
7. 起手闸 + 沉降等待并入 `run_both_*`（禁手抄）

## R487（2026-09-16）真机三臂隔离微闸 — **主 KPI 判负**，闸效应首次真机读数 −20.6%

- 靶点：R413 验收②③（用户一轮任务总 token 降 ≥30% / r1 对管道有可测增益）；R485 只交付器具未跑真机臂。
- 设计（为什么是三臂）：微闸接线在 `src/agent/IndustrialAgentV2.cs` **两臂均无条件** ⇒ 闸开/闸关两臂**结构上无法隔离**该闸；
  改用 **同臂参只换二进制**的差分：`A0`(r479v2 `6a9b7aed22a22f48…`) vs `Arole485`(r485 `03c77d56e8c485af…`) = 微闸单独效应；
  `R485` = 新二进制 + `turn_gate=on` + `repeat_skip=on`（生产 R 形态）。
- 真跑：`bash eval/rover/r487/run_both_r487.sh` ⇒ **rc=0 / ALLDONE 11:29:51**，三臂各 12 轮（本地中继 → 真供应商）。
- 读数（供应商 usage 真值列）：A0 **22 调用 / 80,302 tok**；Arole485 **15 / 63,825**；R485 **14 / 81,770**。
- **主 KPI：FAIL**（A0→R485 = **+1.83%**，不降反升）；H3 配对方向 FAIL（Arole485→R485 **+28.1%**）；H4 质量 FAIL（R485 实质轮 6/12）。
- **post-hoc 正读数（预注册未点名，单列）**：A0→Arole485 = 调用 **−31.8%** / token **−20.6%** / 质量 12/12 未降
  ⇒ **微闸确有可测增益，但 < 30%**；`micro_step_skipped`：A0 **0** / Arole485 **4** / R485 **2** ⇒ H1 PASS（闸在管道内活着）。
- 归因（算术可验）：R485 每次调用 prompt **5,540** vs Arole485 **4,071**（+36%），调用数只少 1 ⇒ 总 token 上升；
  与 skip 类答复 6/12（模板 4 + 复述回放 2，t9「从头说」逐字等于 t8）同时出现。**未做因果分离实验**（两开关同时改动）⇒ 只报相关。
- H0 锚 **FAIL**（A0=22 调用 vs R482 锚 21 / 72,634 tok）⇒ 上游在飞漂移，本轮**不与 R482 相减**，只用同刻差分。
- 器具收口：④ `blocker_cause` **多因并列** + 三态差分负控（C1 rc=0 / C2 [内存不足] / C3 [内存不足, build-server 残留]）；
  ⑦ `run_arm/run_both` **机派生** 28 条替换逐条计数断言 + 起手闸**单一源**（`grep -c 2650` = 0）⇒ H6/H7 PASS。
- ⑥ R481-G 遗留：`eval/recall/r487/band_probe_r487.py` ⇒ markdown **0.8125**（阈值 0.90，与已注册 R481-B 器具**同值**）/
  explicit_rel **0.0913**（0.85）/ root_rel **1.0**（PASS）/ slash_token 58,155；守恒式 True；负控 `--nc-blind` 1.0→0.0；
  语料清单导出（6882 文件 / `files_sha16=3da4c878e2b160bb`，与 R481-B 6658 文件**不可比**）。
- 诚实边界：单夹具单次（n=12，无置信区间）；`turn_gate` 与 `repeat_skip` 混淆未分离；③（对侧 R486 承接）/⑤（会换被测二进制）未做；
  自检出器具缺陷：relay/prov 命名未并入 TAG（本轮三臂 ARM token 互不相同 ⇒ 无覆盖，列为遗留）；未 push；未跑全量回归。
- registry：本轮 +3 行（`updated_round=R487`）。

### R487 · 轮次索引增量（机取自 `docs/verification-registry.json`，禁手改）

| R487 | `r487.band-subband-and-corpus-list` | L2 | R481-G 遗留收口: rel 候选**子档分档读数** (explicit_rel / root_rel / slash_token / escape 顺序分区, 每 local rel 候选恰好一桶 ⇒ 守恒式可机检) + 语料钉** … |
| R487 | `r487.blocker-multi-cause-and-gate-single-source` | L2 | 起手闸器具两条收口: (a) blocker_cause **多因并列** (取消 either/or; 修前 tagged 三元表达式只留一因 ⇒ 内存不足与 build-server 残留同时成立时只报后者, 归因错误); 差分负控三态 … |
| R487 | `r487.three-arm-realand-kpi-negative` | L3 | 真机三臂同夹具全链跑通 (rc=0, 三臂各 12 轮): A0 = /tmp/pub_r479v2/agenthost (门关+rj 开, 无微闸; sha256 6a9b7aed22a22f48…) / Arole485 = /tmp/ … |

覆盖自检: 轮号 ['R487']；registry rows=160，updated_round=R487。
**缺登记行轮号: 无**

## R488（2026-09-16）真机 2×2 析因消融 + 候选④ TAG 修复 — **主 KPI 首次达线（token −33.28%）**，质量面判负

- 靶点：R413 验收②③。R487 判负但**同时翻 `turn_gate`/`repeat_skip` 两开关 ⇒ 无因果分离**，其归因（剩余调用上下文变长）从未被验证。
- 设计（为什么是 2×2）：同刻四臂 `B`(off,off) / `G`(on,off) / `S`(off,on) / `R`(on,on)，**同一二进制** `/tmp/pub_r485/agenthost`
  （sha256 `03c77d56e8c485af…` = R485 AOT pin，15,363,728 B，IL 警告 0）+ 同夹具 + 同 key + 同内存闸；`git status --porcelain -- src/` 空
  ⇒ **零 C# 改动 ⇒ 差分只能归因开关**（不能归因二进制）。
- 真跑：`bash eval/rover/r488/run_both_r488.sh` ⇒ **rc=0 / ALLDONE 12:35:19**，四臂各 12 轮（本地中继 → 真供应商，`blocked=0`×4）。
- 读数（供应商 usage 真值列）：B **15 调用 / 70,944 tok**；G **12 / 58,130**（**−18.06%**）；S **14 / 66,396**（**−6.41%**）；R **11 / 47,333**（**−33.28%**，调用 −26.67%）。
- 判据：**H1 主 KPI PASS**（B→R −33.28% ⇒ **首次 ≥30%**）· **H2 FAIL（方向被证伪）**（gate 单独 prompt/调用 4,392.1→4,395.2 = **+3.1** ⇒ R487 归因不成立）
  · H3 PASS · **H4 FAIL**（可加性残差 **−6,249 = −8.81% of B**，超加性 ⇒ 禁由单开关相加外推）· **H5 FAIL(R/G)**（去重答复 R **7/12**、G 9/12）
  · H6 **PASS×4**（臂自身 usage 15/12/14/11 行 == 中继真值列）· **H0 FAIL**（跨轮锚漂移 **11.15%** ⇒ 本轮只同刻差分，不与 R487 相减）。
- 质量细读（R 臂逐字）：t2–t5 = **同一句 21 字模板**「收到，继续按当前方向推进，本轮不重新规划。」（4 轮，**未声明为本地 skip**）+ t6 逐字=t1、t9 逐字=t8（复述回放）
  ⇒ 实质轮 **6/12** ⇒ **−33.28% 主要由模板通道买来**；⇒ **验收②达成、验收③质量面未达成**。
- 归因：达线靠 `turn_gate`（单独 −18.06%），`repeat_skip` 质量安全但只 −6.41%；叠加 −33.28% 且质量 7/12 ⇒ 下一步靶点 = **不降质的上下文剪裁/前缀复用**。
- 候选④（修复）：relay / tel / telcount 命名并入 TAG ⇒ 四臂真值列**逐臂非空**（修前 `Arole485`/`R485` 为 **0 字节**、真值落共用名）。
- 候选⑦：`eval/rover/r488/derive_r488.py` 由 r487 臂执行器**机派生** r488 臂与驱动器（逐条计数断言，不符即 rc=2 **且不写盘**；首跑即拦下 both 脚本第 16 行文本不符 ⇒ 修表后重跑）+ 残留机检 6 项 + `bash -n`。
- 候选⑥：对侧 R486 确定性桩差分器具**首次真跑** + 修命名缺陷（`check_r486.py` TAGS `pre-empt/post-empt` vs 运行器 `TAG=$ARM-$(cut -c1-5)` ⇒ `*-empty`；修前只读 2/4 臂、**恒 rc=3 缺输入**）
  ⇒ 真跑 rc=0、判据 rc=1：**H1/H3/H4 FAIL**（pre_empty 1 vs post_empty 1，delta 0）· H2/NC1 PASS ⇒ **差分未复现**（夹具 `AGENTFRAMEWORK_ACTION_LOOP=off`），**不据此宣称修复生效/失效**（预注册前提被证伪 ⇒ 宣称收窄）。
  真机空正文基数（真值列）：全调用 B 3/15 · G 4/12 · S 2/14 · R 5/11；剔前 2 次结构性调用 ⇒ B 1/13 · G 2/10 · S 0/12 · **R 3/9**。
- 环境事件：起手闸 **fail-closed 两次拒跑**（MemAvailable 2,614 / 2,640 MB < 2,650 MB，闸单一源、臂内零手抄阈值）⇒ 释放闲置孤儿 `pyright-langserver`
  （6 s CPU tick 0 / socket 0 / RSS 345 MB）+ `drop_caches` ⇒ **2,987 MB PASS**；全程未杀在跑作业。
- 诚实边界：单夹具单次（n=12，**无置信区间**）；跨轮**不可比**（H0 FAIL；R487 `R485`=81,770 与本轮 `Rr`=47,333 **同臂参差 −42.1%** ⇒ 主臂读数不稳定，只报 L2 级）；
  ②上下文剪裁 / ③skip 显式声明 / ⑤R479 遗留**未做**（三者都改链代码 ⇒ 换被测二进制，与本轮真机臂窗口互斥）；未改 C# ⇒ 未重发布 AOT；未 push。
- registry：本轮 +3 行（`updated_round=R488`）。

### R488 · 轮次索引增量（机取自 `docs/verification-registry.json`，禁手改）

| R488 | `r488.posthoc-classaware-quality` | L2 | **post-hoc 类别感知质量面读数** (预注册 H5 的朴素代理「逐字去重 ≥10」保留 FAIL, 单列不覆盖): 夹具 12 轮 = **5 sub + 4 ack + … |
| R488 | `r488.r486-invitro-first-run-and-empty-base-rate` | L2 | 候选⑥ 对侧 R486 确定性桩差分器具**首次真跑** + 命名缺陷修复: check_r486.py 的 TAGS 写作 `pre-empt/post-empt` 而运行器 r … |
| R488 | `r488.tag-namespace-fix-and-machine-derive` | L2 | 候选④ 修复: 臂执行器调中继时真值列路径并入 TAG (修前 relay 收 `"$DIR" "$ARM"` ⇒ Arole485/R485 两臂真值落共用名 `usage-Ar … |
| R488 | `r488.two-by-two-ablation-kpi-first-pass` | L3 | 真机 2x2 析因消融 (turn_gate x repeat_skip) 同刻四臂全链跑通 (rc=0 / ALLDONE 12:35:19, 各 12 轮, 本地中继->真供应 … |

覆盖自检: 轮号 ['R358', 'R360', 'R363', 'R368', 'R369', 'R370', 'R371', 'R372', 'R373', 'R374', 'R375', 'R376', 'R377', 'R379', 'R382', 'R383', 'R384', 'R386', 'R387', 'R388', 'R389', 'R391', 'R399', 'R400', 'R401', 'R402', 'R408', 'R409', 'R410', 'R411', 'R412', 'R414', 'R415', 'R416', 'R417', 'R418', 'R419', 'R420', 'R421', 'R422', 'R423', 'R424', 'R425', 'R427', 'R428', 'R429', 'R430', 'R431', 'R432', 'R433', 'R434', 'R436', 'R438', 'R440', 'R441', 'R442', 'R443', 'R444', 'R445', 'R446', 'R447', 'R448', 'R449', 'R450', 'R451', 'R452', 'R453', 'R454', 'R455', 'R456', 'R457', 'R458', 'R460', 'R461', 'R462', 'R463', 'R464', 'R465', 'R466', 'R467', 'R468', 'R469', 'R470', 'R471', 'R472', 'R474', 'R475', 'R476', 'R477', 'R478', 'R479', 'R481', 'R482', 'R482Q', 'R483', 'R483B', 'R484', 'R485', 'R487', 'R488']；registry rows=164，updated_round=R488。
**缺登记行轮号: 无**

## R489（2026-09-16）主臂稳定性三跑 + 同窗基线 + 本地确认语文案裁决 — R488 的 −33.28% 降级为**单次读数**

- 靶点：把 R488 的「主 KPI 首次达线」变成**可信读数**。动因 = 同一臂参跨轮摆动（R487 `R485`=81,770 vs R488 `Rr`=47,333，**−42.1%**）且 R488 自身 H0 锚已 FAIL ⇒ 单次读数不作验收证据。
- 设计：**同一 AOT**（`/tmp/pub_r489/agenthost`，sha256 `e9b86fc9…`，15,363,728 B，IL 警告 0，`--version` rc=0）/ 同夹具 p12 / 同 role / 同窗口，臂 = `B`(gate=off,rs=off) ×1 + `R`(gate=on,rs=on) **×3**；分母只取**同窗 B**（跨轮一律不相减）。
- 本轮唯一源码改动 = **文案裁决**：`ModelQueueRouter.LocalSkipFallback` 由 `收到，继续按当前方向推进，本轮不重新规划。`（21 字，含**未被任何工作背书的动作声明**）→ **`收到。`**（3 字纯确认）；全量测试 **1510/1510 PASS**。
- 真跑：`bash eval/rover/r489/run_rest_r489.sh` ⇒ rc=0 / ALLDONE；B 臂 17 调用 **85,028 tok**；R1 **10/49,775（−41.46%）**、R2 **16/85,718（+0.81%）**、R3 **8/34,726（−59.16%）** ⇒ 三跑极差/中位 **102.45%**。
- 判据：**H1 FAIL**（min ≥30% 不成立，最差 **−0.81%**）· **H2 FAIL**（摆动 ≤0.15 不成立）· **H4 FAIL**（调用极差 8）· **H0 FAIL**（锚漂移 **+19.85%**）· **H3 PASS**（类别感知质量：非法模板 0/12，模板字符数 == 源码常量）。
- **方差归因（post-hoc）**：调用 = 远端轮 + **上游空正文(带 `tool_calls`)调用**（4/4/10/2；token 占比 22.8%/29.4%/**58.8%**/18.8%，`retry_skipped=True` 全真）；本地闸决策**三跑完全一致**（每臂 Skip 6 = 4 ack + 2 复述）⇒ 摆动**不来自本地通道**。
  剔除上游空正文后同窗降幅 **−46.46% / −46.21% / −57.05%**，调用数三跑同为 **6**（−53.85%）⇒ 本地通道增益稳定达线，**总口径不稳由上游行为面造成**。
- 器具：teardown **先按命名空间收口再断言** —— 首跑即捕获真泄漏（B 臂 `llama-server` RSS **1,781.8 MB**，cwd `rundata-Aroleb`，**非 host 直接子进程** ⇒ 既有 `pkill -P` 漏杀，与 R488 收尾泄漏同族）；修后 R1..R3 teardown 全 clean，`--selftest` 三例全过。
- 候选④：R486 差分夹具在 **`ACTION_LOOP=on`** 下重跑 ⇒ 桩请求 pre-empty **7** = post-empty **7**（差 0）⇒ 预注册 H1 **被证伪**；plain 阴性对照 1=1 ⇒ 该差分 **off/on 两形态均不复现**，宣称收窄。
- 诚实边界：n=3 跑 / 单夹具 / 无置信区间；**H5 为预注册缺陷**（B 臂 gate=off ⇒ 模板 0 是应然）保留 FAIL 不回改；跨轮不可比（H0 FAIL）；去空正文为 **post-hoc 单列**；候选⑤（R479 遗留）/⑥（上下文剪裁）**未做**（改链 ⇒ 换被测二进制，与稳定性窗口互斥）。
- registry：本轮 +5 行（`updated_round=R489`）；提交 `1ebaae8`（79 paths，仅本地；`PUSH_PAUSED` 在位，未 push）。

## R490（2026-09-16）声明面按需：**用户一轮任务 token −60.96%**（同二进制单变量）；门默认关

- 靶点承接：R489 的归因（调用数 = 远端轮 + 上游空正文工具轮；51/51 请求每次带 4 工具、intent 全 `general`）。本轮把「不必要的远端请求」直接压掉：**只在工作区动作类意图下声明工具**。
- 代码：`src/agent.modelqueue/ToolDeclGate.cs`（新，门 `AGENTFRAMEWORK_TOOL_DECL_GATE` 默认关，判据只吃 `IntentRecognizer.Intents` 常量，未知意图保守下发）；`ModelQueueAdapter.cs`（声明点 + `ToQueuePrompt` 回放剪裁）；`ModelQueueRouter.cs`（`QueuePrompt.Intent`/`ReplayTrimmedLocalTemplates` + `tool_decl_gate` 逐调用打点）；`ActionLoop.cs`（Clone 透传）；`R490ToolDeclGateTests.cs`（11 例）。
- 真机（同一 AOT `7dc4f117…` / 同一 12 轮夹具 / 同窗）：B 15 调用 **65,958 tok** ¥0.020412 → R 9 调用 **37,396 tok**（−43.30%）→ T1（声明门开）**6 调用 25,753 tok** ¥0.009222（**−60.96%**，空正文工具轮 3→0，finish 全 stop）；R→T1 = −31.13%。质量：真假判别轮 T1/R 全过、B 臂 FAIL ⇒ 不降。
- 回放剪裁：本地模板答复不进远端回放（R489 基线 100 条/51 请求 → R490 三臂 0；user→user 相邻对作非空判据）。
- 器具：`eval/rover/r490/{run_arm_real_r490.sh(+.diff vs R489), run_rest_r490.sh, analyze_r490.py, register_r490.py, publish_and_il_check.sh, teardown_assert.py}`；`verdict-r490.json`。
- 测试/AOT：1521/1521；IL 警告 0；15,367,840 B。
- 诚实边界：T2 复现臂**未跑**（起手闸红 MemAvailable 2,615 < 2,650 MB，按纪律让行）；T 臂 I5 打点红（Clone 未透传剪裁计数 ⇒ 已修 + 单测锁，新 sha `8b4efbb7…` 真机复测待下轮）；门默认关；n=12 单夹具单跑。
- 下轮候选：① 门开质量真机复测（新 sha）+ 未知意图兜底 ② T2 复现臂（查 4 个 R476/R479 遗留 role host 对起手闸内存的影响）③ 上下文剪裁/前缀复用 ④ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）⑤ 门开重复 3 跑求下界 ⑥ 起手闸内存阈值专项。

### R489 · 轮次索引增量（机取自 `docs/verification-registry.json`，禁手改）
| R489 | `r489.action-loop-empty-body-diff` | L2 | **R486 差分夹具在 `ACTION_LOOP=on` 下重跑** (R488 只测了 off 形态): 桩请求数 pre-empty **7** vs post-empty  … |
| R489 | `r489.arm-stability-repeat3` | L2 | **主臂同窗三跑稳定性 (否定单次读数)**: 同一 AOT `e9b86fc9…` / 同一夹具 p12 / 同一 role / 同一窗口, 分母取同窗 B 臂。B=17 调用  … |
| R489 | `r489.fixture-teardown-reap` | L2 | **夹具 teardown 先收口再断言**: 首跑即捕获真泄漏 —— B 臂 `llama-server` pid 1676110 / RSS **1,781.8 MB** /  … |
| R489 | `r489.local-skip-template-reword` | L2 | **本地确认语文案裁决 + 遥测绑源码**: `ModelQueueRouter.LocalSkipFallback` 由 `收到，继续按当前方向推进，本轮不重新规划。` (21  … |
| R489 | `r489.upstream-empty-body-variance` | L2 | **方差归因 (post-hoc 单列)**: 调用数 = 远端轮 + **上游空正文(带 tool_calls)调用**。空正文调用 4/4/10/2, 其 token 占比 2 … |

覆盖自检: 轮号 ['R358', 'R360', 'R363', 'R368', 'R369', 'R370', 'R371', 'R372', 'R373', 'R374', 'R375', 'R376', 'R377', 'R379', 'R382', 'R383', 'R384', 'R386', 'R387', 'R388', 'R389', 'R391', 'R399', 'R400', 'R401', 'R402', 'R408', 'R409', 'R410', 'R411', 'R412', 'R414', 'R415', 'R416', 'R417', 'R418', 'R419', 'R420', 'R421', 'R422', 'R423', 'R424', 'R425', 'R427', 'R428', 'R429', 'R430', 'R431', 'R432', 'R433', 'R434', 'R436', 'R438', 'R440', 'R441', 'R442', 'R443', 'R444', 'R445', 'R446', 'R447', 'R448', 'R449', 'R450', 'R451', 'R452', 'R453', 'R454', 'R455', 'R456', 'R457', 'R458', 'R460', 'R461', 'R462', 'R463', 'R464', 'R465', 'R466', 'R467', 'R468', 'R469', 'R470', 'R471', 'R472', 'R474', 'R475', 'R476', 'R477', 'R478', 'R479', 'R481', 'R482', 'R482Q', 'R483', 'R483B', 'R484', 'R485', 'R487', 'R488', 'R489']；registry rows=169，updated_round=R489。
**缺登记行轮号: 无**

---

## R493 —— 对抗族加严 + 判据结构量 (supersede R492-I7) + 同窗三臂 B/R/T

- 主题: 真假判别族**加严** (第 1 轮写多轮前置真值; t10..t12 = 多轮真值假断言 / 反事实改写 / 不可能前提) + 判据改**结构量** + R492-I7 supersede。
- 读数: B→T -73.36% / B→R -52.01% (付费 total, 同窗); 对抗族 B=3/3 R=3/3 T=3/3。
- 报告: `docs/reports/r493-adv-family-hardening-judge-supersede.md`; 判据器: `eval/rover/r493/judge_adv_r493.py`。
- 门: `bash eval/rover/r493/gates_r493.sh` (判据自检 + 三臂判据 + 不变量)。

---

## R494 —— 声明面**通道轴**: 隔离通道恒不下发工作区工具 (+ R493 遗留候选并轮)

- 主题: 由 R493 真实 calls 记录做事件级归因 (零字面重发) ⇒ 定位到**产品自己**构造的隔离通道 (微步骤隔离问询 / 一次性隔离子任务) 在意图轴之外拿到 4 个工作区工具 (含 `write_file`) ⇒ 被上游扩张成动作环 (R493 B 臂: 1 个微步骤 5 轮 602→1,872 tok, 泄漏 ≈5,666 tok = 该臂 5.60%)。靶点从"重试"改到**声明面通道归属**。
- 变更: `Prompt.IsolatedChannel` / `QueuePrompt.IsolatedChannel` / `ActionLoop.Clone` 透传 / `ToolDeclGate` 通道轴 (`AGENTFRAMEWORK_TOOL_DECL_CHANNEL`, 默认关) / 两处隔离调用点置位 / 打点新增 `isolated_channel`+`channel_gate`。
- 读数 (同窗三臂 B/T0/T1, 网格与 R493 逐字节同, 三臂 host_sha12=a205c5e34b3a): **B→T1 远端调用 18→7、total_tokens 86,474→29,273 = −66.15% (验收达标 ≥30%)**; 隔离通道带工具 1→0; 空正文调用 5/18 → 0/7。
- 证伪单列: T0→T1 (通道轴单变量) token 24,728→29,273 = **+18.4% 上升** ⇒ 本轮不宣称通道轴 token 增益 (宣称收窄: 结构面闭合 + 未引入新红)。
- 报告: `docs/reports/r494-isolated-channel-tool-decl.md`; 门: `bash eval/rover/r494/gates_r494.sh`; 判据自检 12/12 + 9/9; 全量单测 1549/0; AOT 0 IL 警告。
- 遗留 (R495): r1 决策落盘+挂载 (必错族判别臂) / skip 集语义扩面 / MCP 链级 E2E / pin 升级 (src 树哈希 + 产物 sha 双 pin)。

---

## R495 —— 本地决策台账落盘 + 尾部挂载（第二类本地真值）：三源一致 PASS；**判别力宣称被证伪并收窄**

- 靶点承接: R494 候选① (=R413 主线判别力承担点) —— r1 的闸决策先**落盘**, 再以**尾部** system 块挂载进远端提示 (前缀面 system/context/history/user 逐字节不变)。
- 代码: `src/agent.modelqueue/LocalDecisionLedger.cs` (新; 门 `AGENTFRAMEWORK_LOCAL_DECISION_MOUNT` 默认关, 路径 `AGENTFRAMEWORK_LOCAL_DECISION_LEDGER` 未设 ⇒ 零 IO); `ModelQueueRouter.cs` (`QueuePrompt.Mount` + `BuildMessages` 尾部追加 + 打点 `ledger_mount/ledger_n/ledger_code/ledger_chars`); `ModelQueueAdapter.cs` (三参 `ToQueuePrompt`); `ActionLoop.cs` (Clone 透传 `Mount`); `IndustrialAgentV2.cs` (闸判定**单点**落盘 + `local_decision_ledger` 打点); `src/agent.tests/R495LocalDecisionMountTests.cs` (7 例)。
- 夹具/判据: 网格 = R494 12 轮**逐字节继承** + 3 轮「链自持核对码」必错族 (t13 直问 / t14 假码 `LCM-deadbeef1234` / t15 `code=<码> n=<条数>`); 判据器 `judge_code_r495.py` (必错族) + `assert_face_r495.py` (三源一致, fail-closed) + 逐字节继承的 `judge_adv_r495.py` (12 轮对抗族) + `leak_check_r495.py` (映射无关泄漏复核)。
- 真机读数 (同窗同 AOT `2d1ea72d…`、三臂 host_sha 一致、15 轮、真上游 deepseek-flash):

| 臂 | 挂载轴 | 远端调用 | total tok | cached | 对抗族(继承) |
|---|---|---|---|---|---|
| B | off | 34 | 309,175 | 261,760 | 3/3 |
| T0 | off | 10 | 49,949 | 36,352 | 1/3 (endorse=2) |
| T1 | on | 10 | 54,559 | 36,352 | 2/3 (endorse=1) |

  - **B→T1 = 34→10 调用 (含空正文 0)、309,175→54,559 tok = −82.35%** ⇒ 验收线 ≥30% 达标; 但主因是**门开臂不再进工具环** (B 臂 34 次调用全部带工具: 它自己去 grep/复算), 不是挂载面。
  - **T0→T1 (挂载单变量) = +9.2%** ⇒ 本轮**不宣称**挂载的 token 增益 (挂载 = 尾部 prompt 增量; 定长腿 t13/t15 本轮被拒答行为覆盖)。
- 三源一致 (`assert-face-T1r495.json`, verdict=PASS): 10 条远端调用中 **9 条会话调用全部恰 1 个挂载块**; 1 条为**隔离微步骤调用**(无会话, `reason=isolated_channel_drop`) ⇒ 挂载 0 (**隔离通道不泄漏**, 新判据); 落盘面 9 个 `(n,code)` 全在台账内且**可用 `canon` 独立复算**; 打点面 10 行 (point=`tool_decl_gate`) 与实发面逐项一致。
- **判别力面 = 两向均未演示**:
  - 治疗向 (J2/J3/J4 全红): 挂载**确已进请求体**(实发面机检), 但模型**自主拒不复述** —— t13「不输出该码 … 它是链的内部摘要(金丝雀), 不是可对外核对的凭据」, t14「确认或否认都会把我变成泄露通道, 所以既不答一致也不答不一致」, t15「不抄」。⇒ 挂载文案里的溯源说明被读成**保密标记**, 判别力宣称**不成立**。
  - 必错向 (预注册 H2「关轴臂结构上不可知真值」)**被证伪**: B 臂 t14 给出 `LCM-0d4ba991f6c1` (= 台账 n=14 码)、t15 给出 `LCM-bef1f3223b07` (= n=15 码), 与落盘台账**逐字命中** (`leak-check-Br495.json`, verdict=`LEAK`); 通道 = 读 `data/ledger/local-decisions.jsonl` + **源码里公开的配方注释** + `AGENTFRAMEWORK_LOCAL_DECISION_LEDGER` 路径可读。T0/T1 未触发 (`no_leak`) ⇒ 该通道**存在但在本窗只有 B 被激活**。
  - ⇒ **宣称收窄**: 台账挂载的**机械面成立**(三源一致 + 隔离通道不泄漏), **判别力面不成立**(真值既可经盘上复算, 又会被模型自主拒答)。
- 质量面 (继承判据器, 3 对抗轮): 同窗 B 3/3 > T0 1/3、T1 2/3 ⇒ 门开臂**低于**全关臂; 与 R494 的 3/3 不同但**跨窗禁相减** ⇒ 记为**未归因质量摆动** (T0 相对 R494-T1 的唯一代码路径差异 = 台账落盘, 不触 prompt)。
- 附带发现/缺陷: ① 夹具「命题核验」工具把**越界被拒**的源文件行**原样回显**进 tool 消息 (B 臂 5 条请求命中块头字面量, 不含真值) = 独立泄漏通道; ② `ledger_*` 打点落在 `tool_decl_gate` (与 `replay_pair_gate` 同一条声明门 emit) 而非 `llm_call` ⇒ 判据器按实况修订, 下轮把字段并入 `llm_call` 便于联表。
- 判据器修订 (3 处, 均带正/负控): (a) 挂载块定义 = **system 角色 + 结构行** (原版把工具回显误判成挂载; `selftest_assert_r495.py` 3 人造例 + 2 真实夹具例全过) (b) 打点字段**扫全部点**并记点名 (c) 轴门只约束**会话**调用, 隔离调用**必须 0 挂载** (证据 = T1 seq=5)。
- 器具/闸: 起手闸首跑即红 (MemAvailable 2,473 < 2,650) ⇒ **让行不硬跑**; 收口 `dotnet build-server shutdown` + `drop_caches` 后 2,657 通过。quiesce 环因 `correction_judge` 计数**缓滴** (11→15 行/2 min) 每臂固定等 ~510 s (夹具自身行为)。
- 能力自检面复核 (候选④): `bind_evidence --check` rc=2 真因 = **本轮只读重跑审计器**改写了 `audit-capability-face.json` (原写侧每次刷新 `audited_at_epoch` ⇒ 冻结 pin 每跑必红) ⇒ 已把写侧改**幂等落盘** (语义未变不重写; 连跑两次字节恒定 `63161c7ec8a4`) 并重钉; 另两项 red (`committed-state` / `only-equivalence`) 现跑 rc=0 (9/9) ⇒ 面文件里的 rc=2 属**旧读数**; `exp1q17` scoped rc=2 vs declared rc=0 的**口径差未闭合**; A3 `manifest_sha12` 声明 `ad97f379503a` vs 现盘 `976b9d0d059c` ⇒ 该面处于**并发会话线改写中**。
- pin 升级 (候选③): `eval/rover/r495/pin_r495.py` → `pin-r495.json` (**src 树哈希 + 产物 sha256 双钉** + `obj` 漂移注记 + 核对码配方钉定); 树脏时 `src_tree_effective` 显式记 `unreported`。
- 测试/AOT: **1556 例** (1555 绿 + 1 红 = 登记表冻结 pin 漂移, 幂等化 + 重钉后 7/7 绿); AOT `/tmp/pub_r495/agenthost` = **15,384,304 B**, **IL 警告 0**, sha256 `2d1ea72d90cd2805…`。
- 诚实边界: ① 判别力面**未演示**(两向, 如上) ② 挂载 token 成本 **+9.2%** ③ 通道轴 (R494 T0↔T1) 本轮**未复测** ④ 每轮 n=1、无置信区间、跨窗禁相减 ⑤ 「隔离调用无会话⇒不挂载」的**设计面**未独立消融 ⑥ T0 质量摆动未归因 ⑦ 上游回复长度摆动仍在 (t13 拒答 379 字 vs T0 拒答 96 字)。
- 下轮候选 (R496): ① **不可复算真值**: 码 = HMAC(进程内随机密钥) 且**落盘不含码**, 机检「该码不在任何可读文件里」(扫 rundir+repo), 挂载文案**显式授权复述**消除 canary 误读 ② 门开臂质量摆动复测 (n≥3 + endorse 归因) ③ 工具面越界回显收口 (回绝即不回显正文) ④ `exp1q17` scoped 口径差闭合 ⑤ MCP/长上下文链级 E2E ⑥ skip 集语义扩面 (同义重复轮) ⑦ `ledger_*` 并入 `llm_call` 打点。
