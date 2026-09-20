#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R595 收口器：台账行（幂等原地替换）+ 轮志 + §7 主报告块 + §7 运行状态快照 + improvements 条目。

输入（全部**在盘读数**；本器只汇总与写文档，不重算任何测量）：
  · eval/rover/r595/taskface-pool-r595.json      （判据 v3 第三窗集 = 主判据）
  · eval/rover/r595/kpi-table-r595.json          （成本三列 / 基线 / 真值行）
  · eval/rover/r595/gate-margin-r595.json + face-gate-r595.json  （候选⑤）
  · eval/rover/r595/face-coldset-r595.json       （候选②）
  · eval/rover/r595/face-census-r595.json        （候选③）
  · eval/rover/r595/landing-predicate-r595.json  （候选④）
  · ~/.agentframework/harness/runs/r595/precond-r595-v2.json   （铁律 11 修后行使）
禁：git push / gh api 写 / 镜像上传；禁改任何判据阈值。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
RP = os.path.join(REPO, "eval/rover/r595")
HARNESS = os.path.expanduser("~/.agentframework/harness/runs/r595")
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")
MASTER = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
ROLLBACK = os.path.join(REPO, "docs/reports/dynamic-telemetry-eval-rollback-strategy.md")
IMPROV = os.path.join(REPO, "docs/improvements.md")
REPORT = os.path.join(RP, "report-r595.md")
FIN = os.path.join(RP, "finish-r595.json")
TS = "2026-09-20T14:12+08:00"


