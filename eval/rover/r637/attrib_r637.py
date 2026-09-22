#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R637 · `B_family_block` 整族归零的**只读逐例定因**（承 R636 下轮候选 ①）。

器具派生 = eval/rover/r622/attrib_r622.py（结构复用）+ 下列**逐条声明的差异**：
  ① 扫面 = **census 面 5 轮**（r631/r633/r634/r635/r636）全部跑次（非单轮 3 窗）；题集同 R636（r610 冻结件）。
  ② 判据 J1 新增：独立重放的**逐跑次族级分类**必须与 R636 冻结分类件**逐跑次一致**（交叉校验冻结读数）。
  ③ 判据 J3 新增：**三态归属**（构造缺陷 / 产物缺陷 / 判据缺陷）+ 守恒式（逐例一次且仅一次）。
  ④ 判据 J4 新增：**行为式机制探针**（经产物自身接口取 25×25 网格的隐含冷集，与独立 oracle 的 P 位集合比对）。
  ⑤ 判据 J5 新增：变异负控 **3 件成对**（null 重写 / 正确实现 / 恒 LOSE）+ **最小修复实验**（在副本上改一行，
     只重跑该副本 ⇒ 目标族转绿 ∧ 其它族逐例不变 ⇒ 缺陷归因到该行）。
  ⑥ 判据 J6：整族归零跑次确定性 ×2（逐例逐字节相同）。
  ⑦ VOID 前置剔除（`cli_rc == 124` 或树不存在）—— 承 R636 自捕 E2。

零产品源码改动 / 零新臂 / 零远端 / 零新增夹具语义 / 零重测（只读复算冻结快照）。
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

CASES = os.path.join(REPO, "eval/rover/r610/cases/cases-r521.json")
CASES_SHA = "270128eb85c7afc07244c10c8845a22a541a7a60587a870125089e93422fccd7"
ROUNDS = ["r631", "r633", "r634", "r635", "r636"]
FAMILIES = ["life", "sub", "nim", "wythoff"]
FAM_SIZE = {"life": 14, "sub": 14, "nim": 15, "wythoff": 15}
WIN_RE = re.compile(r"^WIN\s+(\d+)\s+(\d+)$")
HARNESS = os.path.expanduser("~/.agentframework/harness/runs")
CENSUS_R636 = os.path.join(REPO, "eval/rover/r636/family-block-census-r636.json")


