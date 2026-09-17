#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 冻结器 + 汇总器 (承 R528): 产物**冻结进仓内不可变快照**后才判分 (R505 教训: 判分不得读活目录)。

按题族选用**独立判分器** (两条实现路径, 非同源):
  · tid=g1 (F1 锚) → `eval/rover/r519/grade_r519.py`      (R519 起沿用的判决器, 跨轮同源可比)
  · tid=t1 (F2 复用族) → `eval/rover/r529/grade_f2_r529.py` (承 R529 同一判据实现, 逐字节复用 ⇒ 判据不漂移)
产物: snapshots/<win>/<snapdir>/<tid>/** ; evidence/windows/<win>/{artifacts,report}.json ;
      evidence/windows/<win>/grade-<tag>-<tid>.json ; evidence/index-r531.json
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

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r531")
GRADER_BY_TID = {"g1": os.path.join(REPO, "eval/rover/r519/grade_r519.py"),
                 "t1": os.path.join(REPO, "eval/rover/r529/grade_f2_r529.py"),
                 "m1": os.path.join(REPO, "eval/rover/r531/grade_f3_r531.py")}
sys.path.insert(0, os.path.join(REPO, "eval/rover/r511"))
import usage_from_dumps as ufd  # noqa: E402


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def copy_tree(src, dst):
    files = []
    for root, dirs, fns in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in sorted(fns):
            if fn.endswith(".pyc"):
                continue
            sp = os.path.join(root, fn)
            rel = os.path.relpath(sp, src)
            tp = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(tp), exist_ok=True)
            shutil.copy2(sp, tp)
            files.append({"path": rel.replace(os.sep, "/"), "bytes": os.path.getsize(tp),
                          "sha256": sha256(tp)})
    return sorted(files, key=lambda r: r["path"])


def grade(tid, snapdir, out_path):
    g = GRADER_BY_TID[tid]
    p = subprocess.run([sys.executable, g, "--dir", snapdir, "--out", out_path],
                       capture_output=True, text=True)
    try:
        return json.load(io.open(out_path, encoding="utf-8")), p.returncode
    except Exception:
        return None, 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--window", default="w1")
    ap.add_argument("--adapter-dir", required=True)
    ap.add_argument("--map", action="append", default=[], help="<run>=<snapdir>")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    D, win = a.run_dir, a.window
    m = dict(x.split("=", 1) for x in a.map)
    snapwin = os.path.join(R, "snapshots", win)
    evwin = os.path.join(R, "evidence", "windows", win)
    if a.write:
        os.makedirs(snapwin, exist_ok=True)
        os.makedirs(evwin, exist_ok=True)

    rows, arts = [], []
    index = {"window": win, "run_dir": D, "round": "R531", "arms": {},
             "graders": {k: os.path.relpath(v, REPO) for k, v in GRADER_BY_TID.items()},
             "prereg": os.path.relpath(os.path.join(R, "prereg-r531.json"), REPO),
             "prereg_sha256": sha256(os.path.join(R, "prereg-r531.json")),
             "taskset": os.path.relpath(os.path.join(R, "taskset-r531.json"), REPO),
             "taskset_sha256": sha256(os.path.join(R, "taskset-r531.json"))}

    def emit(side, run, tid, worked, snapdir, extra, family):
        dst = os.path.join(snapwin, snapdir, tid)
        if a.write:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            os.makedirs(dst, exist_ok=True)   # R521 修复: 空产物树也必落盘 (缺臂不得被静默跳过)
            files = copy_tree(worked, dst)
        else:
            dry = os.path.join("/tmp", "r531_dry_" + snapdir)
            os.makedirs(dry, exist_ok=True)
            files = copy_tree(worked, dry)
        gpath = os.path.join(evwin, "grade-%s-%s.json" % (extra["tag"], tid))
        g = None
        if a.write:
            g, _grc = grade(tid, dst, gpath)
            assert g is not None, "判分器无输出: %s" % gpath
        arts.extend({"window": win, "arm": run, "side": side, "snapshot_dir": snapdir, "tid": tid,
                     "family": family, "path": f["path"], "bytes": f["bytes"]} for f in files)
        i0, i1 = extra["idx"]
        u = ufd.collect(a.adapter_dir, side, i0, i1) if i1 >= i0 else {"calls": 0}
        row = {"arm": extra["tag"], "run": run, "side": side, "tid": tid, "family": family,
               "all_pass": bool(g and g.get("rc") == 0), "cases_pass": (g or {}).get("passed"),
               "cases_total": (g or {}).get("total"),
               "failed": [c for c in (g or {}).get("cases", []) if not c["ok"]],
               "rc": extra.get("rc"), "elapsed_s": extra.get("elapsed_s"),
               "adapter_range": [i0, i1], "calls": u.get("calls"), "prompt_tokens": u.get("prompt_tokens"),
               "cached_tokens": u.get("cached_tokens"), "completion_tokens": u.get("completion_tokens"),
               "total_tokens": u.get("total_tokens"), "models": u.get("models"),
               "unreported_usage": u.get("unreported_usage"), "artifacts": len(files),
               "snapshot_empty": (len(files) == 0),
               "reply_chars": extra.get("reply_chars"), "ledger_steps": extra.get("ledger_steps"),
               "ledger_calls": extra.get("ledger_calls"),
               "usage": {k: u.get(k) for k in ("calls", "prompt_tokens", "cached_tokens",
                                               "completion_tokens", "total_tokens",
                                               "unreported_usage", "models")}}
        rows.append(row)
        index["arms"]["%s/%s" % (snapdir, tid)] = {"run": run, "side": side, "snapdir": snapdir, "tid": tid,
                                                   "family": family, "files_n": len(files), "files": files,
                                                   "grade": os.path.relpath(gpath, REPO),
                                                   "usage_range": [i0, i1], "calls": u.get("calls"),
                                                   "total_tokens": u.get("total_tokens")}
        print("冻结 %-18s side=%-6s cases=%s/%s calls=%s tok=%s" %
              ("%s/%s" % (snapdir, tid), side, (g or {}).get("passed"), (g or {}).get("total"),
               u.get("calls"), u.get("total_tokens")))

    ts = json.load(io.open(os.path.join(R, "taskset-r531.json"), encoding="utf-8"))
    fam_of = {t["tid"]: t.get("family") for t in ts["tasks"]}
    for arm_dir in sorted(os.listdir(D)):
        sr = os.path.join(D, arm_dir, "side-run.json")
        if not os.path.isfile(sr):
            continue
        side_j = json.load(io.open(sr, encoding="utf-8"))
        run = side_j["arm"]
        if run not in m:
            print("跳过 %s (未在 --map 声明快照目录)" % run)
            continue
        for t in side_j["tasks"]:
            tid = t["tid"]
            emit(side_j["side"], run, tid, os.path.join(D, arm_dir, tid, "work"), m[run],
                 {"tag": run, "idx": t.get("adapter_range") or [1, 0], "rc": t.get("rc"),
                  "elapsed_s": t.get("elapsed_s"), "reply_chars": t.get("reply_chars"),
                  "ledger_steps": t.get("ledger_steps"), "ledger_calls": t.get("ledger_calls")},
                 fam_of.get(tid))

    if a.write:
        io.open(os.path.join(evwin, "artifacts.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps({"window": win, "artifacts": arts}, ensure_ascii=False, indent=1) + "\n")
        io.open(os.path.join(evwin, "report.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps({"window": win, "rows": rows}, ensure_ascii=False, indent=1) + "\n")
        io.open(os.path.join(R, "evidence", "index-r531.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps(index, ensure_ascii=False, indent=1) + "\n")
        print("WROTE %s" % os.path.relpath(evwin, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
