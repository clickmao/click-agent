#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 F2 判分器 (独立实现, **不**复用用例脚本 `run_cases_r529.py` ⇒ 与前置器构成两条独立复核路径)。

与 `grade_r519.py` 同形: --dir <workspace> [--out <json>]; rc=0 仅当全部用例通过。
实跑 `python3 -I -B -m toolkit <mod>` (cwd=被测工作区), 逐字节比对 stdout (仅去尾换行)。
"""
import argparse
import io
import json
import os
import subprocess
import sys

R = "/home/agentuser/AgentFramework"
CASES = os.path.join(R, "eval/rover/r529/cases/cases-r529-f2.json")
ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
ap.add_argument("--out", default="")
a = ap.parse_args()
cases = json.load(io.open(CASES, encoding="utf-8"))
env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": a.dir,
       "PYTHONPATH": a.dir, "PYTHONDONTWRITEBYTECODE": "1"}
res = []
for i, c in enumerate(cases):
    name = "%s#%02d-%s" % (c["mod"], i, c.get("vis", "hidden"))
    try:
        # 禁 -I: 隔离模式忽略 PYTHONPATH ⇒ 子进程找不到 toolkit
        p = subprocess.run([sys.executable, "-B", "-m", "toolkit", c["mod"]], input=c["stdin"],
                           capture_output=True, text=True, timeout=60, cwd=a.dir, env=env)
        ok = (p.returncode == 0) and (p.stdout.strip("\n") == c["expected_stdout"].strip("\n"))
        why = "" if ok else ("rc=%d" % p.returncode if p.returncode != 0 else "stdout 不匹配")
    except Exception as e:  # noqa: BLE001
        ok, why = False, type(e).__name__
    res.append({"game": c["mod"], "name": name, "vis": c.get("vis", "hidden"), "ok": ok, "why": why})
n = sum(1 for r in res if r["ok"])
out = {"task": "t1", "round": "R529", "family": "toolkit-multimodule-v1", "cases": res, "passed": n,
       "total": len(res),
       "public": "%d/%d" % (sum(1 for r in res if r["ok"] and r["vis"] == "public"),
                            sum(1 for r in res if r["vis"] == "public")),
       "hidden": "%d/%d" % (sum(1 for r in res if r["ok"] and r["vis"] == "hidden"),
                            sum(1 for r in res if r["vis"] == "hidden")),
       "rc": 0 if n == len(res) else 1}
if a.out:
    json.dump(out, io.open(a.out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False)[:400])
sys.exit(out["rc"])
