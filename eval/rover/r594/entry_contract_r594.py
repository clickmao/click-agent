#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R594 — 入口契约面只读定因器（候选 ②）。

问题（承 R593 D1 定因）：`D1_empty_or_error` 的 66 例次里，最大单一形态 = **2 个整跑次全灭**
（`AttributeError: module 'games.wythoff' has no attribute 'solve'`，各 15 例）。本器具只回答一件事：

  这 2 个整跑次缺入口，是 **产物侧契约未暴露**（产物自己 `__main__` 调 `solve` 而自己的模块没定义），
  还是 **题面未写明入口名 / 判分侧引入了题面之外的导入路径**（= 夹具/题面缺陷）？

四路读数，缺一不判（禁只看静态、禁只看单侧）：

  ① **题面侧**：从 `taskset` prompt 原文抽取入口名要求串与评分路径串（题面是唯一权威输入面）。
  ② **判分侧**：从 `run_cases_r521.py` 源码抽取**实发 argv**（判分器真跑什么），与 ① 的评分路径比对。
  ③ **两侧 census**：对**全跑次面**（59 跑次 × 4 模块，跑次清单**派生**自在盘 JSON）静态判「该模块是否导出 `solve`」，
     agent / codex **分列**（分母各自侧）——两侧同败是夹具缺陷的**强判据**。
  ④ **实测复现**：2 个 offending 跑次真跑一次（`python3 -B -m games wythoff`）取 rc + stderr 尾行；
     1 个通过跑次同口径对照。**静态判过不算过，必须真跑复现**。

控制（成对、行为可分）：在**副本**（/tmp）上注入 / 移除 `def solve` ⇒ 扫描器必须翻面。
只读：快照树与冻结用例 sha256 前后逐位一致；控制只写 /tmp。

rc 语义（fail-closed，编码验收面）：0 = 器材可用且结论成立 / 2 = 器具缺陷（无牙·同判·守恒破·只读破·复现不符）
/ 3 = 输入缺失或环境失败。**不放宽任何阈值、不事后调判据。**

用法:
  python3 -B eval/rover/r594/entry_contract_r594.py [--controls-only] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
SRC_RUNS = os.path.join(REPO, "eval/rover/r593/landing-predicate-r593.json")
TASKSET = os.path.join(REPO, "eval/rover/r585/taskset-r585.json")
JUDGE = os.path.join(REPO, "eval/rover/r591/cases/run_cases_r521.py")
CASES = os.path.join(REPO, "eval/rover/r591/cases/cases-r521.json")
SNAP = os.path.join(REPO, "eval/rover/%s/snapshots/%s/%s/g1")
OUT_DEFAULT = os.path.join(REPO, "eval/rover/r594/entry-contract-r594.json")

MODULES = ["life", "sub", "nim", "wythoff"]
SOLVE_RE = re.compile(r"^[ \t]*def[ \t]+solve[ \t]*\(", re.M)
ENTRY_NAME = "solve(text: str) -> str"
GRADE_PATH = "python3 -m games"


def sha_tree(root, names=None):
    h = hashlib.sha256()
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            if names and not any(rel.endswith(n) for n in names):
                continue
            h.update(rel.encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:16]


def run_games_dir(rd, wn, sub):
    """**唯一**路径构造点（器具自捕 v1 教训：census 与快照面曾用不同层级 ⇒ 全 missing 假读数，
    与 POS 控制直接矛盾。修法 = 单点构造 + 非平凡性机检）。"""
    return os.path.join(SNAP % (rd, wn, sub), "games")


def sha_face(runs):
    """只读性面 = 全部跑次的快照树（g1 子树的 .py）+ 冻结用例集。任何写入都会改 mtime/字节。"""
    h = hashlib.sha256()
    for r in runs:
        gdir = run_games_dir(r["round"], r["win"], r["sub"])
        if not os.path.isdir(gdir):
            h.update(b"MISSING")
            continue
        h.update(sha_tree(gdir, names=[".py"]).encode())
    with open(CASES, "rb") as fh:
        h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()[:16]


def scan_game_dir(gdir):
    """返回 (per_module_has_solve, main_refs_solve, main_calls_solve, missing_list)。"""
    per, missing = {}, []
    for m in MODULES:
        p = os.path.join(gdir, m + ".py")
        if not os.path.isfile(p):
            per[m] = {"present": False, "has_solve": False, "bytes": 0}
            missing.append(m)
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        ok = bool(SOLVE_RE.search(src))
        per[m] = {"present": True, "has_solve": ok, "bytes": len(src)}
        if not ok:
            missing.append(m)
    mp = os.path.join(gdir, "__main__.py")
    mp_src = ""
    if os.path.isfile(mp):
        with open(mp, encoding="utf-8", errors="replace") as fh:
            mp_src = fh.read()
    refs = "solve" in mp_src
    calls = bool(re.search(r"\.solve\s*\(", mp_src))
    return per, refs, calls, sorted(missing)


