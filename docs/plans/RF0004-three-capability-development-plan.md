# RF0004 · 三能力开发计划（开放域识别 / 生成类 / 多轮工具编排）

> 缘起（用户令，2026-09-21 逐字）：**「开放域识别，生成类，多轮工具编排都做，由你安排开发计划」**
> ⇒ 本文件是这三条能力面的**排期与验收唯一权威面**；RF0001 §4 中「识别类推迟 v2」的理由**作废**（见 §0.2）。
> 依赖面：RF0001 §0/§3/§6 + **铁律 10–14**（其中 **14 = 任务类型-器件选型**，本节落地定义见 §0.4）+ 闸流程令 + `RF0005-completion-protocol.md`（执行协议）

状态：**活计划**（每轮刷新「已落地/待做」，不改历史结论） ｜ 建立轮次：**R607** ｜ 机检口径：出口闸见 §3

---

## 0. 口径与作废项

### 0.1 三能力的可机检定义（防「名义做了、读数没动」）

| 能力 | 定义（机检判据） | 不接受的实现 |
|---|---|---|
| **开放域识别** | 输入任意域文本 ⇒ 产出 `{标签 \| abstain, 依据}`；**abstain 可升级**（未命中时走远端回执补丁，下次命中）；**不绑定固定标签集、不新增本体** | 把既有闭合词表/固定枚举换名成「开放域」；或用远端 LLM 全量代劳（违反「agent 主体 = NLP」） |
| **生成类** | 任务档为 `Generation` 的调用：产物是**新内容**（代码/文本/文件），且**有产物验收器**（独立回放，非模型自裁判） | 把 `CodeAnalysis`/模板填充当生成；用 completion 长度冒充质量 |
| **多轮工具编排** | 同一条链内 **≥2 次工具调用**，且**编排决策来自结构化字段**（非自由文本动作环）；工具回执只走尾部载体 | 直接开旧动作环（对照臂 R544：34 调用 / 714,287 tok / 46-58 ⇒ 成本爆炸）；把工具面全量常驻前缀 |

### 0.2 作废与修订（逐条，避免口径漂移）

1. **作废**：RF0001 §4 排除项中「v1 判据未包含识别面 ⇒ 识别顺延 RF0002」的理由。**视觉侧路（LFM2.5-VL 屏幕识别/视频学习/区域特征库）仍排除**（CPU-only 2 vCPU，图像 prefill 5.6 tok/s ⇒ 351 s/帧）。
2. **v1 发布判据扩张**：原四判据（质量 / token / 前缀缓存 / 前端 api）**∪** 三能力 KPI（§4）⇒ 共七面。
3. 「识别类推迟 v2」「开放域识别·生成类·多轮编排 = 不做」的旧口径**全部作废**。
4. RF0001 §5 阶段表**保持有效**（RF0001.x 仍按原出口闸收）；RF0004 是其**并行/后继版本面**，不与 RF0001.x 抢同一单变量。

### 0.3 硬约束（承袭，逐条机检）

AOT/零反射/单二进制（改链代码必重发布；publish 禁加 `/p:PublishAot`）· 单类型单文件/命名空间=目录（`RefactorStructureTests`）· **恒前缀 ≥97% 且只允许「加厚」**（`PrefixMinCharsForCache97` 门，`CachePrompt=true`）· 远端 LLM 调用 = **skill 插件服务**形态 · 每轮**单变量 + 预注册 + 同窗真机对照 + 铁律 11 `rc=0`** 才算可验收 · 成本判据**两形态并列、禁跨轮相减** · **真值不得当硬上限**（`truthdrop` 证）· 打点机检（治疗面 >0 ∧ 对照面 ==0）· 零产品改动臂必须先**证明变量可生效**再消融（R583/R602 教训）· 提交禁 `git add -A`、`PUSH_PAUSED` 在效 · 零新增夹具（要动代码须先说明它改哪一格读数）。

### 0.4 三档任务的目标读数与现方案落点（铁律 14 的落地定义面，唯一权威；R611 立 / **R613 按用户令修订**）

> 用户令原句（逐字）：**「如果你的任务是分类/路由/评分/意图识别 → 直接用Laya或XGBoost，32ms搞定，零API成本；如果需要文本理解但输出空间有限 → 微调BERT/RoBERTa，精度持平LLM但快50倍；如果需要生成开放文本 → 传统NLP做不到，必须用LLM或扩散模型。实测效果：延迟降低95%，成本降低85-91%，任务成功率不变。」**
>
> **修订令（同日，逐字，优先于上段）**：**「不用laya还是我们现在方案，仅是最后达到那个数据，请修正文档」** ⇒ **器件路径不变**（不采用 Laya）；三档数值降级为**终局目标读数（待达成）**。

