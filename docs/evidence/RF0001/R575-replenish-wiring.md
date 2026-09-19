# R575 — 33 红收口 (W1/W2/W3): 回补机制接线 + 判定面零词表 + 端口/语料重生成

日期: 2026-09-19 · 轮号: R575 · 归属: self (本侧实施 + 本侧自跑) ; 承接 R573 (foreground, 22/33 转换) 与 R574-tick (read-only 复核)
用户令 (R573 文档引, 逐字): 「33红全部要改为现有机制，否则你这么多天的努力全白费了」

## 0. 目的与判据

R573 把 22/33 红改为吃**结构量**，余 11 个方法无法转换 (「再讲一遍」(吸收) 与「讲细一点」(远端) 在无词表结构面完全同形)，
R573 记录的出路 = **用户钦定的回补机制**: `llm 返回时补充闸数据给 nlp 打补丁`，属下一轮。R574-tick 机检该前提:
「`agent.nlp.NlpGate` 已实现、零消费者」，即**机制在、闸不在**。本轮把它接上（零词表方向不变）。

判据 (本轮的「可验收」定义):
1. 全量套件 1900/1900 绿 (R573 工作区态: 11 个方法红 / 33 例失败; HEAD 态: 5 例红)；
2. 11 个方法**逐条双侧断言** (无补丁 ⇒ 交远端 ∧ 回补命中 ⇒ 本地面成立) —— 不是删断言，也不是放宽断言；
3. 端口 (`eval/rover/r468/gate_rules.py`) 与产品判定面**回补 + 重生成语料**后逐条一致 (差分校验绿)；
4. W2 生产回补点已接线 (不是孤岛): 远端轮成功 ⇒ `TurnGateJudge.LearnOnSuccess`。

## 1. 修改点 (逐项: 改哪一格读数)

| 项 | 文件 | 内容 | 改哪一格 KPI |
|---|---|---|---|
| W1 | `src/agent.nlp/NlpGate.cs` | 补丁**按面隔离** (`<face>\t<signature>`) + 纯函数判定面 `IsPatched(text, face, patches)`；面 = gate/repeat/para/claim | token 格 (复述/改写族不必要的远端主调用 ↓) |
| W1 | `src/agent.modelqueue/TurnGateJudge.cs` | `IsPureRepeat` = `IsRepeatShape` ∧ 回补命中；删 `RepeatMarkers`/`QuestionSignals`/`RequestSignals`/`CorrectionSignals`；`Parse` 删中文词标记死循环 | 同上；`MechanicalPass` 覆盖面上界必须重新量 (见 §3) |
| W1 | `src/agent.modelqueue/LocalParaphraseChannel.cs` | `IsPureParaphrase` = `IsParaphraseShape` ∧ ¬复述 ∧ 回补命中；删 `Markers`；守卫 ⑥ 动作声明面 = 回补库 `claim` 面 (按 token 学习，零词表) | 改写族本地化面 + 守卫覆盖面 (诚实边界见 §4) |
| W2 | `src/agent/IndustrialAgentV2.cs` | 远端轮成功 ⇒ `TurnGateJudge.LearnOnSuccess(message.Content, llmResponse.Success)` (唯一回补写入点；Skip 轮不回补；族外输入不登记) | 回补面从「孤岛」变「有生产入口」 |
| — | `src/agent.modelqueue/agent.modelqueue.csproj` | 引用 `agent.nlp` (layer: nlp 是叶子库，无环) | — |
| W3 | 4 个测试类 11 个方法 | 双侧断言 (含 `Patches(face, text)` 显式注入；「无补丁」用**显式空集**保证与执行顺序无关) | 判据面 |
| 器具 | `eval/rover/r468/gate_rules.py` | 源路径 `LocalGenerationPort.cs → TurnGateJudge.cs` (R468 端口因文件改名已**静默失效**: `--selftest` 起手即 `FileNotFoundError`)；按新判定面重派生；新增**零词表 fail-closed 断言** (源码重现词表 ⇒ 端口停) | 外部效度口径 |
| 器具 | `eval/rover/r468/real_traffic_classify.py` + 语料重生成 | 语料行新增 `patch` 声明 (repeat/para，由形状单源产出) + 改写族 InlineData 行；类集新增 `para` | 同上 |

