# RF0002 · NLP 自迭代能力开发计划（远端返回 ⇒ 强化 nlp）

> 口径来源（用户逐字，2026-09-19）：「不补回，加入远端返回后可以优化 nlp 能力的机制」「先机制定稿研究走通确定用什么方案可以加强利用 nlp，之后只写一套 nlp 相关自行迭代程序就可以确定需要远端 llm 返回什么数据」「llm 返回新数据只要有一个评分机制，下次使用时有用就留、没用就扔掉，长期 agent 工作下来逐渐自我完善」「这不是你需要开发的东西，比如那些器具」。
> 排除项：**不新增器具 / 不新增判官 / 不新增夹具 / 不动产品分支**；只扩现有 `agent.nlp` 一个模块 + 现有调用点接线。

## 1. 已定稿并走通的机制（本轮实施，5/5 绿 + 负控）

| 环节 | 方案（语言无关，零词表） | 代码事实 |
|---|---|---|
| 学什么 | 远端回执 ⇒ **形状** = 面 + 语言 + 长度带 + 字符集；不是逐字字符串 | `src/agent.nlp/LearnedShape.cs` |
| 何时学 | 只在远端判定「可本地消化」时学（负例不学） | `NlpGate.LearnFromRemote(text, face, localizable)` |
| 怎么用 | 同面 ∧ 邻带（±1）× 共字符 ≥1 ⇒ 本地命中，basis=`learned-shape` | `NlpGate.IsLearned` / `Decide`（实库模式） |
| 泛化单位 | **字符集**（`char.IsLetterOrDigit` + 小写）：CJK 同义改写几乎不共享 BPE 子词、只共享字符 ⇒ 以字为粒度 | `NlpGate.CharSet` |
| 精确率兜底 | 面 / 邻带 双约束 + **评分剔除**（命中且有用 +1 上限 4；一次无用即扔） | `NlpGate.ReportOutcome` |
| 跨进程 | `gate-shapes.txt`（与 `gate-patches.txt` 同目录，随 `PatchPath` 切换），手写转义、零反射 | `NlpGate.LoadShapes` |
| 遥测 | `ShapeCounters`（命中 / 学到 / 存量） | `NlpGate.ShapeCounters` |

证据：`src/agent.tests/NlpGateLearnTests.cs` → `Passed! 5/5`（含 3 条负控：不学不命中 / 跨面不命中 / 远端判不可消化则不学）+ 评分条（有用留、一次无用即剔除后不再命中）。

## 2. 已实施（R576 接线轮，2026-09-19；仍不新增器具）

1. ✅ 远端返回点把「逐字补回」换成形状通道：`TurnGateJudge.LearnOnSuccess` 由 `Observe` 改 `LearnFromRemote(text, face, localizable: true)`（用户令「不补回」）。
2. ✅ 评分回执：本地消化成立 ⇒ `ReportOutcome(..., useful: true)`；命中却仍需远端（`repeat_no_replayable_prev` / `paraphrase_no_replayable_prev` / `paraphrase_guard_rejected`）⇒ `useful: false`（自动剔除）。
3. ✅ 语言字段只留遥测（超短句 lid 不稳定；跨语言已由「共字符」隐式保证）；跨语言负控由字符集不相交承担。
4. ⏳ 待观察项（长期，不预置）：泛化面在真实分布上的命中率 / 误命中率、评分淘汰曲线的收敛值。

**接线证据**：`docs/evidence/RF0002/R576-shape-wiring.md` —— 定向 **Failed 0 / Passed 158**、全量套件 **Failed 0 / Passed 1910**（首跑 2 例红 = `PublicApiSurfaceTests` 两条，根因 = 新公共成员未重生基线 ⇒ `AGENTFRAMEWORK_API_BASELINE_WRITE=1` 重生，diff **+12/−0** 全为新成员，属设计行为）（含 5 条接线断言 + 3 负控）、形式校验 **14/14**；消费面 = 生产判定面（`TurnGateJudge.IsPureRepeat` / `LocalParaphraseChannel.IsPureParaphrase`），`patches != null` 的注入路径逐位不变。
**诚实边界**：生产库 `data/nlp/` 不存在 ⇒ 真机链路当前**零命中（未测到）**，且本轮**零远端调用 ⇒ 不宣称任何降幅**。

## 3. 约束与验收

- 约束：AOT 可用（零反射、零 STJ 反射序列化）；单文件单类型（铁律 13）；恒前缀只加厚；不改产品分支语义；不作开发期预制；**器件形态按铁律 14 第①/②档选（树/线性打分器，或微调双向编码器；入 AOT 栈须可导出为纯 C# 打分器 / ONNX），禁以本地 LLM 当判别位**（现役本地 3B 判别位 R609-AB 真机 17.2 s/例 ⇒ 档位错，见 RF0004 §0.4）。
- 验收：① 定向测试绿（含负控）② 生产链路出现 `learned-shape` 命中（非孤岛，遥测 `ShapeCounters.ShapeHits > 0`）③ 评分淘汰后可观测到形状存量下降 ④ 命中面不增加远端调用数（token 格不升）。
- 可测化接线（**R579-tick**，判据/阈值**不变**，只补生产侧读数面）：②③④ 的通道级打点 = `nlp_shape`（8 键 `{route, shape, face, basis, hits, learned, shapes, msg_sha16}`，点位在既有回补点 `LearnOnSuccess` 之后；机检 `eval/rover/r579-tick/shape_kpi_face_check.py` **rc=0**，契约/零回归/边界见 `docs/evidence/RF0002/R579tick-shape-kpi-face.md`）。**全量 dump 未测到 ≥1 事件前，②③④ 一律记「未测」**，禁读成「无效应」或「已验收」。