| 档 | 任务特征 | 目标读数（终局口径 · 待达成） | 现方案落点（代码事实） | 状态 |
|---|---|---|---|---|
| **① 判别/路由类** | 分类 · 路由 · 评分 · 意图识别 | 32 ms 级、零 API 成本 | `src/agent.nlp/` 形态/账本规则 + `TaskRelevanceChecker` + `LocalChannelPolicy` 前置门（`DefaultAllowedKinds`） | ◐ 现方案在场；R612 真值：真实流量门判 42 次全为机械族/守卫、真问本地 **0** ⇒ 目标读数未测 |
| **② 受限输出理解** | 需文本理解但输出空间有限（复述 / 认可 / claim 面） | 精度持平 LLM、快 50× | 残余带由**本地 3B LLM** 打分（`ModelQueueRouter.LocalChannel` → `JudgeTurnAsync`；R609-AB 真机 **17.2 s/例**）；形态库学习 = RF0002 | ◐ 保持现方案；目标读数未达成 |
| **③ 开放生成** | 生成新文本 / 代码 / 文件 | ——（原第③句是**能力边界**，非读数） | 远端 LLM = **skill 插件服务**；本地生成端口 `ILocalGenerationPort` | ✅ 形态正确（生成档 `TaskKindHint.Generation` 仍缺 ⇒ §1） |

**三档共用口径纪律**：① 本表数值（32 ms / 快 50× / 延迟 −95% / 成本 −85~91% / 成功率不变）全部为**外部读数**（TabAgent, arXiv **2602.16429** + 其自报 32.8 ms 单 GPU），**是终局目标口径** ⇒ **不得直引为本仓结论、不得记作已达标**；② **器件路径按现方案（不引入 Laya）**；将来若有人再提外部判别器件，四条前提 —— **标签可分 / AOT 可用 / 本机可跑 / 跨语言** —— 缺一即否决（展开见主线铁律 14）；③ 验收仍按 §3 出口闸 + 铁律 11 `rc=0`，成本判据两形态并列、禁跨轮相减。

---

## 1. 现状盘点（代码事实 ⇒ 缺口；每格给出文件:行）

| 能力 | 已有组件（代码事实） | 接线状态 | 缺口（可机检） |
|---|---|---|---|
| **开放域识别** | `src/agent.nlp/`：`NlpGate`（faces `gate/repeat/para/claim`，`FaceSeparator='\t'`）、`LearnedShape`、`GateFeatures`/`GateDecision`/`TextSignal`/`TextTokens`/`LanguageIdentifier`；消费点 `src/agent.modelqueue/LocalParaphraseChannel.cs:92,221`、`TurnGateJudge.cs:88-98`（R575 回补面） | ◐ 只服务**门**（paraphrase/claim/repeat），无对外统一识别出口 | ① 无 `{标签\|abstain, 依据}` 的统一出口结构；② 泛化单位只有 `CharSet`/`Band`（无域维）；③ 无「abstain ⇒ 远端 ⇒ 补丁 ⇒ 下次命中」的**闭环打点** |
| **生成类** | `src/agent.modelqueue/ILocalGenerationPort.cs` + `LlamaCppTextGenerator`（LFM2.5-VL-3B-Q4，**15.8 s/次**，RSS 2,643 MB）；`ModelQueueRouter`（远端）；`src/agent.codegen/`（`CodeAnalysis`/`CodeTemplate`/`Symbol` —— **纯分析/模板，非 LLM 生成**）；`TaskKindHint`（`General/ContextCompression/KeywordTagging/TendencyAnalysis/IntentClassification`，**无 Generation 档**） | ◐ 本地端口已接线；**生成档不存在** ⇒ 计价/选模/本地-远端路由无法区分生成类 | ① `TaskKindHint` 缺 `Generation` ⇒ `LocalChannelPolicy.cs:18-21`/`ModelSelectionPolicy.cs:14-17`/`ChannelScheduler.cs:87-88` 三处白名单均无生成档；② 生成产物无验收器（R1 只对**可执行**产物用 `PublicExampleProbe` 公开用例独立回放）；③ 本地生成无预算/流式控制 |
| **多轮工具编排** | **已存在且已接线**：`ModelQueueAdapter.cs:154`（`_actionPort != null && ActionLoopRunner.IsEnabled()`）⇒ `ActionLoopRunner.RunAsync`；工具面 `ActionToolDecl`（5：`DeleteFile/ListDir/ReadFile/RunCommand/WriteFile`）+ `ActionToolSpec`（声明面与执行面同源，单测锁死）；上限 `DefaultMaxSteps=6`/`StepExtendBy=6`/`StepCeiling=32`/`MaxToolResultBytes=8192`/`DefaultToolResultChars=600`；纪律文本 `ActionLoopDiscipline`（`AGENTFRAMEWORK_ACTION_DISCIPLINE`）；开关 `AGENTFRAMEWORK_ACTION_LOOP`、`_ADAPTIVE_BUDGET`、`_MAX_STEPS`、`_RESULT_CHARS` | ◐ **是旧自由文本动作环**（对照臂）：R544 实测 34 调用 / 714,287 tok / 46-58 | ① 编排决策在**远端自由文本**（违反「主体=NLP」令）；② `_ADAPTIVE_BUDGET` 是否真生效 **待确认**（消融前必先证变量可生效）；③ 工具回执与「恒前缀 ≥97%」张力：回执只能走尾部载体，当前无该约束断言 |

