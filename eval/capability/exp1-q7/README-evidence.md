# EXP1-Q7 证据包 · 文档侧定点修复：改写失效路径 + 补退役标记

- **轮**: EXP1-Q7（60m 自检作业；**不占主线轮号**，与对侧 30m 主线作业（R440 网格）并行时本侧只改文档/探针，不跑 `dotnet`，不占轮号）
- **目标档**: `docs/plans/v0.22.0-exp1-local-index-and-code-graph.md`
- **执行**（附录 G.7 逐字结转）: 「把 `relocated` 的 10 条定点可改 + 3 条写法漂移 做文档侧定点修复（改写为显式路径；省略形态改全路径），并对 `retired_after_write` 引用补退役标记 —— 改动只碰文档，复跑仪器断言两桶归零」
- **证据等级**: **L1 静态机检**（真跑仪器/修复器 + 读回校验；无编译、无单测、无 AOT）
- **日期**: 2026-09-15（CST）

## 1. 预注册判据（读数前落盘）

见 `prereg_q7.json`（原文）与目标档 **附录 H.2**：

| 编号 | 判据 | 结果 |
|---|---|---|
| P1 | `relocated` 13 → 0 | ✅ 0（12 条→`ok`，1 条→`symbol_absent`，见 §3 归因） |
| P2 | `stale_path` 21 → 8，其中 `retired_after_write` 13 → 0、`retired` 8 → 21 | ✅ 8 / 21 |
| P3 | 非目标桶不恶化：`ok` 不下降；`stale_lines` ≤ 4；`symbol_absent` ≤ 66；`waived` ≤ 70 | ✅ 741→753 / 4 / 65→66 / 70 |
| P4 | 仪器 `--selftest` 全绿 | ✅ exit 0（`selftest_q7_after.txt`） |
| P5 | 确定性（同语料两跑逐位相同）∧ 非平凡（修复前后读数互异） | ✅ 两跑逐位相同；922→922 桶分布互异 |
| **P6（本轮新增，事后判定 D1 后补）** | **计数守恒**：语料引用总条数在改写前后**相等** | ✅ 922 = 922（修复器层 582 = 582） |

**排除项（明确零动作）**：`same_commit_as_deletion` **8 条**全部是 `src/agent/registry/CapabilityPlugin.cs`（删除提交 `af9856b`，8 处）。附录 G.2/G.5 已定性为**弃权非清白**（时间轴不可分，需变更前快照）；对其补标记会把弃权类**并入** `retired` 桶而抹掉该区分 ⇒ 本轮不动，语义留待裁定。
**观测项（只登记）**：`symbol_absent 65→66`、`stale_lines 4→4` 为非目标软桶（附录 E.3 已实证主语型启发式误报）。

## 2. 改动面（全部为文档，零 `src/`、零 `skills/`、零登记表）

修复器 `apply_doc_fixes_q7.py` **v1.1.0**（`sha256` 前缀 `e22deb1f0c348e41`），操作**全部由产物派生**（禁手打字面量）：

- 改写字面量 **13** 条（12 个 `(doc,line)`，其中 `v0.22.0-exp2` L32 双引用）＝ 定点 10 + 省略形态 3（`src/agent.core/.../*.cs` / `src/agent/.../*.cs` ⇒ 全路径）
- 补退役标记 **13** 条，标记文本 = `【已删 <sha7>】`，`sha7` 取自 Q6 复核器 `per_path_stale_truth[*].deletion_sha`；`已删` 由仪器模块常量 `RETIRED_MARKERS[0]` 派生，`【】` 由码位 `chr(0x3010)/chr(0x3011)` 构造
- 涉及 **10** 个文档；行数逐文档**不变**；`git diff` 只落在目标行

标记样例码位（防写入通道改写，见 §4 D1/D2）：`[12304, 24050, 21024, 32, 98, 48, 48, 57, 49, 55, 99, 12305]` = `【已删 b00917c】`（**无 U+200B**，已机检）。

