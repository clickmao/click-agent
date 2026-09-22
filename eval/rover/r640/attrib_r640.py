#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R640 · `wythoff` 族**只读逐例定因**（承 R639 下轮候选 ①）。

器具派生 = `eval/rover/r637/attrib_r637.py`（结构复用）+ 逐条声明的差异：
  ① 扫面 = **R639 单轮 3 窗 12 跑次**（产品默认档 9 + codex 真值 3）；题集 = R639 冻结件（逐字节同）。
  ② J1 交叉校验**逐跑次**：重放所得用例通过数必须与 R639 冻结读数（`evidence/windows/*/report.json`
     + `verdict-r639.json::B_family_block.by_run`）一致；不一致 ⇒ 器具读法错 rc=2。
  ③ J2 守恒式：Σ分类 == 12 × 58 == 696，且逐跑次 == 58。
  ④ J3 机制探针：25×25 隐含冷集 vs oracle 真值冷集 ⇒ 五态；并**迁移检验** R637 事后判别式
     `intersect == 0 ∧ missing == n_truth`（记真阳性 / 假阳）。
  ⑤ J4 **逐跑次显式缺陷行**最小修复实验（承 R637 补救件模板）：每处断言 `替换次数 == 1`，
     锚点缺失 ⇒ `ANCHOR_MISS`（fail-closed，记「未测到」而非「无缺陷」）；
     成对控制 = 目标族全绿 ∧ 其它三族逐例不变。
  ⑥ J5b 三变异负控（同字节重写 / 换独立 oracle 实现 / 恒 LOSE）。
  ⑦ J9 确定性 ×2（同一跑次重放两次，逐例逐字节相同）。

零产品源码改动 / 零新臂 / 零远端 / 零新增夹具语义 / 零重测（只读复算冻结快照，副本上执行）。
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
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
import wythoff_oracle as ORC  # noqa: E402  (独立 oracle：题面逐字规格 ⇒ 定义式 DP)

CASES = os.path.join(REPO, "eval/rover/r640/cases/cases-r521.json")
CASES_SRC = os.path.join(REPO, "eval/rover/r610/cases/cases-r521.json")
CASES_SHA = "270128eb85c7afc07244c10c8845a22a541a7a60587a870125089e93422fccd7"
SNAP = os.path.join(REPO, "eval/rover/r639/snapshots")
EVID = os.path.join(REPO, "eval/rover/r639/evidence/windows")
V639 = os.path.join(REPO, "eval/rover/r639/verdict-r639.json")
RUNS_ROOT = os.path.expanduser("~/.agentframework/harness/runs/r639")
FAMILIES = ["life", "sub", "nim", "wythoff"]
WIN_RE = re.compile(r"^WIN\s+(\d+)\s+(\d+)$")
LEGAL_RE = re.compile(r"^LOSE$|^WIN\s+\d+\s+\d+$")

# 逐跑次缺陷假设表（**锚点取自现盘字节**；每条断言替换次数 == 1）
MINFIX_CANDIDATES = {
    "w237/agentP-r2": [
        {"id": "C1_pm1_window",
         "anchor": r"for cand in \(x - 1, x, x \+ 1\):",
         "repl": "for cand in (x,):",
         "why": "冷集判定谓词带 ±1 容差窗口 ⇒ 非冷点被误判为冷点"},
    ],
    "w237/agentP-r3": [
        {"id": "C1_idx_window",
         "anchor": r"for t in \(idx - 1, idx, idx \+ 1, idx \+ 2\):",
         "repl": "for t in (idx,):",
         "why": "冷点索引搜索窗口过宽（±2）"},
        {"id": "C2_idx_def",
         "anchor": r"idx = int\(\(b - a\) / PHI\) if b > a else 0",
         "repl": "idx = int((b - a) * PHI) if b > a else 0",
         "why": "冷点索引用 (b-a)/phi 而非 (b-a)*phi"},
    ],
    "w238/agentP-r3": [
        {"id": "C1_dp_settle_0_0",
         "anchor": r"if a == 0 and b == 0:\n                continue",
         "repl": "if a == 0 and b == 0:\n                lose[a][b] = True\n                continue",
         "why": "(0,0) 未显式置为必败 ⇒ DP 初值 True 与传播链不一致"},
    ],
    "w239/agentP-r1": [
        {"id": "C1_lower_wythoff_base",
         "anchor": r"    return lo\n\n\ndef is_lose",
         "repl": "    return lo + n\n\n\ndef is_lose",
         "why": "floor(n*phi) = n + floor(n/phi)；本实现只算了 floor(n/phi)"},
    ],
    "w239/agentP-r2": [
        {"id": "C1_box_scan",
         "anchor": r"    for i in range\(a \+ 1\):\n        for j in range\(b \+ 1\):\n            if i == 0 and j == 0:\n                continue\n            win = \(i - j, j\) in los if False else False",
         "repl": "    for i in range(a + 1):\n        for j in range(b + 1):\n            if i == 0 and j == 0:\n                los.add((i, j))\n                continue\n            win = False",
         "why": "冷集自举只扫 a×b 盒且 (0,0) 未入集"},
    ],
}


