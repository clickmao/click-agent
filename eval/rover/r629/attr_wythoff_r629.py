#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R629 · 候选②：`wythoff` 族**逐例归因**（只读定因轮，行号级证据）。

只读、零产品源码改动、零新增夹具、零远端 LLM。数据面 = R628 在盘冻结快照
（`eval/rover/r628/snapshots/**`）+ 冻结题集（`eval/rover/r628/cases/cases-r521.json`）
+ R628 判据件（`~/.agentframework/harness/runs/r628/precond-r628.json`）。

四段（每段独立可判）：
  A 独立 oracle 正控   —— 与被测零共享代码（定义式按 a+b 升序的 retrograde DP，非冷点闭式）
                          ⇒ 必须与冻结期望 15/15 一致（否则「夹具缺陷」分支成立）。
  B 独立重放           —— 逐臂窗实跑产物模块（`python3 -B -m games wythoff`）
                          ⇒ 失败集必须与 R628 记录**逐字相同**（判据器可复现性）。
  C 机制归因（行为式） —— 12×12 穷举探针 ⇒ 逐模块错误集 ⇒ 机械化机制判断
                          （`TERMINAL_EXCLUDED` / `APPROX_COLD_SET` / `CRASH_NONE` / 其他）。
  D 最小修复 + null 重写 —— 在**副本**上只改被测缺陷行 ⇒ 目标例转绿且**回归 0**；
                          同字节重写 ⇒ 失败集不变（负控：非「凡改即绿」）。

