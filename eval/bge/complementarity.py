#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""互补性分析: 稠密检索相对词法基线到底加了什么? (R370 焦点问题)

回答三个问题:
  1. 稠密 (bge-*) 单独 vs 词法 (字符二元组 Jaccard) —— 谁赢?
  2. 稠密有没有"词法够不到"的独有命中? (dense_only_wins)
  3. 若有一个完美选择器在两者间择一, 上界是多少? (oracle@k —— **上界不是可达值**)

用法:
  python3 eval/bge/complementarity.py                     # 用 eval/bge/ranks/*.json
  python3 eval/bge/complementarity.py --ranks a.json b.json --md docs/reports/xxx.md
"""
import os
import sys
import json
import glob
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L  # noqa: E402

K = (1, 5, 10, 20)


def metrics(ranks):
    n = len(ranks)
    m = {f"r@{k}": round(sum(1 for r in ranks if r <= k) / n, 4) for k in K}
    m["mrr@10"] = round(sum(1.0 / r for r in ranks if r <= 10) / n, 4)
    m["miss@50"] = round(sum(1 for r in ranks if r > 50) / n, 4)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranks", nargs="*", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    corpus, queries = L.load_fixtures()
    lex = L.lexical_ranks(corpus, queries)
    methods = {"lexical-bigram": lex}

    paths = args.ranks or sorted(glob.glob(os.path.join(L.REPO, "eval", "bge", "ranks", "*.json")))
    loaded = []
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        if len(d["ranks"]) != len(lex):
            print(f"[skip] {p}: 秩长度 {len(d['ranks'])} != {len(lex)}", file=sys.stderr)
            continue
        methods[d["label"]] = d["ranks"]
        loaded.append(d["label"])

    lines = []
    lines.append("| 方法 | r@1 | r@5 | r@10 | r@20 | MRR@10 | miss@50 |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, rk in methods.items():
        m = metrics(rk)
        lines.append(f"| {name} | {m['r@1']} | {m['r@5']} | {m['r@10']} | {m['r@20']} | {m['mrr@10']} | {m['miss@50']} |")

    lines.append("")
    lines.append("| 对照 (基准=lexical-bigram) | dense_only_wins(≤20) | lexical_only_wins(≤20) | both_fail | union@10 | union@20 |")
    lines.append("|---|---|---|---|---|---|")
    detail = {}
    for name, rk in methods.items():
        if name == "lexical-bigram":
            continue
        d_only = sum(1 for a, b in zip(rk, lex) if a <= 20 and b > 20)
        l_only = sum(1 for a, b in zip(rk, lex) if b <= 20 and a > 20)
        both_fail = sum(1 for a, b in zip(rk, lex) if a > 20 and b > 20)
        u10 = round(sum(1 for a, b in zip(rk, lex) if min(a, b) <= 10) / len(rk), 4)
        u20 = round(sum(1 for a, b in zip(rk, lex) if min(a, b) <= 20) / len(rk), 4)
        detail[name] = {"dense_only_wins": d_only, "lexical_only_wins": l_only, "both_fail": both_fail,
                        "union@10": u10, "union@20": u20,
                        "n_lexical_miss_but_dense_hit_at50": sum(1 for a, b in zip(rk, lex) if b > 50 and a <= 20)}
        lines.append(f"| {name} vs 词法 | {d_only} | {l_only} | {both_fail} | {u10} | {u20} |")

    allrk = list(methods.values())
    detail["_oracle_all_methods"] = {f"oracle@{k}": round(sum(1 for i in range(len(lex)) if min(r[i] for r in allrk) <= k) / len(lex), 4) for k in K}
    lines.append("")
    lines.append("**全方法 oracle (完美选择器上界, 非可达值)**: " + ", ".join(f"{k}={v}" for k, v in detail["_oracle_all_methods"].items()))

    text = "\n".join(lines)
    print(text)
    print()
    print(json.dumps({"n_queries": len(lex), "methods": loaded, "detail": detail}, ensure_ascii=False, indent=2))
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write("# 稠密 vs 词法 互补性 (R370)\n\n")
            f.write("> 语料/查询冻结于 eval/bge/fixtures (1299 块 / 120 查询)。oracle 为**上界**, 非可达值。\n\n")
            f.write(text + "\n")
        print(f"[saved] {args.md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