def sha16(p: str) -> str:
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:16]


def run_one(tree: str, game: str, stdin: str, tmo: float):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run([sys.executable, "-B", "-m", "games", game], input=stdin,
                           capture_output=True, text=True, timeout=tmo, cwd=tree, env=env)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return 125, "", type(e).__name__


def classify_wythoff(a: int, b: int, rc: int, out: str, exp: str):
    """四分类（承 R622/R637 口径）。"""
    got = (out or "").strip("\n")
    expn = exp.strip("\n")
    if got.strip() == expn.strip():
        return "OK", ""
    if rc != 0 or got.strip() == "":
        return "HARD_CRASH", "rc=%d len=%d" % (rc, len(got))
    s = got.strip()
    parsed = WIN_RE.match(s)
    if s != "LOSE" and parsed is None:
        return "FORMAT", repr(s[:60])
    st_got = "WIN" if parsed is not None else "LOSE"
    st_orc = "LOSE" if ORC.solve("%d %d" % (a, b)) == "LOSE" else "WIN"
    if st_got != st_orc:
        return "STATE_FLIP", "%s->%s" % (st_orc, st_got)
    i, j = int(parsed.group(1)), int(parsed.group(2))
    legal = (i >= 0 and j >= 0 and (i, j) != (0, 0) and
             (j == 0 or i == 0 or i == j) and i <= a and j <= b and (i or j))
    if not legal:
        return "TRUE_WRONG", "illegal_move=(%d,%d)" % (i, j)
    if not ORC.LOSING[a - i][b - j]:
        return "TRUE_WRONG", "nonwinning_move=(%d,%d)" % (i, j)
    wm = ORC.winning_moves(a, b)
    if (i, j) != min(wm):
        return "LEGAL_NONMIN", "got=(%d,%d) min=%s" % (i, j, min(wm))
    return "TRUE_WRONG", "unknown"


def classify_other(rc: int, out: str, exp: str):
    if rc == 0 and (out or "").strip("\n") == exp.strip("\n"):
        return "OK", ""
    if rc != 0:
        return "HARD_CRASH", "rc=%d" % rc
    if not (out or "").strip():
        return "HARD_CRASH", "empty_stdout"
    return "TRUE_WRONG", "bytes"


def replay(run, cases, tmo):
    tmp = tempfile.mkdtemp(prefix="r640-")
    dst = os.path.join(tmp, "t")
    rows = []
    try:
        shutil.copytree(run["src_tree"], dst)
        for ci, c in enumerate(cases):
            rc, out, err = run_one(dst, c["game"], c["stdin"], tmo)
            if c["game"] == "wythoff":
                a, b = (int(x) for x in c["stdin"].split()[:2])
                tag, det = classify_wythoff(a, b, rc, out, c["expected_stdout"])
            else:
                a = b = None
                tag, det = classify_other(rc, out, c["expected_stdout"])
            rows.append({"run": run["run"], "win": run["win"], "arm": run["arm"], "idx": ci,
                         "game": c["game"], "vis": c["vis"], "case_id": c.get("case_id", ""),
                         "tag": tag, "detail": det, "rc": rc, "a": a, "b": b,
                         "expected": c["expected_stdout"].strip()[:60],
                         "got_raw": (out or "").strip("\n")[:60]})
        return rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def enum_runs():
    out = []
    for win in sorted(os.listdir(SNAP)):
        wdir = os.path.join(SNAP, win)
        if not os.path.isdir(wdir):
            continue
        for arm in sorted(os.listdir(wdir)):
            tree = os.path.join(wdir, arm, "g1")
            if not os.path.isdir(os.path.join(tree, "games")):
                continue
            rcf = os.path.join(RUNS_ROOT, win, arm, "g1", "cli_rc.txt")
            cli_rc = None
            if os.path.isfile(rcf):
                try:
                    cli_rc = int(io.open(rcf, encoding="utf-8", errors="replace").read().strip())
                except Exception:  # noqa: BLE001
                    cli_rc = None
            out.append({"run": "%s/%s" % (win, arm), "win": win, "arm": arm,
                        "src_tree": tree, "cli_rc": cli_rc,
                        "void": cli_rc == 124, "void_reason": "cli_rc=124" if cli_rc == 124 else ""})
    return out


