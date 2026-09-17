# RF0001 · 对照 Claude-Fable-5.1 的重构开发计划（新版本线起点）

> 本文件是**新版本线 RF 的第一份计划**（RF0001）。旧版本线（v0.13–v1.01，共 216 份计划/报告/变更日志）
> 于本轮整体归档进 `docs/archive/`（归档号 `AR-####`，见 `docs/archive/ARCHIVE-INDEX.md`），不再作为权威源。
> 证据面结构见 `docs/evidence/README.md`；指标仍以 KPI 为唯一判据（§3）。

状态：**活计划**（每轮更新「已落地/待做」列，不改历史结论） ｜ 建立轮次：R541 ｜ 对照面：`docs/external-reference/`

---

## 0. 版本口径（本文定义 · 机检）

| 项 | 定义 |
|---|---|
| `RF####` | **版本号序列，从 RF0001 开始**。RF0001 = 本版本（对照 fable 设计动因的重构）；RF0002 = 下一版本（识别侧路等，见 §4） |
| 旧版本线 | v0.13.0–v1.01.0：整体归档为历史桶，保留原版本号 + 归档号 `AR-####`，只读 |
| 归档面 | `docs/archive/{plans,reports,changelogs}/`；台账 `ARCHIVE-INDEX.md` + `archive-registry.json`（含 sha256/行数/原路径/新路径） |
| 活计划面 | `docs/plans/`（旧计划已清出，只放**当前有效**计划） |
| 证据面 | `docs/evidence/`（人读规范+索引+逐版 KPI/证据文档）；机器台账 `docs/verification-registry.json`（能力×验证级 L0–L4） |
| KPI 台账 | `eval/capability/kpi.jsonl`（键：round/ts/kind/artifact/change/readings/honest_boundaries/next/owner_round） |
| 入库例外 | 「当前功能描述」（README/api/architecture/CLI/Role/Skill/验证形式规范）与「证据」不入档；**被机器引用的文档**（代码注释、hooks、scripts、registry 行、`v715_dev_plan.taskplan.json` 的 DocRef）保留原位，逐条理由记在归档台账 `keep_reason` |

---

## 1. 参照面：fable 5.1 为什么这么设计（机检七条，来源 `DESIGN-RATIONALE.md`）

| # | 设计动因 | 机检证据 |
|---|---|---|
| 1 | **前缀逐字节恒定 ⇒ 吃满前缀缓存** | 全文无日期/无用户信息；`<current_date>`/`<user_information>` 不存在；正文写 "The current date is (provided in the conversation below)" ⇒ 时钟与用户态下沉到会话层 |
| 2 | **安全前置 + 每个能力边界再断言** | `<critical_child_safety_instructions>` 出现在全文 1.8% 处并逐工具重复，而非一段总纲 |
| 3 | **能力=XML 块 + 固定块序** | 274,608 字符全部成块（无 markdown 散文夹杂）⇒ 块序固定、可机械重钉 |
| 4 | **工具 schema 单源、字母序、自带调用协议** | 46 个 `<function>`，描述里直接写「何时用/怎么用/返回什么」⇒ 声明面与渲染面同源 |
| 5 | **易变项只出现在尾部** | 任务/上下文/时间全在 user 轮尾部 ⇒ 前缀复用不被打断 |
| 6 | **结构胜于散文** | 强约束以 schema/枚举/必填表达，不靠自然语言「请务必」 |
| 7 | **每层都有可机检判据** | 断言以「块存在/字段必填/顺序」表达 ⇒ 判据可脚本化 |

**推论（本项目要复制的不是文案，而是这七条的因果结构）**：`结构化 prompt ⇄ 远程 LLM ⇄ 结构化结果 ⇒ 精准语义 ⇒ 确定性管道`。

---

## 2. 动因 → 动作 → 落地状态

