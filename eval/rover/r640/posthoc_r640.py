#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R640 · `posthoc`（codex/产品「stdout 优先」重判）**常设件**（承 R639 下轮候选 ③）。

动因：R639 的判决件里 `posthoc_checks` 列为「未生成 ⇒ 不可判」。承 R633 的 `codex_stdout_first_r633.py`
（一次性的 R633 专用件），本轮把它**常设化 + 参数化**（`--face` 指定轮目录），使该诊断列在每一轮都可判。

口径（必须随读数一起报）：
  · 事后复算，**零重测**（只在冻结快照副本上重放），不改写任何历史判决；
  · 判分器冻结式为**退出码优先**（`ok = rc == 0 ∧ stdout == expected`）⇒ 本件报
    `rc≠0 ∧ stdout 逐字节正确` 的条数 = **可能被低估**的条数（测量层，不是能力层）；
  · 逐用例超时 30s（冻结跑为 10s）⇒ 只作**上界**读数。

退出码：0 = 读数生成 / 2 = 器具或输入缺陷 / 3 = 输入缺失。
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
FAMILIES = ["life", "sub", "nim", "wythoff"]


def sha16(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:16]


def one_tree(root, cases, tmo):
    tmp = tempfile.mkdtemp(prefix="r640ph-")
    dst = os.path.join(tmp, "t")
    rec = {"stdout_match": 0, "exit_ok": 0, "both": 0, "rc_nonzero_but_stdout_match": 0,
           "stdout_diff": 0, "error": 0, "n": len(cases), "by_family": {}}
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": dst,
           "PYTHONPATH": dst, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        shutil.copytree(root, dst)
        for c in cases:
            fam = c["game"]
            d = rec["by_family"].setdefault(fam, {"n": 0, "stdout_match": 0,
                                                  "rc_nonzero_but_stdout_match": 0})
            d["n"] += 1
            try:
                p = subprocess.run([sys.executable, "-B", "-m", "games", fam], input=c["stdin"],
                                   capture_output=True, text=True, timeout=tmo, cwd=dst, env=env)
                rc, out = p.returncode, (p.stdout or "").strip("\n")
            except subprocess.TimeoutExpired:
                rc, out = 124, ""
            exp = c["expected_stdout"].strip("\n")
            sm = out == exp
            if rc == 0:
                rec["exit_ok"] += 1
            if sm:
                rec["stdout_match"] += 1
                d["stdout_match"] += 1
            if rc == 0 and sm:
                rec["both"] += 1
            elif sm:
                rec["rc_nonzero_but_stdout_match"] += 1
                d["rc_nonzero_but_stdout_match"] += 1
            elif rc == 0:
                rec["stdout_diff"] += 1
            if rc not in (0, 124) and not sm:
                rec["error"] += 1
        return rec
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--face", default="r639", help="冻结面轮目录名（eval/rover/<face>/snapshots）")
    ap.add_argument("--cases", default=None)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    snap = os.path.join(REPO, "eval/rover", a.face, "snapshots")
    cases_p = a.cases or os.path.join(REPO, "eval/rover", "r640", "cases", "cases-r521.json")
    if not os.path.isdir(snap) or not os.path.isfile(cases_p):
        print(json.dumps({"rc": 3, "error": "input_missing", "snap": snap, "cases": cases_p}))
        return 3
    cases = json.load(io.open(cases_p, encoding="utf-8"))
    res = {"instrument": sha16(os.path.abspath(__file__)), "face": a.face,
           "cases": {"path": cases_p,
                     "sha256": hashlib.sha256(io.open(cases_p, "rb").read()).hexdigest()},
           "timeout_s": a.timeout, "readings": []}
    for win in sorted(os.listdir(snap)):
        wd = os.path.join(snap, win)
        if not os.path.isdir(wd):
            continue
        for arm in sorted(os.listdir(wd)):
            tree = os.path.join(wd, arm, "g1")
            if not os.path.isdir(os.path.join(tree, "games")):
                continue
            rec = one_tree(tree, cases, a.timeout)
            rec.update(run="%s/%s" % (win, arm), win=win, arm=arm)
            res["readings"].append(rec)
    tot = sum(r["rc_nonzero_but_stdout_match"] for r in res["readings"])
    res["summary"] = {"n_runs": len(res["readings"]),
                      "rc_nonzero_but_stdout_match_total": tot,
                      "may_be_underestimated": bool(tot > 0),
                      "by_run": {r["run"]: r["rc_nonzero_but_stdout_match"] for r in res["readings"]}}
    res["rc"] = 0
    out = a.out or os.path.join(REPO, "eval/rover/r640/out", "posthoc-%s.json" % a.face)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res["summary"], ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