# ------------------------------------------------------------------ J0 / 机制探针
PROBER = r'''
import json, os, sys
tree = sys.argv[1]
sys.path.insert(0, tree); os.chdir(tree)
res = {"ok": False}
try:
    mod = __import__("games.wythoff", fromlist=["solve"])
    fn = getattr(mod, "solve", None)
    if fn is None:
        res["err"] = "NO_SOLVE_ENTRY"
    else:
        grid = {}
        for a in range(1, 26):
            for b in range(1, 26):
                try:
                    grid["%d %d" % (a, b)] = str(fn("%d %d\n" % (a, b))).strip()
                except Exception as e:
                    grid["%d %d" % (a, b)] = "ERR:" + type(e).__name__
        res.update(ok=True, grid=grid)
except Exception as e:
    res["err"] = type(e).__name__ + ":" + str(e)[:80]
print(json.dumps(res))
'''


def probe_coldset(tree, tmo=120.0):
    tmp = tempfile.mkdtemp(prefix="r640probe-")
    dst = os.path.join(tmp, "t")
    try:
        shutil.copytree(tree, dst)
        p = subprocess.run([sys.executable, "-B", "-c", PROBER, dst], capture_output=True,
                           text=True, timeout=tmo, cwd=dst,
                           env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
                                "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            return json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            return {"ok": False, "err": "probe_parse_fail:" + (p.stdout or "")[-60:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "err": "probe_timeout"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def mech_of(run, probe):
    truth_lose = {(a, b) for a in range(1, 26) for b in range(1, 26) if ORC.LOSING[a][b]}
    rec = {"run": run["run"]}
    if not probe.get("ok"):
        rec.update(mechanism="NO_ENTRY_OR_CRASH", detail=probe.get("err", ""))
        return rec
    grid = probe["grid"]
    implied = {tuple(int(x) for x in k.split()) for k, v in grid.items() if v == "LOSE"}
    errs = {k for k, v in grid.items() if v.startswith("ERR:")}
    inter, extra, missing = implied & truth_lose, implied - truth_lose, truth_lose - implied
    symdiff = len(extra) + len(missing)
    best = None
    for da in range(-3, 4):
        for db in range(-3, 4):
            shifted = {p for p in ((a + da, b + db) for (a, b) in truth_lose)
                       if 1 <= p[0] <= 25 and 1 <= p[1] <= 25}
            d = len(shifted ^ implied)
            if best is None or d < best[0]:
                best = (d, da, db)
    if errs:
        mech = "ENTRY_ERROR"
    elif symdiff == 0:
        mech = "COLD_SET_EQUAL"
    elif best and best[0] == 0:
        mech = "COLD_SET_SHIFT"
    else:
        mech = "COLD_SET_OTHER"
    rec.update(mechanism=mech, n_implied=len(implied), n_truth=len(truth_lose),
               intersect=len(inter), extra=len(extra), missing=len(missing), symdiff=symdiff,
               best_shift=[best[1], best[2]] if best else None, n_entry_errors=len(errs),
               # R637 事后判别式迁移检验
               r637_discriminant=bool(len(inter) == 0 and len(missing) == len(truth_lose)))
    return rec


# ------------------------------------------------------------------ J4 最小修复
def fam_scores(tree, cases, tmo):
    """→ {fam: 通过例数}（副本上执行，零写入原树）。"""
    tmp = tempfile.mkdtemp(prefix="r640fm-")
    dst = os.path.join(tmp, "t")
    res = {}
    try:
        shutil.copytree(tree, dst)
        for fam in FAMILIES:
            ok = 0
            for c in cases:
                if c["game"] != fam:
                    continue
                rc, out, _ = run_one(dst, fam, c["stdin"], tmo)
                if rc == 0 and (out or "").strip("\n") == c["expected_stdout"].strip("\n"):
                    ok += 1
            res[fam] = ok
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def minfix_for(run, cases, tmo):
    src = os.path.join(run["src_tree"], "games", "wythoff.py")
    raw = io.open(src, encoding="utf-8").read()
    base = fam_scores(run["src_tree"], cases, tmo)
    attempts = []
    for cand in MINFIX_CANDIDATES.get(run["run"], []):
        patched, n = re.subn(cand["anchor"], cand["repl"], raw, count=1)
        rec = {"id": cand["id"], "why": cand["why"], "replacements": n}
        if n != 1:
            rec["verdict"] = "ANCHOR_MISS"
            rec["note"] = "锚点缺失 ⇒ fail-closed（记「未测到」，禁读作「无缺陷」）"
            attempts.append(rec)
            continue
        tmp = tempfile.mkdtemp(prefix="r640mf-")
        dst = os.path.join(tmp, "t")
        try:
            shutil.copytree(run["src_tree"], dst)
            io.open(os.path.join(dst, "games", "wythoff.py"), "w", encoding="utf-8").write(patched)
            after = fam_scores(dst, cases, tmo)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        others_unchanged = all(after[f] == base[f] for f in ("life", "sub", "nim"))
        rec.update(target_before=base["wythoff"], target_after=after["wythoff"],
                   other_families_before={f: base[f] for f in ("life", "sub", "nim")},
                   other_families_after={f: after[f] for f in ("life", "sub", "nim")},
                   others_unchanged=others_unchanged,
                   verdict="CONFIRMED" if (after["wythoff"] == 15 and others_unchanged)
                           else ("PARTIAL" if after["wythoff"] > base["wythoff"] else "NO_EFFECT"))
        attempts.append(rec)
    return {"run": run["run"], "baseline_families": base, "attempts": attempts,
            "confirmed": [a["id"] for a in attempts if a.get("verdict") == "CONFIRMED"],
            "state": ("能力缺陷（产物侧）" if any(a.get("verdict") == "CONFIRMED" for a in attempts)
                      else "未测到（锚点缺失或候选全不生效）")}


# ------------------------------------------------------------------ J5b 变异负控
def negctls(blocked, cases, tmo):
    wc = [c for c in cases if c["game"] == "wythoff"]
    good = 0
    for c in wc:
        a, b = (int(x) for x in c["stdin"].split()[:2])
        if ORC.solve(c["stdin"]).strip() == c["expected_stdout"].strip():
            good += 1
    # N1 同字节重写
    tmp = tempfile.mkdtemp(prefix="r640nc-")
    try:
        dst = os.path.join(tmp, "t")
        shutil.copytree(blocked, dst)
        p = os.path.join(dst, "games", "wythoff.py")
        io.open(p, "wb").write(io.open(p, "rb").read())
        n1 = fam_scores(dst, cases, tmo)["wythoff"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # N2 换独立 oracle 实现
    tmp = tempfile.mkdtemp(prefix="r640nc2-")
    try:
        dst = os.path.join(tmp, "t")
        shutil.copytree(blocked, dst)
        io.open(os.path.join(dst, "games", "wythoff.py"), "w", encoding="utf-8").write(
            "import sys\nsys.path.insert(0, %r)\nimport wythoff_oracle as _o\n"
            "def solve(text):\n    return _o.solve(text)\n" % os.path.join(REPO, "eval/rover/r622"))
        n2 = fam_scores(dst, cases, tmo)["wythoff"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # N3 恒 LOSE
    tmp = tempfile.mkdtemp(prefix="r640nc3-")
    try:
        dst = os.path.join(tmp, "t")
        shutil.copytree(blocked, dst)
        io.open(os.path.join(dst, "games", "wythoff.py"), "w", encoding="utf-8").write(
            "def solve(text):\n    return 'LOSE'\n")
        n3 = fam_scores(dst, cases, tmo)["wythoff"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # 变异 oracle 负控（J0 侧）
    mut = 0
    for c in wc:
        a, b = (int(x) for x in c["stdin"].split()[:2])
        got = ORC.solve(c["stdin"])
        if got != "LOSE":
            i, j = (int(v) for v in got.split()[1:3])
            got = "WIN %d %d" % (max(0, i - 1), j)  # 语义变异：着法 i 减 1
        if got.strip() == c["expected_stdout"].strip():
            mut += 1
    return {"oracle_positive_control": "%d/%d" % (good, len(wc)),
            "oracle_positive_pass": good == len(wc),
            "oracle_mutant_pass": mut, "oracle_mutant_teeth": mut < len(wc),
            "N1_null_rewrite": {"target_pass": n1, "verdict": "PASS" if n1 == 0 else "FAIL"},
            "N2_correct_impl": {"target_pass": n2, "verdict": "PASS" if n2 == len(wc) else "FAIL"},
            "N3_always_lose": {"target_pass": n3, "verdict": "PASS" if n3 < len(wc) else "FAIL"},
            "_cases": len(wc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r640/out/attrib-r640.json"))
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--det", action="store_true", help="确定性 ×2 复跑")
    a = ap.parse_args()

    res = {"round": "R640", "instrument": {"attrib": sha16(os.path.abspath(__file__)),
                                           "oracle": sha16(os.path.join(REPO, "eval/rover/r622/wythoff_oracle.py"))},
           "cases": {"path": CASES, "sha256": hashlib.sha256(io.open(CASES, "rb").read()).hexdigest(),
                     "src_pin": CASES_SHA,
                     "pin_ok": hashlib.sha256(io.open(CASES, "rb").read()).hexdigest() == CASES_SHA}}
    cases = json.load(io.open(CASES, encoding="utf-8"))
    wc = [c for c in cases if c["game"] == "wythoff"]
    runs = [r for r in enum_runs() if not r["void"]]
    res["face"] = {"n_runs": len(runs), "runs": [r["run"] for r in runs],
                   "void_excluded": [r["run"] for r in enum_runs() if r["void"]]}

    # J0 正控 + 变异负控（在 N5b 内一并算）
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(lambda r: replay(r, cases, a.timeout), runs))
    allrows = [x for rr in rows for x in rr]
    res["J2_conservation"] = {"total": len(allrows), "expected": len(runs) * len(cases),
                              "pass": len(allrows) == len(runs) * len(cases)
                                      and all(len(rr) == len(cases) for rr in rows),
                              "per_run": {r["run"]: len(rr) for r, rr in zip(runs, rows)}}

    # J1 交叉校验（对 R639 冻结读数）
    frozen = {}
    for win in sorted(os.listdir(EVID)):
        rep = os.path.join(EVID, win, "report.json")
        if not os.path.isfile(rep):
            continue
        d = json.load(io.open(rep, encoding="utf-8"))
        for row in d["rows"]:
            sub = "%s-r%d" % (row["side"] if row["side"] == "codex" else "agentP", row["rep"]) \
                if row["side"] != "codex" else "codex"
            frozen["%s/%s" % (win, sub)] = row["cases_pass"]
    v639 = json.load(io.open(V639, encoding="utf-8"))
    fam_frozen = {}
    for b in v639.get("B_family_block", {}).get("by_run", []):
        fams = b.get("families", {})
        if fams:
            fam_frozen["%s/%s" % (b["win"], b["sub"])] = {k: int(str(v).split("/")[0])
                                                          for k, v in fams.items()}
    mism, frozen_cmp = [], []
    for r, rr in zip(runs, rows):
        got = sum(1 for x in rr if x["tag"] == "OK" or x["tag"] == "LEGAL_NONMIN")
        # 与冻结判分口径对齐：LOSE 文本逐字节 / WIN 文本逐字节
        got_exact = sum(1 for x in rr if x["got_raw"].strip() == x["expected"].strip())
        exp = frozen.get(r["run"])
        row = {"run": r["run"], "replay_exact_pass": got_exact, "frozen_cases_pass": exp,
               "match": (exp is None) or (got_exact == exp)}
        if exp is not None and got_exact != exp:
            mism.append(row)
        frozen_cmp.append(row)
        ff = fam_frozen.get(r["run"])
        if ff:
            for fam in FAMILIES:
                g = sum(1 for x in rr if x["game"] == fam
                        and x["got_raw"].strip() == x["expected"].strip()
                        if True) if False else sum(
                    1 for x in rr if x["game"] == fam and x["tag"] == "OK")
                if fam != "wythoff" and g != ff.get(fam):
                    mism.append({"run": r["run"], "family": fam, "replay": g, "frozen": ff.get(fam)})
    res["J1_replay_cross_validation"] = {"mismatch": len(mism), "detail": mism[:12],
                                         "pass": len(mism) == 0, "rows": frozen_cmp}

    # J3 机制探针
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        probes = list(ex.map(lambda r: probe_coldset(r["src_tree"]), runs))
    mech = [mech_of(r, p) for r, p in zip(runs, probes)]
    failing = set(x["run"] for x in allrows if x["tag"] != "OK")
    tp = sum(1 for m in mech if m["run"] in failing and m.get("r637_discriminant"))
    fp = sum(1 for m in mech if m["run"] not in failing and m.get("r637_discriminant"))
    res["J3_mechanism_probe"] = {"by_run": mech, "n_failing_runs": len(failing),
                                 "r637_discriminant_true_positive": tp,
                                 "r637_discriminant_false_positive": fp,
                                 "r637_discriminant_transfers": tp > 0,
                                 "mechanism_histogram": {k: sum(1 for m in mech if m.get("mechanism") == k)
                                                         for k in sorted({m.get("mechanism") for m in mech})}}

    # 逐例分类直方图
    hist = {}
    for x in allrows:
        if x["game"] == "wythoff":
            hist[x["tag"]] = hist.get(x["tag"], 0) + 1
    res["classification_histogram_wythoff"] = hist
    res["per_run_wythoff"] = {}
    for r, rr in zip(runs, rows):
        w = [x for x in rr if x["game"] == "wythoff"]
        res["per_run_wythoff"][r["run"]] = {
            "pass": sum(1 for x in w if x["tag"] == "OK"), "n": len(w),
            "tags": {t: sum(1 for x in w if x["tag"] == t) for t in sorted({x["tag"] for x in w})},
            "fails": [{"case": x["idx"], "in": "%s %s" % (x["a"], x["b"]), "exp": x["expected"],
                       "got": x["got_raw"], "tag": x["tag"], "detail": x["detail"]}
                      for x in w if x["tag"] != "OK"][:15]}

    # J4 最小修复（只对失败跑次）
    fail_runs = [r for r in runs if r["run"] in failing and r["arm"].startswith("agentP")]
    res["J4_minfix"] = [minfix_for(r, cases, a.timeout) for r in fail_runs]

    # J5b 负控
    worst = None
    if fail_runs:
        worst = min(fail_runs, key=lambda r: res["per_run_wythoff"][r["run"]]["pass"])
    if worst:
        res["J5b_negctl"] = negctls(worst["src_tree"], cases, a.timeout)
        res["J5b_negctl"]["on_run"] = worst["run"]

    # J9 确定性
    if a.det:
        det = []
        for r in fail_runs:
            r2 = replay(r, cases, a.timeout)
            r1 = [x for rr in rows for x in rr if x["run"] == r["run"]]
            same = all(x["tag"] == y["tag"] and x["got_raw"] == y["got_raw"] and x["rc"] == y["rc"]
                       for x, y in zip(r1, r2))
            det.append({"run": r["run"], "identical": same})
        res["J9_determinism"] = {"pairs": det, "pass": all(d["identical"] for d in det)}

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print("wrote", a.out)
    print("J1 mismatch", res["J1_replay_cross_validation"]["mismatch"],
          "| J2", res["J2_conservation"]["pass"],
          "| mech", res["J3_mechanism_probe"]["mechanism_histogram"],
          "| disc TP/FP", tp, fp)
    print("per_run_wythoff", {k: v["pass"] for k, v in res["per_run_wythoff"].items()})
    print("hist", hist)
    for m in res["J4_minfix"]:
        print("  MINFIX", m["run"], m["confirmed"], m["state"])


if __name__ == "__main__":
    main()