| 动因 | 本项目动作 | 状态（轮次） |
|---|---|---|
| 1 前缀恒定 | 恒定前缀加厚到 14,863 字符 / 6,704 tok，**只允许加厚**（`PrefixMinCharsForCache97` 门） | ✅ R537 `1aac63b`（命中 **97.37%**） |
| 1 易变项下沉 | 增量只追加在 `</prefix>` 前；时钟/记忆/角色下沉 user 轮 | ✅ R537 / R540（role 机检 w1 2/2·w2 1/1） |
| 2 边界前置 | `<hard_gates>` 前移到 `</role>` 后；工具描述自带调用协议 | ✅ R536 `c7453d3` |
| 3 块序固定 | 契约渲染器与校验器机械同源；前缀 sha 钉子 + `--check` 漂移闸 | ✅ R536/R537（`R1GEN_DRIFT_FILES=0`） |
| 4 声明面单源 | 工具 schema 单源派生 + 字母序；展示文案主参数键 = schema `required[0]` | ✅ R536 / R538（真跑抓出 `command`≠`cmd` 偏差并修） |
| 5 尾部易变 | user 轮只带任务体；`json_object` 契约 | ✅ R537–R540 |
| 5 运行期易变项载体（参照 OpenClaw） | 运行期事实（工作区态/步骤/条目进度）只走尾部载体块，快照式取代、空则显式 `none` | ⏳ RF0001.5 候选 C3 |
| 6 结构优先 | R1 契约强类型字段（intent/entities/constraints/missing_slots/ambiguities/plan/done_when/refusal）；缺信息停链（rc=2） | ✅ R539（`ms1` 3/3·steps=0·零副作用） |
| 7 判据机检 | rc 域 0/2/3/4/5/6/8 + 契约校验器 + 前置器（铁律 11） | ✅ R536/R539/R540 |
| 7 判据机检（**产物侧**，R544 新增） | **题面公开用例独立回放**：机械抽取（禁模型自撰期望/禁模型裁判）+ 判分器同语义回放 + 管道自产证据回灌（`AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK`，**默认关**） | ◐ R544 落地：L2 9/9 ∧ 真机 `P1b` = `ran=1 / 8 条全过 / rc=0 / 58/58 / 1 调用`；**触发面只到 `exec.Rc==0`** ⇒ on 臂仅 1/3 生效（预注册 J1 **FAIL**，R545 修） |
| ← 减法三件套 | 扔器具 / 砍模块 / 可合并则合并 | ✅ R534（−3,030 文件 / ≈47.6 万行）、R541（−216 文档 / 21,282 行） |

---

## 3. 版本判据：KPI（唯一指标面，本节每轮刷新）

| KPI | 口径 | 基线（最近实测） | RF0001 目标 |
|---|---|---|---|
| 前缀缓存命中率 | `1 − 新算/前缀`（同一前缀复用口径） | **97.37%**（R537：前缀 6,704 tok，hit 6,528 / miss 176） | ≥97%（hold） |
| 新算 prompt | 每轮逐窗（禁用派生列混算） | R1r 2/1 调用 · 21,874/10,948 tok（R540 w1/w2） | 持平或更低 |
| 调用数 | 按 request_id 去重 | R1r 2/1/1 vs A1-on 33/33/33 ⇒ **Δ93.9/97.0/97.0%** | 保持 ≥90% 降幅 |
| completion | 远端 usage 真值 | R537 真跑 2 调用 **63.7k**（reasoning 吃满 32k 上限） | RF0001.3 判定「是否加直接给结论约束」 |
| 前端 api 利用 | 真机事件流 | `item.*` **0 → 4**、事件 7 → 11、快照 `last_item` 入位（R538） | 前端可重建 codex 式「最新一条」行 |
| 质量 | 隐藏用例逐字节 | t1 **30/30 ×3 窗**；`R1nr` 30/30·30/30·28/30；`g1` **43/58**（未闭合）；R544 同窗：`on` 2/3 全绿（58/58×2）、`off` 1/3（58/58），两列假成功臂 0 | t1 保持 30/30；`g1` 进 `A1-on` 对照后归因 |
| 全量回归 | `dotnet test` | **1867/1867**（R544，Release；API 面显式重生）；AOT IL 警告 0（15,812,000 B） | 每轮不降 |

> **验收口径（铁律 11）**：成本降幅必须 `exec_precondition.py --round <r>` **rc=0** 才算可验收；
> rc≠0 一律标「**参考（未可验收）**」。R540 阻塞面 = `g1` 43/58 / 44/58 ⇒ 本轮降幅仍为参考值。

---

## 4. 范围与排除项

**在 RF0001 内**
1. 上下文精排（前缀恒定+加厚、易变项尾部化）与缓存命中 ≥97% —— 已达标，转 hold。
2. codex-cli **同等能力**同窗外部对照（reps≥3、逐窗+极差、codex 失败窗标 unreliable）。
3. completion 侧压缩（reasoning 上限策略、步数杠杆）。
4. 前端 api 利用（条目面事件、快照重连）。
5. 文档/证据结构（本文件 §6）。
6. 会话级**上下文编排**（参照面 `docs/external-reference/OPENCLAW-CONTEXT-ORCHESTRATION.md`）：缓存对齐压缩、运行期载体块、上下文记账面、缓存保温、子任务上下文白名单。
7. 用例面**精简**：不需要的用例/器具/产物归档，只留经典用例（判定面 = 白名单 ∪ 可执行闭包 ∪ 通配扫描保护；装置 `tools/archive/archive_cases.py`，归档面 `eval/archive/cases/**`，机读台账 `eval/archive/case-registry.json`）。

**排除（整体顺延 RF0002）**：LFM2.5-VL-3B 视觉侧路、屏幕识别、视频学习、区域特征库快路径。
理由：CPU-only 2 vCPU ⇒ 图像 prefill 5.6 tok/s（351 s/帧）；且 v1 判据未包含识别面。

---

## 5. 阶段与闸（每阶段必须有可机检读数才进下一阶段）

