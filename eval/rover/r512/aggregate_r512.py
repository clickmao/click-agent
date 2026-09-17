#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R512 汇总器: 逐 (臂, 题) 机械判分 + 用量分列 (调用数 / tokens, 取自 adapter 落盘真值)。

用法: python3 aggregate_r512.py --run-dir <D> [--json <out.json>]
读: <D>/<arm>/side-run.json + <D>/<arm>/<tid>/work (产物) + <D>/adapter (adapter 落盘)
判分: 调 grade_r511.grade (在**新进程**里 python3 -I -B 跑隐藏用例, 逐条机械判对)。
口径: tokens 一律取上游 usage (unreported 单列, 禁冒充 0); 跨轮禁相减。
"""
from __future__ import annotations

import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "r511"))
import grade_r511  # noqa: E402
import usage_from_dumps as ufd  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    D = a.run_dir
    adapter = os.path.join(D, "adapter")
    out = {"run_dir": D, "adapter_dir": adapter, "rows": [], "arms": []}
    for arm_dir in sorted(os.listdir(D)):
        sr = os.path.join(D, arm_dir, "side-run.json")
        if not os.path.isfile(sr):
            continue
        side = json.load(open(sr, encoding="utf-8"))
        s = side["side"]
        arm = {"agent": "A", "codex": "C"}.get(s, s)  # 窗口件标签: agentA→A / codex 唯一标签 C
        run = side["arm"]
        rows = []
        for t in side["tasks"]:
            tid = t["tid"]
            work = os.path.join(D, arm_dir, tid, "work")
            g = grade_r511.grade(tid, work)
            i0, i1 = (t.get("adapter_range") or [1, 0])
            u = ufd.collect(adapter, s, i0, i1) if i1 >= i0 else {"calls": 0}
            row = {"arm": arm, "run": run, "side": s, "tid": tid, "all_pass": bool(g["ok"]),
                   "cases_pass": g["cases_passed"], "cases_total": g["cases_total"],
                   "failed": [f["name"] for f in g["failed"]],
                   "rc": t.get("rc"), "elapsed_s": t.get("elapsed_s"),
                   "adapter_range": t.get("adapter_range"),
                   "calls": u.get("calls"), "prompt_tokens": u.get("prompt_tokens"),
                   "cached_tokens": u.get("cached_tokens"), "completion_tokens": u.get("completion_tokens"),
                   "total_tokens": u.get("total_tokens"), "models": u.get("models"),
                   "unreported_usage": u.get("unreported_usage"),
                   "artifacts": len(t.get("artifacts") or []),
                   "reply_chars": t.get("reply_chars"),
                   "ledger_steps": t.get("ledger_steps"), "ledger_calls": t.get("ledger_calls")}
            rows.append(row)
        agg = {"arm": arm, "side": s, "tasks": len(rows),
               "full_correct": sum(1 for r in rows if r["all_pass"]),
               "cases_pass": sum(r["cases_pass"] for r in rows),
               "cases_total": sum(r["cases_total"] for r in rows),
               "calls": sum(r["calls"] or 0 for r in rows),
               "prompt_tokens": sum(r["prompt_tokens"] or 0 for r in rows),
               "cached_tokens": sum(r["cached_tokens"] or 0 for r in rows),
               "completion_tokens": sum(r["completion_tokens"] or 0 for r in rows),
               "total_tokens": sum(r["total_tokens"] or 0 for r in rows),
               "elapsed_s": round(sum(r["elapsed_s"] or 0 for r in rows), 2),
               "unreported_usage": sum(r["unreported_usage"] or 0 for r in rows),
               "models": sorted({m for r in rows for m in (r["models"] or [])})}
        out["rows"].extend(rows)
        out["arms"].append(agg)
        print("[%s/%s] 整题全对 %d/%d · 用例 %d/%d · 调用 %d · tok %d · %ss" %
              (s, arm, agg["full_correct"], agg["tasks"], agg["cases_pass"], agg["cases_total"],
               agg["calls"], agg["total_tokens"], agg["elapsed_s"]))
        for r in rows:
            print("    %-3s ok=%-5s 用例 %2d/%2d 调用 %-3s tok %-8s %-7ss %s" %
                  (r["tid"], r["all_pass"], r["cases_pass"], r["cases_total"], r["calls"],
                   r["total_tokens"], r["elapsed_s"],
                   ("FAIL=" + ",".join(r["failed"])) if r["failed"] else ""))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
