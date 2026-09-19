#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R589 成本读数面（只读 adapter 逐调用 dump；供六格 KPI 表的成本列）。

臂: agentD（产品默认档）/ codex（外部真值）。回合: r585..r588 + 并池合计。
归属: `logs/runs.jsonl` 的 per-run `range`（逐字取, 不重算窗口）。
口径: 调用数=有 usage 的调用记录数（request_id 去重由 dump 本身保证: 1 文件 1 调用）;
      新算 prompt = prompt_cache_miss_tokens; 命中 prompt = prompt_cache_hit_tokens;
      未上报 = usage 缺这两键 ⇒ 单列 `unreported`, 不按 0 计入;
      命中率 = hit/(hit+miss)，仅在有上报的调用上算（v_all 口径）。
"""
from __future__ import annotations

import glob
import io
import json
import os

RUNS = os.path.expanduser("~/.agentframework/harness/runs")
ROUNDS = ["r585", "r586", "r587", "r588"]
ARMS = {"agentD": ("agent", "side-agent"), "codex": ("codex", "side-codex")}  # sub 前缀匹配: 产品臂 sub=agentD-r1/r2/r3


def rd(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8", errors="replace"))
    except Exception:
        return default


def usage_of(d):
    u = (d.get("response") or {}).get("usage") or {}
    return u


def agg_calls(paths):
    out = {"calls": 0, "prompt_total": 0, "new_prompt": 0, "hit_prompt": 0,
           "completion_total": 0, "unreported": 0, "untagged": 0, "reported_calls": 0}
    for p in paths:
        d = rd(p)
        if not isinstance(d, dict):
            continue
        u = usage_of(d)
        out["calls"] += 1
        out["prompt_total"] += int(u.get("prompt_tokens") or 0)
        out["completion_total"] += int(u.get("completion_tokens") or 0)
        if "prompt_cache_hit_tokens" in u or "prompt_cache_miss_tokens" in u:
            out["reported_calls"] += 1
            out["hit_prompt"] += int(u.get("prompt_cache_hit_tokens") or 0)
            out["new_prompt"] += int(u.get("prompt_cache_miss_tokens") or 0)
        else:
            out["unreported"] += 1
    tot = out["hit_prompt"] + out["new_prompt"]
    out["hit_rate_v_all"] = round(out["hit_prompt"] / tot, 4) if tot else None
    return out


def main():
    res = {"rounds": [], "pooled": {}}
    pooled = {a: [] for a in ARMS}
    for r in ROUNDS:
        rd_ = os.path.join(RUNS, r)
        runs = [json.loads(l) for l in io.open(os.path.join(rd_, "logs/runs.jsonl"), encoding="utf-8", errors="replace") if l.strip()]
        row = {"round": r, "runs_total": len(runs), "arms": {}}
        for arm, (sub, pref) in ARMS.items():
            fs = sorted(glob.glob(os.path.join(rd_, "adapter", pref + "-*.json")))
            mine = [f for f in fs if any(str(r.get("sub") or "").startswith(sub) and r.get("range")
                                         and int(os.path.basename(f).split("-")[-1].split(".")[0]) >= r["range"][0]
                                         and int(os.path.basename(f).split("-")[-1].split(".")[0]) < r["range"][1]
                                         for r in runs)]
            a = agg_calls(mine)
            a["unattributed"] = len(fs) - len(mine)
            a["runs"] = sum(1 for run in runs if str(run.get("sub") or "").startswith(sub))
            row["arms"][arm] = a
            pooled[arm].extend(mine)
        res["rounds"].append(row)
    for arm in ARMS:
        res["pooled"][arm] = agg_calls(pooled[arm])
        res["pooled"][arm]["runs"] = sum(r["arms"][arm]["runs"] for r in res["rounds"])
    # 盘上全量（含未被 runs.jsonl 覆盖者 ⇒ 暴露 untagged）
    for arm, (sub, pref) in ARMS.items():
        allf = []
        for r in ROUNDS:
            allf.extend(glob.glob(os.path.join(RUNS, r, "adapter", pref + "-*.json")))
        res.setdefault("disk_total", {})[arm] = agg_calls(allf)
    out = os.path.join("/home/agentuser/AgentFramework/eval/rover/r589", "cost-by-arm-r589.json")
    io.open(out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    for r in res["rounds"]:
        print(r["round"], {a: (r["arms"][a]["calls"], r["arms"][a]["new_prompt"], r["arms"][a]["completion_total"],
                               r["arms"][a]["hit_rate_v_all"], "unrep=%d" % r["arms"][a]["unreported"]) for a in ARMS})
    print("pooled", {a: (res["pooled"][a]["calls"], res["pooled"][a]["new_prompt"], res["pooled"][a]["completion_total"],
                         res["pooled"][a]["hit_rate_v_all"]) for a in ARMS})
    print("disk_total", {a: res["disk_total"][a]["calls"] for a in ARMS})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
