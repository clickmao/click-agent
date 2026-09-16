#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R497 候选① 真值收口扫描 (机检, 面分类版)。

口径 (R497 收紧后的三条):
  A. **本臂可读面** = 本臂自己的 `rundata-<arm>/**` + `tel-<arm>/host.jsonl` + `ledger-<arm>.jsonl`
     + `host-<arm>.log` (臂的 cwd 就是自己的 rundir; 别的臂的 rundata 不在其工作区内 ⇒ 不计入本臂泄漏)。
  B. **硬红面** = 打点/台账/遥测 (`tel-*`、`ledger-*`、`rundata-*/data/telemetry/`、`rundata-*/data/ledger/`):
     出现**本臂真值字面量**即红 —— 这正是 R496 判据红的那条通道 (R497 已收口, 期望 0)。
  C. **授权复述的二次落盘** = `rundata-*/data/rag/index.jsonl`、`sessions/`、`think-memory` 等**会话记忆面**:
     若该字面量同时出现在**本臂模型自己的回复** (`turns-<arm>.jsonl`) 里 ⇒ 记 `restatement_derived`
     (挂载臂的授权复述被记忆索引落盘 —— R497 新发现的**次生面**, 单列不红, 交下轮); 否则红。
  D. 源码面: `src/**/*.cs` 不得再有把 raw 码直写打点/落盘的写法 (第二参名含 ledger/LCM)。
  E. 诱饵: 网格自带的假码 (t14 `LCM-deadbeef1234`) 从网格机派生为 decoy ⇒ 产品面出现诱饵不算泄漏。

