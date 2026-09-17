#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R525 冻结器 + 汇总器: 把三臂产物**冻结进仓内不可变快照**后才判分 (R505 教训: 判分不得读活目录)。

产物 (铁律 11 前置器 project 布局的输入面):
  · `snapshots/<win>/<snapdir>/<tid>/**`  逐字节拷贝 (源 mtime/sha 落 index)
  · `evidence/windows/<win>/artifacts.json`  文件清单 (路径+字节)
  · `evidence/windows/<win>/report.json`     自报行 (arm/tid/all_pass/usage; **判分结果**来自 grade-<tag>-<tid>.json)
  · `evidence/windows/<win>/grade-<tag>-<tid>.json`  权威判据器 `grade_r519.py` 的原始输出 (不吃自报)
  · `evidence/index-r525.json`            快照 sha256 清单 + 用量区段

判分只吃快照副本: `grade_r519.py --dir <snapshot>` (与 R519/R520 同判据器, md5 同源)。
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
R = os.path.join(REPO, "eval/rover/r525")
GRADER = os.path.join(REPO, "eval/rover/r519/grade_r519.py")
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
        for fn in fns:
            sp = os.path.join(root, fn)
            rel = os.path.relpath(sp, src)
            tp = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(tp), exist_ok=True)
            shutil.copy2(sp, tp)
            files.append({"path": rel.replace(os.sep, "/"), "bytes": os.path.getsize(tp),
                          "sha256": sha256(tp)})
    return sorted(files, key=lambda r: r["path"])


def grade(snapdir, out_path):
    p = subprocess.run([sys.executable, GRADER, "--dir", snapdir, "--out", out_path],
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
    ap.add_argument("--map", action="append", default=[], help="<run>=<snapdir> (A/C 臂)")
    ap.add_argument("--orch-run")
    ap.add_argument("--orch-snap", default="agentO")
    ap.add_argument("--orch-ws")
    ap.add_argument("--orch-idx")
    ap.add_argument("--orch-rc", type=int, default=0)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    D = a.run_dir
    win = a.window
    m = dict(x.split("=", 1) for x in a.map)
    snapwin = os.path.join(R, "snapshots", win)
    evwin = os.path.join(R, "evidence", "windows", win)
    if a.write:
        os.makedirs(snapwin, exist_ok=True)
        os.makedirs(evwin, exist_ok=True)

    rows, arts, index = [], [], {"window": win, "run_dir": D, "arms": {}}

    def emit(side, run, tid, worked, snapdir, extra):
        dst = os.path.join(snapwin, snapdir, tid)
        if a.write:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            # R521 修复: 空产物树也必落盘 (否则缺臂被静默跳过 ⇒ 前置器假绿 rc=0)
            os.makedirs(dst, exist_ok=True)
            files = copy_tree(worked, dst)
        else:
            os.makedirs(os.path.join("/tmp", "r525_dry_" + snapdir), exist_ok=True)
            files = copy_tree(worked, os.path.join("/tmp", "r525_dry_" + snapdir))
        gpath = os.path.join(evwin, "grade-%s-%s.json" % (extra["tag"], tid))
        g = None
        if a.write:
            g, grc = grade(dst, gpath)
            assert g is not None, "判分器无输出: %s" % gpath
        arts.extend({"window": win, "arm": run, "side": side, "snapshot_dir": snapdir,
                     "tid": tid, "path": f["path"], "bytes": f["bytes"]} for f in files)
        i0, i1 = extra["idx"]
        u = ufd.collect(a.adapter_dir, side, i0, i1) if i1 >= i0 else {"calls": 0}
        row = {"arm": extra["tag"], "run": run, "side": side, "tid": tid,
               "all_pass": bool(g and g.get("rc") == 0), "cases_pass": (g or {}).get("passed"),
               "cases_total": (g or {}).get("total"), "failed": [c for c in (g or {}).get("cases", []) if not c["ok"]],
               "rc": extra.get("rc"), "elapsed_s": extra.get("elapsed_s"),
               "adapter_range": [i0, i1], "calls": u.get("calls"), "prompt_tokens": u.get("prompt_tokens"),
               "cached_tokens": u.get("cached_tokens"), "completion_tokens": u.get("completion_tokens"),
               "total_tokens": u.get("total_tokens"), "models": u.get("models"),
               "unreported_usage": u.get("unreported_usage"), "artifacts": len(files),
               "snapshot_empty": (len(files) == 0),
               "reply_chars": extra.get("reply_chars"), "ledger_steps": extra.get("ledger_steps"),
               "ledger_calls": extra.get("ledger_calls"),
               "usage": {k: u.get(k) for k in ("calls", "prompt_tokens", "cached_tokens",
                                               "completion_tokens", "total_tokens", "unreported_usage", "models")}}
        rows.append(row)
        index["arms"]["%s/%s" % (snapdir, tid)] = {"run": run, "side": side, "snapdir": snapdir,
                                                   "files_n": len(files), "files": files,
                                                   "grade": os.path.relpath(gpath, REPO),
                                                   "usage_range": [i0, i1],
                                                   "calls": u.get("calls"), "total_tokens": u.get("total_tokens")}
        print("冻结 %-14s side=%-6s cases=%s/%s calls=%s tok=%s" %
              ("%s/%s" % (snapdir, tid), side, (g or {}).get("passed"), (g or {}).get("total"),
               u.get("calls"), u.get("total_tokens")))

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
            emit(side_j["side"], run, t["tid"], os.path.join(D, arm_dir, t["tid"], "work"), m[run],
                 {"tag": run, "idx": t.get("adapter_range") or [1, 0],
                  "rc": t.get("rc"), "elapsed_s": t.get("elapsed_s"),
                  "reply_chars": t.get("reply_chars"), "ledger_steps": t.get("ledger_steps"),
                  "ledger_calls": t.get("ledger_calls")})

    if a.orch_run and a.orch_ws:
        i0, i1 = (int(x) for x in a.orch_idx.split(","))
        rep = {}
        rp = os.path.join(D, "orch", "report.json")
        if os.path.isfile(rp):
            rep = json.load(io.open(rp, encoding="utf-8"))
        el = sum(int(n.get("elapsed_ms") or 0) for n in (rep.get("nodes") or [])) / 1000.0
        emit("agent", a.orch_run, "g1", a.orch_ws, a.orch_snap,
             {"tag": "O", "idx": [i0 + 1, i1], "rc": a.orch_rc, "elapsed_s": round(el, 2),
              "reply_chars": None, "ledger_steps": None, "ledger_calls": None})

    if a.write:
        io.open(os.path.join(evwin, "artifacts.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps({"window": win, "artifacts": arts}, ensure_ascii=False, indent=1) + "\n")
        io.open(os.path.join(evwin, "report.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps({"window": win, "rows": rows}, ensure_ascii=False, indent=1) + "\n")
        io.open(os.path.join(R, "evidence", "index-r525.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps(index, ensure_ascii=False, indent=1) + "\n")
        print("WROTE %s" % os.path.relpath(evwin, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
