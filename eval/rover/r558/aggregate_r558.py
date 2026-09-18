#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R558 聚合器: 逐窗 + 中位/极差 + 同窗 codex 对照 + 剂量行使面 + 账核对。

输入: <D>/readings-r558.jsonl (ingest_r558.py 逐窗产出) + 各臂 transcript.json。
口径 (R550sc/R557 令): 调用数/新算 prompt/completion 取 **中继 dump 索引区段**; 命中率双口径
  v_all = Σhit/Σprompt (含冷启动) · v_incr = 去第 1 次调用后 Σhit/Σprompt。
分窗 = 逐窗读数并列; 跨轮禁相减 (本器具只读本轮 D)。
"""
from __future__ import annotations
import argparse, glob, io, json, os, statistics as st, sys

ARMS = ("C1", "R558B0", "R558B1", "R558B2")
TR = ("exec_repairs", "public_probe_ran", "public_probe_failed", "public_probe_reason",
      "rc", "stage", "calls", "self_test_unmet", "correctness_asserted", "prefix_chars",
      "max_exec_repair", "reason")


def med(xs):
    return round(st.median(xs), 1) if xs else None


def rng(xs):
    return (max(xs) - min(xs)) if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", default="/tmp/r558")
    ap.add_argument("--pd", default=None)
    a = ap.parse_args()
    pd = a.pd or os.path.join(os.path.dirname(os.path.abspath(__file__)))
    wins = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(a.D, "w*", "readings.json")))
    wins = sorted(wins, key=lambda s: int(s[1:]))
    per = {k: [] for k in ARMS}
    dose, ledger, rows = [], [], []
    for w in wins:
        rec = json.load(io.open(os.path.join(a.D, w, "readings.json"), encoding="utf-8"))
        for arm in ARMS:
            v = rec["arms"].get(arm) or {}
            if not v.get("calls"):
                continue
            t = v.get("self_transcript") or {}
            row = {"win": w, "arm": arm, "cases_pass": v["cases_pass"], "cases_total": v["cases_total"],
                   "all_pass": v["all_pass"], "calls": v["calls"], "new_prompt": v["new_prompt"],
                   "prompt": v["prompt"], "completion": v["completion"], "v_all": v["v_all"],
                   "v_incr": v["v_incr"], "stage": t.get("stage"), "rc": t.get("rc"),
                   "exec_repairs": t.get("exec_repairs"), "probe_failed": t.get("public_probe_failed"),
                   "probe_ran": t.get("public_probe_ran"), "max_exec_repair": t.get("max_exec_repair"),
                   "failed_cases": v.get("failed_cases")}
            rows.append(row)
            per[arm].append(row)
            if arm.startswith("R558"):
                dose.append({"win": w, "arm": arm, "max_exec_repair": t.get("max_exec_repair"),
                             "exec_repairs": t.get("exec_repairs"), "cases_pass": v["cases_pass"],
                             "probe_failed": t.get("public_probe_failed"), "stage": t.get("stage")})
                d = (rec.get("ledger_check") or {}).get(arm) or {}
                ledger.append({"win": w, "arm": arm, **d})
    valid = {k: [r for r in v if r["cases_total"] == 58] for k, v in per.items()}
    summary = {}
    for k in ARMS:
        rs = per[k]
        vl = valid[k]
        q = [r["cases_pass"] for r in vl]
        summary[k] = {
            "windows": [r["win"] for r in rs],
            "cases_pass_by_window": {r["win"]: r["cases_pass"] for r in rs},
            "quality_median": med(q), "quality_range": rng(q), "all58": sum(1 for x in q if x == 58),
            "n_windows": len(rs), "n_valid": len(vl),
            "calls_total": sum(r["calls"] for r in rs),
            "calls_by_window": {r["win"]: r["calls"] for r in rs},
            "new_prompt_total": sum(r["new_prompt"] for r in rs),
            "new_prompt_by_window": {r["win"]: r["new_prompt"] for r in rs},
            "completion_total": sum(r["completion"] for r in rs),
            "prompt_total": sum(r["prompt"] for r in rs),
            "hit_total": None, "v_all": None, "v_incr": None,
        }
    # 命中率双口径: 由 per-call turns 重算 (读 readings.json 的 turns)
    turns = {k: [] for k in ARMS}
    for w in wins:
        rec = json.load(io.open(os.path.join(a.D, w, "readings.json"), encoding="utf-8"))
        for arm in ARMS:
            v = rec["arms"].get(arm) or {}
            if v.get("calls"):
                turns[arm] += v.get("turns") or []
    for k in ARMS:
        t = turns[k]
        tp = sum(x["prompt"] for x in t)
        summary[k]["hit_total"] = sum(x["hit"] for x in t)
        summary[k]["v_all"] = round(summary[k]["hit_total"] / tp, 4) if tp else None
        inc = t[1:]
        ip = sum(x["prompt"] for x in inc)
        summary[k]["v_incr"] = round(sum(x["hit"] for x in inc) / ip, 4) if ip else None
        summary[k]["v_incr_note"] = "去冷启动 (仅第 2..n 次调用), n=%d" % len(inc)
    # 成本比 (逐窗, vs codex 同窗)
    cost = {}
    for arm in ("R558B0", "R558B1", "R558B2"):
        ratios_new, ratios_calls = {}, {}
        for w in wins:
            c = next((r for r in per["C1"] if r["win"] == w), None)
            b = next((r for r in per[arm] if r["win"] == w), None)
            if c and b and c["new_prompt"]:
                ratios_new[w] = round(b["new_prompt"] / c["new_prompt"], 4)
            if c and b and c["calls"]:
                ratios_calls[w] = round(b["calls"] / c["calls"], 4)
        cost[arm] = {"new_prompt_ratio_by_window": ratios_new, "calls_ratio_by_window": ratios_calls,
                     "max_new_prompt_ratio": max(ratios_new.values()) if ratios_new else None,
                     "max_calls_ratio": max(ratios_calls.values()) if ratios_calls else None}
    # 剂量行使
    dose_ex = {}
    for arm in ("R558B0", "R558B1", "R558B2"):
        dl = [d for d in dose if d["arm"] == arm]
        dose_ex[arm] = {
            "max_exec_repair_seen": sorted({d["max_exec_repair"] for d in dl}),
            "windows_exercised": [d["win"] for d in dl if (d["exec_repairs"] or 0) > 0],
            "windows_at_budget": [d["win"] for d in dl if d["max_exec_repair"] and (d["exec_repairs"] or 0) >= d["max_exec_repair"]],
            "windows_dose2": [d["win"] for d in dl if (d["exec_repairs"] or 0) >= 2],
            "probe_failed_windows": {d["win"]: d["probe_failed"] for d in dl if (d["probe_failed"] or 0) > 0},
            "by_window": dl,
        }
    out = {"round": "R558", "windows": wins, "arms": summary, "cost_vs_codex_samewindow": cost,
           "dose_exercise": dose_ex, "ledger_check": ledger, "rows": rows,
           "rule": "调用/新算 prompt/completion = 中继 dump 索引区段; 命中率双口径 v_all/v_incr; 逐窗并列, 跨轮禁相减",
           "caveat": "铁律 11 前置器 rc≠0 ⇒ 成本降幅「参考(未可验收)」"}
    json.dump(out, io.open(os.path.join(pd, "kpi-table-r558.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ev = os.path.join(pd, "evidence")
    os.makedirs(ev, exist_ok=True)
    json.dump(out, io.open(os.path.join(ev, "kpi-r558-windows.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("windows=%s" % wins)
    hdr = "%-8s %-28s %7s %7s %7s %8s %7s %7s" % ("arm", "quality(逐窗/中位/极差)", "calls", "newprompt", "complet", "hit(v_all)", "hit(incr)", "all58")
    print(hdr)
    for k in ARMS:
        s = summary[k]
        qs = "/".join(str(s["cases_pass_by_window"][w]) for w in s["windows"])
        print("%-8s %-28s %7d %7d %7d %8s %7s %7d" % (
            k, "%s med=%s rng=%s" % (qs, s["quality_median"], s["quality_range"]),
            s["calls_total"], s["new_prompt_total"], s["completion_total"],
            s["v_all"], s["v_incr"], s["all58"]))
    print("--- cost vs codex (同窗比, 逐窗) ---")
    for k, v in cost.items():
        print("  %s newprompt<=%.3f  calls<=%.3f  %s" % (k, v["max_new_prompt_ratio"] or -1,
                                                          v["max_calls_ratio"] or -1, v["calls_ratio_by_window"]))
    print("--- dose ---")
    for k, v in dose_ex.items():
        print("  %s max_seen=%s exercised=%s at_budget=%s dose2=%s" % (
            k, v["max_exec_repair_seen"], v["windows_exercised"], v["windows_at_budget"], v["windows_dose2"]))
    nz = [x for x in ledger if x.get("diff")]
    print("--- ledger diff (dump 区段 vs transcript.calls) ---")
    print("  n=%d/%d %s" % (len(nz), len(ledger), nz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
