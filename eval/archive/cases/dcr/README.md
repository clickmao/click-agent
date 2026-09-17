# eval/dcr —— 可证伪的 DCR 判定评测配件

本目录是 DCR（Decision Compliance Rate，判定一致率）评测的**配件**：一套标签不靠人拍的判定
题集，一个从真实装配输出算 DCR / 覆盖率 / 混淆矩阵的判定脚本，以及把它们跑通的全部证据。

> 铁律：本目录内所有期望标签均由**独立 oracle z3** 对 `premise ∧ ¬goal` 做**整数** SAT 推导；
> 结论全部来自真实运行。`src/**` 未被修改（harness 用共享源码编译，只读）。
>
> **口径定稿（R397, 单一口径）**：`DCR = (TP+TN)/(TP+TN+FP+FN)`，**无弃权项**，非 `Proceed` 一律 **fail-closed 记 block**（FAVA 语义）。
> 实测 **145/145 = 100.00%**（TP=94 · TN=51 · FP=0 · FN=0）；**口径敏感度 30.34pp**（弃权/畸形按放行 ⇒ 69.66%）。
> ⇒ **禁止再以双口径并列汇报**；重算器 `eval/dcr/dcr_align.py`（`--selftest` 7/7，机读产物 `docs/reports/dcr/dcr-single-metric.json`，报告 `docs/reports/r397/`）。

---

## 1. 文件清单

| 路径 | 行数 | 说明 |
|---|---|---|
| `eval/dcr/gen_cases.py` | 713 | 题集生成器 + 生成期自验（parser → z3） |
| `eval/dcr/dcr_cases.jsonl` | 145 | **交付物 A**：判定题集，6 类 |
| `eval/dcr/verify_cases.py` | 72 | 独立重算自验：读回 jsonl ↔ z3 oracle 逐条比对 |
| `eval/dcr/assembly_out.jsonl` | 145 | 真实装配层（`PlanNodeFormalGate.Evaluate`）判定输出 |
| `eval/dcr/kernel_out.jsonl` | 145 | 真实内核 CLI（`agent.rover check --json`）输出，按行序对齐 |
| `eval/dcr/harness/` | — | 真实装配回放 harness（csproj + Program.cs + Stubs.cs） |
| `eval/dcr/dcr_align.py` | 307 | **单一口径重算器**（FAVA 语义 fail-closed）+ 敏感度表 + 独立实现对账 + `--selftest` 负控 7/7 |
| `eval/dcr/dcr_report.txt` | — | 真实装配输出的 DCR 报告快照 |
| `eval/dcr/selftest/` | — | 脚本自测夹具与负例（非 DCR 结论） |
| `scripts/kpi_dcr.py` | 356 | **交付物 B**：DCR 判定脚本（stdlib only） |

---

## 2. 交付物 A：判定题集 `dcr_cases.jsonl`

### 2.1 分类计数（每类 ≥12）

| category | N | 期望 | z3 参与 |
|---|---:|---|---|
| entail | 33 | Proceed / Proved | 是（unsat） |
| refute | 30 | Violation / Refuted | 是（sat + model） |
| vacuous | 20 | Violation / Vacuous | 是（premises unsat） |
| out_of_fragment | 19 | Abstained / Unknown | 否（`z3_label=n/a`） |
| malformed | 25 | Malformed / Malformed | 否（`z3_label=n/a`） |
| absent | 18 | Proceed / NoFormal | 否（`z3_label=n/a`） |
| **合计** | **145** | | 83 条有 z3 标签 / 62 条显式 n/a |

每行字段：`id, category, contract, expected_disposition, expected_verdict, label_source,
z3_label, z3_label_why, z3_model, self_check`。

### 2.2 对抗族（题集要求逐条落实）

- **(a) 整数严格性边界**：`x > 4` ⊨ `x >= 5`（c001，等价对，z3=unsat）；`x < 11` vs `x <= 10`
  （c038 refute）；整数不可满足 `2*x == 7`（vacuous）。
