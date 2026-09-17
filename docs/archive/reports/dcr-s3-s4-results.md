# exp12 · S3/S4 结果：DCR 判定题集 + 真实装配评测（R386）

- 状态：**已执行，口径未完全对齐（见 §4 诚实边界）**
- 关联：`docs/plans/v0.23.0-exp12-agent-chain-dcr-90p5-feasibility.md`（S1–S5）· `docs/plans/v0.23.0-exp13-r385-tail-hardening.md`
- 产物：`eval/dcr/dcr_cases.jsonl`(145 条) · `scripts/kpi_dcr.py` · `src/agent.host/FormalEvalCommand.cs`（`--formal-eval`）· `eval/dcr/README.md`

## §1 口径与来源

目标数字 **90.5%** 出处 = **FAVA（arXiv 2607.27267）的 Decision Compliance Rate（DCR）**，原文 *"achieves a 90.5% Decision Compliance Rate (DCR) over the aggregate dataset"*。
目标区间 = **[85.5%, 95.5%]**（±5pp）。
**但 FAVA 的 DCR 公式 / 分母 / 弃权处置 / aggregate 合并方式（T1–T4）本次未能取得**：arXiv HTML、`/pdf/`、ar5iv、alphaXiv 四个来源均只返回摘要与引言（正文不可得）。⇒ 本报告**必须按多口径给出**，不得只报一个数。

## §2 题集构成（145 条，6 类）

| 类别 | N | 标签来源 | 说明 |
|---|---|---|---|
| entail（真蕴含 ⇒ Proceed） | 33 | z3 | premise ∧ ¬goal 整数 unsat |
| refute（可反驳 ⇒ Violation） | 30 | z3 | premise ∧ ¬goal 整数 sat（model = 反例） |
| vacuous（前提不可满足 ⇒ Violation） | 20 | z3 | premise 整数 unsat（空真，非证据） |
| out_of_fragment（片段外 ⇒ Abstained） | 19 | 构造 | 非线性/超片段，按定义弃权 |
| malformed（契约畸形 ⇒ Malformed） | 25 | 构造 | 缺 premise/goal、矛盾声明等 |
| absent（未声明 ⇒ Proceed） | 18 | 构造 | null/空/纯自然语言 |

**标签独立性**：83/145 由**独立 oracle z3** 重新推导（每条带 `z3_label` + `z3_label_why`，`self_check=ok`）；62/145 按**构造定义**（absent/out_of_fragment/malformed 是定义性标签，非经验结论）。**这一点必须明示**：只有 83 条是 oracle 实证标签。

## §3 真实装配复现（可复现命令 + 实测）

```
# 1) 真装配二进制逐条裁决（零 LLM / 零 daemon / 零 shell）
export PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
dotnet run --project src/agent.host -c Release --no-build -- \
  --formal-eval eval/dcr/dcr_cases.jsonl > /tmp/r387/assembly_real.jsonl
#    → EXIT=0, 145 行, 尾行 formal_eval: cases=145 ... gate_enabled=True
# 2) 与子代理 harness 输出逐字段对账（id/disposition/verdict/reason/allowed/counterexample）
python3 /tmp/r387/verify_dcr.py
#    → ids 145/145, field_diffs = 0, would_call_llm = 0
# 3) 打分
python3 scripts/kpi_dcr.py --cases eval/dcr/dcr_cases.jsonl --decisions /tmp/r387/assembly_real.jsonl
```

**关键独立性事实**：`field_diffs=0` ⇒ 子代理 harness（共享源编译真实 `PlanNodeFormalGate`）与**真装配二进制**逐字段一致 ⇒ 数字不是自证；`would_call_llm` 全 false ⇒ 判定过程**零 token**。

## §4 结果（多口径）

> **⚠ 本节是 R387 首轮数字（当时的快照），已被 §7/R388 修内核 + R392 刷新快照后的结论取代** —— 保留作演进留痕，勿引用其口径结论。

