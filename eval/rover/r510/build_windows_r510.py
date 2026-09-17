#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R510: A/B 跑次的落盘物 → 快照面板 (evidence/windows + snapshots)。

布局 (与 r508/r509 同构, exec_precondition.py --round R510 直接可吃):
  eval/rover/r510/snapshots/r510ab<N>/<arm>/p3/            ← 跑次的 work 树 (kvsvc/ 在此)
  eval/rover/r510/evidence/windows/r510ab<N>/artifacts.json ← { "<arm>/p3": [[rel,size],...] }
  eval/rover/r510/evidence/windows/r510ab<N>/grade-<tag>-p3.json ← 自报读数 (只作对照)
用法: python3 build_windows_r510.py --run-dir /tmp/r510/ab [--reps 3]
"""
from __future__ import annotations
import argparse, json, os, shutil

REPO = "/home/agentuser/AgentFramework"
ROUND = os.path.join(REPO, "eval/rover/r510")
ARMS = ["agentBefore", "agentAfter"]


def tag(arm: str) -> str:
    return arm[len("agent"):] if arm.startswith("agent") else arm


def tree(root: str):
    out = []
    for r, _d, fs in os.walk(root):
        for f in fs:
            p = os.path.join(r, f)
            out.append([os.path.relpath(p, root), os.path.getsize(p)])
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--reps", type=int, default=3)
    a = ap.parse_args()
    built = []
    for rep in range(1, a.reps + 1):
        win = "r510ab%d" % rep
        wdir = os.path.join(ROUND, "evidence/windows", win)
        sdir = os.path.join(ROUND, "snapshots", win)
        os.makedirs(wdir, exist_ok=True)
        os.makedirs(sdir, exist_ok=True)
        art = {}
        for arm in ARMS:
            work = os.path.join(a.run_dir, arm, "rep%d" % rep, "p3", "work")
            if not os.path.isdir(work):
                print("[缺] %s" % work)
                continue
            dst = os.path.join(sdir, arm, "p3")
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(work, dst)
            art["%s/p3" % arm] = tree(dst)
            g = os.path.join(a.run_dir, "evidence", "grade-%s-rep%d-p3.json" % (arm, rep))
            if os.path.isfile(g):
                shutil.copy2(g, os.path.join(wdir, "grade-%s-p3.json" % tag(arm)))
        json.dump(art, open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        built.append({"win": win, "arms": sorted(art.keys())})
    print(json.dumps({"run_dir": a.run_dir, "windows": built}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