---

## 2. 机制假设（复用优先；每条声明**改哪一格读数**）

> 原则（用户令）：**不新增夹具、不做额外开发**；只有能说清「改六格中哪一格」的改动才立项。

| # | 假设（机制） | 复用件（零新建） | 改哪一格 | 证伪条件 |
|---|---|---|---|---|
| M1 | **统一识别出口**：`NlpGate` 决策与 `GateFeatures` 直接渲染成 `RecognitionVerdict{Label\|Abstain, Evidence}`，只读地接到 `TurnGateJudge` 的既有打点 | `NlpGate`/`GateFeatures`/`GateDecision`/`TurnGateJudge` | ⑥ 回复质量（识别命中率↑）+ ⑤ tokens（远端调用↓） | 打点后 abstain 率不降 ∧ 远端调用不降 |
| M2 | **生成档 + 产物验收器**：新增 `TaskKindHint.Generation` 走既有三处政策白名单；产物验收复用 `PublicExampleProbe`（公开用例独立回放）与 `agent.files`（备份/竞争/三方合并） | `TaskKindHint`/`LocalChannelPolicy`/`ModelSelectionPolicy`/`ChannelScheduler`/`PublicExampleProbe`/`agent.files` | ⑤ tokens（本地-远端分流按档位）+ ①prompt 面（生成类走独立档） | 生成类 completion 不降 ∧ 产物回放通过率不升 |
| M3 | **编排结构化**：动作候选成为 R1 契约字段（`StructuredContract.SchemaText` 只**加厚**，`src/agent/contract/`），编排决策由闸族系给出，远端只做候选声明 | `Semantics`/`StructuredContract`/`SemanticsPipeline`/`ActionToolSpec`/`SupplementBlock` | ②执行 面（调用数按 request_id 去重↓）+ ⑤ tokens | 调用数不降 ∧ 恒前缀命中 <97% |
| M4 | **回执 → 补丁闭环（运行期自升级）**：远端修复回执 ⇒ `LearnedShape` 形状补丁 ⇒ 下次识别/编排命中；无补丁时**逐位等于旧行为** | `LearnedShape`/`NlpGate.IsLearned`/`SupplementInbox` | ⑥ 质量 + ⑤ tokens（同一题重复轮次↓） | 补丁生效率 ==0 ∧ 命中率不升 |

---

## 3. 里程碑与排期（DAG：节点 / 依赖 / 并行面 / 重启判据）

```
DAG（箭头=依赖；【并行面】=可同时推进的节点集合；重启判据=该边失败时回退到哪个节点）

  R607 盘点/器具面（零产品改动，只读+打点）
        │
        ├──────────────► M1 出口统一（R608–R609）
        │                       │
        │                       └──► M4 回执闭环（R614–R615）
        │
        ├──────────────► M3 编排结构化（R610–R612）
        │        【并行面 A：M1 与 M3 文件面不相交（agent.nlp vs agent/contract+modelqueue）】
        │
        └──────────────► M2 生成档（R613）── 依赖 M1（先识别是生成类，再路由）

  收口 R616（仅当 M1–M4 全绿；否则如实标未闭合）

  重启判据：① 任一里程碑出口闸 rc≠0 ⇒ 回到本节点，禁跨节点累加；② 恒前缀命中 <97% ⇒ 回到 M3 的前缀加厚步；
           ③ 起手闸 fail-closed（余量不足）⇒ 先按「同窗禁构建」清场再重采样，禁挪阈值。
```