| 阶段 | 内容 | 出口闸 |
|---|---|---|
| RF0001.1 | 前缀/命中 hold + 文档证据结构（本文件生效） | 全量绿 ∧ 归档悬空引用 0 ∧ 命中 ≥97% |
| RF0001.2 | codex 同窗 reps≥3 + `g1` 归因（非同源 oracle） | `exec_precondition --round` rc=0 或逐条点名阻塞项 |
| RF0001.3 | completion 压缩（步数/上限策略），同窗对照 | 新算 prompt/completion 双列不劣化 ∧ 质量不降 |
| RF0001.5 | 上下文编排（参照 OpenClaw）：记账面 → 运行期载体 → 缓存对齐压缩 → 保温 | 记账面与 `PromptCacheKpi` 同源 ∧ 压缩条目写入即冻结（sha 断言）∧ 冷启动调用单列 ∧ 命中率 hold ≥97% |
| RF0001.6 | 用例面精简（归档不需要用例，只留经典） | `archive_cases.py --verify` PASS ∧ 全量绿 ∧ 悬空引用 0 ∧ 保留面机检器（registry/kpi/起手闸/契约）全绿 |
| RF0001.4 | 收口：仅当 RF0001.1–.5 全绿才收；否则如实标未闭合 | KPI 表全绿 ∧ API 面/结构闸绿 ∧ AOT 0 IL |

---

## 6. 文档与证据结构（本版本起生效）

```
docs/
  plans/RF0001-…md          # 活计划（唯一权威计划面）
  external-reference/       # 外部参照面（fable corpus + OPENCLAW-CONTEXT-ORCHESTRATION.md）
  evidence/                 # 证据文档面（人读）；规范=README.md，索引=INDEX.md
    RF0001/{KPI.md, EVIDENCE.md}   # 逐版 KPI 目标/实测/口径/边界 + 逐条证据指针(命令+sha+level)
  archive/                  # 归档面（只读）：ARCHIVE-INDEX.md + archive-registry.json + {plans,reports,changelogs}/
  verification-registry.json# 机器台账（能力 × 验证级 L0–L4，机检器 VerificationFormTests 绑定）
```
规则：①**证据本体不进 docs**（仍在 `eval/**`），文档面只存**指针 + sha256 + 复现命令**；
②机器台账只有一份（`verification-registry.json`）⇒ 不新建第二本台账，避免漂移；
③KPI 行只写 `eval/capability/kpi.jsonl`，证据文档按 `round` 引用，不复制读数。

---

## 7. 未闭合项（诚实边界，不粉饰）

1. `g1` 跨族长任务 **未闭合**（43/58 · 44/58），失败族逐窗漂移（`wythoff`↔`life`）—— **EXP1-Q51 已定因**（只读机检，见 `docs/evidence/RF0001/EVIDENCE.md` E12）：两窗失败族均**产物缺陷**（w1 `wythoff` 冷点集构造错 / w2 `life` `bytes`↔`str` 契约违反），题面 oracle 正控 58/58 ⇒ 夹具分支排除；缺 `A1-on` 在 `g1` 的基线仍为阻塞。
   · **R542**：修复预算轴（1/2/3 × 3 rep）**证伪**；`A1-on` 基线已补（4 调用 / 38,990 tok / 58/58）⇒ 阻塞项换为「r1 臂 0/9 全绿 ∧ 同窗无成本增益（Δ0.0%/+0.1%）」。
   · **R544**：产物侧**公开用例独立回放**已落地（E16，默认关）+ L2 9/9 + 真机 1 臂全过（8/8 公开用例、58/58、1 调用 / 10,405 tok，同窗最省）；**但** 预注册 J1 判 FAIL（探针只在 `exec.Rc==0` 触发 ⇒ 3 个 on 臂里 2 个 `rc=5` 时**结构性不可达**）；`exec_precondition --round r544` **rc=1**（验收面 = `P1c` 43/58）；旧路径 `A1-on` 本窗自身崩到 **34 调用 / 714,287 tok / 46/58**（R542 为 4 / 38,990 / 58/58）⇒ **该对照列自身是方差源**，g1 族「r1 更省且质量不降」仍未成立/未可判。
2. codex 外部列 **单窗不可比**（窗间 4.2×/6.5× 摆动）；R540 前置器 rc=1 ⇒ 全部降幅标参考。
3. role 挂载**只证「挂上去」，未证增益**（两臂同分）。
4. `iteration-master-plan.md` §7 止于 R532、`improvements.md` 止于 R528 ⇒ 旧文档滞后项已随归档转入历史桶，**交接面为本文件**。
5. 逐链 fable 映射表目前只交 R1 子集（`R1-EXTRACT.md`），其余链条待 RF0001.2 内逐条补。
6. **上下文编排缺口**（2026-09-18 对照 OpenClaw 采编，见 `docs/external-reference/OPENCLAW-CONTEXT-ORCHESTRATION.md`）：无压缩触发策略（`ContextGradientCompressor` 286 行**未进主链**，只被 `Program.cs:190` audit 与测试消费）、无上下文记账面、无缓存保温（首调用 **89.0%** 冷起损失）、无工具回执上限。**核心张力**：压缩要重写历史中段，与「恒定前缀 ≥97% 命中」算术互斥 ⇒ 压缩必须**缓存对齐**（条写入即冻结 + 冷启动单列，不计入 97% 稳态口径）。