用法: python3 truth_reclose_scan_r497.py --dir eval/rover/r497 [--arms B,T0,T2,T1,T1n,O1]
退出码: 0 = 无红; 1 = 有红
"""
import argparse
import json
import os
import re
import sys

RAW_RX = re.compile(r"LCM-[0-9a-f]{12}")
MOUNT_RX = re.compile(r"\[本地决策台账-链自持\][^\n]*code=(LCM-[0-9a-f]{12})")
SELF = "truth-reclose-r497.json"
HARD_PAT = re.compile(r"(^tel-|^ledger-|/data/telemetry/|/data/ledger/)")
MEM_PAT = re.compile(r"(/data/rag/|/sessions|think-memory|/data/activity/)")


def text_files(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "obj", "bin")]
        for n in fn:
            p = os.path.join(dp, n)
            if n == SELF:
                continue
            try:
                if os.path.getsize(p) > 40 * 1024 * 1024:
                    continue
                with open(p, encoding="utf-8", errors="replace") as f:
                    yield p, f.read()
            except Exception:
                continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="eval/rover/r497")
    ap.add_argument("--arms", default="B,T0,T2,T1,T1n,O1")
    ap.add_argument("--grid", default=None)
    a = ap.parse_args()
    D = a.dir.rstrip("/")
    arms = [x for x in a.arms.split(",") if x]
    repo = os.path.abspath(os.path.join(D, "..", "..", ".."))
    grid_p = a.grid or os.path.join(D, "grid/task-p17-code.json")
    decoys = set(RAW_RX.findall(open(grid_p, encoding="utf-8").read())) if os.path.exists(grid_p) else set()
    red, out_arms = [], {}
    lits_all = set()
    wire_by_arm = {}
    for arm in arms:
        cp = os.path.join(D, "calls-%s.jsonl" % arm)
        codes = set()
        if os.path.exists(cp):
            codes = set(MOUNT_RX.findall(open(cp, encoding="utf-8", errors="replace").read())) - decoys
        wire_by_arm[arm] = sorted(codes)
        lits_all |= codes
    lits_all |= decoys
    for arm in arms:
        own_to = open(os.path.join(D, "turns-%s.jsonl" % arm), encoding="utf-8", errors="replace").read() \
            if os.path.exists(os.path.join(D, "turns-%s.jsonl" % arm)) else ""
        own_prefix = ("rundata-%s/" % arm, "tel-%s/" % arm, "host-%s.log" % arm, "ledger-%s.jsonl" % arm,
                      "relay-%s.log" % arm, "usage-%s.jsonl" % arm, "turns-%s.jsonl" % arm, "calls-%s.jsonl" % arm)
        by_lit, hard, restated, unexplained = {}, [], [], []
        for p, t in text_files(D):
            rel = os.path.relpath(p, D)
            if not rel.startswith(own_prefix):
                continue
            for l in lits_all:
                c = t.count(l)
                if not c:
                    continue
                by_lit.setdefault(l, []).append([rel, c])
                if l in decoys:
                    continue
                if rel.startswith("calls-%s.jsonl" % arm) or rel.startswith("turns-%s.jsonl" % arm):
                    continue                      # 实发/回显通道 (设计内)
                if HARD_PAT.search(rel):
                    hard.append([rel, l, c])
                elif MEM_PAT.search(rel) or rel.startswith("rundata-%s/" % arm):
                    (restated if l in own_to else unexplained).append([rel, l, c])
                else:
                    unexplained.append([rel, l, c])
        if hard:
            red.append("%s: 硬红面 (打点/台账/遥测) 出现本臂真值: %r" % (arm, hard[:4]))
        if unexplained:
            red.append("%s: 本臂真值出现在无法归因的面: %r" % (arm, unexplained[:4]))
        out_arms[arm] = {"present": os.path.exists(os.path.join(D, "calls-%s.jsonl" % arm)),
                         "wire_codes_n": len(wire_by_arm[arm]), "hits_by_literal": by_lit,
                         "hard_face_hits": hard, "restatement_derived": restated, "unexplained": unexplained}
    # 源码面
    src_hits = []
    for dp, dn, fn in os.walk(os.path.join(repo, "src")):
        dn[:] = [d for d in dn if d not in ("obj", "bin")]
        for n in fn:
            if not n.endswith(".cs") or n == "LocalDecisionLedger.cs" or n.startswith("R497"):
                continue
            p = os.path.join(dp, n)
            try:
                t = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for m in re.finditer(r'"code"\s*,\s*[A-Za-z_.]*(?:[Ll]edger|LCM)[A-Za-z_]*', t):
                src_hits.append({"file": os.path.relpath(p, repo), "match": m.group(0)})
    if src_hits:
        red.append("src 面仍有 raw 码直写: %r" % src_hits[:4])
    rep = {"round": "R497", "instrument": "truth_reclose_scan_r497.py", "self_excluded": SELF,
           "scope_note": "A 本臂可读面 / B 硬红面=打点台账遥测 / C 会话记忆面命中若可从本臂回复复现记 restatement_derived "
                         "/ D 源码面 / E 诱饵机派生 (网格假码)",
           "grid": os.path.relpath(grid_p, repo), "decoys_from_grid": sorted(decoys),
           "arms": out_arms, "src_face_raw_emit": src_hits, "red": red,
           "verdict": "GREEN" if not red else "RED"}
    with open(os.path.join(D, SELF), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print("[truth_reclose] verdict=%s decoys=%s" % (rep["verdict"], sorted(decoys)))
    for arm, r in out_arms.items():
        if not r["present"]:
            print("  %-4s 缺 calls ⇒ 未跑" % arm)
            continue
        print("  %-4s 线上真码 %d / 硬红面 %d / 授权复述次生 %d / 未归因 %d"
              % (arm, r["wire_codes_n"], len(r["hard_face_hits"]), len(r["restatement_derived"]), len(r["unexplained"])))
        for rel, l, c in r["restatement_derived"][:3]:
            print("       [restatement] %s %s x%d" % (rel, l, c))
    print("  src 面 raw 直写: %d 处" % len(src_hits))
    for x in red:
        print("  [RED] " + x)
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
