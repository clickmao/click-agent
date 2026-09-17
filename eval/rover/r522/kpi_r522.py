#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R522 KPI 表: 按 (调用数, 新算 prompt, completion) 分列 —— R521 口径修正的落地判据。

禁用口径: `total_tokens` 名义量 (把近免费 cached 当全额, 且被每步重发放大)。
本表口径: new_prompt = prompt_tokens - cached_tokens; hit% = cached/prompt; 主判据 = calls。
输入: freeze 产出的 report.json(rows) + prereg 阈值; 输出: kpi-r522.json + 机检结论。
"""
from __future__ import annotations
import argparse, io, json, os, sys

REPO = "/home/agentuser/AgentFramework"


def load_rows(p):
    return (json.load(io.open(p, encoding="utf-8")) or {}).get("rows") or []


def agg(rows, run):
    rs = [r for r in rows if r.get("run") == run]
    calls = sum(int(r.get("calls") or 0) for r in rs)
    pt = sum(int(r.get("prompt_tokens") or 0) for r in rs)
    ct = sum(int(r.get("cached_tokens") or 0) for r in rs)
    comp = sum(int(r.get("completion_tokens") or 0) for r in rs)
    tot = sum(int(r.get("total_tokens") or 0) for r in rs)   # 上游自称 total(口径与加总不一致 ⇒ 只留档, 不作判据)
    passed = sum(int(r.get("cases_pass") or 0) for r in rs)
    total = sum(int(r.get("cases_total") or 0) for r in rs)
    unreported = sum(int(r.get("unreported_usage") or 0) for r in rs)
    empty = sum(1 for r in rs if r.get("snapshot_empty"))
    return {"arm": run, "runs": len(rs), "cases_pass": passed, "cases_total": total, "all_pass": all(r.get("all_pass") for r in rs),
            "calls": calls, "new_prompt": pt - ct, "cached_prompt": ct, "prompt_tokens": pt,
            "hit_pct": round(100.0 * ct / pt, 1) if pt else None, "completion": comp,
            "nominal_prompt_plus_completion": pt + comp, "upstream_total_tokens": tot,
            "unreported_usage": unreported, "snapshot_empty": empty,
            "models": sorted({m for r in rs for m in (r.get("models") or [])})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--prereg", default=os.path.join(REPO, "eval/rover/r522/prereg-r522.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = load_rows(a.report)
    pr = json.load(io.open(a.prereg, encoding="utf-8"))
    A0, A1, C = agg(rows, "A0-off"), agg(rows, "A1-on"), agg(rows, "C-codex")
    pred = pr.get("predictions") or {}
    cmp = {}
    def ratio(x, base):
        return round(float(x) / base, 3) if base else None
    cmp["calls_ratio_A1_over_A0"] = ratio(A1["calls"], A0["calls"])
    cmp["new_prompt_ratio"] = ratio(A1["new_prompt"], A0["new_prompt"])
    cmp["completion_ratio"] = ratio(A1["completion"], A0["completion"])
    verdict = {
        "C2_quality_no_regression": (A1["cases_pass"] == A1["cases_total"] and A1["cases_pass"] >= A0["cases_pass"]),
        "C3_calls": (cmp["calls_ratio_A1_over_A0"] is not None and cmp["calls_ratio_A1_over_A0"] <= 1 - pred.get("calls_drop_pct_min", 30) / 100.0),
        "C4_new_prompt": (cmp["new_prompt_ratio"] is not None and cmp["new_prompt_ratio"] <= 1 - pred.get("new_prompt_drop_pct_min", 30) / 100.0),
        "C5_completion": (cmp["completion_ratio"] is not None and cmp["completion_ratio"] <= 1 - pred.get("completion_drop_pct_min", 40) / 100.0),
    }
    blob = {"round": "R522", "arms": {"A0-off": A0, "A1-on": A1, "C-codex": C}, "ratios": cmp,
            "verdict": verdict, "thresholds": pred, "criteria": pr.get("criteria")}
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
    hdr = "%-8s %-13s %6s %10s %10s %8s %10s" % ("arm", "cases", "calls", "new_prompt", "cached", "hit%", "completion")
    print(hdr); print("-" * len(hdr))
    for x in (A0, A1, C):
        print("%-8s %-13s %6d %10d %10d %8s %10d" % (x["arm"], "%s/%s" % (x["cases_pass"], x["cases_total"]),
                                                     x["calls"], x["new_prompt"], x["cached_prompt"], x["hit_pct"], x["completion"]))
    print("ratios(A1/A0):", json.dumps(cmp, ensure_ascii=False))
    print("verdict:", json.dumps(verdict, ensure_ascii=False))
    ok = all(verdict.values())
    print("KPI_ALL_PASS=%s" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
