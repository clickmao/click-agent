#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 汇总器: 逐臂逐题判分 (铁律11 前置) + 取 tokens/调用/墙钟, 出对照报告。

布局: <run-dir>/{agentA,agentB,codex}/<tid>/work ; <run-dir>/adapter ; <run-dir>/evidence
判分: 调 proj_grade.py --isolate (独立物化 + python3 -I -B 逐条隐藏用例)。
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import usage_from_dumps as ufd  # noqa: E402

ARMS = [("A", "agent", "agentA", "本侧默认"), ("B", "agent", "agentB", "本侧步数上限=24"),
        ("C", "codex", "codex", "codex-cli 外部真值")]


def grade(task, workdir, out_json, timeout=420):
    cmd = [sys.executable, os.path.join(HERE, "proj_grade.py"), "--task", task,
           "--dir", workdir, "--isolate", "--json", out_json]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    try:
        return json.load(open(out_json, encoding="utf-8"))
    except Exception:
        return {"error": "no_json", "rc": p.returncode, "stderr": p.stderr[-400:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--taskset", default=os.path.join(HERE, "taskset-r508.json"))
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    rd = a.run_dir
    ts = json.load(open(a.taskset, encoding="utf-8"))
    ev = os.path.join(rd, "evidence")
    os.makedirs(ev, exist_ok=True)
    adir = os.path.join(rd, "adapter")
    rows = []
    for tag, side, sub, desc in ARMS:
        base = os.path.join(rd, sub)
        sr = os.path.join(base, "side-run.json")
        if not os.path.exists(sr):
            rows.append({"arm": tag, "side": side, "desc": desc, "missing": sr})
            continue
        run = json.load(open(sr, encoding="utf-8"))
        for t in run["tasks"]:
            tid = t["tid"]
            g = grade(tid, os.path.join(base, tid, "work"),
                      os.path.join(ev, "grade-%s-%s.json" % (tag, tid)))
            rng = t.get("adapter_range") or [1, 0]
            u = ufd.collect(adir, side, rng[0], rng[1]) if rng[1] >= rng[0] else {"calls": 0}
            rows.append({
                "arm": tag, "side": side, "desc": desc, "tid": tid,
                "all_pass": bool(g.get("all_pass")),
                "cases_pass": g.get("pass_count"), "cases_total": g.get("case_count"),
                "failed": [c["name"] for c in (g.get("cases") or []) if c["status"] != "PASS"],
                "rc": t.get("rc"), "elapsed_s": t.get("elapsed_s"),
                "calls": u.get("calls"), "prompt_tokens": u.get("prompt_tokens"),
                "cached_tokens": u.get("cached_tokens"), "completion_tokens": u.get("completion_tokens"),
                "total_tokens": u.get("total_tokens"), "models": u.get("models"),
                "unreported_usage": u.get("unreported_usage"),
                "ledger_calls": t.get("ledger_calls"), "ledger_steps": t.get("ledger_steps"),
                "artifacts": len(t.get("artifacts") or []),
                "artifact_bytes": sum(int(x.get("bytes") or 0) for x in (t.get("artifacts") or [])),
                "reply_chars": t.get("reply_chars"),
            })
    out = {"run_dir": rd, "rows": rows,
           "models": sorted({m for r in rows for m in (r.get("models") or [])})}
    if a.json:
        json.dump(out, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("arm tid 全对 用例 调用 tok_prompt tok_total s  产物 失败用例")
    for r in rows:
        print("%-2s %-3s %-4s %s/%s %-4s %-8s %-9s %-5s %-3s %s" % (
            r["arm"], r["tid"], "Y" if r.get("all_pass") else "N",
            r.get("cases_pass"), r.get("cases_total"), r.get("calls"),
            r.get("prompt_tokens"), r.get("total_tokens"), r.get("elapsed_s"),
            r.get("artifacts"), ",".join(r.get("failed") or [])[:60]))
    print("MODELS=%s" % (out["models"],))
    return 0


if __name__ == "__main__":
    sys.exit(main())