| 指标 | 值 | 备注 |
|---|---|---|
| **DCR（弃权计合规，FAVA 风格口径）** | **132/145 = 91.03%** | 落在 [85.5%, 95.5%] 内 |
| **DCR（弃权不计合规/保守口径）** | **88/145 = 60.69%** | 远离目标区间 |
| 覆盖率（Proceed+Violation） | 88/145 = 60.69% | **低于自定下限 70%** ⇒ 按成对条件**达标不成立** |
| 弃权率 | 32/145 = 22.07% | 全部为内核 Unknown |
| 畸形率 | 25/145 = 17.24% | 契约格式类 |
| 决断条目一致率 | 88/88 = 100% | 只要内核给结论就正确 |
| **主动误判（unsafe 放行/误阻断）** | **0** | 混淆矩阵无交叉错栏 |

分类一致率：entail 90.91% · refute 83.33% · vacuous 75.00% · out_of_fragment 100% · malformed 100% · absent 100%。

**结论**：达标**依赖口径**且**覆盖率不足** ⇒ 诚实结论是「**安全但不够决断**」：从不放行未证明节点（unsafe=0），但在 13 条 z3 可判定的用例上弃权。**达标不成立**。

## §5 13 条不一致 = 三条内核完备性缺口（下轮精确靶点）

| 缺口 | 失败用例 | 真实契约样例 | 根因 |
|---|---|---|---|
| (a) 等式传递/多变量消元 | c018, c023, c024 | `premise x+y==10 / premise z==x+y / goal z==10` | FM 消元未做等式替换 ⇒ `premise_decision_unknown` |
| (b) 反例搜索域过小 | c044, c052–c055 | `premise 0<=x / premise x<=1000000 / goal x<500000` | 真反例 `x=504034` 落在搜索框外 ⇒ `refute_decision_unknown` |
| (c) **整数 gcd/整除判定缺失** | c066, c074, c077, c079, c081 | `premise 3*x-3*y==1 / goal x==y`（`3∤1` 无整数解 ⇒ 空真） | 有理数判定无法为整；缺 `gcd(a_i) | b` 检验 |

修复 (c) 预计可救 5 条 vacuous（≥+3.4pp DCR、+3.4pp 覆盖率）；(a)(b) 各再 +2~4pp。三条全修 ⇒ 覆盖率可望达 70% 下限。

## §6 诚实边界（未测/不可测）

1. **T1–T4 未对齐**：上表两种口径给 91.03% 与 60.69%，区间跨 30pp ⇒ **在口径未定前，"达到 90.5% ±5pp"不可断言**。
2. 62/145 标签是构造性的（非 oracle 实证）。
3. 题集是**判定层**评测；**未测**"模型自产契约 → 计划 → 节点闸门"的 live 端到端合规率（需契约前置注入生产线，属 S2 后续）。
4. 子代理内核层对比（`kernel_out.jsonl`）**按行序对齐**（该文件无 id）⇒ 该对比仅作旁证，不作为结论依据。
5. z3 是独立 oracle，但 z3 与内核**同为整数语义**，二者共同盲区不可由本方案发现。

---

## §7 R388：内核三条缺口全修 ⇒ 真装配 145/145 全对（口径修正）

### §7.1 三条缺口的修法（对应 §5）

| 缺口 | 修法 | 为什么不引入不健全 |
|---|---|---|
| (c) 整数 gcd 整除判定缺失 | `Satisfiable` 开头新增**(c) 健全整数必要条件**：显式等式 `Σaᵢxᵢ=b` 且 `gcd(aᵢ)∤b` ⇒ `Sat.Unsat` | **只可能新增 Unsat**（必要条件，无假 Unsat）；c066/c074/c077/c079/c081 全转 Vacuous |
| (b) 反例搜索域过小 | 取点窗口由硬编码 `±65536` **参数化**（`-window/+window`），窗野外可取点、外框无界 ⇒ Unknown | 窗口变大只影响**能不能找到**反例；找到的反例仍逐点代回校验 ⇒ 只可能更完备，不新增假反例 |
| (a)(d) 等式传递/多变量消元 + 主元误选 | 等式代入**对每个 \|系数\|=1 的候选主元都代入一遍**（弃"出现次数最少"单点启发式） | 上一版启发式挑到 `b` 而目标变量 `a` 留在策略值上 ⇒ c052–c054 永取不到反例 |

