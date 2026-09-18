#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R565 汇总: 从逐窗 readings.json 归并三臂 KPI (口径同 ingest: 中继 dump 索引区段)。
只读**已落盘**件, 幂等。中位/极差按窗 (n=6) 给出; 不出率值。"""
import argparse, io, json, os, statistics

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    wins = sorted([d for d in os.listdir(a.D) if d.startswith("w") and os.path.isdir(os.path.join(a.D, d))])
    per = {}
    led = []
    for w in wins:
        p = os.path.join(a.D, w, "readings.json")
        if not os.path.isfile(p):
            continue
        rec = json.load(io.open(p, encoding="utf-8"))
        for arm, e in rec["arms"].items():
            d = per.setdefault(arm, {"windows": [], "calls": 0, "new_prompt": 0, "prompt": 0, "hit": 0,
                                     "completion": 0, "cases_total": 0})
            d["windows"].append({"win": w, "calls": e["calls"], "new_prompt": e["new_prompt"],
                                 "completion": e["completion"], "v_all": e["v_all"], "v_incr": e["v_incr"],
                                 "cases_pass": e["cases_pass"], "cases_total": e["cases_total"],
                                 "rc": e["self_transcript"].get("rc") if e["self_transcript"] else None,
                                 "stage": e["self_transcript"].get("stage") if e["self_transcript"] else None,
                                 "max_exec_repair": e["self_transcript"].get("max_exec_repair") if e["self_transcript"] else None,
                                 "exec_repairs": e["self_transcript"].get("exec_repairs") if e["self_transcript"] else None,
                                 "public_probe_ran": e["self_transcript"].get("public_probe_ran") if e["self_transcript"] else None,
                                 "public_probe_failed": e["self_transcript"].get("public_probe_failed") if e["self_transcript"] else None})
            if e["calls"]:
                for k in ("calls", "new_prompt", "prompt", "hit", "completion"):
                    d[k] += e[k] or 0
        for k, v in (rec.get("ledger_check") or {}).items():
            led.append({"win": w, "arm": k, **v})
    for arm, d in per.items():
        wl = [x for x in d["windows"] if x["cases_total"]]
        cp = [x["cases_pass"] for x in wl]
        d["median_cases"] = statistics.median(cp) if cp else None
        d["range_cases"] = (max(cp) - min(cp)) if cp else None
        d["max_exec_repair_observed"] = sorted({x["max_exec_repair"] for x in wl if x["max_exec_repair"] is not None})
        d["exec_repairs_max"] = max([x["exec_repairs"] or 0 for x in wl], default=None)
    tab = {"round": "R565", "windows": wins, "arms": per, "ledger_check": led,
           "ledger_diff_nonzero": [x for x in led if (x.get("diff") or 0) != 0],
           "rule": "调用/新算 prompt/命中率 取中继 dump 索引区段; 命中率双口径 v_all(含冷启动)/v_incr(去冷启动); 中位/极差按窗 (n=6) 不出率值"}
    json.dump(tab, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for arm in ("C1", "R565B0"):
        d = per.get(arm)
        if not d:
            continue
        print("  [KPI %s] calls=%d new=%d completion=%d med=%s rng=%s max_exec_repair=%s exec_max=%s" % (
            arm, d["calls"], d["new_prompt"], d["completion"], d["median_cases"], d["range_cases"],
            d["max_exec_repair_observed"], d["exec_repairs_max"]))
    print("  [KPI] ledger 非零差额 %d 条" % len(tab["ledger_diff_nonzero"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
