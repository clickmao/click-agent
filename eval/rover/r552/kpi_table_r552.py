#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R552 KPI 表: 逐臂 (调用Σ / 新算 promptΣ / completionΣ / 命中率 / 有效窗 / 全对窗) —— 供报告直接引用。"""
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
WINS = {"R552b0": [30, 31, 32, 39, 40, 41, 49, 50, 51],
        "R552b1": [33, 34, 35, 43, 44, 45, 52, 53, 54],
        "R552b2": [36, 37, 38, 46, 47, 48, 55, 56, 57]}
d = json.load(io.open(os.path.join(REPO, "eval/rover/r552/readings-r552.json"), encoding="utf-8"))
rows = []
for a, ws in WINS.items():
    calls = prompt = comp = hit = miss = 0
    missing = []
    for w in ws:
        r = d["windows"].get("w%d" % w, {}).get(a)
        if not r:
            missing.append(w)
            continue
        calls += r["calls"] or 0
        prompt += r["prompt_tokens"] or 0
        comp += r["completion_tokens"] or 0
        hit += r["cache_hit_tokens"] or 0
        miss += r["cache_miss_tokens"] or 0
    h = d["hitrate"][a]
    v_all = 1.0 * (1 - h["rows"][0]["sum_miss_tok"] / h["rows"][0]["sum_prompt_tok"]) if False else None
    art = [r for r in (d["windows"].get("w%d" % w, {}).get(a) for w in ws) if r and r["cases"] and r["cases"]["total"]]
    pre = [r for r in art if not r["void"]]
    rows.append({"arm": a, "windows": len(ws), "missing": missing, "calls_sum": calls,
                 "prompt_sum": prompt, "completion_sum": comp, "new_prompt_sum": prompt - hit,
                 "hit_sum": hit, "miss_sum": miss,
                 "hitrate_transcript": round(1.0 * hit / prompt, 4) if prompt else None,
                 "windows_with_artifact": len(art), "prereg_valid_windows": len(pre),
                 "full_mark_windows": sum(1 for r in art if r["cases"]["pass"] == r["cases"]["total"]),
                 "quality_artifact": ["%d/%d" % (r["cases"]["pass"], r["cases"]["total"]) for r in art],
                 "quality_prereg": ["%d/%d" % (r["cases"]["pass"], r["cases"]["total"]) for r in pre]})
print(json.dumps(rows, ensure_ascii=False, indent=1))
json.dump(rows, io.open(os.path.join(REPO, "eval/rover/r552/kpi-table-r552.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
