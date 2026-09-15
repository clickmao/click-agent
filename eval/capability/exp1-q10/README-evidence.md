# EXP1-Q10 证据说明 · 弱边再细分轴 (仪器 v2.5.0 → v2.6.0)

- **轮次标签**: `EXP1-Q10`（**不占主线轮号**；对侧 30m 作业在跑 R444 构建窗口 ⇒ 本侧只跑纯静态仪器、零 dotnet、不动 `src/`）
- **推进的计划项**: `docs/plans/v0.22.0-exp1-local-index-and-code-graph.md` J.10 **候选 #1**（弱边再细分 `weak_kind` + 两侧夹具），只推进一步
- **证据等级**: **L1-static**（无编译/测试/AOT —— 不得对外报 L3/L4）
- **计划文档**: 本附录 K（含预注册表 / 读数 / A-B / 对账 / 缺陷 / 边界 / 下轮候选）

## 1. 本轮改了什么（一句话因果链）

弱边轴（v2.5.0）只能回答"这条引用是强边还是弱边"，无法回答**"弱边里哪些根本不是缺陷嫌疑"**；
J.9 的 25 项人工抽检虽已给出分界线，但**散文结论混用了两个单位**（符号级 20 ÷ 引用级 62 = "32%"）——
⇒ 本轮把该分界线做成**可机检的平行轴**（`weak_kind`，四类 + 预注册优先级），并**用同一条规则同时施加于符号级与边级**，
再回头对账旧散文 ⇒ 旧句作废，量级改为边级 `11/63 = 17.5%`；且证明该规则与 Q9 表格**逐项 25/25 一致**（分歧只在散文计数）。

## 2. 产物表（全部在 `eval/capability/exp1-q10/`）

| 文件 | 内容 | 体积/结果 |
|---|---|---|
| `prereg_q10.json` | 预注册（判据 C1–C8 / 预测 P1–P5 / 排除项）**读数前写入** | — |
| `patch_v250_to_v260.py` | 锚点式纯文本补丁（14 条锚点，每条命中数必须 == 1） | exit 0 |
| `patch_pins.json` | 源/产物 sha256 + 逐条锚点日志 | `probe_v260.py` sha `e90c7d7f…`, 90,535 B |
| `probe_v260.py` | 仪器 v2.6.0（新增 `name_shape` / `declaration_index` / `symbol_weak_kind` / `weak_kind` + G9 闸） | — |
| `selftest_v250.json` / `selftest_v260.json` | 双向夹具自证 | **71/71 → 89/89 全绿**（+18 条新夹具，含 K1–K11 两侧 + 负控） |
| `attribution_q10.json` / `citations.jsonl` / `continuations.jsonl` | 真机读数全量落盘 | probe exit **0**，G1–G9 **全绿** |
| `weak_kind_table.json` / `.md` | 63 条弱边逐条 kind + 逐符号证据 + 被引文件上下文行（人工可审计） | 5 项自检全过 |
| `ab_kind.py` / `ab_kind.json` / `ab/run250/` `ab/run260/` | A/B 零回归 + 守恒 + 非平凡 + 口径对账 + 逐项一致率 | exit 0，`CRITERIA_PASS` |
| `probe_stdout.json` / `kind_table_stdout.json` / `ab_stdout.json` | 三条命令的 stdout 原始落盘 | — |

复现（一条命令链）：
```
cd eval/capability/exp1-q10
python3 patch_v250_to_v260.py && python3 probe_v260.py --selftest \
  && python3 probe_v260.py --repo /home/agentuser/AgentFramework --out attribution_q10.json \
  && python3 kind_table_v260.py && python3 ab_kind.py
```

## 3. 读数（v2.6.0 真机）

| 面 | 值 |
|---|---|
| 引用判定（旧轴，与 v2.5.0 逐位相同） | `ok 758` / `symbol_absent 67` / `waived 70` / `retired 21` / `stale_path 8` / `stale_lines 4` |
| 边强（旧轴） | `strong 365` / `weak 63` / `broken 39` / `waived 461`（和 **928** == live 代码引用，G8 守恒） |
| 弱边子级（旧轴） | `weak_code 46` / `weak_noncode 17` |
| **边级 kind（新）** | `cross_file 33` / `other 17` / **`named_fact 11`** / `comment_only 2`（和 **63** == 弱边数） |
| **符号级 kind（新）** | `cross_file 41` / `other 30` / `named_fact 16` / `comment_only 3`（90 枚） |
| 强边内混的弱符号 | `named_fact 6` / `cross_file 5` / `comment_only 2` / `other 5`（18 枚，旧轴只记个数） |

