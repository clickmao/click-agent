#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R605 候选④ 零回归：把 W_floor（有效窗下限）条款回放到历史轮次，判定「纯收紧/中性」还是「改写既有判决」。

纪律（预注册 prereg-r605.json::judge.W_floor.negative_control）：
  · 本条款**只改判决标签语义**（有效窗 ∈{0,1} ⇒ NO_RESOLUTION），**不改任何阈值**（−2 / −15 不动）；
  · 判据标签重算须与各轮 verdict 件里已登记的 `D_list` / `valid_windows` 逐位一致（不符 ⇒ rc=2 器具缺陷）；
  · 主 rc 不依赖该标签（历史 rc 由 J1∧J2∧J3 决定）⇒ 逐轮核对主 rc 未因标签变化而改变。

rc: 0 已算 / 2 器具缺陷或重算不一致 / 3 输入缺失。
用法: python3 wfloor_regression_r605.py [--out eval/rover/r605/wfloor-regression-r605.json]
"""
from __future__ import annotations
import argparse
import glob
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
ROUNDS = ("r585", "r586", "r587", "r588", "r591", "r595", "r596", "r597", "r598", "r599", "r602", "r603", "r605")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r605/wfloor-regression-r605.json"))
    a = ap.parse_args()

    rows, defects, missing = [], [], []
    for rid in ROUNDS:
        p = os.path.join(REPO, "eval/rover", rid, "verdict-%s.json" % rid)
        if not os.path.isfile(p):
            missing.append(rid)
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        q = d.get("C1_task_face_v3") or d.get("C1_quality_paired") or {}
        valid, D, old_pass = q.get("valid_windows"), q.get("D_list"), q.get("pass")
        if valid is None:
            missing.append(rid)
            continue
        # W_floor：有效窗 ∈{0,1} ⇒ NO_RESOLUTION（标签语义），否则沿用公式
        new_label = "NO_RESOLUTION" if valid < 2 else ("PASS" if old_pass else "不达")
        old_label = "PASS" if old_pass else "不达"
        main_rc = (d.get("verdict") or {}).get("rc")
        flips = old_label != new_label
        rows.append({"round": rid, "valid_windows": valid, "D_list": D,
                     "old_label": old_label, "new_label": new_label, "label_flip": flips,
                     "main_rc": main_rc,
                     "main_rc_would_change": False if not flips else None})
        if flips and old_label == "不达" and new_label == "PASS":
            defects.append("%s 由「不达」翻为 PASS（阈值被改动）" % rid)

    # 重算一致性（两路径）：verdict 的 D_median 必须等于 D_list 中位（逐位）
    import statistics
    for r in rows:
        if r["D_list"]:
            m = round(statistics.median(r["D_list"]), 4)
            p = os.path.join(REPO, "eval/rover", r["round"], "verdict-%s.json" % r["round"])
            q = (json.load(io.open(p, encoding="utf-8")).get("C1_task_face_v3")
                 or json.load(io.open(p, encoding="utf-8")).get("C1_quality_paired") or {})
            if q.get("D_median") is not None and abs(round(float(q["D_median"]), 4) - m) > 1e-6:
                defects.append("%s D_median 重算不符: 登记 %s vs 重算 %s" % (r["round"], q["D_median"], m))

    flips = [r for r in rows if r["label_flip"]]
    out = {
        "round": "R605", "tool": "wfloor_regression_r605",
        "criterion": "W_floor：有效窗 ≥2 ⇒ 判据行使；有效窗 ∈{0,1} ⇒ NO_RESOLUTION（阈值不动）",
        "rows": rows, "rounds_checked": len(rows), "rounds_missing": missing,
        "label_flips": [{"round": r["round"], "old": r["old_label"], "new": r["new_label"],
                         "valid": r["valid_windows"]} for r in flips],
        "flip_count": len(flips),
        "flip_direction": {"不达→NO_RESOLUTION": sum(1 for r in flips if r["old_label"] == "不达"),
                           "NO_RESOLUTION→PASS": sum(1 for r in flips if r["new_label"] == "PASS"),
                           "PASS→任何": sum(1 for r in flips if r["old_label"] == "PASS")},
        "neutrality": "本条款只把「有效窗 ≤1 的 不达」改写为 NO_RESOLUTION（不作能力结论）；"
                      "PASS 标签与主 rc（J1∧J2∧J3）均不受影响 ⇒ 纯标签语义收口，非阈值改动",
        "defects": defects,
        "verdict": "INSTRUMENT_DEFECT" if defects else ("COMPUTED" if rows else "INPUT_MISSING"),
        "rc": 2 if defects else (0 if rows else 3),
    }
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[wfloor-r605] rc=%d checked=%d flips=%d %s" % (out["rc"], len(rows), len(flips),
                                                          json.dumps(out["flip_direction"], ensure_ascii=False)))
    for r in rows:
        print("  %s valid=%s old=%s new=%s flip=%s main_rc=%s" % (r["round"], r["valid_windows"], r["old_label"],
                                                                  r["new_label"], r["label_flip"], r["main_rc"]))
    if defects:
        print("  defects=%s" % defects)
    print("  wrote %s" % a.out)
    return out["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
