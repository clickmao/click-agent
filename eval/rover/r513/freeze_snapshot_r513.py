#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R513 快照冻结器: 把 /tmp 活目录产物**不可变入库** + 出 project 布局窗口件。

为什么必须 (R505 入册纪律): /tmp 活目录会被后续作业静默覆盖 ⇒ 读数成立但事后不可重放。
本器把每个窗口每臂每题的 work 树逐字节拷进 `eval/rover/r513/snapshots/<win>/<dir>/<tid>/`,
并写 `evidence/windows/<win>/{report.json,artifacts.json}` (铁律 11 project 前置器的入口)。

三处 fail-closed: ① 源 work 不存在 ⇒ 不写任何文件 rc=3; ② 拷贝后逐文件 sha256 读回一致;
③ 窗口目录已存在且非空 ⇒ 拒跑 (禁覆盖)。
用法: python3 freeze_snapshot_r513.py --run-dir <D> --window w1 --map A-r1=agentA --map C-r1=codex [--write]
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, shutil, sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval/rover/r513")


def sha256_file(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


def copy_tree(src, dst):
    out = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        rel = os.path.relpath(root, src)
        tgt = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(tgt, exist_ok=True)
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                continue
            shutil.copy2(os.path.join(root, f), os.path.join(tgt, f))
            out.append(os.path.relpath(os.path.join(tgt, f), dst))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--window", required=True)
    ap.add_argument("--map", action="append", required=True, help="<arm_dir>=<snapshot_dir>")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", help="aggregate report.json (用于窗口 report 行)")
    ap.add_argument("--append", action="store_true",
                    help="窗口已存在时**只追加新臂**(R513 增补臂 B): 每个新臂快照目录必须不存在; 行/件按 (run,tid) 去重合并")
    a = ap.parse_args()

    mapping = [m.split("=", 1) for m in a.map]
    D = a.run_dir
    for arm_dir, _ in mapping:
        if not os.path.isfile(os.path.join(D, arm_dir, "side-run.json")):
            print("[致命] 缺 %s/side-run.json ⇒ fail-closed, 不写任何文件" % arm_dir)
            return 3
    win_ev = os.path.join(HERE, "evidence/windows", a.window)
    snap_win = os.path.join(HERE, "snapshots", a.window)
    if a.append:
        for _, snap_dir in mapping:
            tgt = os.path.join(snap_win, snap_dir)
            if os.path.isdir(tgt) and os.listdir(tgt):
                print("[致命] --append 但快照臂目录非空 (禁覆盖): %s" % tgt)
                return 4
        if not (os.path.isdir(win_ev) or os.path.isdir(snap_win)):
            print("[致命] --append 但窗口 %s 不存在 (首写请去掉 --append)" % a.window)
            return 4
    else:
        if os.path.isdir(win_ev) and os.listdir(win_ev):
            print("[致命] 窗口 %s 证据目录非空 ⇒ 拒覆盖" % a.window)
            return 4
        if os.path.isdir(snap_win) and os.listdir(snap_win):
            print("[致命] 窗口 %s 快照目录非空 ⇒ 拒覆盖" % a.window)
            return 4

    arts, files_n, bytes_n = [], 0, 0
    staged = {}
    for arm_dir, snap_dir in mapping:
        sr = json.load(io.open(os.path.join(D, arm_dir, "side-run.json"), encoding="utf-8"))
        for t in sr["tasks"]:
            tid = t["tid"]
            work = os.path.join(D, arm_dir, tid, "work")
            if not os.path.isdir(work):
                print("[致命] 缺产物树 %s ⇒ fail-closed" % work)
                return 3
            rel_files = copy_tree(work, os.path.join(snap_win, snap_dir, tid)) if a.write else []
            for rp in (t.get("artifacts") or []):
                arts.append({"window": a.window, "arm": sr["arm"], "side": sr["side"], "snapshot_dir": snap_dir,
                             "tid": tid, "path": rp["path"], "bytes": rp["bytes"]})
                bytes_n += int(rp["bytes"] or 0)
            files_n += len(rel_files) if a.write else len(t.get("artifacts") or [])
            staged[(snap_dir, tid)] = rel_files
    if a.write:
        # 读回复核 (拷贝后逐文件 sha256, 与源比对)
        bad = []
        for arm_dir, snap_dir in mapping:
            sr = json.load(io.open(os.path.join(D, arm_dir, "side-run.json"), encoding="utf-8"))
            for t in sr["tasks"]:
                tid = t["tid"]
                src = os.path.join(D, arm_dir, tid, "work")
                dst = os.path.join(snap_win, snap_dir, tid)
                for f in staged[(snap_dir, tid)]:
                    sp, dp = os.path.join(src, f), os.path.join(dst, f)
                    if not os.path.isfile(dp) or sha256_file(sp) != sha256_file(dp):
                        bad.append("%s/%s/%s" % (snap_dir, tid, f))
        if bad:
            print("[致命] 快照读回不一致: %s" % bad[:5])
            return 3
        os.makedirs(win_ev, exist_ok=True)
        ap_p, rp_p = os.path.join(win_ev, "artifacts.json"), os.path.join(win_ev, "report.json")
        if a.append and os.path.isfile(ap_p):
            arts = (json.load(io.open(ap_p, encoding="utf-8-sig")).get("artifacts") or []) + arts
        io.open(ap_p, "w", encoding="utf-8", newline="\n").write(
            json.dumps({"window": a.window, "run_dir": D, "artifacts": arts}, ensure_ascii=False, indent=1) + "\n")
        rows = []
        if a.json and os.path.isfile(a.json):
            rep = json.load(io.open(a.json, encoding="utf-8-sig"))
            keep = {json.load(io.open(os.path.join(D, ad, "side-run.json"), encoding="utf-8"))["arm"]
                    for ad, _ in mapping}
            rows = [r for r in rep["rows"] if (r.get("run") or r["arm"]) in keep]
        if a.append and os.path.isfile(rp_p):
            old = json.load(io.open(rp_p, encoding="utf-8-sig")).get("rows") or []
            oldk = {(o.get("run"), o["tid"]) for o in old}
            rows = old + [r for r in rows if (r.get("run"), r["tid"]) not in oldk]
        io.open(os.path.join(win_ev, "report.json"), "w", encoding="utf-8", newline="\n").write(
            json.dumps({"window": a.window, "run_dir": D, "rows": rows}, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"window": a.window, "write": a.write, "append": a.append, "arms": [m[1] for m in mapping],
                      "artifacts": len(arts), "files": files_n, "artifact_bytes": bytes_n},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
