#!/usr/bin/env python3
"""阶段级对比: 早期轮均值 vs 近期轮均值 (tokens/wall/pass), 判定整体趋势。
v0.11.0 R37: 固化中期分析 — 每若干轮跑一次, 输出阶段演进。"""
import glob
import json
import statistics
import sys

ROUNDS = "data/logs/eval/rounds"


def load_full_rounds():
    """全部 10/10 用例的全量轮 (排除 quick/失败轮, 但失败轮单独标注)。"""
    def round_num(path):
        import re
        m = re.search(r"round(\d+)\.json$", path)
        return int(m.group(1)) if m else 0

    rows = []
    for f in sorted(glob.glob(f"{ROUNDS}/round*.json"), key=round_num):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if "passed" not in d:
            continue
        rows.append({
            "round": d["round"], "passed": d["passed"], "cases": d["cases"],
            "tokens": d["tokens_total"], "wall": d["wall_total_ms"] / 1000,
            "label": d.get("label", ""),
        })
    return rows


def split_phases(rows):
    ok = [r for r in rows if r["passed"] == r["cases"] == 10]
    half = max(1, len(ok) // 2)
    return ok[:half], ok[half:]


def phase_stats(phase):
    return (statistics.mean(r["tokens"] for r in phase),
            statistics.mean(r["wall"] for r in phase))


def main():
    rows = load_full_rounds()
    if not rows:
        print("无 round 数据")
        return
    early, late = split_phases(rows)
    et, ew = phase_stats(early)
    lt, lw = phase_stats(late)
    print(f"全量轮: {len(rows)} (全部通过 {sum(1 for r in rows if r['passed']==r['cases']==10)})")
    fails = [f"{r['round']}({r['passed']}/{r['cases']})" for r in rows if r["passed"] != r["cases"]]
    if fails:
        print("含失败轮:", ", ".join(fails))
    print(f"\n早期 (n={len(early)}): {' '.join(r['round'] for r in early[:4])} … {early[-1]['round']}")
    print(f"  tokens 均值 {et:.0f}  wall 均值 {ew:.1f}s")
    print(f"近期 (n={len(late)}): {' '.join(r['round'] for r in late[:4])} … {late[-1]['round']}")
    print(f"  tokens 均值 {lt:.0f} ({(lt/et-1)*100:+.1f}%)  wall 均值 {lw:.1f}s ({(lw/ew-1)*100:+.1f}%)")
    trend = "改善" if lt < et and lw < ew else ("回归" if lt > et * 1.15 or lw > ew * 1.15 else "持平")
    print(f"\n阶段判定: {trend}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