- **(b) 隐藏反例的大区间**：`premise 0 <= x / premise x <= 1000000 / goal x < 500000`
  （c044，z3=sat，model `{x: 504034}`）。**这是本评测最有价值的发现**：真实内核在此**弃权**
  （见 §5），说明其反例搜索在宽反例域上不闭合。
- **(c) 表面像蕴含实则不蕴含**：如 `premise x + y == 10 / goal x < 10`（c031，refute）。
- **(d) 系数为 0 的退化约束**（曾出真 bug）：`x + 0*y == 7 / goal x == 8`（c047）、
  `0*x + y == 3 / goal y >= 4`（c048）、`0*x + 0*y + x == 5 / goal x >= 6`（c049）。
- **(e) 多变量（≥4 变量）线性系统**：`a+b+c+d==20, a>=0 / goal a<=4`（c052，refute）；
  以及**可判**对照 `a==5,b==6,c==7,d==8 / goal a+b+c+d==25`（c061，refute）。

### 2.3 生成 + 生成期自验（真实输出）

```
$ /tmp/z3env/bin/python eval/dcr/gen_cases.py
z3: 5.1.0
total=145
  entail           33
  refute           30
  vacuous          20
  out_of_fragment  19
  malformed        25
  absent           18
self_check: 145 ok / 0 bad
wrote /home/agentuser/AgentFramework/eval/dcr/dcr_cases.jsonl (145 lines)
```

### 2.4 独立重算自验（读回文件 ↔ z3，真实输出）

```
$ /tmp/z3env/bin/python eval/dcr/verify_cases.py
cases file : /home/agentuser/AgentFramework/eval/dcr/dcr_cases.jsonl
total      : 145
z3-checked : 83
no-z3      : 62 (out_of_fragment/malformed/absent, label_source 显式 n/a)
categories : {'absent': 18, 'entail': 33, 'malformed': 25, 'out_of_fragment': 19, 'refute': 30, 'vacuous': 20}
RESULT     : OK — 文件内标签与 z3 oracle 重算完全一致 (0 mismatch)
```

### 2.5 oracle 单条取证（真实输出）

```
$ /tmp/z3env/bin/python - <<'PY'
from gen_cases import z3_label_contract
for cid in ['c001','c044','c052','c066','c079']: ...
PY
c001 [entail] status=entail z3_label=unsat model=None          # x > 4 ⊨ x >= 5
c044 [refute] status=refute z3_label=sat   model={'x': 504034} # 大区间隐藏反例
c052 [refute] status=refute z3_label=sat   model={'a': 20, 'b': 0, 'c': 0, 'd': 0}
c066 [vacuous] status=vacuous z3_label=premises_unsat model=None  # 3x-3y==1
c079 [vacuous] status=vacuous z3_label=premises_unsat model=None  # 2x==2y+1
```

---

## 3. 真实装配层回放（产生 decisions）

harness 以**共享源码编译**方式引用仓库真实 `src/agent.rover/formal/*.cs` +
`FormalAssertionContract.cs` + `PlanNodeFormalGate.cs`，逐条把 contract 交给真实 `Evaluate()`。
`Stubs.cs` 仅提供 `PlanNode.Id` / `AgentTelemetry.Emit` 的编译依赖，**不替代任何判定逻辑**。

```
$ export PATH="$HOME/.dotnet:$PATH"
$ dotnet build eval/dcr/harness/dcrval.csproj -c Release --nologo -v q \
    -o /tmp/dcrval_out -p:BaseIntermediateOutputPath=/tmp/dcrval_obj/
Build succeeded.  0 Warning(s)  0 Error(s)
$ dotnet /tmp/dcrval_out/dcrval.dll eval/dcr/dcr_cases.jsonl eval/dcr/assembly_out.jsonl
wrote eval/dcr/assembly_out.jsonl rows=145
```