## 4. 判据与预测

| 项 | 结果 |
|---|---|
| C1 加性零回归 / C2 守恒 / C3 非平凡 / C6 对账 | ✅ / ✅ / ✅ / ✅ |
| P1 边级 `named_fact` < 20 | ✅ 实测 **11** |
| P2 类别 ≥3 / P3 `cross_file` ≥1 / P5 零回归 | ✅ / ✅ / ✅ |
| **P4 符号级 == 20** | ❌ 实测 **16** —— **分母口径不同**（90 枚含 `code_mention` vs Q9 的 25 枚 `noncode∧ok`）；不据此宣称 Q9 错 |

**对账（`checks_posthoc`）**：Q9 A 表 25 项按 (符号, 被引文件) 逐项比 ⇒ `n_agree=25`、`n_conflict=0`；
本轮 `noncode∧ok` 共 27 枚 = 弱边内 20 枚 + 强边内混的 7 枚，多出的 2 枚（`local_turn_gate_reject`、`msg_sha16`）来自**新文档**（语料漂移，逐条可查）。

## 5. 诚实边界

1. **L1-static**：无真机编译/测试/AOT；`declared_elsewhere` 是词法级启发式（非 AST）⇒ **下界**（漏计只会把 `cross_file` 降级）。
2. 该轴**不判红**：`other`（17 条边）是 catch-all，单列计数；细分不改判任何 verdict。
3. **语料是移动目标**：本轮 live 代码引用 928（Q9 记录 922）、弱边 63（Q9 记录 62）——零回归判据只用**同轮背靠背双执行**，不比跨轮绝对值。
4. **形式校验连续两轮结转**：对侧 MSBuild 节点在跑（`nodemode:1`）、`src/*.cs` 未提交改动、`MemAvailable` 1.64 GB < 2.8 GB 起手闸 ⇒ 拒跑；
   命令已登记（`dotnet test … --filter VerificationForm|SkillGeneralization|DevPlanDocRef`），对侧空闲即补跑。
5. 本轮**零产品源码改动**、**未跑 dotnet**、**只改 `eval/` 与 `docs/`**、**不占轮号**。
6. 未写入对侧在编辑的 `eval/capability/instruments.json`（R444 仪器登记表，`git status` 显示未跟踪且 09:00 仍在改）⇒ 跨作业写者冲突规避；
   若该登记表成为强制门禁，**下一轮**再按对侧 schema 登记本器具（先读后写，不猜格式）。

## 6. 自捕缺陷（均如实入档，不静默修）

| 编号 | 类型 | 症状 | 修法 |
|---|---|---|---|
| fixture-1 | 夹具 | 按符号名归组 ⇒ 同名符号的弱边与强边归同桶，断言读到 `[cross_file, None]` | 归组键改 `(符号元组, 被引文件)` |
| fixture-2 | 夹具 | 归组键用文档书写序，仪器对 `symbols` 排序 ⇒ 键永不命中 | 键用排序序 |
| instrument-1 | **测量** | 事后对账读 `attribution JSON` 的 `citations` 键（**不存在**）⇒ 空分布而判定照旧"通过"（**空心仪器**形态） | 改读 `citations.jsonl` + **非空硬闸**（0 条 ⇒ exit 3） |

## 7. 下轮候选（一步）

1. `other` 桶（17 条边 / 30 枚符号）先落**分布**再谈是否细分（`code_mention` 调用点 vs 形态-面不齐）。
2. J.10 #2 未动：`_queryEmbedding` / `RegisterCapability` 真实方法名人工复核（属**文档时效**，非引用图缺陷）。
3. **形式校验补跑**（连续两轮结转）——对侧空闲窗口一到立刻跑。
4. 把「符号级/引用级两计数分开、互不换算」升为仪器侧一等不变量。
