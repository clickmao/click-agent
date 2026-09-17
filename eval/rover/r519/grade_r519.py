#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R519 判分器: 真执行 `python3 -m games <game>` (cwd=被测工作区), 逐字节比对 stdout。
用法: grade_r519.py --dir <workspace> [--out <json>]  —— rc=0 仅当全部用例通过。"""
import argparse, json, os, subprocess, sys
R = "/home/agentuser/AgentFramework"
ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--out", default="")
a = ap.parse_args()
spec = json.load(open(os.path.join(R, "eval/rover/r519/taskset-r519.json"), encoding="utf-8"))
cases = spec["tasks"][0]["cases"]
res = []
for c in cases:
    cmd = [sys.executable, "-m", "games", c["game"]]
    try:
        p = subprocess.run(cmd, input=c["stdin"], capture_output=True, text=True, timeout=60, cwd=a.dir)
        ok = (p.returncode == 0) and (p.stdout.strip("\n") == c["expected_stdout"].strip("\n"))
        why = "" if ok else ("rc=%d" % p.returncode if p.returncode else "stdout 不匹配")
    except Exception as e:
        ok, why = False, type(e).__name__
    res.append({"game": c["game"], "vis": c["vis"], "ok": ok, "why": why})
n = sum(1 for r in res if r["ok"])
out = {"task": "g1", "round": "R519", "cases": res, "passed": n, "total": len(res),
       "public": "%d/%d" % (sum(1 for r in res if r["ok"] and r["vis"] == "public"), sum(1 for r in res if r["vis"] == "public")),
       "hidden": "%d/%d" % (sum(1 for r in res if r["ok"] and r["vis"] == "hidden"), sum(1 for r in res if r["vis"] == "hidden")),
       "rc": 0 if n == len(res) else 1}
if a.out: json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False)[:400])
sys.exit(out["rc"])
