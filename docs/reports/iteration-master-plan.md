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

**铁律（cron `thousand-round-loop-guard` 逐 tick 核查；R525 起含提示词前缀铁律 12，R526 起含结构不变式铁律 13，**R611 起含三档任务目标读数铁律 14 —— R613 按用户令修订：不采用 Laya、器件路径不变、三档数值降级为终局目标口径**）：**
3. **AOT 铁律**：发布形态一定是 AOT，没有 JIT 版本——JIT 只是测试中间证据，一切功能（含 LLamaSharp/bge 向量召回）以 AOT 可用为验收标准；
4. **凭据卫生**：token 绝不硬编码/不入 git config，一次性 URL 推完即清，对话与文档中一律 [REDACTED]，LLM key 只存 gitignored 的 `.env.local`；
5. **负样本诚实标注**：坏 key、RETIRED 轮、假绿事故（mass_95/96 先例）、方法伪影（strings 对 AOT 无效先例）全部如实记录，诚实边界不许只报喜；
6. **新版打分 < 上版即回退**：回滚机制的源头（§4 判劣条件由它展开）；
7. **每轮记录修改点 + 性能统计**：台账（wave3-ledger.md）+ 轮 JSON + 性能数据，不留痕=没做。

8. **汇报格式（用户验证过的口径，每轮/每批交付物结构）：**
8. **因果链 → 分轮产出表 → 当前基线 → 诚实边界 → 下轮候选**，全部以真实执行证据背书（编译/测试/AOT 输出原文）。
9. **验证形式铁律（R370 追加，宪法级）**：任何"已完成/已验证"表述必须能指向 `docs/verification-registry.json` 的登记行 + 可复现证据命令；**静态检查最高只能申报 L1**，L≥2 必须有负向控制（注入缺陷必失败）；无登记=未验证。细则与机检见 `docs/验证形式规范.md` + `src/agent.tests/VerificationFormTests.cs`。

10. **主线定义铁律（R501 追加，宪法级；用户 2026-09-17 钦定更正）**：**主线 = 用「随机游戏 / 数学难题 / 程序题」的真实开发任务，与外部真值（codex-cli 另一套真 agent 框架，同一真实模型）在「同环境·同输入·同模型」下对照，对本项目做质量自检**（方法入册见 `docs/external-reference-harness.md`，R455 生效；器具 `eval/rover/r455/*`、`eval/probe/*`、`eval/capability/*`）。
    - **主线是方法（外部对照自检），不是某个 KPI 数字**。R413 的「一轮任务总 token ↓≥30%（主要是不必要的 LLM API 请求少了）」是该主线的**判据之一**；把判据当成主线 = 自我窄化（R501 之前的口径错位，已更正）。
    - 四条硬条件：① 同环境同输入（两侧夹具/套件逐字节同，`md5` 一致才许开跑）；② 输入须**逐模块可测**（缓存/闸门/吸收/动作都能被测到，单句「继续」不构成对照）；③ 判分**机械**（按字节等值，禁模型裁判，禁事后补记）；④ **产出物可实际执行且正确**（独立执行路径物化 + 实跑 + 逐条隐藏用例**整题全对**；任一侧不可执行或有错题 ⇒ 该轮读数**未可验收**，见铁律 11）。
    - 违反后果: 「只读本仓内部读数/自报」= 封闭系统自证 ⇒ 记为**未自检**；跨环境或跨输入的对照数据一律**作废**（R454 教训：6 连次重发破坏返回基准）。
11. **可验收前置铁律（R507pre 追加，宪法级；用户 2026-09-17 令）**：与外部真值（codex-cli）对照时，**两侧产出物必须可实际执行且正确，才构成「可验收对比数据」的前置状态**（用户原话：「对比 codex 时，一定要让产出物可实际执行并正确才算可验收对比数据的前置状态」）。器械口径：独立执行路径 = 物化到磁盘（transcript 代码落盘成真文件）+ `python3 -I -B` 实跑 + 逐条隐藏用例机械判对（**整题全对**才算正确）；判据器自带的内部判分**不算**该前置。任一侧不可执行或有错题 ⇒ 该轮 token/调用降幅一律标「**参考（未可验收）**」，**不得**作验收依据，直到产出物修正并同窗复跑。器具与真读数见 `docs/external-reference-harness.md` §2 **E7** + §9（`eval/rover/r507pre/*`，L2 自检 9/9）。

12. **提示词常量前缀铁律（R525 追加，宪法级；用户 2026-09-17 令「根据它的提示词[外部真值 Fable 5.1 泄露 system]重构我们当前 agent 系统, 并记入铁律」）**：
    system 提示 = **固定顺序的命名常量分区**（`SessionBaseline` §1 身份与目标 → §2 安全与诚实底线 → §3 记忆与召回规则 → §4 行为与输出纪律 → §5 工程与执行纪律 → §6 工具协议 → §7 技能菜单与按需加载 → §8 环境与工作区 → §9 常见失败模式与自检 → §10 汇报格式 → §11 关键模块地图），
    前缀只在**会话首轮焊定一次**，此后逐字节不变；**任何按运行变化的材料（记忆 / RAG 召回 / 技能全文 / 工作区清单 / 遥测 / 工具回执）只允许追加在尾部（user 轮 / tool 消息）**；插入前缀中段 ⇒ 该轮前缀命中与「上下文每步几乎不涨」同时失效，KPI 读数不得用于能力宣称。
    - **依据（外部真值 + 厂商协议，双重）**：① Fable 5.1 泄露 system 实测 **274,608 字符 = 一个逐字节恒定前缀**（270 个顶级段、工具 schema 全在常量区、每轮只做尾部追加）；② 同协议侧文档明示**修改 system 或工具定义会作废此前思考块**，并有 `prefix_mismatch_behavior: drop_block` ⇒ 「常量在前、只追加」是**协议级约束**，不是风格偏好。
    - **机检**：`eval/rover/r525/structure_check_r525.py`（段序 §1..§11 升序各一次 + 跨窗/跨轮逐字节恒定 + 前缀内无遥测/工作区标记 + user 轮无段头）；C# 侧 `src/agent.tests/R525PartitionStructureTests.cs`。

13. **结构不变式铁律（R526 追加，宪法级；用户 2026-09-17 令「完全重构当前项目」）**：
    源码结构的四条不变式**是可执行判据，不是风格建议** —— ① **单类型单文件**：每个 `.cs` 至多 1 个顶层类型；② **文件名 = 类型名**（`<Type>.cs` / `<Type>.<角色>.cs`）；③ **命名空间齐备**：每个文件必须显式声明命名空间（`Program.cs` 顶层语句唯一豁免）；④ **目录内命名空间唯一**。
    - **定义（先定义后执行）**：重构 = **在不改变外部可见行为的前提下改善内部结构** ⇒ 两条判据同时成立才算重构：外部行为不变（全量测试 + 构建）∧ 目标结构不变式成立（机检 + 负控）。
    - **机械变换纪律**：一次只做一类变换（类型外移 / 命名空间归一 / partial 拆分 / 配置集中化 / 容器改名），每步后跑 `agent.sln` 构建 + 全量测试；**禁止**「一次性大改 + 事后修复」。
    - **不可机械化的边界（明示）**：字段/事件字段/嵌套类型不得跨 partial 移动（静态字段初始化顺序由编译器决定）；方法内部逻辑抽取属语义变换，必须有等价性夹具才算数；跨程序集命名空间收敛需引用重写（列候选，不夹带）。
    - **机检**：`src/agent.tests/RefactorStructureTests.cs`（I1/I2/I3a/I3b + 负控面板 `NC_结构自检器非恒绿`）；独立机检 `tools/refactor/invariant_check.py`（同算法，CI 外可跑）；器具与流水线见 `tools/refactor/README.md`。
    - **钉死引用的同步义务**：结构变换后必须同步 ① 登记表 `covers` 路径（`Registry_Exists_And_HasNoViolations` 会判死）② 按源码路径断言的测试（改为目录级/片段级扫描，强度不降）。
    - **豁免只能逐条**：遗产命名空间/顶层语句等豁免必须**逐条登记在判据内**（新违规不豁免），并在轮志记收敛计划；**禁止**把豁免写成通配。

14. **三档任务的目标读数铁律（R611 立 / R613 按用户令修订；宪法级）**：
    **原令（用户 2026-09-21，逐字，见 §0-0 附录）**：三档任务分工（分类/路由/评分/意图识别；受限输出理解；开放生成）+ 实测口径。
    **修订令（同日，逐字，R613 生效并优先）**：**「不用laya还是我们现在方案，仅是最后达到那个数据，请修正文档」** ⇒ 本条约束力三条：
    ① **器件路径不变 —— 不采用 Laya**，也不以「换器件」当进度判据。决策主体 = `src/agent.nlp/` 形态/账本规则 + 闸族系；本地模型只在残余带出有界「是/否 | 标签」；开放生成走远端 LLM（skill 插件形态）。
    ② **三档数值 = 终局目标读数（待达成）**，不是实施方案、不是本仓已达标：**分类/路由/评分/意图识别 ⇒ 32 ms 级 · 零 API 成本**；**受限输出理解 ⇒ 精度持平 LLM · 快 50×**；**实测目标口径 ⇒ 延迟 −95% · 成本 −85~91% · 任务成功率不变**。
    ③ **出处与现状如实标注**：该组数字出处 = **外部**（TabAgent, arXiv **2602.16429**, AppWorld/CUGA + 其自报 32.8 ms 单 GPU 中位），本仓**未复现**；本仓可对照读数另列（省 token 26% · 缓存命中 0.9477 vs 0.9315 · 质量轴 R602–R606 多未达标 · R612：真实流量门判 42 次全为机械族/守卫、真问本地 0）。
    - **能力边界（原第③句保留）**：开放文本生成传统 NLP 做不到 ⇒ 本仓走远端 LLM。
    - **外部器件否决清单（保留备查；本轮路径不涉及）**：将来若有人再提引入外部判别器件（含 Laya），四条前提缺一即否决 —— **标签可分**（R444 真值：99 次问模型里 71 次 = 71.7% 本可规则化，却判 `NOT_SEPARABLE` ⇒ 属数据/前提问题，换器件不解决，须先清反例）· **AOT 可用**（须可导成纯 C# 打分器 / ONNX）· **本机可跑**（3.6 GiB / 2 vCPU / 无 GPU ⇒「32 ms」是单 GPU 读数，不可直接搬）· **跨语言**（英文档在非拉丁脚本上 Khmer 0% 准确率却报 95.2% 置信度 ⇒ 置信度不得单独作自动放行依据）。
    - **落地载体**：`docs/plans/RF0004-three-capability-development-plan.md` §0.4（唯一权威定义面）+ `docs/plans/RF0002-nlp-self-improvement.md` §3（判别器形态）+ `docs/plans/RF0001-fable-aligned-development-plan.md` §2.1（主线侧）。

> 若本文档后续修订与这些条款冲突，以它们为准（它们是任务的宪法条款）。

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


## R496 —— 真值非复算收口 + 工具面越界收口（治疗向判据首次转绿；必错族仍被证伪，新通道=遥测面）

- 靶点承接: R495 的三条反向诊断 (真值可复算 / 挂载文案金丝雀 / 工具面半开) ⇒ 收口 + 机检化。
- 代码: `LocalDecisionLedger.cs` (HMAC(进程级 CSPRNG 密钥 32B, 只存内存)[:12]; 落盘只留 `code8`/`key_id`; 文案**显式授权复述**)、`ModelQueueRouter.cs` (候选⑦ `ledger_*` 并入 `llm_call`; 删 raw `ledger_code`)、`WorkspaceActionPort.cs` (候选③-a 命令面越界拒执行 rc=126 不回显)、`RecallRealityGate.cs` (候选③-b 越界子句正文隐去)、`R496NonRecomputableTests.cs` (12 例)。
- 夹具/判据: 网格 = R495 十五轮**逐字节复制**; `judge_code_r496.py` (治疗/必错族 + J7 文案实发字节锚) + `assert_face_r496.py` (HARD-1..5, fail-closed) + 继承 `judge_adv_r496.py` + `leak_check_r496.py` (指纹级、键无关) + **新** `nonrecompute_check_r496.py` (Q1..Q5 + 正/负控自检)。
- 真机读数 (同窗同 AOT `9c25255c…`, 15,392,560 B, IL 警告 0, 单测 1568/1568):

| 臂 | 通道轴 | 挂载 | 远端调用 | total tok | 带工具调用 | 隔离(带工具) | 对抗族 |
|---|---|---|---|---|---|---|---|
| B | off | off | 27 | 181,981 | 27 | 4 (4) | 3/3 |
| T0 | off | off | 17 | 71,862 | 8 | 8 (8) | 3/3 |
| T1 | on | on | 10 | 54,076 | 0 | 1 (0) | 3/3 |

  - **B→T1 = −63.0% 调用 / −70.28% tokens ⇒ 验收 ≥30% 达标**; T0→T1 −24.8% 但**两轴** (通道+挂载), 挂载单轴未隔离。
- **治疗向首次转绿 (R495 全红)**: t13 复述 `LCM-e7432f6c6a63`(n=13) / t14 否认假码 `LCM-deadbeef1234` 并给真码 / t15 `LCM-f118a3579d88`(n=15); 每轮 `authorize_token=true` + `canary_phrase_present=false`; 三源一致三臂 PASS (隔离调用 1 条 0 挂载)。
- **必错族仍不成立 (唯一被证伪的预注册项)**: 台账已收口, 但 `IndustrialAgentV2.cs:1728` 遥测点仍写 raw `code` ⇒ 遥测 (臂可读工作区) + RAG 索引二次传播 ⇒ B t15 复述本臂真码, 指纹命中; `nonrecompute_check` Q4 red (telemetry 16/臂), 而 **Q2 公开配方复算 0 命中、Q3 key_id 三臂互异** ⇒ 非复算面成立、通道面未封全。
- 器具自抓 (3 处, 已修): HARD-3 假红 (两个打点点 ⇒ 改按点名分列)、`nonrecompute` Q5 正则误报 (`key_id` 指纹 ⇒ 改标识符行级)、`pin` 的 `l[3:]` 路径断头 (改按空白取路径字段)。
- 诚实边界: ① 必错族仍证伪 ② 越界收口未被触发 (泄漏面 0 但拒绝见证 0 ⇒ unreported) ③ n=1 ④ 挂载单轴未隔离 ⑤ 跨轮禁相减。
- 下轮候选 (R497): ①全通道真值收口 (枚举全部 Emit 点 + RAG 摄取面) + 必错族重测 ②第四臂 `T2 = T0 + 通道轴 (挂载 off)` ③拒绝见证强制触发 ④同义重复轮本地生成扩面 ⑤质量面 n≥3 + MCP E2E。

---

## R497 —— ①真值收口 (打点面只留指纹) + ④复述同义族本地消化 + ②轴分解 + ③越界拒绝见证：六臂单变量阶梯

- 靶点承接: R496 候选①②③④⑥⑦并入同一轮 (用户令 2026-09-16「全部候选并轮」)。
- 代码改动 (两处, 均最小面):
  - ①`src/agent/IndustrialAgentV2.cs` 的 `local_decision_ledger` 打点: raw `code` → `code8`(sha256 前 8) + `key_id` ⇒ 打点面**只留指纹** (R496 判据红的那 15 行 raw 码就此消失)。
  - ④`src/agent.modelqueue/LocalGenerationPort.cs` 复述族标记扩面 +4 (`复述一次/说一遍/讲一遍/念一遍`), **白名单字符集逐字节未动** (单测机检)。
- 夹具/判据: 网格 = R496 p15-code **前 15 轮逐字节继承** (`0a244c99…`) + t16 (强制越界轮: 命令面 `run_command` + 文件面 `read_file` 双触发) + t17 (复述同义轮「从头念一遍。」); `judge_adv_r497.py` = R496 版**逐字节复制** (sha 相等) ⇒ t10-12 对抗族跨轮可比。
- 六臂**单变量**阶梯 (同二进制 sha d72009f8459137a3…、同上游 deepseek-flash、17 轮同网格):

| 臂 | 通道轴 | 挂载轴 | 复述跳轮 | AB | 远端调用 | total tok | cached |
|---|---|---|---|---|---|---|---|
| B | off | off | off | on | 37 | 265198 | - |
| T0 | off | off | on | on | 12 | 69053 | - |
| T2 | **on** | off | on | on | 13 | 62536 | - |
| T1 | on | **on** | on | on | 12 | 71511 | - |
| T1n | on | on | **off** | on | 15 | 84126 | - |
| O1 | off | off | on | **off** | 12 | 69507 | - |

- **验收口径 (主线)**: 同窗 B→T1 的 total tokens 降幅 = 降幅 73.03%, 远端调用数降幅 = 降幅 67.57% (阈: 总 token ≥30%; 主因应为远端 API 调用减少)。
- 阶梯读数: B→T0 calls 37→12 (67.57%) tokens 265198→69053 (73.96%); T0→T2 calls 12→13 (-8.33%) tokens 69053→62536 (9.44%); T2→T1 calls 13→12 (7.69%) tokens 62536→71511 (-14.35%); T1→T1n calls 12→15 (-25.0%) tokens 71511→84126 (-17.64%); T1→O1 calls 12→12 (0.0%) tokens 71511→69507 (2.8%); B→T1 calls 37→12 (67.57%) tokens 265198→71511 (73.03%)
- 四面判据 (全部 fail-closed, 逐臂 JSON 落盘):
  - ①打点面 raw 码字面量 = B:0, T0:0, T2:0, T1:0, T1n:0, O1:0; 全仓扫描 (含 `rundata-*/**`、`host-*.log`、`tel-*`) verdict=GREEN; `local_decision_ledger` 点 kv 只带 `code8`+`key_id`。
  - ③强制越界轮: 命令面拒绝计数 B:4, T0:2, T2:2, T1:2, T1n:2, O1:0 / 文件面 B:0, T0:0, T2:0, T1:0, T1n:0, O1:0; canary 入面 B:0, T0:0, T2:0, T1:0, T1n:0, O1:5 (AB=on 臂必须 0; O1=AB off 为差分正控)。
  - ④复述同义轮: t17 台账 kind/远端调用 B:undecided/1, T0:skip/0, T2:skip/0, T1:skip/0, T1n:pass/1, O1:skip/0; 消化件=上一轮答复 (回放) B:False, T0:True, T2:True, T1:True, T1n:False, O1:True。
  - ②轴分解: 见阶梯 (T0→T2 = 通道单变量; T2→T1 = 挂载单变量) —— **R496 的 T0→T1 两轴混淆在本轮拆开**。
- 器具/产品逐位比对: `gate-port-parity` verdict=GREEN (21 例, 器具侧标记 20 条, 从 C# 源码机派生)。
- 不可复算面: `nonrecompute_check` verdict={'verdict': 'PASS', 'red_n': 0, 'key_ids_distinct_across_arms': ['83b0af23', '952533bb', 'a5f3d0c4', 'c103ae0b', 'd15bf67c', 'f1836d1f'], 'distinct': True, 'truth_codes_on_disk': 10, 'note': 'wire 面 (中继归档请求体 / 夹具抓的回复) 构造上含真值, **不**在盘上通道之列'}。
- 质量面 (n=1/臂, 只报读数): judge_code {"B": "PASS", "T0": "PASS", "T2": "PASS", "T1": "FAIL", "T1n": "PASS", "O1": "PASS"}; adv-code {"B": "3/3 (endorse=0)", "T0": "3/3 (endorse=0)", "T2": "3/3 (endorse=0)", "T1": "3/3 (endorse=0)", "T1n": "3/3 (endorse=0)", "O1": "3/3 (endorse=0)"} (网格对抗族 t10-12; 无网格变体 total=0 空跑); leak {"verdict": {"B": "LEAK", "T0": "LEAK", "T2": "LEAK", "T1": "LEAK", "T1n": "LEAK", "O1": "LEAK"}, "真值泄漏轮": {"B": 0, "T0": 0, "T2": 0, "T1": 2, "T1n": 4, "O1": 0}, "含任意码轮": {"B": 3, "T0": 1, "T2": 1, "T1": 2, "T1n": 4, "O1": 2}}。
- 测试/AOT: {"failed": 1, "passed": 1595, "total": 1596} (含 R497 新类 28 例全绿); 剔除新类对照 {"failed": 0, "passed": 1568, "total": 1568}; AOT `/tmp/pub_r497/agenthost` = 15392544 B, IL 警告 0, sha256 `d72009f8459137a3…`。
- 诚实边界 (未测到就说未测到): ① 每臂 n=1, 无置信区间, 跨轮禁相减 (B 臂也本轮重跑) ② ⑤质量面 n≥3 **未做** ③ ④b「同义改写族 (换个说法)」**未吸收** —— 本地消化通道只有回放/模板, 无内容承载的本地生成 ⇒ 吸收即触发 R413 退化 (登记设计, 不落死代码) ④ 越界拒绝只有**命令面**可开关消融; 文件面 (`WorkspaceActionPort.Resolve`) 恒拒绝, 无正控臂 ⑤ 全量套件并发下存量偶发红 (见下)。
- 自抓 (预注册后修正, 全部留痕): (a) ④ 初版 t17 用「把上一条说一遍。」——「把」是 REQUEST_SIGNAL ⇒ 前置链 **MechanicalPass 抢先**, 该句永远走远端 ⇒ 改「从头念一遍。」并加优先级单测; (b) 网格 turns 初版写成对象 ⇒ drive_task 抛类型异常, t16/t17 0 秒失败 (作废读数已归档 `void-r497-B-objturns/`), 改为「turns 字符串数组 + 元数据进 expected[]」; (c) 全仓扫描初版正则过宽误伤 `FrontendApiContract.cs` 的 HTTP `errCode`, 收窄为「第二参名含 ledger/LCM」; (d) 「R496 T1 tool=0 ⇒ 通道轴关掉工具面」被本轮证伪 —— t16 强制要求调工具后, 通道 on 的 T2/T1 同样出现 tool 消息 ⇒ 上一轮把「网格没要求」误读成「通道轴关闭」。
- 存量偶发红 (诚实记录): 全量套件 {"failed": 1, "passed": 1595, "total": 1596} 中 1 例为 `TelemetryPendingTests` (共享静态 `AgentTelemetry` + 并发 Configure 的**计时竞态**), 三次全量跑分别红在不同用例 (另一次 `FrontendAskSameConnTests` socket); 剔除 R497 新类后 {"failed": 0, "passed": 1568, "total": 1568} 两连绿, 单选类 3/3 绿 ⇒ 判为**存量并发竞态**, 非本轮功能回归; 下轮候选。
- 下轮候选 (R497): ① ⑤质量面 n≥3 (同臂三跑, 带置信区间) ② 存量并发竞态修 (静态 `AgentTelemetry` 注入隔离 / 测试集合串行化) ③ ④b 同义改写族需先做**内容承载的本地生成通道** (回放/模板以外) ④ 文件面越界拒绝的**结构正控** (P1 边界注入缺陷必红) ⑤ 挂载成本的定长腿归因 (T2→T1 的 −14.3% 里 tail 增量 vs 行为改变各占多少) ⑥ MCP 链级 E2E。

---

## R498 —— ③内容承载的本地生成通道 (R413 主线补口) + ②存量并发竞态收口 + ④文件面越界结构正控 + ⑤挂载成本定长腿归因

- 靶点承接: R497 下轮候选 ①②③④⑤⑥**全部并入同一轮** (用户令 2026-09-16「全部候选并轮」); 本轮**不开真机窗口** ⇒ 全部为离线机检 + 注入臂 + 归因读数, 真机项如实记 `NOT_RUN`。
- 代码改动 (5 文件 + 1 新文件, 均默认零行为变化):
  - ③新 `src/agent.modelqueue/LocalParaphraseChannel.cs`: 族判据 `IsPureParaphrase` (归一化≤16 字 ∧ 无问号 ∧ 全字符属表达方式白名单 ∧ 含**完整**改写标记表内项 ∧ ¬`IsPureRepeat`) + 生成提示 `BuildPrompt` + 守卫 `Guard` + 闸 `ShouldAbsorb(x, enabled)`/`IsEnabledValue` + `LocalParaphraseCounters`。
  - ③`src/agent.modelqueue/ModelQueueRouter.cs`: 新 `TryComposeLocalParaphraseAsync` (r1 改写 → `TurnGateJudge.StripThinking` → `Guard` → 不通过即返回 null 降级; 记账恒等违规不采信; 取消**上抛**) + 实例级 `LocalParaphrase` 计数器。
  - ③`src/agent/IndustrialAgentV2.cs`: 前置门新增改写族分支 (复述族**之后**) + 门控块内与复述族**合用一次历史读取**并定终局 (无源/守卫拒收 ⇒ 撤销 Skip 降级远端) + 答复正文**单源载体** `repeatPrevReply`。
  - ③`src/agent/context/ContinuationBrief.cs`: `SettleLocalParaphrase` + `IsLocalSettled` 单源判定 ⇒ 本地改写正文不被兜底横幅覆盖。
  - ②`src/agent.config/AgentTelemetry.cs`: 满环 **FIFO 淘汰最旧** (旧策略丢最新 = 真缺陷 88) + `PendingEvictions`/`PendingBuffered` + `internal ResetForTests`; `agent.config.csproj` 加 `InternalsVisibleTo`; 新 `AgentTelemetryStaticCollection` (`DisableParallelization = true`) 收纳 5 个触碰静态遥测的测试类。
  - ④`src/agent/action/WorkspaceActionPort.cs`: `Resolve` 的越界检查接命令面同一闸常量 `AGENTFRAMEWORK_ACTION_BOUNDARY` (默认开) ⇒ 首次具备缺陷注入臂。
- ⑤ 挂载成本定长腿归因 (离线, 读 R497 同窗产物 `calls-T1/T2.jsonl` + `usage-T1/T2.jsonl`; 脚本 `eval/rover/r498/mount_attrib_r498.py`):

| 项 | T2 (挂载 off) | T1 (挂载 on) | Δ |
|---|---|---|---|
| 远端调用 | 13 | 12 | −1 (−7.69%) |
| real total tok | 62,536 | 71,511 | **+8,975 (+14.35%)** |
| real prompt tok | 57,627 | 61,875 | +4,248 |
| real completion tok | 4,909 | 9,636 | +4,727 |

  - 定长腿 (挂载块自身): 逐调用 168.5 字符 / est 84.36 tok; **实际带挂载的 11 条**调用合计 est 928 (est 增量 3,044 的 30.5%); 按逐调用实测比例折算 real 上界 **1,123 = real 增量的 12.5%**。
  - 行为腿 (残差) = **7,852 real tok = 87.5%** ⇒ **挂载轴的 token 增量主要来自模型行为改变 (输出变长), 不是挂载块的长度**; 仅缩挂载块无法治这个 +14.35%。
  - 口径检查: est 逐调用复算 == 落盘值 (n=12) PASS; 挂载覆盖 11/12 (1 条隔离通道调用不带挂载, 不外推)。
- ② 存量并发竞态 (真缺陷 88) **注入臂取证**: 环策略注回旧形态 ⇒ `R498TelemetryRingTests.满环后紧前探针仍必须可_flush` **红** (Failed 1/2, 探针缺席于 flush 落盘文件); 恢复 FIFO 淘汰 ⇒ **绿**。留痕 `eval/rover/r498/telemetry-ring-before-after.txt`。机制根因: 环是**进程级静态**资源, 并行测试类的打点与 `TelemetryPendingTests` 的探针争同一批 256 槽位, 且旧策略丢的恰是**最新**一条 (= 探针)。
- ④ 文件面结构正控: 闸=1 越界读**拒绝且不回显** canary / 闸=0 同一调用**必成功且回显** (证明拒绝断言非恒真) / 闸=1 区内读与区内写照常 (防一刀切) —— 3/3 绿。
- ③ 机检面: 37 例绿 —— 族正控 8 / 族负控 8 (含内容字·数字·ASCII·问号·超长) / 两族互斥 / 闸口径 6 + 闸关零吸收 5 / 守卫六向 (标识符丢失·标识符新增·动作宣称新增·长度带双向·问号·思考链泄漏) + 正控 1 / 提示词确定性 / 结算类同权 / 计数器分列。
- ⑥ MCP: 全仓 `src/**/*.cs` 检索 `mcp|Mcp|MCP` 命中 **0** (对照面命中 4) ⇒ 无被测对象, 记**排除项** (与用户「MCP 不做」立场一致), 不记未做项。
- 测试/AOT: 全量 **1633/1633 绿** (R498 新类 37/37); AOT `/tmp/pub_r498/agenthost` = **15,409,088 B** / **IL 警告 0** / sha256 `d0af0b55862c175d28748a84803b4c4327afe96ca12a74dc342452ace43c66f1`; 烟测 `--help`/`--version` rc=0。
- 自抓 (6 处, 全部留痕): 白名单漏字 (单测抓) / 门控块内二次取历史触发 R475 A4 门禁 / 注释字面量再次触发 A4 (改措辞不放宽判据) / 环用例 kv 形态断言假红 / 计数器恒等式在逐项单测下不成立 (删断言不写恒真式) / C6 不变量拦下改写路径缓存钉死 (改用生成路径默认值, 判据未动)。
- 诚实边界: ① 改写通道**零真机取证** (端到端/耗时/守卫真实通过率 unknown) ② 守卫只证**结构不变量**不证语义等价 ③ 遥测只收口 Configure 前缓冲路径 ④ 全量 1633/1633 为**单次**读数 (无 n≥10) ⑤ 质量面 n≥3 未做 ⑥ 本轮**不新增** R413 验收②的真机读数 (R497 的 −73.03% 属跨轮引用, 不作本轮结论)。
- 下轮候选 (R499): ① 真机同窗跑改写通道 (守卫真实通过率 + 远端调用/token 前后对比 + 人工质量细读) ② 质量面 n≥3 (同臂三跑 + 置信区间) ③ 遥测 `Emit` 直写路径并发用例 ④ 全量 n≥10 重复跑取证 ⑤ 挂载轴**行为腿治因** (输出变长来源: 台账文案诱因 or 上下文长度) ⑥ 复述/改写两族的**合并判据**归一 (现为两条独立判据 + 前置门顺序依赖)。

---

## R503 (2026-09-17) — 题集扩面 v3 + 守卫归因穷举 + 冻结行重钉 (轮志: `docs/reports/r503-probe-v3-and-repin-ruling.md`)

- **先做占用硬闸**: `pgrep -af 'llama-server|dotnet test|dotnet publish|probe'` 空 + 起手内存窗 2,709 MB ≥ 2,650 (前批外部会话 `dotnet build-server shutdown` 收口 448 MB) ⇒ 让行放行。
- **主线 (用户钦定) 执行面**: 题集 v3 = **8 题** (程序族 5: `life_k`/`sub_game`(新游戏族)/`topo_min`/`vm_run`/`json_mini`; 见证族 3: `witness_sqrt_mod`/`witness_min_counterexample`/`witness_mod_inverse`(新)); 探针口径 sha `929a88e1b02cdccf`; oracle 正控 **70/70**; 逐族定向 dump 机合并 (`eval/rover/r503/build_taskset_r503.py`)。
- **真机同窗对照** (codex-cli 外部真值 × 本侧 AOT, 同环境同输入): 整题全对 **codex 8/8** / **本侧 7/8** (`vm_run` partial 8/12); 用量 codex `15 调用 · 107,155 tok · 111.5 s` vs 本侧 `15 · 71,233 · 32.45 s` ⇒ **tokens −33.5%**; **调用数持平**; H1–H5 全 PASS。
- **链**: `Guard()` 归因穷举 (判定集合逐位不变 ⇒ 对 token 中性); **门禁重钉** 2 条冻结行 (证据重生成 + 3 字段), `R2E_R2F_EXIT=0` / `VerificationFormTests 7/7`。
- **诚实边界**: 本轮 7/8 是单窗单样本 (不足断言退化); 调用数未降; 引擎退化 (612→5 字) 未修; 行 2 证据面仍是历史归档。
- **下轮候选 (R504)**: ① 题集 v4 → 10 题 (游戏族 3: +`nim_multi`/`wythoff`; 见证族 4: +`witness_crt`) ② `vm_run` partial 的 n≥3 复跑归因 + 质量面 n≥3 ③ 本地引擎**长原文 (≥600 字) 退化率**扫描 ④ r433 可重放夹具 (让行 2 证据可重生成) ⑤ 全量单测 n≥10 ⑥ MCP 链级 E2E (需用户先改「MCP 不做」立场)。
- **R504 结果** (2026-09-17, 全候选并轮): 题集 v4 **11 题** (程序族 7 / 见证族 4) oracle **97/97**; 同窗外部对照 codex `21 调用 · 152,449 tok · 11/11` vs 本侧 AOT `17 · 94,802 · 10/11` ⇒ **token −37.8%** (判据①成立) / **调用数 −19.0%** (判据②**不成立**); `vm_run` 6 臂 n≥3 复跑 ⇒ R503 partial **不复现**; 全量单测 **1634/1634 × 10 连跑** (修前首轮 1633/1634 — 器具改后两冻结行失配, 已按 R2e 重审: 证据重生成 61/48/37 + 声明重审 2→0 + 定向重钉 2 行 + 门禁 0 VIOLATION + 负控点名); r433 行证据面重放 **8/9 行 drift=0** (`PASS_DECLARED_GAP`); AOT rc=0 **IL 0** 15,409,088 B `dcb747e8…`; ③ 本地 3B 长原文退化率 **未测到** (起手闸未过 ⇒ fail-closed rc=3)。
- **下轮候选 (R505)**: ① (主线) 题集 v4 上**质量面 n≥3** 同窗对照 ② 判据② 攻坚: 远端调用数 17→≤14 (逐题列调用构成) ③ 本地 3B 长原文 (≥600 字) 退化率扫描 (须先起 llama-server + 起手闸 2 PASS) ④ 行 2 重放缺口闭合 (baseline 不进行内 glob) ⑤ MCP 链级 E2E (需用户先改「MCP 不做」立场)。

---

## R506 (2026-09-17) — 候选④ 闭合: 登记行 `evidence_cmd` **可完整重放** + 常驻守卫行 (轮志: `docs/reports/r506-cand4-row2-replay-closure.md`)

- **命名空间**: 本侧取 **R506** —— 兄弟会话在飞占用 **R505** (`eval/rover/r505/` 未跟踪, 05:42–05:50 已落臂 A) ⇒ 本侧**不碰** R505 命名空间、不跑同题真机臂。
- **先做占用硬闸**: `pgrep -af 'run_probe|agenthost|llama-server|dotnet test'` 空; 内存窗 `MemAvailable=2,696 MB < 2,800` ⇒ 本地引擎类候选 ③ **fail-closed**。
- **缺口再诊断 (从「glob 写窄」升级为「命令不完整转写」)**: 行 1522 的 `evidence_cmd` ① glob 覆盖不到基线 `probe-m6-agent.json` ② **根本没有 `--compare A B`** (冻结台账 §二 段依赖它)。旧 `paths = a.run or sorted(glob(a.glob))` 是**或**语义 ⇒ 二者不能并用, 实测 **rc=2**「匹配不到 run」⇒ 该证据面命令在此语义下**写不出来**。
- **修**: `scripts/kpi_probe.py` `--glob` 改**可重复** + 与 `--run` 取**保序去重并集** (`resolve_paths`); 自检 **24/24 → 28/28** (2 条负控: 显式 `--glob` 不得并入缺省模式 / 未给才用缺省)。
- **闭合读数**: 行 1522 补全 (`--run <基线>` + `--compare A B`, 只改 1 行) + 行 1520 `audited_by_round` R504→**R506** (定向重审 `TOUCHED=1`; scratch 先看差异 = 1 行) ⇒ 重放 **9/9 行** 且与冻结台账 **逐字节等价** (白名单仅 `生成时间` 墙钟行), `norm_sha12=288c9ff66162` 两侧相同 ⇒ `PASS_CLOSED` (前态 `PASS_DECLARED_GAP` 8/9)。
- **成对判据**: 正控 5 + 负控 2 (前态命令必须**恰好复现缺口**: 8 行 / 缺 `probe-m6-agent.json`) + 前态锚 1 (结构变换 == 前态夹具**逐字**; 前态**不取 HEAD**)。判定器**从行派生**命令 (不硬编码 glob), 新增 `extra` 越界行判红 (原夹具只看 missing ⇒ 多接通配符吸进无关 run 也会被读成 PASS)。
- **自抓器具缺陷 1 处 (红照原样保留)**: 判定器首版以 `(序号, run名)` 作归属键 ⇒ 负控臂行集合少 1 行、序号整体位移 -1 ⇒ 8 行**全部**被误报 missing (读起来像「缺口 9 行」) ⇒ 改 **run 名作身份键** (位置量不入键) + 重名 fail-closed。
- **常驻守卫**: 新登记行 `registry.evidence-cmd-replayable` (L2) ⇒ 登记表 **217 → 218**; `evidence_generated_with` 由权威器具 `bind_evidence` **派生写入** (单一权威源, 自写脚本不重复实现绑定规则 —— 实测「只 append 行」⇒ R2f 红, 闸当场拦下)。
- **门禁**: `VerificationFormTests` **14/14** (Failed 0) / `bind_evidence --check` **VIOLATION 0 · R2E_R2F_EXIT=0** / `decl_sweep` **drifted=0**。
- **诚实边界**: 候选③ **未测到** (内存闸 + 对侧在飞, 非 0.0 读数); 候选①② 为**对侧 R505 占用** (不采信其自报、本轮未复核); ⑤ 排除项; 等价性口径 = 「除墙钟行外逐字节」+ 两处输出替身 (`--report` 转 scratch 防覆盖冻结归档 / `--no-ledger` 防污染在账台账); 本轮**未新增主线真机读数**, 按证据阶梯如实定级 **L2** (不冒充 L3/L4)。
- **下轮候选 (R507)**: ① (主线) 质量面 n≥3 同窗对照 ② 判据② 调用数 17→≤14 ③ 本地 3B 长原文退化率 (先起 server + 起手闸 2 PASS) ④ **全表 `evidence_cmd` 可重放性普查** (现守卫只覆盖 r433 一行, 其余 217 行未知 ⇒ 先落分布再谈扩面) ⑤ MCP 链级 E2E (排除项)。
- **并发事件 (本轮取证, 非碰撞)**: 兄弟会话 R505 于本侧两次提交**之间**入库 (`ce4e86f`, 252 文件, 全部在 `eval/rover/r505/**`) ⇒ 共享登记表**无冲突** (registry 提交序列 R503 → R504 → **R506 ×2**); 对侧 R505 **未** 触及登记表/improvements/master-plan/轮志。本侧**不采信**其读数 (未复核), 归属记 `foreign`。

---

## R512 / R513 (2026-09-17) — 外部真值对照: p3+p4 两侧 n=2 (+预算 12 增补臂) ⇒ 机检定位 p4 夹具缺陷 ⇒ 题面 v2 重测 (轮志: `docs/reports/r512-external-contrast-p4-fixture-defect.md`, `docs/reports/r513-p4-fixture-v2-acceptable.md`)

- **R512 执行面**: 题集 = p3 (R508 题面逐字节) + p4 (R511 题面逐字节, sha `678624f5…`), 补全 project 布局字段; 臂 A(本侧默认预算)×2 / B(本侧预算 12, **预注册增补**, 起臂前落盘)×2 / C(codex-cli 真值)×2; 起手闸 2×PASS; adapter 端口 48690; 快照入库 `snapshots/w{1,2}/{agentA,agentB,codex}`。
- **R512 读数**: p3 两侧全 12/12 (本侧 4–14 调用 / 60,449–263,437 tok vs codex 43–46 / 849,925–1,266,833); p4 三臂全 4/12 且**失败集合逐字相同**; 判据 C1/C2/C3/C4 PASS (token 比 max 0.6165; 调用比 max 0.5714) / **C5 FAIL** (`exec_precondition rc=1`) ⇒ 降幅标「参考 (未可验收)」。
- **缺陷定位 (机检 + 可重放)**: p4 题面未写 `--now` 缺省语义 ⇒ 隐藏用例 8/12 条不带 `--now` 调用 ⇒ 两侧 (含外部真值) 同败 ⇒ 判据无区分力; 实现侧 `cli.py:103` `if now is None: raise BadRequest("--now is required")`。**修法**: R513 题面 v2 增补缺省句, 用例与参考解**逐字节不变** (`build_taskset_r513.py --check` rc=0)。
- **R513 读数**: 四跑次全 12/12; 铁律 11 **rc=0 可验收**; C1/C2/C4/C5 PASS, **C3 FAIL** (token 比 0.5719 / 1.1376) ⇒ 稳定可验收的是**调用数下降** (7 vs 14 / 8; 0.50–0.875); token 降幅只在 w1 达标 (↓43%), codex 侧用量跨跑次 2 倍级摆动。
- **判据器负控**: R512 `nc_r512.py` = 正控 p3/p4 各 12/12 + 6 变异体全检出 (`SELFTEST=OK`); 首跑 NC_NOT_DETECTED 系我方预期名口径错误 (用例名无 `test_` 前缀) ⇒ 修正后 OK。
- **诚实边界**: R512 降幅不作验收依据 (C5 未过); B 臂为事后增补; 排除 dump 区段 29–58; 未测 p1/p2/p5 与预算曲线; R512 与 R513 窗口**禁相减**。
- **下轮候选 (R514)**: ① token 判据稳健化 (主判据改为「不必要的远端调用数下降」; token 取 n≥5 中位数并预声明噪声源) ② **题面-判据一致性机检器** (逐条用例断言→题面依据句, 本轮缺陷属此类且目前靠人工定位) ③ p1/p2/p5 纳入对照面 + 预算曲线 6/9/12/16 × n≥3 ④ 第二外部参照 (除 codex-cli)。

---

## R514 (2026-09-17) — 夹具自检器具化: 题面-判据一致性**机检器** + 判据主口径切换 (轮志: `docs/plans/v0.98.0-r514-fixture-selfcheck-instrument.md`)

- **命名空间**: 本侧取 **R514** —— `/tmp/r514/` 有前序会话遗留的 recon 脚本 (10:19, 非活写者), `eval/rover/r514/` 此前不存在; 起手 `pgrep` 无兄弟执行体 ⇒ 无撞号。
- **候选②(主)**: `eval/rover/r514/statement_contract_check.py` —— 静态 AST 器具, 从**题面**抽选项契约事实、从**用例**抽调用/断言面, 判定「用例依赖了题面没写明的契约」; 判据 D1/D2/D3/D4 + 信息项 I1/I2; rc 0/1/2/3 分层 (2 = 器具缺陷 fail-closed)。
- **核心读数**: p4 题面 v1 ⇒ `predicted binding` **8 条**与 R512 真机 6 跑次**众数失败集合逐字相等** (`binding_eq_observed=true`), 另单列 `masked=1` (`bad_request_exit2` — 只断言错误码 ⇒ 缺陷被错误路径掩盖, **人工定位时看不见**)。
- **负控阶梯 8 臂全绿** (`eval/rover/r514/evidence/nc-r514.json`): PC1 v2 rc=0 / PC2 p3 rc=0 / NC1 v1 检出==锚 / NC2 去掉新增句即复发 / NC3 注入未声明选项 / NC4 删退出码条目 / NC5 加可选括号 ⇒ 判据非恒开火 / NC6 缺字段 rc=2; `frozen_fixtures_unchanged=true`。外部锚**机取**自 R512 run 产物 (来源 + sha256 登记), 禁手抄。
- **候选①**: `check_criteria_r514.py` 主判据切为**不必要的远端调用数下降** (规则式, 且要求 min<1 防「不更差」冒充「更好」); token 降为**中位数 + n≥5**, 否则**弃权单列**; 噪声源预声明 (缺 ⇒ rc=2)。影子自检 **9/9** (含 A/C 互换必须翻转判决)。**归档回放**: R512 旧读数在新口径下 `C2 = ABSTAIN_N_BELOW_MIN (n=4<5)` ⇒ 旧轮 token 判据**由 PASS 降为弃权** (口径变更, 非读数变化)。
- **诚实边界**: ① checker→归档 比对属**器具校准 (事后锚定)**, 不作预测命中宣称; ② D4 在 HTTP 类题族 (p3) 分辨力有限 (用例不逐条断言键面); ③ 候选③④ 未做 (真机臂预算 + 内存闸 2,362MB<2,650MB; 第二外部参照仅探到未验证的 `qwen`); ④ `improvements.md` R404–R407 轮节仍缺 (结转, 未静默丢失)。
- **下轮候选 (R515)**: ① 对照轮**强制前门**: 冻结题集进臂前必须先跑 checker (rc=1 ⇒ 该轮读数标「参考(未可验收)」) ② 候选③ 预算曲线 6/9/12/16 × n≥3 (须先过内存闸/让行) ③ 候选④ 第二外部参照 (`qwen` 接入预注册) ④ `improvements.md` R404–R407 回填 + R403 排序违例修 ⑤ D4 判据在 HTTP 题族的可达面扩展 (先落分布再谈扩面)。

---

## R516 (2026-09-17) — 节点成功必须绑产物证据 + 节点写范围契约 (fail-closed 机检) (轮志: `docs/reports/r516-node-artifact-scope-contract.md` · 计划: `docs/plans/v1.00.0-r516-node-scope-contract.md`)

- **命名空间**: 起手闸 `pgrep -af 'llama-server|dotnet test|dotnet publish|probe'` 空输出; mtime 取证判定兄弟 R515 已闭合 (报告 11:04 收口, `/proc/2588066` CPU 计数 4 s 冻结) ⇒ 轮号取 max+1 = **R516** (`eval/rover/r516/`、`/tmp/r516/` 均不存在)。
- **前态锚 (R515 归档, 冻结)**: `eval/rover/r515/evidence/report-orch-v2-12step.json` 中 `n3` (5 ms) / `n4` (178 ms) 均 **Completed ∧ files=[]** ⇒ 「节点成功」与「真实交付」之间无机械绑定 (R515 v2 只把范围写进提示词 = 软约束)。
- **候选①②(本轮全部候选 + 未闭合遗留同轮解决)**: ① `src/agent/intent/NodeScopeFile.cs` (新) = 范围文件 DSL `nodeId | 路径[,路径]` (尾部 `/` = 目录前缀, `*` = 字面前缀通配, **段边界**判定 ⇒ `out` 不匹配 `out2/x`) + fail-closed 解析 (字段数/空 id/重复声明/空范围/越界路径全拒); ② `TaskOrchestrator` 接管**逐节点快照差**(单一权威源) ⇒ 「节点成功必须绑磁盘证据」(声明了范围却零范围内增改 ⇒ Failed 假绿防护) + 「越界写 ⇒ Failed 且**逐条点名路径**」 + 「**同层**(会并发)写范围重叠 ⇒ 建立 agent **之前** rc=2 拒收 (零 LLM 调用)」; 宿主 `OrchestrateCommand` 侧的同名实现**删除**并新增 `--scope` (校验在 agent 之前)。
- **真机 5 臂 6 判据全绿** (`eval/rover/r516/evidence/verdict.json`, VERDICT PASS): RED (旧 AOT, 同计划) rc=0 Completed 且报告**无 scope 字段** = 前态确无机制 / A5 前态锚 n3,n4 / G1 零产物 ⇒ Failed+`no_artifact` / G2 真干活 ⇒ Completed+`A out/hello.py` (**不误杀**) / G3 越界 ⇒ Failed+`out_of_scope` 点名 `outside/rogue.py` / N 同层重叠 ⇒ rc=2 · 报告未生成 · **adapter 调用 24→24 (零 LLM)**。判定器只读落盘 + 退出码 (无模型裁判)。
- **读数**: 单测 **22/22** (新) · 全量 **1706/1706** rc=0 (R515 基线 1684 ⇒ +22) · AOT rc=0 **IL 警告 0** · 15,592,688 B (R515 15,555,120 B ⇒ +0.24%, sha12 `b31af1d94da1`) · 本窗用 24 次调用 / 54,584 prompt + 1,344 completion (**标「参考 (未可验收)」**)。
- **登记/门禁**: 新登记行 `agent.node-artifact-scope-contract` (L3) ⇒ 登记表 **231 → 232**; `bind_evidence --only … --round R516 --apply` `TOUCHED=1 · SER_ASSERT=OK · WRITE_READBACK=OK · R2E_R2F_EXIT=0`; `decl_sweep drifted=0`; registry 形式自检 `bad=[]`。
- **诚实边界**: 铁律 11 `exec_precondition --round R516` **rc=3 DISCOVER_FAIL** (无对照题集) ⇒ 本轮**不宣称** token 降幅; 快照差在同层并发窗内**不作归属唯一性宣称**; 多层并发未真机跑过; R515 规模臂 (双包 24 用例) 仍未跑 (内存闸 2650 MB)。`instruments_check` 面本轮 29 项判据/2 红 (均 R507 外部对照行的**自身 L2 字段声明缺口**: `input_surface_source=BAD/MISSING`, 其 `cmd` 实测 rc=0 / 负控 pass) ⇒ 记为**前置缺口**, 不计入 R516 回归; HEAD 独立树复跑**未做** (归档树非 git 仓, 该路径废弃)。
- **并发事件**: 兄弟 R515 只落 `docs/reports/r515-*.md` + registry + eval,**未**落 master plan / improvements 轮节 ⇒ 本侧**不代写**对侧轮节 (缺口记 E5)。
- **下轮候选 (R517)**: ① (主线) 规模臂: R515 双包 24 用例 + `--scope` 争 token/调用降幅判据 (先过内存闸) ② 对 R515 `plan-p4-v2.txt` 声明范围后重跑, 机检 n3/n4 是否被新机制判 Failed (本轮只做前态锚) ③ 写范围**运行时互斥** (目录级独占锁, 超出「起臂前拒收」) ④ `improvements.md` R404–R407 回填 (结转) ⑤ D4 判据在 HTTP 题族可达面扩展 (结转)。

---

## R519 (2026-09-17) — 游戏类多文件长任务三臂同窗 (**兄弟会话实施; 本侧事后复核**)

- **归属**: 由同 gateway 的兄弟会话实施并提交 `8342649`; 本侧**未参与**该轮, 只做复核 (同判据器对同一 ws 复跑逐位相同 + 影子机检 RED), 轮节亦由本侧回填。
- **读数**: 单轮臂 **58/58** (×3 窗) · codex 外部真值 **58/58** (打平) · 编排臂 **0/58** (n1 越界写入 fail-closed, n2–n5 未执行)。
- **改判 (R520 定因后)**: 编排臂的 0/58 不是能力读数, 而是**路径框架缺陷** (影子副本 + 回执不回显落点) ⇒ 该轮编排面读数作废, 修复后重跑见 R520。

## R520 (2026-09-17) — 影子路径闸: 编排臂阻断项闭合 (轮志: `eval/rover/r520/REPORT-r520.md`)

- **定因**: 节点把工作区绝对路径裁成**仓根相对串**当工具 `path` ⇒ 端口按「相对根」解析 ⇒ 工作区内**影子副本** `<ws>/eval/rover/…/ws/games/life.py`, 而 `write_file` 回 `ok` + 回显**请求串** ⇒ 节点读到另一份文件并误判为「环境预置的另一版实现」⇒ 范围闸 `out_of_scope` ⇒ 整条编排 fail-closed。
- **交付**: `WorkspaceActionPort` 影子路径闸 ((a) 以根完整路径开头 / (b) 前 k 段 (k≥2) == 根后 k 段; 单段同名不判; 报文给落点+建议改写; 与 P1 同闸可消融) + `BuildNodePrompt` 第 5 条纪律 + `R520ShadowPathTests` (正控/负控/消融臂) + 磁盘级独立机检 `shadow_check_r520.py`。
- **读数**: 节点 **1/5 → 5/5 Completed** · 范围违规 **1 → 0** · 影子文件 **1 → 0** · 58 用例 **0/58 → 9/58** (用例级/异窗) · 单测 **40/40** · 形式校验 **14/14** · 登记表 **237 → 239 行**。
- **诚实边界**: 铁律 11 前置器 `--round r520` rc=3 (无同窗两侧对照) ⇒ **不宣称降幅**; 9/58 的整题全对率仍 0。
- **下轮候选 (R521)**: ① (主线) 同窗三臂 (单轮/编排/codex) 取可比读数 ② 编排臂 9/58 逐用例定因 ③ 契约机检硬前门 ④ R517/R404–R407 轮节回填 ⑤ 回执回显落点 (待 token 数据裁定)。

## R521 (2026-09-17) — 游戏长任务三臂同窗 + 器具两缺陷自查 (轮志: `eval/rover/r521/REPORT-r521.md`)

- **归属**: 本侧独立实施 (无兄弟会话); 单轮 AOT 二进制 `.agentframework` 外 `/tmp/pub_r520/agenthost` (sha256 `a0ac9695…`) 复用, **零产品源码改动** (只改 `eval/` 器具)。
- **窗口**: `w2` = `run-0917-154115`; 题面 `games-longtask-v1` (plan/scope/taskset 与 R519 同源 md5); 硬前门: 契约机检 `clean=True` rc=0 · 起手闸 ×2 PASS (mem ≥2650 MB)。
- **读数**: A 58/58 · C 58/58 · O 31/58 (调用 19/5/30; tok 302,809 / 46,372 / 429,908) ⇒ 质量打平, 效率面本侧 6.53× codex。
- **器具自查 (两条, 同轮修)**: ① 臂 A 缺 `--max-steps` ⇒ 工具面关闭 ⇒ 零产物 (w1 作废); ② 冻结器空树静默跳过 ⇒ 前置器 **rc=0 假绿** ⇒ 修 `makedirs` + 负控 `r521nc` 机检 rc=1。
- **铁律 11**: `exec_precondition --round r521` **rc=1** (预注册 scope 的 w1/* 因作废窗失配 ⇒ w2/agentO 未声明 fail-closed) ⇒ 读数标「参考 (未可验收)」⇒ **本轮未达可验收**。
- **下轮候选 (R522)**: ① 同窗关闸消融臂 (R413 唯一可宣称路径) ② 编排节点 I/O 契约自测 ③ 编排摆动量化 ④ `evidence_scope` 窗口无关模式 ⑤ 回执回显落点。

## R522 (2026-09-17) — 动作环上下文纪律: 同窗单变量消融 (结果: 无增益, 如实收窄) (轮志: `docs/reports/r522-action-loop-context-discipline.md`)

- **靶点来源 (用户逐字质疑)**: 「问题codex也有 新算token你仅是上下文用的没codex好，召回等系统全是问题」⇒ R521 原样 usage 逐调用定因: 19 调用里 20 步全用在自测往返 (14 × `run_command` + 探针落盘/删除), 回读命令 (`cat/grep/head`) 计数 **0** ⇒ 病灶是**验证回路粒度 + 收尾长度**, 非召回。
- **改动 (产品源码)**: `src/agent.modelqueue/ActionLoopDiscipline.cs` —— ① 验证合并 ② 探针不落盘 ③ 收尾从简; 注入点 = 动作环分支 system 尾部; 环境轴 `AGENTFRAMEWORK_ACTION_DISCIPLINE` (缺省开, `off/0/false` 关); AOT `/tmp/pub_r522/agenthost` sha256 `cc611646…` · 15,609,168 B · IL 警告 0 · 单测 1,733/1,733。
- **挂载证明 (实发 prompt)**: M1 处理臂 anchor_all ✓ · M2 对照臂 anchor_none ✓ · M3 system 5,234→5,456 · M4 两组 prompt_sha8 互斥 ✓ ⇒ `MOUNT_OK=True`。
- **读数 (单窗 w1, 每臂 n=1, 同二进制)**: `A0-off` 56/58 · 4 调用 · 新算 9,075 · completion 3,850 / `A1-on` **58/58** · 4 调用 · 新算 10,128 · completion 4,973 / `C-codex` 58/58 · 5 调用 · 新算 **3,775** · 命中率 **90.8%**。
- **裁决 (预注册)**: C2 质量不降 ✅ (58 vs 56) · C3 调用降 ❌ (1.00×) · C4 新算 prompt ❌ (1.116×) · C5 completion ❌ (1.292×) ⇒ **不宣称任何 token/调用增益**; 且 R521 的「19 调用」两臂都不复现 (各 4) ⇒ 主因非纪律。
- **同轮修的器具缺陷 (2 条)**: ① `mount_check_r522.py` M4 写在「长度唯一」分支内 ⇒ 键缺失假红 (改独立计算); ② 前置器 `acceptable_scoped=True` 可绕过 `BLOCKED` 非空 ⇒ rc=0 假绿 (改 rc 前置 `blocked` 空)。
- **诚实边界**: `exec_precondition --round r522` **rc=1** (A0 56/58) ⇒ 全部读数标「参考 (未可验收)」; n=1 单窗禁作能力结论 · 跨窗禁相减; A1 末次调用系**宿主机器闸门修复回路**, 其 completion 增量不可归因于纪律。
- **下轮候选 (R523)**: ① reps≥3 消融判定「19→4」方差归属 ② 缓存友好化 (稳定前缀 + 抑末次短提示) ③ 调用数纳入主判据。

## R523 (2026-09-17) — n=3 同窗对照 (reps≥3): 纪律臂无增益 · 本侧不优于外部真值 · 验收面语义收窄 (轮志: `docs/reports/r523-n3-same-window-contrast.md`)

- **本轮 = R522 候选①+③ 同轮闭合**: 三窗 (w1/w2/w3) × 三臂 (`A0-off` 消融控制 / `A1-on` 交付面 / `C-codex` 外部真值) = 9 跑次; 每窗独立 adapter 端口 (48700/48701/48702) + 独立 run 目录 + 每跑次独立 session; 单变量 = env `AGENTFRAMEWORK_ACTION_DISCIPLINE`; 三臂**同一** AOT 二进制 `cc611646…` (零产品源码改动); 题面 sha256 `516f3208…` 硬门; 起手闸 6/6 PASS; 挂载 `MOUNT_OK=True` 3/3。
- **读数 (调用数 / 新算 prompt / completion / 用例)**: `A1-on` 17/20,004/9,440/**58** · 4/10,068/4,217/**58** · 12/13,548/10,712/**58**; `A0-off` 4/6,655/6,641/58 · 8/11,069/6,572/58 · 12/14,054/6,302/58; `C-codex` 7/3,824/4,125/58 · 9/6,133/5,067/**46** · 5/3,506/2,370/58。
- **裁决 (预注册 C1..C7)**: 中位比 A1/codex = 调用 **1.71** · 新算 prompt **3.54** · 有效 token **3.05** · 名义 **2.29** ⇒ **C3/C4/C5 三否, 不宣称任何降幅**; A1 三窗 58/58 ≥ A0 58/58 ⇒ 质量未降; A1/A0 调用中位比 **1.50** (逐窗 4.25/0.50/1.00, 符号翻转) ⇒ **纪律无增益**, R522「19→4」判定为**窗口方差** (同臂跨同输入窗摆动 4.25 倍)。
- **外部真值不稳定 (机检事实)**: codex 三窗用例 58/**46**/58 ⇒ 单窗交叉对比在该任务族无判别力; 后续轮次必须逐窗读数 + 极差。
- **器具 (验收面语义, R523 预注册 line 66)**: 前置器 rc 改由**验收面** (require ∪ 未声明) 判定 (原为全局 `blocked` ⇒ 非验收面控制臂失败污染整轮验收); 早退分支 (`task_not_in_taskset`/`missing_case_script`) 经 `_early_scope()` 同规则; 7 项正/负控 A/B: 仅 NC2/NC6 (非验收面失败) rc 1→0, NC1/NC3/NC4/NC5/NC7 rc 恒 1 ⇒ **未放水**; 旧轮重跑 rc 不变 (r521=1 · r522=1); **R523 本体 rc 仍 1** (w2/codex 属验收面且失败) ⇒ 修复非为本轮开绿灯。
- **诚实边界**: 铁律 11 rc=1 ⇒ 全部 token/调用读数标「参考 (未可验收)」; 题面族仅 1 题 (games-longtask-v1, 58 隐藏用例); 纪律对数学/程序题族未测; cached 与 new 的价差未计入任何宣称。
- **下轮候选 (R524)**: ① **步数/调用数是唯一杠杆** (A1 中位 12 调用 vs codex 5; 新算 prompt ≈ 调用数 × 上下文) ⇒ 降 token 必先降步数 (一次性计划→批量执行 / 工具面合并), 步数入 KPI 主列 ② n≥5 + codex 失败窗标 `unreliable` 的判据化 ③ 纪律缺省位裁决 (消融已备: 改 `off` 或降级为不占上下文预算的纯提示) ④ 控制臂噪声根治 (轮模板固定写 `evidence_scope.nonrequired`)。

## R528 (2026-09-17) — 主线回归: **产物落位与自验纪律** (R525 w3 的 0/58 定因 = 布局漂移, 非代码缺陷) · 五窗同窗对照 (轮志: `docs/reports/r528-product-placement-and-selfverification.md` · 预注册: `eval/rover/r528/prereg-r528.json`)

- **定因 (机检)**: R525 w3 两侧 agent 臂 0/58 (同窗 codex 58/58) 曾被读成「产物不可运行/能力不足」。逐调用取证: 该臂 8 调用/3 步把 `games/` 包写到 `<工作根>/sols/games_pkg/games/`, 并在该子目录 `python3 -m games life` 自验 rc=0 即自认完成; 而验收形态是**工作根**下 `python3 -m games <id>` (判据器 cwd=树根 + `PYTHONPATH=wd`) ⇒ 包不可导入 ⇒ 0/58。**实跑复验**: 同一棵归档树以漂移目录为 cwd 跑同一隐藏用例脚本 ⇒ **58/58** ⇒ 归因纠正为「产物落位 + 自验位置」。归档普查 30 棵树: `layout_ok` 26 (22 全对 / 4 真部分错) · `layout_drift_code_ok` **1** (即 R525 w3) · `missing_artifacts` 3 (皆控制臂空产出)。
- **单变量**: env `AGENTFRAMEWORK_ACTION_DISCIPLINE`; 唯一产品改动 = `ActionLoopDiscipline.Text` 第 6 条「产物落位与自验」(工作根 + 题面相对路径 + 工作根自验 + rc≠0 不得收尾)。同一 AOT `8f801491…` (15,613,264 B) · 同一题面 sha `516f3208…` · 同判据器。
- **读数 (五窗, 调用/新算/completion/质量)**: A1-on `6/3,819/3,477/58` · `7/4,614/7,383/58` · `19/7,647/6,035/58` · `7/2,258/3,184/58` · `10/4,269/6,834/58` ⇒ **本侧 5/5 窗整题全对**; codex `5/4,083/3,007/58` · `7/4,519/2,981/52` · `11/4,273/3,932/58` · `4/3,734/2,919/58` · `29/17,871/9,015/58`; A0-off (控制臂) `0/58 · 58 · 58 · 58 · 0/58` 双峰。中位比 A1/codex = 调用 **1.00** · 新算 **1.00** · completion **2.01**。
- **机检裁决**: J1 挂载 **5/5 PASS** (A1-on system 9,968 = A0-off 9,434 + 2 + **532** 字符常量块; 块 sha `16efa2f0` 跨窗恒定; 条目 [1..6]; 负控 = 同器具对 R525 修前 dumps 判红, 块 sha `cbc691bb`) · J2 布局漂移 **0/5** · J3 质量 **58/58 ×5** · J4 铁律 11 前置器 **rc=1** · J5 三列记录。
- **诚实边界**: J4 未达成的唯一原因在**验收面的外部真值臂** (`w2/codex` 52/58, R523 已立「codex 失败窗不可靠」) ⇒ 全部成本读数标「参考 (未可验收)」, **不对本轮事后收窄验收面凑 rc=0**; 只改一条纪律文本 ⇒ 不宣称能力提升 (宣称限为「纪律生效面: 挂载 5/5 + 漂移 0/5 + 本侧五窗全对」); 题集族仅 1 题, 跨窗摆动仍是主不确定源, 禁跨轮相减。
- **下轮候选 (R529)**: ① codex 失败窗 `unreliable` **判据化** (须先落盘再跑, 不回写 R528 rc) ② completion 2× 为下一杠杆 (调用/新算已追平; 先做按类分解的天花板算式) ③ 题集扩面 (不同族一题, 保留 58 用例族作可比锚)。


## 轮节回填 (R524 / R525 / R526 / R527 / R529 / R530) —— 2026-09-17 22:35 由 R531 收口时补写

- **补写依据**: `eval/capability/kpi.jsonl` 登记行 `EXP1-Q47` (21:53) 点名「master plan §7 轮节滞后」并自定「面在飞期间禁编辑该面 ⇒ 归主线轮收口」。该委托在本轮兑现: 下列轮节**只摘录各轮 `docs/improvements.md` 条与轮志**, 不含任何新读数、不改判据。
- **R524 (提示词前缀纪律 · 常量前置/易变后置/自指遥测闸)** — 产品改动 `SessionInjectionPlanner.cs`/`ContextAssembler.cs`/`ActionLoop.cs`/`ActionLoopDiscipline.cs`(3→5 条)。读数(三窗 v2, 同二进制 `7c5b59ef…`): M1/M2 ✅×3 · M3 首调用新算 5,372→**343–349** ✅ · M4 ✅ · M5 2/3 窗 · **M6 ❌×3**(`[技能知识参考]` 仍在 user 轮)。质量 A1-on 51/58·58/58·58/58, A0-off 0/58·0/58·46/58(双峰)。**裁决: 结构修成立, v2 不宣称达标**; M6 缺口定因 = 材料块硬编码进 user 轮 (`IndustrialAgentV2.cs:1308`) 绕过白名单 ⇒ 交 R525。轮志 `docs/reports/r524-*`。
- **R525 (提示词分区常量前缀重构 · 外部真值 Fable 5.1 结构对齐 · 铁律 12 入宪)** — `SessionBaseline.Compose` 重写为 **§1..§11 命名常量分区**; 技能材料焊进首轮冻结常量前缀(修 R524 M6)。读数(三窗, AOT `1e25edd6…` 15,617,360 B): 处理臂 system **9,803 字符 / 11 段 / 跨三窗同 sha `6910b5eb`**; M6/M2/M5/M1 ✅×3 · M3 ✅ w2/w3(354/359, w1 冷启 2,582 判否) · M4 ✅ w1/w3。质量 w1/w2 三臂全 58/58; **w3 两侧 agent 臂 0/58**(后由 R528 定因为产物布局漂移, 非能力缺陷)。**裁决: 结构对齐达成且机检通过; 能力增益未证**。轮志 `docs/reports/r525-prompt-partition-prefix.md`。
- **R526 (项目级完全重构: 单类型单文件 / 命名空间归一 / 巨类拆分 / 构建配置集中化)** — 重构判据 = **不改外部可见行为** ∧ 结构不变式机检。读数: `src` 文件 475→**1054**; 含 >1 顶层类型文件 **176→0**; 文件名≠类型名 33→0; 无命名空间 20→0; 测试 **1755/1755 绿**; AOT 15,617,360 B。负控 4 类注入缺陷全红。**铁律 13 入宪**。诚实边界: `agent.core/{userinteraction,subagent}` 20 文件未收敛 / `OnProcessAsync` 未拆 / 行数 +3.4%(文件头成本)。轮志 `docs/reports/r526-project-refactor.md`。
- **R527 (结构收口: R526 五候选同轮闭合)** — ns 收敛(`agent.core` 残留 0)+ `OnProcessAsync` 有界抽取(**1600→1550 行**)+ `ModelQueueRouter`/`ContextAssembler` partial(最大分片 531 行)+ CPM(`Directory.Packages.props` 22 条目接管 41 处引用)+ 前置闸 `tools/refactor/new_file_gate.py`(G1..G7)**接入真实生效钩子**。读数: 测试 1755/1755 · AOT `d70a9741…` 15,609,168 B · **IL 警告 0** · 等价性夹具 **10 臂逐字节全同** · 登记表 +6 行(`R2E_R2F_EXIT=0`)。**J1 收窄**(预注册「全 src=0」过宽: `agent.core=0` ✅, 余 31 处为合法所有者声明) · **J5 未达**(−50 行 vs 目标 ≥300) · `exec_precondition --round R527` **rc=3**(无题集 fail-closed)⇒ 本轮不宣称任何 token/调用降幅。轮志 `docs/reports/r527-structural-closure.md`。
- **R529 (主线扩面: 第二题族 · 外部真值失败窗 `unreliable` 判据化 · completion 按类分解)** — 新族 `toolkit-multimodule-v1`(30 隐藏例/公开 4, 判分两条**非同源**实现)。读数(3 窗 × 3 臂 × 2 族 = **18 格**): 本侧 A1-on **F1 58/58×3 · F2 30/30×3**; codex 同窗 F1 58/58×3、F2 30/30·30/30·**29/30**。判据列 F2 calls `0.667/0.714/4.125` 倍 ⇒ **3 窗极差极大, 本轮不宣称降幅**。**J3 未达成**: `exec_precondition --round r529` **rc=1**(① 基线臂 w2/g1 55/58 ② w2/w3 各臂 `UNDECLARED_SCOPE` = 预注册未把 w2/w3 写进 `evidence_scope.require`, 事后禁补) ⇒ 全部降幅读数标「参考(未可验收)」。轮志 `docs/reports/r529-second-family-and-unreliable-policy.md`。
- **R530 (R529 遗留闭合 · 零新 LLM 调用)** — 逐例定因: 基线臂失败 = **两堆互换的非法字典序着法**(判据由题面明文「字典序最小(先比 i 再比 j)」支撑, `#44` 即题面公开用例); codex 失败例 = 题面明文「uXXXX 码点须 ≥0x20」而输出裸 BEL ⇒ `fixture_defect_suspected=false`。**调用数按类分解(18 格)**: 本侧 **S3 注入轮 = 0**、`calls ≈ 1 + 工具轮数` ⇒ R529「门控引入额外往返」**证伪**, 唯一杠杆 = **降步数/合批**。器具: `eval/rover/r507pre/prereg_scope_gate.py`(起臂前声明面闸) 自检 3/3 + **真数据负控 rc=1 missing=6**(R529 终局 rc 的唯一可控因)。口径冲突**以制品为准**: R529 报告称「预注册加了 w2/w3 窗」, 制品 `prereg-r529.json` 至今 `window_plan.window="w1"` ⇒ 两窗从未预注册。轮志 `docs/reports/r530-r529-leftover-closure.md`。

## R531 (2026-09-17) — 合批轴单变量臂 / 第三族外部对照 (窗口 w1) · 单窗读数 · 定因=能力缺陷(独立 oracle 判夹具无缺陷) (轮志: `docs/reports/r531-merge-axis-third-family.md` · 预注册: `eval/rover/r531/prereg-r531.json`)

- **靶点**: R530 下轮候选①②同轮并推 —— ① 预注册补 `window_plan.windows[]` + 起臂前跑声明面闸(接进 run 脚本首步)② **降步数/合批**(唯一杠杆, 单变量开关, 同窗对照量 calls)。第三族题集与之同窗: F1 `games-longtask-v1`(58 例, 可比锚) + F2 `toolkit-multimodule-v1`(30 例) + F3 新族, 共 4 臂 × 3 题 = 12 跑次/窗。
- **单变量**: env `AGENTFRAMEWORK_ACTION_MERGE`; 唯一产品改动 = `ActionLoopDiscipline.MergeText` **第 7 条(合批)**, 由 `A1-on` 的 6 条块**尾部追加 132 字符**(实测: A1-on system 9,968 → A2-merge **10,100**; 前缀逐字节相同)。
- **w1 读数 (调用 / 总 token / 命中率 / 用例)**: `A0-off` 80 / 1,276,549 / 95.62% / **116/118** · `A1-on` 59 / 1,010,604 / 96.26% / **116/118** · `A2-merge` **52** / 950,671 / 96.58% / **118/118** · `C-codex` 32 调用 / — / — / 118/118。同窗对比: 合批 vs 关 = calls **−35.0%** / 新算 prompt −42.3% / completion +0.46%; 合批 vs 纪律开 = calls **−11.86%** / 新算 prompt −14.51%。逐题 calls: g1 **33 → 34 → 10**、t1 **34 → 17 → 33** ⇒ 单题摆动大(±) 。
- **预注册裁决 (P1–P3)**: P1(合批 vs 纪律开 calls ↓≥15%) **证伪**(实测 −11.86%); P2(30/30/40 阈值)**否**; P3(质量不降) **成立**; **KPI rc=1**。铁律 11 前置器 `exec_precondition --round r531` **rc=1**(阻塞 = `A0-off`/`A1-on` 各 2 例 F1 失败) ⇒ **本轮全部 token/调用降幅标「参考(未可验收)」**。
- **定因 (非同源独立 oracle, R531 新增器具)**: `eval/rover/r531/oracle_wythoff_r531.py` 手写「必败点 DP + 暴力枚举合法着法」对 15 条 wythoff 冻结用例重算期望 ⇒ **与夹具 `expected_stdout` 15/15 完全一致(夹具无缺陷)**; 逐例分类: `A0-off` 13/15(`#43 (21,25)`→`WIN 1 13`、`#57 (25,25)`→`WIN 2 11`, 皆 **`illegal_move`** = 取两堆不等量, 题面只允许单堆取或等量双取) · `A1-on` 13/15(`#55 (1,1)`、`#57 (25,25)` 皆 `LOSE` = **`wrong_lose`**, 漏 `(t,t)` 双取分支) · `A2-merge` 15/15 · codex 15/15 ⇒ **rc=1 属能力缺陷, 非夹具缺陷**(两臂缺陷类别不同, 非同败)。
- **挂载证明 (实发 prompt 取证)**: `eval/rover/r531/mount_check_r531.py` v2 —— 从 adapter FULL dump 直读 system: **M1** A1-on 是 A2-merge 前缀 · **M2** 差值 **逐字节等于**源码 `ActionLoopDiscipline.MergeText`(132 字符, 双侧 sha12 `9be41f32e862`) · **M3** A0-off 无纪律块 · **M4** 两侧共享前缀锚 `MOUNT_OK=True`; 负控**换序必红**(NC1/NC2 皆响)。
- **诚实边界**: ① **只跑了 w1**(声明面 12 格 / 执行面 4 格), 预注册的 w2/w3 由本轮定时链续跑 ⇒ 现读数一律 **provisional(单窗=噪声, R523 已立)**, w2/w3 补齐后按「逐窗 + 极差」重报 ② w1 臂用的 AOT 是 `/tmp/pub_r531/agenthost`(sha `d5848776…`, 21:28), 而现行树产物 `/tmp/pub_r532/agenthost`(`d399142c…`, 同体积 15,613,264 B, **IL 警告 0**)—— 差异源 = 兄弟主线 **R-N1 `af8c15b`(22:13)** 把 `src/agent/contract/*` 落进 `agent` 库(编译图内、`未接线`, 不改变臂行为); 两台产物**同目录重建逐字节相同**(已验: `/tmp/pub_r532` == `/tmp/pub_r532b`)⇒ AOT 输出与输出目录无关, sha 差是**树内容差**, 不是构建噪声。③ 未测: 合批轴在 F2/F3 的成本符号、`#43` 类「非法着法」在其他题族的复现率、A2-merge 的 118/118 是否跨窗稳定。④ codex 侧 token 未计量(只有调用数)。
- **下轮候选 (R532)**: ① 补齐 w2/w3 并按逐窗 + 极差重报 ② 第 8 条纪律候选(题面逐条对齐 + 着法合法性自验)单变量臂 —— 靶点 = 本轮两条 `illegal_move`/`wrong_lose` ③ 合批轴在 F2/F3 的成本符号单列 ④ codex token 计量接进 adapter(现仅调用数) ⑤ `EXP1-Q47` 委托的轮节回填**本轮已兑现**, 建议该侧登记行收口。

- **w2 追加 (22:40, 修正 w1 结论)**: 两窗同窗对照 ⇒ calls 比 merge/on **0.881 (w1) / 1.429 (w2) 符号翻转**, merge/off 0.65 / 3.158, on/off 0.738 / 2.211; 质量亦翻转(合批臂 w1 118/118 最好 → w2 113/118 最差)。**⇒ 「合批轴降调用」未获支持, w1 的 −35.0%/−11.86% 属单窗噪声**(R523「单窗=噪声」再证)。挂载两窗皆 4/4 PASS(A2-merge−A1-on 逐字节 = `MergeText` 132 字符, sha12 `9be41f32e862`) ⇒ 轴真挂上、效果不稳。F1 定因(w2 独立 oracle): `A0-off` **4/15**(11 条同退化输出 `WIN 0 1`) · `A1-on` 15/15 · `A2-merge` 15/15 · `codex` **13/15**(`#43 (21,25)` 出 `WIN 1 13` 非法着法, 该例期望 `WIN 15 15` 即题面公开用例)。本窗 `structure_check` **rc=1** ⇒ 按 run 脚本自带规则不得宣称降幅; `exec_precondition --round r531` 仍 **rc=1**(验收面 5 项)。聚合器 `eval/rover/r531/aggregate_r531.py` 产出 `evidence/kpi-r531-windows.json`(逐窗 + 极差, 窗数<3 标 provisional); w3 在飞。

- **终局裁决 (三窗齐, 23:00)**: merge/on calls **0.881 (w1) / 1.429 (w2) / 0.488 (w3)** (median 0.881, 极差 **2.93×**)、merge/off 0.65/3.158/0.362、on/off 0.738/2.211/0.741 ⇒ **2/3 窗同向、1/3 反向 ⇒ 未证稳定增益**; 三窗质量 A1-on **352/354** > codex 350/354 > A2-merge **349/354** > A0-off 339/354; 挂载 **3/3 窗 PASS**(delta 132 字符 = `MergeText`, sha12 `9be41f32e862` 三窗同)。**前缀机检 w2/w3 rc=1**(w3 `M1_system_constant=false`)⇒ 按 run 脚本自带规则**本轮不得宣称任何降幅**; `exec_precondition --round r531` **rc=1** ⇒ 成本读数「参考(未可验收)」。**R530「唯一下一步=合批降步数」假设未获支持 ⇒ 候选降级**; 跨臂共同缺陷面 = **着法/输出合法性**(`#43 (21,25)` 类非法着法 4 臂共 5 次, 含 codex 在**题面公开用例**上出错) ⇒ R532 第 8 条纪律候选。w3 首跑因起手闸 mem 2,636 MB < 2,650 MB 阻塞 ⇒ 清 build-server 后重跑成窗(门限贴边)。


## R532 (2026-09-17) — **R1 结构化契约管道接线**(用户方向令 · 「结构化 prompt ⇄ 远程 LLM ⇄ 结构化结果 ⇒ 精准语义 ⇒ 管道」) · 单调用计划 → 机械执行 · 同窗迷你对照 (轮志: `docs/reports/r532-r1-contract-wiring.md` · 器具 `eval/rover/r532/`)

- **靶点来源**: 兄弟主线 **R-N1 (`af8c15b`)** 自报未闭合项「宿主尚未调用该模块 ⇒ 有代码行 ≠ 生效(未接线)」+ 用户令(逐字)「利用 r1 对真假信息判别(记得要挂载 role 的额外数据，管道里应该已经接了)来让用户一轮任务总数 tokens 使用量显著下降 30% 以上(主要是不必要的 llm api 请求少了)」。
- **机制 (单一接线点, 可回退)**: `Program.cs` 单条路径内 `env AGENTFRAMEWORK_R1_CONTRACT ∈ {1,on,true}` ⇒ `R1CliEntry` ⇒ `agent.r1.R1Pipeline`(pin 自检 → 1 次结构化调用 → 契约校验 → 语义闸 → 白名单执行 → 台账); 新增 `src/agent/r1/` 12 文件(单类型单文件); rc 域 0/2/3/4/5/6; role 数据只进 user 轮尾块。
- **同窗读数 (mini1, 题面 `t1` sha `9fbfaeb3…`, 同 adapter, 起手闸 2/2 PASS)**: `R1` **1 调用 / 6,731 token / 26-30 用例** vs `A1-on` **19 调用 / 277,529 token / 30-30 用例** ⇒ 调用 **0.053×** · token **0.024×** · 新算 prompt **0.131×**; R1 臂整包四文件由**一次 completion** 产出。
- **挂载证明 (实发 prompt)**: head **3,889 字符 sha `58e2df67afe1923b…` 逐字节 == 台账 pin** + 宿主 R522 尾块 **532 字符 sha `16efa2f069698edd` 与对侧臂同** ⇒ 线上恒定前缀 4,423 字符不变(`wired_constant_prefix_ok=True`); 负控: 同器具对 A1-on 判假。
- **诚实边界**: 铁律 11 `exec_precondition --round r532` **rc=3**(无 codex 侧/题集未注册)⇒ 降幅标「参考(未可验收)」; **单题单窗 n=1** ⇒ 不宣称能力结论; **质量 26/30 < 30/30 ⇒ 判据「质量不降」未成立**; AOT `47fbd7fc…` 15,729,408 B · IL 警告 0 · 测试 1780/1780。
- **同轮发现未闭合产品缺陷**: ① 台账 completion 计数漏(0 vs 中继 3,348) ② R1 调用面仍带 tools_n=5 ③ `expect_stdout` 不符即停机(应降级) ④ R522 纪律尾块对结构化前端无意义。
- **下轮候选 (R533)**: ① 缺陷②③闭合(关工具面 + 期望降级) ② 质量补差(`max_repair` 修复轮 / 自检命令执行器注入) ③ 同窗 n=3 逐窗 + 极差 ④ 建 `snapshots/evidence/windows` ⇒ 前置器 rc 0/1 转可验收 ⑤ role 挂载首测。

## R549 (2026-09-18) — R548 **关账轮**：仓外运行树入仓 + 铁律 11 机检 + `wythoff` 定因 + 前置器泄漏修复 · **产品源码零改动** (轮志: `docs/reports/r549-r548-acceptance.md` · 器具: `eval/rover/r549/`)

- **靶点**: R548 候选①（wythoff 定因）+ 铁律 11。R548 的 58/47/58 与逐调用 usage 原本只在仓外 `/tmp/r548_{c2,d}` ⇒ 前置器不可发现 ⇒ 只能标「参考(未可验收)」；本轮按字节入仓（72 文件，逐文件 sha256），题面 sha256 与 R548 运行树逐字节同、`cases-r521.json` 与 r531/r547 逐字节同。
- **机检**: `exec_precondition --round r549` ⇒ `R548b` **58/47/58** · `R548base` 46/47/52 · **失败 100% 落 `wythoff`** · `SELF_REPORT_AGREES=True` · **rc=1**（声明面笔误 run#1 `DECLARED_ARM_ABSENT` fail-closed、run#2 评分字段逐字节同 ⇒ 声明修正非评分修正）。
- **同尺 KPI（三窗并列）**: 调用 Σ 6 / 7 / 108（R548b / R548base / codex）· prompt Σ 50,331 / 57,878 / 2,030,796（判据① **−97.5% 成立**）· 质量 Σ 163 / 145 / 172（判据② **不成立**，差 9 例全在 wythoff）⇒ **主线判据整体未达成**，降幅一律标**参考(未可验收)**。
- **定因（独立 oracle，含保形重钉）**: 夹具 vs oracle 15/15（**夹具无缺陷**）；`R548b` 15/4/15 · `R548base` 3/4/9；`non_winning_move` 27 · `illegal_move` 9 · `wrong_lose` 2 ⇒ 机制 = 自建必败点表后**未自验落点**；错例含**题面公开用例**，public probe 已命中（rc=8）⇒ 缺口在「自测未过仍交付」。
- **口径复核**: 三种自明口径**无一**复现 R548 报告命中率（且 w1 冷启动 miss 8,105 与 95.6% 直接冲突、两行数值错位重叠）⇒ 该行**不得作验收依据**，重钉 per-call 双口径。
- **器具修复**: `exec_precondition.py` 独立进程组 + 收尾整组 SIGKILL + `group_gone` + `--leak-selfcheck`（现场泄漏 pid 203815/205078 各烧 77% CPU 逾 2h，cwd 指向前置器临时目录）；旧 `rc` 编码保形。
- **诚实边界**: 零远端调用（无新增能力证据）· 快照入仓但运行环境未冻结 · w2 两臂同败(4/15) · codex token 为自报非同口径 · 修复未实施。
- **下轮候选 (R550)**: ① wythoff **落点自验**（58/58 ⇒ 前置器 rc=0 ⇒ 降幅首次可验收）② 命中率口径脚本化重钉 ③ `--leak-selfcheck` 入起手闸 ④ codex token 接 adapter ⑤ 遗留：δ=1 质量损伤、旧路径 n≥5。

## R551 (2026-09-18) — 探针证据回灌的**独立预算**（单变量轴 0→1）三窗两臂同窗对照 + `wythoff#43` 错例文本级定因 (轮志: `docs/reports/r551-probe-repair-budget.md` · 器具: `eval/rover/r551/`)

> 缺口登记: **R550sc 无本轮节**（该轮由上一 tick 兄弟会话收口，其轮志在 `docs/improvements.md` 顶部 + `eval/rover/r550sc/`）；按「本侧不代写对侧轮节」未补写。

- **靶点**: R550sc 候选①/② 与 R549 候选①（`wythoff` 落点自验面）合并 → 落在**已有开关**上（用户 2026-09-18 令「开工，不许新增夹具和额外开发；提质只能翻已有开关/复用既有组件」）：`AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR ∈ {0,1}`（`SELFCHECK=1` 保持不动）。实现源码由上一 tick 兄弟会话写出，本 tick **接管**（先核 diff 再收口），产品源码本 tick 零改动。
- **同窗读数（中继 dump 时间轴归属）**: b1 治疗（轴=1）3/3 有效窗用例 **56/58/43**（中位 56，极差 15）· 调用 Σ **12** · Σprompt **100,423** · 命中 96.1% · `probe_repairs=1/1/1`（机制 3/3 窗触发）；b0 对照（轴=0）**仅 1/3 有效窗**（w8/w9 死于上游契约面 `rc=4`；3/11 dump 不可解析）用例 45、调用 Σ 11、Σprompt 91,737、命中 97.0%、**无 `probe_repairs` 字段**（轴=0 逐位等于旧台账）⇒ 同窗质量 Δ = w7 **56 vs 45 = +11**（n=1）。
- **铁律 11（独立重跑）**: `exec_precondition --round r551` ⇒ **rc=1**（w7 w8 满、w7 b1 56/58、w9 b1 43/58）⇒ **本轮任何 token/调用降幅标「参考（未可验收）」且成本对比 n/a（对照臂不等价工作量）**。
- **定因（器具 `diagnose_wythoff43.py`，非同源 Beatty 判据，快照可复现）**: #43 期望 `WIN 15 15` ⇒ b1 w8 正确 · b1 w7 = `WIN 1 13` **非法着法**（漏 `i!=j` 排除）· b1 w9 = **崩溃交付**（`best=None` 无兜底；自建 `_rook_win` 用三角数顶替 `a==⌊dφ⌋`）· b0 = `WIN 0 14` **打错落点**（漏 `(0,k)` 必败点）⇒ **本轴把失败类别从「打错落点」推向「非法着法/崩溃」；探针看见失败且预算已花，产物仍崩溃交付** ⇒ R549 定因「自测未过仍交付」在加预算后依旧存在 ⇒ 下根轴转向**交付闸/停止条件**。
- **外部真值同错（实证）**: codex 在 R531 w2 对 #43 输出 `WIN 1 13`（`r531/run-0917-222519-w2/C-codex/g1/raw/codex-001.jsonl:21`）与 b1 w7 逐字节相同 ⇒ 该错法属**模型族共有**，非本项目特有；裁判面应把「双方共错」单列（登记事实，未改判据）。
- **成本方向**: 同窗多 2 次调用 / +16.7k prompt tok 换 +11 例 ⇒ **本轴是质量器械，不是成本器械**；主线 `token ↓≥30%` 成立依据仍只在 R1-vs-codex 跨侧（R549 prompt −97.5% / 调用 −94.4%）。
- **器具**: `run_r551.sh`（起手闸 A1/A2/B + 单变量导出 + 摘要含 `probe_repairs`）· `prereg-r551.json`（**先写后跑**）· `ingest_r551.py`（基线）· `hitrate_dual.py`（适配版唯一差异 = 窗号参数化，**同输入差分**证零行为变更）· `diagnose_wythoff43.py` + `diag-wythoff43.json`（本轮新增定因器具，只读快照）· `snapshots/w{7,8,9}/…`（VOID 窗不入仓）。
- **基线**: 全量测试 **1882/1882 PASS** · 单测 `R1ProbeRepairBudgetTests` 6/6 · AOT `/tmp/pub_r551/agenthost` **15,812,016 B**、IL 警告 **0**（IL2*/IL3* 计数 0）。
- **诚实边界**: 对照臂 n=1 且死于上游契约面 ⇒ Δ 不可归因本轴；治疗臂极差 15 ⇒ 单窗按 R523 判噪声；探针证据**消息文本**未截取 ⇒「措辞不可操作」vs「模型不采信」未分离；`MAX_PROBE_REPAIR>1` 未测；codex 非同窗。附注：`readings-r550.json` 命中率行在当前 `/tmp` 树不可复现（源树 mtime 已变）⇒ R550 命中率行同样禁作验收依据。
- **下轮候选 (R552)**: ①**交付闸轴**（`probe_failed>0` ⇒ 拒交付/降级；只翻既有开关）②剂量面 {0,1,2} 同窗 n≥3 ③上游退化率 fail-closed 入起手闸（只改器具）④对照臂补窗（先写后跑）⑤遗留：δ=1 成对检验 / 旧路径列 n≥5 / codex token 接 adapter。

## R552 (2026-09-18) — 探针修复预算的**剂量面**（既有开关 0/1/2）三臂同窗对照 · **剂量在本窗族内未被行使** · 元凶定因 = **上游契约面退化（rc=4 占 62%）** (轮志: `docs/reports/r552-dose-surface.md` · 器具: `eval/rover/r552/`)

- **单变量**: `AGENTFRAMEWORK_R1_MAX_PROBE_REPAIR ∈ {unset(=0),1,2}`，**同一 AOT 二进制 sha `e2fdab87…`**（无源码改动 ⇒ 单变量由构造保证；本轮**零产品改动、零重发布**）。先写后跑四级：`prereg-r552.json`(v1, 起臂前机检) → `-v2` → `-sup1` → `-sup2`。
- **读数（24 窗：b0 6 / b1 9 / b2 9）**: 有产物窗质量 b0 `0×4,55,58` · b1 `0×3,45,47,47,53,56,58` · b2 `0,45,53,54,58×4`；**预注册有效窗 0 / 2 / 2（均 <3 ⇒ J2 不可判）**；调用 Σ 13 / 27 / 23；新算 prompt Σ 59,705 / 153,355 / 119,885；completion Σ 29,993 / 62,855 / 51,412。
- **J1 剂量行使面**: b2 的 **5 个探针窗零失败**（`probe_failed=0/8`）、全窗最大 `probe_repairs=1`（从未到 2）⇒ **「1 vs 2」无机会产生差别** ⇒ b2 的全对窗（5）**不可归因剂量**。
- **铁律 11**: `exec_precondition --round r552 --scope prereg-r552-sup1.json` ⇒ **rc=1**；前置器自跑 b1 六窗 53/47/45/**58**/47/56（仅 1 窗全对）、b2 五窗全对；判红两层 = ①验收面 b1 无一窗全对（错题集中 `wythoff#43-public` 与 `#45–#56`）②`SCOPE_SOURCE=…sup1.json PREREG=False ⇒ VERDICT_POSTHOC_ONLY`。⇒ 本轮读数全部标**参考（未可验收）**。
- **元凶定因**: 24 窗 **15 窗（62%）`rc=4 stage=contract`**，逐窗上游闸（新增：dump mtime 时间片内 `response.text` 可解析率 `>0.25 ⇒ void_upstream`，自检 `has_teeth=True`）触发同 15 窗；文本级形态 = 模型**多出一个 JSON 对象** / **复读指令**（`finish_reason=stop` ⇒ **非截断**）⇒ 与 R551 w8/w9 同源、本轮更重。**该判据过宽**（实测 `rc=4` 窗仍产出 45/55/56/58÷58；退化率 0.333 窗产出 58/58）⇒ 修正（仅「无产物」判 VOID）留 R553 预注册。
- **器具自捕三处（本侧）**: ① v1 漏复制 `cases-r521.json` ⇒ 判分 `FileNotFoundError` ⇒ 每窗 `0/0`（v1 三条运行改名保留、无能力读数）② 裁决件写死 `summary.json` 被后一批**覆盖**（原始件无损；已参数化）③ 真 VOID 窗空目录让前置器判「快照缺失」假红（首跑 20 项 blocked 中 12 项此因，已修）。
- **候选①机检**: 全仓 **87 个 env 开关**中交付/拒绝/降级语义命中 **0**（`gate-switch-inventory.txt`）⇒ 「只翻既有开关」**不可满足**，若做须新增一处分支（只改回执面 rc/stage，不改质量/成本格）。
- **诚实边界**: 无 codex 外部真值列；三臂均未达 n≥3；b0 仅 6 窗（w39-41 起手闸内存阈未过**未跑**）；命中率只作 hygiene（跨轮禁相减，恒等式违反 0 笔）。
- **下轮候选 (R553)**: ①**上游契约面退化轴**（最高优先：起手闸侧健康预检 **或** 产品侧有界契约面重试；须先写「改哪一格读数」）②VOID 规则改写（仅「无产物」判 VOID）③交付闸轴（须新增分支）④剂量面复测（要求探针失败窗 ≥2 才算行使）⑤遗留：δ=1 成对检验 / 旧路径列 n≥5 / codex token 接 adapter。

## R555 (2026-09-18) — 契约语义加厚 v2（规格保真 + 逐条自验）· 单变量同轮两臂 ×3 窗 · **铁律 11 rc=1（未达成）**

- **单变量**: 契约版本（`tools/r1gen/contract.py` +172 字节）· 对照臂 v1 复用 R553 AOT `e2fdab87…` / 治疗臂 v2 重发布 `d2813218…` · 题面 + 用例两侧逐字节同 · 运行树 `/tmp/r555`
- **读数（逐窗 cases/58）**: A0 = 47, 0(rc=4), 58（有效 2 窗, 极差 11）· A1 = 58, 58, 51(rc=4)（有效 2 窗, 极差 0）· codex 真值（R554 同窗异轮）= 58, 56, 56
- **挂载证明**: prefix_chars 15119 → 15291, Δ = +172 == 加厚字节数 ⇒ 契约 v2 进实发 prompt
- **铁律 11**: `exec_precondition --round r555 --scope scope-r555.json` ⇒ rc=1（验收面 A1 w82 = 51/58, failed=wythoff#44-public,45,46,48,49,50,56）
- **定因（R553 快照只读）**: wythoff 三类产物缺陷（未列走法 / 字典序未落实 / 必败点判定错）；公开用例 8/8 全过仍可 54/58；探针修复轴"被行使但无效"
- **诚实边界**: 每臂有效窗 n=2（各 1 窗 rc=4 契约面退化）；异轮读数禁相减；本轮不写 kpi.jsonl
- **下轮候选 (R556)**: ①上游契约面退化轴（先量分布再谈修）②契约加厚 v3（产物侧自检条款：候选 ⊆ 规格动作集 / tie-break 逐字对齐 / 必败点双路径核验）③codex 同窗**同轮**复跑 ④铁律 11 门限口径待裁

## R557 (2026-09-18) — 复跑分布轮 (同冻结对 ×4 新窗: A0=R555 件 / A1=R556 件, 无单变量) + 起手闸自排除闭合 · **铁律 11 rc=1 (未达成: C2 质量新窗中位 54.5 < 真值 58 − 2)**
- **主旨**: 承 R556 §5 候选② (契约面死亡率加样本 ≥8 窗)。两枚二进制 sha 与 R556 逐位同 ⇒ 本轮禁作臂间效应宣称; 新窗与 R556 旧窗**并列不相减**。
- **读数 (新 4 窗)**: 质量 A1 53/58/56/**45** (中位 54.5, 极差 13) / codex 58/58/56/58 (中位 58, 极差 2) / A0 58/53/**0**/58; 成本 A1 新算 prompt 1549 vs codex 47213 (**−96.7%**), 调用 6 vs 90 (**−93.3%**)。
- **分布 (8 窗)**: 契约面死亡 A1 **0/8** vs A0 **2/8** (w92/w96); 质量 A1 中位 57 / 极差 13 ⇒ **极差为唯一剩余缺口, 失分 100% 集中 `wythoff`**。
- **定因**: 离线复判器具正控 (R556 四窗逐位复现) ⇒ 必败点判据 `k` 取错 (`int(phi×小堆)` vs `两堆之差`); 修复轮同一缺陷换算法仍错; w96 两侧同败已按纪律排除夹具 (同两例在其它窗两侧各自通过)。
- **器具**: 起手闸自身工具自排除落地 (血统绑定的 T1–T6 判据), 成对控制 NC `GATE_BLOCKED 2515` / PC `PASS 2769` (收口 164+162MB) ⇒ R556 §4 待办闭合; 另自捕 `run_r55x.sh` 前置器 `--json` 参数错 (argparse rc=2 与断言同码)。
- **下轮候选 (R558)**: ① wythoff 生成/修复面 (先量「公开用例自验被行使」的分布, 禁预言式修) ② 极差收敛 (13→≤5) ③ 调用账显式记账 ④ 铁律 11 验收面口径待裁。

## R558 (2026-09-18) — 执行面回灌修复预算的**剂量面** (既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 0/1/2, 同一枚二进制 ⇒ 单变量) · 同窗 4 臂 × 6 新窗 · **铁律 11 rc=1 (未可验收; C2 未过)**
- **主旨·承上**: 承 R557 候选① —— 「公开用例自验被行使」先量分布再判 (`dist_probe_r558.py`, 离线只读, 零远端调用): pre 16 窗 / post 34 窗两分母并列, probe_ran 88%→91%, probe 看见失败 43%→58%, exec 预算行使 56%→59%, **行使后仍非全对 67%→65%**, **probe 失败却全对 0% (0/18)**。
- **KPI·同窗 6 窗 (w98–w103)**: 质量逐窗 codex 58×6 (中位 58/极差 0) · B0 53/50/47/58/49/47 (49.5/11) · B1 58/43/50/0/58/45 (47.5/58) · B2 58/43/58/51/46/49 (50.0/15); 调用 53/6/13/20, 新算 prompt 35043/906/3181/5959, completion 26221/14426/31049/42091, 命中 v_all 0.9435/0.9819/0.9710/0.9650。
- **判据裁定**: C1 成本 **过** (B1 逐窗 ≤22.2% 新算 / ≤60% 调用); C2 质量 **未过**; C3 剂量 **过** (B2 6/6 窗 `exec_repairs=2`); C4 铁律 11 **rc=1**; C5 调用账 2/18 臂有差 (−1) ⇒ 裁决 **未达标**, 成本读数标「参考(未可验收)」。
- **剂量结论**: 剂量 1→2 **无质量增益**且剂量确被行使 ⇒ 「行使 ≠ 有效」; 建议冻结为 0 (最省档) + 写死重开条件。
- **器具**: `dist_probe_r558.py` 输出路径写死 ⇒ pre-arm 读数被 post 重跑静默覆盖 (已 `--out` 参数化 + 确定性重算恢复 + 落 provenance); `transcript` 缺 `max_exec_repair` 字段待收口。
- **轮志**: `docs/reports/r558-dose-exec-repair-budget.md` · 器具 `eval/rover/r558/`。
- **下轮候选 (R559)**: ① 修复预算轴裁定 ② wythoff 生成面靶点 (先量分布) ③ 极差收敛 ≤5 ④ 铁律 11 验收面口径待裁 (对照组臂是否进 require) ⑤ 调用账收口。

## R559 (2026-09-18) — 执行面回灌修复预算轴的**上限档 (3)** 补扫 (既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 0 vs 3, 同一枚二进制 ⇒ 单变量) · 同窗 3 臂 × 3 新窗 · **质量判据首次被单臂达成 (中位 56 / 极差 2); 铁律 11 rc=1 ⇒ 未可验收**
- **主旨·承上**: 承 R558 候选①(2)——R558 只扫 0/1/2 即建议「冻结为 0」, 其「0..3 全扫」前提未成立; 本轮只补**唯一未测档 3** (合法域上限)。
- **KPI·同窗 3 窗 (w104–w106)**: 质量 codex 58/58/58 (中位 58 / 极差 0) · B0 0/45/46 (45/46) · B3 **56/58/56 (56/2)**; 调用 17/3/9, 新算 prompt 11853/453/2933, completion 8634/6191/19699, 命中 v_all 0.8979–0.9286 / 0.9819 恒 / 0.9597–0.9623。
- **判据裁定**: C1 成本 **过** (B0 逐窗 ≤4.5% 新算 / ≤25% 调用; B3 同尺 14.7/25.3/**38.0**% ⇒ w106 超 30% 点名); C2 质量 **过 (B3 单臂)**; C3 剂量 **过** (`max_exec_repair=3` 9/9 臂窗在位, w106 `exec_repairs=3` 用尽); C4 铁律 11 **rc=1** (blocked 5: B0×3 + B3 w104/w106; 全对臂窗 1 = w105/B3; codex 3/3 全绿); C5 调用账 **0 差额 (9/9)** ⇒ 裁决 **未达标**, 成本读数标「参考(未可验收)」。
- **机制读数**: 剂量 3 是首个把管道走到 `stage=done` 的档位 (2/3 窗完成整份计划), R558 的 0/1/2 全停在 `expect_stdout(_exhausted)` ⇒ **R558「冻结为 0」的外推被证伪**, 该裁定改列 R560 复跑。
- **定因 (非同源 oracle)**: wythoff 15 例 per-arm C1 15/15×3 · B0 0/2/3 · B3 13/15/13 —— `fixture_agrees_with_oracle=true` ×3 窗 ⇒ 残余 4 例为**合规面** (`illegal_move` 2 含公开用例 #43 / `legal_but_not_canonical` 1 / `wrong_lose` 1), B0 面为 `malformed` 15 (整窗回显输入) + `non_winning_move` 19 + `wrong_lose` 6。
- **声明纠错 (本轮自捕)**: R558 候选⑤「`transcript` 缺 `max_exec_repair` (全 18 臂 None)」经 18/18 机检**为假** (字段全在位且与臂 env 一致) ⇒ 真因是**聚合件**未带该字段; 本轮 ingest 已加进取数表 ⇒ 剂量归属自证。
- **分布 (只读 R558 冻结件)**: 族级失败 wythoff 138 / nim 15 / sub 14 / life 14; **计划未完成 16/18 臂**; codex 6 窗 0 失败。
- **轮志**: `docs/reports/r559-dose3-first-quality-pass.md` · 器具 `eval/rover/r559/` (prereg/run/ingest/kpi/dist, 派生件按 `assert 命中==1` + 写回逐字节校验生成)。
- **下轮候选 (R560)**: ① 剂量 3 扩窗复跑 (n=3→6, 同窗含 B0 + codex) ② 铁律 11 验收面口径**待用户裁定** (require 是否含对照臂) ③ wythoff 残余 4 例稳定性 (契约加厚 v3 属新增开发, 须放行) ④ B0/`rc=8 public_probe_unmet` 交付闸 ⑤ 调用账再复验一轮。


## R560 (2026-09-18) — 执行面回灌修复预算轴**上限档 (3) 扩窗复跑** (n=3→6, 既有开关 `AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 0 vs 3, 同一枚二进制 ⇒ 单变量) · 同窗 3 臂 × 6 新窗 · **R559 的质量单臂达成被证伪; 铁律 11 rc=1 ⇒ 未可验收**
- **主旨·承上**: 承 R559 候选① —— R559 以 n=3 判「剂量 3 质量中位 56 / 极差 2 = C2 首次达成」, 单窗摆动不可排除 ⇒ 本轮只**加窗**(w107–w112), 零产品改动 / 零新增夹具 / 零新开关。
- **KPI·同窗 6 窗**: 质量 codex 56/47/58/58/58/52 (**中位 57.0 / 极差 11**) · B0 56/58/45/45/55/53 (54.0/13) · B3 50/47/58/43/58/55 (52.5/15); 调用 37/6/25, 新算 prompt 22303/906/8874, completion 18837/14576/51912, 命中率 v_all 0.8943–0.9537 / 0.9819 恒 / 0.9443–0.9701 (口径 = 中继 dump 时间轴; v_incr 与归属交叉校验 18/18 通过)。
- **判据裁定**: C1 成本 **过 (B0 新算 4.06%)** / B3 逐窗 31.9–53.7% **6/6 窗超 30% 点名**; C2 质量 **未过** (B0 中位 54.0 < 真值−2=55; B3 52.5; 三臂极差 11/13/15 全 >5, 真值自身极差即 11); C3 剂量 **过** (B3 `exec_repairs=3` **6/6 窗**); C4 铁律 11 **rc=1** (blocked 12/18, 全为本侧臂); C5 调用账 **0 差额 (18/18)** ⇒ 裁决 **未达标**, 成本读数标「参考(未可验收)」。
- **机制读数**: 剂量上限档被**稳定行使**但管道 `stage=done` 仅 **1/6** 窗 (R559 为 2/3) ⇒ 再次「行使 ≠ 有效」; B0 w111 出现 `rc=8 self_test_unmet` (自测未过仍交付) 新形态实例。
- **定因 (非同源 oracle, 6 窗)**: `fixture_agrees_with_oracle=true` **6/6** 窗 ⇒ 残余为能力面; 但 wythoff **15/15 例在 6 窗里每例至少出现一次**, B3 逐窗 15/15→0/15 摆动, 类目亦变 (本轮 B3 = `non_winning_move` 36 + `wrong_lose` 1, 无 R559 记的 `illegal_move`) ⇒ **R559「残余 4 例稳定」与类目归类均被证伪**, 不得沿用。
- **真值不稳**: codex 在 w108 (47/58) / w112 (52/58) 自身崩 ⇒ 「与同窗真值比」时真值也会崩, 崩窗按 unreliable 登记, 不筛窗不改判据。
- **器具自捕**: 命中率读数器首版按请求文本沙箱路径归属失效 (42/68 未归属) ⇒ **rc=2 器具缺陷 (fail-closed, 未计入被测)**, 定因 = 本侧中继 dump 不存请求正文; 改为「臂=dump 请求形状 (`input_items` vs `prompt_sha8`) + 窗=落盘时间轴」+ 两条独立交叉校验后 68/68 归属、18/18 通过。
- **窗口体检**: 调用 68, 空正文∧无 tool_calls **0**, unreported **0**, VOID 窗 **0**, 18/18 臂窗有产物。
- **轮志**: `docs/reports/r560-dose3-extended-n6.md` · 器具 `eval/rover/r560/` (prereg/run/ingest/kpi/hitrate/oracle, 预注册落盘早于起臂)。
- **下轮候选 (R561)**: ① 执行面预算轴收口裁定 (6/6 行使无增益 ∧ B3 成本 6/6 窗超门槛 ⇒ 建议冻结 0 + 写死重开条件) ② 判据口径修订 (逐窗并列 + 真值崩窗标 unreliable) ③ wythoff 族先量「逐窗通过数 + 类目」分布 (禁预言式修) ④ 铁律 11 验收面口径**待用户裁定** ⑤ 交付闸/停止条件 (rc=8/rc=5 仍交付; 需新增开发, 待放行)。

## R561 (2026-09-18) — **判据口径修订 + 剂量轴收口** (离线判定轮: 零远端调用 / 零产品源码改动 / 零新增夹具与开关 / **零新臂**) · 质量判据 v2 (逐窗并列 + 真值崩窗 `unreliable` + VOID 臂窗单列) · **封存前提被自身机检证伪 ⇒ 不封存为「已证无增益」** · 铁律 11 rc=1 ⇒ 全部降幅读数标「参考(未可验收)」
- **主旨·承上**: 承 R560 候选 ①②③④。旧质量判据 (臂中位 ≥ 真值中位−2 **∧ 极差 ≤5**) 在**真值自身崩窗** (w108 47/58 · w112 52/58, 真值极差 11) 上**结构性不可达** = 判据缺陷 (非被测缺陷) ⇒ 本轮只做**判据/测量面**修订 + 收口, 不产新臂、不动产品源码 (用户 2026-09-18 令「不许新增夹具和额外开发」)。
- **数据源**: R559 (w104–w106) + R560 (w107–w112) 的冻结快照 27 个臂窗, 用**同一件**判分器 (`sha a67215a7…`) 对**副本**离线重判; 复算一致性 (负控位) = 27/27 臂窗 `cases_pass` 与已落盘 `report.json` **逐窗相等** (errors 0 / xref 不一致 0)。
- **判据 v2**: 红绿只由**真值可靠窗**上的逐窗配对决定 (n≥3 ∧ 无窗 ≤ −3 ∧ 配对中位 ≥ −2); 真值崩窗三态分类 `unreliable <=> truth_cases <= median(9窗)−3 (=55)` ⇒ w108/w112 排除并单列; VOID 臂窗 (R559 w104/B0 `rc=8 public_probe_unmet`) 单列排除; 极差/中位降为信息项; 上线前**影子自检 6 夹具** (rc 0/1/2/3 各分支) `has_teeth=true` 才允许出读数。
- **判据裁定**: 主判窗 R560 6 窗 (可靠 4) ⇒ **R560B0 未过** (配对 med −8.0, 点名 w109/w110/w111) · **R560B3 未过** (med −3.0, 点名 w107/w110); 次判窗 R559 3 窗 ⇒ **R559B3 过** (med −2.0, 无点名) / R559B0 未过 — **v2 在旧判据可用的窗集上给出与旧判据相同的结论** ⇒ 修订未放宽。
- **族分布 (9 窗口径)**: **wythoff 是唯一系统性失分族** (R560B0 59/90 · R560B3 53/90; life/nim 满, sub 84/84); 逐例稳定性 = R560B0 wythoff 15 例中 **13 摆动** / R560B3 **15 例全摆动** ⇒ 「残余固定几例」被彻底否证 (机制化落盘, 供靶点选择)。
- **收口裁定 (前提机检)**: 预注册 3 条封存前提 ⇒ ① 行使 6/6 ✓ ② `median(B0) ≥ median(B3)` **两轮同时成立 = 否** (R559 45 vs 56 / R560 54.0 vs 52.5) ③ B3 成本 6/6 窗超 30% ✓ ⇒ 按 `on_fail` 条款**不得封存为「已证无增益」**; 实际裁定自降一档 = **停用该实验轴** (不再产新臂) + **产品默认不改** (`R1Options` 默认 1 保持, 无「剂量 0 等价」的可验收证据) + 写死重开条件 (换题型族 ∧ 新窗 n≥6 ∧ 先出该族分布 ∧ 铁律 11 可 rc=0 的口径)。
- **铁律 11 口径 (候选④, 据宪法原文判定)**: 铁律 11 原文为「**两侧**产出物必须可实际执行且正确 ∧ **任一侧**不可执行或有错题 ⇒ 未可验收」⇒ `require` 含对照臂是**原文口径** ⇒ 不留待裁, 本轮据文落档 (0 有效澄清 / 0 无效提问)。实测重跑 `exec_precondition --round r560` ⇒ **rc=1** (blocked 含真值臂 w107/w108/w112 ⇒ 真值自身也崩)。
- **器具自捕 (三处, 全部 fail-closed 挡住)**: ① 影子自检**首跑即判红** —— 首版 `decide()` 从判定结果内部读自检结论 (`r["selftest"]`) ⇒ 夹具回放 6/6 全 rc=2, 真实读数完全没出 (修法 = 自检结论**显式入参**, 断言不放宽) ② 臂作用域跨轮 ⇒ R559 臂在主判窗内不存在被记成「质量未过」(伪红) ③ VOID 臂窗以 −58 混入配对 ⇒ 单列排除。
- **轮志**: `docs/reports/r561-judge-v2-and-dose-axis-closure.md` · 器具 `eval/rover/r561/` (prereg / matrix / verdict / readings / kpi-table, 预注册落盘早于任何复算)。
- **下轮候选 (R562)**: ① wythoff 族靶点 (已出 9 窗分布 ⇒ 下一步是**按族定因**, 若需动契约/产品分支须先获放行) ② 交付闸/停止条件 (rc=8/rc=5 仍交付; 需新增产品分支, 待放行) ③ 判据 v2 收口到台账 (把 v2 写进 `docs/external-reference-harness.md` 作为正式口径, v1 声明作废) ④ 起手闸/共享机测量口径与判据 v2 的联合回归。

## R562 (2026-09-18) — **器具收口轮**: 判据 v2 入册 + 起手闸/判据 v2/铁律 11 前置器**同轮联合回归** + wythoff 族**只读定因** (零新臂 / 零产品源码改动 / 零远端 / 零新增夹具与开关)
- **主旨·承上**: 承 R561 候选 ③④ 与 ①（只读面）。用户令「开工, 不许新增夹具和额外开发了」⇒ 本轮只做**收口与复用**: 把已在 R561 立起的质量判据 v2 写进权威载体, 把三件既有器具同轮复跑证明彼此一致, 用既有冻结件对唯一系统性失分族做定因。
- **修改点**: ① 判据 v2 入册 `docs/external-reference-harness.md` §12（v1 声明作废 + **作废登记**指明仍带 v1 行的历史轮志只作历史读数）＋ §12.1 起手闸/共享机口径 ＋ §12.2 wythoff 定因; ② `eval/rover/r562/{wythoff_cause_r562.py,gate_regression_r562.py,collect_r562.py}`; ③ 台账行 `eval/capability/kpi.jsonl`（键集与同族既有行逐字相同, 同轮原地更新 ⇒ 幂等）+ 缺陷态行留档 `superseded-kpi-line-r562.json`; ④ 本手册 R562 节 + `docs/reports/r562-*.md`; ⑤ 主线状态块「最近一轮」字段刷新（闭合 EXP1-Q46 登记的待办, R509 行转历史快照）。
- **KPI·联合回归 (全部为已落盘件机检)**: A 判据 v2 复跑 vs 已提交 `verdict-r561.json` **判决面 6 字段逐字段相同** ∧ 影子自检 **6/6**; B 逐例矩阵 vs r559/r560 `report.json` **27/27** 臂窗相等; C 定因器失败例集合 vs 铁律 11 前置器 `blocked` 串 **27/27** 臂窗逐条相同; D 起手闸成对控制 **rc=0**（`0 PASS / 2 GATE_BLOCKED / 0 PASS / 2 GATE_BLOCKED / 2 GATE_BLOCKED`, `expectations_violated=[]`）; E 独立 oracle 复现 wythoff **15/15** 期望值（判据器 15/15 正控 + 59 变异 0 误放行）; 形式校验 `VerificationForm|SkillGeneralization|DevPlanDocRef` **14/14**（Failed 0 / Skipped 0）。
- **wythoff 族只读定因 (405 例次 = 9 窗 × 3 臂 × 15 例, 冻结快照副本)**: 失效份额 `MOVE_NOT_COLD 67 / LOSE_FOR_WIN 34 / WIN_FOR_LOSE 19 / MOVE_ILLEGAL 6 / LOSE_LABEL_MISMATCH 4 / MOVE_NOT_LEXMIN 1` ⇒ **主因 = 胜负判对、落点非冷点 (51%)**, 次因 = 冷集判定双向错 (41%); 逐窗通过数 (/15, w104→w112): 真值 `15/15/15/13/4/15/15/15/9`（w108=4 **崩窗**）· R559B0 `0/2/3` · R559B3 `13/15/13` · R560B0 `13/15/2/7/12/10` · R560B3 `7/4/15/0/15/12`; 跨窗摆动: 真值 15/15 例 · R560B0 13/15 · R560B3 15/15 ⇒ 「残余固定几例」**再被否证**; 同例同输入不同输出的例数 15/13/15。
- **判据裁定**: 本轮**零新臂** ⇒ 不宣称任何质量/成本降幅; 铁律 11 `--round r559` **rc=1**(blocked 5) / `--round r560` **rc=1**(blocked 12) ⇒ 一切读数「**参考（未可验收）**」; 质量读数与旧窗**并列不相减**。
- **本轮自捕 (五处, 全部 fail-closed 挡住, 缺陷态读数留档不撤)**: ① 定因器冷点集漏 `(0,0)` 且首版误以语义类替代逐字节主判据; ② 双实现交叉校验的**域/排序**不一致（首跑 `phi_vs_brute_equal=false` ⇒ rc=2）; ③ LOSE 词标不符被并入 `OK`（4 例）; ④ 收官器**命名错位**（族内序 vs 题集全局序 43–57）⇒ 首跑 C=10/27 (rc=2), 机取映射后 27/27; ⑤ 诱饵控制**前提静默落空**（`bash -c 'sleep N' <字面量>` 被 bash exec 替换 ⇒ 字面量消失, `shells_skipped_n=0`）⇒ 改不 exec 替换的复合命令 + `/proc/<pid>/cmdline` 核实前提。
- **诚实边界**: 定因结论仅在 wythoff (15 例) 成立, 禁外推; 族内摆动 > 臂间效应 ⇒ 禁据单窗下能力结论; `MOVE_ILLEGAL` 6 例**全在外部真值臂**（把「双堆不等量移除」当合法招法, 题面明禁）⇒ 真值侧读题不严, 非夹具缺陷（夹具经独立 oracle 复核); 起手闸本轮 PC `mem 2652` 对门槛 `2650`（余量 2 MB）⇒ **擦边 PASS 不算窗口**。
- **轮志**: `docs/reports/r562-harness-closure-and-wythoff-cause.md` · 器具 `eval/rover/r562/` (wythoff_cause / gate_regression / collect / verdict / superseded-kpi-line)。
- **下轮候选 (R563)**: ① wythoff 修复（须动契约/产品分支 ⇒ **待放行**） ② 交付闸/停止条件（rc=8/rc=5 仍交付 ⇒ 新增产品分支 ⇒ **待放行**） ③ 起手闸**擦边 PASS** 的振幅余量条款落地（阈值 + 观测振幅 + 连续 2 次, 本轮已给出 2 MB 余量的反例读数） ④ 判据 v2 在下一轮真机对照中首次作为**预注册判据**引用（本轮只做一致性回归, 未参与新判决）。

## R563 (2026-09-18) — **判据 v2 首次作预注册判据的真机对照轮 + 起手闸振幅余量条款行使** (产品默认档 × 外部真值 codex · 同窗 2 臂 × 6 新窗 w113..w118 · 零产品源码改动 / 零新增夹具 / 零新增开关)
- **主旨·承上**: R562 候选 ③④ **并轮**. 用户令「开工, 不许新增夹具和额外开发了」 ⇒ 本轮只复用: 判据 v2 (R562 入册) 首次进预注册并参与**新判决**; 起手闸条款以**既有闸 `--gate-mb`** 生效 (零新逻辑进闸)。
- **修改点**: ① 判据 v2 首次作预注册判据 (`prereg-r563.json` 只**引用**手册 §12 口径, 不重定义) + 判决器 `adjudicate_r563.py` 只把窗集/臂集喂给 R561 装置 (零逻辑复制, `verdict_r561.py` sha 前后相同) ② `eval/rover/r563/{run_r563.sh (派生自 run_r560.sh, 6 处差异逐条声明), ingest, kpi, matrix, gate_margin, mem_sampler, mem_sample_once, append_ledger}.py` + 规范布局件 (`taskset-r563.json` / `cases/` 冻结件逐字节拷贝) ③ 台账行 + 手册 §12/§12.1.1 + 本手册 R563 节 + 轮志。
- **KPI 读数 (判据 v2 首次行使)**: `rc=1` (未过) —— 真值 **6/6 窗全可靠** (median 58 / range 0 ⇒ **无崩窗**, v2 的 `unreliable` 分支本轮未被行使); 产品默认档逐窗 `[50,58,43,58,58,55]` (median 56.5), 配对中位 **−1.5** (过 ≥−2 门) 但单窗 **w115 −15** 命中 `PAIR_FLOOR` ⇒ 点名 ⇒ `fail_arms=[R563B0]`。tokens 三列: C1 **34 调用 / 22,418 新算 / 18,653 completion** (v_all .9244 / v_incr .952); R563B0 **6 调用 / 906 / 13,379** (v_all .9819 / v_incr n/a 单调用窗)。铁律 11 `--round r563` **rc=1** (blocked 3 臂窗: w113 50/58, w115 43/58, w118 55/58) ⇒ 全部读数「**参考（未可验收）**」。
- **起手闸条款 (候选③) 行使读数**: v1 (常量 200MB = R562 **跨区制**振幅) **首跑拒起臂** (ceiling 2610 < 2850, `rc=2`, **零臂运行**; 读数原样留档 `gate-margin-r563-v1-blocked.json`)。定因二条: ① 常量取自另一区制 ⇒ 本宿主**结构性不可达** (与 R561 v1 判据不可达同族) ② 本侧 .py 写入经 gateway 唤起**共享语言服务器** (RSS 191MB) 把顶棚 2855→2670, 该进程**不在既有闸 blocker 模式内** (沉默占用)。按「闸红先查残留」按 pid 清本侧残留 ⇒ 顶棚 2808 ⇒ v2 条款 `MARGIN = max(60MB, 上一轮运行中实测振幅)` 以既有闸 `--gate-mb 2710` 行使: A1 2793 / A2 2798 **连续 2 次 PASS** + leak-selfcheck rc=0; 运行中 41 样本 `in_min 2734 / swing 64 / window_drift=false` ⇒ **下一轮 MARGIN = 64** (数据先行)。成对控制 **6/6** (2 正控 + 4 负控: 擦边 2652 / 抖动 / 低顶棚 / v1 常量不可达参数化)。
- **本轮自捕 (三处, 全部 fail-closed 挡住)**: ① 条款首版把余量**夹到下限** ⇒ 低顶棚被放行 = **空心条款** (负控 `NC_low_ceiling` 抓到) ② v1 常量**结构性不可达** ③ 铁律 11 前置器的**布局依赖** (轮目录须自带 `taskset-<r>.json` 与 `cases/`) ⇒ 首跑 `rc=3 DISCOVER_FAIL` / `rc=1 missing_case_script`, 补齐规范布局后矩阵 **12/12** xref 一致。
- **诚实边界**: 铁律 11 rc=1 ⇒ 读数一律标「参考（未可验收）」; 单窗 w115(−15) 是分歧主源, n=6 窗且与 w104..w112 **并列不相减**; v2 的崩窗分支与 VOID 分支本轮**均未行使** (零 VOID 臂窗); 条款余量受宿主顶棚限制 (2808 − 2710 = 98MB), 语言服务器沉默占用**仅登记未修**; 前一轮作业收尾 (22:55:44) 重写过 R562 台账行与 `verdict-r562.json` (本侧未做该改写, 归属=前轮 tick)。
- **轮志**: `docs/reports/r563-judge-v2-prereg-and-gate-margin.md` · 器具 `eval/rover/r563/` · 前置器 `eval/rover/r507pre/precondition-r563.json`。
- **下轮候选 (R564)**: ① wythoff 族修复 (须动契约/产品分支 ⇒ **待放行**) ② 交付闸/停止条件 (rc=8/rc=5 仍交付 ⇒ 新增产品分支 ⇒ **待放行**) ③ 条款按本轮实测 swing=64 派生行使 (`REQ=2714`) ④ **w115 单窗 −15 的族级只读定因** (复用 `eval/rover/r562/wythoff_cause_r562.py`; 零产品改动)。

## R564 (2026-09-19) — **器具/只读轮**: 起手闸振幅余量条款**按 R563 实测振幅派生**行使 (REQ=2714) + w115 单窗 −15 的**族级只读定因** (零新臂 / 零产品源码改动 / 零远端 / 零新增夹具与开关)
- **主旨·承上**: 承 R563 候选 ③④ **并轮**; ①② (wythoff 族修复 / 交付闸停止条件) 须**新增产品分支** ⇒ 用户 2026-09-18 令「开工, 不许新增夹具和额外开发了」⇒ **未放行, 未做** (候选台账见轮志)。
- **修改点**: ① `eval/rover/r564/gate_clause_r564.sh` (候选③ driver: 起手前 3 次采样 → 派生 → **既有闸** `--gate-mb` 行使 → 成对控制) ② `eval/rover/r564/wythoff_cause_r564.py` (**driver**; 逻辑源 `r562/wythoff_cause_r562.py` **一字未改**, 只替换窗集常量 `WINDOW_MAP`/`WINDOWS`/`ARMS`, 源 sha256 登记进读数件) ③ `prereg-r564.json`(先写后跑) / `readings-r564.json` / `leak-selfcheck-r564.json` / `precondition-r563-r564.json` ④ 台账行 + 本手册 R564 节 + 轮志。
- **候选③ 读数**: 余量由上轮**落盘件**派生 (`gate-postcheck-r563.json swing_mb=64`) ⇒ `MARGIN=64 / REQ=2714` (rc=0, 成对控制 6/6); 真机正控 **连续 2 次 PASS** (mem 2786/2790, blockers 0); 负控 400MB 占用 ⇒ mem 2392 ⇒ `GATE_BLOCKED`; **判别力成对控制 (承重)** = 同一内存态 (2680~2689) 下 `--gate-mb 2650` 判 **PASS** 而 `--gate-mb 2714` 判 **GATE_BLOCKED** ⇒ 条款**比基础门槛更严** (R562 记录的 2652 擦边 PASS 形态不再算窗口)。收尾按 pid 杀占用进程, mem 回到 2880~2890 ⇒ 无泄漏。
- **候选④ 读数 (只读定因, 复用器具)**: 器具自证 = 正控 15/15 ∧ 59 变异**零**误放行 ∧ 独立 oracle `phi_vs_brute_equal=true` ∧ `fixture_agrees_with_oracle=true` ⇒ 夹具无缺陷。本侧 `R563B0` wythoff 逐窗 `7/15 · 15/15 · 0/15 · 15/15 · 15/15 · 12/15` (真值 `C1` **6 窗全 15/15**) ⇒ 与 R563 判决逐窗失分 `−8 / 0 / −15 / 0 / 0 / −3` **精确对齐** (`58−15+wythoff_n_pass`); 单窗 −15 = **整族塌陷** (非个别例), 构成 `MOVE_NOT_COLD 11 + WIN_FOR_LOSE 4` = 与 R562 同族同形 (胜负判对落点非冷点 / 冷集双向错), **非新缺陷类**; 6 窗合计 `MOVE_NOT_COLD 18 / WIN_FOR_LOSE 5 / MOVE_SHAPE 2 / LOSE_FOR_WIN 1`。摆动: 本侧 **15/15** 例在 6 窗内既过又败, 且同输入产出 **2~3** 个不同输出 ⇒ 「残余固定几例」**再次被否证**。
- **独立两侧交叉校验 (闭合 R562 登记的「族内序 vs 题集全局序」命名错位)**: 复用器具 (族内序 `i`) ↔ 铁律 11 前置器 (全局序 `43+i`) 的失败集合 **3/3 窗逐条相同** (w113 8 例 / w115 15 例 / w118 3 例; 其余 3 窗两侧皆零失败)。
- **铁律 11**: `--round r563` 复跑 ⇒ **rc=1** (blocked 3 臂窗: w113 50/58 · w115 43/58 · w118 55/58, **全部为本侧臂**; 真值臂 6/6 窗 58/58); `--leak-selfcheck` ⇒ `LEAK_SELFCHECK_OK=true` ⇒ R563 读数继续标「**参考（未可验收）**」。
- **本轮自捕 (两处, 均 fail-closed 挡住)**: ① `--leak-selfcheck` 与轮级前置器**共用 `--out`** ⇒ 自检记录**覆盖**轮级落盘件 (且该件内含硬编码 `round: R549` 标签) ⇒ 改名留档 `leak-selfcheck-r564.json` + 轮级独立 `--out` 重跑 (两者并存); ② **负控带位不对**: 400MB 占用只能证「内存低时会拦」, 补 2680~2689 带内**两门槛反判**后才证「条款比基础门槛更严」(与「缺负控的余量条款是空心的」同族)。
- **复跑 (独立命名空间 `eval/rover/r564/replay`, 不覆盖首跑)**: 顶棚由 2803 降至 **2657** ⇒ 派生步**自身 fail-closed rc=2** (slack −57, `ceiling_below_required_margin`) ⇒ 闸未启用 ⇒ **余量条款是顶棚依赖的**: 顶棚 < `2650+MARGIN` 时等待窗口**结构性不可开启**(fail-closed, 不静默放行), 窗口可用率随宿主负载区制变化。复跑 rc=2 **不翻案**首跑读数, 两侧分列禁相减。
- **诚实边界**: **零新臂 ⇒ 不宣称任何质量/成本降幅**; 读数与 R563/R560/R559 窗集**并列不相减**; 定因只在 wythoff (15 例) 成立, **禁外推** (life/nim/sub 本侧 6 窗满); 余量受宿主顶棚限制 (首跑 2803 / 复跑 2657, 窗口非随时可得); 共享语言服务器沉默占用**仅登记未修**。
- **轮志**: `docs/reports/r564-gate-derived-and-w115-cause.md` · 器具 `eval/rover/r564/` · 前置器 `eval/rover/r564/precondition-r563-r564.json`。
- **下轮候选 (R565)**: ① wythoff 族修复 (冷集**落点自验** + 必败点判定; 须动契约/产品分支 ⇒ **待放行**) ② 交付闸/停止条件 (`rc=8`/`rc=5` 仍交付 ⇒ 新增产品分支 ⇒ **待放行**) ③ **下一轮条款派生行使** (MARGIN = 新运行窗口实测振幅; 零产品改动) ④ 判定输入指纹 / 命中率双口径在新窗的复核 (换命名空间, 不与 R563 相减) ⑤ 铁律 11 验收面口径已按原文落档 (R561), 无新增动作。
- **下轮候选 (R566)**: ① 契约加厚 v3 / 产物**落点自验**（wythoff 族唯一直面手段；须动契约/产品分支 ⇒ **待放行**） ② 交付闸/停止条件（`rc=5`/`rc=8` 仍交付 = 静默降级 ⇒ 新增产品分支 ⇒ **待放行**） ③ C4-3 非平凡判据**换臂行使**（点选 ≥2 调用臂）+ 起手闸 `REQ=2720` 行使（零开发） ④ R560∪R566 剂量轴并池只读复核（w107..w112 ∪ w125..w130 = 12 窗 × 3 剂量档，逐例稳定性池化；零新臂） ⑤ 本轮已闭合：R565-② 预算轴单变量（同窗 exec 0 vs 1）、R565-④ 指纹/口径双口径新窗复核（C4-1/2 rc=0，C4-3 未行使）。
- **下轮候选 (R567)**: ① 契约加厚 v3 / 产物**落点自验**（wythoff 族唯一直面手段；须动契约/产品分支 ⇒ **待放行**） ② 交付闸/停止条件（`rc=5`/`rc=8` 仍交付 = 静默降级 ⇒ 新增产品分支 ⇒ **待放行**） ③ 剂量轴**并池只读复核**（R560 ∪ R566 ∪ R567 = 18 窗 × 3 档：0/1/3，逐例稳定性池化；零新臂） ④ 起手闸 `REQ=2753` 行使（零开发） ⑤ 本轮已闭合：R566-③ C4-3 换臂行使（rc=0，`sensitivity_exercised=True`）、R566-④ 剂量轴第二窗集单变量（0 vs 3，两档均不过判据）。
- **R568（只读并池轮：候选③ 剂量轴并池复核 + 候选④ 起手闸 REQ 行使；零新臂/零新窗口/零远端/零产品源码改动）**: 并池合法性 P1 PASS（33 窗 × 58 例 × 3 剂量档，判分器 sha / 题集 sha / 二进制 sha 各唯一；派生纠正：`R565B0` 的 `B0` 是**环境标签**不是剂量 0，产品默认档由源码派生 `R1Options.MaxExecRepair = 1` ⇒ 属剂量 1）。**预注册判决（原样不改阈值）**: P2 逐例稳定 **FAIL** — 根因是**判据标定缺陷**（均匀模型下 dose0 全过例期望 53.68 ⇒ 期望混合例约 4.3，阈值 6 仅在失败率 <1% 可达），同一读数给出更有信息的量：观测全过例 **0/58、z=−26.84 ⇒ 过分散**（失败几乎覆盖每一例 ⇒ **单窗逐例读数不可作读数**）；P3 逐例剂量敏感 PASS（0 例）但 `Δ_min≈29~39pp` ⇒ **不可判面，0 只能记未可判**；P0 非平凡 PASS。**补记面（明示事后性，预注册判决不变）**: 同窗配对（无窗混淆，McNemar 精确）0v3 **+10.46pp**（剔 `w104` 臂级崩溃窗 0/58 后 **+4.31pp, p=0.0013**）、0v1 **+4.89pp**（p=0.0046）；族分列剔除崩溃窗后 = sub +5.10pp / wythoff +11.90pp（剂量 1 的增益**只在 wythoff**）；逐窗回退 ≥3 例 = 0v3 4/15 窗、0v1 1/6 窗 ⇒ **平均增益 ≠ 逐窗不回退，与 R566/R567 的单窗判决不矛盾，禁相减**；同窗配对下对 codex 差距 140→**49 例窗（收窄 65%）**, 仍余 5.6% 未闭合；归属 `same_fail=0`、6 例独败全在 wythoff ⇒ 能力侧。**候选④**: 条款 `REQ=2753`（MARGIN = R567 观测振幅 103）**派生 rc=2 = 当前宿主不可行使**（顶棚 2704 < 2753，可支配余量仅 54MB），但**判别力为真**（同一状态基础门槛 2650 PASS @2685MB / 条款 GATE_BLOCKED @2694MB，rc=0）；缺陷族与 R564「v1 常数 200 ⇒ 2850 不可达」**同一族**（把拍脑袋常数换成数据派生未夹上界）⇒ 下次规则 `MARGIN := min(prev swing, 顶棚 − GATE − 地板)` ⇒ 本宿主 `min(103,54)=54 ⇒ REQ=2704`。**诚实边界**: 零新臂 ⇒ **不宣称任何质量/成本降幅**，并池读数与各轮单窗读数并列不相减；补记面为事后增补；`w104` 崩溃两数并列报；铁律 11 复核 R567 仍 `VERDICT_BLOCKED` ⇒ R567 读数继续标「参考（未可验收）」。**轮志**: `docs/reports/r568-pooled-dose-axis-and-gate-exercise.md` · 器具 `eval/rover/r568/`（预注册机取 `setup_r568.py` sha `93dec94ec1d33921`、并池判据器 `pool_r568.py` sha `0c19b9423737cc0a`、判据器自检 5/5 有牙）· 读数 `pooled-r568.json` · 条款 `gate-margin-r568.json` / `gate-disc-pair-r568.json` / `gate-disc-c-r568.json`。
- **下轮候选 (R569)**: ① 契约加厚 v3 / 产物**落点自验**（wythoff 唯一直接面；须动契约或产品分支 ⇒ **待放行**） ② 交付闸/停止条件（`rc=5`/`rc=8` 仍交付 = 静默降级 ⇒ 新增产品分支 ⇒ **待放行**） ③ **剂量轴新窗集单变量（0 vs 3）**，预注册写入「逐窗回退窗点名」+「臂级崩溃窗（≤5%）排除规则」，检验 **+4.31pp** 是否复现（复用既有夹具/开关，需跑新窗） ④ **w104 型臂级崩溃定因**（剂量 0 臂 0/58 而剂量 3 臂 56/58：执行体崩溃 / 落盘 / 判定哪一层；零开发查既有日志） ⑤ **MARGIN 上界规则落地**（`min(prev swing, ceiling − GATE − floor)`）+ 条款行使（器具改 ⇒ 须重审 + 保形重钉） ⑥ 本轮已闭合：R567-③ 剂量轴并池只读复核、R567-④ 起手闸 REQ 行使。
- **R569（同窗单变量轮：剂量轴第三窗集 0 vs 3 + 拒收窗定因 + 起手闸上界行使；零产品源码改动/零新增夹具/零新增开关）**: 6 新窗 w137..w142 × 3 臂 × 58 例，全臂同枚 AOT 二进制（sha `320d0eb17e709d15`）。**真值面**: codex 6/6 窗 58/58（中位 58 / 极差 0，六窗全 `reliable`）。**质量**: B0(剂量0) 52/58/52/43/58/53（中位 **52.5**/极差 15）、B3(剂量3) 53/46/44/43/55/58（中位 **49.5**/极差 15）；配对面 B3−B0 = `[+1,−12,−8,0,−3,+5]`，**中位 −1.5**、极差 `[−12,+5]` ⇒ **同臂跨窗摆动 15 ≫ 效应 1.5** ⇒ 按并池纪律**剂量档位非承重变量、定案关闭**；R567 窗集的 +4 增益在本窗集**不复现**（跨轮禁相减，只并列）。**代价**: 剂量 3 = **3.5× 调用**(21 vs 6) / **6.8× 新算**(6200 vs 906) / **2.9× completion**(45687 vs 15762) 换中位 −1.5；机制确已启用（`exec_repairs` 逐窗 `[1,3,3,3,3,0]`，B0 全 0）⇒ 不是 `mechanism-not-engaged`，而是「启用后质量更低」。**判决**: 判据 v2 **rc=1 FAIL**（`quality_paired_shortfall:R569B0,R569B3`，中位 −5.5/−8.5）；铁律 11 **rc=1**（9 项 BLOCKED）⇒ 成本读数标「参考（未可验收）」；`self_report_agrees=True` ⇒ 无「自报通过而实测不过」假绿。**指纹**: rc=0（恒等式 21/21 调用 0 违反；call1 prompt sha8 唯一 `b9068f56`；call1≠call2 5/5 互异 ⇒ 确定性≠恒定输出）。**候选④（拒收窗定因，更正 R568 定名）**: w104/R559B0 三层读数 = ①产物**落盘存在**（非崩溃）②冻结判分器**副本**复跑 **0/58** 且失败模式**唯一** `stdout_mismatch` ③产品 transcript `rc=8 · stage=public_probe_unmet · reason=public_examples_failed · public_probe 8/8 失败 · self_test_unmet=1 · correctness_asserted=0 · calls=1 · steps 6/6` ⇒ **「自测闸拒收窗」而非「臂级崩溃窗」**；同类普查：`rc=8` 臂窗 10 个，其中 `public_probe_unmet` 者 = `w104/R559B0` **与本轮 `w140/R569B3`** ⇒ 类稳定且本轮天然复现。**候选⑤（起手闸上界行使）**: 上界规则（R568 派生 `MARGIN := min(prev swing, ceiling − GATE − floor)`）**两分支都被真实行使** —— attempt1 `margin_capped=true / cap −10 < floor 60 / floor_unreachable=true` ⇒ **rc=2 拒跑**（顶棚 2640 被**本会话** LSP ≈250MB 压低，非本闸血统 ⇒ 闸看不见它）；回收后 attempt2 顶棚 2803 ⇒ REQ 2753 放行，postcheck rc=0（振幅 90MB / n=182 / drift=false）。**自捕（器具使用）**: `matrix_r569.py --work` 误传运行根 `/tmp/r569`（该参数会被 `rmtree` 清空，默认 `--work /tmp/r569/pc` 才是 scratch）⇒ 清掉运行根日志面；**结论面不依赖**（全部读数 06:08 前入仓或由冻结快照重算），已用 `closeout_r569.py` 重算 windows/verdict/summary 并做两条独立路径逐窗交叉校验 **18/18 一致**；代价 = plan 步数面丢失（表内记「未测」）。**轮志**: `docs/reports/r569-dose-axis-third-window-set-and-reject-window-cause.md` · 器具 `eval/rover/r569/`（只读定因件 `cause_reject_window_r569.py`、收口件 `closeout_r569.py`）· 读数 `kpi-table-r569.json` / `verdict-r569.json` / `summary-r569.json` / `readings-candidate4-r569.json` · 验收面 `eval/rover/r507pre/precondition-r569.json`（rc=1）。
- **下轮候选 (R570)**: ① **剂量轴不再开窗**（本轴非承重、已定案关闭；重开条件 = 换承重面或臂内机制改动）② **g1/wythoff 失分面**（三次定因均为产物缺陷 ⇒ 契约加厚 v3 / 产物落点自验，**待放行**）③ **交付闸语义**（`rc=5`/`rc=8` 已证「会拒收」，缺「拒收后可见原因 / 有界重试」⇒ 只读取证先行，动产品分支须待放行）④ 起手闸把**本会话工具子进程**（LSP/编辑器，非闸血统）纳入噪声面（器具改 ⇒ 先写后跑 + 保形重钉）⑤ 步数面回仓（`transcript`/`steps_executed` 入仓或由 ingest 吸收，防本轮同类丢失）⑥ 铁律 11 验收面口径待裁（对照组臂是否进 `require`）。
- **R570（同窗单变量轮：早停轴 `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL` 0 vs 2 × 外部真值 codex + 步数面回仓；零产品源码改动/零新增夹具/零新增开关）**: 6 新窗 `w143..w148` × 3 臂 × 58 例，全臂同枚 AOT 二进制（sha `320d0eb17e709d15`）。**真值面**: codex 逐窗 `58/58/43/56/58/58`（中位 58 / 极差 15；`w145` 真值自身失败 ⇒ `unreliable` 单列）。**质量**: E0(轴0) `58/58/58/58/52/47`（中位 **58**/极差 11）、E2(轴2) `58/47/45/58/49/45`（中位 **48**/极差 13）；配对面 `E2−E0` = `[0,−11,−13,0,−3,−2]`，**中位 −2.5**、极差 `[−13,0]`；同臂跨窗摆动 11/13/15 与效应同尺度 ⇒ 质量面**不可判**为轴致损失。**预注册三判据（原样判，不改阈值）**: A1 行使面 **PASS**（`early_stop_skipped` 逐窗 `[0,1,1,0,1,1]` Σ=4；`early_stop_pfail` 六窗恒 2 ⇒ 天然可行使）；A2 成本 **PASS**（调用 7/11 = **0.636**、新算 1423/3152 = **0.451**，均 ≤0.70）；A3 质量不降 **FAIL**（中位 −2.5 < −2 ∧ 三窗 ≤ −3）⇒ 按「宣称规则」定性 = **「成本降 / 质量降」前沿读数，禁用收益动词**。**代价与归因**: 省下的正是「公开用例回放已失败 ⇒ 那一次远端回灌修复请求不发」；E2 失败集合**严格大于** E0 且只落 `wythoff`（省掉的那次回灌正是该族唯一修复入口）。**判决**: 判据 v2 **rc=1 FAIL**（`quality_paired_shortfall:R570E0,R570E2`）；铁律 11 **rc=1**（8 臂×窗 BLOCKED，失败集合全落 `wythoff` 族 + 2 条真值侧）⇒ 成本读数标「参考（未可验收）」；起手闸 postcheck **rc=2**（运行窗 `in_min=2539` < GATE 2650、振幅 290 ≫ 上轮 90）⇒ 叠加「参考（门越线）」。**指纹**: rc=0（C4-1/2/3 三项 + 自检 4/4 有牙）；命中率（中继 dump 时间轴口径）v_all 中位 = C1 0.9403 / E0 0.9672 / E2 0.9819。**候选⑤（步数面回仓）**: ingest/kpi 声明式增补 ⇒ E0 `[15,7,14,9,7,7]`、E2 `[14,7,7,8,7,7]` 回仓（codex 侧无该字段记未测）。**自捕（器具面两件）**: ① 派生件**语法缺陷**（`ingest` 的 `rule` 串未转义引号 ⇒ 6 窗后处理件全缺、连铁律 11 前置器的 project 布局发现一并 `rc=3`）——按纪律**只重跑后处理、未重测**（首跑 `windows.jsonl` 区间齐备），并在 `setup_r570.py` 落**派生件语法门**（`py_compile` 全量派生件 fail-closed rc=3）+ 成对控制（正控现盘全过 / 负控取首跑真实坏行副本必须 rc=3，实测有牙）；② 残留机检漏 token `轴=3` ⇒ 已补 token + 声明式改写。**轮志**: `docs/reports/r570-early-stop-axis-frontier.md` · 器具 `eval/rover/r570/`（含 `closeout_r570.py`）· 读数 `kpi-table-r570.json` / `verdict-r570.json` / `summary-r570.json` · 验收面 `eval/rover/r507pre/precondition-r570.json`（rc=1）。
- **下轮候选 (R571)**: ① **早停轴的「有界替代」**（E2 失败面 = E0 失败面 + `wythoff` 增量 ⇒ 省下的那次回灌需替代路径或分族阈值；须动产品分支 ⇒ **待放行**） ② **g1/wythoff 失分面**（契约加厚 v3 / 产物落点自验；第三次定因仍为产物缺陷 ⇒ **待放行**） ③ **起手闸把本会话工具子进程纳入噪声面**（本轮 postcheck 越线 `in_min=2539`/振幅 290 = 承重新证据；器具改 ⇒ 先写后跑 + 保形重钉） ④ **交付闸语义**（`rc=5`/`rc=8` 仍交付 = 静默降级 ⇒ 待放行） ⑤ 本轮已闭合：R570-⑤ 步数面回仓、R570-⑥ 早停轴单变量（A1/A2 PASS、A3 FAIL）。
- **R571（同窗单变量轮 + 重复臂：既有开关 `AGENTFRAMEWORK_R1_MAX_REPAIR`(**契约不过时最大修复轮数**) 1 vs 3 × 外部真值 codex + 起手闸自体归因器具改 v3；零产品源码改动/零新增夹具/零新增开关）**: 3 新窗 `w149..w151` × 每窗 (codex ×1 + M1 ×4 + M3 ×4) = **27 跑次**（每跑次独立会话，外部真值 = `logs/runs.jsonl` 行数），全臂同枚 AOT 二进制（sha `320d0eb17e709d15`）。**本轴 = 既有开关里最后一个从未被单变量化的一格**（R542/R544/R547/R550/R551/R552/R558/R559/R560/R566/R567/R570 预注册均把它恒设为 1/默认）。**先量分布（96 份归档 transcript）**: `repair_rounds=1` 23 (24.0%)，其中 `stage=contract` rc=4 **5 例 (5.2%)** = 靶人群 ⇒ 天花板算式 `≤5.2%`（运行级）⇒ 12 跑次/臂下靶期望 0.62 例 ⇒ 预注册先写死 `resolution_bound`（**禁把「未测到」读成「无效应」**）。**真值面**: codex `[54,58,58]`（中位 58；`w149` 真值自身在同族失败 4 例）。**质量（逐跑次/58）**: M1 `[58,51,47,52,44,58,58,58,58,46,44,58]` 中位 **55**（逐窗中位 51.5/58/52）、M3 `[51,56,58,55,58,58,58,51,47,43,56,58]` 中位 **56**（55.5/58/51.5）；`D=M3−M1` 逐窗 `[+4.0, 0.0, −0.5]` 中位 0.0；同臂跨窗极差 14/15 **远大于**效应。**成本**: M1 `calls 24 / new_prompt 5,381 / completion 55,624`、M3 `24 / 5,712 / 57,182`（比 1.00 / 1.06），codex `279 / 72,506 / 52,919`；命中率 v_all M1 0.98 / M3 0.97 / C1 0.96。**预注册三判据（原样判）**: **A1 行使面 FAIL**（M3 上 `repair_rounds>=2` 的跑次 0；「同窗 M1 契约死 ∧ M3 非契约死」0 ⇒ 24 跑次里无一次把预算用到 1 以上）⇒ A2/A3 名义 PASS 但按预注册**作废**，判决 **rc=1 / mechanism-not-engaged**；并给出结构性理由: 归档 96 + 本轮 24 = 120 跑次、靶合计 5 (4.2%)，检出下限 ≈25 跑次/臂 > 本轮 12 ⇒ **单轮预算内结构性不可判定**（不冻结该轴）。**候选③ 器具改 v3（先量再改）**: ① R570 越线 `in_min=2539/swing=290` 的时间轴为**阶跃且与最长真值窗 w144(672 s) 边界对齐**；② 本轮**直接测到**: 起手前 `MemAvailable 2,510 MB < GATE 2650`（闸会拒起臂），清掉**本会话工具子进程**（`pyright-langserver` 274 MB + `bash-language-server` 147 MB，**均不在闸 blocker 血统内**）⇒ **2,839 MB（+359 MB）**，随后起手前 3 采样极差 **1 MB**、闸 A1/A2 连续 PASS ⇒ 前提获真机证实；③ `mem_sampler v2` 逐样本落 `own_rss_mb`（血统 = 采样器父进程后代 ∪ 命令行含运行根/端口者），`postcheck` 出 **v1(原始)/v2(自体加回) 双栏**，顶层 rc 取 v2 并同落 `rc_v1_raw`；**读数** `rc=0/rc_v1_raw=0`、362/362 样本带该字段、`own_rss_max=266 MB`、`own_rss_at_v1min=214 MB`、`foreign_residual=+165 MB` ⇒ **「v1 红/v2 绿」真机判别实例本轮未出现**（诚实边界），判别力由**成对控制 12/12 有牙**承担（含「部分归因 2630<2650 ⇒ v2 必红」与「R570 形状无字段 ⇒ v2≡v1 ⇒ 旧判 rc=2 **不翻案**」两例）。**铁律 11**: `--round r571` ⇒ **rc=1**（`EXECUTABLE_AND_CORRECT=False`；blocked 全落 `wythoff` 族全局序 `#43..#57`，含题面公开用例 `#43-public`；**真值臂同族也失败** ⇒ 与三次定因一致、非本轮变量所致）⇒ 全部质量/成本读数标「参考（未可验收）」。**自捕（器具/派生面两件）**: ① 轮目录复制 `cp -r r570 r571` 连 `evidence/windows/w143..w148` 一并带入 ⇒ 前置器报 6 条**伪 BLOCKED**（上一轮窗口「快照缺失」）⇒ 删陈旧窗口 + **只重跑检查不重测**（rc 仍 1、blocked 只剩真失败；纪律 = 轮目录复用必须显式排除上一轮产物面）；② 采样器 v2 升级后 `derive()` 旧 selftest 夹具（纯 int）触发 `TypeError` ⇒ 被 `--selftest` **起臂前当场拦住**，修法 = 输入归一化、**不放宽任何判据**。**轮志**: `docs/reports/r571-contract-repair-budget-axis.md` · 器具 `eval/rover/r571/` · 读数 `kpi-table-r571.json` / `verdict-r571.json` · 验收面 `eval/rover/r507pre/precondition-r571.json`（rc=1）。
- **下轮候选 (R572)**: ① **g1/`wythoff` 失分面修复**（契约加厚 v3 / 产物落点自验 —— **唯一质量杠杆**；第四次定因仍为产物缺陷，真值臂同族也失败 ⇒ 须动契约或产品分支 ⇒ **待放行**） ② **契约修复预算轴第二窗集并抬重复数**（≥25 跑次/臂 才过检出下限；零开发、既有开关）或按天花板 **冻结 1 + 写死重开条件** ③ **起手闸噪声面把会话工具子进程并入判据**（本轮只做了清场 + 测量，判据侧仍缺；+359 MB 已实测） ④ **交付闸语义**（`rc=5`/`rc=8` 仍交付 = 静默降级 ⇒ 新增产品分支 ⇒ **待放行**） ⑤ 本轮已闭合：R571-③ 器具改 v3（own_rss 归因 + 成对控制 12/12）、R571-⑤ 契约修复预算轴行使面取证（mechanism-not-engaged）。

- **R575（33 红收口轮：回补机制接线 W1/W2/W3 + 判定面零词表 + 端口/语料重生成；零新增夹具/零新增开关，动产品分支由用户令放行）**: 承接 R573（foreground, 22/33 转换, 未提交）· R574-tick（read-only 复核: 工作区 33 例红 × 提交态 5 例红, `agent.nlp.NlpGate` 已实现**零消费者**）。用户令（R573 引, 逐字）: 「33红全部要改为现有机制，否则你这么多天的努力全白费了」。**W1 判定面**（`src/agent.modelqueue/{TurnGateJudge.cs,LocalParaphraseChannel.cs}`）: `IsPureRepeat = IsRepeatShape ∧ 回补库命中`、`IsPureParaphrase = IsParaphraseShape ∧ ¬复述(⑤) ∧ 回补命中`、守卫 ⑥ 动作声明面 = 回补库 `claim` 面；删 `RepeatMarkers / QuestionSignals / RequestSignals / CorrectionSignals / Markers / ClaimWords` + `Parse` 中文词标记死循环。**W2 生产回补点**（`src/agent/IndustrialAgentV2.cs`）: 远端轮成功 ⇒ `TurnGateJudge.LearnOnSuccess(message.Content, llmResponse.Success)`（唯一写入点；Skip 轮不回补；族外输入不登记）。**W3 判据**: 11 个方法改**双侧断言**（无补丁 ⇒ 交远端 ∧ 回补命中 ⇒ 本地面成立），「无补丁」= 显式空集（不读进程级库 ⇒ 顺序无关）。**真机读数**: 起点 11 方法/33 例红 ⇒ 聚焦面 148 例 **Failed 0** ⇒ 全量 **Failed 0 / Passed 1900**；端口 `--selftest` PASS（ack 13 / repeat 15 / para 8）；API 基线 **+16 / −0**（纯增，复跑绿）。**真实流量组成**（state.db 只读复算, 规则变更 ⇒ 强制重生成语料）: 机械放行 0.7549 → **0.6509**（−10.4 pt = 删词面信号代价，该部分轮改走本地 r1 字母判官）、残余 0.1467 → 0.2545、**真实可跳面仍 0.0000**、真实轮「形状上可被回补」计数 **0**（反事实上界 0）。**器具自捕**: R468 端口源路径 `LocalGenerationPort.cs` 已不存在（文件改名 ⇒ 端口**静默失效**）⇒ 重钉真源 + 增**零词表 fail-closed 断言**（源码重现词表 ⇒ 端口停）。【诚实边界】① 守卫 ⑥ 无回补时**不覆盖**（只钉不误杀）；② 机械放行覆盖面 −10.4 pt 未补偿；③ 本轮**零真机远端调用 ⇒ 不宣称任何 token 降幅**；④ 回补库默认路径 `data/nlp/gate-patches.txt`（单测不写）。**轮志**: `docs/evidence/RF0001/R575-replenish-wiring.md` · 台账 `eval/capability/kpi.jsonl`（R575）· 器具 `eval/rover/r468/{gate_rules.py,real_traffic_classify.py,real-traffic-corpus.jsonl}`。
- **下轮候选 (R576)**: ① 守卫 ⑥ 动作声明面回补点（从 LLM 轮/评审学习声明词面；补回 R575 诚实边界①） ② R571-② 契约修复预算轴第二窗集（≥25 跑次/臂）或按天花板冻结 + 写死重开条件 ③ R572-③ 起手闸把会话工具子进程并入判据 ④ R572-① g1/`wythoff` 失分面修复 与 R572-④ 交付闸语义（`rc=5`/`rc=8`）仍**待放行**。 ⑦ 裁定「登记表证据是否随提交」：干净检出树（worktree@HEAD）跑登记表机检得 **22 项违规**（covers/evidence_path 指向未跟踪产物`data/probe`·`eval/rover`），主树因产物在场而绿 ⇒ 既有假绿形态（详见 `docs/evidence/RF0002/R576-shape-wiring.md` §4d）。

- **R576（RF0002 §2 形状通道接线轮 · 用户令「不补回」落地；零新增夹具/零新增开关）**: 起手核验发现 `LearnFromRemote`/`ReportOutcome` **生产零消费者**（孤岛）⇒ 本轮 A–F 六处接线：`LearnOnSuccess` 由逐字 `Observe` 改 `LearnFromRemote(..., localizable: true)`；`TurnGateJudge.IsPureRepeat` / `LocalParaphraseChannel.IsPureParaphrase` 判定面 = 结构面 ∧ (`IsPatched` ∨ `IsLearned`)；`NlpGate.IsLearned(text, face, libraryMode)` 新增重载（注入模式不读形状库 ⇒ 机检/差分用例顺序无关，R575 双侧断言逐位不变）；`IndustrialAgentV2` 4 处评分回执（本地消化成立 ⇒ useful:true；3 个降级点 ⇒ useful:false）。真机：定向 **Failed 0 / Passed 158**（含 5 接线断言 + 3 负控）、形式校验 **14/14**。证据 `docs/evidence/RF0002/R576-shape-wiring.md`。**诚实边界**：生产库 `data/nlp/` 不存在 ⇒ 真机**零命中（未测到）**、零远端调用 ⇒ **不宣称任何降幅**；归属：`agent.nlp` + RF0002 §1 由前台会话实施，本 tick 实施 §2 并代为落盘提交。
- **下轮候选 (R577)**: ① **形状通道真机首验**（跑一次真机链路使 `ShapeCounters.ShapeLearned/ShapeHits > 0`，把「零命中」变 ≥1 事件 + 命中不增远端调用的成对断言） ② 评分淘汰曲线观测（真实分布形状存量变化；零开发） ③ R571-② 契约修复预算轴第二窗集（≥25 跑次/臂）或按天花板冻结 + 写死重开条件 ④ R572-③ 起手闸把会话工具子进程并入判据（器具改 ⇒ 先落预注册） ⑤ R572-① g1/`wythoff` 失分面 与 R572-④ 交付闸语义（rc=5/rc=8）仍**待放行**。

- **R579-tick（RF0002 §3 验收面 ②③④ 的「可测化」轮：形状通道**通道级打点** + 机检器 P1–P5；零行为改动 / 零远端调用 / 零新增夹具 / 零新增开关）**: 前态锚 R578（`1536b2c`）。**动因 F1（可复现）**: RF0002 §3 的 ②③④ 依赖「形状通道被生产链路消费」，而 `ShapeCounters` 在生产面**只有定义、零消费者**（P1: 前态生产面 1 = `src/agent.nlp/NlpGate.cs:216`，测试面 2）⇒ 「**未接出**」与「**零命中**」在读数上**不可分**（且 `IsLearned` 明确不计数 ⇒ 模块计数对 repeat/paraphrase 面结构性恒 0）⇒ ②③④ 当时**不可判，不是「判为无」**。**改动（唯一变量）**: `src/agent/IndustrialAgentV2.cs` 一处通道级打点点位 `nlp_shape`，插在既有回补点 `TurnGateJudge.LearnOnSuccess(...)` **之后**（`--numstat` **+24 / −0**），键集 8 枚 `{route, shape, face, basis, hits, learned, shapes, msg_sha16}` 分别服务 ②（`shape`/`face`/`basis`/`hits`/`learned`）③（`shapes`）④（`route` + `msg_sha16` 与同轮 `llm_call` join）；点位只**读**既有状态（`repeatTurnFlag`/`paraphraseTurnFlag`/`IsLearned`/`ShapeCounters`/**既有** `LastBasis`），不入任何判定分支。**判据（预注册先落盘: `eval/rover/r579-tick/prereg-r579tick.json`）**: 机检器 `eval/rover/r579-tick/shape_kpi_face_check.py` **rc=0** —— P2 **前态锚有牙**（同一契约在前态字节判红: `has_point=false` → 现盘 `true`；sha16 `699008bc63e83379`→`4e9453b915626b45`）、P3 键集**恰好**（缺/多均判红: missing 0 / extra 0）∧ 点位在回补之后、P4 **零行为改动**（判定链 8 文件逐位不变 ∧ 目标文件删除行 **0**）。**真机**: 编译 **0 error**；定向 7 类（NlpGateLearn/LocalTurnGate/TelemetryPending/GateRulesPortDiff/VerificationForm/SkillGeneralization/DevPlanDocRef）**Failed 0 / Passed 114**，`--no-build` 逐类复跑加总 **114 == 合并跑 114**（无重复/漏计），形式校验面 **14/14 绿**。**自捕（器具 1 件，fail-closed 挡住）**: 键集扫描窗口含点位名字面量 ⇒ P3 把 `Emit` 形参 `"nlp_shape"` 当 kv 键 ⇒ `extra=["nlp_shape"]` **首跑 rc=1 假红**；定因 = **器具读法错**（非被测不符），修法 = 扫描窗口跳过点位名/模块名，**未放宽任何判据**（首跑读数留档不翻案）。**诚实边界**: ① **②③④ 现在「可测」但**未测到 ≥1 事件** —— 本 tick 零远端调用 ⇒ 点位所在分支（远端轮后的回补点）本轮**结构性不可达**；且现有测试类**无一**同时「配置遥测目录」∧「驱动 `IndustrialAgentV2` 轮次」（旁证: 遥测仅 `Program.cs:293` + 3 个遥测类自身 `Configure`），真机 host 需真实端点（无 `FAKE_LLM` 类开关）而本地判别位 3B 档 RSS 2643 MB > 起手前 `MemAvailable` 2398 MB ⇒ 本轮不起本地档（不为一次读数违约内存闸）；**「未测到」不得读成「无效应」，也不得读成「已验收」** ② 零行为改动 ⇒ **不宣称任何质量/成本降幅**（无可比窗口，本 tick 无质量读数）③ P4 冻结面按本轮变量范围枚举（判定链 + 闸计数），非全仓零改动。**轮志**: `docs/evidence/RF0002/R579tick-shape-kpi-face.md` · 器具 `eval/rover/r579-tick/shape_kpi_face_check.py` · 读数 `eval/rover/r579-tick/readings-r579tick.json` · 台账 `eval/capability/kpi.jsonl`（R579-tick）。**注**: R578 在 §7 **无块**（读数落提交信息 + `eval/rover/r578/` + `docs/verification-registry.json`）⇒ 本块「上一轮」= R577/R578 并列，不相减。
- **下轮候选 (R580)**: ① **形状通道真机首验**（= R577-①/本轮唯一直接面: 使 `nlp_shape{shape:"1"}` 落盘 **≥1 事件** + 成对断言「`shape=1` 的轮 ≥1 ∧ 该轮远端调用数不增」；**前置 = 远端调用放行 或 内存闸放行本地判别位档**，二者取一） ② 评分淘汰曲线观测（③ 的存量下降面；零开发，依赖 ①的首验） ③ R571-② 契约修复预算轴第二窗集（≥25 跑次/臂）或按天花板冻结 + 写死重开条件 ④ R572-③ 起手闸把会话工具子进程并入判据（器具改 ⇒ 先落预注册 + 保形重钉） ⑤ R572-① g1/`wythoff` 失分面 与 R572-④ 交付闸语义（`rc=5`/`rc=8`）仍**待放行**。

- **R581（RF0002 §3 验收面 ②③④ 真机首验：形状通道落 ≥1 条 `nlp_shape` 事件；零产品源码改动）**: 前态锚 R580（`adbe56d`）。**两跑次**: ① v1（18:44）三臂逐轮 `失败: 环境变量 AGENTFRAMEWORK_KEYS_DEEPSEEK 未设置` ⇒ 依预注册 `fail_closed` 第 2 条（远端调用不成功 ⇒ 学习前提不成立）**全臂 VOID**，原始日志留档 `eval/rover/r581/v1keys-absent/`（VOID 不判缺陷）；② v2（19:57）**同预注册重跑**（唯一差异 = 环境变量面；远端预检 `http=200`），A 18s / B 4s / N 7s 三臂齐。**真机读数（`readings-r581.json` + `verdict-r581.json`）**: 机制挂载面 `local_turn_gate_config{turn_gate_enabled=True, local_channel_ready=True, repeat_skip=on, role=skeptic}` 三臂均落盘（**非未接线**）。**判据（预注册照原样判，未放宽）**: **P1 PASS**（A 轮2/轮3 `shape=1 ∧ route=local_skip ∧ face=repeat`）、**P2 FAIL**（命中轮 llm_call **4 / 7** 次 ≠ 0）、**P3_learned PASS**（轮1 `learned=1 / shapes=1`，库落盘 1 条 40 B）、**P3_eviction FAIL**（`repeat_degrade_remote{reason=no_replayable_prev}` **逐字落盘** ∧ 同轮 `hits=0` ⇒ 合取第二项不成立）、**P4 PASS**（轮3 不同措辞 `msg_sha16=147757f75f39bd44` 仍 `local_skip`）、**P5 PASS**（N: `learned=0 / shape=0 / shapes 不增`）；`P3_net_decrease` 预注册已写明**不可观测** ⇒ 未测到（不作失败）。**后验归因（`posthoc-r581.json`，不改判据）**: ① P2 机理 = 命中轮远端调用**全部**为 `finish_reason=tool_calls` 的**工具循环**调用（`empty_cause=tool_call` / `retry_skipped=true` / `routed_to=action*`），t1 形态的主回答调用（`stop`, prompt 4362）确未发生 ⇒ **「本地消化」当前只覆盖最终答复文本**（`local_gate_skip_reply` 重放），未覆盖该轮工具循环面；② **三列口径（逐轮）**: 调用 1→4→7、**新算 prompt 4234→1150→2311**（命中轮 −73% / −45%）、completion 599→616→1408、含 cache 总 prompt 4362→7038→14727 ⇒ 命中轮**不是单向的省或费**，必须三列分列；③ P3_eviction 机理 = `hits` 语义为本地回放命中数，全新会话结构性为 0 ⇒ 预注册把「降级路径可达」与「回放命中」绑成一个合取 ⇒ 下轮拆成 P3a/P3b 后重注册。**自捕（器具 1 件，已修，未放宽判据）**: `extract_r581.py::read_slice` 文本模式 `read(byte_delta)` 入参是**字符数** ⇒ 多字节切片被多读（arm A 多读 1 条 arm B 事件）并在切点产生 1 条**假解析失败**；改字节切片后 `events A 148→147`、`parse_fail 2→0`，**verdict 逐键相同**（⇒ 判据未受读法影响）；首跑读数留档 `readings-r581-v1textmode.json` / `verdict-r581-v1textmode.json`，**不翻案**。**诚实边界**: ① 四条 `nlp_shape` 事件的 `hits` **全为 0**，命中轮依据字段 = `basis mechanical:repeat→local`（规则面）⇒ 本轮证实的是**「学到了」+「规则面本地化」**，「**按 learned-shape 命中**」**未测到**（未测到 ≠ 无效应 ≠ 已验收）；② 零产品源码改动 ⇒ **不宣称任何质量/成本降幅**（无可比窗口）；③ 单轮 n=1 每臂 ⇒ 只作**机制存在性**证据；④ **质量 / 轮数 / 命中率 / 问答计数 / codex 外部真值对照：本轮未测**（非质量对照窗）。**轮志**: `docs/evidence/RF0002/R581-shape-channel-firstrun.md` · 预注册/DAG: `eval/rover/r581/{prereg-r581.json,dag-r581.json}` · 台账: `eval/capability/kpi.jsonl`（R581） · 冲突登记: `docs/reports/round-collision-log.jsonl`（R581 / arm-void）。**注**: R580 与 R580-tick 在 §7 **均无块**（R580-tick 为让行 tick，读数落 `eval/rover/r580-tick/tick-record-r580tick.json`）⇒ 本块「上一轮」= R579-tick / R580 并列，**不相减**。

- **下轮候选 (R582)**: ① **命中轮工具循环面**（调用 4/7；P2 FAIL 的直接面）—— **先量再改**（按类分解天花板，禁预防性机制轮） ② **P3 合取判据拆分**（P3a 降级路径可达 / P3b 回放命中）后**重注册** ③ **learned-shape 命中 vs 规则面命中 分离臂**（非 repeat 面 / 同面异规则；目标把 `hits>0` 变 ≥1） ④ 命中轮 completion 上升（599→616→1408）归因：工具循环 vs 上游空正文 ⑤ **作业环境自备 key 面**（本轮 v1 VOID 的直接原因；cron 会话环境缺 `AGENTFRAMEWORK_KEYS_DEEPSEEK`） ⑥ R580 候选① 余项（形状通道成对断言「`shape=1` 的轮 ≥1 ∧ 该轮远端调用数不增」的**第二合取项**本轮已判 FAIL，其收窄路径见 ①）。

- **R583（RF0002 §3 验收面 P2/P3 **判据面收窄与重注册**：调用面分层 + 形状面真机臂；**零产品源码改动**）**: 修改点 ① **量（先量再改，归档数据分层）** `eval/rover/r583/{plane_split_r583.py,plane-split-r583.json}` —— R581 命中轮 4/7 次调用**全部**为会话外面（`llm_call.agent_session` 空 ∧ `turn=0`；臂A 宿主面 11/12 = **91.67%**），agent 面命中轮 = **0**；命中轮 completion 616/1408 **100% 来自宿主面** ⇒ 「命中面零调用」在**窗口口径**下结构性不可达 ⇒ 判据面改为 **agent 面**（两条独立路径交叉校验，不符即 rc=2）。② **重注册** `eval/rover/r583/prereg-r583.json`（先于任何跑次）+ 器具 `extract_r583.py`：P2 分层（agent 面调用 1→0）、P3 拆 **P3a**（降级路径可达）/ **P3b**（形状命中呈报；`hits` 生产面结构性恒 0 —— `_shapeHits++` 唯一写点 `src/agent.nlp/NlpGate.cs:129` 在 `Decide` 内，而 `NlpGate.Decide` 生产调用点 **0**）⇒ P3b 改判 `shape=1`。③ **真机臂单变量 = 形状库有无**（fixture 逐字复用 R581 真机产物 sha256 `c98f8ab3…`；库起手 `data/nlp` absent）：S1 轮2 `local_skip`（shape=1/face=repeat/basis=mechanical:repeat→local/agent+宿主面调用均 0/completion 0/kind=repeat_verbatim）vs S0 同输入无库 = `remote`（shape=0）；D 臂 `repeat_degrade_remote{no_replayable_prev}` 可达 ∧ 同轮 shape=1；N 族外 shape=0/learned=0。④ **自捕（真缺陷形态，登记不定因修复）**：形状库**内存剔除不落盘**（degrade 点 `ReportOutcome(useful:false)` 只改内存 + 同轮远端成功后重新学习 ⇒ `Same(face/lang/band)` 未拦住 ⇒ **追加行**）⇒ 臂 D 库 1→2 行（sha `04ad26a8…`），**同源解释 R581 重复行异常**（原登记「机理未定因」在本轮定因）。⑤ **候选⑤ 落地**：常驻作业 `b15eb2f40a69` prompt 补 key 自备步骤（store 备份 + 指纹 + 回读断言，prompt 4195→4347 字符；key 值不入仓）。⑥ 收口：台账行 `eval/capability/kpi.jsonl`（R583）、登记行 `docs/verification-registry.json`（`r583.shape-face-plane-split`, L3, rows 277→278, `updated_round=R583`）、轮志 `docs/evidence/RF0002/R583-shape-face-plane-split.md`。**判据裁定 rc=0（6/6 PASS），器具负控 3/3 有牙**（注入 agent 面调用 ⇒ P1/P2 红；伪造 S0 命中 ⇒ P4 红；去掉 degrade ⇒ P3a/P3b 红）。**诚实边界**：零产品改动 ⇒ 不宣称质量/成本降幅；单轮 n=1 每臂 ⇒ 只作机制存在性；codex 外部真值同题对照/回复质量/轮数/问答计数**未测**；**R581 的 P2 FAIL / P3_eviction FAIL 保留不翻案**（判据未放宽，本轮 agent 面口径为新注册，与 R432「先分通道再汇总」同族）。
- **下轮候选 (R584)**: ① **形状库落盘一致性修复**（`ReportOutcome` 剔除须落盘 + 去重/行数守恒成对判据；本轮已定因但需产品改动放行） ② **宿主面调用面量化**（agent 面已 0 ⇒ 收窄靶点转为「会话外循环的调用触发谓词与占比可省性」，先量再改） ③ **分层判据并入 RF0002 §3 正文**（`docs/plans/RF0002-nlp-self-improvement.md` 同步 agent 面口径与 P3a/P3b） ④ **codex 外部真值同题对照轮**（主线质量列，R583 未测） ⑤ 主线：与外部真值同窗对照的**质量/轮数**面（R567 后未再跑）。

- **R585（主线对照轮 · 器具环境恢复后首次可起臂；零产品源码改动 / 零新夹具语义 / 零新开关）**: **修改点** ① **前置件落点修复**：R584 前 harness 前置件只存 `/tmp` 且已被回收（R585 定因） ⇒ 落点改为稳定路径 `~/.agentframework/harness/runs/r585`（`restore_env_r585.py` 等价性证明 + 回读），驱动器起手自恢复、仍缺则 `exit 3` fail-closed（合「只存 /tmp 的产物入仓」先例 `1dac7689` 的同类纪律）；② 驱动器 `run_r585.sh` 派生自 `run_r571.sh`（轮号/臂集合/剂量键**三枚显式 unset**/二进制 sha 运行前后一致性断言/起手闸条款）+ 判据器 `kpi_r585.py` 派生自 `kpi_r571.py`（主线段改 C0/C1/C2，无剂量轴）；③ 台账行 `eval/capability/kpi.jsonl`（键集与同族既有行逐字相同，同轮原地更新 ⇒ 幂等）+ 报告 `eval/rover/r585/report-r585.md`。**真机读数**（3 窗 `w154..w156`，每窗 = 真值 ×1 + 产品默认档 ×3；冻结题集 sha `e0c667c2…` 与 R559–R583 同件；二进制 sha `4b70fd7c…` 运行前后一致）：**质量（58 例）** 真值逐窗 `56 / 58 / 58`（中位 58、极差 2）vs 产品默认档逐窗中位 `58 / 50 / 55`（中位 55、极差 8；逐跑次 `58,58,58 / 53,50,47 / 58,48,55`）。**判据裁定 rc=1 FAIL**：C0 真值 `w154` 自身 56/58（`wythoff#55/57-hidden`）⇒ 该窗标 unreliable 不进配对（**该 2 例单列，不记我方缺陷**）；C1 有效窗 = `w155/w156`，配对差（产品−真值）= `[−8, −3]`、中位 **−5.5** < 预注册下限 −2 ⇒ **质量未达判据**（逐窗下限 −15 全过；有效窗 2 恰达下限）。C2 成本三列（**因铁律 11 rc=1 ⇒ 一律标「参考（未可验收）」**）：调用 20 vs 74（−73%）/ 新算 prompt 5,601 vs 28,392（−80%）/ completion 48,941 vs 23,907（**+105%**）/命中率 v_all 0.97 vs 0.97、v_incr 0.96 vs 0.97。**铁律 11**：`executable_and_correct=false`、`acceptable_scoped=false` ⇒ rc=1 未可验收，而 `self_report_agrees=true` ∧ `self_report_mismatch=[]`（独立物化实跑与在跑自报**逐条一致**）。**逐例归因**（`per-case-failures-r585.json`）：失败 **100% 集中 `wythoff` 单族**（`stdout_mismatch` 为主；`TimeoutExpired` 8 例仅 w155-r2；`rc=1` 2 例）⇒「一个模块缺陷带走整族」结构复现；超时**两条独立路径互证**（在跑自报 8 例 ∧ 前置器独立重跑同跑次 `rc=124`，50/56 —— 后 2 例因其自身超时未测，分母 56<58 为诚实边界）⇒ 非采集侧假红。**起手闸/判别力**：条款 = 阈值 + 观测振幅余量（R571 实测 swing 105MB）+ 连续 2 次 ⇒ `REQ=2713`（ceiling 2773）；A1/A2 真机 PASS（2768/2761MB）；**判别力成对控制 rc=0**（压制入带 ⇒ 基础门槛 PASS ∧ 条款 GATE_BLOCKED ⇒ 闸确行使）；泄漏自检 rc=0；起臂前按 pid 清本会话工具子进程（2 个 LSP 共 317MB ⇒ `MemAvailable` 1906→2890MB）。**自捕器具 2 件（均未放宽判据）**：① **闸输出读契约** —— 闸 stdout = pretty JSON **＋ 尾行 `out <path>`**，首版 `json.load(stdin)` 解析异常被吞成空串 ⇒ 起手闸读成「未过」并 `exit 2`：**fail-closed 生效、未起臂零污染**，修法 = 读 `--out` 落盘件（与 R571 同形），失败跑次留痕不翻案；② KPI 判据器残留 `R585M1/R585M3` 引用 ⇒ 汇总 `KeyError`，修后**只重跑后处理不重测**（`readings.jsonl` 未变）。**诚实边界**：① 铁律 11 rc≠0 ⇒ 调用/token 降幅**不得作验收依据**，completion +105% 单列不得被调用下降掩盖；② 质量列按预注册判 FAIL（中位 −5.5）；③ 跨窗摆动 8 例 ≈ 或 > 部分臂间差 ⇒ 单窗不作能力结论；④ `steps_executed/plan_steps_total`（轮数列）**R585 报告面纠偏（R586 轮 C6 段机检）**：该列**本就在档**（`verdict-r585.json::arms.R585D.steps=[8,15,7,14,7,7,7,7,7]`），而 R585 报告与本节原写「本轮未测（adapter 未取该字段）」= **报告面与自身读数不一致**（「adapter 未取该字段」为误述）；**首跑读数不撤**，仅更正措辞（下条候选②随之闭合）；⑤ 真值臂 rc 字段 null（外部 CLI 无本仓 rc 语义）；⑥ w154 不可配对 ⇒ 有效窗仅 2，不补窗。**轮志**：`eval/rover/r585/report-r585.md` · 预注册/DAG：`eval/rover/r585/{prereg-r585.json,dag-r585.md}` · 台账：`eval/capability/kpi.jsonl`（R585）。
- **下轮候选 (R586)**: ① **`wythoff` 单族失分收口**（本轮唯一承重族：先量「同族内失败例的分布 + 是否落在同一子规格」再改，禁预防性机制轮；须产品改动放行） ② **轮数列补齐**（`steps_executed/plan_steps_total` 进 adapter ⇒ 六格报表的「步数/轮数」列由「未测」转实测） ③ **`TimeoutExpired` 与 `stdout_mismatch` 分离臂**（固定 60s 截止的敏感性：同族同例复跑 3 次判「不收敛 vs 慢」） ④ 铁律 11 前置器分母补齐（本轮 `50/56` ⇒ 对超时例补独立判定） ⑤ 主线：`w154` 类「真值自身失分窗」的配对口径（单列 vs 剔除）在预注册里写成显式二选一。

- **R586（主线对照轮 · **同被测件 + 同冻结题集、只换窗集**的复跑：判定 R585 质量缺口是否跨窗复现；零产品源码改动 / 零新夹具语义 / 零新开关）**: **修改点** ① 驱动器 `run_r586.sh` 派生自 `run_r585.sh`（轮号/臂集合/窗口段替换 + 二进制 sha 运行前后一致性断言 + 起手闸条款）；② 判据器 `kpi_r586.py` 派生自 `kpi_r585.py`（主线段 C0/C1/C2 替换 + **C5 缺口复现段**（与 R585 D 集同号 ∧ 区间重叠的三态判定）+ **C6 步数列面段** + 汇总打印面补 `steps` 列）；③ **判据器影子自检** `eval/rover/r586/shadow_selftest_r586.py`（零被测执行，7 例：可判绿 / 异轮臂名缺侧 fail-closed rc=3 / R585 读数投影后逐值复现其判决 / floor 有牙 / 有效窗不足判红 / 步数缺档 rc=2 / `bad_dumps` rc=2）；④ 只读定因器 `eval/rover/r586/wythoff_cause_r586.py`（派生自 r562 同族器具 + `--only-idx/--timeout/--reclassify` 三参数）；⑤ 台账行 `eval/capability/kpi.jsonl`（R586）+ 轮志 `eval/rover/r586/report-r586.md` + 主线状态块「最近一轮」刷新（R585 行转历史快照）。**真机读数**（3 窗 `w157..w159`，每窗 = 真值 ×1 + 产品默认档 ×3；冻结题集 sha `e0c667c2…`；二进制 sha `4b70fd7c…` **与 R585 同件**、`bin_sha_stable=true`）：**质量（58 例）** 真值逐窗 `58/58/58`（中位 58、极差 0、`all_pass` 3/3 ⇒ 无 unreliable 窗）vs 产品默认档逐窗中位 `58/55/43`（中位 49、极差 15；逐跑次 `47,58,58 / 55,58,49 / 48,43,43`）。**判据裁定 rc=1 FAIL**：C1 配对差（产品−真值）= `[0,−3,−15]`、中位 **−3** < 下限 −2 **且** `w159` D=−15 **触底**（两条同时未过）；C5 = **「缺口跨窗复现」**（与 R585 `[−8,−3]` 同号 ∧ 区间重叠；**并列不相减**）；C6 **PASS**（步数 9/9 `[7,7,7,13,8,7,7,7,7]` / `plan_steps_total [10,10,17,14,9,10,10,11,11]`）；C7 = **0 超时例**（R585 的 8 例 `TimeoutExpired` 未再现，同 60s 口径；零产品改动 ⇒ 不作「已修复」宣称）；C0 PASS。**C2 成本三列（铁律 11 rc=1 ⇒ 一律标「参考（未可验收）」）**：调用 19 vs 51 / 新算 prompt 4,058 vs 25,012 / completion 44,380 vs 24,561（**按跑次归一** 2.11 vs 17.0 / 451 vs 8,337 / 4,931 vs 8,187；两侧跑次数 9 vs 3 ⇒ **禁比总量**）/ 命中率 v_all 0.97 vs 0.95、v_incr 0.97 vs 0.96。**铁律 11**：`precond.rc=1`、6 臂窗不合格（`w157-r1 47/58 · w158-r1 55/58 · w158-r3 49/58 · w159-r1 48/58 · w159-r2 43/58 · w159-r3 43/58`，全为本侧臂）、`executable_and_correct=false` / `acceptable_scoped=false` / `self_report_agrees=true`。**逐例归因（只读，冻结快照副本重放 + 与被测零共享 oracle）**：失败 **100% 集中 `wythoff` 单族**（15 例），类别 `MOVE_NOT_COLD` 38 / `EMPTY_OR_ERROR` 12 / `LOSE_FOR_WIN` 7 / `WIN_FOR_LOSE` 6；族内通过数 `w157 4/15/15 · w158 12/15/6 · w159 5/0/0` 加回非族 43 例后与铁律 11 前置器逐臂窗 **9/9 完全一致** ⇒ 非采集侧假红；**同臂同例跨窗「既过又败」11/15 · 15/15 · 15/15、跨窗产出多类 13/15 · 15/15 · 15/15 ⇒ 摆动 ≥ 臂效应，单窗不作能力结论**；定因器自证 oracle 正控 15/15 ∧ 59 变异零误放行（`has_teeth=true`）。**起手闸**：`ceiling=2819 / margin=105 / REQ=2755`；A1/A2 真机 PASS（2835/2840MB）；leak-selfcheck rc=0；**判别力成对控制未行使**（`gate-disc-pair.json` = 两臂同判 `GATE_BLOCKED`、`in_band=true`、`true_discrimination=false`、rc=3，按「未行使已登记」放行起臂 ⇒ **不得读成闸已行使**）；起臂前按 pid 清本会话工具子进程（2 个 LSP 278MB ⇒ 2567→2845MB）。**自捕 3 件（均未放宽判据）**：① **R585 报告面与自身读数不一致**（`steps` 列本在档而报告写「未测」⇒ 已按 C6 更正措辞，读数不撤）；② 判据器汇总**打印面缺 `steps` 列**（读数在档而打印面丢列）⇒ 补列后**只重跑后处理**（不重测）；③ **影子自检用例自身缺陷**（初版直接喂 R585 读数期望 rc=1，实得 rc=3 —— 判据器 fail-closed 正确、错在用例未做臂名投影）⇒ **修用例不改判据**，修后 7/7。**诚实边界**：① 铁律 11 rc≠0 ⇒ 调用/token 降幅**不得作验收依据**，completion 亦只作参考；② 质量列按预注册判 FAIL（中位 −3 ∧ 一窗触底）；③ 两侧跑次数不等 9 vs 3 ⇒ 总量不可比，须按跑次归一（本报告已给双列）；④ 真值臂无快照（外部 CLI 产物在回复正文）⇒ 定因只覆盖产品 9 臂窗，3 条 `missing_snapshot` 如实登记；⑤ 真值臂 rc=null / 步数 n/a；⑥ `MOVE_NOT_COLD` 落点指纹已落盘但**是否落在同一子规格本轮未定**（下轮靶点）；⑦ 超时未再现不得读成「已修复」。**轮志**：`eval/rover/r586/report-r586.md` · 预注册/DAG：`eval/rover/r586/{prereg-r586.json,dag-r586.md}` · 定因：`eval/rover/r586/wythoff-cause-r586.json` · 台账：`eval/capability/kpi.jsonl`（R586）。

- **下轮候选 (R587)**: ① **`wythoff` 单族「同子规格」定因**（本轮已量出类别分布与落点指纹：38 例 `MOVE_NOT_COLD` 的 `target(a,b)` 是否落在**同一子规格**（如 `int(phi*min)` 型错法）——**只读量化，零产品改动**；产品改动须用户放行） ② **`EMPTY_OR_ERROR` 12 例定因**（集中在 w159-r2，与「产物未交付」族是否同源；本轮 `rc=5` 全档） ③ **有效窗下限的判据面收口**（R585 因真值自身失分只剩 2 窗、R586 全 3 窗；「真值自身失分窗」= 剔除 vs 单列 的**显式二选一**写法）+ `w154` 类窗的历史读数并列清单 ④ 成本列**按跑次归一**口径入册（两侧跑次数不等时的标准写法；本轮仅在报告面落实） ⑤ 主线：`w157..w159` 三窗是否扩到 ≥6 窗以把摆动估计收紧（摆动 15/15 ⇒ 需更多窗才能谈「臂效应」） ⑥ **审计器作用域分支**：`tools/roundcheck audit` 对「零产品源码改动对照轮」的 **R1/R6/R8 三项结构性 FAIL**（R585/R586 **同形**：无能力新增 ⇒ 无登记行；逐窗快照归档 115/124 文件 > 阈值 40；R8 只读登记行 + 其 `evidence_path`）⇒ 为该类轮次增「无登记行」分支或显式 scope 声明（**禁改判据凑绿、禁补假登记行**）；本轮收口只做「提交标题按轮号约定改写 `R586: …`」使 **R2/R7 真跑**（密钥面得证）。

- **R587（主线**同件扩窗轮** + R586 六项候选并轮收口：w160..w162 第三窗集；零产品源码改动 / 零新夹具语义 / 零新开关）**: **修改点** ① 驱动器 `run_r587.sh` 派生自 `run_r586.sh`（轮号/窗口段 157→160/端口 49551→49571/**起手闸摆动余量 105→130 = max(130 r585 实测, 79 r586 实测)** 随观测收紧）；② 候选 ① 只读定因器 `eval/rover/r587/wythoff_subspec_r587.py` + `arm_spec_vs_outcome_r587.py`（产物 sha **与去注释语义骨架哈希** × 例级结果 × 落点多样性，随轮自证指纹有牙 `selftest_fails=[]`）；③ 候选 ② 只读重放器 `empty_error_cause_r587.py`（**两侧成对控制**：已知全过产物 0 例本族 ∧ 已知空产物产物 10 例本族 ⇒ `has_teeth=true`；新增 `NO_ARTIFACT` 臂级分支把「臂级未交付产物」与例级崩溃分开；类别标签 `NONEMPTY_RC0_FAIL`→`NONEMPTY_RC0_OTHER` 更名，**首跑/扩轮跑产物不重跑不覆盖**，旧标签由 join 白名单排除）；④ 候选 ③④⑤ 收口器 `sixwindow_pool_r587.py`（7 有效窗并列摆动 + `cost_per_run` 三列口径入册 + 有效窗下限显式二选一；修一处 arm-key 解析缺陷 `R585D`≠`R586D`）；⑤ 候选 ⑥ `tools/roundcheck/roundcheck.py` 增 `read_audit_scope()` + R1/R6/R8 对照轮分支 + **6 夹具（正控 1 + 负控 5）**，声明件 `eval/rover/r587/audit-scope-r587.json`（`declared_after_run=true`，**冻结预注册未触碰**）；⑥ **重审**：`r582.round-validity-auditor` 行 `instrument_sha12` 477d53280507→b348eff8dd63 ∧ `audited_by_round`→R587（官方 `bind_evidence --only … --apply` 对 `frozen/archived-per-round` 行 `COVERED 0 → 0` **不覆盖** ⇒ 按「先断言序列化器逐字节复现原文件」做程序化定向重钉，rows 279→280，`numstat +23/−4`，回读断言仅该行+新行+`updated_round` 变化）。**真机读数**（3 窗 `w160..w162`，每窗 真值×1 ＋ 产品默认档×3；题集 sha `e0c667c2…`、二进制 sha `4b70fd7c…` **与 R585/R586 同件**、`bin_sha_stable=true`）：**质量（58 例）** 真值逐窗 `58/53/58`（`w161` 自身失分 ⇒ `unreliable` 剔除配对并单列）vs 产品逐窗中位 `58/50/45`（逐跑次 `58,58,58 / 50,43,58 / 45,58,0`）。**判据裁定 rc=1 FAIL**：C1 配对差 `{w160:0, w162:−13}`、中位 **−6.5** < 下限 −2（逐窗下限 −15 未触发）；C0 因 `w161` 真值 53/58 判 FAIL（剔除+单列）；**C5 = 「缺口跨窗复现」**（与 R586 D 集同号 ∧ 区间重叠，**并列不相减**）；C6 步数 9/9 `[14,7,7,8,7,7,13,14,0]` PASS；C9 有效窗下限**显式二选一**（剔除 ∧ 单列 ∧ 不记我方缺陷）+ `w154` 类窗历史读数并列。**六窗并列摆动（候选⑤）**：7 有效窗 D `[−8,−3,0,−3,−15,0,−13]`、中位 **−3**、极差 **15**、逐窗偏离中位 max **12**；窗口集效应量 −3.5 ⇒ 按预注册 C5 原文判 **「摆动 ≥ 效应 ⇒ 单窗不作能力结论，需更多窗」**；三窗集中位 −5.5 / −3 / −6.5 **同号且落在摆动带内**。**C2 成本三列（铁律 11 rc=1 ⇒ 一律标「参考（未可验收）」）**：调用 20 vs 17 / 新算 prompt 5,377 vs 10,584 / completion 44,856 vs 8,364（**按跑次归一** 2.22 vs 5.67 / 597 vs 3,528 / 4,984 vs 2,788；两侧跑次数 9 vs 3 ⇒ **禁比总量**，`runs_jsonl_consistent=true`）/ 命中率 v_all 0.97 vs 0.91、v_incr 0.95 vs 0.94。**候选 ① 定因（wythoff 是否同一子规格）**：36 跑次取 `games/wythoff.py` 身份 ⇒ **在盘 35 份、sha 与语义骨架哈希两两不同、共享 sha = 0** ⇒ 「同一子规格」**在产物层为假**（每次跑次生成不同实现）；同输入落点多样性 15 例中 9 例 ≥2（**max 4**）⇒ 排除「一条固定错法解释全族」；形态指纹 `PHI_DIFF 15/36`、`UNCLASSIFIED 18/36`（**可识别率 0.472 如实登记**）。**候选 ② 定因（EMPTY_OR_ERROR 是否与「产物未交付」同源）**：本族 24 例 = `IndexError` 10 ＋ `TypeError` 6 ＋ `TIMEOUT` 8；R586 的 12 例 `EMPTY_OR_ERROR` = `w159-r2` IndexError×10 ＋ `w158-r1` TypeError×2，且**同一对异常形态在 R585（`w155-r1`）/ R587（`w162-r1`）复现** ⇒ **跨三轮同源**（产物在边界/异常路径未自验即交付）；`TIMEOUT` 8 例集中 `w155-r2` 单跑次（独立族）；**新发现**：`w162-r3` = `rc=4` ∧ 回复 18,913 B ∧ **工作区零文件** ⇒ **臂级未交付产物**（真实读数 0/58，非器具 VOID）。**候选 ⑥ 收口 + 重审链**：`--selftest` 对照轮分支 正控 1/1 + 负控 5/5 全绿（触碰 `src/` / 无声明 / 声明非法 / 声明面缺形式门禁 / 提交面越界）；**历史判决中性**（现盘器具重跑 `audit R580` rc=0、`audit R586` rc=1 且**同三条红**）；`bind_evidence --check` `R2E_R2F_EXIT` 2→**0**；`decl_sweep` 0 漂移；`status_gen --check` PASS。**起手闸**：attempt v1 被 **fail-closed 拦下**（顶棚 2585MB 装不下 2650+60，驱动器 exit 2，留档 `prearm-v1-gate-blocked.json`）—— 归因 = **会话端工具子进程（LSP）残留**（不在闸 `own_n` 匹配面内却吃 `MemAvailable`），按已核实 pid 清场 **2621→2839MB（+218）** 后 v2 放行（`ceiling=2804 / margin=94 / REQ=2744`，A1/A2 PASS，**判别力成对控制真行使 rc=0**，`leak-selfcheck rc=0`）。**形式门禁**：首跑 **13/14**，唯一真红 = `r582.round-validity-auditor` 器具绑定漂移（**本轮器具改动应有的后果**，非假红）⇒ 定向重审后 **14/14 绿（Failed 0）**。**铁律 11**：`rc=1`、`executable_and_correct=false`、`acceptable_scoped=false`、`self_report_agrees=true`；未过臂窗逐条点名 `w161/r1 50/58 · w161/r2 43/58 · w161/codex 53/58 · w162/r1 45/58 · w162/r3 0/58` ⇒ **成本降幅不得作验收依据**。**诚实边界**：① 摆动 15 ≥ 效应 3.5 ⇒ 单窗集不作能力结论；② `w162-r3` 为**臂级未交付产物**（按「VOID 臂窗单列」事后校核剔除后 D 集中位 −3.25，**仍 FAIL**，主判据不翻案）；③ 形态指纹可识别率 0.472 ⇒ 子规格分类**不完整**，结论只到「产物两两不同」；④ ② 的扩轮跑沿用首跑落盘件旧标签名（语义=本族外），**不重跑不覆盖**；⑤ ⑥ 声明件为**跑后落盘**、R6 面形状为代理判据、无 CI 接线；⑥ 真值臂 `w162` 无 `reply.txt` ⇒ 其 rc `null`/步数 n/a。**轮志**：`eval/rover/r587/report-r587.md` · 预注册/DAG：`eval/rover/r587/{prereg-r587.json,dag-r587.md}` · 定因：`eval/rover/r587/{wythoff-subspec-r587.json,empty-error-cause-r587.json,spec-vs-outcome-r587.json}` · 客观读数：`sixwindow-pool-r587.json` · 器具：`tools/roundcheck/roundcheck.py` + `docs/evidence/RF0001/R587-roundcheck-contrast-scope.md` · 台账：`eval/capability/kpi.jsonl`（R587）。

- **下轮候选 (R588)**: ① **`w163..w165` 第四窗集**（把有效窗推到 ≥6：摆动 15 与效应 3.5 尚未分离；同件同题集、零产品改动） ② **`TIMEOUT` 族定因**（`w155-r2` 8 例集中单跑次：先量「不收敛 vs 慢」，同族同例复跑 3 次 + 逐步计时） ③ **臂级未交付产物 `rc=4` 定因**（`w162-r3`：18,913 B 回复 + 工作区零文件 ⇒ 只读回放其 transcript，定位「计划未落盘」的谓词） ④ **`PHI_DIFF` 骨架下的边界处理分类加厚**（把 18/36 欠分类降下来，纯只读、不改判据） ⑤ 铁律 11 前置器对「臂级零产物」窗的**分母口径**（现按 0/58 计入 ⇒ 是否与「未执行臂窗」分列；先给判据面写法再动器具）。

- **R588（主线**同件扩窗轮 · 第四窗集** + R587 五项候选并轮收口：`w163..w165`；零产品源码改动 / 零新夹具语义 / 零新开关）**: **修改点** ① 驱动器 `run_r588.sh` 派生自 `run_r587.sh`（轮号/窗口段 160→163/端口 49571→49591/**起手闸摆动余量 130→65 = R587 实测振幅**（`min(65, cap=151)` 不夹））；② 判据器 `kpi_r588.py` 派生自 `kpi_r587.py`（C5 前序集指向 R587 + **C5b 四窗集池化段**：逐集并列 + 池化中位/极差 + 双侧精确二项 + 三态规则）；③ 候选② 器具 `timeout_cause_r588.py`；④ 候选③⑤ 器具 `noartifact_cause_r588.py` + 判据面 `noartifact-denominator-spec-r588.md`；⑤ 候选④ 器具 `subspec_v2_r588.py`（轴 A 恒等 + 轴 B 加厚 + 对照组判别力 + 结果面交叉）；⑥ 收口器 `finish_r588.py`（台账行原地替换 ⇒ 幂等 + 轮志生成）。**真机读数**（3 窗 `w163..w165`、每窗 真值×1 ＋ 产品默认档×3；题集 sha `e0c667c2…`、二进制 sha `4b70fd7c…`、`bin_sha_stable=true`）：**质量（58 例）** 真值逐窗 `[58, 58, 53]`（`w165` 自身失分 ⇒ `unreliable` 剔除并单列）vs 产品逐窗中位 `[58, 47, 43]`（逐跑次 `[51, 43, 58, 43, 58, 47, 44, 46, 43]`）。**判据裁定 rc=1 FAIL**：C1 有效窗 2、配对差 None、中位 **-9.0** < 下限 -2；C0 FAIL（`w165`）；C5 = **「缺口跨窗复现」**；C6 PASS（步数 9/9 `[13, 7, 14, 13, 7, 7, 7, 7, 7]`）。**候选①(第四窗集)**：有效窗 7→**9**；池化 D 中位 **-7**、极差 **15**、符号 {'neg': 7, 'pos': 0, 'zero': 2}、**p=0.0156** ⇒ 预注册 C5b 规则判 **「摆动 ≥ 效应 ⇒ 该轴非承重变量、定案关闭」**（符号面稳定、量级面未分离 ⇒ **不再加窗求效应**）。**候选②**：`TIMEOUT` 8 例（`w155-r2` 单跑次）三阶复跑 ⇒ `{'NONCONVERGENT': 3, 'NONCONVERGENT_AT_T10': 5}`（T=10s 3/3 达上限 ∧ T=60s 仍达上限 ⇒ **不收敛**，非「慢」；对照 4 例秒级、3 次同形；冻结快照读前读后 sha 同值）。**候选③**：27 产品跑次分类 `{'OK_RC0': 4, 'EXHAUSTED': 19, 'SELFTEST_UNMET': 3, 'NO_ARTIFACT': 1}`；`NO_ARTIFACT` **单例** `r587/w162/agentD-r3` 定因 = **契约块结构不闭合** ⇒ 严格解析在读至 **byte 6455** 的 `{` 处落「期望属性名」，与产品自报 `BytePositionInLine: 6455` **逐字节对齐（delta=0）** ⇒ `stage=contract`/`rc=4`（`src/agent/r1/R1Pipeline.cs:147`）⇒ `steps=0` ⇒ 零文件；成对控制 `has_teeth=true`。**候选④**：轴 A **恒等复刻通过**；轴 B 把 `UNCLASSIFIED` 18→**2**，但**对照组判别力 gap=0.007**（0.882 vs 0.889）⇒ 只作描述性登记。**候选⑤**：`NO_ARTIFACT` 的 `0/58` **计入配对** + 同窗 `denominator_class` 单列点名（1/27=3.7%）；`unreliable` 只留给真值自身失分窗；**改判据面写法而不动前置器语义**。**C2 成本三列（一律标「参考（未可验收）」）**：调用 66 vs 18 / 新算 prompt 30790 vs 4260 / completion 37046 vs 40447（按跑次归一 22.0 vs 2.0 / 10263 vs 473 / 12349 vs 4494；9 vs 3 ⇒ 禁比总量）/ 命中率 v_all 0.96 vs 0.98、v_incr 0.97 vs 0.98。**自捕 2 件（均未放宽判据）**：① 首跑 `noartifact_cause` 正控翻红（提取口径过贪 ⇒ rc=0 块读成 `Extra data`）⇒ 改平衡括号切读，首跑留档不翻案；② R587 `missing_wythoff_py` 口径（键存在性 ≠ 值缺失）⇒ 修正并登记。**诚实边界**：① 铁律 11 rc≠0 ⇒ 成本列不得作验收依据；② 候选④ 与结果面交叉 max|gap| 已入档；③ 候选③ 字符级病因未定因（残余）；④ 本轴定案关闭，不再加窗。轮志 `eval/rover/r588/report-r588.md`、预注册/DAG：`eval/rover/r588/{prereg-r588.json,dag-r588.md}`、台账 `eval/capability/kpi.jsonl`（R588）。

- **下轮候选 (R589)**: ① **本轴（产品 vs 外部真值质量缺口）定案关闭的处置裁定**（预注册规则已触发「摆动 ≥ 效应」；三种续法会产出不同交付物: (a) 换判据面=**整题全对率/按族分列**后同件复跑 (b) 停止加窗、直进产品侧修复（须用户放行产品改动）(c) 换更长的真任务题面（同件不可比 ⇒ 新基线））—— **须用户裁定**；② 候选③ **字符级**最小化复现（把契约块按元素二分定位首个使解析器偏离的元素；若归因到模型侧转义，A 类占比给出「加厚哪一段 prompt」的收益上界）；③ 真值臂成本异常定因（本轮 66 调用 vs R587 17；用 adapter per-call dump 时间轴 + `finish_reason` 分布，判「长命令 yield 轮询」占比；只读）；④ 「自报期待 vs 外部用例」脱钩量化（`w164-r2` 拿到 58/58 却 `rc=5`；统计 27 跑次里 `rc≠0 ∧ cases_pass=58` 的占比，只读）；⑤ 候选④ 子类的**结果面判别力**：per-tag `cases_pass` gap 已落盘（max |gap| 见 `subspec-v2-r588.json`），若 ≈0 则该分类轴整体降为描述项。

- **R589（判据面切换轮 · 只读并池：`R585–R588` 四窗集在盘机械判分件；零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关）**: 
**修改点** ① 并池器 `eval/rover/r589/pool_taskface_r589.py`（两面重算 + 按族 + 配对 + C6/C7/C10/C11；
器具自捕 3 件：`cases.txt` 读法漏 `FAIL <reason>` 行 ⇒ 15 行读空 rc=3、负控首版两侧同步位移 ⇒ 假阴性、判别力成对控制混用两仪器读数 ⇒ 判据恒不可行）；
② 起手闸 `gate_r589.sh`（MARGIN 由 R588 实测振幅派生）+ `disc_pair_r589.sh`（同仪器可比修后 rc=0）；
③ 候选② `charlevel_bisect_r589.py`；④ 候选③ `codex_cost_cause_r589.py`；⑤ `readonly_fingerprint_r589.py`（与并池器同指纹口径, 直接 import）；⑥ `finish_r589.py` + `docs_blocks_r589.py`。
**读数**（12 窗 × 48 跑次 × 58 例；题集 sha `e0c667c2a313c04b`、二进制 sha `4b70fd7cdb39`）：**有效窗 9**（真值自身失分窗 w154, w161, w165）；
**整题全对率面**中位 **-0.6667** / 极差 **1.0** / 符号 {'neg': 8, 'zero': 1, 'pos': 0} ⇒ **判据 C1 PASS「整题面缺口成立」、rc=0**；
**用例级面**中位 -7（同向）；**按族分列**：life all-pass 0.9722（真值 12/12、失败原因 rc=1×14）；nim all-pass 0.9722（真值 12/12、失败原因 rc=1×15）；sub all-pass 0.9722（真值 12/12、失败原因 rc=1×14）；wythoff all-pass 0.3889（真值 9/12、失败原因 stdout_mismatch×174, rc=1×58, TimeoutExpired×8） ⇒ 缺口集中在 `wythoff` 单族。
**候选②** 字符级最小复现：最小删除集 [7]（基数 1），下沉到 `plan` 元素第 6；栈 8 个未闭合 ∧ 补闭合不恢复 ⇒ 内层异常。
**候选③** 真值臂成本定因：调用 17→68（×4.0）、prompt 150360→1261783（×8.392）、`write_stdin` 占比 0.0588→0.0882 ⇒ 成本异常在 **单窗集中**（`r588/w165`）。
**候选④** 脱钩 9/36 = 0.2500；**候选⑤** 子类 gap max|gap|=0.0070 ⇒ 描述项定案。
**诚实边界**：零新跑次 ⇒ 不宣称任何降幅/增益；铁律 11 本轮重跑 rc=1（4/4 轮 · executable_and_correct=false；失败族 **wythoff 独占 3/4 轮**，与整题面按族读数同向 = 独立第三面）；(b)/(c) 待用户裁定。
轮志 `eval/rover/r589/report-r589.md`、预注册/DAG `eval/rover/r589/{prereg-r589.json,dag-r589.md}`、台账 `eval/capability/kpi.jsonl`（R589）。

- **下轮候选 (R590)**: ① **本轴缺口定案后的处置裁定（待用户放行）**：(b) 直进产品侧修复（须放行 ⇒ 本轮未动产品源码）(c) 换更长题面=新基线（会改可比性 ⇒ 非可自决）；② **按族定因继续下沉**：`wythoff` 单族整族塌陷 ⇒ 从 C8 已定位的「`plan` 元素内过度转义」出发，量「该形态在 12 窗 36 产品跑次的出现率」与「与整族塌陷的相关性」（纯只读；出现率 0 则本候选自证无价值，应改查落点非冷点主因）；③ **判据面入册**：把「整题全对率 + 按族分列」写进 `docs/external-reference-harness.md` 判据 v3（v2 保留、作废登记，跨版本禁相减）；④ 起手闸余量条款按 R589 实测振幅重派生；⑤ 前置器在 project 布局下的**耗时**（本轮 4 轮重跑未跑完 ⇒ 只读轮可用「各轮自身已登记读数 + 抽样复跑」替代，写成口径再动器具）。


- **R590（只读定因/入册轮：候选 ②③④⑤ 并轮；零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关）**:
**修改点** ① 候选② 普查器 `eval/rover/r590/escape_form_census_r590.py`（契约块 `contract_span` **import** R589 器具，禁重写第二份；器具自捕 #1: v1 把「契约块未闭合」支读成空串 ⇒ 同一条跑次在 POS 控制与 `scan_run` 上给出**互相矛盾**的形态读数 ⇒ 修后未闭合支也纳入形态判定并另记 `span_balanced`；v1 读数留档 `escape-census-r590-v1spanpath.json`，**不翻案**）；② 候选④ `gate_margin_r590.py` + `gate_r590.sh`（派生自 r589 版，**只改余量条款这一处自由度**）；③ 候选⑤ `precond_cost_r590.py`（守恒判据 = 复跑结论 == 该轮自身已登记 `precond.rc`）；④ N5 `readonly_fingerprint_r590.py`（与 r589 并池器同口径 import；对照物升级为**跨轮不变式**）；⑤ 候选③ 判据面入册 `docs/external-reference-harness.md` §12.3。
**读数**（R585–R588 在盘件；题集 sha `e0c667c2a313c04b`、二进制 sha `4b70fd7cdb39`）：**候选② 否证** —— 目标形态（契约块内双反斜杠 + n）出现率 **0.9722（35/36，近乎普遍）**、Δ_allpass **0.4000** < 阈值 **0.5833**（= R589 实测族间落差 0.9722 − 0.3889）⇒ **与整族塌陷非承重**；唯一缺档跑次（`r586/w159/agentD-r2`）**同时**是「契约块未闭合」跑次 ⇒ 该轴与「解析失败」**共线**、无独立可分面 ⇒ 依预注册决策树**转记落点非冷点主因**（post-hoc：`wythoff` 失败由 `stdout_mismatch×174` 主导，与 §12.2 的 `MOVE_NOT_COLD` 主因同向）；成对控制 POS（`r587/w162/agentD-r3`，form_n=59）/ NEG1（合成正确转义⇒否）/ NEG2（合成注入⇒是）全翻面（`has_teeth=true`）。**候选④ 三处缺陷一次收口** —— ① 只读轮（零臂）无在飞窗 ⇒ 条款 `prev_swing` **取值未定义**（缺分支，非数值问题）；② 条款写明「起手前样本极差 ≤ 50MB」而 r589 实现**未落**（r589 实测极差 361MB 仍被放行）⇒ 本轮落成 fail-closed 并行使（n=3 / 顶棚 2748 / 极差 **3MB** ⇒ 过）；③ R589 的 361MB 系**清场跳变**（两个样本分别落在清本会话工具子进程**之前/之后**：2480→2726MB，**+246MB 复现**）⇒ 非同态、不可当宿主振幅用，回退源 = 最近一次同态在飞窗振幅 R588 = 314MB，稳健性表证明换源**不改结论**；`cap` 在 2494–2900 全档**恒 binding** ⇒ **振幅项退化**（收紧的是上界、不是下界）；**真机行使 rc=2 fail-closed「窗口不可开」**（`cap = 2748 − 2650 − 60 = 38 < floor 60`）⇒ A1/A2 与判别力成对控制**未行使**（fail-closed 是**正确行为**、不记缺陷，但本轮因此**无闸 PASS 读数**）。**候选⑤** —— 前置器 **4/4 完成**、守恒判据 `all_consistent=true`（复跑结论与各轮自身 `runs/<r>/precond.rc` **逐轮一致**）、耗时（**墙钟信息字段**）相邻完成间隔 `[22,20,21] s` / 4 轮窗口 63 s（第 1 轮起点无锚 ⇒ 只测 2..4 轮）；**冲突定因（本轮只读定位）**：`eval/rover/r589/finish_r589.py` 的两处打印（:252 / :361）读的是它**自己从未回填的收集字典** `pre_rc` ⇒ 写「in_flight / 0/4」，而同报告另一处写「4/4」⇒ 同轮两处读数**都不是「回读磁盘归档」**（与「计数类读数取外部真值、不采信内存账本」同族）；R589 的「0/4 / 未全数完成」读数**不翻案**（原样留档），只作口径修正登记。**候选③** 判据 v3 入册（整题全对率 + 按族分列；v2 **判决面作废登记**、保留为用例级参照 + 派生器口径来源；**跨版本禁相减**；**事后入册**披露）。**只读性** 2210 文件、**跨轮不变式**成立（含 mtime ⇒ 任何写都会改 mtime）。**形式门禁** **14/14**（Failed 0 / Passed 14 / Skipped 0）· 本轮零 `src/` 改动、零登记表改动 ⇒ **不造** `owner_round=R590` 的 capability 登记行（与 R588/R589 同处置）。
**诚实边界**：零新跑次 ⇒ **不宣称任何质量/成本降幅/增益**；候选②为**否证**结论且属只读相关（唯一缺档组 n=1 ⇒ 不报显著性）；候选④ 本轮**无闸 PASS 读数**（「窗口不可开」不记缺陷、也不得读成「条款已收紧生效」）；候选⑤ 耗时只作信息字段；候选③为**事后入册**；候选①（(b) 直进产品侧修复 / (c) 换更长题面）**待用户放行**，本轮未推进。
轮志 `eval/rover/r590/report-r590.md`、预注册/DAG `eval/rover/r590/{prereg-r590.json,dag-r590.md}`、台账 `eval/capability/kpi.jsonl`（R590）。

- **下轮候选 (R591)**: ① **本轴处置裁定（待用户放行）**：(b) 直进产品侧修复（须放行 ⇒ 本轮未动产品源码）(c) 换更长题面=新基线（改可比性 ⇒ 非可自决） ② **落点非冷点主因定因**（候选②已把「过度转义」形态轴**否证** ⇒ 靶点转入 `MOVE_NOT_COLD`：从 §12.2 的 67/131 份额出发，只读量「落点谓词的真值 vs 产物」逐例差，判「算法错」还是「冷集构造错」；纯只读、零产品改动） ③ **起手闸「只读轮分支」入册**（把 R590 派生的 `prev_swing_effective = max(在飞窗振幅, 起手前采样振幅)` + 「极差 ≤ 50MB」fail-closed 条写进 `docs/external-reference-harness.md` §12.1.1；v2 保留、标注禁相减） ④ **前置器抽样复跑口径入册**（守恒判据「复跑结论 == 该轮自身已登记读数」+ fail-closed 条件；器具面零开发） ⑤ **判据 v3 的第二窗集行使**（`−0.34` 阈值只在一个窗集上行使过 ⇒ 分辨率未经复核；同件同题集、零产品改动 ⇒ 须跑新窗 = 真机臂）。

- **R591（判据 v3 **第二窗集行使** · 真机臂轮 `w166..w168` × 外部真值 codex 同题面；零产品源码改动 / 零新增夹具语义 / 零新增开关）**: **修改点** ① 判据 v3 器具 `eval/rover/r591/pool_taskface_r591.py`（**import** R589 逻辑源，禁重写第二份；只参数化窗集 + C0 期望值）；② 候选② 只读定因器 `eval/rover/r591/landing_predicate_r591.py`（落点谓词层 (a) vs 冷集构造层 (b)）；③ 候选③ 入册 `docs/external-reference-harness.md` §12.1.2（余量来源分支 / 极差 ≤50MB fail-closed / `cap binding ⇒ 振幅项退化`）；④ 候选④ 入册 §12.4（抽样复跑口径：守恒判据 = 复跑结论 == 该轮自身已登记 rc，耗时只作信息字段）；⑤ 起手闸 v3 三件（3 样本取 min + 极差 ≤50MB fail-closed + `cap_binding` 记法）；⑥ 新增 15 例 wythoff 冻结用例**副本**（源文件 sha `270128eb…` 一字未改）。**真机读数**（3 窗 `w166..w168`，每窗 真值×1 ＋ 产品默认档×3 = 12/12 跑次 × 58 例；题集 sha `e0c667c2a313c04b`、二进制 sha `4b70fd7cdb39` 前后一致）：**主判据 v3（整题全对率 + 按族分列）** 有效窗 **1/3**（`w167` 真值 47/58、`w168` 真值 56/58 ⇒ `unreliable` 剔除配对并单列）⇒ 配对差 `w166 = −1`、中位 **−0.6667**、负号窗 1 ⇒ 规则 **PASS（缺口成立）**，**但 n=1 ⇒ 按 §12.3 纪律不作能力结论**，只登记「阈值 −0.34 的分辨率未能在第二窗集上被检验」；按族 all-pass 率（产品侧）`life/nim/sub` 0.9722 三族持平、`wythoff` **0.3889 → 0.4444**（失败由 `stdout_mismatch` 主导）。**用例级参照（v2 判决面已作废，仅同向）**：中位 −1 ⇒ C1 未达、`kpi_r591.py` **rc=1**。**C5 缺口复现**（与 R588 集**并列不相减**）：`prev_D [−7,−11]`（中位 −9.0）vs `this_D [−1]` ⇒ 方向一致、量级漂移、区间不重叠。**C5b 摆动 vs 效应**（池化 9 有效窗）：效应中位 **−7**、摆动极差 **15**、符号 {neg 7, zero 2, pos 0}、精确检验 p **0.0156** ⇒ **摆动 > 效应 ⇒ 该轴非承重变量、定案关闭**。**成本三列（铁律 11 rc=1 ⇒ 一律标「参考（未可验收）」）**：调用 **12 vs 59** / 新算 prompt **3,189 vs 16,367** / completion **29,727 vs 18,694** / 命中率 v_all **0.97 vs 0.99**、v_incr **0.94 vs 0.99**；两侧跑次数不等（9 vs 3）⇒ **禁比总量**，按跑次归一 1.33 vs 19.7 / 354 vs 5,456 / 3,303 vs 6,231。**C6 步数列 PASS**（9/9 非空；`steps_executed [0,7,8,13,7,7,14,14,7]`）。**起手闸**：`prev_swing_effective = 314MB`（同态在飞窗 r588 n=189）、`ceiling_min_of_3 = 2788`、起手前极差 **0MB**、`REQ = 2728`、A1/A2 真机 **PASS**（2814/2812MB）、**判别力成对控制 rc=0**、`leak-selfcheck rc=0`；`cap = 78 < prev_swing` ⇒ **`cap_binding = true`（振幅项退化：收紧的是上界而非下界）**。**候选②（定因器）**: 12/12 跑次可判、oracle 一致 `True`；失败例次分桶 `A_landing_loose 33 / B_coldset 18 / D_delivery_or_shape 18`（0.4783 / 0.2609 / 0.2609）、层分布 12/12 = (b)，**但成对控制无牙**（POS 夹具：冷集正确 ∧ 落点谓词取反 ⇒ 被判 (b)、防恒真 False）⇒ `has_teeth=false`、**rc=2 ⇒ 定因不成立、不入结论**（登记件留待修判定器后重跑，→ R592 已定因：分层只用 `C_prod == C_true` 单条件 + 冷集比较域不对称）。**器具自捕 5 条（零判据放宽）**：`PY_MEM unbound`（`set -u` 中止 ⇒ 闸后零臂读数）/ 判分 60s **无上界**（改 `AGENTFRAMEWORK_GRADE_TIMEOUT`，默认 60 保形；良构树 10s≡60s **逐用例逐位一致** 作零回归控制）/ 逐跑次工作区只建不清 ⇒ 残留树被续写（加 `rm -rf`）/ 受限窗口目录被池化器当窗（移出轮目录后 `runs=12/12 windows=3 issues=0`）/ 池化器 `exp_runs` 漏 ×3（修后 set1 **48/48 复现 R589 登记值**）。**被污染/中止跑次留档不翻案**：v1（`w166` 判分无界中止）+ v2-restart1（`w166` 残留树续写 76s rc=5 ×3、`w167` 空），两目录保留（`$HARNESS/runs/r591-evidence/w166-contaminated-v2/…`）。**形式门禁/只读性**：零 `src/` 改动、零登记表改动 ⇒ 依 R588–R590 同处置**不造** capability 登记行；C11 只读面 sha 清单前后一致。**诚实边界**：① n=1 有效窗 ⇒ 主判据只出「规则 PASS」不出能力结论；② 铁律 11 rc=1 ⇒ 三列成本不得作验收依据，completion 高于真值单列；③ 候选② 未过控 ⇒ 主因裁定不作结论；④ **（R592 事后追加）同机争用**：本窗口内宿主曾被 **2 个遗留孤儿子进程**（`python3 -B -m games {nim,wythoff}`，各 ~95% CPU，起于 07:43:43 / 08:07:05，2 vCPU 宿主）吃满 2 核，R592 按已核实 pid 清场 ⇒ 本窗口读数可能受同机争用影响，**留档不翻案**、也不得读成「已修复」。**轮志**：`eval/rover/r591/report-r591.md` · 预注册/DAG：`eval/rover/r591/{prereg-r591.json,dag-r591.md}` · 判据：`eval/rover/r591/{verdict-r591.json,taskface-pool-r591-set2.json,taskface-pool-r591-set1.json}` · 定因：`eval/rover/r591/landing-predicate-r591.json` · 条条款：`eval/rover/r591/gate-margin-r591.json` · 入册：`docs/external-reference-harness.md` §12.1.2/§12.4/§12.5 · 台账：`eval/capability/kpi.jsonl`（R591）。


- **R592（R591 收口 + 候选② 定因器重钉：器具有牙修复；只读 / 零产品源码改动 / 零新臂 / 零远端调用）**: **修改点** ① 定因器 v2 `eval/rover/r592/landing_predicate_r592.py`（先量再改：`probe_v1_defect_r592.py` 在单树上量出 v1 三处缺陷 D1 冷集比较域不对称（网格仅 `a≤b` vs oracle 双向对 ⇒ `C_prod`/`C_true` 恒 9/9 对称差 ⇒ `cold_set_equal` 恒 False）/ D2 跑次级分层只用 `C_prod==C_true` 单条件 ⇒ 控制无牙 / D3 网格输出只分 WIN/非 WIN ⇒ 非法或空输出并入「声明冷集」（实测 `cold_only_prod=350 ≈ 全网格`））；v2 修器具面三处：两侧过 `canon=(min,max)` / 分层改**两个行为信号**机械组合（`V_land>0` ⇒ (a)；`V_land==0 ∧ C_prod≠C_true` ⇒ (b)；两者皆无 ⇒ (c)）/ 网格三分 `WIN/LOSE/ERROR`（只 LOSE 计入声明冷集）；② 控制三件改**行为可分**（`OK` 真值冷集+正确落点+lexmin / `POS` 落点谓词取反 / `NEG` Nim 式信念）；③ 子进程 `start_new_session=True` + `killpg` **进程组**收口（v1 只杀直接子进程 ⇒ R591 实测 2 孤儿各 ~95% CPU 存活 66–90 min，本轮按已核实 pid 清场）；④ R591 遗留收口：轮志 `eval/rover/r591/report-r591.md` + 本块（含「R592 事后追加·同机争用」边界）。**真机读数（只读重放，44/44 跑次可判 `err=0`，窗集 = `r585 w154–w156 / r586 w157–w159 / r587 w160–w162 / r588 w163–w165 / r591 w166–w168` ×3）**：**只读性 True**（44 份快照树 + `cases-r521.json` sha256 前后**逐位一致**）、oracle 一致 `True`、残留子进程 `0/0`；**成对控制有牙**（`OK → (c)` 例 15/15 ∧ `C_prod==C_true` ∧ `V_land=0`；`POS → (a)`（`V_land=347`）；`NEG → (b)`）、**非平凡 True**（控制面 3 形态互异）、**确定性 ×2 逐位相同**（`--controls-only` 复跑 sha `1ae24ebb…`）⇒ **rc=0**；**负控成对**：同控制面上 v1 = `POS:(b) / NEG:(b)`（同层 ⇒ 无牙）`rc=2`（取证 `eval/rover/r592/negctl-v1-r592.json`，命令与判定已登记进预注册）。**层分布（44 跑次）**：`(b) 冷集构造层` **22** / `(c) 本轴外` **19** / `(a) 落点/选择谓词层` **3**；**失败例次分桶** `B_coldset` **184（0.6595）** / `D_delivery_or_shape` **69（0.2473）** / `A_landing_loose` **20（0.0717）** / `A_selection_order` **6（0.0215）** ⇒ 主因 = **`B_coldset`**。**同窗集（r591 9 跑次，与 v1 同一窗面）**：`(c)` 5 / `(b)` 4 / `(a)` 0、分桶 `B_coldset 36（0.6667）` / `D_delivery_or_shape 18（0.3333）`。**结论（R591 候选② 定因成立）**：主因在**冷集构造层**，「落点/选择谓词错」形态**基本否证**（(a) 3/44 跑次、例次份额 0.0717；同窗集 0/9）；第二大项 `D_delivery_or_shape` 属**本轴之外**。**器具自捕 3 条（零判据放宽）**：`--controls-only` 下非平凡性取自轮次面 ⇒ 面为空 ⇒ 自检恒红（改以控制臂形态为准 + rc 语义显式分层 0/2/3）/ `main()` 末 `return 0` ⇒ **rc 打印但不进退出码**（改 `return rc`）/ `max(shares, key=shares.get)` 类型噪音（改 `lambda`）。**形式门禁 14/14**（Failed 0 / Passed 14 / Skipped 0）；零 `src/` 改动、零登记表改动 ⇒ **不造** capability 登记行（与 R588–R591 同处置）。**诚实边界**：① v1 的 `12/12=(b)` 是 D1 **恒真退化**产物，与 v2「(b) 主导」**不可互为证据**（巧合不采信）；两轮跑集不同（v1 `r591`-only 9 vs v2 全量 44）⇒ **禁相减、只并列**；② 定因面为**只读产物诊断**（副本上重放产物行为）⇒ **不构成能力验收**、不得回写成「产品已修」；③ 44 跑次横跨 5 个历史窗，`r587` 只有 8 跑次；④ 本轮**零远端调用** ⇒ tokens 三列 **未测**；⑤ `V_int` 只作诊断、不作分层触发。轮志 `eval/rover/r592/report-r592.md`、预注册/DAG `eval/rover/r592/{prereg-r592.json,dag-r592.md}`、读数 `eval/rover/r592/landing-predicate-r592.json`、台账 `eval/capability/kpi.jsonl`（R592）。

- **下轮候选 (R593)**: ① **本轴处置裁定（待用户放行）**：主因已定位到**冷集构造层** ⇒ 产品侧修复属改 `src/` ⇒ 未放行不动 ② **`D_delivery_or_shape`（0.2473）第二大项只读定因**（本轴之外：交付形态 / 网格非法输出；零产品改动）③ **定因器 v2 扩到 codex 侧跑次**（`--codex-too`）：判「冷集构造错」是我方缺陷还是题面歧义（题面-判据一致性纪律；只读）④ `V_int` 诊断项**先落分布**再谈阈值（不许预建）。

- **R593（只读定因并轮：候选 ②③④ 并轮 —— `D_delivery_or_shape` 桶机械细分 / 定因器扩 codex 侧跑次 / `V_int` 先落分布；零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关）**: **修改点** ① 定因器 **v3** `eval/rover/r593/landing_predicate_r593.py`（**import** v2 helpers（`canon`/`legal_moves`/`run_one`/`probe_grid`/`synth_fixture`/`audit_strays`/`sha_tree`/`WIN_RE`）+ R562 oracle/classify，**禁重写第二份**；只加三处读数面：**D 桶机械细分**（`D1_empty_or_error`/`D2_move_shape`/`D3_move_illegal`/`D4_label_mismatch`/`D5_win_unparseable`/`D6_other`，并把 D1 按**原因**二分 `nonzero_rc` vs `empty_body`）、`--codex-too` 同器具同口径纳入 codex 跑次、`V_int` 直方图（**不设阈值、不作触发**））；② 追加只读探针 `eval/rover/r593/d1_stderr_probe_r593.py`（`v2.run_one` 的**同语义**变体：唯一差别 = 同时返回 stderr；超时仍判 `rc=124` + 空正文 ⇒ 重放可**逐例与产物侧 rc/空正文对账**）；③ 控制扩到 **8 件**（`OK/POS/NEG` + `D_EMPTY/D_RC/D_SHAPE/D_ILLEGAL/D_LABEL`）。
**真机读数（只读重放 44 跑次 agentD（5 窗集 ×3）+ 15 跑次 codex 同窗集；`err=0`）**：**只读性 True**（59 份快照树 + `cases-r521.json` sha256 前后逐位一致、`src/` 树 sha 前后一致）、oracle 一致 `True`、残留子进程 `0/0`；**成对控制有牙**（8 件**落点唯一**：(桶[,原因]) 签名互异 —— `OK→(c)` 例 15/15 ∧ `C_prod==C_true` ∧ `V_land=0`；`POS→(a)`（`V_land=347`）；`NEG→(b)`；`D_EMPTY→D1+empty_body`；`D_RC→D1+nonzero_rc`；`D_SHAPE→D2`；`D_ILLEGAL→D3`；`D_LABEL→D4`）∧ **旧粒度对照臂**（同 5 件 D 控制在 v2 单一 `D_delivery_or_shape` 粒度下**互异桶数 = 1 ⇒ has_teeth=false** ⇒ 证明细分有分辨率、非装饰）∧ **确定性 ×2 逐位相同**（`--controls-only` 复跑 sha 相同）∧ **守恒 `Σ D_sub == D_total`**（逐跑次 + 全量）∧ **零回归对照臂 True**（A/B 级桶总额与逐跑次层分布与 R592 登记值**逐位复现**：`B_coldset 184 / A_landing_loose 20 / A_selection_order 6`、层 `(b) 22 / (c) 19 / (a) 3`）⇒ **rc=0**。
**候选②（D 桶细分定因）**：D 桶 **69 例次（份额 0.2473）** 拆为 `D1_empty_or_error` **66（0.9565；原因 100% = `nonzero_rc`）** + `D3_move_illegal` **3（0.0435）**，`D2/D4/D5/D6 = 0` ⇒ **第三刀定因**：D 桶主因**不是**「非法着法 / 词标错 / 输出畸形」而是**子进程非零退出**（执行/交付形态面）。追加探针把 66 例次定因到具体形态：产物侧 rc 分布 `{1: 58, 124: 8}` ⇒ **58/66 = 带异常退出、8/66 = 60s 挂死超时**；**形态族**：`AttributeError: module 'games.wythoff' has no attribute 'solve'` **30**（= **2 个整跑次** `r588/w163`、`r591/w166` 各 15 例全灭 ⇒ 交付物未暴露入口）、`IndexError: list index out of range` **15**、`TypeError: 'NoneType' object is not subscriptable` **11**、`TIMEOUT_60s` **8**、`TypeError: %d format: a real number is required, not NoneType` **2**；探针逐例重放与产物侧 rc/空正文**零不一致**（`mismatch=0`，66/66）⇒ 重放可信、rc 口径与产物侧同源；⇒ **定因收口**：D 桶最大单一形态 = **交付物未暴露入口**（2 整跑次全灭），其次下标记/None 类异常与挂死 —— **均属执行/交付形态面，非题目语义错**。**结论**：`D_delivery_or_shape` 的 0.9565 属**执行面崩溃/挂死**（非语义错）；`B_coldset 0.6595` 仍是**第一主因**（未变）。
**候选③（codex 侧同口径对照）**：codex **15/15 跑次**可判（同题集、同机械判据、同冻结夹具）。**跑次率为主口径**：冷集构造层 **我方 22/44 = 0.5** vs **codex 4/15 = 0.2667**；D 桶例次份额 我方 0.2473 vs codex 0.1200。**同败窗 3/15**（`r587/w161`、`r588/w165`、`r591/w167`：codex 层 (b) ∧ 我方 ≥2/3 跑次 (b)），**但三窗的失败用例集合与我方任一跑次均非逐字相同**（`failset_identical = false`）⇒ 按「题面-判据一致性」纪律（**强判据 = 两侧同败 ∧ 失败集合逐字相同**）**不成立** ⇒ **不判夹具/题面缺陷**，只登记「**系统性同踩点 3/15**」；我方独有 (b) 窗 **9 个**（`w155/w156/w158/w159/w162/w163/w164/w166/w168`）、codex 独有 **1 个**（`w154`）。**质量面（同窗配对、只读重算）**：整题全对率 **我方 0.4091（18/44） vs codex 0.6667（10/15）**；逐窗配对差（我方三跑中位 − codex）**中位 -3**、**极差 17**；逐窗 `[2, -8, -3, 0, -3, -15, 0, -3, -6.5, -7, -11, -9, -1, -1, 2]` ⇒ 缺口成立且方向对我方不利。
**候选④（`V_int` 先落分布）**：直方图 我方 `{0: 25, 1: 1, 4: 1, 5: 2, 6: 2, 10: 1, 11: 2, 13: 1, 25: 1, 29: 1, 48: 2, 94: 1, 115: 1, 169: 1, 235: 1, 350: 1}`、codex `{0: 11, 2: 1, 19: 1, 50: 1, 350: 1}`；**交叉校验**（两条独立路径）：`cold_set_equal=True ∧ V_int>0` 的跑次 **0/59** ⇒ 与「真冷集对任何合法着法封闭」自洽；**不设阈值、不作触发**（预注册禁止），只登记为下轮候选。
**铁律 11**：`python3 eval/rover/r507pre/exec_precondition.py --round r593` ⇒ **rc=3（`DISCOVER_FAIL`，无两侧产出物）**——本轮零新臂 ⇒ 前置器**不适用**，**不作任何降幅/增益宣称**（tokens 三列 = 未测，与「未测到 ≠ 测过通过」一致）。
**形式门禁 14/14**（Failed 0 / Passed 14 / Skipped 0）；零 `src/` 改动、零登记表改动 ⇒ **不造** capability 登记行（与 R588–R592 同处置）。
**诚实边界**：① 只读产物诊断（副本上重放产物行为）⇒ **不构成能力验收**，不得回写成「产品已修」；② D1 的 66 例次来自 44 跑次（横跨 5 窗集）⇒ **非独立样本**；③ 同败窗 3/15 只作「系统性踩点」登记，**强判据不成立 ⇒ 不据此改题面/夹具**；④ 质量面为**同快照重算**（非新跑次）⇒ 与真机成本面**不可混用**；⑤ **跨轮禁相减**：R592 读数只用于零回归对照臂的逐位复现；⑥ `V_int` 只作诊断、不作分层触发。
轮志 `eval/rover/r593/report-r593.md`、预注册/DAG `eval/rover/r593/{prereg-r593.json,dag-r593.md}`、读数 `eval/rover/r593/{landing-predicate-r593.json,kpi-r593.json,d1-stderr-probe-r593.json,verdict-r593.json}`、台账 `eval/capability/kpi.jsonl`（R593）。

- **下轮候选 (R594)**: ① **本轴处置裁定（待用户放行）**：主因 = **冷集构造层**（0.6595）＋ **执行面崩溃/挂死**（D 桶 0.9565）⇒ 产品侧修复属改 `src/` ⇒ 未放行不动 ② **降级为已闭合（R594 不再重做）**：58 例 `rc=1` 的 stderr 形态族**已在本轮落盘**（`AttributeError: … has no attribute 'solve'` 30 / `IndexError` 15 / `NoneType` 下标 11 / `%d` 2）；R594 改为**入口契约面只读定因**：判「2 整跑次缺入口」是**产物侧契约未暴露**还是**题面未写明入口名**（只读：比对裁判侧导入路径 vs 题面文字） ③ `V_int` 阈值化前先补**第二窗集分布**（扩跑次面）④ codex 独有 (b) 窗 `w154` 单窗只读定因 ⑤ **形态族按窗集分层**：`IndexError`/`NoneType` 是否集中在特定窗（只读，扩展本轮探针的按窗聚合）。

- **R594（只读定因并轮：入口契约面（候选②）+ 面读数并轮（候选③④⑤）；零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关）**: **修改点** ① `eval/rover/r594/entry_contract_r594.py`（题面原文抽取入口名/评分路径 + 判分器源码 argv 同源检查 + **全跑次面** `def solve` census（agent/codex 分列）+ 实测复现 + POS/NEG 副本控制 + 单点路径构造 + 非平凡性机检）；② `eval/rover/r594/face_readings_r594.py`（纯聚合：`V_int` 按窗集分层 + 2×2 列联 / codex `w154` 逐字段复算 + 层规则重算 / 形态族 × 跑次集中度；零回归对照臂与 R593 登记值**逐位复现**）；③ 轮志/台账/§7 块/§7 快照/improvements。**真机读数**：**候选② 入口契约面**（决定性）—— 题面明文要求 `solve(text: str) -> str`（True）∧ 评分路径 `python3 -m games`（×2）∧ 判分器实发 argv `-B -m games`（**同源**）∧ 判分器**无**直接导入；两侧 census **agent 2/44** 跑次缺 `solve`（均仅 `wythoff`，`r588/w163/agentD-r2`、`r591/w166/agentD-r2`）vs **codex 0/15**；实测复现两跑次 rc=1 ∧ stderr 尾行 `AttributeError: module 'games.wythoff' has no attribute 'solve'`，对照跑次 `r585/w154/agentD-r1` rc=0 ⇒ **裁定 `branch_product_contract=True` / `branch_fixture_defect=False`**：两跑次**自己的** `__main__.py` 都调用 `.solve` 而其**自己的** `wythoff.py` 只定义 `_win`/`_lose` ⇒ **产物自身契约自相矛盾**；题面/夹具分支被否证，两侧同败强判据（codex 0/15）**不成立** ⇒ 不判夹具/题面缺陷。**候选③**：`V_int` 按 15 窗集 × 两侧分层直方图落盘；交叉校验 `cold_set_equal ∧ V_int>0` = **0/59**；2×2 列联 agent `(T,0)=19/(F,pos)=19/(F,0)=6`、codex `(T,0)=11/(F,pos)=4` ⇒ **V_int>0 恒伴随冷集不等**；**阈值化未测**（需新跑次）。**候选④**：codex 独有 (b) 窗 `w154` 确为 (b) —— codex 声明冷集 **51** vs 真值 **10**（多 41，形如整行 `(0,1..6)` 被判冷）、13/15 通过、2 例 `B_coldset`；同窗 3 个 agent 跑次全 **15/15** 且层 `(c)` ⇒ 该窗缺口**属 codex 侧**（不得计入我方份额）。**候选⑤**：5 形态族中 **4 族 top-run 份额 ≥0.5（集中在单一跑次）**、1 族（`TypeError:'NoneType'` n=11/4 跑次，份额 0.455）散布 ⇒「执行面崩溃/挂死」形态**按跑次成簇**（`AttributeError` 30 = 2 跑次 / `TIMEOUT` 8 = 1 跑次 / `%d` 2 = 1 跑次）。**零回归/只读性**：A/B 级桶 `B_coldset 184 / A_landing_loose 20 / A_selection_order 6`、层 `(b)22/(c)19/(a)3`、`d_subs D1 66 / D3 3`、两侧 `V_int` 直方图与 R593 登记值**逐位复现**，`D_delivery_or_shape == d_total = 69`；59 跑次快照树 + 冻结用例 sha 前后一致（`411434e5f8939c3b`）；确定性 ×2 逐位相同。**器具自捕 2 件（零判据放宽、首跑留档不翻案）**：① `entry_contract_r594` v1 **路径层级错**（census 传 `g1` 而非 `g1/games`）⇒ 全跑次「全 missing」，与同轮 POS 控制直接矛盾 ⇒ 修法 = 单点路径构造 + 非平凡性机检（留档 `entry-contract-r594-v1pathbug.json`）；② `face_readings_r594` 首跑**打印面 KeyError**（读数面/打印面键名分叉）⇒ 修打印面不改读数面（留档 `face-readings-r594-v1printbug.json`；扩展列联前中间版 `face-readings-r594-v2.json`）。**形式门禁** **14/14**（Failed 0 / Passed 14 / Skipped 0）。**铁律 11**：`exec_precondition --round r594` ⇒ **rc=3 DISCOVER_FAIL**（零新臂 ⇒ 前置器不适用）⇒ **不作任何降幅/增益宣称；tokens 三列 = 未测**。零 `src/` 改动、零登记表改动 ⇒ 依 R588–R593 同处置**不造** capability 登记行。**诚实边界**：① 只读产物诊断 ⇒ 不构成能力验收、不得回写成「产品已修」；② 候选②定因到位但**产品侧修复仍待用户放行**（候选①）；③ `V_int` 阈值化**未测**；④ 形态族集中度为**跑次级**统计（44 agent 跑次横跨 5 窗集）⇒ 非独立样本；⑤ 跨轮**禁相减**（R593 读数只用于零回归对照臂）；⑥ `w154` 的 (b) 属 codex 侧 ⇒ 不计我方缺陷份额。轮志 `eval/rover/r594/report-r594.md`、预注册/DAG `eval/rover/r594/{prereg-r594.json,dag-r594.md}`、读数 `eval/rover/r594/{entry-contract-r594.json,face-readings-r594.json}`、台账 `eval/capability/kpi.jsonl`（R594）。

- **下轮候选 (R595)**: ① **本轴处置裁定（待用户放行）**：候选②已把「缺入口」定因到**产物侧契约自相矛盾**、候选④已排除 codex 窗 ⇒ 产品侧修复（`src/` 或题面外契约面）**须用户放行** ② **`wythoff` 冷集构造层定因继续下沉**：从 R592 的 `B_coldset 184（0.6595）` 出发，只读量「声明冷集 vs 真值冷集的集合差结构」（超出/缺失的方向与形态），判「Beatty 判定错」还是「边界处理错」 ③ **候选② 的姊妹面**：对**交付物自洽性**做只读普查（`__main__` 引用 vs 模块导出、4 模块 × 59 跑次的**契约一致性**，含非 `solve` 面）——本轮只查了 `solve` 单键 ④ `V_int` 阈值化前的**第二窗集分布**（须新跑次 ⇒ 真机臂轮，与主线对照合并跑） ⑤ 起手闸只读轮分支余量按 R594 实测派生。

- **R595（真机臂轮：判据 v3 **第三窗集**行使（w169..w171，codex 真值 ×1 + 产品默认档 ×3）+ 只读并轮（候选②③⑤）+ 候选④ `V_int` 第二窗集分布；零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集）**: **修改点** ① `eval/rover/r595/{run_r595.sh,kpi_r595.py,pool_taskface_r595.py,launch_r595.sh,derive_r595.py}` 派生件（只替换命名空间/窗集常量，判据逻辑源一字未改）；② `eval/rover/r595/face_r595.py`（候选②冷集集合差结构 + 候选③全属性契约普查 + 候选⑤起手闸余量派生）；③ 候选④复用 r593 同件定因器（`--rounds r595 --codex-too`）；④ 后处理重跑器 `rejudge_r595.sh`；⑤ 轮志/台账/§7 块/§7 快照/improvements。**真机读数**：**主判据 v3 第三窗集** set3（w169–171）**valid=2、中位 −0.5、负号窗 2 ⇒ PASS**（阈值 −0.34 写死；w170 因真值自身未全对标 unreliable、不进配对）；set1/set2 并列（9/−0.6667/8；1/−0.6667/1），set1 与 R589 登记件**逐位复现**；族 all-pass 率 `life`/`nim`/`sub` = 0.9722/1.0/1.0、**`wythoff` = 0.3889/0.4444/0.4444** ⇒ 缺口**只在 wythoff 族**、跨三窗集稳定复现。**成本三列**（参考·未可验收）：产品 18 调用 / 4,180 新算 / 39,526 completion，真值 45 / 23,709 / 21,140；命中率 v_all 0.98/0.90、v_incr 0.97/0.94（口径 = 中继 dump 时间轴）；产品 rc `[5,5,5,5,8,0,5,0,5]`、stage `expect_stdout_exhausted`×6 / `self_test_unmet`×1 / `done`×2。**候选②**（只读，零子进程）：由登记件集合字段重建 `D=(T\M)∪U`，守恒 **59/59**；agent **CONSISTENT 19 / B1 15 / B3 9 / B2 1**、codex **11 / 1 / 3**；控制四值互异（非恒真门）⇒ **重要修正**：冷集**并非普遍坏**（19/44 跑次逐点等于真值），R592 的 `B_coldset 0.6595` 是**例次份额**而非跑次份额。**候选③**：修 docstring 假属性后 59 跑次零不自洽，但 POS 控制**不翻面**（交付物走 `importlib` 动态派发 ⇒ 静态面结构性盲）⇒ **rc=2 器具缺陷单列，「0 不自洽」不得引用为结论**。**候选④**：r595 12 跑次同件定因器 ⇒ 层 `(b)6/(c)6`、`cold_set_equal` 6/6、`v_int_hist {0:10,38:1,26:1}` ⇒ `V_int>0` 仍非活触发面、**阈值化未测**；agent 90/135（`D_delivery_or_shape 24 / B_coldset 20 / A_selection_order 1`）、codex 40/45（全 `B_coldset` 5）；`zero_regression=false` 属口径错配的结构性红、单列不作结论。**候选⑤**：余量源 = r591 同态在飞窗采样（n=97、2713–2815MB ⇒ swing **102MB**）；本轮 attempt#1 **FAIL-CLOSED**（CEIL 2683）、attempt#2 **PASS**（CEIL 2788、margin 78（cap_binding）、REQ 2728）⇒ 条款有牙；起手前收口本会话 own-tool 子进程并记差（Δ113MB）。**器具自捕 3 件（留档不翻案、未放宽判据）**：① **缺冻结用例集 ⇒ 空心绿**（12 跑次判分全 Traceback ⇒ kpi 0/0 恒真、铁律 11 rc=1 同源；处置 = v1 整份归档 + **只重跑后处理不重测** + 补件 sha 与 R591 同源比对）；② `main_refs` docstring 跨行假属性；③ 候选③控制无牙。**形式门禁** **14/14**（Failed 0 / Passed 14 / Skipped 0）。**铁律 11**：`exec_precondition --round r595` ⇒ **rc=1 BLOCKED**（6 臂未全对）⇒ **全部质量/成本读数标「参考（未可验收）」**，禁作验收依据。零 `src/` 改动、零登记表改动 ⇒ **不造** capability 登记行。**诚实边界**：① set3 仅 2 个有效窗 ⇒ 摆动与 set1 同尺度比较后才可作趋势，跨窗集**禁相减**；② 铁律 11 rc=1 ⇒ 未过可验收前置；③ 候选②③④为只读/聚合面，不构成能力验收，候选①（产品侧修复）**仍待用户放行**；④ 候选③面**无牙**；⑤ 候选④零回归红为口径错配；⑥ 铁律 11 v1 读数不翻案，v2 并列在档。轮志 `eval/rover/r595/report-r595.md`、预注册/DAG `eval/rover/r595/{prereg-r595.json,dag-r595.md}`、读数 `eval/rover/r595/{taskface-pool-r595.json,kpi-table-r595.json,verdict-r595.json,gate-margin-r595.json,face-gate-r595.json,face-coldset-r595.json,face-census-r595.json,landing-predicate-r595.json}`、台账 `eval/capability/kpi.jsonl`（R595）。

- **下轮候选 (R596)**: ① **产品侧处置裁定（待用户放行）**：候选②已把份额修正为「例次而非跑次」、B1 15 例次簇机制可命名（双向差、非边界局限）⇒ 落点已收束到 `wythoff` 冷集构造器；产品侧修复**须用户放行** ② **铁律 11 可验收化**：`rc=1` 的 6 臂全部集中在 `wythoff` 族（`w169/r1 52/58`、`w169/r2 45/58`、`w170/r1 51/58`、`w170/r2 43/58`、`w170/codex 53/58`、`w171/r2 54/58`）⇒ 只读逐例归因（A 类 = 加厚 prompt 的收益上界）③ **候选③改制**：静态面在动态派发下无牙 ⇒ 改**行为面**口径（逐游戏 `-m games` rc/stderr census）并配两侧控制 ④ `V_int` 阈值化的**第三窗集**（须新跑次；本轮已扩到第二窗集） ⑤ 起手闸余量按本轮实测振幅（`run-samples` r595 面）重派生。

- **R596（真机臂轮: 判据 v3 **第四窗集** w172..w174 × 外部真值 codex + 只读并轮 候选②③④⑤；零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集）**: **主判据 v3** set4 valid=2 / 中位 -0.5 / 负号窗 2 ⇒ **PASS**（set1 {'valid': 9, 'median': -0.6667, 'neg': 8, 'pass': True} / set2 {'valid': 1, 'median': -0.6667, 'neg': 1, 'pass': True} / set3 {'valid': 2, 'median': -0.5, 'neg': 2, 'pass': True} 并列，禁相减）；族 all-pass `wythoff` {"life": 1.0, "nim": 1.0, "sub": 1.0, "wythoff": 0.5556}。**候选②（铁律 11 可验收化）** 桶池化 {"OK_两侧全过": 933, "A2_摆动带": 231, "E_真值败_我方部分": 26, "A_我方独败": 22, "B_真值独败": 4, "C_两侧同败": 2}（A 份额 0.0181 = 加厚 prompt 的收益上界）。**候选③** 行为面契约普查: agent ENTRY_FAIL 2/63 跑次、codex 0/21（POS 有牙=True）。**候选④** `V_int` 第三窗集: agent 层 {"(c) 本轴外": 5, "(b) 冷集构造层": 3, "(a) 落点/选择谓词层": 1}、`v_int_hist` {"0": 6, "350": 1, "102": 1, "25": 1}（阈值化仍未测）。**候选⑤** 余量源 r595 实测振幅 133MB ⇒ margin 71 / REQ 2721（cap_binding=True）。**成本三列（参考·未可验收）**: 产品 19 调用 / 4190 新算 / 46389 completion vs 真值 38 / 24802 / 16819；命中率 v_all None/None。**铁律 11 rc=1**（blocked 5 条）⇒ 全部读数标「参考（未可验收）」。轮志 `eval/rover/r596/report-r596.md`。

- **R597（真机臂轮: 判据 v3 **第五窗集** w175..w177 × 外部真值 codex + 只读并轮 候选②③④⑤；零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集）**: **主判据 v3** set5 **valid=1 / 中位 -0.3333 / 负号窗 1 ⇒ 不达 PASS 形态**（真值 w175/w176 自败 56/58 ⇒ 按 C0 unreliable 不进配对、禁筛窗；w177 有效 D_task=-0.3333；有效窗 1 ⇒ 判据无分辨率，不作能力结论）；族 all-pass `wythoff` set5=**0.7778**（set1 0.3889 / set2 0.4444 / set4 0.5556 并列，禁相减）。**候选②**（铁律 11 可验收化，r597 单窗集）桶池化 {"OK": 155, "A2_摆动带": 15, "B_真值独败": 2, "E_真值败_我方部分": 2, "A_我方独败": 0} ⇒ A 份额 0.0；交叉校验 696/0。**候选③** 行为面普查 r597: agent OK 9/9、codex OK 3/3（ENTRY_FAIL 0；POS 有牙）。**候选④** `V_int` 第四窗集: agent 层 {(c)8, (b)1}、`v_int_hist` {0:8, 10:1}（阈值化仍未测）；landing 零回归=False 属单窗集 scope 伪影，同器具对 r585..r591 历史全集复算 **match=True** ⇒ 器具完好。**候选⑤** 余量源 r596 实测振幅 168MB ⇒ ceiling 2835 / margin 125 / REQ 2775（cap_binding=True）⇒ A1/A2 PASS。**成本三列（参考·未可验收）**: 产品 18 调用 / 3719 新算 / 39146 completion vs 真值 17 / 12446 / 9536；命中率 v_all 0.98/0.92、v_incr 0.97/0.94（口径 = 中继 dump 时间轴）。**铁律 11 rc=1**（blocked 4 条，全落 wythoff）⇒ 全部读数标「参考（未可验收）」。**器具自捕 2 件**（留档不翻案）: ① pool C7 负控无靶（选择面 = agentD-r1 单臂 × set5 的 r1 零失败例）⇒ rc=2，禁手改判据凑绿 ② landing 零回归 scope 伪影（见候选④）。轮志 `eval/rover/r597/report-r597.md`。

- **下轮候选 (R598)**: ① **产品侧处置裁定（待用户放行）**：五窗集 wythoff all-pass 0.3889→0.7778 并列向好的方向摆动但全部「参考（未可验收）」且 set5 无分辨率；落点已收束到 `wythoff` 冷集构造器 ⇒ 修复须动 `src/`，未放行不动 ② **真值侧 wythoff 缺口归因**（只读）：w175/w176 codex 连续 56/58 且失败例同为 wythoff#43-public + wythoff#57-hidden ⇒ 判「题面对两侧同难」还是「真值臂自身漂移」（对 R585..R596 真值失败集合做只读普查） ③ **C7 负控选择面改制**（器具缺陷 ① 的修法预注册）：靶点选择从「agentD-r1 单臂」扩为「首个含失败例的产品臂」，配 POS/NEG 成对控制与零回归（先写后跑，禁事后改本轮读数） ④ `V_int` 阈值化**第五窗集**（须新跑次；目前四窗集 `V_int>0` 恒低） ⑤ 起手闸余量按 r597 实测振幅重派生。

- **R598（真机臂轮: 判据 v3 **第六窗集** w178..w180 × 外部真值 codex + 只读并轮 候选②③④⑤；零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集）**: **主判据 v3** set6 **valid=2 / 中位 -0.3333 / 负号窗 2 ⇒ 不达 PASS 形态**（距阈值 -0.34 差 0.0067；真值 w178 自败 56/58 ⇒ 按 C0 unreliable 不进配对、禁筛窗；有效窗 2 ⇒ 不作能力结论）；族 all-pass `wythoff` set6=**0.5556**（set1 0.3889 / set2 0.4444 / set5 0.7778 并列，禁相减）。**候选②**（真值侧 wythoff 缺口归因，只读普查 r585..r598 共 27 窗）: 真值失败**全部**落 wythoff（10/27 窗、38 例次；life/nim/sub = 0），失败集合 6 种（非常量）⇒ 判 **真值臂自身漂移**；「两侧失败集合逐字相同」窗 = 0 ⇒ 题面/夹具嫌疑**未现**；`wythoff#43-public + wythoff#57-hidden` 在 4 窗逐字重复（r596 w173 / r597 w175、w176 / r598 w178）；控制 NEG-A 确定性=True、NEG-B 非平凡=True、POS 注入 ③→①=True；rc=0。**候选③** C7 负控选择面改制（器具缺陷修法）: v1（保留不覆写）r1-only 选择面 ⇒ set5/set6 无靶 rc=2；v2（全产品跑次）靶点 set5 w176 / set6 w178 ⇒ has_teeth True、rc=0，**判定面差异全字段 NONE（6/6 窗集）**；`checks_posthoc`: rc 与判据判定脱钩（v2 下 set5/set6 rc=0 而 C1.pass=False），本轮不改、留档待下轮预注册。**候选④** `V_int` 第五窗集: agent 层 {(c)6,(b)3}、桶 {D 14, A 2, B 16}、`v_int_hist` {0:7, 25:1, 35:1}（**阈值化仍未测**）；codex 桶 {D 2}、层 {(c)3}；份额差 A +0.0625 / B +0.5 / D -0.5625；零回归=False 属单窗集 scope 伪影（历史全集 r585–r588+r591 复算 match=True ⇒ 器具完好（单窗集读法伪影已定因））。**行为面普查** r598: agent 81 跑次 {OK 73, ENTRY_FAIL 2, INTERNAL 4, TIMEOUT 1}、codex 27/27 OK；ENTRY_FAIL 2 例同报 `games.wythoff has no attribute 'solve'`。**逐例归因**（27 窗 1566 例次）: {OK 1235, A2 271, E 30, A 22, B 6, C 2}、A 份额 0.0140；交叉校验 6262/0。**候选⑤** 余量源 r597 实测振幅 83MB ⇒ ceiling 2856 / margin 83 / REQ **2733**（cap_binding=False）⇒ A1/A2 PASS + 判别力成对控制 true_discrimination=true；起手前清场（own-tool reap 177MB + drop_caches）已登记。**成本三列（参考·未可验收）**: 产品 17 调用 / 4293 新算 / 39556 completion vs 真值 48 / 25636 / 20462；命中率 v_all 0.98/0.95、v_incr 0.96/0.97（口径 = 中继 dump 时间轴）。**铁律 11 rc=1**（blocked 5 条，全落 wythoff）⇒ 全部读数标「参考（未可验收）」。轮志 `eval/rover/r598/report-r598.md`。

- **下轮候选 (R599)**: ① **产品侧处置裁定（待用户放行）**：落点收束到 `wythoff` 冷集构造层（候选④ B 份额 +0.5）与产物侧入口契约（ENTRY_FAIL 2 例）② **rc 语义收口（预注册）**：把验收面（`C1_task_face_v3.pass`）编入 rc（fail-closed），配历史判决审计证明「纯收紧、判决中性」 ③ **真值侧弱点面收口**：`wythoff#43-public + wythoff#57-hidden` 文本级定因（真值产出 vs 期望） ④ `V_int` 第六窗集 + landing 零回归面**钉到可复现 scope**（消除单窗集伪影） ⑤ 起手闸余量按 r598 实测振幅重派生。

#### R599（判据 v3 第七窗集行使）
- 真机臂轮 w181..w183（codex 真值 ×1 + R599D 产品默认档 ×3，同件 sha 4b70fd7cdb39 / 题集 e0c667c2）；**真值三窗自败**（56/51/56 of 58）⇒ C0 unreliable ⇒ set7 有效窗 **0**、判据无分辨率（不作能力结论）。
- 成本三列（信息项，参考）: 产品 18 调用 / 新算 prompt 4,127 / completion 40,617；真值 25 / 15,522 / 12,001。
- 候选② rc 语义收口（C11）: 器件-公式一致 7/7、tightening 3（set5/6/7 0→1）、relaxation **0**、控制全过 rc=0。
- 候选③ 真值侧文本级定因: 40 复现实例（codex 14 / 产品 26）全判 **semantic**（#43-public 实得 `WIN 1 13` vs 期望 `WIN 15 15`；#57-hidden 实得 `WIN 2 11` vs 期望 `WIN 25 25`），控制 NC-D/NC-T/POS 全过 rc=0。
- 候选④ `V_int` 第六窗集 agent {"0":7,"118":1,"6":1} / codex {"0":3}（阈值化未测）；landing scope 绑定机检 rc=0（请求 ⊊ 登记全 scope ⇒ 零回归面 not_applicable）。
- 候选⑤ 起手闸余量 swing 83→**264**（r598 同态在飞窗实测），ceiling 2889 / margin 179(cap_binding) / REQ 2829 ⇒ A1/A2 PASS。
- 铁律 11: `exec_precondition.py --round r599` rc=**1** ⇒ 全部成本/质量读数标「参考（未可验收）」；轮志 `eval/rover/r599/report-r599.md`。


- **R600（产品侧修复轮 · 用户令 2026-09-20「放行」）**: **回灌修复环「带现状」** —— 修复指令随附**管道自己写入的盘上产物原文**（只做字节搬运，语言无关；越界/缺失/二进制不随附但显式列出）。**定因**：R585–R599 缺口 100% 集中 `wythoff` 族（主桶冷集构造层），R600 只读定因实测失败臂产物在**题面公开用例**上即失败（`21 25`⇒`WIN 0 10` / `WIN 0 1` / `WIN 1 15` 非法着法），而管道**已**机械回放该用例并**已**花掉一次回灌修复 ⇒ 病灶 = 无状态管道下的**盲修**。
**单变量** `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`（T=缺省 on / C=显式 0，同二进制同剂量键）· 窗集 w184–w186 · 7 跑次/窗。
**读数**：J1 机制 **PASS**（T 8/9 跑次有随附、轮数 [1, 1, 1, 1, 1, 1, 0, 1, 1]；C 0/9）· J2 修复收敛（主）**PASS**（T 3/9 Wilson [0.1206, 0.6458] vs C 1/9 Wilson [0.0199, 0.435]）· J3 成本 **PASS**（T max calls 4 vs C max 4）· J4 能力（次级/欠功率）**FAIL**（T 4/9 vs C 3/9 vs C1 2/3）；同窗配对 D(T−C) 逐窗 {"w184": 0.3333, "w185": -0.6667, "w186": 0.6667}。
**门禁**：定向 7/7 · 全量 **1943/1943** · 形式门禁 **14/14** · API 基线 **+8/−0** · AOT `rc=0` **IL 警告 0** 原生 ELF 19,735,472 B sha12 8c3ade04d542（禁 `-p:PublishAot`）· 起手闸 A1/A2 PASS（cap_binding=true）+ 判别力成对控制真判别行使 + leak-selfcheck rc=0 · 铁律 11 前置器 rc=1（⇒ 成本列参考（未可验收））。
**诚实边界**：① J4 n=9/档 欠功率 ⇒ 只并列不作能力结论；② 被测件按设计变更（改源码 ⇒ 重发布 AOT）⇒ 与 R585–R599 冻结件轮**禁相减**；③ 本轮**零新增夹具语义**（真机臂 runner 由 run_r599.sh 逐条声明派生）；④ `bins-r600.json` 未在起臂前落盘（派生缺漏 `KeyError: 'R600D'`）⇒ 跑后同算法补生成，臂身份由 BIN_SHA_BEFORE/AFTER + 逐跑次 `arm_env.txt` 双证；⑤ 对照档与被测件同 sha ⇒ 单变量由 env 构造保证。
**artifacts**: `eval/rover/r600/{report-r600.md,prereg-r600.json,dag-r600.md,kpi-table-r600.json,verdict-r600.json,gate-margin-r600.json,run_r600.sh,judge_r600.py}` · `docs/evidence/RF0001/R600-repair-carryover.md` · `src/agent/r1/{ArtifactCarryover.cs,R1Options.cs,R1Pipeline.cs,R1RunResult.cs,R1Transcript.cs}` · `src/agent.tests/ArtifactCarryoverTests.cs`

- **R602（同件扩窗轮 · 第九窗集 w187..w189；零产品源码改动 / 零新增夹具语义 / 零新增开关）**: 被测件 `pub_r600` sha12 **8c3ade04d542** 与 R600 **同一枚**（逐字节同）· 冻结题集 `taskset-r602.json` sha256 `e0c667c2a313c04b` 与 r600 件 `cmp` **零差异** · 判分脚本同源 ⇒ **唯一自由度 = 窗集**。臂：`T` 产品默认档 ×3/窗 · `C` 轴关对照档 ×3/窗 · `C1` codex 外部真值 ×1/窗（21 跑次）。**主判据 v3（同窗 codex 配对，公式逐字取自 `kpi_r599.judge` 主线段）**: set9 **valid=2 / D_list=[0, −12] / D_median=−6.0 / 负号窗 1 ⇒ 不达 PASS**（阈值 D_median≥−2；w188 真值自败 56/58 ⇒ C0 unreliable 剔除、禁筛窗）。**J1 机制 PASS**（T 9/9 跑次含随附、C 0/9）· **J2 修复收敛（主）FAIL**（T 1/9 vs C 2/9）· **J3 成本 PASS**（T max calls 2 vs C 3）· **J4 能力（次级/欠功率）FAIL**（整题全对 T 4 vs C 3 vs C1 2）· **J5 跨窗集同向性 PASS**（set8 +0.1111 / set9 +0.1111，率、并列、禁相减）。整题全对逐窗：T {w187 2/3, w188 2/3, w189 0/3} · C {0/3, 0/3, 3/3} · C1 {1/1, 0/1, 1/1}。**成本三列（参考·未可验收）**: T 17 调用 / 新算 13,100 / completion 38,976 · C 18 调用 / 4,460 / 44,092 · 真值 15 / 11,663 / 9,241；命中率 v_all 中位 0.9068/0.9712/0.9104、v_incr 0.8423/0.9605/0.9378（口径 = 中继 dump 时间轴）。**只读并轮**: L2 前缀连续性 PASS（18 跑次 `prefix_chars` 唯一 15291 ∧ `prefix_sha256` 唯一 ∧ `task_sha256` 唯一）· L3 判定卫生 PASS（18/18 由外部用例集判、自证面 0）· **Q1 假信心率 0.0/18**（反向「rc≠0 ∧ 外部 58/58」= **4 例** ⇒ 自判**过度保守**方向，两侧同列）· **L1 可构造性机检 = 台账 §3.1「零产品改动加 BR/P 两臂」被证伪**（`axis_states=2`，该轴 env 面仅 on/off；三控制全过 ⇒ 器具有牙）· V_int（r600+r602）见 `vint-r600-r602.json`。**器具自捕 3 件（全部当场修复 + 留痕，不翻案）**: ① `checks_r602.py` 负控读的是注入前**内存副本**（注入后未重枚举）⇒ 负控恒绿；② J5 比较域「一侧计数 vs 一侧率」**不同源** ⇒ 判据退化成恒不同号；③ `int(rc or -1)`（`0 or -1 ⇒ -1`）使 **rc==0 恒错判** ⇒ 假信心率**结构性恒 0（空心）**——修复后本读数非空心。**铁律 11 rc=1**（`executable_and_correct=false`）⇒ 全部成本/质量读数标「**参考（未可验收）**」。**文献小步（≤3 检索式）**: 采信 1（arXiv:2609.20812**v1** overclaim 定义 ⇒ 落为 Q1 机检字段，已实施）· 受阻 1（arXiv:2609.00854**v1** 盲重采样/安慰剂三臂 ⇒ 与本仓 L1 轴面冲突，降为观测项）· 证伪 0 · 顺延 0。**artifacts**: `eval/rover/r602/{report-r602.md,prereg-r602.json,dag-r602.md,run_r602.sh,judge_r602.py,finish_r602.py,checks_r602.py,l1_axis_probe_r602.py,kpi-table-r602.json,verdict-r602.json,checks-r602.json,gate-margin-r602.json,vint-r600-r602.json}` · `docs/evidence/RF0001/R602-windowset-expansion.md` · `docs/research/lit-review-ledger.md` §5。

- **R603（同件扩窗轮 · 第十窗集 w190..w192；零产品源码改动 / 零新增夹具语义 / 零新增开关）**: 被测件 `pub_r600` sha256 `8c3ade04d542c0915fd7…`（**本侧独立复核**：`sha256sum $HOME/.agentframework/artifacts/pub_r600/agenthost` 前 12 位 = `8c3ade04d542`，与 R600/R602 **同一枚**）· 冻结题集 `taskset-r603.json` sha256 `e0c667c2a313c04b` 与 r600/r602 件 `cmp` 零差异 ⇒ **唯一自由度 = 窗集**。臂：`T` 产品默认档 ×3/窗 · `C` 轴关对照档 ×3/窗 · `C1` codex 外部真值 ×1/窗（21 跑次）。**主判据 v3**：`valid=1`（w192 D=0）· w190/w191 **真值自身自败** ⇒ C0 `unreliable` 剔除、禁筛窗 ⇒ **有效窗 1 ⇒ 判据无分辨率（不作能力结论）**。**J1 机制 PASS**（T 4/9 跑次含随附、C 0/9）· **J2 修复收敛（主）PASS**（T 4/9 Wilson [0.1888,0.7334] vs C 2/9）· **J3 成本 FAIL**（T `max_calls` 4 vs C 3；池化 T 16 调用 / 新算 9,576 / completion 36,688 vs C 17 / 3,949 / 39,195 ⇒ **判据取 max-of-9 单点极值**，本轮翻号；读数**照原样判 FAIL、不翻案**）· **J4 能力（次级/欠功率）PASS**（整题全对 T 6 vs C 3 vs C1 1；逐窗 T {w190 1/3, w191 2/3, w192 3/3} · C {1/3, 2/3, 0/3}）· **J5 跨窗集同向性 PASS**（set9 池化 T−C 0.1111 / set10 0.3334，同号、并列、禁相减）。**成本三列（参考·未可验收）**: T 16 / 9,576 / 36,688 · C 17 / 3,949 / 39,195 · codex 22 / 12,925 / 9,766；命中率 v_all 中位 T 0.9477 / C 0.9787 / C1 0.9315（口径 = 中继 dump 时间轴）。**只读并轮**: L2 前缀连续性 PASS（18 跑次 `prefix_chars` 唯一 15291 ∧ `prefix_sha256` 唯一 `f1280f71e6fc74c1…` ∧ `task_sha256` 唯一）· L3 判定卫生 PASS（18/18 由外部用例集判、自证面 0）· **Q1 假信心率 0.0/18（冲突 0）**；反向（rc≠0 ∧ 外部 58/58）= **3 例**（`w191/DC-r3 rc=5`、`w191/DT-r2 rc=8`、`w191/DT-r3 rc=5`）⇒ 自判**过度保守**方向 · 负控有牙（注入前缀漂移 ⇒ L2 翻红：`rc=0, negctl=true, l2_violated=true`）· L1 可构造性 `axis_states=2`（沿用 R602 机检结论）· 起手闸 A1/A2 PASS（`ceiling=2892 prev_swing=252 margin=182 REQ=2832 cap_binding=true`；首采 2641 装不下下限 ⇒ **fail-closed 退 N0 重开窗口**后 PASS）。****V_int 分布扩展（N4④）顺延**（`landing_predicate_r593.py --rounds r602,r603` 壁钟 >15min 未完成、零输出 ⇒ 本轮零读数入库、进程与 7 个 oracle 子进程已按 pid 清场，挪 R604；见轮志 §4）· N4⑤ 真值掉线面（新器具，只读）**: `eval/rover/r603/truthdrop_r603.py` 四桶（S1 两侧过 / S2 我方独败 / **S3 我方过 ∧ 真值败** / S4 两侧同败）——r602 `{S1 884, S2 148, S3 5, S4 7}` · r603 `{S1 901, S2 119, S3 **15**, S4 9}`；r603 的 S3 **全部**落 `w190`/`w191` 且用例 id 恒为 `wythoff#43-public` + `wythoff#57-hidden`（与 R596–R599 逐字同）⇒ ① codex 真值**不得当硬上限**（J4/J5 的隐含假设）② 归属标签 15/15 为 `L_mixed` ⇒ 该两例**跨跑次不稳定**（两侧均摆动）= 低区分度用例。**器具自捕 4 件（全部当场修复 + 留痕，不翻案）**: ① `truthdrop` 首版 `REPO` 层级错 ⇒ 输入恒缺失（rc=3）；② 域派生用 `cases_expected`（实为 **int** 而非常量表）⇒ 前缀域退化；③ 臂标签取 `tag`（实为 `g1`）而非 `DC-r1/DT-r1` ⇒ 归属恒 `L_mixed`；④ **`checks_r603.py --negctl` 写默认 `--out` ⇒ 覆盖主读数文件**（首版主读数被 negctl 内容替换；用显式 `--out` 分离后主读数复跑得 L2 pass=True）——留痕：主/负控两文件并列入档。**铁律 11 rc=1**（`precond-r603.json`：`executable_and_correct=false`；blocked 11 项 / 验收面 `blocked_scoped` 32）⇒ 全部成本/质量读数标「**参考（未可验收）**」。**文献小步（3 检索式 ≤ 上限）**: 采信 1（arXiv:2609.20804**v1** 组件级消融口径 ⇒ 支持本仓「固定执行环 + 单变量轴」判据形态，已实施）· 候选 1（arXiv:2609.20455**v1** 失败→可编辑位置的**结构化路由 + 范围化验证/回滚** ⇒ 落为修复回灌**粒度**轴候选，**须产品放行**）· 证伪 0 · 顺延 0。**artifacts**: `eval/rover/r603/{report-r603.md,prereg-r603.json,dag-r603.md,run_r603.sh,judge_r603.py,finish_r603.py,checks_r603.py,truthdrop_r603.py,l1_axis_probe_r603.py,kpi-table-r603.json,verdict-r603.json,checks-r603.json,checks-r603-negctl.json,precond-r603.json,truthdrop-r603.json,gate-margin-r603.json}` · `docs/evidence/RF0001/R603-windowset-expansion.md` · `docs/research/lit-review-ledger.md` §6。

- **下轮候选 (R604)**: ① **产品侧处置裁定（待用户放行）**：缺口仍 **100% 集中 `wythoff` 族**（T 112/135 = 83.0%，life/sub/nim 全 100%）⇒ 主桶 = 冷集构造层 ⇒ 修复属改 `src/`，未放行不动 ② **J3 判据形态收口（预注册）**：`max-of-9` 单点极值 ⇒ 改「池化调用数 ∧ 新算 prompt 双列」或「`T_max ≤ C_max + 1`」，先写后跑、本轮读数不翻案 ③ **真值掉线面下沉**：对 `wythoff#43-public` / `wythoff#57-hidden` 做**跨轮全窗集 census**（r585..r603 真值失败集合 + 我方逐跑次摆动）⇒ 判「低区分度用例」并给出**剔除/单列**的显式写法（只读、零产品改动）④ **有效窗下限判据面收口**（R587 遗留）：真值窗自败（本轮 w190/w191）⇒ 「剔除 vs 单列」显式二选一写法入册 ⑤ 起手闸余量按 r603 实测振幅重派生。

- **R604（只读/器具轮 · 候选 ①②③④⑤ + 遗留 V_int 并轮；零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关）**: 被测件与题集**未被触碰**（本轮零真机臂 ⇒ 无新臂读数、无降幅/增益宣称）。**C1 起手闸余量重派生**: `gate_margin_r604.py`，源 = r603 run-samples（n=146，min 2584 / max 2869，极差 **285**MB）⇒ MARGIN := clamp(prev_swing, 60, cap=CEIL−GATE−60)。现态 `ceiling=2577` ⇒ cap = 2577−2650−60 = **−133 < floor** ⇒ 判决 **WINDOW_UNOPENABLE（fail-closed，rc=2，非器具缺陷）**；归因：本会话工具子进程（pyright LSP，**249MB**，pid 2081094）**不在闸 blocker 血统内**（R571 同族）⇒ 反事实栏（只报不改）「回收后 `ceiling≈2826 cap=116 MARGIN=116 REQ=2766 openable=True`」；**判别力成对控制**（同一内存态两门槛反判）anchor=2650 ⇒ 基础门槛 PASS ∧ 条款门槛 GATE_BLOCKED，`stricter=true`（有牙）。**条款本轮未真机行使（未测）**。**C2 J3 成本判据形态收口**: `judge_j3v2_r604.py`，两路径交叉 = **adapter dump 逐跑次重算 == kpi-table 数组**（三轮逐位一致）；v1（`max_calls`）**三轮逐位复现** kpi.jsonl 已登记值 ⇒ 零回归。v2（预注册、无自由参数）= `Σ调用数 T ≤ Σ调用数 C` ∧ `逐窗 Σ T ≤ Σ C` ∧ `单位调用新算 prompt T ≤ C`。读数：**r600 v1 PASS(4/4) → v2 FAIL**（`a2@w186`；b1 单位 734 vs 197 = **3.726×**）· **r602 v1 PASS(2/3) → v2 FAIL**（`a2@w189`；770.6 vs 247.8 = **3.110×**）· **r603 v1 FAIL(4/3) → v2 FAIL**（`a2@w191`；598.5 vs 232.3 = **2.577×**）⇒ 形态收口**不是放宽而是收紧**：v1 在 r600/r602 的「成本 PASS」是**空心通过**（只数调用、不看单次新算 prompt）；b1 对机制**结构性不利**（随附产物必然抬高修复轮新算 prompt）⇒ 「b1 当闸 vs 只作报告列」须**先预注册**再改（列 R605）。控制：POS（注入 calls+2）必红并**点名 a1**、NEG 与 base 同、非平凡（三轮读数互异）三件齐。**R603 已登记 J3 FAIL 不翻案**（两形态并列）。**C3 真值掉线面跨轮 census**: `truthcase_census_r604.py`，**13 轮 × 3 窗 = 39 窗**，统一源 = run root `cases.txt`（口径与 `judge_r603.read_cases` 同源），守恒 **10614/10614**（早轮 3 产品臂、r600+ 每窗 6 产品臂 ⇒ 通过率取**比率**口径方可比）。真值失败面 = **13 例 / 57 窗次 / 17 窗**（**全部 `wythoff` 族**）；Top2 = `wythoff#57-hidden` **17 窗 / 12 轮**（我方通过率 0.5833）· `wythoff#43-public` **13 窗 / 9 轮**（0.5）⇒ **T1「真值侧掉线用例」成立**，但 **T2「我方稳定通过」不成立**（两侧五五**摆动带**）⇒ 判**低区分度候选**，**不作我方收益**；窗级 S3（全部产品跑次通过 ∧ 真值失败）仅 **4 窗**，与 `truthdrop_r603` 的**跑次级** S3（r603 15 行）口径并列、**禁混算**。控制：POS（注入 ⇒ 计数 +1 且轮面扩大）、NEG（越域 ⇒ 身份闸 rc=2）、非平凡三件齐。**C4 入册**: `docs/external-reference-harness.md` **§12.6**（增量 32 行）= 真值自败窗**显式二选一**（剔除配对 ∧ **单列我方读数** ∧ **不记我方缺陷**；有效窗 = 0 ⇒ 判「无分辨率」**禁筛窗**）+ 真值失败面**两级口径**（跑次级 / 窗级）+ 低区分度用例写法。**C5 文献小步（3 检索式 = 上限）**: 采信 **2** · 证伪 0 · 顺延 0 —— `arXiv:2609.20794`**v1**（欠定问题的**点估计评测不足**，须比对解集/后验）⇒ 支持本仓既有「独立 oracle 解集复核」：代码证据 `eval/rover/r592/landing_predicate_r592.py`（独立实现 oracle，与被测零共享）+ R593 分桶 `A_landing_loose 0.0717 / B_coldset 0.6595` ⇒ **判据僵硬非缺口主因**（采信·已实施）；`arXiv:2609.20822`**v1**（**声明式约束不承重**：约束写在提示里≠进入优先级，机器人域实证 planning 阶段丢失）⇒ 支持本仓「把约束转**可执行前置步骤**」：代码证据 `src/agent/r1/R1Pipeline.cs:192`（probe = PublicSelfCheck ∧ probeSet）→ `R1RunResult.cs:12`（`rc=8 public_probe_unmet`，**非模型自述**的公开用例回放）+ `eval/rover/r507pre/exec_precondition.py`（独立物化 + 逐用例判对 = 铁律 11）（采信·已实施，机制只取一句、具体件属机器人域不移植）。**遗留 V_int 分布扩展**（`landing_predicate_r593 --rounds r602,r603`）本轮已后台起（`vint-r602-r603.log`，**0 字节**）——**壁钟 424s 零输出、`vint-r602-r603.json` 未落盘 ⇒ 按 pid 清场（4 进程，含 `-m games wythoff` oracle 子进程）、零读数入库、如实再顺延**（与 R602/R603 同因，**不静默跳过**）。**诚实边界**: ① 零真机臂 ⇒ **不宣称任何降幅/增益**；② C1 条款未行使（未测）；③ C2 两形态并列、R603 判决不翻案；④ C3 通过率为比率口径、跑次级/窗级禁混算；⑤ 铁律 11 前置器本轮**不适用**（零产品改动、零新臂）。**artifacts**: `eval/rover/r604/{dag-r604.md,prereg-r604.json,gate_margin_r604.py,gate-margin-r604.json,judge_j3v2_r604.py,j3v2-r604.json,truthcase_census_r604.py,truthcase-census-r604.json,report-r604.md}` · `docs/external-reference-harness.md` §12.6 · `docs/research/lit-review-ledger.md` §7。

- **下轮候选 (R605)**: ① **产品侧处置裁定（待用户放行）**：缺口仍 100% 集中 `wythoff` 族（冷集构造层）⇒ 属改 `src/`，未放行不动 ② **J3 形态 v2 起效**：必须在**新的**窗集上按 v2 预注册后跑（**禁**拿 R603 数据翻案）③ **b1 列口径裁定**：随附产物结构性抬高单次新算 prompt ⇒ 「b1 只作报告列 vs 当闸」须**先预注册**再改 ④ **有效窗下限判据面落到判据器**（本轮只入册文档：§12.6 A 条）⑤ **低区分度用例剔除/单列写法落到 judge**（本轮只出 census；须先写冻结名单与负控）⑥ **起手闸清场后重派生**：按 pid 收回本会话工具子进程（LSP）再取 ceiling，验证 REQ≈2766 的可开性。

- **R605（同件扩窗轮 · 第十一窗集 w193..w195；零产品源码改动 / 零新增夹具语义 / 零新增开关）**: 被测件 `pub_r600` sha256 `8c3ade04d542c091…`（本侧独立复核前 12 位一致，与 R600/R602/R603 **同一枚**）· 冻结题集 `taskset-r605.json` sha256 `e0c667c2a313c04b`（与 r603 件 `cmp` **零差异**）⇒ **唯一自由度 = 窗集**。臂：`T` 产品默认档 ×3/窗 · `C` 轴关对照档 ×3/窗 · `C1` codex 外部真值 ×1/窗（21 跑次）。
**主判据 v3（同窗 codex 配对）**: set11 **valid=3 / D_list=[0, −2, 0] / D_median=0 ⇒ PASS**（阈值 D_median≥−2 ∧ 各窗>−15；**三窗真值全 58/58 = 首例** ⇒ 主判据**第一次具备完整分辨率**）；set9(r602)/set10(r603) 并列（禁相减）。
**J1 PASS**（T 8/9 跑次含随附、C 0/9）· **J2（主）FAIL**（T 1/9 vs C 1/9，Wilson 同为 [0.0199, 0.435]）· **J3 成本 v2（本轮主判据，首次在新窗集行使）FAIL**（a1 池化 Σcalls 21 vs 19；a2 破于 w193 10 vs 5；b1 单位调用新算 prompt 665.81 vs 287.89 = 2.31×；控制 POS 有牙 ∧ NEG 同底 ∧ 非平凡）· **J3 v1 并列 FAIL**（`max_calls` 4 vs 3，**不翻案**）· **J3 v2′（b1 作报告列）FAIL**（a1/a2 仍破 ⇒ b1 降级不改变本轮结论）· **J4（次级/欠功率）FAIL**（整题全对 T 4 vs C 4 vs C1 3）· **J5 FAIL**（set10 +0.3334 / set11 0.0 ⇒ 方向未复现）。
**候选④ W_floor 首次落到判据器**：有效窗 ∈{0,1} ⇒ 标签 `NO_RESOLUTION`（不作能力结论、不记不达；真值自败窗剔除配对 ∧ 单列我方读数）；零回归回放 **11 轮 ⇒ 翻号 3**（全为 `不达→NO_RESOLUTION`：r591/r597/r599），`NO_RESOLUTION→PASS` **0**、`PASS→任何` **0** ⇒ **纯标签语义收口、非阈值改动**（`wfloor-regression-r605.json`，rc=0）。
**候选⑤ LD 冻结名单**（`wythoff#43-public` / `wythoff#57-hidden`，源 = R604 census）只作诊断列 `v3_ex_LD`=[0, −4, 0]，**不作判据、不进 rc**；三控制齐（POS 空名单 ≡ v3 / NEG 未知 id 拒 / 非平凡 True）。
**成本三列（参考·未可验收）**: T 21 调用 / 13,982 新算 / 43,809 completion · C 19 / 5,470 / 44,278 · codex 15 / 12,104 / 8,802；命中率 v_all 中位 T 0.9202 / C 0.9654（口径 = 中继 dump 时间轴）。
**只读并轮**：L2 前缀连续性 PASS（`prefix_chars` 唯一 15291 ∧ `prefix_sha256` 唯一）· L3 判定卫生 PASS（18/18 由外部用例套件判、自证面 0）· **Q1 假信心率 0.0556（1/18：w194/agentDT-r3 rc=0 ∧ 57/58）**；反向（rc≠0 ∧ 外部满分）**7 例** ⇒ 自判**过度保守**方向 · 负控有牙（注入前缀漂移 ⇒ L2 翻红）。
**门禁**：起手闸 A1/A2 PASS（`ceiling=2775 / prev_swing=285 / margin=65(cap_binding) / REQ=2715`；起手前按 pid 收口会话端 LSP 子进程 ⇒ `MemAvailable` **+177MB**，候选⑥ 落实）· 判别力成对控制**未行使**（内存高于条款带 ⇒ 如实记「未测」）· leak-selfcheck rc=0 · **形式门禁 14/14**（Failed 0 / Passed 14 / Skipped 0） · 铁律 11 `rc=1`（blocked 10 条全落 `wythoff`）⇒ 成本/质量读数标「参考（未可验收）」。
**诚实边界**：① J4 欠功率（n=9/档）只并列；② 与 R585–R599 冻结件轮禁相减；③ rc 语义本轮分层（0 器具可用 / 2 器具缺陷 / 3 输入缺失）＋新增 `mechanism_rc`（**首跑后补记** `checks_posthoc`，不改判据）⇒ 与 r603 的 rc 列**不可直接并列**；④ 「b1 降级」须用户裁定（候选③）；⑤ **V_int 第六窗集已取得读数**（`vint-r605.json`）：21/21 跑次、oracle 一致、控制三值互异（新粒度 has_teeth=True / 旧粒度 False）、守恒 True；agent 桶 {B_coldset 48 / A_landing_loose 27 / D_delivery_or_shape 9 / A_selection_order 3}、`v_int_hist` agent {0:14, 3:1, 29:1, 32:1, 118:1}、层 {(c)12,(b)4,(a)2}；**器具 rc=2 两项 False 均已定因**：零回归=False = 已知 scope 伪影；只读=False = **两个不可区分的候选因**：① 本侧在器具运行期间并发跑 `dotnet test`（构建写 `src/*/obj|bin`，违反「批测/单测/build 三者互斥」纪律）② **对侧写者在飞**（`.git/ROUND_CLAIM` = R606 @04:31:28，且工作区有未提交 `src/` 改动 2 文件）；快照树 0 文件改动 ⇒ 被测面未被改 ⇒ R606（对侧已开）后在无并发条件下重跑。
**artifacts**: `eval/rover/r605/{report-r605.md,prereg-r605.json,dag-r605.md,run_r605.sh,judge_r605.py,finish_r605.py,checks_r605.py,wfloor_regression_r605.py,kpi-table-r605.json,verdict-r605.json,evidence-r605.json,gate-margin-r605.json,checks-r605.json,checks-r605-negctl.json,wfloor-regression-r605.json}`

- **下轮候选 (R606)**: ① **产品侧处置裁定（待用户放行）**：缺口仍 100% 集中 `wythoff` 族，落点 = 冷集构造层 ⇒ 属改 `src/`，未放行不动 ② **b1 列口径裁定**（报告列 vs 当闸）须**先预注册再改**（本仓已有 v2/v2′ 并列读数可作裁定输入）③ **J2/J4 欠功率面**：扩 reps（≥25/档）须**先写预算与判据**（禁无界加跑次）④ **起手闸判别力成对控制**：本轮未行使（内存高于条款带）⇒ 改操作顺序（先**压低 CEIL** 再行使，先预注册）⑤ **V_int 第六窗集**（本轮顺延；须给后台作业**分段落盘**，防一次性收尾超时）⑥ **文献候选 L4**（同任务独立复本一致性，不需真值参照）落为**分布先行**项。

- **R607（里程碑盘点轮 · RF0004.0 盘点+打点；**零产品源码改动** / 零新增夹具语义 / 零新增开关；提交面 `src/` = 0，commit `ee3fa146`）**: 二进制 `src/agent.host/bin/Release/net10.0/agenthost` **从现盘 src 重建** ⇒ sha256 `fe1fb720…820dd3` = **与 R583 登记值逐位相同**（重建可复现 ⇒ 与 HEAD `f8128c6b` 同源）。**新增盘点器具** `eval/rover/r607/inventory_r607.py`（3 面 × 15 键；发射点 file:line **由现盘 grep 派生**、独立发射点计数、全史现读数；缺口判据 = `emit_count_sites == 0`）+ `judge_r607.py`（P1–P5；判定只读 `verdict` 键、rc 由 verdict 派生）。**盘点缺口三条（RF0004.1/.2/.3 的开工前置）**：① 开放域识别出口**无统一 `{标签|abstain, 依据}` 打点** ② `TaskKindHint` 五档**无 Generation** ⇒ 生成面结构性无档 ③ `ActionLoopRunner.cs`/`ActionLoopGate.cs` 的 `Emit(` 计数 = **0** ⇒ 编排面**零专用打点**。**真机（单变量 `AGENTFRAMEWORK_GATE_REPEAT_SKIP` 缺省 vs 显式 off；T×3 / C×3；复用 r583 夹具 `fixture-shapes-line1.txt`（sha `c98f8ab3…`）与轮序 `turns-S0.txt`，跑后 `data/nlp` 复原为 absent 且回读断言；6/6 rc=0，11–31 s/臂）**: **P1 治疗>0 PASS**（T×3 三键 [1,1,1]：`local_turn_gate{verdict=Skip}` ∧ `nlp_shape{shape=1∧face=repeat∧route=local_skip}` ∧ `local_gate_skip_reply{kind=repeat_verbatim}`）· **P2 对照==0 PASS**（C×3 三键 [0,0,0]）· **P3 闸前置 PASS**（6/6 `local_turn_gate_config{turn_gate_enabled=真 ∧ role=skeptic}`）· **P4 冻结恒前缀 PASS**（`F_env.prefix.chars`=15291 ∧ sha `f1280f71…4d4a`；**命中率 ≥97% 记未测**＝REPL 面无口径）· **P5 有牙 PASS**（负控注入 + 非平凡互异）⇒ `verdict=PASS, rc=0`。**轴归因（`checks_posthoc`，不入 verdict）**: 两臂 turn2 输入指纹逐位相同（`msg_sha16=147757f75f39bd44`）而 `basis` 互斥（T `mechanical:repeat→local` / C `mechanical:nonack→remote`）⇒ 差异只来自门轴。**器具缺陷披露式重注册 v1→v2**: v1（保留 `verdict-r607-v1-RED-boolexact.json`）判 `VOID(rc=3)`，根因 = **读数口径错**（`turn_gate_enabled` 以 .NET `"True"` 落盘而判据按字面 `true` 比较 ⇒ 前置判 False ⇒ 连带 P1/P2/P5 失败）= 器具缺陷非被测失效；v2 只加归一 `_boolish()`，**阈值与判据集一字未改**、原始遥测与偏移未变（同一跑次复判，非重跑），并把两形态写入头部影子自检防回归；v1 判定**未翻案**。**跳步（各一行原因）**: AOT 面（零产品改动 + publish 会抬高同窗 `PREV_SWING`，RF0004 §6.2）· C1 codex 臂（打点面盘点轮无质量对照项）· 恒前缀命中率 · 三面能力收益（三面未接线，禁作能力宣称）。**门禁**: 形式门禁 **14/14** · 全量 **1942/1943**（红 = `PromptCacheChannelTests.溯源` 遥测错误行缺 `prompt_tokens`，**前态同形**、与本轮零产品改动无关）· `status_gen.py --check` **PASS**（违规 0 / 基准漂移 0 / 缺源 0）· `decl_sweep` 0 漂移 · registry R2e 冻结 pin 首跑红（`artifact_sha12` 误钉 `verdict` 而非证据文档）⇒ 重钉为证据文档 sha12 `78b6e034c5ef` 后转绿（**声明滞后类，非行为回归**）。

- **下轮候选 (R608)**: ① **RF0004.1 开工 = 识别出口统一打点**（`{标签|abstain, 依据}`；前置已由 R607 盘点确证缺失），落地后**先证变量可生效再消融**（RF0004 §0.3）② **RF0004.0 遗留**：恒前缀命中率口径（REPL 面不产）／AOT 面（零改动轮跳步待补，须在无 publish 抑制波动的窗内做）／C1 codex 臂 ③ **起手闸 swing 重取**（R606 无自产 window-samples ⇒ R607 沿用 r603 洁净源 285 MB；R608 起臂前应取新洁净窗）④ **文献候选 L4**（动作空间粒度轴，arXiv:2609.20804v1 预印本、只作机制假设）待 RF0004.2 编排面打点前置闭合后才可起臂 ⑤ 三面缺口须**分别**立打点，禁一轮塞三面（一问题不吃多轮的反面：一问题不塞多面）。

- **R610（RF0004.2 首轮 = M3 第一刀；**机制面落地 + 恒前缀基线与口径重钉；真机臂顺延**）**: **唯一变量(预注册)** `AGENTFRAMEWORK_R1_ACTION_CANDIDATES`（缺省 on / 显式 `0` = 旧行为逐位）；窗集定 **w199..w201**（第十三窗集）。**改动**: 契约面以**尾部载体块** `<action_candidates>` 追加（前缀 15291→**15675** 字符，首次分歧 **15283** = 前 99.95% 逐位不变；`gen --check` **drift 0**）+ 新件 `src/agent/r1/ActionCandidates.cs`（白名单取执行面、必填参数取声明面、逐条可机检原因码）+ 台账三计数（**声明数 0 ⇒ 字段缺席**）+ 单测 6 条。**机检读数**: 单测 **6/6**（正控 / 判别性负控 5 类 / 同源闸 / 零回归 / 边界 / 轴解析）· 定向面 **80/80** · 形式门禁 **14/14** · API 基线 **+16/−0** · `status_gen --check` **PASS（违规 0 / 基准漂移 0 / 缺源 0）** · `decl_sweep` **0 漂移**。**基线重钉**: `F_env.prefix.chars` 15291→**15675** · `F_env.prefix.sha256`→**a9792fdb…**（新源 `eval/rover/r610/prefix-r610.json`）。**自捕 2 件**: ① 首版字段插进 schema 段内（分歧 **1889**、*87.6% 前缀被推移*）违反 RF0004 §131「一律走尾部载体块」⇒ 改尾部块；② 基线 threshold 字面「前 15291 字符逐位不变」**与历史实践不符**（历史厚化分歧在 1641/796，无强检）⇒ 判「字面不成立、实义=每次厚化重取 chars/sha 并重钉」并已按实义执行。**新发现口径**: 前缀为编译期常量 ⇒ 会话内命中率不受内容影响，「中段插入⇒破缓存」不成立（首版定因误把跨轮冻结可比性读成会话内命中率）。**顺延**: N8 发布 / N9 真机臂 —— 同仓兄弟会话在飞改 `src/`（mtime 09:59:03）⇒ 被测件身份不成立 ∧ `MemAvailable` 1543MB < REQ 2820MB ∧ 兄弟 `MSBuild/VBCSCompiler` 在飞（禁拆共享编译节点）；**重启判据 = 只重启 N8→N9 这条边**，同 `prereg-r610.json` 起臂（prereg 已在臂前落盘），**禁调闸值**。**诚实边界**: 零真机臂 ⇒ 不宣称任何质量/调用/命中率降幅；M3 出口闸（调用数 ≤ 旧臂 50%）本轮**不判**（执行接线属 R611 第二刀）；铁律 11 前置器本轮不适用。**artifacts**: `eval/rover/r610/{dag-r610.md,prereg-r610.json,report-r610.md,prefix-r610.json,run_r610.sh,judge_r610.py,taskset-r610.json}` · 台账 `eval/capability/kpi.jsonl`（R610）· `docs/research/lit-review-ledger.md` §11。**注**: R608/R609 的轮志在 `docs/evidence/RF0001/` 与 `kpi.jsonl`（§7 未逐轮同步；本轮只增量追加，不补写历史轮、不改旧读数）。

- **下轮候选 (R611)**: ① **N8→N9 重启**（同 prereg 起臂：AOT 重发布 `artifacts/pub_r610/agenthost` → 第十三窗集 w199..w201 T×3/C×3/codex×1 → `judge_r610.py`）—— 起臂前三闸：同仓无在飞写者 ∧ `MemAvailable ≥ 2650+clamp(170,60,cap)` ∧ 端口空闲。② **M3 第二刀 = 本地执行接线**（让 `ActionCandidates.Selection` 被执行面消费 ⇒ M3 出口闸「调用数 ≤ 旧臂 50%」才可判）；前置 = R611 先证 J1 声明到岸率 > 0。③ 文献候选 C2（候选**排序值**按关键路径缩减，arXiv 2604.16469v1）**不得抢占** ① ② 预算。
- **R614（R610 顺延边 N8→N9 重启 · **真机 21 跑次**；零产品源码改动 ⇒ `src/` 与 R610 提交零 diff，单变量 = 已提交的 `AGENTFRAMEWORK_R1_ACTION_CANDIDATES`）**: 权威预注册沿用 `eval/rover/r610/prereg-r610.json`（臂前 10:05 已落盘，本轮为**首跑**·无窥视），r614 件为**引用件**（阈值/臂表/窗集/证伪条目一字未改）。窗集 **w199..w201**（第十三窗集，与历史不相交）；被测件 `artifacts/pub_r610/agenthost` sha256 `6a31fc47a694d567…` ∧ `bin_sha_stable=true`；题集逐字节冻结 sha16 `e0c667c2a313c04b`。**真机读数（21 跑次：T×9 / C×9 / C1×3）**: **质量** 整题全对 T `3/3·2/3·2/3`（池化 **0.778**，用例中位 58）vs C `1/3·1/3·1/3`（0.333，中位 51）vs C1(codex 真值) `1/1·1/1·0/1`（0.667，中位 58，w201 用例 47/58 = 真值自败 ⇒ `unreliable` 窗剔除配对）；**任务面主判 v3 PASS**（T−真值同窗率差 `w199 0 / w200 −0.333 / w201 +0.667` ⇒ 有效窗 2、D_list `[0,0]`、中位 0，floor −15 / median −2 未触）。**成本三列（铁律 11 rc=1 ⇒ 一律标「参考（未可验收）」）**: 调用池化 **17 vs 17**（T 单位调用新算 prompt 987.4 vs C 726.0 ⇒ b1 **更差**）· 新算 prompt 16,785 vs 12,342 · completion 40,777 vs 38,891 · 命中率 v_all 中位 0.900 vs 0.915、v_incr 0.834 vs 0.855（口径 = 中继 dump 时间轴）。**机制面 J1 = 未达标（`mechanism_rc=1`）**: `action_candidates_declared = 0` 于 **T 9/9 ∧ C 9/9 ∧ C1 3/3** ⇒ 轴**未被行使** ⇒ T−C 的成本/能力差**不可归因（摆动）**，`mechanism-not-engaged` 下禁读作「无收益」。**归因（关键，证伪接线缺口假设）**: 实发请求体（`AGENTFRAMEWORK_DUMP_REQUEST`）system **15,675 字符 = `PrefixChars`** ∧ 含 `<action_candidates>` 块 ∧ `prefix_sha256 a9792fdb…` pinned **18/18** ⇒ 接线正确；21 条回复全文 grep `action_candidates` **0 命中** ⇒ **远端零遵守**（非接线缺口、非抽取器读空）。**铁律 11 前置器 rc=1**（`EXECUTABLE_AND_CORRECT=False` / `ACCEPTABLE_SCOPED=False` / `POLICY_ACTIVE=False no_policy_key`；不合格臂窗 9 项，含 `w199 C-r1 rc=124 超时 0/6`）；**外部真值臂自身 47/58 × 3 窗**（失败**全在 wythoff 族** 34/45，life/sub/nim 42/42/45 全绿）⇒ 真值非硬上限。**自捕 2 件（均未放宽判据）**: ① **J2b 守恒判据「真空绿」**（声明数 0 ⇒ 守恒式真空成立 ⇒ v1 报 `pass=True`，与其自身 `need` 串「需有声明跑次 > 0」不符）⇒ 门加 `j2b_declared_runs > 0`（**阈值未改**）+ `reason=NO_DECLARATION_VACUOUS`，**后处理幂等重算**得 v2（`verdict-r610-v2.json`，judge sha12 `66fa17ad3d42`），首跑 v1（sha12 `cbc98163980d`）与 `kpi-table-r610-v1.json` **原样保留**；负控有牙 `eval/rover/r614/j2b_teeth_r614.py` = 正控 rc=0（门**源派生** + 三例两侧样例）∧ 前态负控 **rc=2 GATE_MISSING**（前态件 sha256 `cbc98163980d…` **与 v1 首跑同源**）。② **读法错**：首查用 adapter dump 判「前缀是否含块」得「不含」——实为 dump **截断到 12,000 字符** ∧ STJ 把 `<` 转义 `\u003C`；改用实发件原文才定案（纪律：判「字段/块是否在实发请求」只认实发件，且先验未截断）。**DAG 收尾判定**：按 DAG 预写的判据器缺陷分支 ⇒ **只重启 N6（后处理重算），禁重测**（已执行）。**门禁**: 形式门禁 14/14 · `status_gen.py --check` PASS（违规 0 / 基准漂移 0 / 缺源 0）。**artifacts**: `eval/rover/r614/{dag-r614.md,prereg-r614.json,report-r614.md,aot_r614.sh,j2b_teeth_r614.py,j2b-teeth-r614.json,j2b-teeth-r614-precontrol.json,pretest/}` · `eval/rover/r610/{verdict-r610-v2.json,verdict-r610-v1.json,kpi-table-r610.json}` · 台账 `eval/capability/kpi.jsonl`（R614）· registry 行 `r614.m3-cut1-realmachine-readings` · 文献 `docs/research/lit-review-ledger.md` §12（arXiv 面本轮 429/超时不可用 ⇒ 第二来源官方工程文档 2 件，采信 0 / 观察 2）。

- **下轮候选 (R615)**: ① **声明面驱动**（最高优先，`src/` 改动，未放行不动放行前须写「改哪一格读数」）：把候选字段从「可选」提到 `self_check` 必查项 ⇒ 判据 = 声明到岸率 **> 0**（≥1 跑次）∧ 前缀加厚不破 97% 命中下限 ② **M3 第二刀 = 执行面接线**（`accepted` 当前消费者数 0）⇒ 出口闸「调用数按 request_id 去重 ≤ 旧臂 50%」才可判 ③ 捕获面加固（adapter dump 截断显式化）④ `w199 C-r1 rc=124` 超时是否复现（**不调阈值**）⑤ wythoff 族**双侧共同缺口**（真值 34/45）⇒ 先判题面/夹具（R512 教训）再谈能力。


- **R615（M3 第一刀 J1 的**测量面修复** + 提示尾块**单变量**真机重测；21 跑次；`src/`+`tools/` 有改动 ⇒ 被测件变更）**: **先把 R614 的归因证伪**——前提机检（`eval/rover/r615/premise-r615.json` rc=0，正/负控成对：`POS_opt_out_flips=True` / `NEG_empty_corpus=True` / `non_trivial=True`）显示冻结 17 跑次里 `declared_field_present = 0` 而 `plan_ge2 = 17/17`，三条结构检查全中（尾块词表与管道菜单**不同源** ∧ 旧尾块写「**可选**…不声明 ⇒ 本地只按 plan 执行」= **显式豁免** ∧ 有编排零声明）⇒ 归因由「远端零遵守」**改判** `contract_face_structural`（契约面结构决定 + 测量面不可见）。**唯一单变量** = 提示尾块 `AGENTFRAMEWORK_R1_ACTION_PROMPT`（unset = 新块 / `legacy` = R610–R614 旧块**逐位**）；窗集 **w202..w204**（与历史不相交）；臂 T×9 / C×9 / C1(codex 真值)×3。**产品侧最小改动**: ① 尾块措辞「可选」→「**回复顶层必填字段**」∧「确实没有动作时给空数组 `[]`（字段缺席 = 契约不完整）」（`tools/r1gen/r1prompt.py`）② 旧尾块**逐字节**副本（由 `git show HEAD:` 派生，禁手抄）+ 轴解析纯函数（`tools/r1gen/gen_csharp.py` → `src/agent/contract/StructuredPrompt.cs:615-660`）③ 生效前缀三消费点改走轴解析（`src/agent/r1/R1Pipeline.cs:36,37,41,94`）④ **键到达面与「声明非空」解耦**（`src/agent/r1/ActionCandidates.cs:47-49,84-85`）⑤ 台账 `present` 字段（仅在**到达**时落，值恒 1；`src/agent/r1/R1Transcript.cs:75,77,122,124`）⑥ 单测 5 条（`ActionCandidatesTests` / `R524PrefixStabilityTests`）。**只加厚不变量**（`prefix-r615.json`）: chars **15675→15794**（+119）、前 **15282** 字符逐位不变（= 尾块起点）、尾块整体置换 382→501、尾块后收尾逐位不变；**轴关逐位等价** sha = `a9792fdb…`（= R610–R614 冻结 pin，单测钉住）。**真机读数**: **J1（主）PASS** —— 键到达跑次 **T 8/9 vs C 0/9 vs C1 0/3**，其中 **6/8 为「到达但空数组」**（R614 台账结构性读 0 的形态），有声明跑次 T 2（declared 10/7，rejected 0）；旁证 = AOT 冒烟回复原文以 `"action_candidates":[]` 结尾而 stats 行同时有 `action_candidates_present:1` 且 `declared` 字段缺席（`evidence/smoke-aot-r615.txt`）。**J2b PASS**（有声明跑次 > 0 ∧ 守恒违例 0）。**J4 能力面无增益**（整题全对 T 5/9 = 0.5556 vs C 6/9 = 0.6667 vs C1 0/3；用例中位两侧同为 58，极差 12/15/13 ⇒ **摆动 ≥ 效应**，本轴不承重能力面）。**J3 成本**: v1 PASS / v2 FAIL（调用 Σ 16 vs 22；命中率 v_all 中位 0.8992 vs 0.9152）——**铁律 11 rc=1 ⇒ 一律「参考（未可验收）」**。**J5 符号相反**（本轮 −0.1111 vs R610 窗集 +0.4445 ⇒ 窗集依赖，并列不改主 rc）。**任务面 v3 `NO_RESOLUTION`**（真值自败窗剔除后有效窗 0 ⇒ 不可判，不判红不判绿）。**铁律 11**（`precond-r615.json` rc=1）: 21 臂全部独立物化实跑、`self_report_agrees=True` ∧ `executable_and_correct=False`；10 臂未达 58/58，**含 codex 真值臂 3/3 窗（56/43/56）**⇒ 未通过面非本侧独有，主失败族 `wythoff#43..#57`。**自捕器具缺陷 2 件（均修、读数未重测）**: **I1 判据器读取契约缺新键** —— `judge_r615.py:read_transcript` 按 `TR_FIELDS` 白名单取值 ⇒ 新键 `action_candidates_present` 静默读空 ⇒ J1 **假红**（T 档 `present` 全 null 而同一 transcript 的 `declared` 有值）；修法 = 并入读取契约（数据在盘完好 ⇒ 只重跑后处理）；v1 判决件 `verdict-r615-v1readcontract.json` 原样保留。**I2 前缀块长口径错** —— 把 raw 源码里的尾块长度（含 `\uXXXX` 4 字符字面）当作「前缀内的块长」⇒ `append_only` 误判 False；改按**前缀字节**切块、不放宽判据。**运行期（非器具）**: 派生驱动器首跑在预注册闸 fail-closed（`assert d["round"]=="R610"` 与 `exec_precondition --round r610` 两处轮号残留未替换到位）⇒ 改轮号，**阈值/判据一字未改**。**门禁**: 起手闸 A1/A2 PASS（`ceiling=2919 / prev_swing=70 / REQ=2720`；起手前 `dotnet build-server shutdown` + 按 pid 收 LSP 子进程 ⇒ `MemAvailable` **+1017MB**，2821→2939）· 判别力成对控制 rc=0（真判别行使）· leak-selfcheck rc=0 · 定向单测 **73/73** ∧ R524 面 **40/40** ∧ 形式门禁 **14/14** · `status_gen.py --check` **PASS**（违规 0 / 基准漂移 0 / 缺源 0）· `decl_sweep` 0 漂移 · **基线重钉** `F_env.prefix.chars`→15794 ∧ `F_env.prefix.sha256`→`8b8be6b8…` ∧ 新增 `F_env.prefix.legacy_anchor`→`a9792fdb…`（源 = `eval/rover/r615/prefix-r615.json`）。**诚实边界**: ① 本轴只证「措辞决定键到达」，**不证能力/成本收益**；② 成本与降幅一律「参考（未可验收）」；③ 任务面不可判（有效窗 0）；④ 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**；⑤ 新尾块仍保留 R610 的「plan 已表达的写文件/执行步骤**不要**在本字段里重复声明」豁免句 —— 它是「到达但空数组 6/8」的**首要嫌疑**（premise 显示 17/17 跑次真实动作都在 plan 里）⇒ 下轮单变量候选。**artifacts**: `eval/rover/r615/{dag-r615.md,premise-r615.json,premise_r615.py,prereg-r615.json,prefix-r615.json,report-r615.md,run_r615.sh,judge_r615.py,aot_r615.sh,taskset-r615.json,bins-r615.json,gate-margin-r615.json,verdict-r615.json,verdict-r615-v1readcontract.json,kpi-table-r615.json,kpi-table-r615-v1readcontract.json,evidence/}` · 台账 `eval/capability/kpi.jsonl`（R615，带 `baselines` 5 条）· registry 行 `r615.j1-arrival-face-and-prompt-block-axis` · 文献 `docs/research/lit-review-ledger.md` §13（首段采信 2）/§14（当轮小步 3 检索式全不相关 ⇒ 新增采信 0；两条引用逐字复核通过）。**证据文档形态说明**: 本仓 `docs/evidence/<版本线>/` 只收 RF 版本线（RF0001/RF0002/RF0006），R 轮次不收 ⇒ 本轮证据面 = 轮报告 `report-r615.md`（已作 registry 行 `artifact_sha12` 钉住）+ 本 §7 块 + registry 行 + kpi 行，**不新建 `docs/evidence/R615/`**（与 R614 同处置，不破目录约定）。

- **下轮候选 (R616)**: ① **豁免句单变量**（最高优先、`src/` 改动，未放行不动；须先写「改哪一格读数」= J1 键到达**且声明非空**跑次率）：删/软化新尾块里「plan 已表达的写文件/执行步骤**不要**在本字段里重复声明」⇒ 判据 = 有声明跑次由 **2/9** 抬升（≥ +2 跑次）∧ 轴关档仍 0/9 ∧ 前缀只加厚（重取 chars/sha 重钉）② **M3 第二刀 = 执行面接线**（`accepted` 消费者数 0；出口闸「调用数按 request_id 去重 ≤ 旧臂 50%」才可判）③ **wythoff 族双侧共同缺口**（真值也 43-56/58）⇒ 先判题面/夹具（R512 教训：两侧失败集合逐字相同 ⇒ 先怀疑夹具）再谈能力 ④ 铁律 11 可验收面（21 臂实跑但 10 臂未达 ⇒ 需要「多臂全绿」或显式降级写法先预注册）⑤ 文献小步（连续 0 采信计数 = R615 第 1 轮；达 3 轮 ⇒ 检索降频为每 3 轮一次，须在台账如实登记）。
- **R617（尾块**第二档单变量**：`豁免句 → 必声明句`；21 跑次；`src/`+`tools/` 有改动 ⇒ 被测件变更）**: **唯一单变量** = 提示尾块轴 `AGENTFRAMEWORK_R1_ACTION_PROMPT`（unset = R617 新块 / `r615` = R615 现盘尾块**逐字节**；`legacy` 档仍在册但本轮不作臂）；窗集 **w205..w207**（与历史 w184..w204 **不相交**）；臂 T×9 / C×9 / C1(codex 真值)×3；被测件 `artifacts/pub_r617/agenthost` sha256 `cd7c8dca2ae252c1a1b220a73152ff8eb041f82e271e963488105fc9ab994b44` ∧ `bin_sha_stable=true`；题集逐字节冻结 sha16 `e0c667c2a313c04b`。**产品侧最小改动**: 尾块里那句**豁免句**（「plan 已表达的写文件/执行步骤**不要**在本字段里重复声明」）⇒ 换为**必声明句**（「执行面**只读本字段**：plan 里需要工具执行的动作必须在本字段**逐条重复声明**一遍（只写在 plan 里 = 不会被执行）」）（`tools/r1gen/r1prompt.py`）+ R615 现盘尾块逐字节副本 `ACTION_CANDIDATES_R615` + 轴解析（`tools/r1gen/gen_csharp.py` → `src/agent/contract/StructuredPrompt.cs`）+ 单测 3 条（`R524PrefixStabilityTests`）。**只加厚不变量**（`prefix-r617.json`）: chars **15794→15796**；T pin sha `25c97bef…`；C pin sha `8b8be6b8…`（= R615 冻结 pin 逐位）；legacy 锚 `a9792fdb…`（chars 15675）。**真机读数**: **J0 臂轴生效 PASS**（T 9/9 pinned `25c97bef…` ∧ C 8/9 pinned `8b8be6b8…` ∧ 集合互斥；遥测缺席 **1** 单列 `instrument_gap` = `w207/agentC-r3` rc=124）；**J1（主判据）PASS** —— **有声明跑次 T 9/9 vs C 2/9**（R615 同判据基线 T **2/9**），**「到达但空数组」6/8 → T 0 / C 5**，到达面 T 9/9 vs C 7/9 ⇒ **R615 定位的病灶（豁免句）归因成立**；**J2b PASS**（T 9/9 跑次 `accepted+rejected==declared`，守恒违例 0）。**J4 能力面**: 整题全对 T **6/9 = 0.667**（Wilson95 [0.354,0.879]，逐窗 1/3·3/3·2/3）vs C **3/9 = 0.333**（1/3·1/3·1/3；**剔 rc=124 超时跑次后 3/8**）vs codex 真值 **3/3 = 1.0**；用例级 T 498/522 = 95.4% vs C 491/522 = 94.1%；预注册判据「T ≥ C+1 ∧ 无窗下降」PASS，但 **J5 跨窗集方向翻号**（R615 池化 T−C **−0.1111** vs 本轮 **+0.3334**）⇒ **能力面只作并列、不作结论**。**J3 成本 v2 FAIL**: 调用 Σ 16 vs 17 · 新算 prompt Σ 15,430 vs 15,845 · **单位调用新算 964.4 vs 932.1** · **completion Σ 66,509 vs 47,716 = +39.3%**（声明句的直接代价，如实入档）——**铁律 11 rc=1 ⇒ 一律「参考（未可验收）」**。**任务面 v3 PASS**（C1 真值 3/3 窗 58/58；D_list [−6,0,0]、中位 0、floor −15/−2 未触）；`W_floor` 有效窗 3。**铁律 11**（`precond-r617.json` rc=1）: 21 臂**独立物化 + 实跑 + 逐条机械判对**（`SELF_REPORT_AGREES=True` ∧ `EXECUTABLE_AND_CORRECT=False`），blocked 9 臂（`w205/C-r2 47` · `w205/C-r3 44` · `w205/T-r1 48` · `w205/T-r3 52` · `w206/C-r1 47` · `w206/C-r2 56` · `w207/C-r1 56` · **`w207/C-r3 rc=124 0/6`** · `w207/T-r1 50`），**codex 真值臂 3/3 窗全对**，主失败族 `wythoff#43..#57`（承 R615）。**自捕器具/流程缺陷 3 件（均修，读数未重测）**: **I1 判决器 v1 崩整轮汇总** —— J0 `sorted({None,str})` ⇒ `TypeError`（15:14 日志 Traceback 在案、无判决件）⇒ 缺测哨兵 `∅` + 覆盖度列 `D_telemetry_coverage` + `instrument_gap` 单列（缺席**不判红、也不吞掉**）+ pin 判定只取有遥测者；**负控有牙** `eval/rover/r617/nc_j0_r617.py` 四例 **rc=0**（PC 真 / NC1 单次缺席仍真且 gap=1 / NC2 两臂同 sha ⇒ 假 / NC3 全臂缺席 ⇒ 假，防「缺席当绿」空心）。**I2 铁律 11 首跑 BLOCKED=材料缺口** —— 本轮器具面缺 `eval/rover/r617/cases/` ⇒ 21 臂全 `missing_case_script`（判 **BLOCKED 而非 FAIL**，fail-closed 正确）⇒ 从 r615 **逐字节**补齐（`d9aecf4d397550b8…` / `270128eb85c7afc0…`，与 r610 同值）后**只重跑后处理**。**I3 首跑读数被同路径 `--out` 覆盖**（已披露；下轮起派生物名带 `-v1<原因>` 后缀）。**门禁**: 起手闸 A1/A2 PASS（`ceiling=2795 / prev_swing=70 / margin=70 / REQ=2720`；A1 2,905MB / A2 2,908MB）· 判别力成对控制 rc=0 · leak-selfcheck rc=0 · `roundcheck preflight --round R617` rc=0（P5 WARN = 本臂自身在飞，非对侧写者）· 形式门禁 **14/14** · `status_gen.py --check` **PASS**（违规 0 / 基准漂移 0 / 缺源 0）· **基线重钉** `F_env.prefix.chars`→15796 ∧ `F_env.prefix.sha256`→`25c97bef…` ∧ 新增 `F_env.prefix.r615_anchor`→`8b8be6b8…`。**诚实边界**: ① 只证「那句措辞决定**声明面**」，不证能力/成本收益（J5 方向翻号 ⇒ 能力面并列）；② 成本与降幅一律「参考（未可验收）」；③ `w207/agentC-r3` rc=124 超时 = 已知现象（R615 候选 ④）本轮**复现 1 例**；④ 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**；⑤ **M3 出口闸**（调用数按 request_id 去重 ≤ 旧臂 50%）本轮**不判**（`accepted` 只有声明没有执行接线，属第二刀）；⑥ 被测件变更轮 ⇒ 与 R585–R616 冻结件轮**禁相减、只并列**。**artifacts**: `eval/rover/r617/{dag-r617.md,prefix-r617.json,prefix_r617.py,prereg-r617.json,run_r617.sh,judge_r617.py,nc_j0_r617.py,aot_r617.sh,taskset-r617.json,bins-r617.json,gate-margin-r617.json,cases/,snapshots/,evidence/,report-r617.md,verdict-r617.json,kpi-table-r617.json}` · 台账 `eval/capability/kpi.jsonl`（R617，带 `baselines` 7 条）· registry 行 `r617.prompt-tail-block-mandatory-declaration` · 文献 `docs/research/lit-review-ledger.md`（追加 2 行：采信 C7 / 不采纳 1 / 证伪 0 / 顺延 0）。**证据文档形态说明**: 与 R614/R615 同处置 —— R 轮次证据面 = 轮报告 `report-r617.md`（registry 行 `artifact_sha12` 钉住）+ 本 §7 块 + registry 行 + kpi 行，**不新建 `docs/evidence/R617/`**。**注**: R616（器具面：roundcheck 违例基线治理）轮志在 `kpi.jsonl` + registry 行 `r616.roundcheck-baseline-governance`，§7 未逐轮同步（与 R610 同处置，只增量追加不补写历史轮）。
- **下轮候选 (R618)**: ① **M3 第二刀 = 执行面接线**（最高优先：`accepted` 消费者数 0 ⇒ 声明已 9/9 到岸而无人执行；出口闸「调用数按 request_id 去重 ≤ 旧臂 50%」须接线后才可判；前缀再动前先写「改哪一格读数」）② **completion +39.3% 的收口**（声明句的直接代价；候选 = 声明面**格式压缩**（同语义更短的行式）或**复用 plan 的 id/字段**，判据 = 有声明跑次不回落 ∧ completion 回到 C 档 ±10%）③ **wythoff 族双侧共同缺口**（真值臂本轮已 **3/3 全对** ⇒ 与 R615 的「真值也失分」不同源，须先判题面/夹具再谈能力；R512 教训）④ **`rc=124` 超时**复现 1 例（不调阈值；候选 = 单跑次超时预算显式化并单列 `invalid`，禁计入质量分母）⑤ **遥测覆盖率**：判决器已把缺席单列，须把「transcript 缺席」在**产生侧**补成可见失败（防「缺派生件当通过」，R587 纪律）。

- **R618（RF0004.2 · M3 **第二刀 = 执行面接线**；21 跑次；`src/` 有改动 ⇒ 被测件变更）**: **唯一单变量** = 新轴 `AGENTFRAMEWORK_R1_ACTION_EXEC`（**产品缺省 off**；T 档显式 `=1` = 执行面读采纳集，C 档 `unset` = 产品缺省 = 执行面读 `plan`；档位约定与 R617 相反是**故意的** —— 本轴缺省 off ⇒ 「轴关 = 旧行为」的臂就是缺省臂）；窗集 **w208..w210**（与历史 w184..w207 **不相交**）；臂 T×9 / C×9 / C1(codex 真值)×3；被测件 `artifacts/pub_r618/agenthost` sha256 `886db888d744a6196dbdefd6aa482c8fc0b966eaab16fac7e6c3add44a0f3ca6`（19,834,064 B；AOT `PUBLISH_RC=0 / IL_WARNINGS=0`）∧ `bin_sha_stable=true`；题集逐字节冻结 sha16 `e0c667c2a313c04b`。**产品侧最小改动（第二刀）**: ① 新记录 `AcceptedAction`（id/工具/args **原文**/理由）= 采纳集载体，`ActionCandidates.Selection` 增 `AcceptedActions`（`src/agent/r1/AcceptedAction.cs` · `ActionCandidates.cs`）② 新映射器 `ActionExecPlan`：采纳候选 ⇒ 执行面节点（窄腰 `write_file`/`run`），**不另立工具表**（同源 `ActionToolDecl`），窄腰外工具计 `unmapped`（**禁静默丢**），自述期望 `expect_stdout` 由 `plan` 里 (工具,参数) **逐字命中**节点**继承** ③ **唯一接线点** `src/agent/r1/R1Pipeline.cs`（`execPlan = map.Steps` 取代 `sem.Plan`；轴关 ⇒ `execPlan == sem.Plan` **逐位等价**）④ 台账四字段 `exec_source`/`_executed`/`_unmapped`/`_expect_inherited`（**轴关 ⇒ 字段缺席**，`R1Transcript.cs`/`R1RunResult.cs`）⑤ 单测 `ActionExecPlanTests`（9 条：零回归逐位 / 映射守恒 / 坏参数不静默 / 期望继承 / 空候选 / 轴档解析 / 真实落盘副作用 / 早退语义）⑥ 判据器 `eval/rover/r618/judge_r618.py`（J0/J1 重写 + **读取契约并入本轮新键**，承 R617 I1 教训）+ **影子自检五态** `selftest_judge_r618.py`（正常 / 两臂不可区分 / 真空 / 守恒违例 / 跨轮锚不成立，**rc=0 全态符合**）。**前缀零改动**：`tools/r1gen` 未动 ⇒ T/C 两档 `prefix_sha256` **均为 `25c97bef…`**（= R617 T 档 pin 逐位）⇒ 跨轮锚成立（`claims_violated=[]`）；API 基线重钉 **20 行**（全属本轮新增成员，差异仅本轮行）。**真机读数（21 跑次）**：**J0 臂轴生效 PASS**（T `exec_source=candidates` **9/9** ∧ C 四新字段出现跑次 **0/9** ∧ 两臂前缀同源 ∧ 每臂非全缺席）；**J1（主判据）PASS** —— `executed>0` 跑次 **8/9**、四字段齐备 8/9、**条目守恒违例 0**（`unmapped<=accepted ∧ executed<=accepted−unmapped ∧ inherited<=accepted−unmapped`；**起臂前 v2 修订**：等式改不等式，因计划执行器可在任一步**早退**，等式会把合法早退记成器具缺陷）、`unmapped` 合计 0 / 自述期望继承合计 **26**（⇒ 换载体未丢自检面，可机检）⇒ 第一刀「`accepted` 消费者数 0」缺口在**执行面**闭合（闭合由读数判，不由代码行判）；**J2b PASS**（8/9 跑次 `accepted+rejected==declared`，违例 0）；**J2 修复收敛不达**（converged T 2/9 vs C 5/9，并列不动 rc）。**J4 能力面（并列，欠功率）—— 负向**: 整题全对 T **4/9 = 0.4444**（Wilson95 [0.189,0.733]，逐窗 3/3·1/3·0/3，用例中位 49）vs C **6/9 = 0.6667**（[0.354,0.879]，2/3·3/3·1/3，中位 58）vs C1 真值 **2/3**（w208 52/58 = **真值自败窗**）；逐窗配对差 `T−C` **+0.333 / −0.667 / −0.333**、`T−C1` +1.0 / −0.667 / −1.0 ⇒ **J5 跨窗集方向不一致**（R617 池化 +0.3334 → 本轮 **−0.2223**）⇒ 按「摆动 ≥ 效应 ⇒ 非承重」**该轴在能力面不构成提升**；`W_floor` 有效窗 **2** ⇒ 判据行使，任务面 v3 label **不达**（D_list [−11,−15]，中位 −13；我方 47/43 vs 真值 58/58）。**J3 成本（一律「参考（未可验收）」）**: 调用 Σ 16 vs 16 · 新算 prompt Σ 12,138 vs 12,054 · **单位调用新算 758.6 vs 753.4 ⇒ b1 更差** · completion Σ 59,803 vs 58,603（**+2.0%**）· 命中率 v_all 0.9035–0.9709 vs 0.9071–0.9709 · `bad_dumps` 0 ⇒ J3 v1 PASS / **v2 FAIL**（`a2_per_window_calls:w209` ∧ `b1_unit_new_prompt`）⇒ **无降幅可宣称**。**失败定因（逐条可机检，禁超证据归因）**: **D1 无候选 ⇒ 空执行面 ⇒ 零步执行**（`w210/agentT-r1`：`declared/accepted` 缺席 ∧ `exec_source=candidates` ∧ `executed=0` ∧ `plan_steps_total=10` ⇒ 该跑次**什么都没跑**，而对照档会跑 plan 的 10 步）= **轴引入的新失败形态**，为能力面负向的直接来源之一；**D2 候选序 ⇒ 早退更早**（6/9 T 跑次 `executed=6 < mapped`，`w210/agentT-r2` reason = `step a7 stdout 与 expect_stdout 不符`；对照档同题 `15/15`）—— **未定因**（候选序 vs plan 序差异**未证**）；**D3** 一跑次 `rc=8 public_probe_unmet`（产物未成型，既有族，与 D1 不同源，**两个 0/58 不得合并叙述**）。**铁律 11**（`precond-r618.json` rc=1）: 21 臂独立物化实跑，**blocked 9**（T 5 / C 3 / codex 1；含 `w209/agentT-r1` 与 `w210/agentT-r1` 各 **0/58**、codex `w208` 52/58）；首跑 `BLOCKED=missing_case_script`（器具面缺 `eval/rover/r618/cases/`，判 BLOCKED 而非 FAIL，fail-closed 正确）⇒ 从 r610 **逐字节**补齐（`run_cases_r521.py` sha16 `d9aecf4d397550b8` · `cases-r521.json` sha16 `270128eb85c7afc0`，与 r615 同值）后**只重跑后处理、不重测**。**门禁**: `roundcheck preflight --round R618 --min-avail-mb 2775` **rc=0**（起手前清 VBCSCompiler −534MB / pyright −323MB ⇒ 2,244→2,824MB）· 起手闸 A1/A2 PASS（`ceiling=2814 / prev_swing=125 / margin=104 / REQ=2754`；**`cap_binding=true`** 振幅项退化，已落盘 `gate-margin-r618.json`）· 判别力成对控制 rc=0 · leak-selfcheck rc=0 · 判据器影子自检 5 态 rc=0 · 形式门禁 **14/14** · `status_gen.py --check` **PASS**（违规 0 / 基准漂移 0 / 缺源 0）。**诚实边界**: ① 机制 PASS ≠ 能力收益：能力面**负向**且受欠功率与摆动支配，禁宣称任何提升；② 第二刀只接**动作面**，信息类工具（`read_file`/`list_dir`/`delete_file`）属第三刀；③ 轴**默认 off、未放行**（关闭态由逐跑次字段缺席 + 单测逐位双钉）；④ 成本/质量一律「参考（未可验收）」（铁律 11 rc=1）；⑤ **M3 出口闸**（调用数按 `request_id` 去重 ≤ 旧臂 50%）本轮**只作读数不作验收**（R1 链每任务 1–2 次调用，旧「自由文本动作环」为跨轮形态 ⇒ 分母不同源，禁跨形态相减）；⑥ 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**；⑦ 被测件变更轮 ⇒ 与 R585–R617 冻结件轮**禁相减、只并列**。**artifacts**: `eval/rover/r618/{dag-r618.md,prereg-r618.json,report-r618.md,run_r618.sh,judge_r618.py,selftest_judge_r618.py,closeout_r618.py,aot_r618.sh,repin_api_r618.sh,taskset-r618.json,bins-r618.json,gate-margin-r618.json,verdict-r618.json,kpi-table-r618.json,cases/,snapshots/,evidence/,cases/}` · 台账 `eval/capability/kpi.jsonl`（R618，带 `baselines` **11 条**）· registry 行 `r618.exec-face-wiring`（L3）· 文献 `docs/research/lit-review-ledger.md` §16（2 检索式 ⇒ 采信 2 / 未实施队列 1（C8）/ 证伪 0 / 顺延 0）。**证据文档形态说明**: 与 R614–R617 同处置 —— R 轮次证据面 = 轮报告 `report-r618.md`（registry 行 `artifact_sha12` 钉住）+ 本 §7 块 + registry 行 + kpi 行，**不新建 `docs/evidence/R618/`**。
- **下轮候选 (R619)**: ① **第三刀 · 空候选回退**（最高优先：D1 形态 —— 候选键未到达/采纳面为空时回退读 `plan`；轴仍默认 off；判据 = 同窗对照 ∧ `exec_source` 三态取值（`candidates`/`plan`/`plan_fallback`）可见 ∧ 轴关逐位零回归）② **第三刀 · 序/依赖面**（D2 —— 窄腰内写盘先于执行的依赖排序；须在 ① 落定后单独起轮，**禁双自由度**；判据 = 同窗 reps≥3 + 逐窗 + 中位 + 极差 + 早期退出步次可见）③ **能力面负向的复核**（本轮 T 4/9 vs C 6/9 且 J5 翻号 ⇒ 摆动 ≥ 效应；先补 reps/扩窗，**禁调阈值**）④ **completion 面**（本轮 +2.0%，R617 的 +39.3% 已回落 ⇒ 该缺口按 R617 判据可关闭或降级为观察）⑤ **wythoff 族双侧共同缺口**（本轮 codex 真值 w208 亦 52/58 ⇒ 与 R617 的「真值全对」不同源，须先判题面/夹具，R512 教训）⑥ **信息类工具的回执走尾部载体**（第三刀的一部分，需先写「改哪一格读数」）⑦ **pre-existing 红登记**（本轮**首发现**，非本轮引入）：`eval/capability/exp1-q30/check_committed_state_q30.py` 判 **FAIL(1)** —— registry 行 `internal.r536-r1-contract-deadend-and-rc-split` 的 `artifact_sha12` 钉在 `eval/rover/r536/run-w1/logs/analysis-w1.json`，而该路径被 `eval/rover/.gitignore:3: run-*/` 覆盖 ⇒ **原理上不可入 index**（`git log -- <path>` 空 ∧ HEAD~1 亦无该 blob ⇒ 提交前后同态，非本轮造成）。候选修法（择一，须由 R536 所有者语义裁定）：① 该行改 `pin_status: live`（run-* 目录按设计不入库）② 或把证据件搬到可入库归档路径后重钉；禁静默改写他轮证据声明。

- **R621（RF0004.2 · M3 **第五刀 = 等价面分辨率取证 + 判据分级**；39 跑次；**零产品源码改动** ⇒ 与 R619/R620 逐字节同件 sha `a184d731…`）**: **唯一变量** = 与 R620 同轴同档位（`AGENTFRAMEWORK_R1_ACTION_EXEC`，held-constant = `AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy` 两臂同值），本轮**只动器具面**：判据 v3→v4（J6 移出 `instrument_defects` ⇒ rc 分级 0/1/2/3；J6 三态化）+ reps 3→6/窗 + 影子自检新建。窗集 **w217..w219**（与历史 w184..w216 不相交）；臂 T×18 / C×18 / C1(codex 真值)×3；题集逐字节冻结 sha12 `e0c667c2a313`。**真机读数**：**J0 PASS**（T 18/18 `exec_source=plan_fallback` ∧ C 五字段 0/18 ∧ 两臂前缀同 sha `a9792fdbe5b2…` = legacy 锚 ⇒ held-constant 真生效）；**J1（机制面主判据）PASS**（回退行使 **18/18**、三态 `EXERCISED_OK`、`candidates∧executed==0` 形态 0）；**J6 三态 = `NO_RESOLUTION` ×3 窗**（Δ中位(C−T) = −6.0 / −0.5 / −1.5，而同臂极差恒 **15** ⇒ 摆动 ≥ 效应 ⇒ **不可判**）⇒ 按 RF0005 §3 R5 记「该等价面非承重变量、**定案关闭**」，**禁为同一缺口再加轮**（reps 3→6 的补救已用尽）；**rc = 0 / `mechanism_rc` = 0**（`defects=[]` ∧ `mech_secondary=[]`）—— R620 同批数据会被编码成 `rc=2`（器具层）而本轮分层后不再如此，两轮 rc **不可直接并列**。**能力面（J4 次级·欠功率·并列）**：整题全对 T **12/18 = 0.667**（逐窗 6/3/3）vs C **6/18 = 0.333**（3/2/1）vs 真值 **3/3 = 1.000**；配对逐窗 T−C **+0.5 / +0.167 / +0.333**（同向为正），T−C1 **0.0 / −0.5 / −0.5** ⇒ **未追平外部真值**。**承重缺口定位（族分列）**：life 250/252 · sub 252/252 · nim 270/270 · **wythoff T 223/270 (82.6%) vs C 158/270 (58.5%) vs 真值 45/45** ⇒ 失败**几乎全在 wythoff 族**且**真值全对** ⇒ 非夹具缺陷、非两侧同败，是产品侧真实能力缺口（回退面在该族 +24pt）。**J3 成本 v2 = FAIL（如实，阈值零改动）**：调用 Σ **35 vs 34**（w217 逐窗 12 vs 11）· 新算 prompt Σ 29,871 vs 28,939 · 单位调用新算 **853.5 vs 851.1** ⇒ 三条款全不成立，**无降幅可宣称**；命中率 v_all 中位 0.9103 vs 0.9087 / v_incr 0.8491 vs 0.8449（口径 = 中继 dump 时间轴；未上报 0）。**J5 PASS**（池化 (T−C) 本轮 **+0.3334** 与 R617 表 +0.3334 同号）。**铁律 11**（`precond-r621.json`，rc = 1 由 `acceptable_scoped=false` 派生）= **全部质量/成本读数标「参考（未可验收）」**（blocked 18 臂窗，失败全在 wythoff 族；真值 3/3 全对 ⇒ 未可验收由我方臂造成）。**门禁**：起手闸 A1/A2 PASS（`ceiling=2836 / prev_swing=119 / margin=119 / REQ=2769`；A1 2,858MB / A2 2,859MB）· 判别力成对控制 rc=0（0 真行使 / 3 未行使已登记）· leak-selfcheck rc=0 · 前提闸 rc=0（`plan_fallback` ∧ `candidates_absent` ∧ 前缀 == legacy 锚）· 判据器**影子自检 11/11** · 形式门禁 **14/14** · `status_gen.py --check` **PASS（违规 0 / 基准漂移 0 / 缺源 0）**。**自捕器具缺陷 2 件（均未放宽判据）**：① **J6 状态机「比较变量写反」**（起臂**前**由影子自检抓到 ⇒ Δ 符号约定写进字段名 `delta_median_C_minus_T`，修代码不放宽断言）；② **`label` 口径矛盾**（旧式直接读 `j2b_pass`，而 legacy 档 J2b **结构性 N/A** ⇒ 与 `mechanism_rc` 谓词不一致）⇒ 只改 label 文本并**逐字段 diff 取证**（两版 verdict 相交键仅 3 项变化：`verdict.label` / `checks_posthoc` / `driver_sha12`），修前判决件 `verdict-r621-preLabelFix.json` **原样保留**。**运行期外因（已披露）**：内存采样中一枚 237MB 编辑器 LSP 压低该窗读数（已按 pid 清场；下轮 swing 重派生方向**保守**）。**诚实边界**：① J6 = 不可判（**禁读作零回归、禁读作通过**）；② 质量/成本一律「参考（未可验收）」；③ J4 n=6/窗欠功率 ⇒ 只作并列；④ 与 R620 **禁相减、只并列**（rc 编码层不同）；⑤ `claims_violated`：撤回「前缀零改动」宣称（本轮 held-constant 换 legacy 档，同轮可比性不受影响）；⑥ 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**。**artifacts**：`eval/rover/r621/{dag-r621.md,prereg-r621.json,derive_r621.py,run_r621.sh,judge_r621.py,selftest_judge_r621.py,closeout_r621.py,taskset-r621.json,bins-r621.json,gate-margin-r621.json,premise-r621.json,verdict-r621.json,verdict-r621-preLabelFix.json,kpi-table-r621.json,report-r621.md,evidence-run-r621.txt,cases/,snapshots/,evidence/}` · 台账 `eval/capability/kpi.jsonl`（R621，带 `baselines` 11 条）· registry 行 `r621.equivalence-resolution-and-rc-tiering`（L4）· 文献 `docs/research/lit-review-ledger.md` §18（3 检索式 ⇒ 采信 0 / 已实施（既存）1 / 不采纳 1 / 顺延 0；连续 0 采信第 2 轮）。**注**：R619/R620 轮志在各自 `report-r619/r620.md` + `kpi.jsonl` + registry 行，§7 未逐轮同步（与本文件既有处置一致，只增量追加、不补写历史轮、不改旧读数）。
- **下轮候选 (R622)**: ① **wythoff 族能力缺口定因**（最高优先·零产品改动即可做）：用本轮 `snapshots/` 冻结产物逐例复算 + 独立 oracle 四分归因（真错 / 合法非期望解 / 状态误判 / 格式差异），判据 = 目标子型占比 ≥50% 且 oracle 正控绿 ∧ 变异零误放行 ② **等价面判据重启条件**（已关闭）：仅当换**逐例级**判据粒度 ∧ 摆动 < 效应时重开，须先预注册新粒度 ③ **J3 成本三条款同向差**（+1 调用 / +932 新算 / +2.3 单位）⇒ 按中继 dump 逐档分解定位 ≥50% 差额来源 ④ 文献面 = wythoff 类「博弈解生成-验证分离」机制（预算 3 query / 轮）⑤ 「信息类工具回执」与「序/依赖面」仍挂 R619 候选（未闭合，随主线推进）。

- **R622（RF0004.2 · M3 **承重缺口定因轮（只读）**；**零产品源码改动 / 零新臂 / 零远端调用 / 零新增夹具语义**）**: 承 R621 候选 ①。**唯一动作面 = 器具**：新建与被测**零共享代码**的独立 oracle（来源 = 冻结题面**逐字规格**，路线 = 按 `a+b` 升序的定义式 DP 求 P 位 + 枚举三族着法取字典序最小；**不使用期望输出、不读 cases**）+ 逐例四分 + **行为式**机制归因（问产物自身接口）+ 夹具普查/成本分解/崩溃取证 + 机械裁决，对 R621 冻结产物（`snapshots/w{217,218,219}`，39 跑次 × 15 例）只读复算。**读数（全部可复现；`percase` 两次跑次 sha256 同值 `344ffa22…`）**：**J0 oracle 正控 PASS**（15/15 复现冻结期望字节）· **J1 变异负控 PASS**（v2 逐例对应 mismatch **0/45**；**v1 判据「变异体非 OK == 15/15」首跑即证伪**，实得 4/15 · 12/15，原样入档 `out/negctl-r622-v1.json` **不翻案**）· **J2 PASS**（复算 == R621 冻结裁决；期望从 `verdict-r621.json` 的 `J4.by_arm.*.families.wythoff` **派生**，非写死常量）· **J3 PASS**（159 个非 OK 实例 100% 落入四分，无残留桶）· **J4（主判据）PASS**（目标子型 71.1% ≥50%）· **J5 PASS**（codex 真值 **45/45** 全对 ⇒ 非夹具缺陷、非两侧同败，R512 教训）⇒ `rc=0`。**承重缺口定因（本轮核心产出）**：wythoff 族 **T 223/270 (82.6%) vs C 158/270 (58.5%) vs 真值 C1 45/45**；159 非 OK 实例四分 = `TRUE_WRONG` 74 · `STATE_FLIP` 52 · `HARD_CRASH` 31 · `LEGAL_NONMIN` **2**（⇒ 判据僵硬**非**主因）· `FORMAT` 0。**机制归因 = 判定层主导**：`COLD_PRED_WRONG` **113 (71.1%)** + `CRASH` **31 (19.5%)** = **144/159 = 90.6%**；选点层 `ILLEGAL_MOVE` 9 · 枚举序 `ENUM_ORDER` 2 · `UNCLASSIFIED` 4 ⇒ 「冷点谓词 / 胜负态判定」是承重段，「选点 / 枚举序」仅 6.9%（⇒ 加厚「最小着法」提示的收益上界很低）。**CRASH 与判定层同源、有代码级证据**：产物树副本上 `python3 -B -m games wythoff`（输入 `21 25`）⇒ `rc=1 / stdout 空 / games/wythoff.py:48` `i, j = best` 上 `TypeError: cannot unpack non-iterable NoneType` ⇒ 谓词全否 ⇒ `best=None` ⇒ **未自验即交付**（与 R600 登记的「主桶 = 冷集构造层」不冲突但**独立定因并量化**：本轮把该桶拆成判定层 90.6% / 选点层 6.9%，并**新增**同源硬崩一桶；**不沿用旧结论**）。**候选 ③（成本三条款同向差）本轮一并收口**：逐档分解净差/Σ|Δ| = **0.0851** · 单档最大 |Δ| 占比 **0.1402**（均 <0.5）⇒ **无 ≥50% 集中来源**，差额为对称摆动残差 ⇒ 按 RF0005 §3 R5「摆动 ≥ 效应 ⇒ 该轴非承重变量、**定案关闭**」，**禁再加轮**（方向：签名约定 `C−T` ⇒ 新算 prompt T 29,871 vs C 28,939 = **T 多花 932 / +3.2%**，伴随用例级 +24pt）。**夹具面登记（J1 v1 证伪的副产物，不判能力）**：该族「字典序最小」子型**仅 3/15 例被行使**（多解例），退化解「取字典序最大必胜着法」拿 **12/15 = 80%** ⇒ 夹具判别力偏弱；受「禁新增夹具」令约束，只登记候选、**须用户放行**才可加隐藏用例。**门禁**：`roundcheck preflight --round R622` rc=0 · 形式门禁 **14/14**（首跑 **13/14**：`artifact_sha12` 误钉**裁决件**而非 `evidence_path` 指向的报告 ⇒ roundcheck `R4_pin_matches` + `VerificationFormTests` 同报，**重钉到报告字节后转绿**，属**自伤**非产品回归，首跑读数保留不翻案）· `status_gen.py --check` **PASS（违规 0 / 基准漂移 0 / 缺源 0）** · `roundcheck audit --round R622` **FAIL=0**（仅 R9 提交后暂存面空 WARN）· build **0 error** · commit `480530e8`。**文献小步**：4 式（**超上限 1 式** —— 前 3 式输出在上下文压缩中丢失 ⇒ 按新检索计入，如实登记）+ 1 摘要取件；**采信 1 条**（arXiv **2606.25276v1**，cs.GT，**纯预印本** ⇒ 权威代理最低档）⇒ 机制假设 = 「某公式是否**恰好刻画**胜负态集合」一般**不可判**、**终止**情形可判 ⇒ 用谓词判 P 位须先固定**终止性前提**并给**可判定的刻画校验**；**不采信 1 条**（引号短语被拆散 ⇒ 结果数虚高 179,869、返回「当日最新」⇒ 记「未取到原文」，下轮改 `ti:`/`abs:` 复测）。台账 = `docs/research/lit-review-ledger.md` §19（连续 0 采信计数归零 ⇒ 检索不降频）。**诚实边界**：① 本轮**无对照臂、无产品改动、无远端** ⇒ **不产出任何降幅/达标读数**，质量与成本面沿用 R621「**参考（未可验收）**」（铁律 11 rc=1）；② `rc=0` **仅**表本轮判据全绿，**禁**读作能力/成本达标；③ 机制归因基于**行为式谓词** ⇒ 只判「产物是否自认该落点为必败位」，**不判**其内部实现；④ 与 R585–R621 冻结件轮**禁相减、只并列**（`baselines` 的 wythoff 项 = 135 例次/9 跑次口径，本轮 270 例次/18 跑次 ⇒ **只比通过率、禁比总和**）；⑤ 判定层与选点层的**因果顺序未判明**；⑥ 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**。**artifacts**：`eval/rover/r622/{wythoff_oracle.py,attrib_r622.py,mech_r622.py,aux_r622.py,closeout_r622.py,closeout_write_r622.py,prereg-r622.json,dag-r622.md,report-r622.md,verdict-r622.json,out/}` · 台账 `eval/capability/kpi.jsonl`（R622，带 `baselines` 10 条）· registry 行 `r622.wythoff-attribution-and-mechanism`（L3）· 文献 §19。**证据文档形态说明**：与 R614–R621 同处置 —— R 轮次证据面 = 轮报告 `report-r622.md`（registry 行 `artifact_sha12` 钉住）+ 本 §7 块 + registry 行 + kpi 行，**不新建 `docs/evidence/R622/`**。

- **下轮候选 (R623)**: ① **判定位替换（最高优先，`src/` 改动 ⇒ 未放行不动；须先写「改哪一格读数」）**：把该族判定位从「模型/学习谓词」换成**构造性可判定过程**（枚举 DP / SG 表）+ 显式**终止性前提**（文献 L4 机制假设）⇒ 判据 = wythoff 用例级通过率 **0.585 → ≥0.80** ∧ `COLD_PRED_WRONG` 占比 **≥71% → ≤10%**；可证伪点 = 提升 **<10pt** 即该机制假设证伪 ② **交付前自验**（同源硬崩 29 例 C 臂的直接对策；轴 = 产出非得空值 + 盘上用例回放；判据 = `HARD_CRASH` **29 → 0**）③ **夹具判别力**（「字典序最小」多解例补样：现 3/15；判据 = 退化解 `M2` 由 12/15 降到 ≤6/15）—— 受「禁新增夹具」令约束，**须用户放行** ④ **等价面**已定案关闭（R621 J6 `NO_RESOLUTION`）；**成本三条款差**本轮亦定案关闭（无集中来源）⇒ 两者**禁再加轮** ⑤ 「信息类工具回执 / 序依赖面」（R619 候选，未闭合，随主线推进）。
