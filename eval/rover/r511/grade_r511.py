#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R511 判分器: 按 (task, dir) 在**新进程**里以 `python3 -I -B` 跑隐藏用例, 逐条机械判对。

用法: python3 grade_r511.py --task p3|p4 --dir <产物目录> [--json <out.json>]
退出码: 0 全过 / 1 有失败 / 9 仪器错 (用例文件缺失等)。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CASES = {
    "p3": os.path.join(REPO, "eval/rover/r508/cases/p3_cases.py"),
    "p4": os.path.join(REPO, "eval/rover/r511/cases/p4_cases.py"),
}
REF = {
    "p3": os.path.join(REPO, "eval/rover/r508/ref/p3"),
    "p4": os.path.join(REPO, "eval/rover/r511/ref/p4"),
}


def grade(task, work):
    cases = CASES.get(task)
    if not cases or not os.path.exists(cases):
        return {"task": task, "ok": False, "instrument_error": "cases_missing", "cases": cases}
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": work,
           "PYTHONDONTWRITEBYTECODE": "1"}
    p = subprocess.run([sys.executable, "-I", "-B", cases], cwd=work, capture_output=True,
                       text=True, timeout=900, env=env)
    res = {"task": task, "dir": work, "rc": p.returncode}
    res["cases"] = [{"name": m.group(1), "pass": True}
                    for m in re.finditer(r"^CASE (\S+) PASS$", p.stdout, re.M)]
    res["failed"] = [{"name": m.group(1), "reason": (m.group(2) or "").strip()[:200]}
                     for m in re.finditer(r"^CASE (\S+) FAIL (.*)$", p.stdout, re.M)]
    summ = re.search(r"^SUMMARY (.+)$", p.stdout, re.M)
    res["summary"] = summ.group(1) if summ else "(no SUMMARY)"
    res["cases_passed"] = len(res["cases"])
    res["cases_total"] = res["cases_passed"] + len(res["failed"])
    res["ok"] = p.returncode == 0 and res["cases_total"] > 0 and not res["failed"]
    res["stdout_tail"] = p.stdout[-400:]
    res["stderr_tail"] = (p.stderr or "")[-400:]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=sorted(CASES), required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--oracle", action="store_true", help="用参考解目录做正控")
    ap.add_argument("--json")
    args = ap.parse_args()
    work = REF[args.task] if args.oracle else os.path.abspath(args.dir)
    r = grade(args.task, work)
    r["oracle"] = bool(args.oracle)
    print(json.dumps({k: r[k] for k in ("task", "ok", "cases_passed", "cases_total", "summary", "oracle")},
                     ensure_ascii=False))
    if r["failed"]:
        print("FAILED:", json.dumps(r["failed"], ensure_ascii=False))
    if args.json:
        json.dump(r, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0 if r["ok"] else (9 if r.get("instrument_error") else 1)


if __name__ == "__main__":
    sys.exit(main())
