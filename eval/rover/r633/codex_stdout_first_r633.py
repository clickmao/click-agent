#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R633 · 事后复算：**codex 真值臂的「stdout 优先」重判**（冻结快照只读重放，零重测）。

动因（承 skill 的 R417 教训「分类不能先看退出码」）：
  冻结判分器 `eval/rover/r610/cases/run_cases_r521.py` 的判对式 =
      `ok = (returncode == 0) and (stdout == expected)`
  ⇒ **退出码优先**：程序 stdout 逐字节正确但按 CLI 惯例 `sys.exit(1)` 时被记为 FAIL。
  R633 观测：codex 真值臂的失败**全部**为 `rc=1`（w225 13/13、w226 14/14、w227 15/15），
  无一条 `stdout_mismatch` ⇒ 该侧读数**可能是判分器严苛造成的低估**（测量层，不是能力层）。

本件回答：把同一批冻结产物按 **stdout 优先**（`stdout == expected` 即判过，另记 exit_ok）
重放一遍，给出「rc=1 但 stdout 正确」的条数 = 可能被低估的条数。

口径声明（必须随读数一起报）：
  · 本件是 **事后复算**（不重测臂、不动冻结快照、不改任何历史判决）；
  · 逐用例超时 30s（冻结跑为 10s，见 run_cases_r521.py 头注）⇒ 只作**上界**读数（更宽松）；
  · 产物侧仍为 R633 冻结快照（`eval/rover/r633/snapshots/<win>/<arm>/g1`）。

用法: python3 codex_stdout_first_r633.py [--out <json>] [--timeout 30]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SNAP = os.path.join(REPO, "eval/rover/r633/snapshots")
CASES = os.path.join(REPO, "eval/rover/r633/cases/cases-r521.json")


def one_tree(root, cases, tmo):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": root,
           "PYTHONPATH": root, "PYTHONDONTWRITEBYTECODE": "1"}
    rec = {"stdout_match": 0, "exit_ok": 0, "both": 0,
           "rc_nonzero_but_stdout_match": 0, "stdout_diff": 0, "error": 0, "n": len(cases)}
    ex = []
    for i, c in enumerate(cases):
        name = "%s#%02d-%s" % (c["game"], i, c["vis"])
        try:
            p = subprocess.run([sys.executable, "-B", "-m", "games", c["game"]], input=c["stdin"],
                               capture_output=True, text=True, timeout=tmo, cwd=root, env=env)
            sm = p.stdout.strip("\n") == c["expected_stdout"].strip("\n")
            ok = p.returncode == 0
            rec["stdout_match"] += 1 if sm else 0
            rec["exit_ok"] += 1 if ok else 0
            rec["both"] += 1 if (sm and ok) else 0
            if sm and not ok:
                rec["rc_nonzero_but_stdout_match"] += 1
                ex.append({"case": name, "rc": p.returncode})
            if not sm:
                rec["stdout_diff"] += 1
        except Exception as e:  # noqa: BLE001
            rec["error"] += 1
            ex.append({"case": name, "exc": type(e).__name__})
    rec["examples"] = ex[:12]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r633/evidence/codex-stdout-first-r633.json"))
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--arms", default="codex,agentP-r1,agentP-r2,agentP-r3")
    a = ap.parse_args()
    cases = json.load(io.open(CASES, encoding="utf-8"))
    arms = a.arms.split(",")
    out = {"round": "R633", "kind": "事后复算（零重测；冻结快照只读重放）",
           "frozen_judge": "eval/rover/r610/cases/run_cases_r521.py（ok = rc==0 ∧ stdout==expected ⇒ 退出码优先）",
           "timeout_s": a.timeout, "frozen_timeout_s": 10.0,
           "caveat": "复算超时 30s > 冻结跑 10s ⇒ 只作上界读数",
           "by_run": {}}
    for win in sorted(os.listdir(SNAP)):
        for arm in arms:
            root = os.path.join(SNAP, win, arm, "g1")
            if not os.path.isdir(root):
                continue
            rec = one_tree(root, cases, a.timeout)
            out["by_run"]["%s/%s" % (win, arm)] = rec
            print("%s/%-12s stdout_match=%d/%d both=%d rc1_stdout_ok=%d stdout_diff=%d err=%d"
                  % (win, arm, rec["stdout_match"], rec["n"], rec["both"],
                     rec["rc_nonzero_but_stdout_match"], rec["stdout_diff"], rec["error"]), flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("OUT=%s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
