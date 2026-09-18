#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R570 离线复算: 把 R559/R560 的 9 窗 × 3 臂冻结快照**重新判分**成逐例矩阵。

零远端 · 零产品改动 · 零新增夹具: 复用两轮同一件的判分器 (sha a67215a7…) 与题集 (sha 270128eb…),
判分一律对**副本** (/tmp/r570/pc/…), 冻结快照零写入 (判分器会往被判树写 __pycache__ 等)。

输出: --out percase-matrix-r570.json
  { "grader_sha", "cases_sha", "sets": [...], "windows": { "w104": { "C1": {"pass": n, "cases": [{"idx","name","family","vis","ok","why"}]} } } }
失败语义 (fail-closed): 某 (窗,臂) 的 CASE 行数 != 58 或缺快照 => 记 "error", rc=2 (器具/输入缺陷), 不出判决。
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

REPO = "/home/agentuser/AgentFramework"
G = os.path.join(REPO, "eval/rover/r560/cases/run_cases_r521.py")
CASES = os.path.join(REPO, "eval/rover/r560/cases/cases-r521.json")
ERRSHA = "a67215a792845cb4a3adec4553c8d06211fa3a7a1dc1ec258ed9dbf3f6e59109"
CASSHA = "270128eb85c7afc07244c10c8845a22a541a7a60587a870125089e93422fccd7"
EXP_N = 58
SETS = [
    {"round": "R570", "snap": "eval/rover/r570/snapshots", "wins": ["w143", "w144", "w145", "w146", "w147", "w148"],
     "arms": ["C1", "R570E0", "R570E2"], "reports": "eval/rover/r570/evidence/windows"},
]
LINE = re.compile(r"^CASE (\S+) (PASS|FAIL)\s*(.*)$")


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default="/tmp/r570/pc")
    a = ap.parse_args()

    gs, cs = sha(G), sha(CASES)
    if gs != ERRSHA or cs != CASSHA:
        print("JOIN_FAIL grader_sha=%s cases_sha=%s (器具/题集漂移 => rc=2)" % (gs[:16], cs[:16]))
        return 2
    cases = json.load(io.open(CASES, encoding="utf-8"))
    assert len(cases) == EXP_N, len(cases)
    shutil.rmtree(a.work, ignore_errors=True)
    os.makedirs(a.work, exist_ok=True)

    out = {"round": "R570", "instrument": "matrix_r570.py", "grader": {"path": G, "sha256": gs},
           "cases": {"path": CASES, "sha256": cs, "n": len(cases)},
           "judging_on_copies": True, "sets": [], "windows": {}, "errors": []}
    for s in SETS:
        out["sets"].append({k: s[k] for k in ("round", "wins", "arms")})
        for w in s["wins"]:
            out["windows"][w] = {"round": s["round"]}
            for arm in s["arms"]:
                src = os.path.join(REPO, s["snap"], w, arm, "g1")
                if not os.path.isdir(src):
                    out["errors"].append({"win": w, "arm": arm, "err": "snapshot_missing", "path": src})
                    out["windows"][w][arm] = {"error": "snapshot_missing"}
                    continue
                dst = os.path.join(a.work, "%s-%s-%s" % (s["round"].lower(), w, arm))
                shutil.copytree(src, dst, symlinks=True)
                p = subprocess.run([sys.executable, "-I", "-B", G], cwd=dst, capture_output=True,
                                   text=True, timeout=900)
                rows, npass = [], 0
                for ln in p.stdout.splitlines():
                    m = LINE.match(ln.strip())
                    if not m:
                        continue
                    name, st, why = m.group(1), m.group(2), m.group(3)
                    npass += 1 if st == "PASS" else 0
                    i = int(name.split("#")[1].split("-")[0])
                    fam = name.split("#")[0]
                    rows.append({"idx": i, "name": name, "family": fam,
                                 "vis": cases[i]["vis"], "ok": st == "PASS", "why": why})
                rec = {"pass": npass, "total": len(rows), "rc": p.returncode, "rows": rows}
                if len(rows) != EXP_N:
                    rec["error"] = "case_lines=%d != %d (stderr=%s)" % (len(rows), EXP_N, p.stderr[-300:])
                    out["errors"].append({"win": w, "arm": arm, "err": rec["error"]})
                out["windows"][w][arm] = rec
                print("[%s %s] %d/%d rc=%d" % (w, arm, npass, len(rows), p.returncode), flush=True)

    # 复算一致性 (负控位 4): 与已落盘 report.json 逐窗 cases_pass 对齐
    xref = []
    for s in SETS:
        for w in s["wins"]:
            rp = os.path.join(REPO, s["reports"], w, "report.json")
            if not os.path.isfile(rp):
                xref.append({"win": w, "err": "report_missing"})
                continue
            rep = json.load(io.open(rp, encoding="utf-8"))
            for row in rep.get("rows", []):
                arm, got = row["arm"], row["cases_pass"]
                mine = out["windows"][w].get(arm, {})
                xref.append({"win": w, "arm": arm, "recorded": got, "recomputed": mine.get("pass"),
                             "agree": got == mine.get("pass")})
    out["xref_reports"] = xref
    out["xref_disagreements"] = [x for x in xref if x.get("agree") is False]
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    bad = len(out["errors"]) + len(out["xref_disagreements"])
    print("MATRIX windows=%d arm_windows=%d errors=%d xref=%d/%d agree" % (
        len(out["windows"]), sum(len(out["windows"][w]) - 1 for w in out["windows"]),
        len(out["errors"]), sum(1 for x in xref if x.get("agree")), len(xref)))
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
