# R579-tick — RF0002 §3 验收面 ②③④ 的**可测化**（度量面接线）

- 轮次: `R579-tick`（60 分钟 cron tick）· 前态锚 `1536b2ca61dd713a8401daacd158a3537c911c2d`（R578, HEAD）
- 约束（预注册 `eval/rover/r579-tick/prereg-r579tick.json`）: **零行为改动**（只读既有状态 + 一处通道级打点）/ **零远端调用** / **零新增夹具** / **零新增开关**
- 判据（预注册 P1–P6，阈值与键集**先落盘后动码**）: `eval/rover/r579-tick/prereg-r579tick.json`
- 读数: `eval/rover/r579-tick/readings-r579tick.json`（rc=0）· 器具 `eval/rover/r579-tick/shape_kpi_face_check.py`

## 1. 动因（F1，可复现）

RF0002 §3 的验收 ②③④ 建立在「形状通道被生产链路消费」这一前提上，而该前提在**测量面**不成立：

| 读数（P1，`src/**/*.cs` 排除 bin/obj，子串 `ShapeCounters`） | 前态 | 现盘 |
|---|---|---|
| 生产面引用点 | **1**（仅定义 `src/agent.nlp/NlpGate.cs:216`） | 3（定义 + 注释 + 真实消费者 `src/agent/IndustrialAgentV2.cs:1861`） |
| 测试面引用点 | 2（`src/agent.tests/NlpGateLearnTests.cs:27,76`） | 2 |

⇒ 前态「形状通道**未接出**」与「形状通道**零命中**」在读数上**不可分**（两者都表现为生产面零引用）；且模块计数对 repeat/paraphrase 面**结构性恒 0**（`NlpGate.IsLearned` 明确不计数）。**故 ②③④ 当时不可判，不是「判为无」。**

## 2. 改动（唯一变量）

`src/agent/IndustrialAgentV2.cs` 一处**通道级打点**（点位名 `nlp_shape`），插在既有回补点 `TurnGateJudge.LearnOnSuccess(...)` **之后**（`git diff --numstat` ⇒ **+24 / −0**）：

| 键 | 语义 | 服务的验收面 |
|---|---|---|
| `route` | `local_skip` / `remote`（本轮判定结果） | ④ |
| `shape` | `1` / `0`（本轮形状通道**是否被消费**） | ② |
| `face` | `repeat` / `paraphrase` / `none` | ② |
| `basis` | `TurnGate.LastBasis`（判定依据串） | ② |
| `hits` / `learned` | `ShapeCounters.ShapeHits` / `ShapeLearned` | ② |
| `shapes` | `ShapeCounters.Shapes`（存量） | ③ |
| `msg_sha16` | `LocalInputFingerprint.Sha16(输入)` | ④（与同轮 `llm_call` join） |

