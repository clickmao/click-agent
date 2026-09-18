#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R561 读数/前提机检:
  · C4 封存裁定的**前提**逐条机检 (只读已落盘读数; 预注册写死了三条 assert 与 on_fail);
  · 9 窗 pooled 逐窗配对视图 (信息项, 与 R559/R560 并列不相减);
  · 族 × 臂 汇总 + 逐例稳定性三类计数;
  · 成本逐窗比 (新算 prompt, 分母 = 同窗真值臂) 复算 R560 report 的 31.9–53.7%。
输出: --out freeze-premise-r561.json, --readings readings-r561.jsonl
"""
from __future__ import annotations
import argparse
import io
import json
import os
import sys
from statistics import median

REPO = "/home/agentuser/AgentFramework"
ROUNDS = {
    "R559": {"wins": ["w104", "w105", "w106"], "b0": "R559B0", "b3": "R559B3",
             "reports": "eval/rover/r559/evidence/windows"},
    "R560": {"wins": ["w107", "w108", "w109", "w110", "w111", "w112"], "b0": "R560B0", "b3": "R560B3",
             "reports": "eval/rover/r560/evidence/windows"},
}


def med(xs):
    xs = [x for x in xs if x is not None]
    return median(xs) if xs else None


def rows_of(round_key, win):
    p = os.path.join(REPO, ROUNDS[round_key]["reports"], win, "report.json")
    if not os.path.isfile(p):
        return []
    return json.load(io.open(p, encoding="utf-8")).get("rows", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--readings", required=True)
    a = ap.parse_args()
    mat = json.load(io.open(a.matrix, encoding="utf-8"))
    W = mat["windows"]

    # --- C4 前提①: 剂量>0 被行使 (R560 B3 exec_repairs == 3 的窗数)
    ex3, ex_all = [], {}
    for rk, cfg in ROUNDS.items():
        for w in cfg["wins"]:
            for row in rows_of(rk, w):
                if row["arm"] == cfg["b3"]:
                    ex_all.setdefault(rk, {})[w] = row.get("exec_repairs")
                    if row.get("exec_repairs") == 3:
                        ex3.append((rk, w))
    a1 = {"assert": "R560 B3 exec_repairs==3 的窗数 == 6",
          "value": len([1 for rk, w in ex3 if rk == "R560"]), "per_window": ex_all.get("R560"),
          "ok": len([1 for rk, w in ex3 if rk == "R560"]) == 6}

    # --- C4 前提②: 质量无增益 median(B0) >= median(B3) 在两轮同时成立
    q, q_ok = {}, {}
    for rk, cfg in ROUNDS.items():
        b0 = [W[w][cfg["b0"]]["pass"] for w in cfg["wins"]]
        b3 = [W[w][cfg["b3"]]["pass"] for w in cfg["wins"]]
        q[rk] = {"B0_windows": b0, "B3_windows": b3, "B0_median": med(b0), "B3_median": med(b3)}
        q_ok[rk] = med(b0) >= med(b3)
    a2 = {"assert": "median(B0) >= median(B3) 在 R559 与 R560 同时成立", "per_round": q,
          "ok": all(q_ok.values()), "on_fail": "预注册写死: 前提不成立 ⇒ 判 rc=1 且**不得封存**(回退为『待再测/不可验收』)"}

    # --- C4 前提③: 成本劣化 (B3 逐窗新算比 > 30% 的窗数, 分母 = 同窗真值臂)
    cost, cw = {}, {}
    for rk, cfg in ROUNDS.items():
        per = {}
        for w in cfg["wins"]:
            rows = {r["arm"]: r for r in rows_of(rk, w)}
            t, b3 = rows.get("C1", {}).get("new_prompt"), rows.get(cfg["b3"], {}).get("new_prompt")
            if t and b3 is not None:
                per[w] = round(100.0 * b3 / t, 1)
        cost[rk] = per
        cw[rk] = sum(1 for v in per.values() if v > 30)
    a3 = {"assert": "B3 逐窗新算比 > 30% 的窗数 >= 1", "per_window_pct": cost,
          "n_over30": cw, "ok": cw.get("R560", 0) >= 1,
          "note": "口径 = B3 新算 prompt / 同窗 codex 真值臂 新算 prompt (与 R560 report 同尺)"}

    # --- pooled 9 窗逐窗配对 (信息项) —— VOID 窗按本轮两轮既有惯例排除并单列
    rk_of = {}
    for rk, cfg in ROUNDS.items():
        for w in cfg["wins"]:
            rk_of[w] = (rk, cfg)
    void, deltas = {}, {}
    for w in sorted(W.keys()):
        rk, cfg = rk_of[w]
        t = W[w]["C1"]["pass"]
        for arm in (cfg["b0"], cfg["b3"]):
            row = next((r for r in rows_of(rk, w) if r["arm"] == arm), {})
            if row.get("stage") == "contract" or row.get("cases_pass") == 0:
                void["%s/%s/%s" % (rk, w, arm)] = "arm_void(rc=%s stage=%s cases=%s)" % (
                    row.get("rc"), row.get("stage"), row.get("cases_pass"))
                continue
            deltas.setdefault(arm, {})[w] = W[w][arm]["pass"] - t
    pooled = {arm: {"windows": d, "n": len(d), "median": med(list(d.values())), "min": min(d.values()),
                    "max": max(d.values()), "excluded_void": sorted([k for k in void if k.split("/")[2] == arm])}
              for arm, d in deltas.items()}
    pooled["_void"] = void

    # --- 族汇总 + 逐例稳定性
    fam, stab = {}, {}
    for rk, cfg in ROUNDS.items():
        for arm in (cfg["b0"], cfg["b3"]):
            per_case = {}
            for w in cfg["wins"]:
                for r in W[w][arm].get("rows") or []:
                    per_case.setdefault(r["family"], {}).setdefault(r["idx"], []).append(1 if r["ok"] else 0)
            agg = {}
            for f, d in per_case.items():
                pts = sum(sum(v) for v in d.values())
                tot = sum(len(v) for v in d.values())
                agg[f] = {"pass": pts, "total": tot, "always_fail": sum(1 for v in d.values() if sum(v) == 0),
                          "always_pass": sum(1 for v in d.values() if sum(v) == len(v)),
                          "wobble": sum(1 for v in d.values() if 0 < sum(v) < len(v))}
            fam[arm] = agg
            stab[arm] = {"n_cases": len(per_case.get("nim", {})) + len(per_case.get("wythoff", {})) + len(per_case.get("life", {})) + len(per_case.get("sub", {})),
                         "always_fail_by_family": {f: agg[f]["always_fail"] for f in agg},
                         "wobble_by_family": {f: agg[f]["wobble"] for f in agg}}

    out = {"round": "R561", "instrument": "readings_r561.py",
           "C4_axis_freeze_premise": [a1, a2, a3], "C4_premise_ok": bool(a1["ok"] and a2["ok"] and a3["ok"]),
           "pooled_9w_paired": pooled, "family_summary": fam, "per_case_stability": stab,
           "note": "本轮零新臂读数: 以上全部来自 R559/R560 冻结落盘 (离线只读), 与两轮并列不相减。"}
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(out, io.open(a.readings, "a", encoding="utf-8"), ensure_ascii=False)
    print(json.dumps({"C4": [a1["ok"], a2["ok"], a3["ok"]], "q_medians": {rk: (q[rk]["B0_median"], q[rk]["B3_median"]) for rk in q},
                      "B3_cost_pct": cost,
                      "pooled_median": {k: v.get("median") for k, v in pooled.items() if k != "_void"}}, ensure_ascii=False))
    print("PRIMARY_NEXT_STEP: " + ("premise_all_true" if out["C4_premise_ok"] else "premise_false=>不可封存为已证无增益"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
