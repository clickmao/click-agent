#!/usr/bin/env python3
"""KPI-2 token 周报生成器 (R324) — 每 10 批 audit 节奏运行 (与 compression audit 同节奏)。
全量重算 rounds/*.json → era 均值 / 口径细分 / top 消耗案 / 周环比。
用法: python3 eval/token_report.py [--last N]
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def load_rows():
    rows = []
    for p in glob.glob("data/logs/eval/rounds/mass_*.json"):
        mm = re.search(r"mass_(\d+)", p)
        if mm is None:
            continue
        n = int(mm.group(1))
        try:
            d = json.load(open(p))
            cases = d.get("cases", 0)
            if cases <= 0:
                continue
            rows.append({
                "mass": n,
                "cases": cases,
                "passed": d.get("passed", 0),
                "tok": d.get("tokens_total", 0) // cases,
                "prompt": d.get("prompt_total", 0) // cases,
                "completion": d.get("completion_total", 0) // cases,
                "label": d.get("label", "")[:44],
            })
        except Exception:
            continue
    rows.sort(key=lambda r: r["mass"])
    return rows


def caliber(cases, tok):
    """口径归类 (口径变更登记制度 — 可比性断点)"""
    if tok > 5000 and cases >= 20:
        return "xl"
    if cases == 3:
        return "route-3"
    if cases == 13:
        return "quick-13"
    if cases == 12:
        return "quick-12"
    if cases == 11:
        return "quick-11"
    if cases in (23, 24):
        return "explore"
    return f"n{cases}"


def main():
    last = 30
    if "--last" in sys.argv:
        last = int(sys.argv[sys.argv.index("--last") + 1])
    rows = load_rows()
    data = [r for r in rows if r["cases"] >= 4]
    print(f"KPI-2 token 周报 (R324) — 有效批 {len(data)} / 总 {len(rows)} (mass_{rows[0]['mass']}→{rows[-1]['mass']})")

    # 1. 近 N 批按口径分组
    recent = data[-last:]
    groups = {}
    for r in recent:
        groups.setdefault(caliber(r["cases"], r["tok"]), []).append(r)
    print(f"\n== 近 {last} 批按口径 ==")
    for cal in sorted(groups):
        g = groups[cal]
        toks = [r["tok"] for r in g]
        print(f"  {cal:9s} n={len(g):3d} 均值 {sum(toks)//len(toks):5d} min {min(toks):5d} max {max(toks):5d}")

    # 2. top 消耗案 (近 5 批合计)
    per_case = {}
    for r in recent[-5:]:
        p = f"data/logs/eval/rounds/mass_{r['mass']}.json"
        try:
            d = json.load(open(p))
            for x in d["results"]:
                if x.get("total_tokens", 0) > 0:
                    per_case.setdefault(x["id"], []).append(x["total_tokens"])
        except Exception:
            continue
    print("\n== Top 消耗案 (近 5 批均值) ==")
    for cid, toks in sorted(per_case.items(), key=lambda kv: -sum(kv[1]))[:8]:
        print(f"  {cid:36s} 均值 {sum(toks)//len(toks):5d} (n={len(toks)})")

    # 3. 周环比 (最近 10 批 vs 前 10 批, 同口径内)
    print("\n== 环比 (quick-11 口径, 近10 vs 前10) ==")
    q11 = [r for r in data if r["cases"] == 11 and r["tok"] <= 1500]
    if len(q11) >= 20:
        a = [r["tok"] for r in q11[-20:-10]]
        b = [r["tok"] for r in q11[-10:]]
        da = sum(a) // len(a)
        db = sum(b) // len(b)
        print(f"  前10: {da} → 近10: {db} ({db-da:+d}, {(db-da)*100//max(1,da):+d}%)")
    else:
        print(f"  quick-11 数据不足 ({len(q11)})")


if __name__ == "__main__":
    main()
