#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产品线真身口径: lex + dense-small(链上 25.2MB bge-q8) 的 r@10 —— 网格里缺的那个数。

为什么要这个: fusion-knob-grid-2026-09-14.json 的 21 个变体**全部含 dense-base(110MB)**,
登记值 0.8500 = `lex+base`; 而产品侧 (.env.local AGENTFRAMEWORK_BGE_MODEL=bge-q8.gguf,
ServiceCollectionExtensions.cs Fusion{Enabled,K0=10,W=1:1}) 的稠密路是 **small**。
⇒ 产品真实组合 = `lex+small`, 从未登记; 且 DI 注释把 small 单路基线 0.6333 与 base 融合读数 0.8500 相接。

设计 (控制组先行):
  ① 身份控制: dense-small 单路 r@10 必须 == 0.6333 / dense-base == 0.7417 (仓库冻结节账)
  ② 接线控制: `lex+base k0=10 w=1:1` 必须 == 0.8500 (复现登记网格) —— 复现不出则本脚本的数值不可信
  ③ 目标: `lex+small` 扫 k0 × w, 报 r@1/r@10/r@20/mrr@10 + 配对 McNemar 精确 p (对比 small 单路)
复用 fusion.py 的打分函数 (单一实现源, 不自造第二套)。
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L          # noqa: E402
import fusion as F           # noqa: E402

SMALL = "bge-q8"                       # ~/.agentframework/models/bge-q8.gguf
BASE = "bge-base-zh-v1.5-q8"           # /tmp/models/bge-base-zh-v1.5-q8.gguf
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results",
                   "fusion-lex-small-2026-09-14.json")
FROZEN = {"dense-small": 0.6333, "dense-base": 0.7417, "lex+base k0=10 w=1:1": 0.8500}


def cached(prefix, texts, mt):
    t = L.tag(prefix, texts, model=mt)
    v = L.cache_load(t, len(texts))
    assert v is not None, f"缓存缺失(不得重嵌入, 否则口径漂): {t}"
    return v


def gold_ranks(rl, cpos, golds):
    return [rl[qi][cpos[golds[qi]]] for qi in range(len(golds))]


def hit_set(rl, cpos, golds, k=10):
    return {qi for qi in range(len(golds)) if rl[qi][cpos[golds[qi]]] < k}


def mcnemar_exact(a, b):
    """双侧精确 McNemar: n=a+b, p = 2*sum_{i<=min(a,b)} C(n,i)/2^n (上限 1)。"""
    n = a + b
    if n == 0:
        return 1.0
    m = min(a, b)
    p = 2.0 * sum(math.comb(n, i) for i in range(m + 1)) / (2.0 ** n)
    return round(min(1.0, p), 6)


