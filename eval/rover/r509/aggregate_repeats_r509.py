#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R509 聚合器: 重复臂 × 逐用例通过率 × tokens 区间。

布局: <run-dir>/<arm>/rep<N>/<tid>/{work,side-run.json,audit/action_loop.jsonl}
      <run-dir>/adapter  <run-dir>/evidence
"""
from __future__ import annotations
import argparse, glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R508 = os.path.join(os.path.dirname(HERE), "r508")
sys.path.insert(0, R508)
import usage_from_dumps as ufd  # noqa: E402


def grade(tid, workdir, out):
    subprocess.run([sys.executable, os.path.join(R508, "proj_grade.py"), "--task", tid, "--dir", workdir,
                    "--isolate", "--json", out], check=False, capture_output=True)
    return json.load(open(out, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--tasks", default="p3")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    D = a.run_dir
    tids = [t for t in a.tasks.split(",") if t]
    ev = os.path.join(D, "evidence")
    os.makedirs(ev, exist_ok=True)
    arms = sorted({os.path.basename(p) for p in glob.glob(os.path.join(D, "*", "rep*", "*")) if os.path.isdir(p)})
    rows, case_matrix = [], {}
    for arm_dir in sorted(glob.glob(os.path.join(D, "*"))):
        arm = os.path.basename(arm_dir)
        if not os.path.isdir(os.path.join(arm_dir, "rep1")):
            continue
        side = "codex" if arm.lower().startswith("codex") else "agent"
        for rep in range(1, a.reps + 1):
            for tid in tids:
                rd = os.path.join(arm_dir, "rep%d" % rep, tid)
                work = os.path.join(rd, "work")
                if not os.path.isdir(work):
                    continue
                g = grade(tid, work, os.path.join(ev, "grade-%s-rep%d-%s.json" % (arm, rep, tid)))
                try:
                    sr = json.load(open(os.path.join(arm_dir, "rep%d" % rep, "side-run.json"), encoding="utf-8"))
                    t = (sr.get("tasks") or [{}])[0]
                    rng = t.get("adapter_range") or [1, 0]
                    elapsed = t.get("elapsed_s")
                except Exception:
                    rng, elapsed = [1, 0], None
                u = ufd.collect(os.path.join(D, "adapter"), side, rng[0], rng[1])
                led = []
                lf = os.path.join(rd, "audit", "action_loop.jsonl")
                if os.path.isfile(lf):
                    led = [json.loads(l) for l in open(lf, encoding="utf-8") if l.strip()]
                rows.append({"arm": arm, "rep": rep, "tid": tid, "all_pass": g["all_pass"],
                             "pass": g["pass_count"], "total": g["case_count"],
                             "fails": [c["name"] for c in g["cases"] if c["status"] != "PASS"],
                             "calls": u.get("calls"), "total_tokens": u.get("total_tokens"),
                             "prompt_tokens": u.get("prompt_tokens"), "elapsed_s": elapsed,
                             "steps": max([r.get("step", 0) for r in led] or [0]), "ledger_calls": len(led)})
                for c in g["cases"]:
                    case_matrix.setdefault((arm, tid, c["name"]), []).append(c["status"])
    # 汇总
    def stat(vals):
        v = [x for x in vals if isinstance(x, (int, float))]
        return None if not v else {"n": len(v), "min": min(v), "max": max(v), "mean": round(sum(v) / len(v), 1)}
    summary = {}
    for arm in sorted({r["arm"] for r in rows}):
        for tid in tids:
            rs = [r for r in rows if r["arm"] == arm and r["tid"] == tid]
            if not rs:
                continue
            summary.setdefault(arm, {})[tid] = {
                "reps": len(rs), "all_pass_reps": sum(1 for r in rs if r["all_pass"]),
                "pass_rates": "%d/%d" % (sum(r["pass"] for r in rs), sum(r["total"] for r in rs)),
                "total_tokens": stat([r["total_tokens"] for r in rs]),
                "calls": stat([r["calls"] for r in rs]), "elapsed_s": stat([r["elapsed_s"] for r in rs]),
                "steps": stat([r["steps"] for r in rs]),
            }
    unstable = {("%s|%s|%s" % k): v for k, v in case_matrix.items() if len(set(v)) > 1}
    out = {"run_dir": D, "rows": rows, "summary": summary, "unstable_cases": unstable}
    if a.json:
        json.dump(out, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("arm tid  全对轮次  用例合计    tok min/mean/max        calls  墙钟s        steps")
    for arm, d in summary.items():
        for tid, s in d.items():
            tk = s["total_tokens"] or {}
            print("%-6s %-4s %d/%d      %-8s  %s/%s/%s  %s  %s  %s" % (
                arm, tid, s["all_pass_reps"], s["reps"], s["pass_rates"],
                tk.get("min"), tk.get("mean"), tk.get("max"),
                (s["calls"] or {}).get("mean"), (s["elapsed_s"] or {}).get("mean"), (s["steps"] or {}).get("mean")))
    print("不稳定用例 (跨轮次状态不一致):")
    for k, v in unstable.items():
        print("  ", k, v)
    print("SUMMARY_JSON=" + (a.json or "-"))


if __name__ == "__main__":
    main()