## 3. 读数（仪器 v2.3.0；178 文档 / 594 只读输入逐文件 sha256）

| 桶 | 修前 | 修后 | 说明 |
|---|---|---|---|
| `relocated` | **13** | **0** | P1 |
| `stale_path` | **21** | **8** | P2（余 8 = 排除项） |
| `retired` | 8 | **21** | +13 本轮补标记 |
| `ok` | 741 | **753** | +12（12 条改写后路径成立；第 13 条落软桶） |
| `symbol_absent` | 65 | 66 | 第 13 条（`PromptAuditEntry` 省略形态，`relocated_fact_verdict` **修前即为** `symbol_absent`）迁移至此 |
| `stale_lines` | 4 | 4 | 未动 |
| `waived` | 70 | 70 | 未动（`ambiguous_bare_name 25 / out_of_scope 34 / unresolvable_bare_name 11`） |
| **引用总条数** | **922** | **922** | P6 计数守恒 |
| `stale_like_n` | 90 | 78 | 软桶合计 |

判据闸（仪器自证）：`G1_instrument_selfproof` / `G2_two_pass_identical` / `G3_waiver_visible` / `G4_premise_refuted` / `G5_families_distinct` / `G6_cont_nontrivial` **全 true**，`exit_code 0`。
修复器层读回校验（**绑定仪器真实行为**，非文本代理）：13 条改写复跑 `extract_citations` + `judge_citation` ⇒ `ok 11 / symbol_absent 1`；13 条补标记 ⇒ **`retired` 13/13**；`verify_bad 0`，`exit 0`。

## 4. 测量层缺陷与负控（本轮自捕）

### D1（真缺陷，已修）：标记插进引用 token **内部** ⇒ 13 条引用从语料消失，"桶归零"变空心绿

- **首版 v1.0.0**：按 `path` 子串 `find()` 定位，标记被插进 `路径` 与 `:行号` 之间（`` `...ForwardCli.cs【已删 b00917c】:16` ``）⇒ `CITE_RE` 不再匹配该 token ⇒ **13 条引用从语料中消失**。
- **症状形态（最危险的一种）**：**目标桶全部"达标"** —— `relocated` 13→0 ✅、`stale_path` 21→8 ✅、仪器 `exit 0`、两跑逐位相同 ✅；只有**总条数**不平（`ok +12` 与 `symbol_absent +1` 只能解释 13 条改写，**13 条标记引用的去向无处安放**）⇒ 追查发现总数 922→909。
- **触发方式（如实记录）**：不是靠判据，是靠**桶账不平**（读数复核）发现的；**首读的漏洞在于判据只看桶、不看总量**。
- **修法（v1.1.0）**：① 插入锚点改为**仪器自己的** `extract_citations()["pos_end"]`（+1 若紧跟 `]`/`` ` ``），不再用子串切片；② 判据改为**绑定仪器真实行为** —— 复跑仪器抽取 + `judge_citation`，断言该引用仍被抽取且档位符合预期（`retired`），而非"行内出现标记文本"；③ 新增**计数守恒不变量**（逐文档引用条数 + 全语料总条数）。
- **负控（可复现，已归档）**：修复器保留 `--insert-mode=path_end` 复现缺陷 ⇒ 计数 `582→569`、`count_invariant_ok=false`、`verify_bad=13`（全部 `MARK-MISSING`）、`exit 2`；仪器读数落 `attribution_q7_after_D1repro.json`（**总条数 909**，桶面仍"绿"）。即：**桶判据在缺陷态下会放行，只有计数守恒闸会报红** —— 这是 P6 被补进预注册的实证依据。

### D2（观察项）：写入通道对手打字面量的改写

本轮所有替换串/标记均由产物派生（模块常量 + 从 JSON 取 `sha7`），并**读回比对码位**（见 §2 样例）。未再复现附录 F.3 的斜杠改写。

## 5. 证据文件

- `prereg_q7.json` — 预注册判据 + 文档 sha256 前后 + 派生参数
- `apply_doc_fixes_q7.py` — 修复器 v1.1.0（含负控模式）
- `edit_plan.json` — v1.1.0 操作台账（逐文档 `sha256` 前后、`count_invariant`、`verify_verdicts`、排除项）
- `edit_plan_v100_defect.json` — **v1.0.0（缺陷版）**操作台账（含被销毁引用的行 sha256）
- `edit_plan_d1_negative_control.json` + `negctl_d1_stdout.txt` — 负控执行记录
- `attribution_q7_before.json` / `attribution_q7_after.json` / `attribution_q7_after_rerun.json` / `attribution_q7_after_D1repro.json` — 仪器读数（修复前 / 修复后 ×2 / **缺陷态负控**）
- `selftest_q7_after.txt` — 仪器自检（exit 0）
- `apply_stdout.txt`、`probe_after_stdout.txt` — 真跑 stdout 存档

## 6. 复现

```bash
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
# 1) 修复前读数（需先把 10 个文档回到 HEAD）
python3 eval/capability/exp1-q4/probe_doc_ref_integrity.py --out eval/capability/exp1-q7/attribution_q7_before.json
# 2) 应用文档侧定点修复（幂等；--apply 才落盘）
python3 eval/capability/exp1-q7/apply_doc_fixes_q7.py --apply
# 3) 修复后读数 ×2（确定性）
python3 eval/capability/exp1-q4/probe_doc_ref_integrity.py --out eval/capability/exp1-q7/attribution_q7_after.json
python3 eval/capability/exp1-q4/probe_doc_ref_integrity.py --out eval/capability/exp1-q7/attribution_q7_after_rerun.json
# 4) 负控（证明计数守恒闸会报红；跑完须 git checkout 10 文档再回 2)）
python3 eval/capability/exp1-q7/apply_doc_fixes_q7.py --apply --insert-mode=path_end \
        --plan-out=eval/capability/exp1-q7/edit_plan_d1_negative_control.json
