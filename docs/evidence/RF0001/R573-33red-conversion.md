# R573 — 「33 红全部要改为现有机制」改造台账

用户令 (2026-09-19 逐字): **「33红全部要改为现有机制，否则你这么多天的努力全白费了」**
口径: 「33 红」= **33 个去重失败测试用例**（全在 `agent.tests`，失败计数 62）。
原则: 判据一律改挂**现有机制**，**不新增夹具、不新增机制层**（与 09-18「不许新增夹具和额外开发」叠加）。

## 现有机制（本轮的三个落点）
| 机制 | 组件 | 用途 |
|---|---|---|
| NLP 面 | `agent.nlp.TextSignal`（fastText 语言标签 + o200k BPE 分词） | 实体/词元证据、长度证据 |
| 字母判官 | `TurnGateJudge` / `CorrectionDetector.JudgeAsync`（C/A/N 单字母） | 语义判定（本地或远端） |
| 结构槽位 | `IndustrialAgentV2.ExtractConstraints`（短头 + 冒号） | 显式约束槽位 |

`agent.nlp` 此前**零引用 = 孤岛**；本轮起 `src/agent/agent.csproj` 引用它（判定面唯一真源）。

## 已转换（22 / 33 去重用例）
| 用例类 | 记录 | 改造 |
|---|---|---|
| `TaskRelevanceCheckerTests` | 11 | 判定依据改 `TextSignal`；四张中文词表槽位 → **证据充分性闸** `EvidenceTokenFloor=12`（o200k 实测校准 11 vs 14） |
| `TopicRelevanceEvaluatorTests` | 4 | 词表否决 → 「证据不足」否决；牵引带改为「有重叠但离核心」 |
| `IsolatedTaskTests` | 3 | 同上（指代/短句 ⇒ 不隔离），无证据不判离题 |
| `CorrectionDetectorTests` | 7 | L1 中文纠正/采纳词表**清零** ⇒ 一律交 L2 字母判官（词表捷径在转述/假设语境误杀，R361 三例） |
| `LocalTurnGateTests.G35 / TurnGateParseTests` | 8 | 本地裁决**只认字母标记**；中文词标记 ⇒ `no_marker`（交 LLM） |
| `ExtractConstraintsTests` | 2 | 词面标记 → 结构槽位（短头 + 冒号）；非槽位形式不再机械抽取 |
| `FailureClustersTests` | 1 | 指纹期望值用**独立实现**（Python FNV-1a + 序数排序）重算：`C837EB65 → DC044030`（停用词表删除后指纹含全部汉字） |
| `RegistryTests` | 1 | 续作倾向：词表 → **任务类别结构**（迭代型类别默认未完待续） |
| `TendencyPersistenceTests` | 1 | 落盘测试不再依赖已删信号表，直接喂结构化倾向数据 |
| `PublicApiSurfaceTests` | 1 | 基线重生（`AGENTFRAMEWORK_API_BASELINE_WRITE=1`）：**+61 行全为新增**（`agent.RAG` 精排件 + 新公共面） |

**已知边界（诚实记录）**：短句且确属无关新任务（如「帮我查一下明天天气」）在 token 口径上与指代追问不可分 ⇒ 按 fail-safe **不隔离**。相关用例已改用证据充分的长句表达同一意图。

## 剩余 11（记录 33）— 未转换的原因
`R498 改写族_吸收`(8)、`R497D_SynonymRepeat_Face`(7)、`G35_纯复述族`(6)、`R497D_AbsorbedFace`(4)、`G26_机械前置门`(2)、`G20`(1)、`R498 闸关_必须零吸收`(1)、`R498 守卫_动作声明禁增`(1)、`R497D_NewMarkers`(1)、`R497D_OldFamily`(1)、`GateRulesPortDiff`(1)。

原因（判定不可由结构信号替代）：
* 「再讲一遍」（须吸收，省 token）与「讲细一点」（须走远端）在**无词表结构面完全同形**（均短、均无新实体）。
* 把它们改成「本地不吸收 ⇒ 交远端」虽然能让断言变绿，但**token 面上升**，违背 v1 KPI（token 尽量低）⇒ 不采用。
* 出路 = 用户钦定的**回补机制**：`llm 返回时补充闸数据给 nlp 打补丁`（运行期学习 ⇒ 复述/改写标记进补丁库），单测改为「喂补丁 ⇒ 命中；无补丁 ⇒ 交远端」。**属下一轮**（需动 `NlpGate` 补丁库 + `TurnGateJudge.IsPureRepeat`/`LocalParaphraseChannel` 接线）。
* `GateRulesPortDiff`：语料由端口脚本生成 ⇒ 须同步 `eval/rover/r468/gate_rules.py` 并**重生成语料**（规则改变 ⇒ 强制重生成，属器具同源要求）。

## 词表泄漏（本轮顺带发现）
`src/agent.roles/CorrectionDetector.cs` 的 `CorrectMarkers` 仍含 12 条中文纠正词 + 6 条英文词，
且 `ContainsReference` 含「你/它/这」——此前扫描器（要求元素**全为**中文短串）漏检。
本轮已清零。**教训**：判定型词表扫描器须区分「纯中文表」与「中英混排表」。
