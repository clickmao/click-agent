#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""融合检索实测 (R395, 用户令"走融合线")。

回答: 词法 (字符二元组 Jaccard) + 稠密 (bge) 的**真实可达**融合收益是多少?
`complementarity.py` 只给 union@k —— 那是"至少一路命中"的集合口径, **不是**任何融合算法的可达值。
本脚本算 RRF (Reciprocal Rank Fusion) 的真值: score(d) = Σ_r w_r / (k0 + rank_r(d) + 1)。

为何用秩而不用分数: Cos ∈ [-1,1] 与 Jaccard ∈ [0,1] 尺度不可比, 加权求和无法标定权重;
RRF 只用秩 ⇒ 跨检索器天然可比。**分数归一化不在本脚本口径内** (见判据②的饱和/重标定说明)。

判据 (全部可复算):
  ① **同口径对账**: 我用同一算法独立重建的排秩, 其"金标准秩向量"必须与仓库冻结实现
     `L.lexical_baseline` / `L.recall_metrics` **逐位一致** ⇒ 含 tie-break (索引倒序);
     再与跨运行冻结节账 (small r@10 0.6333 / base 0.7417) 交叉验证 ⇒ 数字不是本次才冒出来的。
  ② **秩级不变量**: RRF 只依赖秩 ⇒ 对分数做**严格单调且无浮点饱和**的变换 (x³, x+3, 5x)
     后融合结果必须逐位不变; **负控**: 非单调扰动 (随机改 5% 分数) 必须改变结果 ⇒ 判据有判别力。
  ③ **秩单调性** (fuzz): 把金标准在任一路里上移一名 (其余不变), 其融合秩不得变差。
     ※ 注意两条**伪不变量** (本脚本不采用, 因为数学上不成立): "融合 ≥ 单路最优" 与
       "融合 ≤ union@k" —— RRF 既可能低于单路最优, 也可能把两路 top-k 外的文档推进 k 内。
  ④ 负控: 与随机列表融合不得**显著**优于单路最优; 金标准标签洗牌后 r@10 必须塌到 ~10/1299。