python3 eval/capability/exp1-q4/probe_doc_ref_integrity.py --out eval/capability/exp1-q7/attribution_q7_after_D1repro.json
```

## 7. 诚实边界

1. **L1 静态机检**：无编译/单测/AOT/真机运行 ⇒ 不得报为 L3/L4。
2. **语料是移动目标**（对侧 30m 主线作业在改 `src/` 与 `docs/`，本轮期间其 `docs/plans/v0.60.0-r440-*` 为新未跟踪文件）⇒ 读数与 HEAD 绑定；确定性由两跑逐位相同 + 594 只读输入指纹归因，**不做"文件不动"的假设**。
3. **8 条 `same_commit_as_deletion` 未处理**（弃权非清白，见 §1 排除项）⇒ `stale_path` 未归零是**设计结果**，不是残留缺陷。G.7 原文「两桶归零」按**可动作类**解读（`relocated` + `retired_after_write`），本轮两者均 0；若按字面读作 `stale_path → 0`，则须先裁定这 8 条的语义（禁止用标记把弃权类洗成 retired）。
4. **`symbol_absent` 是全文匹配启发式**（非 AST）：同名出现在注释/字符串里也算命中 ⇒ 66 条只作候选，不作对外结论；本轮唯一的 66 号是**修前既定**的 `symbol_absent`（未引入新缺陷，但**也没有修好它**）。
5. **退役标记只声明"该路径在 HEAD 不存在且删除提交为 HEAD 祖先"**（外部真值来自 Q6 复核器），不声明引用"何时成形"；标记是**留痕**，不是引用正确性证明。
6. 修复器与仪器**解耦**：修复器只消费读数 JSON + 仪器模块常量/抽取器，**不修改仪器判据面**；仪器本轮的桶账变化全部可由改动解释（`ok +12` / `symbol_absent +1` / `retired +13` / `stale_path −13` / 总量不变）。
