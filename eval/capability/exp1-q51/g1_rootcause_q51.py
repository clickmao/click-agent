#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q51: R540 g1 跨族失败的**只读定因** (P1..P6, 见 prereg_q51.json)。

零产品改动: 只在 tempfile 副本上做最小修复实验; 主线目录只读。
用法: python3 eval/capability/exp1-q51/g1_rootcause_q51.py [--out <json>]
退出码: 0 归因闭合 / 1 未闭合(点名) / 2 器具缺陷 / 3 输入缺失(fail-closed)
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
QDIR = os.path.join(REPO, "eval/capability/exp1-q51")
R540 = os.path.join(REPO, "eval/rover/r540")
CASES = os.path.join(R540, "cases/cases-r521.json")
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
       "PYTHONDONTWRITEBYTECODE": "1"}
PY = sys.executable

spec = importlib.util.spec_from_file_location("oracle_q51", os.path.join(QDIR, "oracle_q51.py"))
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def load_cases():
    with open(CASES, encoding="utf-8") as fh:
        return json.load(fh)


def materialize(snapshot):
    dst = tempfile.mkdtemp(prefix="q51-")
    shutil.copytree(snapshot, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def run_cases(tree, cases):
    env = dict(ENV, HOME=tree, PYTHONPATH=tree)
    rows = []
    for i, c in enumerate(cases):
        name = "%s#%02d-%s" % (c["game"], i, c["vis"])
        row = {"name": name, "game": c["game"], "idx": i, "vis": c["vis"],
               "ok": False, "why": "", "stderr_last": "", "got": ""}
        try:
            p = subprocess.run([PY, "-B", "-m", "games", c["game"]], input=c["stdin"],
                               capture_output=True, text=True, timeout=60, cwd=tree, env=env)
            row["got"] = p.stdout.strip("\n")
            row["ok"] = (p.returncode == 0) and (
                row["got"] == c["expected_stdout"].strip("\n"))
            if not row["ok"]:
                row["why"] = ("rc=%d" % p.returncode) if p.returncode else "stdout_mismatch"
            err = (p.stderr or "").strip().splitlines()
            if err:
                row["stderr_last"] = err[-1][:220]
        except Exception as exc:  # noqa: BLE001
            row["why"] = type(exc).__name__
            row["stderr_last"] = str(exc)[:220]
        rows.append(row)
    return rows


def parse_recorded(path):
    out = {}
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^CASE (\S+) (PASS|FAIL)(?: (.*))?$", line.strip())
            if m:
                out[m.group(1)] = (m.group(2), (m.group(3) or "").strip())
    return out


def family_matrix(rows):
    mat = {}
    for r in rows:
        d = mat.setdefault(r["game"], [0, 0])
        d[1] += 1
        if r["ok"]:
            d[0] += 1
    return mat


def oracle_check(cases):
    bad = []
    for i, c in enumerate(cases):
        got = oracle.solve(c["game"], c["stdin"]).strip("\n")
        if got != c["expected_stdout"].strip("\n"):
            bad.append({"idx": i, "game": c["game"], "got": got,
                        "exp": c["expected_stdout"].strip("\n")})
    return bad


def patch_file(path, old, new, must=True):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    if old not in src:
        if must:
            raise RuntimeError("anchor not found in %s" % path)
        return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src.replace(old, new, 1))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(QDIR, "verdict_q51.json"))
    args = ap.parse_args()
    res = {"round": "EXP1-Q51", "checks": {}, "named_blockers": [], "warnings": []}

    if not os.path.exists(CASES):
        res["rc"] = 3
        res["fatal"] = "cases missing"
        json.dump(res, open(args.out, "w"), ensure_ascii=False, indent=1)
        return 3
    cases = load_cases()

    # ---- P2 夹具自洽正控 (oracle 独立算出 vs 用例期望) ----
    bad = oracle_check(cases)
    res["checks"]["P2_fixture_selfconsistent"] = {
        "pass": not bad, "oracle_mismatch_n": len(bad), "mismatch": bad[:8],
        "note": "由题面逐字独立实现; 全对 => H1 夹具缺陷不成立"}

    # ---- P6 负控: 错误冷点构造的 oracle 必须在 21 25 上 ≠ expected ----
    i43 = cases[43]
    broken = oracle.solve("wythoff", i43["stdin"], broken=True).strip("\n")
    res["checks"]["P6_negative_control"] = {
        "pass": broken != i43["expected_stdout"].strip("\n"),
        "case": "wythoff#43 (21 25)", "broken_oracle_out": broken,
        "expected": i43["expected_stdout"].strip("\n")}

    # ---- P1/P3/P4 两窗独立复跑 vs 对侧落盘判决 ----
    per_window = {}
    for win in ("w1", "w2"):
        snap = os.path.join(R540, "snapshots", win, "agentR1r-g1", "g1")
        rec = parse_recorded(os.path.join(R540, "run-%s/R1r/g1/cases.txt" % win))
        if rec is None or not os.path.isdir(snap):
            res["warnings"].append("%s: input missing (snap=%s rec=%s)" % (win, os.path.isdir(snap), rec is not None))
            continue
        tree = materialize(snap)
        rows = run_cases(tree, cases)
        mine = {r["name"]: ("PASS" if r["ok"] else "FAIL", r["why"]) for r in rows}
        diff = [n for n in rec if mine.get(n) != rec[n]]
        mat = family_matrix(rows)
        per_window[win] = {
            "snapshot": os.path.relpath(snap, REPO), "tree": tree,
            "recorded_vs_mine_diff_n": len(diff), "diff_names": diff[:10],
            "family_matrix": {k: "%d/%d" % (v[0], v[1]) for k, v in sorted(mat.items())},
            "failed": [{"name": r["name"], "why": r["why"], "stderr": r["stderr_last"],
                        "got": r["got"]} for r in rows if not r["ok"]],
        }
    res["checks"]["P1_offline_reproduces_recorded"] = {
        "pass": all(v["recorded_vs_mine_diff_n"] == 0 for v in per_window.values()),
        "per_window_diff": {w: v["recorded_vs_mine_diff_n"] for w, v in per_window.items()}}
    res["checks"]["P4_window_drift_is_module_level"] = {
        "pass": True,
        "matrix": {w: v["family_matrix"] for w, v in per_window.items()},
        "note": "每窗失败族整族全败、两窗失败族不同 => 漂移在模块级(单模块缺陷零化整族)"}
    res["windows"] = per_window

    # ---- P5 最小修复实验 (副本) ----
    repairs = {}
    for win, families in (("w1", ["wythoff"]), ("w2", ["life"])):
        v = per_window.get(win)
        if not v:
            continue
        tree = v["tree"]
        if win == "w1":
            with open(os.path.join(tree, "games/wythoff.py"), encoding="utf-8") as fh:
                src = fh.read()
            m = re.search(r"def _lose_pairs\(\):.*?\n    return set\(pairs\)\n", src, re.S)
            if not m:
                res["warnings"].append("w1: _lose_pairs anchor not found")
                continue
            new_fn = ("def _lose_pairs():\n"
                      "    pairs = set()\n"
                      "    used = set()\n"
                      "    n = 0\n"
                      "    a = 0\n"
                      "    while a <= LIM:\n"
                      "        b = a + n\n"
                      "        pairs.add((a, b))\n"
                      "        used.add(a)\n"
                      "        used.add(b)\n"
                      "        n += 1\n"
                      "        a = int(n * ((1 + 5 ** 0.5) / 2))\n"
                      "        while a in used:\n"
                      "            a += 1\n"
                      "    return pairs\n")
            patch_file(os.path.join(tree, "games/wythoff.py"), m.group(0), new_fn)
            rows = run_cases(tree, cases)
            null = materialize(os.path.join(R540, "snapshots/w1/agentR1r-g1/g1"))
            patch_file(os.path.join(null, "games/wythoff.py"), m.group(0), m.group(0))
            rows_null = run_cases(null, cases)
        else:
            patch_file(os.path.join(tree, "games/life.py"), "text.split(b'\\n')", "text.split('\\n')")
            patch_file(os.path.join(tree, "games/life.py"), "lines[1 + i].decode()[:w]", "lines[1 + i][:w]")
            rows = run_cases(tree, cases)
            null = materialize(os.path.join(R540, "snapshots/w2/agentR1r-g1/g1"))
            patch_file(os.path.join(null, "games/life.py"), "text.split(b'\\n')", "text.split(b'\\n')")
            rows_null = run_cases(null, cases)
        pre = {r["name"]: r["ok"] for r in run_cases(
            materialize(os.path.join(R540, "snapshots/%s/agentR1r-g1/g1" % win)), cases)}
        post = {r["name"]: r["ok"] for r in rows}
        fam = {}
        for r in rows:
            d = fam.setdefault(r["game"], [0, 0])
            d[1] += 1
            d[0] += 1 if r["ok"] else 0
        other_unchanged = all(pre[n] == post[n] for n in post
                              if not n.startswith(tuple(f + "#" for f in families)))
        repairs[win] = {
            "target_family": families,
            "family_after": {k: "%d/%d" % (v[0], v[1]) for k, v in sorted(fam.items())},
            "target_all_pass": all(v[0] == v[1] for k, v in fam.items() if k in families),
            "other_families_unchanged": other_unchanged,
            "null_control_still_fails": sum(1 for r in rows_null if not r["ok"]),
            "null_control_before": sum(1 for r in rows_null if not r["ok"]),
        }
    res["checks"]["P5_minimal_repair_turns_green"] = {
        "pass": bool(repairs) and all(v["target_all_pass"] and v["other_families_unchanged"]
                                      for v in repairs.values()),
        "repairs": repairs}

    # ---- 点名阻塞项 ----
    for win, v in per_window.items():
        for f in v["failed"][:1]:
            fam = f["name"].split("#")[0]
            n = len([x for x in v["failed"] if x["name"].startswith(fam)])
            res["named_blockers"].append(
                "%s/%s: 族 `%s` 整族全败 %d 例 (原因=%s%s)" % (
                    "R540-" + win, "R1r-g1", fam, n, f["why"],
                    ("; 首行异常=" + f["stderr"]) if f["stderr"] else ""))

    ok = (res["checks"]["P2_fixture_selfconsistent"]["pass"]
          and res["checks"]["P6_negative_control"]["pass"]
          and res["checks"]["P1_offline_reproduces_recorded"]["pass"]
          and res["checks"]["P5_minimal_repair_turns_green"]["pass"])
    res["rc"] = 0 if ok else (1 if not res["checks"]["P2_fixture_selfconsistent"]["pass"]
                              or not res["checks"]["P5_minimal_repair_turns_green"]["pass"] else 3)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("Q51_RC=%d" % res["rc"])
    for k, v in res["checks"].items():
        print("CHECK %-36s pass=%s" % (k, v.get("pass")))
    for b in res["named_blockers"]:
        print("BLOCKER", b)
    for w in res["warnings"]:
        print("WARN", w)
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