"""
import argparse
import json
import math
import os
import random
import sys
import time
from operator import mul

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_MODEL = "/tmp/models/bge-base-zh-v1.5-q8.gguf"
PORT_BASE = 18100
NP = 1299


# ── 检索器: 排秩 ────────────────────────────────────────────────────────────
def order_key(scores):
    """仓库 tie-break: `sorted(((s, i) ...), reverse=True)` ⇒ 同分时**索引大者在前**。
    必须复刻, 否则边界名次会漂 (判据①逐位对账就是为此)。"""
    return sorted(range(len(scores)), key=lambda i: (-scores[i], -i))


def ranks_from_scores(scores):
    """返回秩数组: r[d] = 文档 d 的名次 (0 起)。"""
    order = order_key(scores)
    r = [0] * len(order)
    for rank, d in enumerate(order):
        r[d] = rank
    return r


def grams(s):
    s = "".join(ch for ch in s if not ch.isspace())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def lexical_scores(corpus, q):
    qg = grams(q["query"])
    return [len(qg & g) / (len(qg | g) or 1) for g in [grams(c["text"]) for c in corpus]]


def metrics_from_ranks(ranks):
    """ranks: **0 起**名次; 判 50 的口径按 1 起 (与仓库 recall_metrics 一致: >50 记 999)。"""
    r1 = [r + 1 if r + 1 <= 50 else 999 for r in ranks]
    n = len(r1)
    return {"r@1": round(sum(1 for r in r1 if r <= 1) / n, 4),
            "r@5": round(sum(1 for r in r1 if r <= 5) / n, 4),
            "r@10": round(sum(1 for r in r1 if r <= 10) / n, 4),
            "r@20": round(sum(1 for r in r1 if r <= 20) / n, 4),
            "mrr@10": round(sum(1.0 / r for r in r1 if r <= 10) / n, 4),
            "miss@50": round(sum(1 for r in r1 if r == 999) / n, 4)}


def rrf_rank_of_gold(rank_lists, weights, golds, cids, k0=60):
    """返回每条查询金标准的**融合名次** (0 起, 精确)。rank_lists: 每路的秩数组。"""
    cpos = {c: i for i, c in enumerate(cids)}
    n = len(cids)
    out = []
    for qi, g in enumerate(golds):
        sc = [0.0] * n
        for w, rl in zip(weights, rank_lists):
            for d, r in enumerate(rl):
                sc[d] += w / (k0 + r + 1)
        order = sorted(range(n), key=lambda i: (-sc[i], i))
        out.append(order.index(cpos[g]))
    return out


def union_at_k(rank_lists, golds, cids, k=10):
    """单查询: 至少一路把金标准排进前 k (集合口径, **非任何融合算法的可达值**)。"""
    cpos = {c: i for i, c in enumerate(cids)}
    hit = sum(1 for qi, g in enumerate(golds)
              if min(rl[cpos[g]] for rl in rank_lists) < k)
    return round(hit / len(golds), 4)


def rrf_all(P, weights, golds, cids, k0=60):
    """P[r][qi] = 第 r 路对第 qi 条查询的秩数组 ⇒ 返回每条查询金标准的融合名次 (0 起)。"""
    cpos = {c: i for i, c in enumerate(cids)}
    n = len(cids)
    out = []
    for qi, g in enumerate(golds):
        sc = [0.0] * n
        for w, pq in zip(weights, P):
            rl = pq[qi]
            for d in range(n):
                sc[d] += w / (k0 + rl[d] + 1)
        order = sorted(range(n), key=lambda i: (-sc[i], i))
        out.append(order.index(cpos[g]))
    return out


def union_all(P, golds, cids, k=10):
    cpos = {c: i for i, c in enumerate(cids)}
    hit = sum(1 for qi, g in enumerate(golds) if min(pq[qi][cpos[g]] for pq in P) < k)
    return round(hit / len(golds), 4)


# ── 向量 ────────────────────────────────────────────────────────────────────
def cached_vecs(prefix, texts, mt, model_path, port):
    t = L.tag(prefix, texts, model=mt)
    v = L.cache_load(t, len(texts))
    if v is not None:
        print(f"[cache] {prefix} n={len(texts)} -> hit", flush=True)
        return v
    print(f"[cache] {prefix} n={len(texts)} -> MISS, embedding", flush=True)
    proc = L.start_server(pooling="cls", port=port, model=model_path)
    try:
        v = [L.normalize(x) for x in L.embed(texts, port=port)]
    finally:
        proc.kill()
    L.cache_save(t, v)
    return v


def dense_scores(vecs_c, vecs_q):
    return [[sum(map(mul, cv, qv)) for cv in vecs_c] for qv in vecs_q]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=None)
    args = ap.parse_args()
    t0 = time.time()

    corpus, queries = L.load_fixtures()
    ctexts = [c["text"] for c in corpus]
    qtexts = [q["query"] for q in queries]
    cids = [c["id"] for c in corpus]
    golds = [q["gold_id"] for q in queries]
    print(f"[fixtures] corpus={len(corpus)} queries={len(queries)}", flush=True)

    # ── 判据①: 词法逐位对账 ──
    lex_rl = [ranks_from_scores(lexical_scores(corpus, q)) for q in queries]
    lex_g0 = [rl[[c["id"] for c in corpus].index(g)] for rl, g in zip(lex_rl, golds)]
    mine = [r + 1 if r + 1 <= 50 else 999 for r in lex_g0]
    ref_m, ref_r = L.lexical_baseline(corpus, queries)
    assert mine == ref_r, f"词法秩与冻结实现不一致: 首差 {next(i for i,(a,b) in enumerate(zip(mine,ref_r)) if a!=b)}"
    assert metrics_from_ranks(lex_g0)["r@10"] == ref_m["r@10"], (metrics_from_ranks(lex_g0), ref_m)
    print(f"[判据①] 词法逐位对账 OK  r@1={ref_m['r@1']} r@10={ref_m['r@10']} mrr@10={ref_m['mrr@10']}", flush=True)

    # ── 稠密两路 ──
    mt = L.model_tag()
    small_rl = [ranks_from_scores(s) for s in
                dense_scores(cached_vecs("fuse_corpus", ctexts, mt, L.MODEL, L.PORT),
                             cached_vecs("fuse_queries", qtexts, mt, L.MODEL, L.PORT))]
    base_mt = os.path.basename(BASE_MODEL).replace(".gguf", "")
    if not os.path.exists(BASE_MODEL):
        # 用户令 2026-09-14: 本机只保留链上真身(bge-small q8), 110MB base 已删除。
        # base 臂降级为**只读缓存复现**; 缓存缺失则明确失败 —— 绝不静默改用 small 顶替
        # (跨基座混算会把 0.8500 这种 base 口径读数冒充成产品读数 = 空心指标)。
        _cached = os.path.isdir(L.CACHE) and any(
            f.startswith(base_mt + "__fuse_") for f in os.listdir(L.CACHE))
        assert _cached, "base 模型已删且无向量缓存, base 臂不可复现: " + BASE_MODEL
    base_rl = [ranks_from_scores(s) for s in
               dense_scores(cached_vecs("fuse_corpus", ctexts, base_mt, BASE_MODEL, PORT_BASE),
                            cached_vecs("fuse_queries", qtexts, base_mt, BASE_MODEL, PORT_BASE))]
    cpos = {c: i for i, c in enumerate(cids)}
    singles = {"lexical": lex_rl, "dense-small": small_rl, "dense-base": base_rl}
    grank0 = {k: [singles[k][qi][cpos[golds[qi]]] for qi in range(len(golds))] for k in singles}
    tbl = {k: metrics_from_ranks(v) for k, v in grank0.items()}
    # 判据① (稠密): 与跨运行冻结节账交叉验证
    frozen = {"dense-small": 0.6333, "dense-base": 0.7417}
    for k, want in frozen.items():
        assert abs(tbl[k]["r@10"] - want) < 1e-9, f"{k} r@10={tbl[k]['r@10']} != 冻结节账 {want}"
    print(f"[判据①] 稠密与冻结节账一致: small r@10={tbl['dense-small']['r@10']} "
          f"base r@10={tbl['dense-base']['r@10']}", flush=True)

    # ── 判据②: 秩级不变量 + 负控 ──
    s0 = dense_scores(cached_vecs("fuse_corpus", ctexts, mt, L.MODEL, L.PORT),
                      cached_vecs("fuse_queries", qtexts, mt, L.MODEL, L.PORT))
    ref_fused = rrf_all([lex_rl, small_rl], [1.0, 1.0], golds, cids)
    # 严格单调且无浮点饱和的变换 (tanh(100x) 会把 |x|>0.2 压成 ±1.0 —— 真丢序, 不作样例)
    for nm, tf in (("cube", lambda x: x ** 3), ("plus3", lambda x: x + 3.0), ("times5", lambda x: 5.0 * x)):
        t_rl = [ranks_from_scores([tf(v) for v in row]) for row in s0]
        assert t_rl == small_rl, f"单调变换 {nm} 改变了排秩 (应只依赖序)"
        assert rrf_all([lex_rl, t_rl], [1.0, 1.0], golds, cids) == ref_fused, nm
    rng = random.Random(7)
    ph = [row[:] for row in s0]
    for _ in range(int(0.05 * len(ph) * len(ph[0]))):
        i, j = rng.randrange(len(ph)), rng.randrange(len(ph[0]))
        ph[i][j] = rng.uniform(-1, 1)
    n_changed = sum(1 for a, b in zip([ranks_from_scores(r) for r in ph], small_rl) if a != b)
    assert n_changed > 0, "负控失效: 随机扰动未改变任何排秩 ⇒ 判据②无判别力"
    print(f"[判据②] 秩级不变量 OK (3 变换逐位不变); 负控: 随机扰动改变 {n_changed}/{len(ph)} 条排秩", flush=True)

    # ── 判据③: 秩单调性 fuzz ──
    rng3 = random.Random(11)
    for _ in range(300):
        n = 60
        lists = []
        for _ in range(3):
            p = list(range(n)); rng3.shuffle(p); lists.append(p)
        gi = rng3.randrange(n)
        gid = "c%d" % gi
        base_rank = rrf_rank_of_gold(lists, [1.0] * 3, [gid], ["c%d" % i for i in range(n)])[0]
        k = rng3.randrange(3)
        if lists[k][gi] == 0:
            continue
        cur = lists[k][gi]
        other = lists[k].index(cur - 1)
        lists[k][gi], lists[k][other] = cur - 1, cur
        up_rank = rrf_rank_of_gold(lists, [1.0] * 3, [gid], ["c%d" % i for i in range(n)])[0]
        assert up_rank <= base_rank, (up_rank, base_rank)
    print("[判据③] 秩单调性 fuzz 300 例 OK (上移一名 ⇒ 融合秩不变差)", flush=True)

    # ── 融合主表 ──
    combos = [("lexical+dense-small", ["lexical", "dense-small"]),
              ("lexical+dense-base", ["lexical", "dense-base"]),
              ("dense-small+dense-base", ["dense-small", "dense-base"]),
              ("lexical+small+base", ["lexical", "dense-small", "dense-base"])]
    rows, best = [], None
    for nm, ks in combos:
        rls = [singles[k] for k in ks]
        for k0 in (10, 20, 60):
            wsets = [("1:1", [1.0] * len(ks)), ("lex-heavy", [2.0] + [1.0] * (len(ks) - 1))]
            if len(ks) == 2:
                wsets.append(("dense-heavy", [1.0, 2.0]))
            for wname, w in wsets:
                gr = rrf_all(rls, w, golds, cids, k0=k0)
                m = metrics_from_ranks(gr)
                u = union_all(rls, golds, cids, 10)
                row = {"combo": nm, "k0": k0, "w": wname, "r@1": m["r@1"], "r@10": m["r@10"],
                       "r@20": m["r@20"], "mrr@10": m["mrr@10"], "miss@50": m["miss@50"], "union@10": u}
                rows.append(row)
                if best is None or (row["r@10"], row["mrr@10"]) > (best["r@10"], best["mrr@10"]):
                    best = row
    for k in singles:
        print(f"[single] {k:12s} r@1={tbl[k]['r@1']:.4f} r@10={tbl[k]['r@10']:.4f} "
              f"r@20={tbl[k]['r@20']:.4f} mrr@10={tbl[k]['mrr@10']:.4f}", flush=True)
    print(f"[best-fusion] {best}", flush=True)

    # ── 判据④: 负控 ──
    rng4 = random.Random(3)
    rand_rl = [list(range(len(cids))) for _ in golds]
    for rl in rand_rl:
        rng4.shuffle(rl)
    nr = metrics_from_ranks(rrf_all([lex_rl, rand_rl], [1.0, 1.0], golds, cids))
    assert nr["r@10"] <= tbl["lexical"]["r@10"] + 0.05, (nr, tbl["lexical"])
    shuf = golds[:]
    rng4.shuffle(shuf)
    sm = metrics_from_ranks(rrf_all([lex_rl, small_rl], [1.0, 1.0], shuf, cids))
    assert sm["r@10"] <= 0.12, sm
    print(f"[判据④] 随机路负控 r@10={nr['r@10']} (≤词法+0.05); 洗牌负控 r@10={sm['r@10']} (~{10/1299:.4f} 随机水平)", flush=True)

    out = {"singles": tbl, "rows": rows, "best": best,
           "controls": {"random_r10": nr["r@10"], "shuffle_r10": sm["r@10"],
                        "changed_ranks_on_perturb": n_changed},
           "elapsed_s": round(time.time() - t0, 1)}
    print(json.dumps(out, ensure_ascii=False), flush=True)
    if args.md:
        L_doc = os.path.join(REPO, args.md) if not os.path.isabs(args.md) else args.md
        os.makedirs(os.path.dirname(L_doc), exist_ok=True)
        with open(L_doc, "w", encoding="utf-8") as f:
            f.write(render_md(tbl, rows, best, nr, sm, n_changed, time.time() - t0))
        print(f"[md] {L_doc}", flush=True)
    return 0


def render_md(tbl, rows, best, nr, sm, n_changed, secs):
    Ln = []
    A = Ln.append
    A("# 融合检索实测 (RRF) — 2026-09-13\n")
    A("> 脚本 `eval/bge/fusion.py` 自动生成 (禁手抄)。口径冻结: 1299 块语料 + 120 查询 (1 条 = 0.83pt)。\n")
    A("## 1. 单路基线 (与冻结节账逐位对账)\n")
    A("| 检索器 | r@1 | r@5 | r@10 | r@20 | mrr@10 | miss@50 |")
    A("|---|---|---|---|---|---|---|")
    for k, m in tbl.items():
        A(f"| {k} | {m['r@1']} | {m['r@5']} | {m['r@10']} | {m['r@20']} | {m['mrr@10']} | {m['miss@50']} |")
    A("\n## 2. RRF 融合 (k0 × 权重)\n")
    A("| 组合 | k0 | 权重 | r@1 | r@10 | r@20 | mrr@10 | miss@50 | union@10 (参考,非上界) |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        A(f"| {r['combo']} | {r['k0']} | {r['w']} | {r['r@1']} | {r['r@10']} | {r['r@20']} | {r['mrr@10']} | {r['miss@50']} | {r['union@10']} |")
    A(f"\n**最优**: `{best['combo']}` k0={best['k0']} w={best['w']} ⇒ **r@1 {best['r@1']} / r@10 {best['r@10']} / mrr@10 {best['mrr@10']}**")
    A(f"\n对比: 词法单路 r@10 {tbl['lexical']['r@10']} / dense-base {tbl['dense-base']['r@10']} / dense-small {tbl['dense-small']['r@10']}")
    A("\n## 3. 判据与负控 (都可复算)\n")
    A("- ① 同口径对账: 自建排秩的金标准秩向量与 `L.lexical_baseline` **逐位一致**; dense 与冻结节账 (small 0.6333 / base 0.7417) 一致 ⇒ 融合数字起点可信。")
    A("- ② 秩级不变量: 严格单调无饱和变换 (x³, x+3, 5x) 后融合逐位不变; 负控 (随机改 5% 分数) 改变了排秩 ⇒ 判据有判别力。")
    A("- ③ 秩单调性 fuzz 300 例: 金标准在某一路名义上移一名 ⇒ 融合秩不变差。")
    A(f"- ④ 负控: 随机路融合 r@10={nr['r@10']} (不得显著优于词法单路); 标签洗牌后 r@10={sm['r@10']} (随机水平 ≈ {10/1299:.4f})。")
    A("\n### 两条**伪不变量** (明确不采用)\n")
    A("- 「融合 ≥ 单路最优」: RRF 可能把金标准排到比最优单路更差 (两路互不背书时)。")
    A("- 「融合 ≤ union@k」: RRF 可能把两路 top-k 之外的文档推进 k 内 (两路名次都中等但一致)。")
    A(f"\n耗时 {secs:.1f}s; 扰动判据实测改变排秩 {n_changed} 条。\n")
    return "\n".join(Ln)


if __name__ == "__main__":
    sys.exit(main())
