#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R518 编排器臂 (agentO) 快照冻结器 —— 与 R513 冻结器同布局, 供铁律 11 前置器自动发现。

为什么单独一个: 编排器臂不经 proj_run_side.py (无 side-run.json), 冻结器按「一臂一题一 work 树」
的约定入库; 本器把**同一个**编排工作区树分别拷进 `snapshots/<win>/<snap>/<tid>/` (双包共一树,
逐题判分器只看自己那包), 逐题**实跑**隐藏用例出 `grade-<tag>-<tid>.json`, 并把行/件并入窗口件。

fail-closed: ① 源树不存在 ⇒ 不写任何文件 rc=3; ② 拷贝逐文件 sha256 读回一致; ③ 窗口件非 append
且已存在 ⇒ rc=4; ④ 判分器报 instrument_error ⇒ rc=3 (禁把器具故障当「答错」)。
用法: python3 freeze_orch_r518.py --run-dir D --orch-dir D/orch --window w1 --snapshot-dir agentO \
        --tag O --arm O-r1 --tasks p3,p4 --idx-before N --idx-after M [--write] [--append]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r511"))
sys.path.insert(0, os.path.join(REPO, "eval/rover/r510"))
import grade_r511  # noqa: E402

try:
    import usage_from_dumps as ufd  # noqa: E402
except Exception:  # pragma: no cover
    ufd = None


def sha256_file(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


def copy_tree(src, dst):
    out = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        rel = os.path.relpath(root, src)
        tgt = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(tgt, exist_ok=True)
        for f in sorted(files):
            if f.endswith((".pyc", ".pyo")):
                continue
            shutil.copy2(os.path.join(root, f), os.path.join(tgt, f))
            out.append(os.path.relpath(os.path.join(tgt, f), dst))
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--orch-dir", required=True, help="编排器运行目录 (内含 ws/ 工作区树)")
    ap.add_argument("--window", required=True)
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--idx-before", type=int, default=0)
    ap.add_argument("--idx-after", type=int, default=-1)
    ap.add_argument("--adapter-dir", default="")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--append", action="store_true")
    a = ap.parse_args()

    n = HERE = os.path.join(REPO, "eval/rover/r518")
    win_ev = os.path.join(HERE, "evidence/windows", a.window)
    snap_win = os.path.join(HERE, "snapshots", a.window)
    src = os.path.join(a.orch_dir, "ws")
    if not os.path.isdir(src):
        print("[致命] 缺编排工作区树 %s ⇒ fail-closed, 不写任何文件" % src)
        return 3
    if not a.append and os.path.isdir(os.path.join(snap_win, a.snapshot_dir)) \
            and os.listdir(os.path.join(snap_win, a.snapshot_dir)):
        print("[致命] 快照臂目录非空 (禁覆盖)")
        return 4

    tids = [t for t in a.tasks.split(",") if t]
    files_n = bytes_n = 0
    staged, grades, arts = {}, {}, []
    for tid in tids:
        dst = os.path.join(snap_win, a.snapshot_dir, tid)
        rel_files = copy_tree(src, dst) if a.write else []
        staged[tid] = rel_files
        for f in rel_files:
            fp = os.path.join(dst, f)
            files_n += 1
            bytes_n += os.path.getsize(fp)
            arts.append({"window": a.window, "arm": a.arm, "side": "agent",
                         "snapshot_dir": a.snapshot_dir, "tid": tid, "path": f,
                         "bytes": os.path.getsize(fp)})
        g = grade_r511.grade(tid, dst if a.write else src)
        if g.get("instrument_error"):
            print("[致命] 判分器具故障 (%s): %s" % (tid, g["instrument_error"]))
            return 3
        grades[tid] = g

    if not a.write:
        print(json.dumps({"window": a.window, "write": False,
                          "grades": {k: {"ok": v["ok"], "pass": v["cases_passed"], "total": v["cases_total"]}
                                     for k, v in grades.items()}}, ensure_ascii=False))
        return 0

    bad = []
    for tid in tids:
        for f in staged[tid]:
            sp, dp = os.path.join(src, f), os.path.join(snap_win, a.snapshot_dir, tid, f)
            if not os.path.isfile(dp) or sha256_file(sp) != sha256_file(dp):
                bad.append("%s/%s" % (tid, f))
    if bad:
        print("[致命] 快照读回不一致: %s" % bad[:5])
        return 3

    calls = prompt_tokens = cached_tokens = completion_tokens = None
    if ufd and a.adapter_dir and a.idx_after >= a.idx_before:
        u = ufd.collect(a.adapter_dir, "agent", a.idx_before + 1, a.idx_after)
        calls = u.get("calls")
        prompt_tokens = u.get("prompt_tokens")
        cached_tokens = u.get("cached_tokens")
        completion_tokens = u.get("completion_tokens")

    os.makedirs(win_ev, exist_ok=True)
    for tid in tids:
        g = grades[tid]
        io.open(os.path.join(win_ev, "grade-%s-%s.json" % (a.tag, tid)), "w",
                encoding="utf-8", newline="\n").write(json.dumps(
                    {"tag": a.tag, "tid": tid, "arm": a.arm, "side": "agent",
                     "all_pass": bool(g["ok"]), "cases_passed": g["cases_passed"],
                     "cases_total": g["cases_total"],
                     "failed": [f["name"] for f in g.get("failed") or []]},
                    ensure_ascii=False, indent=1) + "\n")

    ap_p, rp_p = os.path.join(win_ev, "artifacts.json"), os.path.join(win_ev, "report.json")
    if a.append and os.path.isfile(ap_p):
        old = json.load(io.open(ap_p, encoding="utf-8-sig")).get("artifacts") or []
        oldk = {(o.get("snapshot_dir"), o.get("tid"), o.get("path")) for o in old}
        arts = old + [x for x in arts if (x.get("snapshot_dir"), x.get("tid"), x.get("path")) not in oldk]
    io.open(ap_p, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"window": a.window, "artifacts": arts}, ensure_ascii=False, indent=1) + "\n")

    rows = [{"arm": a.tag, "run": a.arm, "side": "agent", "tid": tid,
             "all_pass": bool(grades[tid]["ok"]),
             "cases_pass": grades[tid]["cases_passed"], "cases_total": grades[tid]["cases_total"],
             "failed": [f["name"] for f in grades[tid].get("failed") or []],
             "calls": calls, "prompt_tokens": prompt_tokens, "cached_tokens": cached_tokens,
             "completion_tokens": completion_tokens,
             "adapter_range": [a.idx_before + 1, a.idx_after]} for tid in tids]
    if a.append and os.path.isfile(rp_p):
        old = json.load(io.open(rp_p, encoding="utf-8-sig")).get("rows") or []
        oldk = {(o.get("run"), o["tid"]) for o in old}
        rows = old + [r for r in rows if (r.get("run"), r["tid"]) not in oldk]
    io.open(rp_p, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"window": a.window, "rows": rows}, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps({"window": a.window, "snapshot_dir": a.snapshot_dir, "files": files_n,
                      "artifact_bytes": bytes_n, "calls": calls,
                      "grades": {k: "%d/%d" % (v["cases_passed"], v["cases_total"])
                                 for k, v in grades.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