| 里程碑 | 计划轮次 | 单变量（唯一） | 改动面（复用件） | 出口闸（全绿才进下一步） |
|---|---|---|---|---|
| **RF0004.0 盘点+打点** | R607 | 零产品改动：识别出口/生成档/编排面**打点齐全** | `TurnGateJudge` 打点 + `roundcheck` 只读 | 打点面治疗 >0 且对照 ==0 ∧ 全量绿 ∧ 恒前缀 ≥97% ∧ 起手闸 rc=0 |
| **RF0004.1 开放域识别** | R608–R609 | 统一识别出口（`RecognitionVerdict`） | M1 | abstain 率↓ ∧ 命中后正确率 ≥ 基线 ∧ 远端调用不升 ∧ 命中 hold ≥97% |
| **RF0004.2 多轮工具编排** | R610–R612 | 动作候选进 R1 契约（前缀**只加厚**） | M3 | 调用数 ≤ 旧臂 50%（按 request_id 去重）∧ 质量 ≥ 旧臂 ∧ 命中 ≥97% |
| **RF0004.3 生成类** | R613 | `TaskKindHint.Generation` + 产物验收器 | M2 | 生成类质量不降 ∧ completion 不升 ∧ 本地/远端分流比有分离 |
| **RF0004.4 闭环自升级** | R614–R615 | 远端回执 ⇒ `LearnedShape` 补丁 | M4 | 补丁生效率 >0 ∧ 无补丁逐位等于旧行为（零回归可机检） |
| **RF0004.5 收口** | R616 | — | — | 七面 KPI 全绿 ∧ API 基线/结构闸绿 ∧ AOT 0 IL |

**排期口径**：每轮 = 1 真机跑（14 窗次量级）+ 闸；**串行真机**（2 vCPU/3.6 GB/单 llama-server ⇒ 同时只允许一条起臂）；按近 20 轮真实动能（产品侧提交率 5%）计，本条线预计 **10–14 轮**；若「放行+每轮都动产品侧」则 **5–7 轮**。

---

## 4. 验收 KPI（三能力面 + 与既有四判据合并）

| 面 | 主指标 | 前置/负控 | 口径要点 |
|---|---|---|---|
| 开放域识别 | **abstain 率** ∧ **命中后正确率** | 负控：无补丁臂（对照） | 信号须**自算**（上游 Signature 对中文恒空）；标签集合不固定 ⇒ 不得用闭集 F1 冒充 |
| 生成类 | 产物**独立回放通过率** + completion（真值取中继 usage） | 负控：模型自裁判禁用；`unreported` 禁记 0 | 本地生成 15.8 s/次 ⇒ 主路径=远端；本地只做判别位 |
| 多轮工具编排 | **调用数**（request_id 去重）∧ 质量（逐窗整题全对） | 对照臂 = 旧自由文本动作环（同窗） | 步数/步骤总数两列并列；恒前缀命中 ≥97% 为硬门 |
| 合并 | 原四判据（质量 / token / 前缀缓存 / 前端 api）**不降** | `truthdrop`（真值自身失分窗单列）· 铁律 11 rc=0 | 成本**两形态并列**（v1 逐位 / v2），禁跨轮相减；单窗=噪声 ⇒ reps≥3 报逐窗+极差 |

### 4.1 检验数据：可观测基准台账（`eval/capability/baselines.json`）

> 令（2026-09-21）：**「将某些可观测基准融入 kpi 作为检验数据」** ⇒ KPI 不只报读数，还须逐条挂上**现盘可核对**的基准（外部真值 / 对照臂 / 冻结不变量 / 环境闸 / 负控）。