### §7.2 真装配复跑（L3，零 LLM 调用）

`dotnet run --project src/agent.host -c Release -- --formal-eval eval/dcr/dcr_cases.jsonl` ⇒ 145 行、`gate_enabled=True`、exit=0。

| 口径 | 数值 | 说明 |
|---|---|---|
| **DCR（弃权计合规）** | **145/145 = 100.00%** | 弃权/畸形按合规计 ⇒ 触到该口径上界 |
| 保守口径（已决断且正确 / N） | 101/145 = **69.66%** | **恰等于题集可决断集上限**（145 − 19 out_of_fragment − 25 malformed = 101） |
| **可决断集覆盖率（修正口径）** | **101/101 = 100.00%** | 分母 = 可决断集，非全量题集 |
| 弃权率 / 畸形率 | 13.10% / 17.24% | |
| 决断条目一致率 / 主动误判 | **100.00% / 0** | 无一条"放行未证明节点" |

**分类一致率：entail 100% · refute 100% · vacuous 100% · out_of_fragment 100% · malformed 96%(24/25) · absent 100%。**

### §7.3 z3 独立审计（第四条验证腿，新增）

`eval/dcr/audit_decisions.py`（**不 import 内核任何代码**，只用 z3 复核装配裁决）：

```
AUDIT by z3 (独立 oracle, 与内核实现无关)
  决策总数              = 145
  Refuted 反例经复核为真 = 30   反例为假 = 0
  Proved 经复核确 unsat  = 33   存在反例 = 0
  非数学断言 (Unknown/Malformed/NoFormal/无目标) = 82
AUDIT_RESULT=SOUND
```

即：**反例不是编的**（30/30 逐变量代入后 z3 仍 sat）、**证明不是假的**（33/33 `premise ∧ ¬goal` 真 unsat）。

### §7.4 口径修正（§4/§5 的原结论作废）

- 原自定"覆盖率 ≥70%"**数学上不可达**：19 条 out_of_fragment + 25 条 malformed 共 44 条**设计上就不该决断** ⇒ 上限 = 101/145 = 69.66% < 70%。**是口径设定错误，不是能力不足** ⇒ 已改为**可决断集覆盖率**（分母 = 可决断集）。
- 因此 §4 的"达标不成立"**只对旧口径成立**；新口径下可决断集覆盖率 100%、主动误判 0 ⇒ **安全性与决断力同时满足**。
- **仍未解**：T1–T4（FAVA 的 DCR 公式/分母/弃权处置/aggregate 合并）不可得 ⇒ **"达到 90.5%±5pp"仍不可单口径断言**；两个口径分别落在区间之上（100%）与之下（69.66%），**达标与否完全取决于弃权是否计合规**。

### §7.5 内核层 vs 装配层 19 条差异 = 层职责，不是错误

| 差异 | 条数 | 说明 |
|---|---|---|
| 内核 CLI 对空契约返回 Malformed，闸门按 `NoFormal("absent")` → Proceed | 18 | absent 类**缺失≠错误**（契约四态铁律①） |
| 内核 CLI 允许 goal-only 并 Refute，闸门要求 premise/no_formal ⇒ Malformed | 1（c108） | 契约结构完整性属**契约层**职责 |

⇒ 内核层对比的期望列应读作"原始内核能力"，**装配层才是契约语义的裁决**；内核层自检 `check --selftest` **14/14 全绿**。

---

## §8 R392：仓库内两份 eval 快照是 R387 旧物（已刷新）+ 重命名零漂移证明

### §8.1 触发（重命名被迫复跑）

