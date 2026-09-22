#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R640 · 缺口族**可执行前置步骤**（`wythoff_precheck`）—— 承用户令
「缺口族优先做**可执行前置步骤**使其从静默错步变硬证据」（RF0005 §3 规则 R2 的换杠杆动作）。

它改哪一格读数：**不改变任何既有读数**（零产品改动 / 零重测）。它把 `wythoff` 缺口
从「事后用例通过数（一个标量）」变成「**事前可执行、逐谓词点名**的违规清单」。

规格来源 = 冻结题集里 `wythoff` 的**逐字样例**（`WIN i j` = 从两堆各取 i / j 枚；样例
`21 25 ⇒ WIN 15 15` / `10 9 ⇒ WIN 0 3` / `18 8 ⇒ WIN 5 0` 皆指向 `(6,10)/(6,10)/(8,13)`
—— Wythoff 必败位，着法语义由此**逐例反解**，非猜测）；真值参照 =
`eval/rover/r622/wythoff_oracle.py`（独立实现，与判定器/生成器零共享代码）。

谓词（全部只读，零写入被测树）：
  P0 预算内可评估（625 格全跑完；超预算 ⇒ 交付物侧缺陷，非器具侧）
  P1 入口存在且可调用（`games.wythoff.solve`；导入/属性错 ⇒ 交付物侧）
  P2 输出格式合法（`LOSE` 或 `WIN <i> <j>`）
  P3 着法合法性（i∈[0,a], j∈[0,b], (i,j)≠(0,0), 且 i==0 ∨ j==0 ∨ i==j）
  P4 状态正确（LOSE/WIN 与 oracle 一致；必胜局的着法须走到 oracle 必败位）
  P5 冷集自洽（25×25 网格的隐含必败集 == oracle 必败集）
  P6 字典序最小（必胜局着法 == oracle 的 min(winning_moves)）

退出码（分层，fail-closed）：0 = 全谓词通过 / 1 = 交付物侧违规（逐条点名）/ 2 = **器具**缺陷
（探针自身不可解析 / 解释器失败）/ 3 = 输入缺失。

## v2 变更（**披露式**；v1 读数与器具字节原样留存）
v1（`instruments/wythoff_precheck_v1_r640.py`, sha16 `f34c1cd7e856cb38`；读数
`out/precheck-r640-v1.json`）两侧齿证**双红**，根因两条，**均在器具侧**：
  ① 期望表**手写**（把 `w239/codex` 当「全绿跑次」）—— 冻结面实测该真值跑次 13/15（其产物在
     204/625 格给出**非法着法**，如 `21 25 ⇒ WIN 1 13`）⇒ 手写期望表 = **编造控制**；v2 改为
     由冻结面读数**机取**（`out/attrib-r640.json.per_run_wythoff`），缺源即 rc=3 fail-closed。
  ② 探针超时被归 rc=2（器具层）—— 实为**交付物侧过慢**（该跑次 625 格实测 148.18 s，v1 预算
     120 s）⇒ v2 把「超预算」独立成谓词 `P0_budget`（rc=1，点名），并把预算抬到 300 s；
     rc=2 只保留「探针 stdout 不可解析 / 解释器失败」。
预注册判据**照原样**判（v1 ⇒ J6 FAIL），v2 读数单列 `checks_posthoc` 并于下轮重新注册。
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
FROZEN_READINGS = os.path.join(REPO, "eval/rover/r640/out/attrib-r640.json")
SNAP = os.path.join(REPO, "eval/rover/r639/snapshots")
GRID = 25
BUDGET_S = 300.0
WIN_RE = re.compile(r"^WIN (\d+) (\d+)$")
VERSION = "v2"

