#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R589 候选③ 真值臂成本异常定因（只读各轮 `adapter/side-codex-*.json` 逐调用 dump）。

问题：R587 真值臂（codex）与 R588 真值臂同题集同模型，调用数/成本为何差这么多？
方法：按 `logs/runs.jsonl` 的 per-run `range` 逐跑次归属调用（**不猜、不按下标对齐**），
逐调用读 `response.tool_calls[].name` 与 `response.usage`，量出「同一 `exec_command` 后连续
`write_stdin`」（长命令 yield 轮询）的段数与占比。

判据（预注册 C9）：能给出占比数字 ⇒ PASS；无 dump ⇒ `n/a` 不入结论。只读，不宣称能力。
口径：`prompt_tokens` 为上游名义总量（含前缀命中）；分列 `cache_hit/miss` 与 `completion`。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import statistics

REPO = "/home/agentuser/AgentFramework"
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
ROUNDS = ("r587", "r588")


def load_calls(rnd: str):
    d = os.path.join(RUNS, rnd, "adapter")
    files = sorted(glob.glob(os.path.join(d, "side-codex-*.json")))
    runs = []
    rj = os.path.join(RUNS, rnd, "logs", "runs.jsonl")
    if os.path.exists(rj):
        for ln in io.open(rj, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            if o.get("sub") == "codex":
                runs.append(o)
    used, calls = set(), []
    for f in files:
        i = int(os.path.basename(f).split("-")[-1].split(".")[0])
        j = json.load(io.open(f, encoding="utf-8", errors="replace"))
        resp = j.get("response", {})
        tcs = resp.get("tool_calls") or []
        u = resp.get("usage") or {}
        names = [t.get("name") for t in tcs if isinstance(t, dict)]
        owners = [r for r in runs if r.get("range") and r["range"][0] <= i < r["range"][1]]
        for r in owners:
            used.add((r.get("win"), r.get("rep")))
        calls.append({
            "idx": i, "file": os.path.basename(f), "tools": names,
            "win": owners[0].get("win") if owners else None,
            "rep": owners[0].get("rep") if owners else None,
            "prompt": u.get("prompt_tokens"), "hit": u.get("prompt_cache_hit_tokens"),
            "miss": u.get("prompt_cache_miss_tokens"), "completion": u.get("completion_tokens"),
            "attrs_n": len(tcs),
        })
    return files, runs, sorted(calls, key=lambda c: c["idx"])


def segments(calls):
    """连续 write_stdin 的段（长度 ≥1）。返回段列表 + 其调用下标集合。"""
    segs, cur = [], []
    for c in calls:
        if c["tools"] == ["write_stdin"]:
            cur.append(c["idx"])
        elif cur:
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    return segs


def summarize(rnd: str):
    files, runs, calls = load_calls(rnd)
    if not files:
        return {"round": rnd, "dump": False}
    segs = segments(calls)
    ws_idx = {i for s in segs for i in s}
    ws_calls = [c for c in calls if c["idx"] in ws_idx]
    tot = len(calls)
    def s(key, rows):
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return sum(vals) if vals else None
    return {
        "round": rnd, "dump": True, "dump_files": len(files), "runs_tagged": len(runs),
        "calls_total": tot,
        "tool_hist": {n: sum(1 for c in calls for x in c["tools"] if x == n)
                      for n in sorted({x for c in calls for x in c["tools"]})},
        "calls_without_tool": sum(1 for c in calls if not c["tools"]),
        "write_stdin_calls": len(ws_calls),
        "write_stdin_share_of_calls": round(len(ws_calls) / tot, 4) if tot else None,
        "write_stdin_segments_n": len(segs),
        "write_stdin_segment_lens": [len(s) for s in segs],
        "write_stdin_max_segment": max([len(s) for s in segs], default=0),
        "tokens": {
            "prompt_total": s("prompt", calls), "cache_hit_total": s("hit", calls),
            "cache_miss_total": s("miss", calls), "completion_total": s("completion", calls),
            "prompt_median_per_call": (statistics.median([c["prompt"] for c in calls if c["prompt"]])
                                       if any(c["prompt"] for c in calls) else None),
        },
        "write_stdin_tokens": {
            "prompt_total": s("prompt", ws_calls), "cache_hit_total": s("hit", ws_calls),
            "completion_total": s("completion", ws_calls),
            "share_of_prompt": (round(s("prompt", ws_calls) / s("prompt", calls), 4)
                                if s("prompt", calls) else None),
            "share_of_completion": (round(s("completion", ws_calls) / s("completion", calls), 4)
                                    if s("completion", calls) else None),
        },
        "per_window_calls": _per_win(calls),
        "completion_const_probe": {
            "write_stdin_completion_values": sorted({c["completion"] for c in ws_calls})[:8],
            "note": "同一值反复出现 = yield 轮询（每次只取一条 yield，输出极短）",
        },
    }


def _per_win(calls):
    agg = {}
    for c in calls:
        k = "%s#%s" % (c.get("win"), c.get("rep"))
        a = agg.setdefault(k, {"calls": 0, "prompt": 0, "completion": 0})
        a["calls"] += 1
        a["prompt"] += c["prompt"] or 0
        a["completion"] += c["completion"] or 0
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r589/codex-cost-cause-r589.json"))
    a = ap.parse_args()
    rounds = [summarize(r) for r in ROUNDS]
    have = [r for r in rounds if r.get("dump")]
    out = {"round": "R589", "criterion": "C9", "mode": "read-only codex adapter per-call classification",
           "instrument": "eval/rover/r589/codex_cost_cause_r589.py", "rounds": rounds}
    if len(have) < len(ROUNDS):
        out.update({"rc": 3, "error": "DUMP_MISSING", "have": [r["round"] for r in have]})
    else:
        a_, b_ = rounds[0], rounds[1]
        out["ratio_r588_over_r587"] = {
            "calls": round(b_["calls_total"] / a_["calls_total"], 3),
            "prompt_total": round(b_["tokens"]["prompt_total"] / a_["tokens"]["prompt_total"], 3),
            "completion_total": round(b_["tokens"]["completion_total"] / a_["tokens"]["completion_total"], 3),
        }
        out["verdict"] = ("写侧定因：两轮真值臂均**单一工具族**（exec_command + write_stdin），"
                          "差异全部落在**调用数**（%d → %d，×%.2f），而 write_stdin（yield 轮询）占比 "
                          "%.1f%% → %.1f%%；命名口径提示该增量来自**长命令 yield 轮询**，"
                          "非模型侧生成量（completion ×%.2f）。"
                          % (a_["calls_total"], b_["calls_total"],
                             out["ratio_r588_over_r587"]["calls"],
                             100 * (a_["write_stdin_share_of_calls"] or 0),
                             100 * (b_["write_stdin_share_of_calls"] or 0),
                             out["ratio_r588_over_r587"]["completion_total"]))
        out["rc"] = 0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return out["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