R392 把模块 `click-rover` 改名为 `agent.rover`（目录/项目名/内部文件夹/命名空间全小写，类名不动）。
按"改名后必须用真产物复验数值不变"的纪律重跑，发现仓库内 `eval/dcr/assembly_out.jsonl` 与
`eval/dcr/kernel_out.jsonl` **不是 R388 真装配/kernel 快照**，而是 **R387 时代旧物**：

| 文件 | 旧快照（=R387 旧物） | R388 权威 / R392 复跑 |
|---|---|---|
| `assembly_out.jsonl` | 145 行、32 条 `Unknown` ⇒ **DCR 132/145 = 91.03%** | 19 条 `Unknown`（全为 out_of_fragment）⇒ **DCR 145/145 = 100.00%** |
| `kernel_out.jsonl` | 32 条 `Unknown` | 19 条 `Unknown` |
| 差异行 | — | **13 条**（c018/c023/c024/c044/c052–c055/c066/c074/c077/c079/c081） |

13 条差异行的契约全部命中 §7.1 已修的三条缺口（等式传递/反例域/gcd 整除）⇒ 说明这两份仓库快照
**早于 R388 的内核修复**。R387 的 `91.03%` 因此是**修前**数字。

### §8.2 复跑证据（两条独立腿）

1. **装配层**：AOT 原生产物（`dotnet publish src/agent.host -c Release -r linux-x64` ⇒ 原生
   `agenthost`，IL 警告 0）跑 `--formal-eval eval/dcr/dcr_cases.jsonl` ⇒ 145 行；
   与 `/tmp/r388/assembly_real.jsonl`（R388 真装配快照）**逐条 0 差异**；`ms` 由 R388 的 ~32.7 ms/条
   降到 **~0.18 ms/条**（AOT 免 JIT，仅作旁证）。
2. **内核层**：重命名后的 `agent.rover check <case>.assert --json` 逐条复跑 145 条 ⇒ 与
   `/tmp/r388/kernel_out.jsonl` **逐条 0 差异**（含 `note` 与反例变量取值）。

⇒ **重命名零语义漂移**（两条腿各自 145/145、0 差异），且仓库快照已刷新为 R388/R392 权威值。

### §8.3 z3 独立审计（刷新后重跑）

`eval/dcr/audit_decisions.py`（不 import 内核代码，仅 z3）⇒ `AUDIT_RESULT=SOUND`：
**30/30 Refuted 反例经 z3 复核为真、33/33 Proved 确 unsat、0 假**；
另有 1 条 `Refuted` 属内核层（c108，装配层判 Malformed ⇒ 层职责差异，同 §7.5）。
逐条与题集自带 `expected_verdict` 比对：**145/145 一致**。

### §8.4 刷新后的权威结论（`eval/dcr/dcr_report.txt`）

| 口径 | 数值 |
|---|---|
| **DCR（弃权计合规）** | **145/145 = 100.00%** |
| 保守口径 | 101/145 = 69.66%（= 可决断集上限） |
| 覆盖率（Proceed+Violation） | 101/145 = 69.66%（Proceed 51 / Violation 50 / Abstained 19 / Malformed 25） |
| 分类一致率 | entail/refute/vacuous/out_of_fragment/malformed/absent **全 100%** |
| 主动误判 | **0** |

### §8.5 诚实边界（新增）

- 旧快照之所以长期未被发现，是因为 **R388 的真装配复跑产物落在 `/tmp`，仓库内那份未同步** ⇒
  "临时目录里的权威快照 ≠ 仓库里的权威快照"。**已加纪律**：涉及仓库内 eval 快照的轮次，必须
  **由仓库内产物（相对路径）复跑并直接覆盖仓库文件**，禁止只在 `/tmp` 留证。
- 内核层 `kernel_out.jsonl` **行内无 id**，与 cases 的对齐仍靠行序（脚本已显式声明该假设）⇒
  该对比只作旁证。
- T1–T4 与"90.5%±5pp 能否成立"**仍开放**（口径取决于弃权是否计合规）。