- **唯一权威面** = `eval/capability/baselines.json`（schema `kpi-baselines/1`，`indent=1` 保形，尾 LF）。**禁手改读数**：改 `value`/`source_path` 必须重算 `source_sha12`。
- **每条基准四要素**：① `value` 读数（+`unit`）② `source_path` + `source_sha12`（现盘 pin；**改源必重算**）③ `check_cmd`（单行可复跑，实测 14/14 rc=0）④ `threshold` + `threshold_source`（阈值只能引**预注册件**或冻结声明件，**禁引历史读数**）。
- **判绿命令** = `python3 eval/capability/status_gen.py --check` ⇒ 登记表 0 违规 **∧ 基准 0 漂移 ∧ 0 缺源**。**有牙证明（负控）**：改任一 `source_sha12` ⇒ rc=1 并打印 `declared -> disk`；删源 ⇒ rc=1；正控 ⇒ rc=0。
- **机器可读硬规则**（`rules` 字段）：① 成本/质量基准**禁跨轮相减**（只许同窗同题集对照）；② 外部真值（codex）**不得当硬上限**（`truthdrop` 证），失分窗单列 unreliable；③ `kind=history` 只可并列展示，**不得充当阈值**。
- **引用义务**：每轮 `eval/capability/kpi.jsonl` 行须带 `baselines`（本轮**实际用到的**基准 id 列表）；未引用的面**不得声称「已检验」**。行 schema = `round/ts/kind/change/readings/honesty/artifacts/baselines`；`artifacts` 一律**仓内相对路径**（运行目录产物须注明非仓内）。
- **现状（2026-09-21，R606 后）**：基准 **14 条**（`frozen_invariant` 2 / `env_gate` 3 / `external_truth` 1 / `contrast_arm` 6 / `negative_control` 1 / `diagnostic` 1），**0 漂移 0 缺源**；台账 sha12 以 `docs/reports/status.json` → `.baselines.file_sha12` 为准。
- **已暴露的台账卫生缺口（不粉饰）**：`kpi.jsonl` 144 行中 **19 行缺 `kind`**、**60 个非轮 tag**（`EXP1-Q*` / `R403-scope` / `loop-mechanism` / `unknown` 等）⇒ 仅 `round` 匹配 `^R\d+$` **且有 `kind`** 的行可作「检验数据」被引用，其余一律按**观测列**处理。

---

## 5. 每轮固定小步与开销（承袭现行纪律）

1. **文献环**（每轮必跑）：arXiv ≤3 检索式/轮、全文 ≤2 篇、单次 ≤120 s、间隔 ≥4 s；候选须经本仓真机单变量对照改了 KPI 才算「已实施/已证伪」；台账 `docs/research/lit-review-ledger.md`（追加、禁整档回写）。
2. **闸序**：起手闸（`PREV_SWING` 余量；**本侧同窗禁跑 `dotnet test`/`publish`**，先清 VBCSCompiler/pyright 并记 MemAvailable 前后差）→ 铁律 11 前置器 → 判据器（`defects: []`）。
3. **AOT 面**：任一改链代码的里程碑后必重发布，IL 警告 0，`bins-<round>.json` 记 sha12。
4. **提交**：逐名列 `git add`；`PUSH_PAUSED` 在效（禁 push/镜像/`gh api` 写）。
5. **汇报**：六格（①prompt ②怎么执行 ③回执 ④自动下一步 ⑤tokens+命中 ⑥是否偏离意图），≤3 行 + 表。

---

## 6. 风险与诚实边界

1. **环境**：CPU-only 2 vCPU、MemTotal 3,659 MB、磁盘 `/` **94%（free ~2 GB）** ⇒ 本地生成只能做判别位；产物面须归档清场，否则 RF0004 写盘会撞盘。
2. **起手闸余量**：三面**并行开发、串行真机**；同窗构建会把 `PREV_SWING` 抬到千 MB 级（r605 1,091 MB vs 洁净 r603 285 MB）⇒ 排轮期间本侧零构建。
3. **判据分辨率**（第二瓶颈）：`valid=1` 型「无分辨率」尚未收口 ⇒ 新能力 KPI 必须先证**有分辨率**再谈达标。
4. **真值面**：codex 同窗受铁律 11 rc 限制 ⇒ 成本列可能长期为**参考·未可验收**；真值自身失分窗（wythoff 族）单列，不作硬上限。
5. **编排面反冲**：M3 若把动作候选塞进前缀 ⇒ 违反「只加厚」以外的任何改动都会破缓存 ⇒ 一律走**尾部载体块**（`SupplementBlock` 形态）。
6. **零回归**：产品档缺省可翻，**库内显式构造缺省保持旧值**（R606 教训：该轴已判负并撤回 ⇒ 本条线不得重开 R606 轴，除非 `reps ≥25/档` 的新证据面）。

---

## 7. 未闭合项（不粉饰）

1. `wythoff` 冷集构造层（缺口 100% 集中族）**仍未修** ⇒ 质量面任何「达标」宣称前必须先处置它（否则 J4 整题全对恒 4-7/9）。
2. 精排四项真值（NDCG@k / Recall@N / MRR / Precision@k）**仍「未测」** ⇒ 原四判据之一在 RF0004 收口前必须有真值。
3. `agent.files`（R584 文件插件）**未接产品写盘路径** ⇒ M2 生成类写盘前必须接线，否则生成类产物无三保证。
4. `AGENTFRAMEWORK_ACTION_ADAPTIVE_BUDGET` 是否真生效 **待确认**（消融前必先证变量可生效）。
5. 运行期自升级（M4）依赖 `LearnedShape` 落盘与补丁库只读语义 ⇒ 与「同窗在飞窗」纪律的交互**未验**。