内核层输出（真实 CLI，逐条 `check --json`，按**行序**与 cases 对齐）：

```
$ CL=src/agent.rover/bin/Release/net10.0/agent.rover
$ # 对每条 case 写 .assert 文件后: "$CL" check <file> --json
kernel rows: 145 nonjson: 0
```

---

## 4. 交付物 B：`scripts/kpi_dcr.py`

stdlib only。用法：

```
python3 scripts/kpi_dcr.py --cases <cases.jsonl> --decisions <agent_out.jsonl> \
                           [--kernel <agent.rover_out.jsonl>] [--json]
```

输出：N、DCR=agree/N、覆盖率=(Proceed+Violation)/N（分母含弃权与畸形，两者单列）、弃权率、
畸形率、决断一致率、**unsafe 主动误判数**、每 category 计数/一致率、混淆矩阵、未一致明细。
`--json` 追加机器可读 JSON（报告之后）。

### 4.1 真实装配输出的 DCR 结论（`eval/dcr/dcr_report.txt`）

> **快照刷新 (R392, 2026-09-13)**：装配层 `assembly_out.jsonl` 由 **AOT 原生产物**
> (`dotnet publish src/agent.host -c Release -r linux-x64` 后的 `agenthost --formal-eval`) 复跑生成；
> 内核层 `kernel_out.jsonl` 由重命名后的 `agent.rover check <case>.assert --json` 复跑生成。
> 此前仓库内两份快照是 **R387 时代旧物**（含 13 条 `Unknown`），与 R388 已修的内核不一致 ——
> 详见 `docs/improvements.md` R392 节。刷新后二者与 R388 真装配/kernel 权威快照 **逐条 0 差异**。

```
N (总条目)              = 145
DCR                     = 145/145 = 1.0000  (100.00%)
覆盖率 (Proceed+Violation) = 101/145 = 0.6966  (69.66%)
  其中 Proceed          = 51 (35.17%)
  其中 Violation        = 50 (34.48%)
弃权率 (Abstained)      = 19/145 = 13.10%
畸形率 (Malformed)      = 25/145 = 17.24%
决断条目一致率           = 1.0000  (100.00%)
主动误判 (unsafe)        = 0
category             N   agree       rate
entail              33      33    100.00%
refute              30      30    100.00%
vacuous             20      20    100.00%
out_of_fragment     19      19    100.00%
malformed           25      25    100.00%
absent              18      18    100.00%
混淆矩阵 (行=expected, 列=actual):
                Proceed  Violation  Abstained  Malformed
Proceed              51          0          0          0
Violation             0         50          0          0
Abstained             0          0         19          0
Malformed             0          0          0         25
```

**0 条不一致、0 条主动误判**（Proceed/Violation 方向无一错误）；弃权 19 条全部是设计上不该决断的
`out_of_fragment`（诚实弃权口径）。

### 4.2 内核层对比（`--kernel`）

按行序对齐（行内无 id，报告显式声明该假设；行数不等即报错）。真实数字：
**内核 vs 期望 = 126/145 (86.90%)；内核 vs 装配 = 126/145 (86.90%)**。
19 条内核≠装配的差异**不是内核判错**，而是层职责不同：18 条 absent（原始 CLI 无契约层
`no_formal` 语义，空输入→Malformed，闸门→NoFormal/Proceed）+ 1 条 `goal x < 10`（契约层要求
premise，CLI 允许 goal-only 故能 Refute）。脚本已在报告中打印该说明。

### 4.3 脚本自测（**手造假 decisions，非 DCR 结论**）

夹具：4 条 case + 手工 decisions（t3 故意弃权不一致），手算 DCR = 3/4 = 0.75。

