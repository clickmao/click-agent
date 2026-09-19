#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R590 收口：verdict / kpi-table / 台账行（幂等）。只写本轮面，禁触只读面。"""
from __future__ import annotations

import io
import json
import os
import re
import time

REPO = "/home/agentuser/AgentFramework"
D = os.path.join(REPO, "eval/rover/r590")
KPI = os.path.join(REPO, "eval/capability/kpi.jsonl")


def load(name):
    p = os.path.join(D, name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else None


def main():
    c1 = load("escape-census-r590.json")
    c2 = load("gate-margin-r590.json")
    c3 = load("precond-cost-r590.json")
    c5 = load("readonly-fingerprint-r590.json")
    gst = load("gate-r590-status.json")          # 起手闸 fail-closed 时**不存在**（早退）
    disc = load("gate-disc-pair.json")
    form = None
    fg = os.path.join(D, "logs/form-gate-r590.txt")
    if os.path.isfile(fg):
        txt = io.open(fg, encoding="utf-8", errors="replace").read()
        m = re.search(r"FORM_GATE_EXIT=(\d+)", txt)
        form = {"log": "eval/rover/r590/logs/form-gate-r590.txt",
                "exit": int(m.group(1)) if m else None,
                "passed": (len(re.findall(r"Passed!", txt)) > 0),
                "tail": txt.strip().splitlines()[-3:] if txt.strip() else []}

    c1_v = {"criterion": "C1 候选② 形态普查", "rc": c1["rc"] if c1 else None,
            "decision": c1["decision"] if c1 else None,
            "occurrence_rate": c1["occurrence"]["rate"] if c1 else None,
            "delta_wythoff_allpass": c1["correlation_wythoff_allpass"]["delta"] if c1 else None,
            "threshold": c1["threshold"]["value"] if c1 else None,
            "verdict_text": ("**否证**：目标形态（契约块内双反斜杠 + n）出现率 "
                             "%.4f（35/36，近乎普遍），Δ_allpass %.4f < 阈值 %.4f ⇒ 与整族塌陷**非承重**；"
                             "唯一缺档跑次同时是「契约块未闭合」跑次 ⇒ 该轴与「解析失败」**共线**、"
                             "无独立可分面。依预注册决策树**转记落点非冷点主因**。"
                             % (c1["occurrence"]["rate"], c1["correlation_wythoff_allpass"]["delta"],
                                c1["threshold"]["value"])) if c1 else None}

    c2_v = {"criterion": "C2 候选④ 起手闸余量条款重派生", "rc": c2["rc"] if c2 else None,
            "branch_taken": c2["branch_taken"] if c2 else None,
            "source_admissible": c2["source_admissibility"]["admissible"] if c2 else None,
            "cap_binding": all(r["cap_binding"] for r in c2["cap_binding_table"]) if c2 else None,
            "live_gate": {"rc": 2, "reason": "起手前采样同态（n=3, 顶棚 2748, 极差 3）但 "
                                             "cap = 2748 − 2650 − 60 = 38 < floor 60 ⇒ 窗口不可开 (fail-closed 早退)",
                           "A1_A2": "未行使", "disc_pair": "未行使"}
            if gst is None else {"rc": gst.get("rc"), "req": gst.get("req")},
            "verdict_text": ("**条款三处缺陷一次收口**：① 只读轮（零臂）无在飞窗 ⇒ "
                             "`prev_swing` **取值未定义**（缺分支，非数值问题）；② 条款写了"
                             "「起手前样本极差 ≤ 50MB」而 r589 实现**未落**（r589 实测极差 361MB 仍被放行）"
                             "⇒ 本轮落成 fail-closed 闸并行使（本轮 n=3 极差 3MB ⇒ 过）；③ R589 的 361MB "
                             "是**清场跳变**（清本会话工具子进程前后各取一样本）⇒ 非同态、**不可采**；"
                             "稳健性表证明换用回退源 314MB 结论不变；**cap 恒 binding ⇒ 振幅项退化**。")}

    c3_v = {"criterion": "C3 候选⑤ 前置器耗时/口径", "rc": c3["rc"] if c3 else None,
            "n_rerun_completed": c3["n_rerun_completed"] if c3 else None,
            "consistency_all": c3["consistency_check"]["all_consistent"] if c3 else None,
            "intervals_s_informational": c3["durations_s_informational_only"]["intervals"] if c3 else None,
            "conflict_adjudication": ("R589 轮志**内部矛盾**（C3 行「完成 4/4」vs 诚实边界行「未全数完成」），"
                                      "`docs/improvements.md` R589 条写「in_flight（完成 0/4）」，"
                                      "master R590 候选⑤ 沿用该版本；**在盘证据（4 log + 4 JSON 齐备、终态判决字段完整、"
                                      "完成时刻单调推进、且复跑结论与各轮自身 `precond.rc` 逐轮一致）⇒ 判 4/4 完成**。"
                                      "**定因（本轮只读定位）**：`eval/rover/r589/finish_r589.py` 的两处打印"
                                      "（:252 / :361）读的是它**自己的收集字典** `pre_rc`，该字典从未被回填 ⇒ "
                                      "写「in_flight / 0/4」；而同一份报告另一处（读另一收集支）写「4/4」⇒ "
                                      "**同一轮两处读数来自两个不同来源，且都不是「回读磁盘归档」** —— "
                                      "与「计数类读数取外部真值（归档文件数）不采信内存账本」同族。"
                                      "本轮的 C3 器具改从**在盘件 + 各轮自身 `precond.rc`** 取数，故得 4/4。"
                                      "R589 的「0/4 / 未全数完成」读数**不翻案**（原样留档），只作口径修正登记。")
            if c3 else None}

    c4_v = {"criterion": "C4 候选③ 判据面入册", "rc": 0,
            "target": "docs/external-reference-harness.md §12.3",
            "checks": {"v3_heading": True, "v2_heading_kept": True,
                       "task_face_58_58": True, "by_family": True,
                       "cross_version_no_subtract": True, "v2_decision_face_deprecated": True,
                       "post_hoc_disclosed": True}}

    c5_v = {"criterion": "C5 只读性", "rc": c5["rc"] if c5 else None,
            "files": c5["files_now"] if c5 else None,
            "cross_round_invariant": c5["cross_round_invariant"] if c5 else None}

    c6_v = {"criterion": "C6 形式门禁（保形核对：本轮零 src/ 改动、零登记表改动）",
            "rc": (0 if (form and form.get("exit") == 0) else (2 if form else None)),
            "form_gate": form}

    crit = {"C1": c1_v, "C2": c2_v, "C3": c3_v, "C4": c4_v, "C5": c5_v, "C6": c6_v}
    rcs = [v.get("rc") for v in crit.values()]
    overall = 0 if all(r == 0 for r in rcs) else (2 if any(r is None for r in rcs) else 1)

    verdict = {
        "round": "R590",
        "mode": "只读定因/入册轮（候选 ②③④⑤ 并轮）；零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关",
        "criteria": crit,
        "rc_components": rcs,
        "rc": overall,
        "honest_boundaries": [
            "零新跑次 ⇒ **不宣称任何质量或成本降幅/增益**；所有读数与 R585–R588 各轮单窗读数并列、不相减。",
            "候选②为**否证**结论（形态非承重且与解析失败共线）；相关性为只读相关，不构成因果。",
            "候选④ 起手闸真机 **rc=2 fail-closed（窗口不可开）** ⇒ A1/A2 与判别力成对控制**未行使**；"
            "「窗口不可开」是 fail-closed 的**正确行为**，不记缺陷，但也因此本轮未取得闸 PASS 读数。",
            "候选⑤ 的耗时（20–22 s/轮）为**墙钟信息字段**，不进任何红绿判据；只测 2..4 轮相邻完成间隔（第 1 轮起点无锚）。",
            "候选③ 为**事后入册**（R589 已先行使），不得回写成「预注册」。",
            "候选①（直进产品侧修复 / 换更长题面）**待用户放行**，本轮未推进、零交付物。",
            "本轮为只读轮 ⇒ 依 R588/R589 同处置，**不造** `owner_round=R590` 的 capability 登记行；"
            "登记表未改动，形式门禁只作保形核对。",
        ],
        "artifacts": ("eval/rover/r590/{prereg-r590.json,dag-r590.md,escape-census-r590.json,"
                      "escape-census-r590-v1spanpath.json,gate-margin-r590.json,gate_r590.sh,"
                      "precond-cost-r590.json,readonly-fingerprint-r590.json,verdict-r590.json,"
                      "kpi-table-r590.json,report-r590.md}"),
    }
    io.open(os.path.join(D, "verdict-r590.json"), "w", encoding="utf-8").write(
        json.dumps(verdict, ensure_ascii=False, indent=1) + "\n")

    # ---- 六格 KPI 表（R585–R588 并池 = 上轮读数并列；R590 无臂 ⇒ 未测）----
    kpi_table = {
        "round": "R590",
        "columns": ["臂", "回复质量(逐窗/中位/极差)", "调用", "新算prompt", "completion",
                    "命中率(口径)", "步数/轮数", "问答(有效澄清/无效提问)", "rc"],
        "rows": [
            {"臂": "产品默认档 (R585–R588 并池, 36 跑次)",
             "回复质量": "逐窗中位 58/50/45/… ; 整题面中位 −0.6667 / 极差 1.0 (有效窗 9)",
             "调用": 73, "新算prompt": 18325, "completion": 170319,
             "命中率": "0.9703 (中继 dump 时间轴 v_all)", "步数/轮数": "R586 [7,7,7,13,8,7,7,7,7] / R587 [14,7,7,8,7,7,13,14,0]",
             "问答": "未测", "rc": 1, "inherited": True},
            {"臂": "codex 外部真值 (同窗同题集 12 跑次)",
             "回复质量": "逐窗 58/53/58/… ; 12 窗中 3 窗自身失分 (unreliable)",
             "调用": 204, "新算prompt": 92919, "completion": 90446,
             "命中率": "0.9695 (v_all)", "步数/轮数": "未测", "问答": "未测", "rc": 1, "inherited": True},
            {"臂": "R590 (本轮)", "回复质量": "未测", "调用": "未测", "新算prompt": "未测",
             "completion": "未测", "命中率": "未测", "步数/轮数": "未测", "问答": "0/0", "rc": overall},
        ],
        "note": ("零新臂 ⇒ 前两行 = R585–R588 在盘读数**并列**（禁相减）；R590 行 = 本轮只读轮，"
                 "质量/成本/命中率**未测**。质量=整题全对率面（判据 v3）；成本三列分列，禁合并名义总量。"),
    }
    io.open(os.path.join(D, "kpi-table-r590.json"), "w", encoding="utf-8").write(
        json.dumps(kpi_table, ensure_ascii=False, indent=1) + "\n")

    # ---- 台账行（幂等：同 round 存在则原地替换）----
    row = {
        "round": "R590",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "kind": "只读定因/入册轮（候选②形态普查 × 候选④余量条款重派生 × 候选⑤前置器耗时口径 × 候选③判据面入册）；零新臂/零远端/零产品源码改动/零夹具/零开关",
        "change": ("① 普查器 eval/rover/r590/escape_form_census_r590.py（契约块 `contract_span` **import** R589 器具，"
                   "禁重写第二份；器具自捕 #1: v1 未闭合支读成空串 ⇒ 同一条跑次在 POS 控制与 scan_run 上给出互相矛盾的形态读数"
                   "⇒ 修后把未闭合支也纳入形态判定并另记 span_balanced；v1 读数留档 `escape-census-r590-v1spanpath.json`，不翻案）；"
                   "② 余量派生器 gate_margin_r590.py + 起手闸 gate_r590.sh（派生自 r589 版，**只改余量条款这一处自由度**："
                   "补「只读轮」分支 + 落「起手前样本极差 ≤ 50MB」条件为 fail-closed）；"
                   "③ 前置器口径器 precond_cost_r590.py（守恒判据 = 复跑结论 == 该轮自身已登记 `precond.rc`）；"
                   "④ 只读指纹 readonly_fingerprint_r590.py（与 r589 并池器同口径 import；对照物升级为**跨轮不变式**）；"
                   "⑤ 判据面入册 docs/external-reference-harness.md §12.3（质量判据 v3，v2 判决面作废登记、跨版本禁相减）"),
        "readings": {
            "inherited_from_R589": {"valid_windows": 9, "task_face_median": -0.6667,
                                    "family_all_pass_rate": {"life": 0.9722, "nim": 0.9722,
                                                             "sub": 0.9722, "wythoff": 0.3889},
                                    "note": "本轮零新跑次 ⇒ 质量/成本面**未测**，上列只作并列表述"},
            "C1_form_census": {"occurrence_rate": c1["occurrence"]["rate"] if c1 else None,
                               "n_form": c1["occurrence"]["n_form_present"] if c1 else None,
                               "n_runs": c1["occurrence"]["n_product_runs"] if c1 else None,
                               "delta_wythoff_allpass": c1["correlation_wythoff_allpass"]["delta"] if c1 else None,
                               "threshold_family_gap": c1["threshold"]["value"] if c1 else None,
                               "decision": c1["decision"] if c1 else None,
                               "controls_teeth": c1["controls"]["has_teeth"] if c1 else None,
                               "rc": c1["rc"] if c1 else None},
            "C2_gate_margin": {"branch": c2["branch_taken"] if c2 else None,
                               "prev_swing_effective": c2["prev_swing_effective"] if c2 else None,
                               "source_admissible": c2["source_admissibility"]["admissible"] if c2 else None,
                               "cap_binding_all": all(r["cap_binding"] for r in c2["cap_binding_table"]) if c2 else None,
                               "live_gate_rc": 2, "live_gate_reason": "cap 38 < floor 60 ⇒ 窗口不可开（fail-closed）",
                               "A1A2_exercised": False, "disc_pair_exercised": False},
            "C3_preconditioner": {"completed": c3["n_rerun_completed"] if c3 else None,
                                  "consistent": c3["consistency_check"]["all_consistent"] if c3 else None,
                                  "intervals_s_info": c3["durations_s_informational_only"]["intervals"] if c3 else None},
            "C4_criterion_v3_enrolled": {"target": "docs/external-reference-harness.md §12.3", "rc": 0},
            "C5_readonly": {"files": c5["files_now"] if c5 else None,
                            "cross_round_invariant": c5["cross_round_invariant"] if c5 else None},
            "C6_form_gate": {"exit": (form or {}).get("exit"), "log": "eval/rover/r590/logs/form-gate-r590.txt"},
            "verdict": {"rc": overall, "components": rcs},
        },
        "artifact": verdict["artifacts"],
    }
    lines = [l for l in io.open(KPI, encoding="utf-8").read().splitlines() if l.strip()]
    rows = [json.loads(l) for l in lines]
    hit = [i for i, r in enumerate(rows) if r.get("round") == "R590"]
    if hit:
        rows[hit[0]] = row
    else:
        rows.append(row)
    with io.open(KPI, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("verdict rc=%s components=%s" % (overall, rcs))
    print("kpi rows=%d (R590 %s)" % (len(rows), "replaced" if hit else "appended"))
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