def load(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-docs", action="store_true")
    a = ap.parse_args()

    pool = load(os.path.join(RP, "taskface-pool-r595.json"))
    kpi = load(os.path.join(RP, "kpi-table-r595.json"))
    gm = load(os.path.join(RP, "gate-margin-r595.json"))
    fg = load(os.path.join(RP, "face-gate-r595.json"))
    cs = load(os.path.join(RP, "face-coldset-r595.json"))
    cn = load(os.path.join(RP, "face-census-r595.json"))
    lp = load(os.path.join(RP, "landing-predicate-r595.json"))
    pc = load(os.path.join(HARNESS, "precond-r595-v2.json"))

    s1, s2, s3 = (pool["set1_first_window_set"], pool["set2_second_window_set"],
                  pool["set3_third_window_set"])
    jux = pool["juxtaposition"]
    v3 = s3["C1_task_face_v3"]
    recs = kpi["readings"]

    def agg_arm(side):
        rs = [r for r in recs if r["side"] == side]

        def smean(key):
            xs = [r[key] for r in rs if isinstance(r.get(key), (int, float))]
            return round(sum(xs) / len(xs), 4) if xs else None

        return {"calls": sum(r["calls"] for r in rs),
                "new_prompt": sum(r["new_prompt"] for r in rs),
                "completion": sum(r["completion"] for r in rs),
                "v_all_med": smean("v_all"), "v_incr_med": smean("v_incr"),
                "n_vincr_missing": sum(1 for r in rs if not isinstance(r.get("v_incr"), (int, float))),
                "rc": [r["rc"] for r in rs], "stages": [r["stage"] for r in rs],
                "steps": [r["steps_executed"] for r in rs],
                "plan_steps_total": [r["plan_steps_total"] for r in rs],
                "cases": [[r["cases_pass"], r["cases_total"]] for r in rs]}

    prod, tru = agg_arm("agent"), agg_arm("codex")
    # 铁律 11 前置器 rc：JSON 里 rc 是**逐臂**字段，总判决由 acceptable_scoped 编码
    # （rc 语义 0 可验收 / 1 未可验收 / 3 输入缺失，承 r507pre 口径）。
    pc_rc = 0 if (pc.get("executable_and_correct") and pc.get("acceptable_scoped")) else 1
    pc_blocked = len(pc.get("blocked_scoped") or [])
    pc_arms = {}
    for w, wd in (pc.get("windows") or {}).items():
        for s, sd in (wd.get("arms") or {}).items():
            g = sd.get("g1") if isinstance(sd, dict) else None
            if isinstance(g, dict):
                pc_arms["%s/%s" % (w, s)] = {"rc": g.get("rc"), "cases": g.get("cases"),
                                             "expect": g.get("expect"),
                                             "failed": (g.get("failed") or [])[:6]}
    out = {"round": "R595", "ts": TS,
           "inputs": {"pool": s3["C1_task_face_v3"]["pass"], "coldset_rc": cs["rc"],
                      "census_rc": cn["rc"], "lp_rc": lp["verdict"]["rc"], "precond_rc": pc_rc}}
    out["summary"] = {
        "criterion_v3_third_window_set": "valid=%d median=%s neg=%d ⇒ %s"
                                         % (v3["valid_windows"], v3["median_D_task"], v3["neg_windows"],
                                            "PASS" if v3["pass"] else "FAIL"),
        "criterion_v3_set1_reproduced": jux["reproduced_first_set"]["consistent"],
        "family_all_pass": jux["family_all_pass_rate"],
        "gate_clause": "prev_swing=%d margin=%d REQ=%d cap_binding=%s"
                       % (fg["prev_swing_effective"], gm["margin"], gm["req"], gm["cap_binding"]),
        "gate_attempts": len(fg["attempts"]),
        "candidate2_coldset": {k: cs["agg"][k]["class_hist"] for k in ("agent", "codex")},
        "candidate3_census": {"agent": cn["agg"]["agent"]["inconsistent_runs"],
                             "codex": cn["agg"]["codex"]["inconsistent_runs"], "rc": cn["rc"]},
        "iron11_arms": pc_arms, "iron11_blocked_scoped": pc_blocked,
        "candidate4_v_int_second_set": {"runs": lp["scope"]["runs_ok"],
                                        "v_int_hist": lp["agent"]["v_int_hist"],
                                        "layer": lp["agent"]["layer"]},
        "iron_law_11": "rc=%s ⇒ 全部质量/成本读数标「参考（未可验收）」" % pc_rc,
        "tokens": "调用 %d / 新算 prompt %d / completion %d（产品侧；真值 %d / %d / %d）"
                  % (prod["calls"], prod["new_prompt"], prod["completion"],
                     tru["calls"], tru["new_prompt"], tru["completion"]),
    }

    # ---------------- 轮志 ----------------
    report = """# R595 轮志 — 判据 v3 **第三窗集**行使（真机臂轮）+ 只读并轮（候选②③⑤）+ 候选④

**轮次性质**：真机臂轮（新窗 w169..w171，每窗 codex 真值 ×1 + 产品默认档 ×3）+ 只读定因并轮。
零产品源码改动 / 零新增夹具语义 / 零新增开关（承用户令 2026-09-18「不许新增夹具和额外开发」）。
**单变量**：窗集。被测件同件（`bin sha 4b70fd7cdb39`）、题集逐字节复用（`e0c667c2a313c04b`，
g1 题面 sha256 `516f3208963c6e66…`）、判据 v3 与集合 R585–R591 同 sha。
**预注册/DAG**：`eval/rover/r595/{prereg-r595.json,dag-r595.md}`（起手前落盘；草稿 13:54 < 起臂 13:58）。

## 主判据：判据 v3 第三窗集

| 窗集 | 有效窗 | 任务面中位 | 负号窗 | 判决 |
|---|---|---|---|---|
| set1（R585–588，w154–165） | 9 | −0.6667 | 8 | PASS（**与 R589 登记件逐位复现**） |
| set2（R591，w166–168） | 1 | −0.6667 | 1 | PASS |
| **set3（R595，w169–171）** | **2** | **−0.5** | **2** | **PASS** |

阈值 −0.34 与「负号窗 ≥ 半数」写死、非事后调；set3 的 w170 因**真值自身未全对**（C0）标 unreliable、不进配对、单列。
族 all-pass 率（set1/set2/set3）：`life` `nim` `sub` = 0.9722/1.0/1.0；**`wythoff` = 0.3889/0.4444/0.4444`**
⇒ 缺口**只在 wythoff 族**、跨三窗集稳定复现；其余三族无缺口。

## 成本三列（产品默认档 vs 外部真值，同窗面）

| 臂 | 调用 | 新算 prompt | completion | 命中率 v_all / v_incr | 步数 |
|---|---|---|---|---|---|
| R595D（产品） | 18 | 4,180 | 39,526 | 0.98 / 0.97 | [14,7,7,9,7,22,7,14,7] |
| C1（codex 真值） | 45 | 23,709 | 21,140 | 0.90 / 0.94 | 未测 |

rc 分布 `[5,5,5,5,8,0,5,0,5]`；stage：`expect_stdout_exhausted` ×6 / `self_test_unmet` ×1 / `done` ×2。

## 候选② 冷集构造层定因下沉（只读，零子进程）

由在盘登记件的集合字段（`cold_only_prod` / `cold_only_true` 是**位置集合本身**）重建
`D = (T \\ M) ∪ U`（守恒式 `|D| == declared_cold_n` **59/59 全过**），再按预注册判别：

- agent（44 跑次）：**CONSISTENT 19 / B1 15 / B3 9 / B2 1**；
- codex（15 跑次）：**CONSISTENT 11 / B1 1 / B3 3**；
- 分类器控制：POS(边界整行)⇒B2、NEG(Beatty 变体 round)⇒B1、NEG2(单侧缺失)⇒B3、OK⇒CONSISTENT ⇒
  4 个互异值（**非恒真门**）、控制全过。
- **结论修正**：冷集构造**并非普遍坏**——agent 19/44 跑次冷集**逐点等于真值**；R592 的
  `B_coldset 184（0.6595）`是**例次份额**（少数跑次贡献大量例次），不能读成「大多数跑次冷集错」。
  B1（双向差、非边界局限）15 例次簇 + B3（单侧差）9 跑次单列（机制子类：整行超出 / 高 k 缺失 / 散布）。

## 候选③ 交付物自洽性普查（只读）— **器具无牙，结论不可用**

修复 docstring 跨行假属性后：59 跑次**零不自洽**；但 POS 控制（删掉被引属性）**不翻面**
⇒ 根因是交付物的 `__main__` 走**动态派发**（`importlib` + 名字解析），静态属性抽取面在结构上**看不见**该引用
⇒ 该面「0 不自洽」是**盲**而非**自洽**。按纪律记 rc=2 **器具缺陷单列**，不当能力读数。

## 候选④ `V_int` 第二窗集分布（真机臂轮，同件定因器）

对 r595 新窗快照用与 r593 **同一件**定因器（ROUNDS=[r595], `--codex-too`）：
12 跑次全跑通；层 `(b) 冷集构造层` 6 / `(c) 本轴外` 6；`cold_set_equal` True 6 / False 6；
`v_int_hist = {0:10, 38:1, 26:1}` ⇒ **`V_int>0` 仍未成为活触发面**（阈值化 = **未测**，承预注册）。
两侧例次：agent 90/135 通过（桶 `D_delivery_or_shape 24 / B_coldset 20 / A_selection_order 1`），
codex 40/45（桶全 `B_coldset` 5）。`controls/teeth/non_trivial/readonly/conservation` 全过；
`zero_regression=false` 属**口径错配的结构性红**（该检查固定对 r592 的 set1 面，本轮面不同）⇒ 单列、不作结论。

## 候选⑤ 起手闸余量按同态在飞窗实测派生

源 = `r591/logs/run-samples.jsonl`（n=97，2713–2815MB ⇒ swing **102MB**；R594 为只读轮、无运行期采样器 ⇒ 不可作源）。
本轮实测两次起手：**attempt#1 CEIL 2683 < 下限 ⇒ FAIL-CLOSED**；attempt#2 CEIL 2788 ⇒
`margin=clamp(102,60,cap=78)=78`（**cap_binding**）、`REQ=2728`、A1/A2 **PASS**（2810/2801MB）
⇒ 同条款下红绿分别出现，**条款有牙、非恒真门**。起手前按既有纪律收口本会话 own-tool 子进程（血统 = 本会话 gateway）并记前后差
（`reap-own-tool-r595.json`：pyright 155.9MB → 释放 113MB）。

## 器具自捕 3 件（留档不翻案、未放宽任何判据）

1. **缺冻结用例集 ⇒ 空心绿（最贵）**：派生时漏拷 `cases-r521.json` ⇒ 12 跑次 `cases.txt` 全是 Traceback ⇒
   kpi 读到 **0/0**、C1 在 0/0 上**恒真**（D=0）、铁律 11 前置器 rc=1 同源。处置：v1 证据整份归档
   （`archive-v1-casesmissing/` + `kpi-table-r595-v1casesmissing.json` + `verdict-r595-v1casesmissing.json`）；
   **只重跑后处理（判分 + 汇总），不重测测量**；补齐件 sha 与 R591 同源逐位比对（`270128eb85c7afc0`）。
2. **docstring 跨行假属性**：`main_refs` 未剥注释/三引号串 ⇒ `wythoff.Reads` 之类假引用使 NEG 控制也翻红
   （留档 `face-census-r595-v1docstringfp.json`）。
3. **候选③ 控制无牙**（见上）⇒ rc=2 单列。

## 门禁 / 铁律 11

- **形式门禁**：`dotnet test … --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒
  **Failed 0 / Passed 14 / Skipped 0**。
- **铁律 11（修后行使 v2）**：`exec_precondition --round r595` ⇒ **rc=1 BLOCKED**（6 臂未全对：
  w169/agentD-r1 52/58、w169/agentD-r2 45/58、w170/agentD-r1 51/58、w170/agentD-r2 43/58、
  w170/codex 53/58、w171/agentD-r2 54/58）⇒ **全部质量/成本读数标「参考（未可验收）」**。
- 零 `src/` 改动、零登记表改动 ⇒ 依 R588–R594 同处置**不造** capability 登记行。

## 诚实边界

1. set3 只 **2 个有效窗**（w170 真值自身未全对）⇒ 单窗集样本小，**摆动幅度与 set1 同量级比较后才可作趋势**；
   跨窗集**禁相减**，只并列。
2. 铁律 11 rc=1 ⇒ 本轮质量面**未过可验收前置**，只能作「参考（未可验收）」。
3. 候选②③④均为**只读/聚合面**，不构成能力验收；候选①（产品侧修复）**仍待用户放行**。
4. 候选③面**无牙**（动态派发），其「0 不自洽」不得引用为结论。
5. 候选④的 `zero_regression=false` 是口径错配的结构性红，已单列，不进结论。
6. 铁律 11 前置器的 v1 读数（器具缺陷所致）**不翻案**，v2 单独命名空间并列在档。
"""

    # ---------------- 台账行 ----------------
    readings = {
        "round": "R595", "ts": TS,
        "judge_v3_third_window_set": {
            "set1": {"valid": s1["C1_task_face_v3"]["valid_windows"],
                     "median": s1["C1_task_face_v3"]["median_D_task"],
                     "neg": s1["C1_task_face_v3"]["neg_windows"],
                     "reproduced_vs_registered": jux["reproduced_first_set"]["consistent"]},
            "set2": {"valid": s2["C1_task_face_v3"]["valid_windows"],
                     "median": s2["C1_task_face_v3"]["median_D_task"],
                     "neg": s2["C1_task_face_v3"]["neg_windows"]},
            "set3": {"valid": v3["valid_windows"], "median": v3["median_D_task"],
                     "neg": v3["neg_windows"], "threshold": v3["threshold_median"],
                     "pass": v3["pass"], "unreliable_windows": s3["summary"]["unreliable_windows_truth_self_fail"]},
            "family_all_pass_rate": jux["family_all_pass_rate"],
            "negative_control_has_teeth": s3["C7_negative_control"]["has_teeth"],
            "readonly_sha": s3["C5_readonly"]["sha"][:16],
        },
        "cost_three_columns": {
            "product": {"calls": prod["calls"], "new_prompt": prod["new_prompt"],
                        "completion": prod["completion"], "v_all": prod["v_all_med"],
                        "v_incr": prod["v_incr_med"], "rc": prod["rc"], "stages": prod["stages"],
                        "steps": prod["steps"], "plan_steps_total": prod["plan_steps_total"]},
            "truth": {"calls": tru["calls"], "new_prompt": tru["new_prompt"],
                      "completion": tru["completion"], "v_all": tru["v_all_med"],
                      "v_incr": tru["v_incr_med"]},
            "status": "参考（未可验收：铁律 11 rc=1）"},
        "gate_margin_clause": {
            "prev_swing_effective": fg["prev_swing_effective"], "prev_swing_source": fg["prev_swing_source"],
            "attempt1": "FAIL_CLOSED (CEIL 2683)", "attempt2": "PASS (CEIL 2788, margin 78, REQ 2728)",
            "cap_binding": gm["cap_binding"], "has_teeth": True,
            "own_tool_reap_mb": 113},
        "candidate2_coldset_diff_structure": {
            "agent": cs["agg"]["agent"]["class_hist"], "codex": cs["agg"]["codex"]["class_hist"],
            "conservation_all": cs["agg"]["agent"]["conservation_all"],
            "controls_ok": cs["controls_ok"], "classifier_distinct_values": cs["classifier_distinct_values"],
            "headline_correction": "冷集并非普遍坏：agent 19/44 跑次逐点等于真值；B_coldset 0.6595 是例次份额而非跑次份额"},
        "candidate3_self_consistency_census": {
            "agent_inconsistent": cn["agg"]["agent"]["inconsistent_runs"],
            "codex_inconsistent": cn["agg"]["codex"]["inconsistent_runs"],
            "rc": cn["rc"], "usable": False,
            "root_cause": "交付物走 importlib 动态派发 ⇒ 静态属性抽取面结构性盲；POS 控制不翻面"},
        "candidate4_v_int_second_window_set": {
            "runs": lp["scope"]["runs_ok"], "v_int_hist": lp["agent"]["v_int_hist"],
            "layer": lp["agent"]["layer"], "cold_set_equal": {"true": 6, "false": 6},
            "threshold_status": "未测（承预注册：本轮只扩分布面，不作阈值化）",
            "zero_regression": "口径错配的结构性红（固定对 r592 的 set1 面）⇒ 单列不作结论",
            "agent_buckets": lp["agent"]["buckets"], "codex_buckets": lp["codex"]["buckets"]},
        "instrument_self_catch": [
            "缺 cases-r521.json ⇒ 12 跑次判分全 Traceback ⇒ kpi 0/0 空心绿 + 铁律11 rc=1 同源（v1 归档）",
            "census docstring 跨行假属性（wythoff.Reads）⇒ NEG 控制翻红（v1 归档）",
            "census POS 控制无牙（动态派发）⇒ rc=2 单列",
        ],
        "zero_regression": {"set1_reproduced_vs_r589": jux["reproduced_first_set"]["consistent"],
                            "readonly_face_sha": s3["C5_readonly"]["sha"][:16]},
        "form_gate": "14/14 (Failed 0 / Passed 14 / Skipped 0)",
        "iron_law_11": "exec_precondition --round r595 ⇒ rc=%s BLOCKED ⇒ 全部质量/成本读数标「参考（未可验收）」"
                       % pc_rc,
        "tokens": "产品 18 调用 / 4,180 新算 / 39,526 completion；真值 45 / 23,709 / 21,140（口径 = 中继 dump 时间轴）",
    }
    row = {
        "round": "R595", "ts": TS,
        "kind": "判据 v3 **第三窗集**行使（真机臂轮 w169..w171：codex 真值 ×1 + 产品默认档 ×3）+ 只读并轮（候选②③⑤）+ 候选④ V_int 第二窗集分布。零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集",
        "change": ("① 派生 `eval/rover/r595/{run_r595.sh,kpi_r595.py,pool_taskface_r595.py,launch_r595.sh,derive_r595.py}`"
                   "（只替换命名空间/窗集常量，判据逻辑源一字未改）；② `eval/rover/r595/face_r595.py`（候选②冷集集合差结构 +"
                   " 候选③全属性契约普查 + 候选⑤起手闸余量派生，三 part 同器）；③ 候选④ 复用 r593 同件定因器 `--rounds r595`；"
                   "④ 后处理重跑器 `rejudge_r595.sh`（器具缺陷修复后只重跑判分与汇总，不重测）；⑤ 轮志 + 台账 + §7 块 + §7 快照 + improvements。"
                   "器具自捕 3 件（缺冻结用例集 ⇒ 空心绿；docstring 跨行假属性；census 控制无牙）均留档不翻案、未放宽判据。"),
        "readings": readings,
        "artifact": ("eval/rover/r595/{report-r595.md,prereg-r595.json,dag-r595.md,taskface-pool-r595.json,kpi-table-r595.json,"
                     "verdict-r595.json,gate-margin-r595.json,face-gate-r595.json,face-coldset-r595.json,face-census-r595.json,"
                     "landing-predicate-r595.json,archive-v1-casesmissing/,kpi-table-r595-v1casesmissing.json,"
                     "verdict-r595-v1casesmissing.json,face-census-r595-v1docstringfp.json,reap-own-tool-r595.json} · "
                     "docs/reports/iteration-master-plan.md §7 R595 块 · docs/reports/dynamic-telemetry-eval-rollback-strategy.md §7 快照"),
    }
    with io.open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(report)

    lines = io.open(LEDGER, encoding="utf-8").read().splitlines()
    kept, replaced = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            kept.append(ln)
            continue
        if d.get("round") == "R595":
            replaced += 1
            continue
        kept.append(ln)
    kept.append(json.dumps(row, ensure_ascii=False))
    with io.open(LEDGER, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kept) + "\n")
    out["ledger"] = {"rows_before": len(lines), "rows_after": len(kept), "replaced_same_round": replaced}

    if not a.no_docs:
        block = (
            "\n- **R595（真机臂轮：判据 v3 **第三窗集**行使（w169..w171，codex 真值 ×1 + 产品默认档 ×3）+ 只读并轮（候选②③⑤）"
            "+ 候选④ `V_int` 第二窗集分布；零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集）**: "
            "**修改点** ① `eval/rover/r595/{run_r595.sh,kpi_r595.py,pool_taskface_r595.py,launch_r595.sh,derive_r595.py}` 派生件"
            "（只替换命名空间/窗集常量，判据逻辑源一字未改）；② `eval/rover/r595/face_r595.py`（候选②冷集集合差结构 + 候选③全属性契约普查 + "
            "候选⑤起手闸余量派生）；③ 候选④复用 r593 同件定因器（`--rounds r595 --codex-too`）；④ 后处理重跑器 `rejudge_r595.sh`；"
            "⑤ 轮志/台账/§7 块/§7 快照/improvements。**真机读数**：**主判据 v3 第三窗集** set3（w169–171）**valid=2、中位 −0.5、负号窗 2 ⇒ PASS**"
            "（阈值 −0.34 写死；w170 因真值自身未全对标 unreliable、不进配对）；set1/set2 并列（9/−0.6667/8；1/−0.6667/1），"
            "set1 与 R589 登记件**逐位复现**；族 all-pass 率 `life`/`nim`/`sub` = 0.9722/1.0/1.0、**`wythoff` = 0.3889/0.4444/0.4444** ⇒ "
            "缺口**只在 wythoff 族**、跨三窗集稳定复现。**成本三列**（参考·未可验收）：产品 18 调用 / 4,180 新算 / 39,526 completion，"
            "真值 45 / 23,709 / 21,140；命中率 v_all 0.98/0.90、v_incr 0.97/0.94（口径 = 中继 dump 时间轴）；产品 rc `[5,5,5,5,8,0,5,0,5]`、"
            "stage `expect_stdout_exhausted`×6 / `self_test_unmet`×1 / `done`×2。**候选②**（只读，零子进程）：由登记件集合字段重建 "
            "`D=(T\\M)∪U`，守恒 **59/59**；agent **CONSISTENT 19 / B1 15 / B3 9 / B2 1**、codex **11 / 1 / 3**；控制四值互异（非恒真门）⇒ "
            "**重要修正**：冷集**并非普遍坏**（19/44 跑次逐点等于真值），R592 的 `B_coldset 0.6595` 是**例次份额**而非跑次份额。"
            "**候选③**：修 docstring 假属性后 59 跑次零不自洽，但 POS 控制**不翻面**（交付物走 `importlib` 动态派发 ⇒ 静态面结构性盲）⇒ "
            "**rc=2 器具缺陷单列，「0 不自洽」不得引用为结论**。**候选④**：r595 12 跑次同件定因器 ⇒ 层 `(b)6/(c)6`、`cold_set_equal` 6/6、"
            "`v_int_hist {0:10,38:1,26:1}` ⇒ `V_int>0` 仍非活触发面、**阈值化未测**；agent 90/135（`D_delivery_or_shape 24 / B_coldset 20 / "
            "A_selection_order 1`）、codex 40/45（全 `B_coldset` 5）；`zero_regression=false` 属口径错配的结构性红、单列不作结论。"
            "**候选⑤**：余量源 = r591 同态在飞窗采样（n=97、2713–2815MB ⇒ swing **102MB**）；本轮 attempt#1 **FAIL-CLOSED**（CEIL 2683）、"
            "attempt#2 **PASS**（CEIL 2788、margin 78（cap_binding）、REQ 2728）⇒ 条款有牙；起手前收口本会话 own-tool 子进程并记差（Δ113MB）。"
            "**器具自捕 3 件（留档不翻案、未放宽判据）**：① **缺冻结用例集 ⇒ 空心绿**（12 跑次判分全 Traceback ⇒ kpi 0/0 恒真、铁律 11 rc=1 同源；"
            "处置 = v1 整份归档 + **只重跑后处理不重测** + 补件 sha 与 R591 同源比对）；② `main_refs` docstring 跨行假属性；③ 候选③控制无牙。"
            "**形式门禁** **14/14**（Failed 0 / Passed 14 / Skipped 0）。**铁律 11**：`exec_precondition --round r595` ⇒ **rc=1 BLOCKED**"
            "（6 臂未全对）⇒ **全部质量/成本读数标「参考（未可验收）」**，禁作验收依据。零 `src/` 改动、零登记表改动 ⇒ **不造** capability 登记行。"
            "**诚实边界**：① set3 仅 2 个有效窗 ⇒ 摆动与 set1 同尺度比较后才可作趋势，跨窗集**禁相减**；② 铁律 11 rc=1 ⇒ 未过可验收前置；"
            "③ 候选②③④为只读/聚合面，不构成能力验收，候选①（产品侧修复）**仍待用户放行**；④ 候选③面**无牙**；⑤ 候选④零回归红为口径错配；"
            "⑥ 铁律 11 v1 读数不翻案，v2 并列在档。"
            "轮志 `eval/rover/r595/report-r595.md`、预注册/DAG `eval/rover/r595/{prereg-r595.json,dag-r595.md}`、"
            "读数 `eval/rover/r595/{taskface-pool-r595.json,kpi-table-r595.json,verdict-r595.json,gate-margin-r595.json,"
            "face-gate-r595.json,face-coldset-r595.json,face-census-r595.json,landing-predicate-r595.json}`、"
            "台账 `eval/capability/kpi.jsonl`（R595）。\n"
            "\n- **下轮候选 (R596)**: ① **产品侧处置裁定（待用户放行）**：候选②已把份额修正为「例次而非跑次」、"
            "B1 15 例次簇机制可命名（双向差、非边界局限）⇒ 落点已收束到 `wythoff` 冷集构造器；产品侧修复**须用户放行** "
            "② **铁律 11 可验收化**：`rc=1` 的 6 臂全部集中在 `wythoff` 族（`w169/r1 52/58`、`w169/r2 45/58`、`w170/r1 51/58`、"
            "`w170/r2 43/58`、`w170/codex 53/58`、`w171/r2 54/58`）⇒ 只读逐例归因（A 类 = 加厚 prompt 的收益上界）"
            "③ **候选③改制**：静态面在动态派发下无牙 ⇒ 改**行为面**口径（逐游戏 `-m games` rc/stderr census）并配两侧控制 "
            "④ `V_int` 阈值化的**第三窗集**（须新跑次；本轮已扩到第二窗集） ⑤ 起手闸余量按本轮实测振幅（`run-samples` r595 面）重派生。\n"
        )
        with io.open(MASTER, "a", encoding="utf-8") as fh:
            fh.write(block)
        out["master_appended"] = True

        rb = io.open(ROLLBACK, encoding="utf-8").read()
        anchor = "> - **最近一轮（R594，2026-09-20 · cron 60min tick）**:"
        if anchor in rb:
            newline = ("> - **最近一轮（R595，2026-09-20 · cron 60min tick）**: **真机臂轮 = 判据 v3 第三窗集行使**"
                       "（w169..w171：codex 真值 ×1 + 产品默认档 ×3）+ 只读并轮（候选②③⑤）+ 候选④ `V_int` 第二窗集分布；"
                       "零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件（bin sha `4b70fd7cdb39`）同题集。"
                       "**主判据** set3 **valid=2 / 中位 −0.5 / 负号窗 2 ⇒ PASS**（set1 9/−0.6667/8、set2 1/−0.6667/1；set1 与 R589 登记件逐位复现）；"
                       "族 all-pass `wythoff` = 0.3889/0.4444/**0.4444**、其余三族 1.0 ⇒ 缺口只在 wythoff 且跨三窗集稳定。"
                       "**成本三列（参考·未可验收）**：产品 18 调用 / 4,180 新算 / 39,526 completion vs 真值 45 / 23,709 / 21,140；"
                       "命中率 v_all 0.98/0.90、v_incr 0.97/0.94。**候选②**：冷集差结构（守恒 59/59）⇒ agent **19 一致 / B1 15 / B3 9 / B2 1**、"
                       "codex **11/1/3**；**修正** R592 `B_coldset 0.6595` 为**例次份额**而非跑次份额。**候选③**：静态契约普查在动态派发下**无牙** ⇒ rc=2 单列。"
                       "**候选④**：`v_int_hist {0:10,38:1,26:1}`、层 (b)6/(c)6 ⇒ `V_int` 仍非活触发面、阈值化未测。**候选⑤**：余量源 r591 "
                       "（swing 102MB）⇒ attempt#1 FAIL-CLOSED / attempt#2 PASS（margin 78 cap_binding、REQ 2728）⇒ 条款有牙。"
                       "**器具自捕 3 件**（缺冻结用例集 ⇒ kpi 0/0 空心绿与铁律 11 rc=1 同源；docstring 假属性；census 控制无牙）留档不翻案。"
                       "**形式门禁 14/14**；**铁律 11 rc=1**（6 臂未全对）⇒ 质量/成本读数一律「参考（未可验收）」，不宣称降幅。"
                       "轮志 `eval/rover/r595/report-r595.md`。\n")
            rb = rb.replace(anchor, newline + "> - **最近一轮（R594，2026-09-20 · cron 60min tick）**【历史快照，已被上方 R595 行取代】:", 1)
            with io.open(ROLLBACK, "w", encoding="utf-8") as fh:
                fh.write(rb)
            out["rollback_updated"] = True
        else:
            out["rollback_updated"] = False

        imp = io.open(IMPROV, encoding="utf-8").read()
        m = re.search(r"\n## R59\d", imp)
        sec = (
            "\n## R595 · 2026-09-20 · 状态: **完成（主判据 v3 第三窗集 PASS；形式门禁 14/14；铁律 11 rc=1 ⇒ 读数标未可验收）· 真机臂轮 + 只读并轮**"
            " · 主题: **判据 v3 第三窗集行使（缺口只在 `wythoff` 族、跨三窗集稳定）× 冷集差结构（份额口径修正）× `V_int` 第二窗集 × 起手闸余量实测派生**\n\n"
            "- **主判据**: set3（w169–171）**valid=2 / 中位 −0.5 / 负号窗 2 ⇒ PASS**；set1 9/−0.6667/8、set2 1/−0.6667/1；"
            "set1 与 R589 登记件逐位复现；族 all-pass `wythoff` 0.3889/0.4444/**0.4444**、`life`/`nim`/`sub` 1.0。\n"
            "- **候选②（修正 R592 口径）**: 冷集差结构（守恒 59/59、控制四值互异）⇒ agent **19 逐点一致 / B1 15 / B3 9 / B2 1**、codex **11/1/3**；"
            "`B_coldset 0.6595` 是**例次份额**，不得读成「多数跑次冷集错」。\n"
            "- **候选③**: 静态契约普查在交付物动态派发（`importlib`）下**结构性无牙**（POS 控制不翻面）⇒ rc=2 器具缺陷单列，结论不可用。\n"
            "- **候选④**: r595 12 跑次同件定因器 ⇒ 层 (b)6/(c)6、`v_int_hist {0:10,38:1,26:1}` ⇒ `V_int>0` 仍非活触发面、**阈值化未测**。\n"
            "- **候选⑤**: 余量源 = r591 同态在飞窗采样（swing 102MB）⇒ attempt#1 FAIL-CLOSED / attempt#2 PASS（margin 78、cap_binding、REQ 2728）⇒ 条款有牙；"
            "起手前 own-tool 收口 Δ113MB 已记档。\n"
            "- **器具自捕 3 件**: ① **缺冻结用例集 ⇒ 12 跑次判分全 Traceback ⇒ kpi 0/0 空心绿 + 铁律 11 rc=1 同源**（v1 整份归档；"
            "**只重跑后处理不重测**；补件 sha 与 R591 同源比对）；② docstring 跨行假属性；③ census 控制无牙。均不翻案、未放宽判据。\n"
            "- **边界**: 铁律 11 rc=1 ⇒ 全部质量/成本读数「参考（未可验收）」；set3 仅 2 有效窗、跨窗集禁相减；候选①（产品侧修复）待用户放行；"
            "候选④零回归红为口径错配。\n"
            "- 轮志 `eval/rover/r595/report-r595.md`、预注册 `prereg-r595.json`、DAG `dag-r595.md`、台账 `eval/capability/kpi.jsonl`（R595）。\n"
        )
        if m:
            imp = imp[:m.start()] + sec + imp[m.start():]
        else:
            imp = imp + sec
        with io.open(IMPROV, "w", encoding="utf-8") as fh:
            fh.write(imp)
        out["improvements_updated"] = True

    with io.open(FIN, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=1))
    print("ledger", out["ledger"], "docs", out.get("master_appended"), out.get("rollback_updated"),
          out.get("improvements_updated"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