def sha16(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()[:16]


def classify(a: int, b: int, rc: int, out: str, exp: str):
    """四分类（承 R622 口径，逐字节/形态/状态层）。"""
    got = (out or "").strip("\n")
    expn = exp.strip("\n")
    if got.strip() == expn.strip():
        return "OK", ""
    if rc != 0 or got.strip() == "":
        return "HARD_CRASH", "rc=%d len=%d" % (rc, len(got))
    s = got.strip()
    parsed = WIN_RE.match(s) if s != "LOSE" else None
    if s != "LOSE" and parsed is None:
        return "FORMAT", repr(s[:60])
    st_got = "WIN" if parsed is not None else "LOSE"
    st_orc = "LOSE" if ORC.solve("%d %d" % (a, b)) == "LOSE" else "WIN"
    if st_got != st_orc:
        return "STATE_FLIP", "%s->%s" % (st_orc, st_got)
    if parsed is None:
        return "TRUE_WRONG", "lose_not_bytewise"
    i, j = int(parsed.group(1)), int(parsed.group(2))
    wm = ORC.winning_moves(a, b)
    if (i, j) in wm:
        return "LEGAL_NONMIN", "got=(%d,%d) min=%s" % (i, j, min(wm))
    return "TRUE_WRONG", "illegal_or_nonwinning=(%d,%d)" % (i, j)


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


# ---------------------------------------------------------------- 跑次枚举
def enum_runs(rounds):
    """→ [{round,win,arm,src_tree,cli_rc,void,void_reason}]（快照树存在才算）"""
    out = []
    for rd in rounds:
        snaproot = os.path.join(REPO, "eval/rover", rd, "snapshots")
        runroot = os.path.join(HARNESS, rd)
        if not os.path.isdir(snaproot):
            continue
        for win in sorted(os.listdir(snaproot)):
            wdir = os.path.join(snaproot, win)
            if not os.path.isdir(wdir):
                continue
            for arm in sorted(os.listdir(wdir)):
                tree = os.path.join(wdir, arm, "g1")
                if not os.path.isdir(os.path.join(tree, "games")):
                    continue
                rcf = os.path.join(runroot, win, arm, "g1", "cli_rc.txt")
                cli_rc = None
                if os.path.isfile(rcf):
                    try:
                        cli_rc = int(io.open(rcf, encoding="utf-8", errors="replace").read().strip())
                    except Exception:  # noqa: BLE001
                        cli_rc = None
                void, reason = False, ""
                if cli_rc == 124:
                    void, reason = True, "cli_rc=124 (挂死)"
                out.append({"round": rd, "win": win, "arm": arm, "src_tree": tree,
                            "cli_rc": cli_rc, "void": void, "void_reason": reason})
    return out


def side_arm(arm: str):
    side = "codex" if arm.startswith("codex") else "agent"
    suffix = arm.split("-r")[-1] if "-r" in arm else "1"
    return side, arm.split("-r")[0], suffix


def replay_one(run, cases, tmo):
    """在一个**临时副本**上跑全部 58 例（零写入原树）。→ (run, rows)"""
    tmp = tempfile.mkdtemp(prefix="r637-")
    dst = os.path.join(tmp, run["arm"])
    try:
        shutil.copytree(run["src_tree"], dst)
        rows = []
        for ci, c in enumerate(cases):
            rc, out, err = run_one(dst, c["game"], c["stdin"], tmo)
            if c["game"] == "wythoff":
                a, b = (int(x) for x in c["stdin"].split()[:2])
                tag, detail = classify(a, b, rc, out, c["expected_stdout"])
            else:
                # 非 wythoff 族：只做「非空 + 逐字节」层判定（四分类的 wythoff 语义不适用）
                a = b = None
                if rc == 0 and (out or "").strip("\n") == c["expected_stdout"].strip("\n"):
                    tag, detail = "OK", ""
                elif rc != 0:
                    tag, detail = "HARD_CRASH", "rc=%d" % rc
                elif not (out or "").strip():
                    tag, detail = "HARD_CRASH", "empty_stdout"
                else:
                    tag, detail = "TRUE_WRONG", "bytes"
            rows.append({"round": run["round"], "win": run["win"], "arm": run["arm"],
                         "idx": ci, "game": c["game"], "vis": c["vis"], "tag": tag,
                         "detail": detail, "rc": rc, "a": a, "b": b,
                         "expected": c["expected_stdout"].strip()[:80],
                         "got": (out or "").strip()[:80],
                         "got_raw": (out or "").strip("\n")})
        return run, rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 机制探针
PROBER = r'''
import json, os, sys
tree = sys.argv[1]
sys.path.insert(0, tree)
os.chdir(tree)
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


def probe_coldset(tree, tmo=60.0):
    """经产物**自身接口**取 25×25 网格的隐含冷集（独立子进程；零写入原树）。"""
    tmp = tempfile.mkdtemp(prefix="r637probe-")
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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def mech_of(run, probe):
    truth_lose = {(a, b) for a in range(1, 26) for b in range(1, 26) if ORC.LOSING[a][b]}
    truth = {(a, b) for a in range(1, 26) for b in range(1, 26)}
    rec = {"run": "%s:%s/%s" % (run["round"], run["win"], run["arm"])}
    if not probe.get("ok"):
        rec.update(mechanism="NO_ENTRY_OR_CRASH", detail=probe.get("err", ""))
        return rec
    grid = probe["grid"]
    implied = {tuple(int(x) for x in k.split()) for k, v in grid.items() if v == "LOSE"}
    errs = {k for k, v in grid.items() if v.startswith("ERR:")}
    inter = implied & truth_lose
    extra = implied - truth_lose
    missing = truth_lose - implied
    symdiff = len(extra) + len(missing)
    # 平移假设：隐含冷集 == 真值集合按常数偏移平移（在网格内）
    best = None
    for da in range(-3, 4):
        for db in range(-3, 4):
            shifted = {(a + da, b + db) for (a, b) in truth_lose}
            shifted = {p for p in shifted if p in truth}
            d = len(shifted ^ implied)
            if best is None or d < best[0]:
                best = (d, da, db)
    if symdiff == 0:
        mech = "COLD_SET_EQUAL"
    elif errs:
        mech = "ENTRY_ERROR"
    elif best and best[0] == 0:
        mech = "COLD_SET_SHIFT"
    else:
        mech = "COLD_SET_OTHER"
    rec.update(mechanism=mech, n_implied=len(implied), n_truth=len(truth_lose),
               intersect=len(inter), extra=len(extra), missing=len(missing), symdiff=symdiff,
               best_shift=[best[1], best[2]] if best else None, n_entry_errors=len(errs))
    return rec


# ---------------------------------------------------------------- 变异负控
def negctl_and_minfix(blocked_tree, oracle_path, cases, tmo):
    """3 变异负控 + 最小修复实验（只在**副本**上改写目标行）。"""
    wcases = [c for c in cases if c["game"] == "wythoff"]
    base = tempfile.mkdtemp(prefix="r637nc-")
    res = {"_cases": len(wcases)}
    try:
        def build(name, wythoff_src=None, null_rewrite=False):
            tree = os.path.join(base, name)
            os.makedirs(os.path.join(tree, "games"))
            for f in os.listdir(os.path.join(blocked_tree, "games")):
                src = os.path.join(blocked_tree, "games", f)
                if os.path.isfile(src) and not f.endswith(".pyc"):
                    shutil.copy2(src, os.path.join(tree, "games", f))
            tgt = os.path.join(tree, "games", "wythoff.py")
            if null_rewrite:
                data = io.open(tgt, "rb").read()
                io.open(tgt, "wb").write(data)          # 同字节重写（负控：不得变绿）
            elif wythoff_src is not None:
                io.open(tgt, "w", encoding="utf-8").write(wythoff_src)
            return tree

        def eval_tree(tree):
            ok = 0
            tags = {}
            for c in wcases:
                a, b = (int(x) for x in c["stdin"].split()[:2])
                rc, out, _ = run_one(tree, "wythoff", c["stdin"], tmo)
                tag, _d = classify(a, b, rc, out, c["expected_stdout"])
                tags[tag] = tags.get(tag, 0) + 1
                ok += 1 if tag == "OK" else 0
            return ok, tags

        correct = ("import sys\nsys.path.insert(0, %r)\nimport wythoff_oracle as _o\n"
                   "def solve(text):\n    return _o.solve(text)\n") % os.path.dirname(oracle_path)
        always = "def solve(text):\n    return 'LOSE'\n"
        t_null = build("N1_null_rewrite", null_rewrite=True)
        t_corr = build("N2_correct_impl", wythoff_src=correct)
        t_alw = build("N3_always_lose", wythoff_src=always)
        ok_null, tags_null = eval_tree(t_null)
        ok_corr, tags_corr = eval_tree(t_corr)
        ok_alw, tags_alw = eval_tree(t_alw)
        res["N1_null_rewrite"] = {"ok": ok_null, "tags": tags_null,
                                  "verdict": "PASS" if ok_null == 0 else "FAIL",
                                  "rule": "同字节重写 ⇒ 失败例数须与原始跑次相同（非「凡改即绿」）"}
        res["N2_correct_impl"] = {"ok": ok_corr, "tags": tags_corr,
                                  "verdict": "PASS" if ok_corr == len(wcases) else "FAIL",
                                  "rule": "替换为独立 oracle 实现 ⇒ 15/15 全 OK（探针有牙、可转绿）"}
        res["N3_always_lose"] = {"ok": ok_alw, "tags": tags_alw,
                                 "verdict": "PASS" if ok_alw < len(wcases) else "FAIL",
                                 "rule": "恒 LOSE ⇒ 必被大量判红"}
        # --- 最小修复实验：只改一行（冷集生成器起点 0 → 1）---
        src_path = os.path.join(blocked_tree, "games", "wythoff.py")
        raw = io.open(src_path, encoding="utf-8").read()
        patched, n = re.subn(r"(\n\s*)nn = 0\b", r"\1nn = 1", raw, count=1)
        fix = {"applied": bool(n), "old_excerpt": None, "new_excerpt": None}
        if n:
            t_fix = build("N4_minfix", wythoff_src=patched)
            ok_fix, tags_fix = eval_tree(t_fix)
            # 其它族逐例不变（在副本上跑 58 例对照）
            def fam_pass(tree, fam):
                n = 0
                for c in cases:
                    if c["game"] != fam:
                        continue
                    rc, out, _ = run_one(tree, fam, c["stdin"], tmo)
                    if rc == 0 and (out or "").strip("\n") == c["expected_stdout"].strip("\n"):
                        n += 1
                return n

            other_ok = {}
            for fam in ("life", "sub", "nim"):
                o1 = fam_pass(t_fix, fam)
                o0 = fam_pass(blocked_tree, fam)
                other_ok[fam] = {"patched_pass": o1, "orig_pass": o0,
                                 "n": len([c for c in cases if c["game"] == fam]),
                                 "unchanged": o1 == o0}
            fix.update(n=len(wcases), ok=ok_fix, tags=tags_fix,
                       verdict="PASS" if ok_fix == len(wcases) else "FAIL",
                       other_families=other_ok,
                       target_line="games/wythoff.py 冷集生成器起点 `nn = 0` → `nn = 1`")
            io.open(os.path.join(REPO, "eval/rover/r637/out", "minfix-wythoff-r637.py"),
                    "w", encoding="utf-8").write(patched)
        res["N4_minfix_experiment"] = fix
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default=",".join(ROUNDS))
    ap.add_argument("--tmo", type=float, default=10.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r637/out/percase-r637.json"))
    ap.add_argument("--mech-out", default=os.path.join(REPO, "eval/rover/r637/out/probe-coldset-r637.json"))
    ap.add_argument("--negctl-out", default=os.path.join(REPO, "eval/rover/r637/out/negctl-r637.json"))
    ap.add_argument("--limit", type=int, default=0, help="调试用：只跑前 N 个跑次")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    cases = json.load(io.open(CASES, encoding="utf-8"))
    cs = sha16(CASES)
    runs = enum_runs(args.rounds.split(","))
    if args.limit:
        runs = runs[:args.limit]
    live = [r for r in runs if not r["void"]]
    void_runs = [r for r in runs if r["void"]]

    # J0 oracle 正控
    wcases = [c for c in cases if c["game"] == "wythoff"]
    ctrl = {"n": len(wcases), "match": 0, "mismatch": []}
    for c in wcases:
        got = ORC.solve(c["stdin"])
        if got.strip() == c["expected_stdout"].strip():
            ctrl["match"] += 1
        else:
            ctrl["mismatch"].append({"stdin": c["stdin"].strip(), "oracle": got,
                                     "expected": c["expected_stdout"]})
    ctrl["pass"] = ctrl["match"] == ctrl["n"]

    # 逐跑次重放
    rows, per_run = [], []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(replay_one, r, cases, args.tmo) for r in live]
        for fu in cf.as_completed(futs):
            run, rs = fu.result()
            rows.extend(rs)
            side, klass, rep = side_arm(run["arm"])
            fam = {}
            for f in FAMILIES:
                sel = [x for x in rs if x["game"] == f]
                fam[f] = {"n": len(sel), "pass": sum(1 for x in sel if x["tag"] == "OK")}
            per_run.append({"round": run["round"], "win": run["win"], "arm": run["arm"],
                            "src_tree": run["src_tree"],
                            "side": side, "klass": klass, "rep": rep,
                            "cases_pass": sum(1 for x in rs if x["tag"] == "OK"), "cases_total": len(rs),
                            "families": fam,
                            "family_block": [f for f in FAMILIES if fam[f]["n"] and fam[f]["pass"] == 0],
                            "partial_family": [f for f in FAMILIES
                                               if 0 < fam[f]["pass"] < fam[f]["n"]]})
    for p in per_run:
        p["klass_run"] = ("FAMILY_BLOCK" if p["family_block"]
                          else ("PARTIAL_FAMILY" if p["partial_family"] else "CLEAN"))
    # 检查点：重放面（最贵的一段）先落盘，后续节点崩了也不丢（增量落盘纪律）
    io.open(os.path.join(REPO, "eval/rover/r637/out/percase-r637-partial.json"), "w",
            encoding="utf-8").write(json.dumps(
                {"round": "R637", "stage": "replay-only", "runs": per_run, "rows": rows},
                ensure_ascii=False, indent=1))

    # J1 与 R636 冻结分类件交叉校验（同面 = r631/r633/r634/r635/r636）
    j1 = {"checked": 0, "mismatch": [], "frozen_scanned": []}
    if os.path.isfile(CENSUS_R636):
        cen = json.load(io.open(CENSUS_R636, encoding="utf-8"))
        frozen = {}
        for rd, blk in (cen.get("census", {}).get("by_round", {}) or {}).items():
            for r in blk.get("runs", []):
                frozen[(rd, r["win"], r["sub"])] = r["class"]
        j1["frozen_scanned"] = sorted({k[0] for k in frozen})
        for p in per_run:
            k = (p["round"], p["win"], p["arm"])
            if k in frozen:
                j1["checked"] += 1
                if frozen[k] != p["klass_run"]:
                    j1["mismatch"].append({"key": list(k), "frozen": frozen[k], "mine": p["klass_run"]})
        j1["pass"] = (j1["checked"] > 0 and not j1["mismatch"])
        j1["void_excluded"] = [{"round": v["round"], "win": v["win"], "arm": v["arm"],
                                "reason": v["void_reason"]} for v in void_runs]

    # J2/J3 逐例四分 + 三态归属
    non_ok = [r for r in rows if r["tag"] != "OK"]
    constr, crit, prod = [], [], []
    for r in non_ok:
        exp = r["expected"]
        if r["game"] == "wythoff":
            orc = ORC.solve("%d %d" % (r["a"], r["b"])).strip()
            orc_eq_exp = (orc == exp)
        else:
            orc, orc_eq_exp = None, True   # 非 wythoff 族：oracle 面未取证 ⇒ 不判构造缺陷
        if not orc_eq_exp:
            constr.append(r)
        elif r["game"] == "wythoff" and r["tag"] == "LEGAL_NONMIN":
            prod.append(r)                  # 题面明文要求字典序最小 ⇒ 产物缺陷
        else:
            prod.append(r)
    j3 = {"non_ok_total": len(non_ok), "product": len(prod), "construction": len(constr),
          "criterion": len(crit),
          "conservation_ok": len(prod) + len(constr) + len(crit) == len(non_ok),
          "product_fraction": round(len(prod) / len(non_ok), 4) if non_ok else None,
          "pass": (len(prod) + len(constr) + len(crit) == len(non_ok) and len(constr) == 0),
          "tag_hist": {}}
    for r in non_ok:
        j3["tag_hist"][r["tag"]] = j3["tag_hist"].get(r["tag"], 0) + 1

    # J4 机制探针（全跑次 + 干净对照）
    probe_runs = live
    probes, mech_cross = [], {}
    for r in probe_runs:
        pr = probe_coldset(r["src_tree"])
        rec = mech_of(r, pr)
        rec.update(round=r["round"], win=r["win"], arm=r["arm"])
        probes.append(rec)
    p_by_key = {(x["round"], x["win"], x["arm"]): x for x in probes}
    for p in per_run:
        m = p_by_key.get((p["round"], p["win"], p["arm"]), {}).get("mechanism", "?")
        mech_cross.setdefault(p["klass_run"], {}).setdefault(m, 0)
        mech_cross[p["klass_run"]][m] += 1
    blocked = [p for p in per_run if p["klass_run"] == "FAMILY_BLOCK"]
    clean = [p for p in per_run if p["klass_run"] == "CLEAN"]
    j4 = {"n_probed": len(probes), "cross_tab": mech_cross,
          "blocked_all_shift_or_inequal": all(
              (p_by_key.get((b["round"], b["win"], b["arm"]), {}).get("symdiff", 0) or 0) > 0
              for b in blocked) if blocked else None,
          "clean_control_equal": (sum(1 for c in clean
                                      if p_by_key.get((c["round"], c["win"], c["arm"]), {}).get(
                                          "mechanism") == "COLD_SET_EQUAL"), len(clean)),
          "blocked_runs": ["%s:%s/%s" % (b["round"], b["win"], b["arm"]) for b in blocked],
          "pass": bool(blocked) and all(
              (p_by_key.get((b["round"], b["win"], b["arm"]), {}).get("symdiff", 0) or 0) > 0
              for b in blocked)}

    # J5/J6 变异负控 + 最小修复 + 确定性 ×2
    j5 = {}
    if blocked:
        b = blocked[0]
        j5 = negctl_and_minfix(b["src_tree"], os.path.join(REPO, "eval/rover/r622/wythoff_oracle.py"),
                               cases, args.tmo)
    j6 = {"runs": [], "pass": None}
    for b in blocked:
        r1 = replay_one(b, cases, args.tmo)[1]
        r2 = replay_one(b, cases, args.tmo)[1]
        same = all(x["got_raw"] == y["got_raw"] and x["rc"] == y["rc"] and x["tag"] == y["tag"]
                   for x, y in zip(r1, r2)) and len(r1) == len(r2)
        j6["runs"].append({"run": "%s:%s/%s" % (b["round"], b["win"], b["arm"]),
                           "identical": same, "n_total": len(r1),
                           "ok": sum(1 for x in r1 if x["tag"] == "OK")})
    j6["pass"] = all(x["identical"] for x in j6["runs"]) if j6["runs"] else None

    res = {"round": "R637", "kind": "family-block-readonly-attribution",
           "cases_sha16": cs, "cases_pin_ok": cs == CASES_SHA[:16],
           "rounds_scanned": args.rounds.split(","),
           "oracle_control": ctrl, "void_excluded": j1.get("void_excluded", []),
           "runs": per_run, "rows": rows,
           "J1_census_reproduction": j1, "J2_J3_attribution": j3,
           "J4_mechanism": j4, "J5_negative_controls": j5, "J6_determinism": j6,
           "criteria_pass": {"J0": ctrl["pass"], "J1": j1.get("pass"),
                             "J2_residual_bucket_ok": j3["conservation_ok"],
                             "J3": j3["pass"], "J4": j4["pass"], "J5": None, "J6": j6["pass"]}}
    io.open(args.out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    io.open(args.mech_out, "w", encoding="utf-8").write(
        json.dumps({"round": "R637", "probes": probes, "cross_tab": mech_cross},
                   ensure_ascii=False, indent=1))
    if j5:
        io.open(args.negctl_out, "w", encoding="utf-8").write(json.dumps(j5, ensure_ascii=False, indent=1))

    print("J0 oracle 正控: %d/%d %s" % (ctrl["match"], ctrl["n"], "PASS" if ctrl["pass"] else "FAIL"))
    print("跑次: 活 %d / VOID 剔除 %d (%s)" % (len(live), len(void_runs),
                                              [v["arm"] for v in void_runs]))
    print("J1 census 交叉校验: checked=%d mismatch=%d pass=%s" % (j1.get("checked"), len(j1.get("mismatch", [])), j1.get("pass")))
    if j1.get("mismatch"):
        print("   mismatch:", json.dumps(j1["mismatch"][:5], ensure_ascii=False))
    print("J2/J3 逐例: 非OK %d = 产物 %d + 构造 %d + 判据 %d (守恒 %s) tags=%s"
          % (j3["non_ok_total"], j3["product"], j3["construction"], j3["criterion"],
             j3["conservation_ok"], json.dumps(j3["tag_hist"], ensure_ascii=False)))
    print("J4 机制 cross_tab:", json.dumps(mech_cross, ensure_ascii=False))
    print("    整族归零跑次:", j4["blocked_runs"], "| clean 对照 COLD_SET_EQUAL:", j4["clean_control_equal"])
    print("J5 变异负控:", json.dumps({k: (v if not isinstance(v, dict) else {kk: v[kk] for kk in v if kk in ("ok", "verdict", "applied", "n")}) for k, v in j5.items() if k != "_cases"}, ensure_ascii=False))
    print("J6 确定性 ×2:", json.dumps(j6, ensure_ascii=False))
    print("族级分类（逐跑次）:")
    for p in per_run:
        print("  %s %s %-12s %2d/%2d %-15s %s" % (p["round"], p["win"], p["arm"], p["cases_pass"],
                                                  p["cases_total"], p["klass_run"],
                                                  json.dumps({f: "%d/%d" % (p["families"][f]["pass"], p["families"][f]["n"]) for f in FAMILIES}, ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
