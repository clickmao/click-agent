#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R640 · 缺口族**可执行前置步骤**（`wythoff_precheck`）—— 承用户令
「缺口族优先做**可执行前置步骤**使其从静默错步变硬证据」（RF0005 §3 规则 R2 的换杠杆动作）。

它改哪一格读数：**不改变任何既有读数**（零产品改动 / 零重测）。它把 `wythoff` 缺口
从「事后用例通过数（一个标量）」变成「**事前可执行、逐谓词点名**的违规清单」——
即可被管线在交付前调用的前置闸，使静默错步（分数下降）变为硬证据（指名到谓词与实例）。

规格来源 = 冻结题集里 `### 游戏 wythoff` 的**逐字规格**（题面文本）；真值参照 =
`eval/rover/r622/wythoff_oracle.py`（独立实现，与判定器/生成器零共享代码）。

谓词（全部只读，零写入被测树）：
  P1 入口存在且可调用（`games.wythoff.solve`）
  P2 输出格式合法（`LOSE` 或 `WIN <i> <j>`）
  P3 着法合法性（i∈[0,a], j∈[0,b], (i,j)≠(0,0), 且 i==0 ∨ j==0 ∨ i==j）
  P4 状态正确（LOSE/WIN 与 oracle 一致）
  P5 冷集自洽（25×25 网格的隐含必败集 == oracle 必败集）
  P6 字典序最小（必胜局着法 == oracle 的 min(winning_moves)）

退出码（分层，fail-closed）：0 = 全谓词通过 / 1 = 有违规（逐条点名）/ 2 = 器具或输入缺陷 / 3 = 输入缺失。
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r622"))
import wythoff_oracle as ORC  # noqa: E402

CASES = os.path.join(REPO, "eval/rover/r640/cases/cases-r521.json")
GRID = 25
WIN_RE = re.compile(r"^WIN (\d+) (\d+)$")

PROBE = r'''
import json, os, sys
tree = sys.argv[1]
sys.path.insert(0, tree); os.chdir(tree)
res = {"ok": False, "entry": False}
try:
    mod = __import__("games.wythoff", fromlist=["solve"])
    fn = getattr(mod, "solve", None)
    res["entry"] = callable(fn)
    if not callable(fn):
        res["err"] = "NO_CALLABLE_SOLVE"
    else:
        grid = {}
        for a in range(1, %d + 1):
            for b in range(1, %d + 1):
                try:
                    grid["%%d %%d" %% (a, b)] = str(fn("%%d %%d\n" %% (a, b))).strip()
                except Exception as e:
                    grid["%%d %%d" %% (a, b)] = "ERR:" + type(e).__name__
        res.update(ok=True, grid=grid)
except Exception as e:
    res["err"] = type(e).__name__ + ":" + str(e)[:100]
print(json.dumps(res))
''' % (GRID, GRID)


def sha16(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:16]