PROBE = r'''
import json, os, sys, time
tree, budget = sys.argv[1], float(sys.argv[2])
sys.path.insert(0, tree); os.chdir(tree)
res = {"ok": False, "entry": False}
t0 = time.time()
try:
    mod = __import__("games.wythoff", fromlist=["solve"])
    fn = getattr(mod, "solve", None)
    res["entry"] = callable(fn)
    if not callable(fn):
        res["err"] = "NO_CALLABLE_SOLVE"
    else:
        grid = {}; timed_out = False; done = 0
        brk = False
        for a in range(1, %d + 1):
            for b in range(1, %d + 1):
                if time.time() - t0 > budget:
                    timed_out = True; brk = True; break
                try:
                    grid["%%d %%d" %% (a, b)] = str(fn("%%d %%d\n" %% (a, b))).strip()
                except Exception as e:
                    grid["%%d %%d" %% (a, b)] = "ERR:" + type(e).__name__
                done += 1
            if brk:
                break
        res.update(ok=True, grid=grid, timed_out=timed_out, done=done,
                   elapsed=round(time.time() - t0, 2))
except Exception as e:
    res["err"] = type(e).__name__ + ":" + str(e)[:120]
print(json.dumps(res))
''' % (GRID, GRID)


def sha16(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:16]


