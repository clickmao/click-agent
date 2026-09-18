#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R569 收口件 (只读重算, 不产生新臂读数):
  ① windows-r569.json  —— 逐窗三臂读数 (由**仓内冻结件**重算: evidence/windows/*/report.json + kpi-table)
  ② verdict-r569.json   —— 判决组装 (adjudication + 铁律11 + 指纹 + 起手闸), rc 取最高严重度
  ③ summary-r569.json   —— 轮摘要 (与 R567 summary 同形: arms/verdict/precond/fingerprint)

⚠ 本轮自捕器具**使用**缺陷 (非产品): matrix_r569.py 的 --work 会被 `shutil.rmtree` 清空 (默认 /tmp/r569/pc
   是 scratch), 本轮误传 --work /tmp/r569 ⇒ 清掉运行根日志面 (logs/ adapter/ agent-cfg/ gate-*.json)。
   结论面**不依赖**被清件: 全部读数已在 06:08 之前由 ingest/kpi 落入仓内 (kpi-table/fingerprint/
   adjudication/precondition-r569.json) 或由冻结快照重算 (matrix)。本件即重算凭据。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import statistics
import sys

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r569")
WINS = ["w137", "w138", "w139", "w140", "w141", "w142"]
ARMS = ["C1", "R569B0", "R569B3"]


def med(xs):
    """中位; 全为 None 时返回 None (禁把『未上报』当 0 —— 与 KPI 口径一致)。"""
    v = [x for x in xs if x is not None]
    return statistics.median(v) if v else None


def pre_rc(pre):
    """铁律 11 前置器 rc 的 fail-closed 复算 (该器具只落盘字段, 退出码未随件保存 ⇒ 由字段反算):
    可验收前置不成立 ⇒ 1; 快照根缺失/零窗 ⇒ 3 (不可判, 环境面)。"""
    if not pre.get("windows_n") or not pre.get("snapshot_root"):
        return 3
    return 0 if pre.get("acceptable_scoped") else 1


def load():
    kpi = json.load(io.open(os.path.join(PD, "kpi-table-r569.json"), encoding="utf-8"))
    fp = json.load(io.open(os.path.join(PD, "fingerprint-r569.json"), encoding="utf-8"))
    adj = json.load(io.open(os.path.join(PD, "adjudication-r569.json"), encoding="utf-8"))
    pre = json.load(io.open(os.path.join(REPO, "eval/rover/r507pre/precondition-r569.json"), encoding="utf-8"))
    return kpi, fp, adj, pre


def windows_view(kpi):
    out = {"round": "R569", "derivation": "post-hoc 由 evidence/windows/*/report.json + kpi-table-r569.json 重算 (原 /tmp 运行根日志面被误清, 见文件头)", "windows": {}}
    for w in WINS:
        rep = json.load(io.open(os.path.join(PD, "evidence/windows", w, "report.json"), encoding="utf-8"))
        row = {"arms": {}}
        for r in rep.get("rows", []):
            row["arms"][r["arm"]] = {k: r.get(k) for k in
                                     ("cases_pass", "cases_total", "rc", "stage", "exec_repairs",
                                      "public_probe_ran", "public_probe_failed", "correctness_asserted")}
        # 成本三列取 kpi-table (中继 dump 区段口径)
        for arm in ARMS:
            k = next((x for x in kpi["arms"][arm]["windows"] if x["win"] == w), None)
            if k:
                row["arms"].setdefault(arm, {}).update(
                    {"calls": k["calls"], "new_prompt": k["new_prompt"], "completion": k["completion"],
                     "v_all": k.get("v_all"), "v_incr": k.get("v_incr")})
        row["paired_delta_B3_minus_B0"] = (row["arms"]["R569B3"]["cases_pass"] - row["arms"]["R569B0"]["cases_pass"])
        out["windows"][w] = row
    return out


def build_verdict(kpi, fp, adj, pre, winv):
    truth = [winv["windows"][w]["arms"]["C1"]["cases_pass"] for w in WINS]
    b0 = [winv["windows"][w]["arms"]["R569B0"]["cases_pass"] for w in WINS]
    b3 = [winv["windows"][w]["arms"]["R569B3"]["cases_pass"] for w in WINS]
    d = [x - y for x, y in zip(b3, b0)]
    a = kpi["arms"]
    arms = {}
    for k in ARMS:
        cs = [x["cases_pass"] for x in a[k]["windows"]]
        arms[k] = {"cases_windows": cs, "median": statistics.median(cs), "range": max(cs) - min(cs),
                   "calls": a[k]["calls"], "new_prompt": a[k]["new_prompt"], "completion": a[k]["completion"],
                   "v_all_med": med([x["v_all"] for x in a[k]["windows"]]),
                   "v_incr_med": med([x["v_incr"] for x in a[k]["windows"]]),
                   "rc_windows": [x["rc"] for x in a[k]["windows"]],
                   "stages": [x["stage"] for x in a[k]["windows"]]}
    v = {"round": "R569",
         "judge": "判据 v2 (adjudicate_r569.py 零逻辑复制自 r561 装置)",
         "adjudication": {"rc": adj["rc"], "verdict": adj["verdict"], "blocked": adj["blocked"],
                          "fail_arms": adj["fail_arms"], "truth_median": adj["truth_median"],
                          "truth_range": adj["truth_range"], "truth_status": adj["truth_status"]},
         "iron11_precondition": {"rc": pre_rc(pre), "acceptable_scoped": pre.get("acceptable_scoped"),
                                 "executable_and_correct": pre.get("executable_and_correct"),
                                 "blocked_n": len(pre.get("blocked") or []),
                                 "self_report_agrees": pre.get("self_report_agrees"),
                                 "out": "eval/rover/r507pre/precondition-r569.json"},
         "fingerprint_rc": fp["rc"], "fingerprint_checks": {k: val.get("pass") for k, val in fp["checks"].items()},
         "arms": arms,
         "axis_effect_paired": {"deltas_B3_minus_B0": d, "median": statistics.median(d),
                                "range": [min(d), max(d)],
                                "same_arm_cross_window_swing": {"R569B0": max(b0) - min(b0), "R569B3": max(b3) - min(b3)}},
         "rc": max(adj["rc"], fp["rc"], int(pre.get("rc") or 0))}
    # 机检: 逐窗读数必须与 kpi-table 的逐窗 pass 数一致 (两路径交叉, 不符 ⇒ 器具缺陷 rc=2)
    errs = []
    for w in WINS:
        for k in ARMS:
            x = next((y for y in kpi["arms"][k]["windows"] if y["win"] == w), None)
            if x and x["cases_pass"] != winv["windows"][w]["arms"][k]["cases_pass"]:
                errs.append("xref_mismatch:%s:%s" % (w, k))
    v["cross_check"] = {"paths": ["evidence/windows/*/report.json", "kpi-table-r569.json"],
                        "mismatch": errs, "agree": not errs}
    if errs:
        v["rc"] = 2
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=PD)
    a = ap.parse_args()
    kpi, fp, adj, pre = load()
    winv = windows_view(kpi)
    v = build_verdict(kpi, fp, adj, pre, winv)
    summary = {"round": "R569", "windows": WINS, "arms": v["arms"],
               "verdict": {"rc": v["rc"], "judge": v["adjudication"]["verdict"],
                           "blocked": v["adjudication"]["blocked"],
                           "iron11_rc": v["iron11_precondition"]["rc"]},
               "axis_effect_paired": v["axis_effect_paired"],
               "fingerprint": {"rc": fp["rc"], **v["fingerprint_checks"]},
               "cross_check": v["cross_check"],
               "instrument_use_defect": "matrix_r569.py --work 误传运行根 ⇒ /tmp/r569 日志面被清 (结论面不依赖; 见 windows-r569.json 头)"}
    for name, obj in (("windows-r569.json", winv), ("verdict-r569.json", v), ("summary-r569.json", summary)):
        p = os.path.join(a.outdir, name)
        json.dump(obj, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("wrote", os.path.relpath(p, REPO))
    print(json.dumps({"rc": v["rc"], "adjudication": v["adjudication"]["verdict"],
                      "iron11_rc": v["iron11_precondition"]["rc"], "fingerprint_rc": fp["rc"],
                      "axis_paired": v["axis_effect_paired"],
                      "cross_check_agree": v["cross_check"]["agree"],
                      "arms_medians": {k: v["arms"][k]["median"] for k in ARMS}}, ensure_ascii=False, indent=1))
    return v["rc"]


if __name__ == "__main__":
    sys.exit(main())