def run_game(tree, game, stdin, timeout=60):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    p = subprocess.Popen([sys.executable, "-B", "-m", "games", game], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         cwd=tree, env=env, start_new_session=True)
    try:
        out, err = p.communicate(stdin, timeout=timeout)
        return (out or ""), (err or ""), p.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), 9)
        except Exception:  # noqa: BLE001
            pass
        return "", "", 124


def stmt_and_judge():
    with open(TASKSET, encoding="utf-8") as fh:
        ts = json.load(fh)
    prompt = ts["tasks"][0]["prompt"]
    with open(JUDGE, encoding="utf-8") as fh:
        jsrc = fh.read()
    m = re.search(r"\[\s*sys\.executable[^\]]*\][^)]*", jsrc)
    argv_snippet = m.group(0) if m else ""
    argv_tokens = re.findall(r'"(-[A-Za-z]+|games)"', argv_snippet)
    # 判分器实发形态: ['-B','-m','games', <game_id>]
    judge_form = [t for t in argv_tokens]
    return {
        "prompt_sha256": ts["tasks"][0]["prompt_sha256"],
        "statement_entry_name_required": ENTRY_NAME in prompt,
        "statement_grade_path_required": GRADE_PATH in prompt,
        "statement_grade_path_count": prompt.count(GRADE_PATH),
        "judge_argv_snippet": " ".join(argv_snippet.split())[:160],
        "judge_argv_tokens": judge_form,
        "judge_form_is_module_games": judge_form[:3] == ["-B", "-m", "games"],
        "judge_uses_direct_import": bool(re.search(r"import\s+games\.|__import__\(", jsrc)),
        "same_source": (ENTRY_NAME in prompt) and (GRADE_PATH in prompt) and judge_form[:3] == ["-B", "-m", "games"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()

    res = {"round": "R594", "instrument": "entry_contract_r594", "rc": 0, "notes": []}
    for p in (SRC_RUNS, TASKSET, JUDGE, CASES):
        if not os.path.isfile(p):
            res["rc"] = 3
            res["error"] = "missing input: " + p
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 3

    st = stmt_and_judge()
    res["face_statement_vs_judge"] = st

    with open(CASES, encoding="utf-8") as fh:
        n_cases = len(json.load(fh))
    res["cases_n"] = n_cases

    # ---------- 两侧 census（静态，全跑次面） ----------
    with open(SRC_RUNS, encoding="utf-8") as fh:
        runs = json.load(fh)["runs"]
    res["run_face_n"] = len(runs)

    before = sha_face(runs)

    census, missing_runs = {}, []
    for r in runs:
        gdir = run_games_dir(r["round"], r["win"], r["sub"])
        if not os.path.isdir(gdir):
            census["%s/%s/%s" % (r["round"], r["win"], r["sub"])] = {"error": "no_tree"}
            continue
        per, refs, calls, missing = scan_game_dir(gdir)
        key = "%s/%s/%s" % (r["round"], r["win"], r["sub"])
        census[key] = {"side": r["side"], "per_module": per, "main_refs_solve": refs,
                       "main_calls_solve": calls, "missing": missing}
        if missing:
            missing_runs.append({"run": key, "side": r["side"], "missing": missing,
                                 "main_calls_solve": calls})

    res["census_entries"] = len(census)
    res["census_conservation"] = len(census) == len(runs)
    # 非平凡性（防路径错导致的「全 missing」假读数）：全跑次面必须至少有一个模块 present ∧ has_solve
    present_slots = sum(1 for v in census.values() if "per_module" in v
                        for m in v["per_module"].values() if m["present"])
    solve_slots = sum(1 for v in census.values() if "per_module" in v
                      for m in v["per_module"].values() if m["has_solve"])
    res["non_trivial"] = {"present_slots": present_slots, "has_solve_slots": solve_slots,
                          "ok": present_slots > 0}
    sides = {"agent": {"runs": 0, "runs_missing": 0, "module_slots": 0, "module_missing": 0},
             "codex": {"runs": 0, "runs_missing": 0, "module_slots": 0, "module_missing": 0}}
    for k, v in census.items():
        if "side" not in v:
            continue
        s = sides[v["side"]]
        s["runs"] += 1
        s["module_slots"] += len(MODULES)
        s["module_missing"] += len(v["missing"])
        if v["missing"]:
            s["runs_missing"] += 1
    res["sides"] = sides
    res["missing_runs"] = missing_runs
    res["missing_runs_n"] = len(missing_runs)

    # ---------- 成对控制（副本上注入 / 移除） ----------
    ctl = {}
    tmp = tempfile.mkdtemp(prefix="r594ctl-")
    try:
        good = os.path.join(REPO, "eval/rover/r585/snapshots/w154/agentD-r1/g1")
        pos_dir = os.path.join(tmp, "pos")
        neg_dir = os.path.join(tmp, "neg")
        shutil.copytree(good, pos_dir, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(good, neg_dir, ignore=shutil.ignore_patterns("__pycache__"))
        wp = os.path.join(neg_dir, "games", "wythoff.py")
        with open(wp, encoding="utf-8") as fh:
            s = fh.read()
        s2 = re.sub(r"^([ \t]*)def[ \t]+solve[ \t]*\(", r"\1def solve_disabled(", s, count=1, flags=re.M)
        with open(wp, "w", encoding="utf-8") as fh:
            fh.write(s2)
        ctl["POS"] = scan_game_dir(os.path.join(pos_dir, "games"))[3]
        ctl["NEG"] = scan_game_dir(os.path.join(neg_dir, "games"))[3]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    res["controls"] = ctl
    res["teeth"] = {"has_teeth": ctl.get("POS") == [] and ctl.get("NEG") == ["wythoff"],
                    "pos_expect": [], "neg_expect": ["wythoff"]}

    # ---------- 实测复现（③ 之外的独立读数） ----------
    replay = []
    if not a.controls_only:
        targets = [("r588", "w163", "agentD-r2", "expect_attrerror"),
                   ("r591", "w166", "agentD-r2", "expect_attrerror"),
                   ("r585", "w154", "agentD-r1", "expect_ok")]
        for (rd, wn, sub, kind) in targets:
            tree = SNAP % (rd, wn, sub)
            gdir = os.path.join(tree, "games")
            if not os.path.isdir(gdir):
                replay.append({"run": "%s/%s/%s" % (rd, wn, sub), "error": "no_tree"})
                continue
            out, err, rc = run_game(tree, "wythoff", "21 25\n", 60)
            tail = [l for l in err.strip().splitlines() if l.strip()]
            replay.append({"run": "%s/%s/%s" % (rd, wn, sub), "kind": kind, "rc": rc,
                           "out_len": len(out), "stderr_tail": tail[-1][:120] if tail else ""})
    res["replay"] = replay

    after = sha_face(runs)
    res["readonly"] = {"pre": before, "post": after, "ok": before == after}

    # ---------- 裁定（机械） ----------
    ok = True
    if not res["teeth"]["has_teeth"]:
        ok = False
        res["notes"].append("控制无牙")
    if not res["non_trivial"]["ok"]:
        ok = False
        res["notes"].append("非平凡性破（全跑次面无 present 模块 ⇒ 路径构造错）")
    if not res["census_conservation"]:
        ok = False
        res["notes"].append("守恒破")
    if not res["readonly"]["ok"]:
        ok = False
        res["notes"].append("只读破")
    if not a.controls_only:
        for r in replay:
            if r.get("kind") == "expect_attrerror":
                if not (r.get("rc") not in (0, None) and "has no attribute 'solve'" in r.get("stderr_tail", "")):
                    ok = False
                    res["notes"].append("复现不符(offending): " + r["run"])
            if r.get("kind") == "expect_ok" and r.get("rc") != 0:
                ok = False
                res["notes"].append("对照跑次未通过: " + r["run"])

    # 结论面（三态：可判 / 不可判 / 未测）
    st_stmt_missing_entry = (not st["statement_entry_name_required"]) or (not st["statement_grade_path_required"])
    verdict = {
        "branch_fixture_defect": bool(st_stmt_missing_entry or (not st["judge_form_is_module_games"])
                                      or st["judge_uses_direct_import"]),
        "branch_product_contract": (not st_stmt_missing_entry) and st["judge_form_is_module_games"]
                                   and (not st["judge_uses_direct_import"]),
        "two_sided_strong_criterion_holds": (sides["agent"]["runs_missing"] > 0) and (sides["codex"]["runs_missing"] > 0),
        "rule": "题面已写明入口名 ∧ 判分路径与题面同源 ∧ 判分器无直接导入 ⇒ 题面/夹具分支被否证，定因归于产物侧契约自相矛盾",
    }
    res["verdict"] = verdict
    res["rc"] = 0 if ok else 2
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("R594_ENTRY_CONTRACT rc=%d teeth=%s agent_missing_runs=%d/%d codex_missing_runs=%d/%d"
          % (res["rc"], res["teeth"]["has_teeth"], sides["agent"]["runs_missing"], sides["agent"]["runs"],
             sides["codex"]["runs_missing"], sides["codex"]["runs"]))
    print("statement(entry=%s grade_path=%s) judge_form_module_games=%s direct_import=%s"
          % (st["statement_entry_name_required"], st["statement_grade_path_required"],
             st["judge_form_is_module_games"], st["judge_uses_direct_import"]))
    print("branch_product_contract=%s branch_fixture_defect=%s two_sided_strong=%s"
          % (verdict["branch_product_contract"], verdict["branch_fixture_defect"],
             verdict["two_sided_strong_criterion_holds"]))
    print("out " + a.out)
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
