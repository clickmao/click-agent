#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R593 — 从定因器产物复算 KPI 面（只读；不改判据、不重跑器具）。

出：逐窗配对（agent 三跑中位 − codex 同窗）+ 逐窗极差 + 同败窗的「失败用例集合逐字相同」机检
   + 整题全对率（=15/15）+ 层/桶份额对照。判决口径：跑次率（分子/分母各自侧）为**主**，份额为**辅**。
"""
import io
import json
import os
import statistics as st

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r593/landing-predicate-r593.json")
OUT = os.path.join(REPO, "eval/rover/r593/kpi-r593.json")


def failset(r):
    return sorted(x["idx"] for x in r["failures"])


def main():
    d = json.load(io.open(SRC, encoding="utf-8"))
    runs = [r for r in d["runs"] if "err" not in r]
    wins = {}
    for r in runs:
        wins.setdefault("%s/%s" % (r["round"], r["win"]), {}).setdefault(r["side"], []).append(r)
    rows, paired = [], []
    for k in sorted(wins):
        ag = sorted(wins[k].get("agent", []), key=lambda x: x["sub"])
        cx = wins[k].get("codex", [{}])[0] if wins[k].get("codex") else None
        ag_pass = [x["cases_pass_wythoff"] for x in ag]
        med = st.median(ag_pass) if ag_pass else None
        row = {"win": k, "n_agent": len(ag), "agent_pass": ag_pass,
               "agent_median": med, "agent_range": (max(ag_pass) - min(ag_pass)) if ag_pass else None,
               "codex_pass": cx["cases_pass_wythoff"] if cx else None,
               "codex_layer": cx["layer"] if cx else None,
               "agent_layer": [x["layer"] for x in ag],
               "codex_failset": failset(cx) if cx else None,
               "agent_failsets": [failset(x) for x in ag]}
        if cx and ag_pass:
            row["paired_med_minus_codex"] = med - cx["cases_pass_wythoff"]
            # 同败窗：codex (b) ∧ ≥2/3 我方跑次 (b)
            nb = sum(1 for x in ag if x["layer"].startswith("(b)"))
            row["co_fail_coldset"] = bool(cx["layer"].startswith("(b)") and nb >= 2)
            if row["co_fail_coldset"]:
                row["failset_identical"] = any(fs == failset(cx) for fs in row["agent_failsets"])
                row["co_fail_n_agent_b"] = nb
            paired.append(row)
        rows.append(row)
    ag_all = [r for r in runs if r["side"] == "agent"]
    cx_all = [r for r in runs if r["side"] == "codex"]
    ap = [r["cases_pass_wythoff"] for r in ag_all]
    cp = [r["cases_pass_wythoff"] for r in cx_all]
    out = {
        "round": "R593", "source": SRC,
        "agent": {"runs": len(ag_all), "n_cases": ag_all[0]["cases_n"], "pass_each": ap,
                  "median": st.median(ap), "min": min(ap), "max": max(ap),
                  "all_correct_runs": sum(1 for v in ap if v == ag_all[0]["cases_n"]),
                  "all_correct_rate": round(sum(1 for v in ap if v == ag_all[0]["cases_n"]) / len(ap), 4),
                  "coldset_layer_run_rate": round(sum(1 for r in ag_all if r["layer"].startswith("(b)")) / len(ag_all), 4),
                  "d_share": round(sum(r["d_total"] for r in ag_all) / sum(r["fail_total"] for r in ag_all), 4)},
        "codex": {"runs": len(cx_all), "n_cases": cx_all[0]["cases_n"], "pass_each": cp,
                  "median": st.median(cp), "min": min(cp), "max": max(cp),
                  "all_correct_runs": sum(1 for v in cp if v == cx_all[0]["cases_n"]),
                  "all_correct_rate": round(sum(1 for v in cp if v == cx_all[0]["cases_n"]) / len(cp), 4),
                  "coldset_layer_run_rate": round(sum(1 for r in cx_all if r["layer"].startswith("(b)")) / len(cx_all), 4),
                  "d_share": round(sum(r["d_total"] for r in cx_all) / sum(r["fail_total"] for r in cx_all), 4)},
        "windows": rows, "paired": [r["paired_med_minus_codex"] for r in paired],
        "paired_median": st.median([r["paired_med_minus_codex"] for r in paired]) if paired else None,
        "paired_range": ((max([r["paired_med_minus_codex"] for r in paired])
                          - min([r["paired_med_minus_codex"] for r in paired])) if paired else None),
        "co_fail_coldset_windows": [r["win"] for r in paired if r.get("co_fail_coldset")],
        "co_fail_failset_identical": {r["win"]: r.get("failset_identical") for r in paired if r.get("co_fail_coldset")},
        "agent_only_coldset_windows": [r["win"] for r in paired
                                       if not r.get("co_fail_coldset") and any(l.startswith("(b)") for l in r["agent_layer"])],
        "codex_only_coldset_windows": [r["win"] for r in paired if r["codex_layer"].startswith("(b)")
                                       and not any(l.startswith("(b)") for l in r["agent_layer"])],
        "d1_reason": d["agent"]["d1_reason"], "d_subs": d["agent"]["d_subs"], "codex_d_subs": d["codex"]["d_subs"],
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "windows"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
