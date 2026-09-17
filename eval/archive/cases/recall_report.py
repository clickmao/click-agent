#!/usr/bin/env python3
"""多源召回率定量报告 — 聚合 all rounds 的 assembly 点位 (从真机 telemetry 归档) 或跑一轮现场统计。
直接统计: eval/results/*.json 里 per-case snippets + sources 命中。"""
import json, os, sys, glob

ROUNDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/logs/eval/rounds")

def main():
    files = sorted(glob.glob(os.path.join(ROUNDS, "*.json")))
    print(f"rounds: {len(files)}")
    # 每轮 passed 用例的总 snippet 数 / 有 snippet 用例占比
    for f in files:
        d = json.load(open(f))
        snips = [x.get("snippets", 0) for x in d["results"]]
        total = sum(snips)
        hit = sum(1 for s in snips if s > 0)
        print(f"  {os.path.basename(f)[:-5]:18s} passed={d['passed']}/{d['cases']} "
              f"snippet_total={total} cases_with_context={hit}/{d['cases']}")

if __name__ == "__main__":
    main()
