#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 跨窗聚合器 (逐窗 + 极差)。

把 evidence/windows/<win>/report.json 聚成「每臂每窗 calls / 新算 prompt / completion / 命中率 / 质量」
再加轴比值 (合批 vs 纪律开 / 合批 vs 关 / 纪律开 vs 关)。

纪律 (R523 立, R531 续): 单窗读数 = 噪声 (同臂跨三同输入窗调用摆动 4.25×) ⇒ reps>=3 且必须报逐窗 + 极差;
本器**不做**任何跨轮相减, 只做同一轮内的窗间对比; 窗数 < 3 ⇒ verdict 标 provisional。

用法: python3 eval/rover/r531/aggregate_r531.py [--json <out>]
rc: 0 = 有 >=1 窗可聚合 (窗数 <3 时仍 rc=0 但 verdict=provisional); 3 = 无窗 (fail-closed)
"""
import argparse
import glob
import json
import os

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r531")


def load_windows():
    out = {}
    for p in sorted(glob.glob(os.path.join(R, "evidence/windows/*/report.json"))):
        win = os.path.basename(os.path.dirname(p))
        out[win] = json.load(open(p, encoding="utf-8"))
    return out


def arm_agg(rows, arm):
    rs = [r for r in rows if r.get("arm") == arm]
    if not rs:
        return None
    calls = sum(r.get("calls", 0) for r in rs)
    pt = sum(r.get("prompt_tokens", 0) for r in rs)
    ct = sum(r.get("cached_tokens", 0) for r in rs)
    comp = sum(r.get("completion_tokens", 0) for r in rs)
    pas = sum(r.get("cases_pass", 0) for r in rs)
    tot = sum(r.get("cases_total", 0) for r in rs)
    return {"tasks": len(rs), "calls": calls, "prompt_tokens": pt, "cached_tokens": ct,
            "new_prompt": pt - ct, "completion_tokens": comp, "total_tokens": pt + comp,
            "hit_rate": round(ct / pt, 4) if pt else None,
            "cases_pass": pas, "cases_total": tot}


def ratio(a, b, key):
    if not a or not b or not b[key]:
        return None
    return round(a[key] / b[key], 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(R, "evidence/kpi-r531-windows.json"))
    a = ap.parse_args()

    wins = load_windows()
    if not wins:
        print("AGG_RC=3 (无窗: evidence/windows/*/report.json 皆缺)")
        return 3

    arms = ["A0-off", "A1-on", "A2-merge", "C-codex"]
    per_win = {}
    for win, rep in wins.items():
        rows = rep.get("rows", [])
        agg = {}
        for arm in arms:
            g = arm_agg(rows, arm)
            if g:
                agg[arm] = g
        per_win[win] = agg

    summary = {}
    for win, agg in per_win.items():
        summary[win] = {
            "rows": {arm: agg[arm] for arm in agg},
            "ratios": {
                "merge_vs_on_calls": ratio(agg.get("A2-merge"), agg.get("A1-on"), "calls"),
                "merge_vs_off_calls": ratio(agg.get("A2-merge"), agg.get("A0-off"), "calls"),
                "on_vs_off_calls": ratio(agg.get("A1-on"), agg.get("A0-off"), "calls"),
                "merge_vs_on_newprompt": ratio(agg.get("A2-merge"), agg.get("A1-on"), "new_prompt"),
                "merge_vs_off_newprompt": ratio(agg.get("A2-merge"), agg.get("A0-off"), "new_prompt"),
            },
        }

    print("窗数 = %d %s" % (len(wins), "·".join(sorted(wins))))
    hdr = "%-9s %-9s %6s %10s %10s %8s %7s %9s" % (
        "win", "arm", "calls", "new_prompt", "completion", "hit", "case", "total_tok")
    print(hdr)
    for win in sorted(per_win):
        for arm in arms:
            g = per_win[win].get(arm)
            if not g:
                continue
            print("%-9s %-9s %6d %10d %10d %8s %4d/%-4d %9d" % (
                win, arm, g["calls"], g["new_prompt"], g["completion_tokens"],
                g["hit_rate"], g["cases_pass"], g["cases_total"], g["total_tokens"]))
    print("轴比值 (calls):")
    for win in sorted(per_win):
        r = summary[win]["ratios"]
        print("  %-4s merge/on=%s merge/off=%s on/off=%s newprompt(merge/on)=%s newprompt(merge/off)=%s" % (
            win, r["merge_vs_on_calls"], r["merge_vs_off_calls"], r["on_vs_off_calls"],
            r["merge_vs_on_newprompt"], r["merge_vs_off_newprompt"]))

    eff = {}
    for key in ("merge_vs_on_calls", "merge_vs_off_calls", "on_vs_off_calls"):
        vals = [summary[w]["ratios"][key] for w in summary if summary[w]["ratios"][key] is not None]
        if vals:
            eff[key] = {"n": len(vals), "min": min(vals), "max": max(vals),
                        "median": sorted(vals)[len(vals) // 2], "values": vals}
    print("跨窗极差 (%s):" % ("reps>=3 ⇒ 可作结论" if len(wins) >= 3 else "窗数<3 ⇒ provisional"))
    for k, v in eff.items():
        print("  %-22s n=%d min=%s max=%s median=%s" % (k, v["n"], v["min"], v["max"], v["median"]))

    verdict = "provisional(窗数 %d < 3)" % len(wins) if len(wins) < 3 else "reps>=3"
    out = {"round": "R531", "instrument": "eval/rover/r531/aggregate_r531.py",
           "windows": sorted(wins), "window_count": len(wins), "verdict": verdict,
           "per_window": summary, "spread": eff,
           "note": "只做窗间对比, 禁跨轮相减; 单窗=噪声(R523)"}
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
    print("AGG_RC=0 verdict=%s out=%s" % (verdict, os.path.relpath(a.json, REPO)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
