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
