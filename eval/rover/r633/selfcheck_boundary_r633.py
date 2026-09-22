#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R633 · N6 只读取证：**产物自证边界**（R631 冻结面，零重跑）。

动因：承 R629 候选② 逐例归因（主族 = `APPROX_COLD_SET`）+ R632 候选②（wythoff 冷点集修法）。
问题：产品产出的程序**在题面公开用例上全过**而在**隐藏用例上失败**吗？若是 ⇒ 说明
  (a) 自检面（PUBLIC_SELFCHECK，held-constant =1）对该类缺陷**结构性看不见**（题面公开用例不覆盖该边界），
  (b) 缺口不是「规格未读」而是「泛化/边界构造」，属**能力面**而非契约面。

数据面：R631 冻结 run 目录（`$HOME/.agentframework/harness/runs/r631/w2*/<sub>/g1/cases.txt`）——**零重跑**。
判据：诊断列，**不作判据、不进 rc**（防把「自检盲区」写成宣称）。
用法: python3 selfcheck_boundary_r633.py [--root <run根>] [--out <json>]
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os


def split_cases(path):
    pub = [0, 0]
    hid = [0, 0]
    fams = {}
    wfail = []
    for line in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        if not line.startswith("CASE"):
            continue
        cid = line.split()[1] if len(line.split()) > 1 else "?"
        ok = "PASS" in line
        fan = cid.split("#")[0]
        fams.setdefault(fan, [0, 0])
        fams[fan][0] += 1
        fams[fan][1] += 1 if ok else 0
        if cid.endswith("-public"):
            pub[0] += 1
            pub[1] += 1 if ok else 0
        elif cid.endswith("-hidden"):
            hid[0] += 1
            hid[1] += 1 if ok else 0
        if not ok and fan == "wythoff":
            wfail.append(cid)
    return pub, hid, fams, wfail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/.agentframework/harness/runs/r631"))
    ap.add_argument("--out", default="eval/rover/r633/evidence/selfcheck-boundary-r633.json")
    a = ap.parse_args()
    out = {"source": "%s/w2*/agent*/g1/cases.txt（R631 冻结面，**零重跑**）" % a.root,
           "role": "诊断列（承 R629 逐例归因；不改任何历史判决、不进 rc）",
           "criterion": "同一跑次内 题面公开用例(-public)全过 ∧ 隐藏用例(-hidden)有失败 ⇒ blind_spot",
           "by_run": []}
    for f in sorted(glob.glob(os.path.join(a.root, "w2*", "agent*", "g1", "cases.txt"))):
        pub, hid, fams, wfail = split_cases(f)
        sub = f.split("/runs/")[1].rsplit("/g1/", 1)[0] if "/runs/" in f else f
        out["by_run"].append({
            "run": sub, "public": "%d/%d" % (pub[1], pub[0]), "hidden": "%d/%d" % (hid[1], hid[0]),
            "public_all_pass": bool(pub[0] and pub[1] == pub[0]),
            "hidden_has_fail": bool(hid[1] < hid[0]),
            "blind_spot": bool(pub[0] and pub[1] == pub[0] and hid[1] < hid[0]),
            "wythoff_fails": wfail,
            "families": {k: "%d/%d" % (v[1], v[0]) for k, v in sorted(fams.items())},
        })
    runs = len(out["by_run"])
    out["summary"] = {
        "runs": runs,
        "blind_spot_runs": sum(1 for r in out["by_run"] if r["blind_spot"]),
        "wythoff_fail_runs": sum(1 for r in out["by_run"] if r["wythoff_fails"]),
        "public_all_pass_runs": sum(1 for r in out["by_run"] if r["public_all_pass"]),
        "note": "R631 冻结面（2 窗 × 6 跑次）；零重跑只读取证",
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"], ensure_ascii=False))
    for r in out["by_run"]:
        print(r["run"], "pub", r["public"], "hid", r["hidden"], "blind", r["blind_spot"], "wy", r["wythoff_fails"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