def probe(tree, tmo=120.0):
    tmp = tempfile.mkdtemp(prefix="r640pc-")
    dst = os.path.join(tmp, "t")
    try:
        shutil.copytree(tree, dst)
        p = subprocess.run([sys.executable, "-B", "-c", PROBE, dst], capture_output=True,
                           text=True, timeout=tmo, cwd=dst,
                           env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
                                "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            return json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            return {"ok": False, "entry": False,
                    "err": "probe_parse_fail:" + (p.stdout or "")[-80:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "entry": False, "err": "probe_timeout"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def precheck(tree):
    """→ {rc, predicates:{P1..P6:{pass, n_viol, examples[]}}}"""
    pr = {k: {"pass": True, "n_viol": 0, "examples": []} for k in
          ("P1_entry", "P2_format", "P3_legal", "P4_state", "P5_coldset", "P6_lexmin")}
    if not os.path.isdir(os.path.join(tree, "games")):
        return {"rc": 3, "error": "tree_missing_games", "predicates": pr}
    p = probe(tree)
    if not p.get("ok"):
        pr["P1_entry"] = {"pass": False, "n_viol": 1, "examples": [str(p.get("err"))[:120]]}
        return {"rc": 2 if p.get("entry") is False and p.get("err") else 2,
                "error": str(p.get("err"))[:120], "predicates": pr}
    grid = p["grid"]
    implied = set()
    for key, val in sorted(grid.items()):
        a, b = (int(x) for x in key.split())
        if val.startswith("ERR:"):
            pr["P1_entry"]["pass"] = False
            pr["P1_entry"]["n_viol"] += 1
            if len(pr["P1_entry"]["examples"]) < 5:
                pr["P1_entry"]["examples"].append("%s ⇒ %s" % (key, val))
            continue
        if val == "LOSE":
            implied.add((a, b))
        else:
            m = WIN_RE.match(val)
            if not m:
                pr["P2_format"]["pass"] = False
                pr["P2_format"]["n_viol"] += 1
                if len(pr["P2_format"]["examples"]) < 5:
                    pr["P2_format"]["examples"].append("%s ⇒ %r" % (key, val))
                continue
            i, j = int(m.group(1)), int(m.group(2))
            legal = (0 <= i <= a and 0 <= j <= b and (i, j) != (0, 0)
                     and (i == 0 or j == 0 or i == j))
            if not legal:
                pr["P3_legal"]["pass"] = False
                pr["P3_legal"]["n_viol"] += 1
                if len(pr["P3_legal"]["examples"]) < 5:
                    pr["P3_legal"]["examples"].append("%s ⇒ (%d,%d)" % (key, i, j))
                continue
            truth_lose = ORC.LOSING[a][b]
            if truth_lose:                    # 真值必败却给出必胜着法 ⇒ 状态错
                pr["P4_state"]["pass"] = False
                pr["P4_state"]["n_viol"] += 1
                if len(pr["P4_state"]["examples"]) < 5:
                    pr["P4_state"]["examples"].append("%s ⇒ %s (真值 LOSE)" % (key, val))
                continue
            if not ORC.LOSING[a - i][b - j]:   # 着法未走到必败位
                pr["P4_state"]["pass"] = False
                pr["P4_state"]["n_viol"] += 1
                if len(pr["P4_state"]["examples"]) < 5:
                    pr["P4_state"]["examples"].append("%s ⇒ %s 未走到必败位" % (key, val))
                continue
            wm = ORC.winning_moves(a, b)
            if (i, j) != min(wm):
                pr["P6_lexmin"]["pass"] = False
                pr["P6_lexmin"]["n_viol"] += 1
                if len(pr["P6_lexmin"]["examples"]) < 5:
                    pr["P6_lexmin"]["examples"].append(
                        "%s ⇒ (%d,%d) 应为 %s" % (key, i, j, min(wm)))
    truth = {(a, b) for a in range(1, GRID + 1) for b in range(1, GRID + 1) if ORC.LOSING[a][b]}
    if implied != truth:
        extra, missing = sorted(implied - truth), sorted(truth - implied)
        pr["P5_coldset"]["pass"] = False
        pr["P5_coldset"]["n_viol"] = len(extra) + len(missing)
        pr["P5_coldset"]["examples"] = (["多报 %d 处 例 %s" % (len(extra), extra[:4])] if extra else []) + \
                                       (["漏报 %d 处 例 %s" % (len(missing), missing[:4])] if missing else [])
    viol = sum(1 for v in pr.values() if not v["pass"])
    return {"rc": 1 if viol else 0, "n_failed_predicates": viol, "predicates": pr,
            "n_cells": GRID * GRID}


def classify_run(run_id):
    """run_id = 'w237/agentP-r2' 或 'w237/codex'；返回 rc 与谓词读数。"""
    tree = os.path.join(REPO, "eval/rover/r639/snapshots", run_id, "g1")
    if not os.path.isdir(tree):
        return {"run": run_id, "rc": 3, "error": "snapshot_missing"}
    out = {"run": run_id, "tree": tree}
    out.update(precheck(tree))
    return out


FROZEN_EXPECT = {
    "PASS_RUNS": ["w237/agentP-r1", "w238/agentP-r1", "w238/agentP-r2", "w239/agentP-r3",
                  "w237/codex", "w238/codex", "w239/codex"],
    "FAIL_RUNS": ["w237/agentP-r2", "w237/agentP-r3", "w238/agentP-r3",
                  "w239/agentP-r1", "w239/agentP-r2"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=None)
    ap.add_argument("--selfcheck", action="store_true", help="两侧齿证（真机冻结面）")
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r640/out/precheck-r640.json"))
    a = ap.parse_args()
    runs = a.runs or (FROZEN_EXPECT["PASS_RUNS"] + FROZEN_EXPECT["FAIL_RUNS"])
    res = {"instrument": sha16(os.path.abspath(__file__)),
           "cases_pin": hashlib.sha256(io.open(CASES, "rb").read()).hexdigest(),
           "grid": GRID, "readings": [classify_run(r) for r in runs]}
    if a.selfcheck:
        by = {r["run"]: r for r in res["readings"]}
        pos_ok = all(by[r]["rc"] == 0 for r in FROZEN_EXPECT["PASS_RUNS"] if r in by)
        neg_ok = all(by[r]["rc"] == 1 for r in FROZEN_EXPECT["FAIL_RUNS"] if r in by)
        res["teeth"] = {"POS_all_pass_runs_rc0": pos_ok, "NEG_all_fail_runs_rc1": neg_ok,
                        "pass": bool(pos_ok and neg_ok),
                        "rule": "通过跑次（含 codex 真值）⇒ rc=0 ∧ 失败跑次 ⇒ rc=1；任一方向错 = 器具缺陷"}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["readings"]:
        print("%-20s rc=%s failed=%s %s" % (r["run"], r["rc"], r.get("n_failed_predicates"),
              {k: v["n_viol"] for k, v in r.get("predicates", {}).items() if not v["pass"]}))
    if a.selfcheck:
        print("TEETH", res["teeth"])
    print("wrote", a.out)
    return 0 if (not a.selfcheck or res["teeth"]["pass"]) else 1


if __name__ == "__main__":
    sys.exit(main())
