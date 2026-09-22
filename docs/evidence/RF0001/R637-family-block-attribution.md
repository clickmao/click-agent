# R637 证据面 · `B_family_block` 整族归零的只读逐例定因（承 R636 下轮候选 ①）

| 项 | 值 |
|---|---|
| 轮次 / 性质 | R637 · 只读复算轮（零产品源码改动 / 零重测 / 零新臂 / 零远端 / 零新增夹具语义） |
| 起手闸 | `python3 tools/roundcheck/roundcheck.py preflight --round R637`（rc=0；见 kpi 行 `gate`） |
| 预注册（声明先于跑） | `eval/rover/r637/prereg-r637.json`（sha256 见下） |
| 判决件 | `eval/rover/r637/verdict-r637.json`（**rc = 1**：J4 机制假设被证伪，其余全过） |
| DAG | `eval/rover/r637/dag-r637.md` |
| 人读报告 | `eval/rover/r637/report-r637.md` |
| 题集冻结件双钉 | `eval/rover/r610/cases/cases-r521.json` sha256 `270128eb85c7afc07244c10c8845a22a541a7a60587a870125089e93422fccd7`（`cases_pin_ok=true`） |

## 证据命令（可独立复跑；全部零远端、零产品写）

```bash
cd /home/agentuser/AgentFramework
python3 eval/rover/r637/attrib_r637.py                # J0–J6 全量只读定因 ⇒ out/percase-r637.json + out/attrib-run.log
python3 eval/rover/r637/minfix_r637.py                # 逐跑次一行最小修复实验 + 空重写负控 ⇒ out/minfix-r637.json（rc=0）
python3 eval/rover/r637/family_lift_r637.py --selftest # 新判据 F_lift_min 五态自检 ⇒ family-lift-r637-selftest.json
python3 eval/capability/status_gen.py --check         # 收口：违规 0 / 基准漂移 0 / 缺源 0
```

## 关键读数（逐字取自落盘件，非叙述）

| 判据 | 读数 | 出处（文件字段） |
|---|---|---|
| J0 oracle 正控 | `n=15 match=15 mismatch=[] pass=True` | `verdict-r637.json → checks.J0_oracle_positive_control` |
| J1 census 交叉校验 | `checked=47 mismatch=[] pass=True`（VOID 剔除 1：`r633:w227/agentP-r2` `cli_rc=124`） | `→ checks.J1_census_reproduction` |
| J2/J3 归属守恒 | `non_ok_total=205 = product 205 + construction 0 + criterion 0`，`conservation_ok=true` | `→ checks.J2_J3_per_case_attribution` |
| **J4 预注册机制假设** | **`pass=False`**（`FAMILY_BLOCK` 机制分布 = `ENTRY_ERROR 2 / COLD_SET_EQUAL 1 / COLD_SET_OTHER 2`） | `→ checks.J4_mechanism_hypothesis` |
| J5 变异负控三件 | 空重写 `0/15` ∧ 正确实现 `15/15` ∧ 恒 LOSE `4/15` ⇒ 3/3 PASS | `→ checks.J5_negative_controls` |
| J5b 最小修复实验 | 4/4 PASS；`r636:w236/codex` 逐步 `[0, 13, 15]`（**两处缺陷叠加**）；四跑次其它三族逐例不变 | `→ checks.J5b_minfix_per_blocked_run` / `out/minfix-r637.json` |
| J6 确定性 ×2 | 5/5 整族归零跑次逐例 `identical=true` | `→ checks.J6_determinism` |
| 新判据空心闸实证 | S2：`F_lift_min_median=0`（PASS）而 `F_lift_min_worst=−15`（FAIL）；S3 旁路聚合口径判 PASS | `family-lift-r637-selftest.json → S2_detail` |

## 事后判别特征（`checks_posthoc`，**显式标事后性**；预注册 J4 判 FAIL 不翻案）

- 特征 = **`intersect == 0 ∧ missing == n_truth`**（真值冷点在探针面**全丢**）：wythoff 整族归零跑次 **4/4 命中**；非块跑次 **1/21 假阳**；`CLEAN` **0/36 假阳**。
- 原四变类机制标签（`COLD_SET_EQUAL / SHIFT / OTHER / ENTRY_ERROR`）**分辨率不足**：`ENTRY_ERROR` 在 `PARTIAL_FAMILY` 与 `FAMILY_BLOCK` 中均出现 ⇒ 不可作判别式。
- **探针家族覆盖缺口**：冷集探针只覆盖 `wythoff`；第 5 个块位于 `sub` 族 ⇒ 该跑次在本探针下**不可判**（其 `COLD_SET_EQUAL` 是「探针不适用」，**不得**读作「该族正常」）。

## 证据级别与边界（证据阶梯 L0–L4）

- 级别 = **L2/L3 之间**：真机执行（在临时副本上真跑产物，非静态读码）但在**冻结快照**上，非生产链路 ⇒ 行级定因只对冻结面成立。
- **不作**收益/降幅宣称；铁律 14 三档终局目标读数本轮不动、不宣称。
- 未测项声明：`sub` 族块的行级机理 **未测到**；真机（生产链路）修复 **未做**（轮性质 = 只读）。