退出码：0 = 全部读数齐备；2 = 器具缺陷（oracle/重放不可信）；3 = 输入缺失（fail-closed）。
"""

import argparse
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

def _repo_root(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.isdir(os.path.join(p, "eval", "rover")) and os.path.isdir(os.path.join(p, "src")):
            return p
        p = os.path.dirname(p)
    raise SystemExit("INPUT_MISSING repo root")


REPO = _repo_root(os.path.dirname(os.path.abspath(__file__)))
R628 = os.path.join(REPO, "eval", "rover", "r628")
CASES = os.path.join(R628, "cases", "cases-r521.json")
SNAPS = os.path.join(R628, "snapshots")
PRECOND = os.path.expanduser("~/.agentframework/harness/runs/r628/precond-r628.json")
ARMS = [("w220", "agentD-r1"), ("w220", "agentD-r2"), ("w220", "agentD-r3"), ("w220", "codex"),
        ("w221", "agentD-r1"), ("w221", "agentD-r2"), ("w221", "agentD-r3"), ("w221", "codex"),
        ("w222", "agentD-r1"), ("w222", "agentD-r2"), ("w222", "agentD-r3"), ("w222", "codex")]
DIAG = 12  # 12x12 exhaustive behaviour probe


# --------------------------------------------------------------------------
# A. 独立 oracle（与产物零共享代码；定义式 retrograde DP，非冷点闭式）
# --------------------------------------------------------------------------
def _dp(lim):
    """P/N 表：按 a+b 升序做 retrograde 分析（纯定义式，不用 phi/闭式）。"""
    tbl = [[None] * (lim + 1) for _ in range(lim + 1)]
    tbl[0][0] = "P"                      # 无着法可走 ⇒ 轮到者负（题面「取走最后一颗者胜」的终局）
    for s in range(0, 2 * lim + 1):
        for x in range(0, min(s, lim) + 1):
            y = s - x
            if y > lim:
                continue
            if x == 0 and y == 0:
                continue
            win = False
            for i in range(0, x + 1):
                for j in range(0, y + 1):
                    if i == 0 and j == 0:
                        continue
                    if not (i == 0 or j == 0 or i == j):   # 题面合法着法：单堆取 / 等量双取
                        continue
                    if tbl[x - i][y - j] == "P":
                        win = True
                        break
                if win:
                    break
            tbl[x][y] = "N" if win else "P"
    return tbl


def oracle(a, b, tbl):
    if tbl[a][b] == "P":
        return "LOSE"
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if tbl[a - i][b - j] == "P":
                return "WIN %d %d" % (i, j)   # 枚举序即字典序
    return "ERR"


# --------------------------------------------------------------------------
# 行为式机制判断（机械化；不靠读源码猜）
# --------------------------------------------------------------------------
def _parse_move(got):
    if not got.startswith("WIN"):
        return None
    try:
        _, i, j = got.split()
        return int(i), int(j)
    except ValueError:
        return None


def _illegal(i, j):
    """题面只允许：单堆取（i==0 或 j==0）或等量双取（i==j>0）。"""
    return i > 0 and j > 0 and i != j


def classify_behaviour(errs):
    """errs = 12x12 穷举中与 oracle 不符的 (a,b,got,exp) 列表。机械判定，不读源码猜。"""
    if not errs:
        return "CANONICAL"
    if any(g.startswith("<EXC") for _, _, g, _ in errs):
        return "CRASH_NONE"
    moves = [_parse_move(g) for _, _, g, _ in errs]
    if all(m is not None and _illegal(*m) for m in moves):
        return "ILLEGAL_MOVE"               # 状态谓词正确，但着法合法性未过滤
    pos = [(a, b) for a, b, _, _ in errs]
    if all(a == b for a, b in pos):
        return "TERMINAL_EXCLUDED"          # 只错对角线 ⇒ 漏「等量双取至 (0,0)」分支
    if any(a + b <= 3 for a, b in pos):
        return "APPROX_COLD_SET"            # 小数位置也错 ⇒ 冷点集为近似而非精确
    return "OTHER"


def probe_module(path, tbl, lim=DIAG):
    """在子进程里逐位置跑模块。子进程隔离 ⇒ 模块既有的 globals/副作用不串染。"""
    errs = []
    for a in range(1, lim + 1):
        for b in range(1, lim + 1):
            exp = oracle(a, b, tbl)
            code = ("import sys,importlib.util as u;"
                    "s=u.spec_from_file_location('m',%r);m=u.module_from_spec(s);s.loader.exec_module(m);"
                    "sys.stdout.write(m.solve('%d %d\\n'))" % (path, a, b))
            r = subprocess.run([sys.executable, "-B", "-c", code],
                               capture_output=True, text=True, timeout=30)
            got = r.stdout.strip()
            if r.returncode != 0:
                got = "<EXC %s>" % r.stderr.strip().splitlines()[-1][:90] if r.stderr.strip() else "<EXC rc=%d>" % r.returncode
            if got != exp:
                errs.append((a, b, got, exp))
    return errs


def run_cases_dir(d, cases):
    """逐用例实跑 `python3 -B -m games wythoff`（与被判链同调用形态）。"""
    fails = []
    for idx, c in cases:
        r = subprocess.run([sys.executable, "-B", "-m", "games", "wythoff"], input=c["stdin"],
                           capture_output=True, text=True, cwd=d, timeout=60)
        if r.stdout.strip() != c["expected_stdout"].strip():
            fails.append("wythoff#%d-%s" % (idx, c["vis"]))
    return fails


def src_lines(d, lo=None, hi=None):
    p = os.path.join(d, "games", "wythoff.py")
    if not os.path.exists(p):
        return []
    ls = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    return [{"line": n + 1, "text": t} for n, t in enumerate(ls)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r629/attribution-r629.json"))
    ap.add_argument("--nc", action="store_true", help="跑 null-rewrite 负控")
    a = ap.parse_args()

    missing = [p for p in (CASES, PRECOND) if not os.path.exists(p)]
    if missing:
        print("INPUT_MISSING %s" % missing)
        return 3

    raw_cases = json.load(io.open(CASES, encoding="utf-8"))
    cases = list(enumerate(raw_cases))
    wy = [(i, c) for i, c in cases if c["game"] == "wythoff"]
    tbl = _dp(60)

    out = {"schema": "r629-wythoff-attribution/1", "round": "R629",
           "readonly": True, "product_src_changed": False,
           "inputs": {"cases": CASES,
                      "cases_sha12": hashlib.sha256(io.open(CASES, "rb").read()).hexdigest()[:12],
                      "snapshots": SNAPS, "harness_precond": PRECOND}}

    # ---- A 独立 oracle 正控 ----
    oracle_rows, oracle_mismatch = [], []
    for idx, c in wy:
        aa, bb = [int(t) for t in c["stdin"].split()]
        got = oracle(aa, bb, tbl)
        exp = c["expected_stdout"].strip()
        oracle_rows.append({"case": "wythoff#%d-%s" % (idx, c["vis"]), "stdin": c["stdin"].strip(),
                            "fixture": exp, "independent_oracle": got, "agree": got == exp})
        if got != exp:
            oracle_mismatch.append(oracle_rows[-1])
    out["A_independent_oracle"] = {
        "algorithm": "retrograde DP by ascending a+b (definition-level; NOT the phi closed form used by products/codex)",
        "n_cases": len(wy), "agree": len(wy) - len(oracle_mismatch),
        "mismatches": oracle_mismatch, "rows": oracle_rows,
        "positive_control_pass": len(oracle_mismatch) == 0}

    # ---- B 独立重放 vs R628 记录 ----
    pre = json.load(io.open(PRECOND, encoding="utf-8"))
    recorded = {}
    for wn, wv in pre["windows"].items():
        for an, arm in wv["arms"].items():
            recorded[(wn, an.split("/")[0])] = arm.get("failed_cases") or []
    replay = []
    for wn, sub in ARMS:
        d = os.path.join(SNAPS, wn, sub, "g1")
        if not os.path.isdir(d):
            replay.append({"window": wn, "arm": sub, "error": "snapshot_missing"})
            continue
        fails = run_cases_dir(d, wy)
        rec = sorted(recorded.get((wn, sub), []))
        replay.append({"window": wn, "arm": sub, "replayed_failures": fails,
                       "harness_recorded": rec, "identical": sorted(fails) == rec,
                       "n_fail": len(fails),
                       "module_sha12": (hashlib.sha256(io.open(os.path.join(d, "games/wythoff.py"), "rb").read()).hexdigest()[:12]
                                        if os.path.exists(os.path.join(d, "games/wythoff.py")) else None)})
    n_ident = sum(1 for r in replay if r.get("identical"))
    out["B_independent_replay"] = {
        "arms": replay, "n_arms": len(replay), "n_identical": n_ident,
        "rule": "逐字节复现 R628 记录的失败集才算读数可用（判据器可复现性）",
        "pass": n_ident == len([r for r in replay if "error" not in r])}

    # ---- C 机制归因（行为式 12x12 穷举）----
    mech = []
    for wn, sub in ARMS:
        d = os.path.join(SNAPS, wn, sub, "g1")
        if not os.path.isdir(d):
            continue
        errs = probe_module(os.path.join(d, "games", "wythoff.py"), tbl)
        tag = classify_behaviour(errs)
        entry = {"window": wn, "arm": sub, "mechanism": tag, "n_exhaustive_errors": len(errs),
                 "error_positions": ["%d,%d" % (x, y) for x, y, _, _ in errs][:24],
                 "samples": [{"in": "%d %d" % (x, y), "got": g, "exp": e} for x, y, g, e in errs[:4]],
                 "src_lines": src_lines(d)}
        mech.append(entry)
    fam = {}
    for m in mech:
        fam.setdefault(m["mechanism"], []).append("%s/%s" % (m["window"], m["arm"]))
    out["C_mechanism"] = {"per_module": mech, "by_mechanism": fam,
                          "rule": "机制由 12x12 穷举错误集的结构机械判定（非读源码猜）"}

    # ---- D 最小修复 + null 重写（在副本上） ----
    target = ("w221", "agentD-r1")            # 失败集最小且形态单一（2 例，全对角线）
    src = os.path.join(SNAPS, target[0], target[1], "g1")
    anchor = "            if i == a and j == b:\n                continue\n"
    tmp = tempfile.mkdtemp(prefix="r629mr_")
    def clone(name):
        p = os.path.join(tmp, name)
        if os.path.exists(p):
            shutil.rmtree(p)
        shutil.copytree(src, p)
        return p
    base = clone("baseline")
    base_f = run_cases_dir(base, wy)
    rp = clone("minrepair")
    fp = os.path.join(rp, "games", "wythoff.py")
    s_orig = io.open(fp, encoding="utf-8").read()
    anchor_present = anchor in s_orig
    if anchor_present:
        io.open(fp, "w", encoding="utf-8").write(s_orig.replace(anchor, ""))
    mr_f = run_cases_dir(rp, wy)
    d = {"target_arm": "%s/%s" % target, "anchor_lines": anchor.splitlines(),
         "anchor_present": anchor_present,
         "baseline_failures": base_f, "minrepair_failures": mr_f,
         "fixed": sorted(set(base_f) - set(mr_f)), "regressed": sorted(set(mr_f) - set(base_f))}
    if a.nc:
        nr = clone("nullrewrite")
        nfp = os.path.join(nr, "games", "wythoff.py")
        io.open(nfp, "w", encoding="utf-8").write(s_orig)   # 同字节重写
        nr_f = run_cases_dir(nr, wy)
        d["nullrewrite_failures"] = nr_f
        d["nullrewrite_identical_to_baseline"] = sorted(nr_f) == sorted(base_f)
    out["D_minimal_repair"] = d
    shutil.rmtree(tmp, ignore_errors=True)

    # ---- 判据 ----
    K4_oracle = out["A_independent_oracle"]["positive_control_pass"]
    K4_replay = out["B_independent_replay"]["pass"]
    K4_repair = (d["anchor_present"] and len(d["regressed"]) == 0 and len(d["fixed"]) == len(d["baseline_failures"]) > 0)
    K4_null = d.get("nullrewrite_identical_to_baseline", None)
    rc = 0 if (K4_oracle and K4_replay) else 2
    out["verdict"] = {
        "rc": rc,
        "K4_oracle_fixture_consistent": K4_oracle,
        "K4_replay_byte_identical": K4_replay,
        "K4_minrepair_target_only": K4_repair,
        "K4_nullrewrite_negative_control": K4_null,
        "conclusion": ("夹具无缺陷（独立 oracle 15/15 复现冻结期望）∧ 判据器可复现（12/12 臂窗失败集逐字相同）"
                       if rc == 0 else "器具/输入不可信 ⇒ fail-closed"),
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("A oracle vs fixture      : %d/%d agree" % (out["A_independent_oracle"]["agree"], len(wy)))
    print("B replay vs harness      : %d/%d arms byte-identical" % (n_ident, len(replay)))
    print("C mechanism by module    : %s" % json.dumps(fam, ensure_ascii=False))
    print("D minrepair              : base=%d -> repaired=%d fixed=%s regressed=%s" %
          (len(base_f), len(mr_f), d["fixed"], d["regressed"]))
    if a.nc:
        print("D null-rewrite           : %s (identical=%s)" % (d["nullrewrite_failures"], d["nullrewrite_identical_to_baseline"]))
    print("rc=%d" % rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
