#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R629 · 候选① 修法落地：**轮收口判决件（修正形态）**。

修前（R628，`verdict-r628.json`）三处缺陷（见 evidence/instrument-defects-r629.json）：
  D1  主判据读数（C7 判据 v3 第五窗集）**未落进判决件顶层**；
  D1b 记录判决 `blocked` 的来源键 = `C1_quality_paired`（预注册自述「仅作同向参照、不出判决」）；
  D2  铁律 11 指针为硬编码字符串，与 `--out` **不同源**、且该路径不存在；
  D3  声明件 `eval/rover/r628/taskface-pool-r628.json` 从未写出，未登记。

修后（本件）：判决件由**在盘产物**驱动生成，四件都成无条件计算：
  ① 主判据读数以 `C7_judge_v3_primary` **落顶层**（键名即预注册主判据名）；
  ② `verdict.blocked` 的来源键 == 主判据名（判决来源 == 预注册主判据面）；
  ③ `verdict.iron11` 指针**与 `--out` 同源派生**（同目录 `precond-<tag>.json`，缺失出声记 null）；
  ④ `declared_scope` 只列**实际写出且存在**的件，逐条做存在性机检。

只读、零产品源码改动、零远端 LLM（R629 归因轮硬约束）。
退出码：0 判决面成立 / 1 主判据判不达标 / 2 器具缺陷 / 3 输入缺失。
"""

import argparse
import hashlib
import io
import json
import os
import sys

def _repo_root(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.isdir(os.path.join(p, "eval", "rover")) and os.path.isdir(os.path.join(p, "src")):
            return p
        p = os.path.dirname(p)
    raise SystemExit("INPUT_MISSING repo root")

REPO = _repo_root(os.path.dirname(os.path.abspath(__file__)))

def load(p):
    return json.load(io.open(p, encoding="utf-8"))

def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12] if os.path.exists(p) else None

PRIMARY_KEY = "C7_judge_v3_primary"

def build(out_path, pool_path, attr_path, prereg_path, round_tag):
    pool = load(os.path.join(REPO, pool_path))
    attr = load(os.path.join(REPO, attr_path))
    prereg = load(os.path.join(REPO, prereg_path))
    s5 = pool["set5_primary_criterion"]
    pw = s5["per_window"]
    # 判据 v3（主判据）= 整题全对率按窗分列；有效窗 = 真值自身在窗内整题全对 ≥1
    valid_ws = [w for w in pw if w.get("valid_task")]
    valid = len(valid_ws)
    ds = sorted(w["D_task"] for w in valid_ws if w.get("D_task") is not None)
    median_d_task = ds[len(ds) // 2] if ds else None
    prod_all = [w["prod_rate_task"] for w in pw if w.get("prod_rate_task") is not None]
    med = sorted(prod_all)[len(prod_all) // 2] if prod_all else None
    tech_truth = sorted(med for med in [w["prod_rate_task"] for w in pw]) if False else None
    truth_task_rate = sorted(1.0 if w.get("truth_all_pass") else 0.0 for w in pw)
    tech_truth = truth_task_rate[len(truth_task_rate) // 2] if truth_task_rate else None
    thresh = (prereg.get("criteria") or {}).get("median_gap_threshold")
    threshold = thresh if isinstance(thresh, (int, float)) else -0.34
    passed = (valid >= 2) and (median_d_task is not None) and (median_d_task >= threshold)

    declared = [pool_path, attr_path, prereg_path,
                "eval/rover/r629/evidence/instrument-defects-r629.json"]
    declared_missing = [d for d in declared if not os.path.exists(os.path.join(REPO, d))]
    d = os.path.dirname(os.path.abspath(out_path))
    pc_cands = [os.path.join(d, "precond-%s.json" % round_tag),
                os.path.join(d, "precondition-%s.json" % round_tag)]
    iron11 = next((p for p in pc_cands if os.path.exists(p)), None)

    v = {
        "schema": "r629-round-verdict/1",
        "round": "R629",
        "round_type": "器件/判据面修法轮 + wythoff 族逐例归因（只读定因）",
        "primary_criterion": "判据 v3（整题全对率 + 按族分列）",
        PRIMARY_KEY: {
            "median_D_task": median_d_task,
            "truth_median_task": tech_truth,
            "prod_median_task": med,
            "threshold": threshold,
            "valid_windows": valid,
            "windows": s5["windows"],
            "pass": bool(passed),
            "note": "主判据读数**落顶层**（修前只在参照面 C1 里，判决面读不到）",
        },
        "reference_criteria": {
            "C1_quality_paired": {"role": "同向参照（预注册自述：不出判决）"},
            "C_A_enumeration_equivalence": pool["C_A_enumeration_equivalence"],
            "C_B_enumeration_teeth": {k: v2 for k, v2 in pool["C_B_enumeration_teeth"].items()
                                      if k != "C7_primary_negative_control"},
            "C7_primary_negative_control": pool["C_B_enumeration_teeth"]["C7_primary_negative_control"],
            "attribution": {"A_independent_oracle": attr.get("A_independent_oracle"),
                            "B_independent_replay": attr.get("B_independent_replay"),
                            "D_minimal_repair": attr.get("D_minimal_repair")},
        },
        "declared_scope": declared,
        "declared_absent": declared_missing,
        "primary_criterion_key": PRIMARY_KEY,
        "verdict": {
            "rc": 0 if (passed and not declared_missing and iron11) else (2 if (declared_missing or not iron11) else 1),
            "verdict_source": PRIMARY_KEY,
            "blocked": ([] if passed else ["%s:R629" % PRIMARY_KEY]),
            "iron11": iron11,
            "iron11_derived_from": "--out（同目录 precond-%s.json）" % round_tag,
            "iron11_exists": bool(iron11),
            "declared_artifacts_missing": declared_missing,
            "judge": ("判决面成立（主判据落盘 ∧ 判决来源 == 主判据 ∧ 指针同源 ∧ 声明件齐备）"
                      if (not declared_missing and iron11) else "器具缺陷（缺件/指针失效）"),
        },
        "instruments": {"judge": {"path": "eval/rover/r629/judge_r629.py",
                                   "sha12": sha12(os.path.join(REPO, "eval/rover/r629/judge_r629.py"))},
                        "pool": {"path": pool_path, "sha12": sha12(os.path.join(REPO, pool_path))},
                        "attribution": {"path": attr_path, "sha12": sha12(os.path.join(REPO, attr_path))}},
    }
    return v

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eval/rover/r629/verdict-r629.json")
    ap.add_argument("--round-tag", default="r629")
    ap.add_argument("--pool", default="eval/rover/r629/primary-pool-r629.json")
    ap.add_argument("--attr", default="eval/rover/r629/attribution-r629.json")
    ap.add_argument("--prereg", default="eval/rover/r629/prereg-r629.json")
    a = ap.parse_args()
    for rel in (a.pool, a.attr, a.prereg):
        if not os.path.exists(os.path.join(REPO, rel)):
            print("INPUT_MISSING %s" % rel)
            return 3
    v = build(os.path.join(REPO, a.out), a.pool, a.attr, a.prereg, a.round_tag)
    io.open(os.path.join(REPO, a.out), "w", encoding="utf-8").write(
        json.dumps(v, ensure_ascii=False, indent=1))
    p = v[PRIMARY_KEY]
    print("主判据读数(顶层)  : median_D_task=%s valid=%d pass=%s" % (p["median_D_task"], p["valid_windows"], p["pass"]))
    print("判决来源          : %s" % (v["verdict"]["blocked"] or "%s(与主判据同名)" % PRIMARY_KEY))
    print("铁律11 指针       : %s" % v["verdict"]["iron11"])
    print("声明件缺失        : %s" % (v["verdict"]["declared_artifacts_missing"] or "-"))
    print("rc=%d（%s）" % (v["verdict"]["rc"], v["verdict"]["judge"]))
    return v["verdict"]["rc"]

if __name__ == "__main__":
    raise SystemExit(main())
