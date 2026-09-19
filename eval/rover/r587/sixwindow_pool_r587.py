#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R587 · ⑤ 六窗并列（禁相减）+ ④ 成本按跑次归一 + ③ 有效窗下限口径收口。

读入 = 已登记的两轮判决件（`verdict-r586.json` / `verdict-r587.json` / `verdict-r585.json`），
**不重算任何被测读数**（跨轮禁相减, 只能并列; 配对差只在同一轮内算）。

产出:
  ① `pooled_6w`      : 6 窗 D 集（w157..w162）逐窗并列 + 中位/极差 + 逐窗偏离中位量 + 摆动估计
  ② `swing_vs_effect`: 摆动 vs 本轮窗口集效应量（判据 C5 的明文结论）
  ③ `cost_per_run`   : 三列（调用 / 新算 prompt / completion）各给 total 与 per_run（n_runs 取
                       `logs/runs.jsonl` 行数 = 外部真值），两侧跑次不等 ⇒ **禁比总量**（C8 入册）
  ④ `valid_window_floor`: 「真值自身失分窗」口径**显式二选一**后的固定条款 + `w154` 类窗历史读数并列清单（C9）
用法: python3 eval/rover/r587/sixwindow_pool_r587.py
"""
from __future__ import annotations

import io
import json
import os
import statistics

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r587/sixwindow-pool-r587.json")
RND = {"r585": "w154,w155,w156", "r586": "w157,w158,w159", "r587": "w160,w161,w162"}
HARNESS = os.path.expanduser("~/.agentframework/harness/runs")


def load_verdict(rk):
    return json.load(io.open(os.path.join(REPO, "eval/rover", rk, "verdict-%s.json" % rk), encoding="utf-8"))


def runs_n(rk):
    p = os.path.join(HARNESS, rk, "logs/runs.jsonl")
    if not os.path.isfile(p):
        return None
    return len([l for l in io.open(p, encoding="utf-8", errors="replace") if l.strip()])


def main():
    v = {rk: load_verdict(rk) for rk in RND}
    per, med = [], {}
    for rk, wins in RND.items():
        wl = wins.split(",")
        pd_ = v[rk]["paired"]
        d = pd_.get("D_product_minus_truth_per_window") or []
        unreliable = pd_.get("unreliable_windows_truth_self_fail") or []
        prod = pd_.get("product_per_window") or {}
        truth = pd_.get("truth_per_window") or {}
        # 逐窗 D 复原（D 列表按窗序, 已剔除 unreliable/missing）
        i = 0
        for w in wl:
            if w in unreliable or w in (pd_.get("missing_windows") or []):
                per.append({"round": rk, "win": w, "D": None, "unreliable": True,
                            "truth": truth.get(w), "product": prod.get(w)})
                continue
            dd = d[i] if i < len(d) else None
            i += 1
            per.append({"round": rk, "win": w, "D": dd, "unreliable": False,
                        "truth": truth.get(w), "product": prod.get(w)})
        med[rk] = {"D_set": d, "median": pd_.get("D_median"), "valid_windows": pd_.get("valid_windows"),
                   "unreliable": unreliable}

    vals = [x["D"] for x in per if x["D"] is not None]
    pool_med = statistics.median(vals) if vals else None
    dev = [round(x["D"] - pool_med, 2) for x in per if x["D"] is not None]
    swing = (max(vals) - min(vals)) if vals else None
    max_dev = max(abs(x) for x in dev) if dev else None

    # 本轮窗集 vs 上一轮窗集的效应量（同号性/区间重叠 → C5 状态）
    m86, m87 = med["r586"]["median"], med["r587"]["median"]
    effect = round(m87 - m86, 2) if (m86 is not None and m87 is not None) else None
    d86, d87 = med["r586"]["D_set"], med["r587"]["D_set"]
    same_sign = bool(d86 and d87 and (max(d86) <= 0 and max(d87) <= 0 or min(d86) >= 0 and min(d87) >= 0))
    overlap = bool(d86 and d87 and min(max(d86), max(d87)) >= max(min(d86), min(d87)))
    state = ("缺口跨窗复现" if (same_sign and overlap) else
             "方向一致、量级漂移" if same_sign else "未复现（单窗集摆动）")

    # ④ 成本按跑次归一（两侧跑次不等 ⇒ 禁比总量）
    cost = {}
    for rk in RND:
        f_lines = runs_n(rk)
        arms_d = v[rk].get("arms") or {}
        n_codex = (arms_d.get("C1") or {}).get("runs")
        prod_arm = next((k for k in arms_d if k != "C1"), None)   # 各轮产品臂名不同 (R585D/R586D/R587D)
        for arm, key in (("C1", "C1"), (prod_arm, "PROD")):
            a = arms_d.get(arm)
            if not a:
                continue
            n = a.get("runs") or 0          # 本臂跑次数（外部真值: 归档/发送面计数）
            # 成对断言: 文件行数 == 两侧跑次数之和（不符 ⇒ 读数标口径缺陷, 不静默）
            consistent = (f_lines is not None and n_codex is not None and prod_arm is not None and
                          f_lines == n_codex + (arms_d.get(prod_arm) or {}).get("runs", 0))
            cost.setdefault(key, {})[rk] = {
                "runs": n, "runs_jsonl_lines": f_lines, "runs_jsonl_consistent": consistent,
                "calls": a.get("calls"), "new_prompt": a.get("new_prompt"), "completion": a.get("completion"),
                "calls_per_run": round(a["calls"] / n, 2) if n else None,
                "new_prompt_per_run": round(a["new_prompt"] / n, 1) if n else None,
                "completion_per_run": round(a["completion"] / n, 1) if n else None,
                "v_all_med": a.get("v_all_med"), "v_incr_med": a.get("v_incr_med"),
                "cases_per_run": a.get("cases_per_run"),
            }
    cost["note"] = ("两侧跑次不等（C1=3/轮, 产品=9/轮）⇒ **禁比总量**; per_run = total / 本臂跑次数; "
                    "runs_jsonl_consistent 为成对断言（文件行数 == 两侧跑次之和）。")

    out = {
        "round": "R587",
        "instrument": "eval/rover/r587/sixwindow_pool_r587.py",
        "mode": "read_only（读已登记判决件；跨轮禁相减, 只并列）",
        "pooled_6w": {"per_window": per, "D_values": vals, "median": pool_med,
                      "min": min(vals) if vals else None, "max": max(vals) if vals else None,
                      "spread": swing, "deviation_from_pool_median": dev, "max_abs_deviation": max_dev,
                      "note": "D = median_reps(产品) − codex 真值, 同轮内算; 跨轮只并列。"},
        "per_round_sets": med,
        "swing_vs_effect": {
            "this_round_window_set": "w160..w162", "prev_round_window_set": "w157..w159",
            "prev_median": m86, "this_median": m87, "effect_vs_prev_set": effect,
            "swing_over_pooled_6w": swing, "max_abs_deviation": max_dev,
            "same_sign": same_sign, "interval_overlap": overlap, "state": state,
            "rule": "摆动 >= 效应 ⇒ 明文写「摆动 ≥ 效应 ⇒ 单窗不作能力结论，需更多窗」（预注册 C5 原文）",
            "call": ("摆动 ≥ 效应 ⇒ 单窗不作能力结论，需更多窗"
                     if (swing is not None and effect is not None and swing >= abs(effect))
                     else "摆动 < 效应 ⇒ 本窗口集可作方向性结论（仍不得作单点承诺）"),
        },
        "cost_per_run": cost,
        "valid_window_floor": {
            "decision_key": "真值自身失分窗（truth_cases 未达满分的窗）如何计入",
            "explicit_choice": "剔除出配对 ∧ 单列该窗读数 ∧ 不记我方缺陷",
            "why_fixed": "两种解释会产出不同交付物（剔除 vs 单列并计入 D）⇒ 预注册里显式二选一后**固定**，非事后解释",
            "applied_this_round": med["r587"]["unreliable"],
            "historical_parallel_readings": [
                {"round": "r585", "unreliable": v["r585"]["paired"].get("unreliable_windows_truth_self_fail"),
                 "D_set": v["r585"]["paired"].get("D_product_minus_truth_per_window"),
                 "median": v["r585"]["paired"].get("D_median"),
                 "truth_per_window": v["r585"]["paired"].get("truth_per_window"),
                 "note": "w154 类窗（真值自身失分）历史读数**并列**, 不重算、不相减"},
                {"round": "r586", "unreliable": med["r586"]["unreliable"], "D_set": med["r586"]["D_set"],
                 "median": med["r586"]["median"]},
                {"round": "r587", "unreliable": med["r587"]["unreliable"], "D_set": med["r587"]["D_set"],
                 "median": med["r587"]["median"]},
            ],
        },
    }
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"pooled": {"D": vals, "median": pool_med, "spread": swing, "max_dev": max_dev},
                      "sets": {k: (x["median"], x["D_set"]) for k, x in med.items()},
                      "swing_vs_effect": out["swing_vs_effect"]["call"],
                      "state": state,
                      "cost_per_run": cost}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