zero-behavior 论证: 点位只**读**既有状态（`repeatTurnFlag`/`paraphraseTurnFlag`/`IsLearned`/`ShapeCounters`/**已有** `LastBasis`），不入任何判定分支；`LastBasis` 为**既有字段消费**（无产品源码改动，见 §3 P4）。

## 3. 判据读数（器具 `shape_kpi_face_check.py`，rc=**0**）

| 判据 | 内容 | 读数 |
|---|---|---|
| P1 | 生产/测试面消费者计数（含前态对照面，同一器具路径） | 前态 1 / 现盘 3；测试 2 |
| P2 | **前态锚有牙**（同一契约在前态字节上必须判红） | 前态 `has_point=false` / 现盘 `true` ⇒ pass（sha16 `699008bc63e83379` → `4e9453b915626b45`） |
| P3 | 键集 == 预注册声明集（**恰好**，缺/多均判红）∧ 点位在回补之后 | missing 0 / extra 0 / `position_after_learn=true` |
| P4 | **零行为改动** = 判定链 8 文件逐位不变 ∧ 目标文件删除行 == 0 | 8/8 identical；`+24 / −0` |
| P5 | 真机: 编译 + 定向测试 | 编译 **0 error**；定向 7 类 **Failed 0 / Passed 114** |
| P6 | 诚实边界（见 §4） | 生产侧事件 **未测到** |

**P5 逐类（`--no-build` 复跑，加总 114 == 合并跑 114 ⇒ 无重复/漏计）**: NlpGateLearn 10 · LocalTurnGate 85 · TelemetryPending 2 · GateRulesPortDiff 3 · VerificationForm 7 · SkillGeneralization 4 · DevPlanDocRef 3。形式校验面 = VerificationForm 7 + SkillGeneralization 4 + DevPlanDocRef 3 = **14/14 绿**。

**P1 得牙（R477）**: 前态字段由**同一路径**计算（目标文件取前态字节，其余取现盘）⇒ 不是「换了个判据凑绿」。

## 4. 自捕（器具面 1 件，fail-closed 挡住）

1. **键集扫描窗口含点位名** ⇒ P3 把 `Emit` 的形参 `"nlp_shape"`（点位名）算成 kv 键 ⇒ `extra=["nlp_shape"]` ⇒ **rc=1（首跑假红）**。定因 = **器具读法错**（不是被测不符）；修法 = 扫描窗口**跳过点位名与模块名字面量**，**未放宽任何判据**；修后 `extra=[]`、rc=0。留档: 首跑读数即本文件 §3 P3「extra」列的依据（未覆盖、未翻案）。

## 5. 诚实边界（禁越界宣称）

1. **②③④ 现在「可测」，但**未测到 ≥1 事件**：本 tick **零远端调用** ⇒ 点位所在分支（远端轮后的回补点）**本 tick 不可能被执行到**；「未测到」不得读成「无效应」，也不得读成「已验收」。
   结构性原因（非本轮变量）: ① 现有测试类中**无一**同时「配置遥测目录」∧「驱动 `IndustrialAgentV2` 轮次」（P1 旁证: 遥测仅由 `Program.cs:293` 与 3 个遥测类自身 `Configure`）⇒ 走既有测试驱动**拿不到落盘事件**；② 真机 host 需真实端点（无 `FAKE_LLM` 类开关），而本地判别位 3B 档 RSS **2643 MB** > 起手前 `MemAvailable` 2398 MB ⇒ 本轮不起本地档（不为一次读数违约内存闸）。
2. **零行为改动 ⇒ 不宣称任何质量/成本降幅**：判定链 8 文件逐位不变（P4），本 tick 无质量读数，无可比窗口。
3. **未测到** 的验收面（②事件数 / ③淘汰曲线 / ④命中不增远端）一律在报告表内写「未测」。
4. `P4` 的「8 文件冻结面」是按**本轮声称的变量范围**枚举的（判定链 + 闸计数），不等于全仓零改动；全仓改动面由 `git status --porcelain` 与提交清单给出。

## 6. 归属

- 本 tick 实施: 打点点位（§2）、机检器 P1–P5、本文件、§7 块、`kpi.jsonl` 行。
- 前序（非本 tick）: `agent.nlp` 形状库/`ShapeCounters`/`LearnFromRemote` 与 §2 接线由 R575/R576（前台会话 + R576-tick）实施并已提交。
- **轮志口径**: R578 在 §7 **无块**（其读数落在提交信息 + `eval/rover/r578/` + `docs/verification-registry.json`）⇒ 本轮 §7 块的「上一轮」= R577/R578 两处并列，不相减。

## 7. 下轮（唯一直接面）

**R580: 形状通道真机首验**（= R577-①）：需一次**远端轮**（或本地档装载）使 `nlp_shape{shape:1}` 落盘 ≥1 事件，并配成对断言「shape=1 的轮 ≥1 ∧ 该轮 `llm_call` 数不增」。**前置**: 远端调用放行 或 内存闸放行本地判别位档（二者取一）。

## 8. 登记表（`docs/verification-registry.json`）

- 新增行 `r579tick.nlp-shape-kpi-face`（`level=L2`，`owner_round=R579-tick`），`evidence_path` 指向**本文件**（tracked 路径，**不**指向 `eval/rover/` 产物 ⇒ 不放大 R576 §4d 记录的「干净检出树 22 项违规」假绿）；`evidence_cmd` = §3 机检器命令；`negative_control` = P2 前态锚有牙 + §4 器具自捕留档。
- 写入工序: 先断言 `json.dumps(obj, indent=1)` **逐字节复现**原文件（通过）⇒ 才做 dict 级追加 + 回读核对；随后**当轮**跑形式校验。
- **自捕（器具/规范面 1 件）**: 首写成 `audited_by_round="R579-tick"` ⇒ `VerificationFormTests.Registry_Exists_And_HasNoViolations` **判红**（R2e: `^(?:R\d+|EXP1-Q\d+)$`）⇒ 形式校验**当轮**抓到，未搭在全量回归尾部。修法 = 登记表**词汇表内**写 `R579`，tick 身份保留在 `owner_round`/`capability`/`updated_round`（`R579-tick`）。**口径代价如实记录**: 登记表不支持 tick 后缀 ⇒ 「R579-tick」在该面被压缩为「R579」，与将来可能出现的 `R579` 正轮**同 token**，故 §7 块与本文件是轮次身份的唯一权威面。
- 形式校验读数: **Failed 0 / Passed 14**（VerificationForm 7 + SkillGeneralization 4 + DevPlanDocRef 3），`rows` 274 → **275**，`updated_round` → `R579-tick`。
