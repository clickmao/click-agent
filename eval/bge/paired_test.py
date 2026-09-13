#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bge 线的**配对显著性检验** (2026-09-14)。

为何需要它: 台账里所有"提升"都是**聚合百分比** (r@10 0.6333 -> 0.6667 之类),
而 n=120 的评测集里 1 条查询 = 0.83pt —— 聚合差无法回答"这是提升还是抖动"。
本脚本对**同一题集**做逐查询配对检验 (精确 McNemar), 把"提升"落到"净增几条 + p 值"。

判据 (全部可复算, 禁手抄):
  ① 复用 `fusion.py` 自己的函数重建排秩, 复算值必须与冻结报告逐位一致
     (dense-small 0.6333 / dense-base 0.7417 / fusion-best 0.85);
  ② **净增益不可能性界**: 净增 Δ 条查询时, 最小可能 McNemar p = 2^(1-Δ)
     ⇒ Δ<6 时**无论逐查询分布如何都不可能显著** (本线最好的训练版 Δ=+4 ⇒ p≥0.125)。
     这不是"没测出来", 是数学上测不出来。
输出: eval/bge/ranks/fusion-best.json (逐查询 rank, 补审计缺口)。
"""
import importlib.util
import json
import math
import os

spec = importlib.util.spec_from_file_location(
    "fusion", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion.py"))
assert spec is not None and spec.loader is not None, "fusion.py 无法作为模块装载"
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
L = F.L


def collect():
    corpus, queries = L.load_fixtures()
    ctexts = [c["text"] for c in corpus]
    qtexts = [q["query"] for q in queries]
    cids = [c["id"] for c in corpus]
    golds = [q["gold_id"] for q in queries]
    lex_rl = [F.ranks_from_scores(F.lexical_scores(corpus, q)) for q in queries]
    mt = L.model_tag()
    small_rl = [F.ranks_from_scores(s) for s in F.dense_scores(
        F.cached_vecs("fuse_corpus", ctexts, mt, L.MODEL, L.PORT),
        F.cached_vecs("fuse_queries", qtexts, mt, L.MODEL, L.PORT))]
    bmt = os.path.basename(F.BASE_MODEL).replace(".gguf", "")
    base_rl = [F.ranks_from_scores(s) for s in F.dense_scores(
        F.cached_vecs("fuse_corpus", ctexts, bmt, F.BASE_MODEL, F.PORT_BASE),
        F.cached_vecs("fuse_queries", qtexts, bmt, F.BASE_MODEL, F.PORT_BASE))]
    cpos = {c: i for i, c in enumerate(cids)}

    def grank(rls):
        return [rls[qi][cpos[golds[qi]]] for qi in range(len(golds))]

    S = {"lexical": grank(lex_rl), "dense-small": grank(small_rl), "dense-base": grank(base_rl)}
    S["fusion"] = F.rrf_all([lex_rl, base_rl], [1.0, 1.0], golds, cids, k0=10)
    return S


def mcnemar(a, b, k):
    A = [1 if r + 1 <= k else 0 for r in a]
    B = [1 if r + 1 <= k else 0 for r in b]
    x = sum(1 for i in range(len(A)) if A[i] == 1 and B[i] == 0)
    y = sum(1 for i in range(len(A)) if A[i] == 0 and B[i] == 1)
    n = x + y
    if n == 0:
        p = 1.0
    else:
        p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n)
    return x, y, n, p


def main():
    S = collect()
    tbl = {k: F.metrics_from_ranks(v) for k, v in S.items()}
    print("[判据①] 逐位对账: dense-small r@10=%s | dense-base r@10=%s | fusion r@10=%s"
          % (tbl["dense-small"]["r@10"], tbl["dense-base"]["r@10"], tbl["fusion"]["r@10"]))
    assert abs(tbl["dense-small"]["r@10"] - 0.6333) < 1e-9, tbl["dense-small"]
    assert abs(tbl["dense-base"]["r@10"] - 0.7417) < 1e-9, tbl["dense-base"]
    assert abs(tbl["fusion"]["r@10"] - 0.85) < 1e-9, tbl["fusion"]
    print("[判据①] OK 复算 == 冻结报告值")
    print("[判据②] 净增益不可能性界: 净增 Δ 条时 min p = 2^(1-Δ) -> "
          + " ".join("Δ=%d:p>=%.4f" % (d, min(1.0, 2 ** (1 - d))) for d in (2, 4, 6, 13)))
    print()
    for k in (1, 10):
        for a, b in (("fusion", "dense-base"), ("fusion", "lexical"), ("fusion", "dense-small")):
            x, y, n, p = mcnemar(S[a], S[b], k)
            print("  %-7s vs %-11s @%-2d 只A中=%2d 只B中=%2d 不一致=%2d p=%.4f %s"
                  % (a, b, k, x, y, n, p, "★显著" if p < 0.05 else "不显著"))
    out = {"label": "fusion-lexical+dense-base-k10-w11", "k0": 10, "w": "1:1",
           "n_queries": len(S["fusion"]), "metrics": tbl["fusion"],
           "ranks": [r + 1 if r + 1 <= 50 else 999 for r in S["fusion"]]}
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ranks", "fusion-best.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, "w"), indent=1)
    print("\n已落盘逐查询 rank: %s" % dst)


if __name__ == "__main__":
    main()
