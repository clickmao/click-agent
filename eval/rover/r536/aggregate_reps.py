#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R536 reps 读数聚合（只读跑盘，不重算判分）。

为什么需要: analyze_r536.py 的臂布局约定是 `<臂>/<题>`（w1 布局），而复跑落在 `<rep>/<臂>/`。
本脚本只做一件事: 按 logs/idx.txt 的 adapter 索引范围逐 (rep, 臂) 汇总成本，并 join 转写台账的
rc/stage/self_test_unmet 与判分 PASS 数 —— 逐窗报数，**不做任何跨窗相减**。
"""
from __future__ import annotations
import json, os, subprocess, sys

REPO = "/home/agentuser/AgentFramework"
UFD = os.path.join(REPO, "eval/rover/r511/usage_from_dumps.py")


def usage(d, i0, i1, out):
    subprocess.run([sys.executable, UFD, "--dir", d, "--side", "agent",
                    "--from", str(i0), "--to", str(i1), "--json", out],
                   check=False, capture_output=True)
    try:
        return json.load(open(out, encoding="utf-8"))
    except Exception:
        return {}


def main():
    D = sys.argv[1]
    idx = {}
    ip = os.path.join(D, "logs/idx.txt")
    for ln in open(ip, encoding="utf-8"):
        w = ln.split()
        if len(w) >= 3:
            idx[w[0]] = (int(w[1]), int(w[2]))

    rows = []
    for key, (i0, i1) in sorted(idx.items()):
        rep, arm = key.split("-", 1)
        u = usage(os.path.join(D, "adapter"), i0, i1,
                  os.path.join(D, "logs/usage-%s.json" % key))
        tr = {}
        tp = os.path.join(D, rep, arm, "transcript.json")
        if os.path.isfile(tp):
            tr = json.load(open(tp, encoding="utf-8"))
        cp = os.path.join(D, rep, arm, "cases.txt")
        npass = ntot = None
        jrc = None
        if os.path.isfile(cp):
            lines = open(cp, encoding="utf-8", errors="replace").read().splitlines()
            if lines and lines[-1].strip().isdigit():
                jrc = int(lines[-1].strip())
                lines = lines[:-1]
            npass = sum(1 for l in lines if l.startswith("CASE ") and l.strip().endswith("PASS"))
            ntot = sum(1 for l in lines if l.startswith("CASE "))
        rows.append({"rep": rep, "arm": arm, "adapter_range": [i0, i1],
                     "calls": u.get("calls"),
                     "prompt_tokens": u.get("prompt_tokens"),
                     "cached_tokens": u.get("cached_tokens"),
                     # 新算 prompt = 上游 prompt_tokens − 缓存命中（口径沿用 R535/R525）
                     "new_prompt_tokens": (None if u.get("prompt_tokens") is None else
                                           u["prompt_tokens"] - (u.get("cached_tokens") or 0)),
                     "completion_tokens": u.get("completion_tokens"),
                     "total_tokens": u.get("total_tokens"), "unreported": u.get("unreported_usage"),
                     "r1_rc": tr.get("rc"), "r1_stage": tr.get("stage"),
                     "self_test_unmet": tr.get("self_test_unmet"),
                     "plan_steps_total": tr.get("plan_steps_total"), "steps_executed": tr.get("steps_executed"),
                     "judge_rc": jrc, "cases_pass": npass, "cases_total": ntot})

    print("%-4s %-6s %-12s %-6s %-10s %-10s %-6s %-18s %-6s %s"
          % ("rep", "arm", "range", "calls", "new_prompt", "completion", "R1rc", "stage", "st_un", "cases"))
    for r in rows:
        print("%-4s %-6s %-12s %-6s %-10s %-10s %-6s %-18s %-6s %s/%s"
              % (r["rep"], r["arm"], str(r["adapter_range"]), r["calls"], r["new_prompt_tokens"],
                 r["completion_tokens"], r["r1_rc"], r["r1_stage"], r["self_test_unmet"],
                 r["cases_pass"], r["cases_total"]))

    # 逐臂跨窗极差（**只报区间, 不报单点 Δ**）
    print("\n逐臂跨窗 (reps 窗内):")
    for arm in ("R1nr", "R1r"):
        calls = [r["calls"] for r in rows if r["arm"] == arm and r["calls"]]
        q = [r["cases_pass"] for r in rows if r["arm"] == arm and r["cases_pass"] is not None]
        if calls:
            print("  %-6s calls=%s (极差 %.2f×)" % (arm, calls, (max(calls) / min(calls)) if min(calls) else -1))
        if q:
            print("  %-6s cases=%s/30" % (arm, q))

    out = os.path.join(D, "logs/aggregate-reps.json")
    json.dump({"rows": rows}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n落盘: " + out)


if __name__ == "__main__":
    main()
