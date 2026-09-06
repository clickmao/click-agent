#!/usr/bin/env python3
"""round 对比分析 — 当前 round vs 基准 round: token/时长/通过率/用例级差异 + ledger 追加"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUNDS = os.path.join(ROOT, "data/logs/eval/rounds")
LEDGER = os.path.join(ROOT, "data/logs/eval/ledger.jsonl")

def load(rnd):
    p = os.path.join(ROUNDS, f"{rnd}.json")
    if not os.path.exists(p):
        sys.exit(f"round 不存在: {p}")
    return json.load(open(p))

def cmp(cur, base):
    dt = cur["tokens_total"] - base["tokens_total"]
    dpct = (dt / base["tokens_total"] * 100) if base["tokens_total"] else 0
    dw = cur["wall_total_ms"] - base["wall_total_ms"]
    print(f"tokens: {base['tokens_total']} → {cur['tokens_total']}  ({dt:+d}, {dpct:+.1f}%)")
    print(f"wall:   {base['wall_total_ms']}ms → {cur['wall_total_ms']}ms  ({dw:+d}ms)")
    print(f"passed: {base['passed']}/{base['cases']} → {cur['passed']}/{cur['cases']}")
    by_base = {x["id"]: x for x in base["results"]}
    regress, improve = [], []
    for x in cur["results"]:
        b = by_base.get(x["id"])
        if not b:
            continue
        if b["pass"] and not x["pass"]:
            regress.append(x["id"])
        if not b["pass"] and x["pass"]:
            improve.append(x["id"])
        if b["pass"] and x["pass"]:
            tdiff = x["total_tokens"] - b["total_tokens"]
            if abs(tdiff) > 50:
                print(f"  ~ {x['id']}: tokens {b['total_tokens']}→{x['total_tokens']} ({tdiff:+d})")
    if improve:
        print("improved:", ", ".join(improve))
    if regress:
        print("REGRESSED:", ", ".join(regress))
    return {"tokens_delta": dt, "tokens_pct": round(dpct, 1), "wall_delta_ms": dw,
            "improved": improve, "regressed": regress}

def main():
    cur_r = sys.argv[1]
    base_r = sys.argv[2] if len(sys.argv) > 2 else "baseline"
    cur, base = load(cur_r), load(base_r)
    print(f"=== {cur_r} vs {base_r} (label: {cur.get('label','')})")
    d = cmp(cur, base)
    # verdict: 回退判定 — 通过率降 或 token 劣化>15% → REVERT 候选
    verdict = "KEEP"
    if d["regressed"]:
        verdict = "REVERT"
    elif cur["passed"] < base["passed"]:
        verdict = "REVERT"
    elif d["tokens_pct"] > 15:
        verdict = "REVIEW"
    print("verdict:", verdict)
    entry = {"round": cur_r, "base": base_r, "label": cur.get("label", ""),
             "passed": f"{cur['passed']}/{cur['cases']}", "tokens": cur["tokens_total"],
             "verdict": verdict, **d}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("ledger:", LEDGER)

if __name__ == "__main__":
    main()
