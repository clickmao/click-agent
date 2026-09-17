#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 KPI 表: 按题族分列 (F1 锚 / F2 新族) + 三臂 (A0-off 基线 / A1-on 处理 / C-codex 外部真值)。

口径 (与 R521/R528 同源, 跨轮可比): new_prompt = prompt_tokens - cached_tokens; hit% = cached/prompt; 主判据 = calls。
禁用: `total_tokens` 名义量 (每步重发放大) / 跨轮相减。
本表按 (run, tid) 分组 ⇒ 同一臂内两题不混算; 比值只在**同窗同族**内取 (A1/A0), 并显式给出基线可用性。
"""
from __future__ import annotations
import argparse
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
FAM = {"g1": "F1(games-longtask-v1)", "t1": "F2(toolkit-multimodule-v1)"}


def load_rows(p):
    return (json.load(io.open(p, encoding="utf-8")) or {}).get("rows") or []


def agg(rows):
    calls = sum(int(r.get("calls") or 0) for r in rows)
    pt = sum(int(r.get("prompt_tokens") or 0) for r in rows)
    ct = sum(int(r.get("cached_tokens") or 0) for r in rows)
    comp = sum(int(r.get("completion_tokens") or 0) for r in rows)
    tot = sum(int(r.get("total_tokens") or 0) for r in rows)
    passed = sum(int(r.get("cases_pass") or 0) for r in rows)
    total = sum(int(r.get("cases_total") or 0) for r in rows)
    return {"runs": len(rows), "cases_pass": passed, "cases_total": total,
            "all_pass": bool(rows) and all(r.get("all_pass") for r in rows),
            "calls": calls, "new_prompt": pt - ct, "cached_prompt": ct, "prompt_tokens": pt,
            "hit_pct": round(100.0 * ct / pt, 1) if pt else None, "completion": comp,
            "nominal_prompt_plus_completion": pt + comp, "upstream_total_tokens": tot,
            "unreported_usage": sum(int(r.get("unreported_usage") or 0) for r in rows),
            "snapshot_empty": sum(1 for r in rows if r.get("snapshot_empty")),
            "artifacts": sum(int(r.get("artifacts") or 0) for r in rows),
            "elapsed_s": [r.get("elapsed_s") for r in rows],
            "models": sorted({m for r in rows for m in (r.get("models") or [])})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--prereg", default=os.path.join(REPO, "eval/rover/r529/prereg-r529.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = load_rows(a.report)
    pr = json.load(io.open(a.prereg, encoding="utf-8"))
    pred = pr.get("predictions") or {}
    arms = {}
    for run in ("A0-off", "A1-on", "C-codex"):
        for tid in ("g1", "t1"):
            sel = [r for r in rows if r.get("run") == run and r.get("tid") == tid]
            if sel:
                arms["%s|%s" % (run, tid)] = agg(sel)

    def ratio(x, base):
        return round(float(x) / base, 3) if base else None

    def blk(tid):
        b = arms.get("A0-off|%s" % tid)
        t = arms.get("A1-on|%s" % tid)
        c = arms.get("C-codex|%s" % tid)
        o = {"family": FAM[tid]}
        o["baseline_available"] = bool(b and not b["snapshot_empty"] and b["artifacts"] > 0)
        for k, v in (("A0-off", b), ("A1-on", t), ("C-codex", c)):
            if v:
                o[k] = {x: v[x] for x in ("cases_pass", "cases_total", "all_pass", "calls", "new_prompt",
                                          "cached_prompt", "hit_pct", "completion", "artifacts", "snapshot_empty",
                                          "unreported_usage", "elapsed_s")}
        if b and t and b["cases_total"] and t["cases_total"]:
            o["ratios_A1_over_A0"] = {
                "calls": ratio(t["calls"], b["calls"]),
                "new_prompt": ratio(t["new_prompt"], b["new_prompt"]),
                "completion": ratio(t["completion"], b["completion"]),
            }
        o["verdict"] = {
            "quality_no_regression": (t is not None and b is not None
                                      and t["cases_pass"] == t["cases_total"]
                                      and t["cases_pass"] >= b["cases_pass"]),
            "calls_drop_ge_%d" % pred.get("calls_drop_pct_min", 30):
                (o.get("ratios_A1_over_A0", {}).get("calls") is not None
                 and o["ratios_A1_over_A0"]["calls"] <= 1 - pred.get("calls_drop_pct_min", 30) / 100.0),
            "new_prompt_drop_ge_%d" % pred.get("new_prompt_drop_pct_min", 30):
                (o.get("ratios_A1_over_A0", {}).get("new_prompt") is not None
                 and o["ratios_A1_over_A0"]["new_prompt"] <= 1 - pred.get("new_prompt_drop_pct_min", 30) / 100.0),
            "completion_drop_ge_%d" % pred.get("completion_drop_pct_min", 40):
                (o.get("ratios_A1_over_A0", {}).get("completion") is not None
                 and o["ratios_A1_over_A0"]["completion"] <= 1 - pred.get("completion_drop_pct_min", 40) / 100.0),
            "external_truth_all_pass": (c is not None and c["all_pass"]),
        }
        return o

    fams = {tid: blk(tid) for tid in ("g1", "t1")}
    blob = {"round": "R529", "arms": arms, "families": fams,
            "thresholds": {k: pred.get(k) for k in ("calls_drop_pct_min", "new_prompt_drop_pct_min",
                                                    "completion_drop_pct_min")},
            "criteria": pr.get("criteria"), "prereg_sha256_note": "见 SUMMARY 内 sha256",
            "note": "主判据=calls; 名义 total_tokens 只留档; A0-off 基线为空产物的窗 ⇒ baseline_available=false, 该族降幅按「不可判」记账"}
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
    hdr = "%-8s %-9s %-10s %6s %10s %10s %8s %10s" % ("arm", "tid", "cases", "calls", "new_prompt", "cached", "hit%", "completion")
    print(hdr)
    print("-" * len(hdr))
    for k in ("A0-off|g1", "A1-on|g1", "C-codex|g1", "A0-off|t1", "A1-on|t1", "C-codex|t1"):
        v = arms.get(k)
        if not v:
            continue
        run, tid = k.split("|")
        print("%-8s %-9s %-10s %6d %10d %10d %8s %10d" % (run, tid, "%s/%s" % (v["cases_pass"], v["cases_total"]),
                                                          v["calls"], v["new_prompt"], v["cached_prompt"],
                                                          v["hit_pct"], v["completion"]))
    for tid in ("g1", "t1"):
        f = fams[tid]
        print("%s ratios(A1/A0)=%s baseline_available=%s" % (FAM[tid], json.dumps(f.get("ratios_A1_over_A0"), ensure_ascii=False),
                                                            f["baseline_available"]))
        print("   verdict=%s" % json.dumps(f["verdict"], ensure_ascii=False))
    core = all(fams["t1"]["verdict"].get(k) for k in fams["t1"]["verdict"] if k != "external_truth_all_pass")
    print("KPI_F2_CORE_PASS=%s (quality ∧ 三项降幅; external_truth_all_pass=%s)" %
          (core, fams["t1"]["verdict"].get("external_truth_all_pass")))
    print("F1_ANCHOR_QUALITY=%s/%s" % (arms.get("A1-on|g1", {}).get("cases_pass"), arms.get("A1-on|g1", {}).get("cases_total")))
    return 0 if core else 1


if __name__ == "__main__":
    sys.exit(main())