```
$ python3 scripts/kpi_dcr.py --cases eval/dcr/selftest/selftest_cases.jsonl \
      --decisions eval/dcr/selftest/selftest_decisions.jsonl \
      --kernel eval/dcr/selftest/selftest_kernel.jsonl
N (总条目)              = 4
DCR                     = 3/4 = 0.7500  (75.00%)      <- 与手算一致
覆盖率 (Proceed+Violation) = 3/4 = 0.7500  (75.00%)
弃权率 (Abstained)      = 1/4 = 25.00%
畸形率 (Malformed)      = 0/4 = 0.00%
内核层 vs 期望一致率   = 3/4 = 75.00%
内核层 vs 装配层一致率 = 2/4 = 50.00%
未一致条目明细: t3 exp=Violation(Vacuous) act=Abstained(Unknown)
```

by-id 对齐分支同样有夹具（打乱行序、行内带 id）：

```
$ python3 scripts/kpi_dcr.py --cases eval/dcr/selftest/selftest_cases.jsonl \
      --decisions eval/dcr/selftest/selftest_decisions.jsonl \
      --kernel eval/dcr/selftest/selftest_kernel_byid.jsonl
对齐假设              = 行内带 id, 按 id 对齐
内核层 vs 期望一致率   = 3/4 = 75.00%
内核层 vs 装配层一致率 = 2/4 = 50.00%
```

### 4.4 负例（可证伪性：标签缺失 / id 对不上 ⇒ 报错 + 非零退出）

```
$ python3 scripts/kpi_dcr.py --cases eval/dcr/selftest/bad_cases_missing_label.jsonl \
      --decisions eval/dcr/selftest/selftest_decisions.jsonl
ERROR: cases t1: expected_disposition missing/invalid (None); 标签缺失必须报错, 不得猜
exit=2

$ python3 scripts/kpi_dcr.py --cases eval/dcr/selftest/selftest_cases.jsonl \
      --decisions eval/dcr/selftest/bad_decisions_id_mismatch.jsonl
ERROR: decisions/cases id mismatch: missing=3 ['t2', 't3', 't4'] extra=1 ['t9']
exit=2
```

---

## 5. 诚实边界（不得当 DCR 结论的东西）

1. **62/145 条无 z3 标签**：`out_of_fragment`、`malformed`、`absent` 三类的期望是**构造性的**
   （由片段判定 / 语法规则 / 契约层语义给出），不是 z3 推导；文件里 `label_source` 与
   `z3_label=n/a` 已显式标注，绝不冒充 oracle。
2. **entail/refute/vacuous 的 z3 标签是硬真值**；但 `out_of_fragment` 是否真的“超出片段”由
   生成器的片段判定器给出，z3 不判断该分类。
3. **13 条 DCR 缺口全部是诚实弃权**（覆盖 entail 3 / refute 5 / vacuous 5）。根因：真实内核用
   Int128 精确外包围盒枚举，盒体积 > 100000 或存在无界变量时回落到 `Unknown`。典型：
   - 宽反例域（c044 的 50 万点区间）无法枚举 ⇒ 弃权；
   - ≥2 自由变量、无界时的整数奇偶矛盾（`3x-3y==1`、`2x==2y+1` 等）无法用盒判定 ⇒ 弃权。
   这些是**内核完备性缺口**，不是错误判定——`unsafe 主动误判 = 0` 证明方向安全。
4. **内核层对比假设“按行序对齐”**：`agent.rover check --json` 输出不含 id，对齐假设未由数据
   本身保证；脚本在行数不等时直接报错，不猜。
5. **自测非结论**：§4.3 的 0.75 是脚本自证的算术正确性，与真实 DCR 无关，已显式标注。
6. 依赖 `z3-solver`（本机 `/tmp/z3env`，z3 5.1.0）与 .NET 10 SDK；换环境需重装。

## 6. 未完成项

- 真实内核 CLI 输出不含 id，故生产数据走按行序对齐；by-id 分支仅有自测夹具覆盖（已验），
  无真实 by_id 数据。
- 未把 harness 接入仓库测试工程（仅共享源码独立编译）；未做 CI 集成。
- `src/**` 未改、未 commit、未 push（遵守暂停令）。
