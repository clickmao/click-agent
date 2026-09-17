#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R511 汇总器: 逐 (臂, 题) 机检判分 + 规模/预算读数表。

用法: python3 aggregate_r511.py --run-dir <D> [--json <out.json>]
读: <D>/<arm>/side-run.json + <D>/<arm>/<tid>/work (产物) + <D>/<arm>/<tid>/audit/action_loop.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade_r511  # noqa: E402

BUDGET = {"dflt": 6, "s12": 12}


def loc_of(work):
    tot = 0
    files = 0
    for p in glob.glob(os.path.join(work, "**", "*.py"), recursive=True):
        try:
            tot += sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
            files += 1
        except OSError:
            pass
    return files, tot


def steps_of(arm_dir, tid):
    ap = os.path.join(arm_dir, tid, "audit", "action_loop.jsonl")
    rows = []
    if os.path.exists(ap):
        for ln in open(ap, encoding="utf-8"):
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    steps = max([int(r.get("step") or 0) for r in rows] or [0])
    tools = [r.get("tool") for r in rows if r.get("tool")]
    return steps, tools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--json")
    args = ap.parse_args()
    D = args.run_dir
    out = {"run_dir": D, "arms": [], "rows": []}
    for arm_dir in sorted(glob.glob(os.path.join(D, "*"))):
        sr = os.path.join(arm_dir, "side-run.json")
        if not os.path.exists(sr):
            continue
        side = json.load(open(sr, encoding="utf-8"))
        arm = side["arm"]
        base = arm.split("-r")[0]
        armsum = {"arm": arm, "side": side["side"], "budget": BUDGET.get(base),
                  "tasks": [], "full_correct": 0, "cases_pass": 0, "cases_total": 0}
        for t in side["tasks"]:
            tid = t["tid"]
            work = os.path.join(arm_dir, tid, "work")
            g = grade_r511.grade(tid, work)
            nf, nl = loc_of(work)
            steps, tools = steps_of(arm_dir, tid)
            row = {"arm": arm, "tid": tid, "ok": bool(g["ok"]),
                   "cases_passed": g["cases_passed"], "cases_total": g["cases_total"],
                   "failed": [f["name"] for f in g["failed"]],
                   "rc": t.get("rc"), "elapsed_s": t.get("elapsed_s"),
                   "ledger_calls": t.get("ledger_calls"), "ledger_steps": steps,
                   "budget": BUDGET.get(base), "budget_exhausted": bool(BUDGET.get(base) and steps >= BUDGET[base]),
                   "files": nf, "loc": nl, "tools": tools}
            armsum["tasks"].append(row)
            armsum["cases_pass"] += row["cases_passed"]
            armsum["cases_total"] += row["cases_total"]
            armsum["full_correct"] += 1 if row["ok"] else 0
            out["rows"].append(row)
        out["arms"].append(armsum)
        print("[%s] 整题全对 %d/%d · 用例 %d/%d" % (arm, armsum["full_correct"], len(armsum["tasks"]),
                                                  armsum["cases_pass"], armsum["cases_total"]))
        for r in armsum["tasks"]:
            print("   %-3s ok=%-5s 用例 %2d/%2d 步 %s/%s(e=%s) 调用 %s %ss 文件 %d 行 %d %s"
                  % (r["tid"], r["ok"], r["cases_passed"], r["cases_total"], r["ledger_steps"], r["budget"],
                     r["budget_exhausted"], r["ledger_calls"], r["elapsed_s"], r["files"], r["loc"],
                     ("FAIL=" + ",".join(r["failed"])) if r["failed"] else ""))
    if args.json:
        json.dump(out, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
