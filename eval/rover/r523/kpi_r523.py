#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R523 KPI 表 (n=3 窗口): 按 (调用数 / 新算 prompt / completion) 分列, 主判据 = 调用数。

口径 (承 R521 校正, R522 落地):
  · 禁用: 名义 `total_tokens` 当唯一判据 (把近免费 cached 当全额, 被每步重发放大) ⇒ 只作分列留档
  · new_prompt = prompt_tokens - cached_tokens;  hit% = cached/prompt
  · 有效 token = new_prompt + completion (与远端计费正相关的量)
  · 主判据 = 调用数 (R413 的用户意图: 「主要是不必要的 llm api 请求少了」)
  · n=3 ⇒ 报**逐窗**读数 + 中位数 + 极差 (禁只报中位数, 禁跨轮相减)
输出: kpi-r523.json + 机检判决; rc=0 仅当 C2 (质量) 与 C3 (调用, 主判据) 双过。
"""
from __future__ import annotations
import argparse, glob, io, json, os, statistics, sys

REPO = "/home/agentuser/AgentFramework"
ARMS = ("A0-off", "A1-on", "C-codex")


def load_rows():
    rows = []
    for p in sorted(glob.glob(os.path.join(REPO, "eval/rover/r523/evidence/windows/*/report.json"))):
        win = os.path.basename(os.path.dirname(p))
        d = json.load(io.open(p, encoding="utf-8")) or {}
        for r in (d.get("rows") or []):
            r["_win"] = win
            rows.append(r)
    return rows


def agg(rows, win, arm):
    rs = [r for r in rows if r.get("_win") == win and r.get("arm") == arm]
    calls = sum(int(r.get("calls") or 0) for r in rs)
    pt = sum(int(r.get("prompt_tokens") or 0) for r in rs)
    ct = sum(int(r.get("cached_tokens") or 0) for r in rs)
    comp = sum(int(r.get("completion_tokens") or 0) for r in rs)
    return {"window": win, "arm": arm, "runs": len(rs),
            "cases_pass": sum(int(r.get("cases_pass") or 0) for r in rs),
            "cases_total": sum(int(r.get("cases_total") or 0) for r in rs),
            "all_pass": all(bool(r.get("all_pass")) for r in rs) if rs else None,
            "calls": calls, "new_prompt": pt - ct, "cached_prompt": ct, "prompt_tokens": pt,
            "hit_pct": round(100.0 * ct / pt, 1) if pt else None, "completion": comp,
            "effective_tokens": (pt - ct) + comp, "nominal_tokens": pt + comp,
            "upstream_total_tokens": sum(int(r.get("total_tokens") or 0) for r in rs),
            "unreported_usage": sum(int(r.get("unreported_usage") or 0) for r in rs),
            "snapshot_empty": sum(1 for r in rs if r.get("snapshot_empty")),
            "models": sorted({m for r in rs for m in (r.get("models") or [])})}


def med(vals):
    v = [x for x in vals if x is not None]
    return round(statistics.median(v), 3) if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default=os.path.join(REPO, "eval/rover/r523/prereg-r523.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = load_rows()
    wins = sorted({r["_win"] for r in rows})
    tab = {w: {arm: agg(rows, w, arm) for arm in ARMS} for w in wins}
    pr = json.load(io.open(a.prereg, encoding="utf-8"))
    pred = pr.get("predictions") or {}

    def ratio(x, y):
        return round(float(x) / y, 3) if y else None

    per = {}
    for w in wins:
        A1, A0, C = tab[w]["A1-on"], tab[w]["A0-off"], tab[w]["C-codex"]
        per[w] = {
            "A1_over_codex": {"calls": ratio(A1["calls"], C["calls"]),
                              "new_prompt": ratio(A1["new_prompt"], C["new_prompt"]),
                              "completion": ratio(A1["completion"], C["completion"]),
                              "effective_tokens": ratio(A1["effective_tokens"], C["effective_tokens"]),
                              "nominal_tokens": ratio(A1["nominal_tokens"], C["nominal_tokens"])},
            "A1_over_A0": {"calls": ratio(A1["calls"], A0["calls"]),
                           "new_prompt": ratio(A1["new_prompt"], A0["new_prompt"]),
                           "completion": ratio(A1["completion"], A0["completion"]),
                           "effective_tokens": ratio(A1["effective_tokens"], A0["effective_tokens"])}}

    m = {}
    for key, field in (("calls", "calls"), ("new_prompt", "new_prompt"), ("completion", "completion"),
                       ("effective_tokens", "effective_tokens"), ("nominal_tokens", "nominal_tokens")):
        m[key] = {arm: med([tab[w][arm][field] for w in wins]) for arm in ARMS}
    med_ratio = {"A1_over_codex": {k: ratio(m[k]["A1-on"], m[k]["C-codex"]) for k in m},
                 "A1_over_A0": {k: ratio(m[k]["A1-on"], m[k]["A0-off"]) for k in m}}
    extremes = {k: {"A1_over_codex": [per[w]["A1_over_codex"].get(k) for w in wins],
                    "A1_over_A0": [per[w]["A1_over_A0"].get(k) for w in wins]}
                for k in ("calls", "effective_tokens", "nominal_tokens")}

    thr = 1 - pred.get("calls_drop_pct_min", 30) / 100.0
    thr_t = 1 - pred.get("token_drop_pct_min", 30) / 100.0
    models = sorted({x for w in wins for arm in ARMS for x in tab[w][arm]["models"]})
    quality_ok = all(tab[w]["A1-on"]["cases_pass"] == tab[w]["A1-on"]["cases_total"] == 58
                     and tab[w]["A1-on"]["cases_pass"] >= tab[w]["A0-off"]["cases_pass"]
                     and tab[w]["C-codex"]["cases_pass"] == tab[w]["C-codex"]["cases_total"] == 58
                     for w in wins)
    verdict = {
        "C1_models_uniform": (len(models) == 1 and models[0].endswith("deepseek-chat")),
        "C2_quality_no_regression": bool(quality_ok and len(wins) == 3),
        "C3_calls_primary": (med_ratio["A1_over_codex"].get("calls") is not None
                             and med_ratio["A1_over_codex"]["calls"] <= thr),
        "C4_effective_tokens": (med_ratio["A1_over_codex"].get("effective_tokens") is not None
                                and med_ratio["A1_over_codex"]["effective_tokens"] <= thr_t),
        "C5_nominal_tokens": (med_ratio["A1_over_codex"].get("nominal_tokens") is not None
                              and med_ratio["A1_over_codex"]["nominal_tokens"] <= thr_t),
        "C6_ablation_any_dim_leq_thr": any(
            (med_ratio["A1_over_A0"].get(k) is not None and med_ratio["A1_over_A0"][k] <= thr)
            for k in ("calls", "effective_tokens")),
    }
    blob = {"round": "R523", "windows": wins, "thresholds": {"calls_ratio_max": thr, "token_ratio_max": thr_t,
                                                             "prereg": pred},
            "per_window": tab, "ratios_per_window": per, "medians": m, "median_ratios": med_ratio,
            "per_window_ratio_extremes": extremes, "models": models, "verdict": verdict,
            "criteria": pr.get("criteria"), "main_judge": "C3 (远端调用数下降) ; C2 为质量门"}
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")

    hdr = "%-8s %-6s %-9s %6s %10s %10s %8s %11s" % ("arm", "win", "cases", "calls", "new_prompt", "cached", "hit%", "completion")
    print(hdr); print("-" * len(hdr))
    for w in wins:
        for arm in ARMS:
            x = tab[w][arm]
            print("%-8s %-6s %-9s %6d %10d %10d %8s %11d" % (arm, w, "%s/%s" % (x["cases_pass"], x["cases_total"]),
                                                             x["calls"], x["new_prompt"], x["cached_prompt"],
                                                             x["hit_pct"], x["completion"]))
    print("median_ratios A1/codex:", json.dumps(med_ratio["A1_over_codex"], ensure_ascii=False))
    print("median_ratios A1/A0   :", json.dumps(med_ratio["A1_over_A0"], ensure_ascii=False))
    print("per-window calls ratio A1/codex:", [per[w]["A1_over_codex"]["calls"] for w in wins])
    print("per-window calls ratio A1/A0   :", [per[w]["A1_over_A0"]["calls"] for w in wins])
    print("verdict:", json.dumps(verdict, ensure_ascii=False))
    print("KPI_MAIN_PASS=%s" % bool(verdict["C2_quality_no_regression"] and verdict["C3_calls_primary"]))
    return 0 if (verdict["C2_quality_no_regression"] and verdict["C3_calls_primary"]) else 1


if __name__ == "__main__":
    sys.exit(main())