def main():
    corpus, queries = L.load_fixtures()
    ctexts = [c["text"] for c in corpus]
    qtexts = [q["query"] for q in queries]
    cids = [c["id"] for c in corpus]
    golds = [q["gold_id"] for q in queries]
    cpos = {c: i for i, c in enumerate(cids)}
    print(f"[fixtures] corpus={len(corpus)} queries={len(queries)}", flush=True)

    lex_rl = [F.ranks_from_scores(F.lexical_scores(corpus, q)) for q in queries]
    small_rl = [F.ranks_from_scores(s) for s in F.dense_scores(
        cached("fuse_corpus", ctexts, SMALL), cached("fuse_queries", qtexts, SMALL))]
    base_rl = [F.ranks_from_scores(s) for s in F.dense_scores(
        cached("fuse_corpus", ctexts, BASE), cached("fuse_queries", qtexts, BASE))]

    singles = {"lex": lex_rl, "dense-small": small_rl, "dense-base": base_rl}
    table = {k: F.metrics_from_ranks(gold_ranks(v, cpos, golds)) for k, v in singles.items()}
    for k, want in (("dense-small", FROZEN["dense-small"]), ("dense-base", FROZEN["dense-base"])):
        got = table[k]["r@10"]
        assert abs(got - want) < 1e-9, f"身份控制失败 {k}: {got} != 冻结节账 {want}"
    print(f"[①身份控制] small={table['dense-small']['r@10']} base={table['dense-base']['r@10']} "
          f"lex={table['lex']['r@10']}", flush=True)

    base_hits = hit_set(small_rl, cpos, golds)
    variants = {}

    def run(tag, routes, weights, k0):
        r = F.rrf_all(routes, list(weights), golds, cids, k0=k0)  # 直接是金标准秩(0起)
        m = F.metrics_from_ranks(r)
        h = {qi for qi, x in enumerate(r) if x < 10}
        variants[tag] = {"k0": k0, "weights": list(weights), "r@1": m["r@1"], "r@10": m["r@10"],
                         "r@20": m["r@20"], "mrr@10": m["mrr@10"],
                         "hits": len(h), "delta_vs_small": len(h) - len(base_hits),
                         "mcnemar_p_vs_dense_small": mcnemar_exact(
                             len(h - base_hits), len(base_hits - h)),
                         "routes": ["lex", "dense-small" if routes is not base_rl else "dense-base"]}
        return variants[tag]

    ctrl = run("lex+base k0=10 w=1:1", [lex_rl, base_rl], [1.0, 1.0], 10)
    assert abs(ctrl["r@10"] - FROZEN["lex+base k0=10 w=1:1"]) < 1e-9, \
        f"接线控制失败: 复现 {ctrl['r@10']} != 登记 {FROZEN['lex+base k0=10 w=1:1']}"
    assert abs(ctrl["r@1"] - 0.5333) < 1e-9, f"接线控制 r@1 失败: {ctrl['r@1']}"
    print(f"[②接线控制] lex+base k0=10 w=1:1 -> r@10={ctrl['r@10']} r@1={ctrl['r@1']} (与登记网格一致)",
          flush=True)

    for k0 in (1, 5, 10, 20, 60):
        for w in ([1.0, 1.0], [2.0, 1.0], [1.0, 2.0]):
            run(f"lex+small k0={k0} w={w[0]:g}:{w[1]:g}", [lex_rl, small_rl], w, k0)
    for k0 in (10, 60):
        for w in ([1.0, 1.0, 0.5], [1.0, 1.0, 1.0]):
            run(f"lex+base+small k0={k0} w={':'.join('%g' % x for x in w)}",
                [lex_rl, base_rl, small_rl], w, k0)

    prod = variants["lex+small k0=10 w=1:1"]
    print(f"\n[③产品真身] lex+small k0=10 w=1:1 -> r@10={prod['r@10']} hit={prod['hits']}/120 "
          f"r@1={prod['r@1']} r@20={prod['r@20']} mrr@10={prod['mrr@10']}", flush=True)
    print(f"    vs small 单路(0.6333,76/120): Δ={prod['delta_vs_small']} 条 "
          f"McNemar p={prod['mcnemar_p_vs_dense_small']}", flush=True)
    print(f"    vs 登记的 lex+base(0.8500,102/120): Δ={prod['hits'] - ctrl['hits']} 条", flush=True)

    ranked = sorted(variants.items(), key=lambda kv: (-kv[1]["r@10"], -kv[1]["r@1"]))
    print("\n=== lex+small / lex+base+small 全扫 (按 r@10 降序) ===")
    for tag, v in ranked:
        if tag.startswith("lex+small") or tag.startswith("lex+base+small"):
            print(f"{tag:34s} r@10={v['r@10']:.4f} ({v['hits']:>3}/120) r@1={v['r@1']:.4f} "
                  f"Δ={v['delta_vs_small']:+3d} p={v['mcnemar_p_vs_dense_small']}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"fixtures": {"corpus": len(corpus), "queries": len(queries)},
                   "singles": table, "frozen_controls": FROZEN,
                   "control_lex_base_k10_w11": ctrl, "variants": variants,
                   "product_config": {"tag": "lex+small k0=10 w=1:1", **prod},
                   "note": "网格只登记过 lex+base; 本文件补 lex+small(产品真身)"},
                  f, ensure_ascii=False, indent=1)
    print(f"\nDONE -> {OUT}")


if __name__ == "__main__":
    main()