## 2. 真机读数 (dotnet test, 本侧执行)

| 阶段 | 命令 | 结果 |
|---|---|---|
| R573 工作区态 (起点) | `dotnet test src/agent.tests/...` | Failed **11 方法 / 33 例** |
| 聚焦面 (4 类 148 例) | `--filter "~LocalTurnGateTests\|~R497...\|~R498...\|~GateRulesPortDiff"` | **Failed 0 / Passed 148** |
| 全量 (R575 后) | `dotnet test src/agent.tests/...` | **Failed 0 / Passed 1900** |
| 端口双源自检 | `python3 eval/rover/r468/gate_rules.py --selftest` | `selftest: PASS` (ack 13 / repeat 15 / para 8) |
| API 面 | `AGENTFRAMEWORK_API_BASELINE_WRITE=1 …--filter PublicApiSurfaceTests` | 基线 **+16 行 / −0 行** (纯增)，复跑绿 |

## 3. 真实流量组成 (state.db 只读复算; 规则变更 ⇒ 强制重生成语料)

| 口径 | R468 冻结 (词表版) | R575 (零词表 + 回补面) |
|---|---|---|
| 真实用户轮 | 1179 | 1544 (库增长) |
| 机械放行 (pass) 占比 | 0.7549 | **0.6509** (−10.4 pt) |
| 残余 (other) 占比 | 0.1467 | **0.2545** (+10.8 pt) |
| 可跳面 (ack+repeat) | 0.0000 | **0.0000** (未变) |
| 网格 p12 (合成) | pass 1 / ack 4 / repeat 5 | pass 1 / ack 4 / repeat 2 / **para 1** / other 4 |
| 真实轮「形状上可被回补」计数 | 未登记 | **0** (反事实上界 = 0) |

读法: 词面信号删除的代价 = 机械放行面 −10.4 pt，这部分轮**改走本地 r1 字母判官** (本地调用，不是远端 token)；
真实语料的可跳面仍为 0 ⇒ 「网格降幅 ≠ 真实降幅」结论不变 (R468 锚)。`real_shape_reachable = 0` ⇒ 回补面在真实分布上
**无可吸收形状** (诚实边界：本轮的收益面在真实流量上为零，机制面为「接上了且口径闭合」)。

## 4. 诚实边界

1. **语义变更已登记** (非放宽): `重来一遍/再来一次` 旧判据靠标记表排除 (表外 ⇒ 不吸收)，标记表删除后判据 =「白名单形状 ∧ 回补命中」⇒
   **一旦被回补即吸收**。语义仍正确 (原样重来 ⇒ 本地回放即所需)，但这是判据语义的变更，已逐行写入测试注释。
2. **动作声明面 (守卫 ⑥) 在无回补时不覆盖**: 19 条静态词表删除后，该面只由回补库驱动 ⇒ 未学习前本地改写的「凭空动作声明」不被拦截。
   本轮只钉「不误杀 + 喂回补必拒」，**不宣称该面仍有覆盖**；补覆盖 = 下轮候选 (需从 LLM 轮学习声明词面)。
3. **`MechanicalPass` 覆盖面下降 10.4 pt** 是删除词面信号的直接代价，未做补偿性加表 (零词表方向) —— 代价与收益同页登记。
4. **零远端 token 结论未测**: 本轮零真机远端调用 (纯单测面) ⇒ 不宣称任何 token 降幅。
5. 回补库默认路径 `data/nlp/gate-patches.txt`；单测内**不写**该文件 (双侧断言用显式补丁集合)，生产写入由 W2 承接。

## 5. 下轮候选

1. 守卫 ⑥ 动作声明面回补点 (从 LLM 轮/评审学习声明词面) —— 补回 §4-2 的覆盖缺口；
2. R571-② 契约修复预算轴第二窗集 (≥25 跑次/臂) 或按天花板冻结 1 + 写死重开条件；
3. R572-③ 起手闸把会话工具子进程并入判据 (R571 已实测 +359 MB，判据侧仍缺)。