def probe(tree, budget=BUDGET_S):
    """→ (payload, instrument_error)。instrument_error 非 None ⇒ 器具层（rc=2）。"""
    tmp = tempfile.mkdtemp(prefix="r640pc-")
    dst = os.path.join(tmp, "t")
    try:
        shutil.copytree(tree, dst)
        try:
            p = subprocess.run([sys.executable, "-B", "-c", PROBE, dst, str(budget)],
                               capture_output=True, text=True, timeout=budget + 60,
                               cwd=dst, env={"PATH": "/usr/local/bin:/usr/bin:/bin",
                                             "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired:
            return {"ok": False, "entry": True, "timeout": True, "err": "subprocess_budget_exceeded"}, None
        try:
            return json.loads(p.stdout.strip().splitlines()[-1]), None
        except Exception:  # noqa: BLE001
            return None, "probe_stdout_unparsable rc=%s tail=%r" % (p.returncode, (p.stdout or "")[-80:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def precheck(tree, budget=BUDGET_S):
    """→ {rc, predicates:{P0..P6:{pass,n_viol,examples}}, ...}"""
    pr = {k: {"pass": True, "n_viol": 0, "examples": []} for k in
          ("P0_budget", "P1_entry", "P2_format", "P3_legal", "P4_state", "P5_coldset", "P6_lexmin")}
    if not os.path.isdir(os.path.join(tree, "games")):
        return {"rc": 3, "error": "tree_missing_games", "predicates": pr}
    p, ierr = probe(tree, budget)
    if ierr is not None:
        return {"rc": 2, "error": ierr, "predicates": pr, "instrument_error": True}
    assert p is not None
    if p.get("timeout") or p.get("timed_out"):
        pr["P0_budget"] = {"pass": False, "n_viol": 1,
                           "examples": ["预算 %.0fs 内未跑完 625 格（已跑 %s 格，耗时 %s s）"
                                        % (budget, p.get("done"), p.get("elapsed"))]}
    if not p.get("ok"):
        # 交付物侧：导入/入口错（器具层已在上面分离）
        pr["P1_entry"] = {"pass": False, "n_viol": 1, "examples": [str(p.get("err"))[:140]]}
        rc = 1
        return {"rc": rc, "n_failed_predicates": sum(1 for v in pr.values() if not v["pass"]),
                "predicates": pr, "n_cells": 0, "partial": True}
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
            if not ORC.LOSING[a][b]:
                pr["P4_state"]["pass"] = False
                pr["P4_state"]["n_viol"] += 1
                if len(pr["P4_state"]["examples"]) < 5:
                    pr["P4_state"]["examples"].append("%s ⇒ LOSE (真值 WIN)" % key)
            continue
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
        if ORC.LOSING[a][b]:                       # 真值必败却给出必胜着法 ⇒ 状态错
            pr["P4_state"]["pass"] = False
            pr["P4_state"]["n_viol"] += 1
            if len(pr["P4_state"]["examples"]) < 5:
                pr["P4_state"]["examples"].append("%s ⇒ %s (真值 LOSE)" % (key, val))
            continue
        if not ORC.LOSING[a - i][b - j]:           # 着法未走到必败位
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
                pr["P6_lexmin"]["examples"].append("%s ⇒ (%d,%d) 应为 %s" % (key, i, j, min(wm)))
    if not p.get("timed_out"):
        truth = {(a, b) for a in range(1, GRID + 1) for b in range(1, GRID + 1) if ORC.LOSING[a][b]}
        if implied != truth:
            extra, missing = sorted(implied - truth), sorted(truth - implied)
            pr["P5_coldset"]["pass"] = False
            pr["P5_coldset"]["n_viol"] = len(extra) + len(missing)
            pr["P5_coldset"]["examples"] = (["多报 %d 处 例 %s" % (len(extra), extra[:4])] if extra else []) + \
                                           (["漏报 %d 处 例 %s" % (len(missing), missing[:4])] if missing else [])
    viol = sum(1 for v in pr.values() if not v["pass"])
    return {"rc": 1 if viol else 0, "n_failed_predicates": viol, "predicates": pr,
            "n_cells": len(grid), "elapsed_s": p.get("elapsed")}


def expectations():
    """**机取**期望表：冻结面逐跑次用例通过数（禁手写）。缺源 ⇒ None（fail-closed）。"""
    d = None
    if os.path.isfile(FROZEN_READINGS):
        try:
            d = json.load(io.open(FROZEN_READINGS, encoding="utf-8")).get("per_run_wythoff")
        except Exception:  # noqa: BLE001
            d = None
    if not d:
        return None
    n = max(v["n"] for v in d.values())
    return {"source": FROZEN_READINGS, "source_sha16": sha16(FROZEN_READINGS),
            "n_cases": n,
            "PASS_RUNS": sorted(r for r, v in d.items() if v["pass"] == n),
            "FAIL_RUNS": sorted(r for r, v in d.items() if v["pass"] < n),
            "per_run_pass": {r: v["pass"] for r, v in d.items()}}


def classify_run(run_id, budget=BUDGET_S):
    tree = os.path.join(SNAP, run_id, "g1")
    if not os.path.isdir(tree):
        return {"run": run_id, "rc": 3, "error": "snapshot_missing"}
    out = {"run": run_id, "tree": tree}
    out.update(precheck(tree, budget))
    return out


# ---- 合成臂（器具自检；**在 /tmp 副本上**，零仓内夹具）----------------------------
def syn_tree(tmp, body, entry=True):
    d = os.path.join(tmp, "t")
    os.makedirs(os.path.join(d, "games"), exist_ok=True)
    io.open(os.path.join(d, "games", "__init__.py"), "w").write("")
    io.open(os.path.join(d, "games", "wythoff.py"), "w").write(body)
    return d


MUT_LOSE = ("def solve(s):\n    return 'LOSE'\n")
SLOW = ("import time\n"
        "def solve(s):\n    time.sleep(0.5)\n    return 'LOSE'\n")
DEAD = ("import os\nos._exit(3)\n")


def synthetic_arms():
    """四臂：正控（真真值树副本 ⇒ rc0）/ 变异（恒 LOSE ⇒ rc1）/
    超预算（0.5 s/格 ⇒ rc1 且 P0 点名）/ 探针不可解析（进程自杀 ⇒ rc2）。"""
    res = []
    tmp = tempfile.mkdtemp(prefix="r640syn-")
    try:
        exp = expectations()
        pos_src = os.path.join(SNAP, exp["PASS_RUNS"][0], "g1") if exp else None
        if pos_src:
            dst = os.path.join(tmp, "pos", "g1")
            shutil.copytree(pos_src, dst)
            res.append(dict(run="SYN/POS_correct_impl", **precheck(dst)))
        for name, body, bud in (("SYN/NEG_always_lose", MUT_LOSE, 60.0),
                                ("SYN/NEG_over_budget", SLOW, 20.0),
                                ("SYN/INSTR_dead_process", DEAD, 60.0)):
            res.append(dict(run=name, **precheck(syn_tree(tempfile.mkdtemp(prefix="s-"), body), bud)))
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=None)
    ap.add_argument("--selfcheck", action="store_true", help="两侧齿证 + 合成四臂")
    ap.add_argument("--no-synth", action="store_true")
    ap.add_argument("--budget", type=float, default=BUDGET_S)
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r640/out/precheck-r640-%s.json" % VERSION))
    a = ap.parse_args()
    exp = expectations()
    if exp is None:
        print(json.dumps({"rc": 3, "error": "frozen_readings_missing", "src": FROZEN_READINGS}))
        return 3
    runs = a.runs or (exp["PASS_RUNS"] + exp["FAIL_RUNS"])
    res = {"version": VERSION, "instrument": sha16(os.path.abspath(__file__)),
           "cases_pin": hashlib.sha256(io.open(CASES, "rb").read()).hexdigest(),
           "grid": GRID, "budget_s": a.budget, "expectations": exp,
           "readings": [classify_run(r, a.budget) for r in runs]}
    if a.selfcheck and not a.no_synth:
        res["synthetic"] = synthetic_arms()
    if a.selfcheck:
        by = {r["run"]: r for r in res["readings"]}
        pos_ok = all(by[r]["rc"] == 0 for r in exp["PASS_RUNS"] if r in by)
        neg_runs = [by[r] for r in exp["FAIL_RUNS"] if r in by]
        neg_nongreen = all(r["rc"] != 0 for r in neg_runs)
        neg_named = [r["run"] for r in neg_runs if r["rc"] == 1 and r.get("n_failed_predicates")]
        syn = {s["run"]: s["rc"] for s in res.get("synthetic", [])}
        syn_ok = (syn.get("SYN/POS_correct_impl") == 0 and syn.get("SYN/NEG_always_lose") == 1
                  and syn.get("SYN/NEG_over_budget") == 1 and syn.get("SYN/INSTR_dead_process") == 2)
        res["teeth"] = {"POS_all_pass_runs_rc0": pos_ok, "NEG_all_fail_runs_nongreen": neg_nongreen,
                        "NEG_named_predicate_runs": neg_named,
                        "synthetic_arms_rc": syn, "synthetic_ok": syn_ok,
                        "pass": bool(pos_ok and neg_nongreen and len(neg_named) >= 1 and syn_ok),
                        "rule": ("通过跑次（机取）⇒ rc=0 ∧ 失败跑次（机取）⇒ rc≠0 ∧ ≥1 个失败跑次 rc=1 且逐谓词点名 "
                                 "∧ 合成四臂 = {正控 rc0 / 恒 LOSE rc1 / 超预算 rc1 / 探针不可解析 rc2}")}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    for r in res["readings"]:
        print("%-20s rc=%s failed=%s %s" % (r["run"], r["rc"], r.get("n_failed_predicates"),
              {k: v["n_viol"] for k, v in r.get("predicates", {}).items() if not v["pass"]}))
    for s in res.get("synthetic", []):
        print("%-24s rc=%s failed=%s" % (s["run"], s["rc"], s.get("n_failed_predicates")))
    if a.selfcheck:
        print("TEETH", json.dumps({k: v for k, v in res["teeth"].items() if k != "NEG_named_predicate_runs"},
                                  ensure_ascii=False))
    print("wrote", a.out)
    return 0 if (not a.selfcheck or res["teeth"]["pass"]) else 1


if __name__ == "__main__":
    sys.exit(main())
