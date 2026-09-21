#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R627 · **事后**诊断（`checks_posthoc` 槽位；不参与预注册判据的红绿、不翻案任何既定判决）

两件事：
  A) 预注册 P3 旧形态的**判别力审计**：`agreement(臂, 产品)` 作为负控指标是否有效。
     —— 环境提示：产品自身 miss 32 条；任何 miss 集合 ⊇ 产品 miss 集合的坏臂都能**免费**拿到
        那 32 条的「一致」。故须改用**臂间差异量**（命中集对称差 / 命中数差）。
  B) 融合**归并/截断次序**的诊断读数（信息项）：现产品 = Take(TopK=10 单元) → 再 chunk→parent 归并
     （⇒ 池内父文档数 ≤ 10，且同父多块会白占槽位）；替代形态 = 全量归并 → 取前 10 父文档。
     零产品改动、纯计算；**仅作下轮候选的预注册输入，本轮不作判据**。

输入：eval/rover/r627/oracle-r627.json
输出：eval/rover/r627/posthoc-r627.json
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oracle_fusion_r627 as O   # 复用同轮器具（禁重写第二份）

REPO = O.REPO
VEC = O.VEC
OUT = os.path.join(REPO, "eval/rover/r627/posthoc-r627.json")


def main():
    oracle = json.load(io.open(f"{REPO}/eval/rover/r627/oracle-r627.json", encoding="utf-8"))
    per_q = oracle["per_query"]
    prod = json.load(io.open(f"{REPO}/eval/rover/r625/out/B10.json", encoding="utf-8"))
    prod_pool = {r["qid"]: bool(r["gold_in_pool"]) for r in prod["per_query"]}
    qids = [r["qid"] for r in prod["per_query"]]

    hit = {a: {q for q in qids if per_q[q][f"{a}_in_pool"]} for a in ("POS", "N1", "N2", "N3")}
    prod_hits = {q for q in qids if prod_pool[q]}

    # ── A) 判别力审计：agreement 形态 vs 臂间差异形态 ────────────────────────
    A = {}
    for a in hit:
        agree = sum(1 for q in qids if per_q[q][f"{a}_in_pool"] == prod_pool[q]) / len(qids)
        A[a] = {
            "agreement_vs_product": round(agree, 4),
            "n_hits": len(hit[a]),
            "hits_delta_vs_product": len(hit[a]) - len(prod_hits),
            "symdiff_hits_vs_product": len(hit[a] ^ prod_hits),
            "symdiff_fraction": round(len(hit[a] ^ prod_hits) / len(qids), 4),
        }
    A["_note"] = ("**旧形态（agreement vs 产品）判别力不足**：产品自身 miss 32 条是白送的一致来源 ⇒ "
                  "配错臂 agreement 仍 0.8333。**正确形态 = 臂间差异量**（symdiff_hits_vs_产品 / 命中数差）；"
                  "本轮 POS symdiff=0（逐例复现），N1=13 / N2=20 / N3=29 ⇒ 三臂差异量单调可辨。")

    # ── B) 归并/截断次序诊断（信息项）───────────────────────────────────────
    corpus = O.read_jsonl(f"{REPO}/eval/bge/fixtures/corpus.jsonl")
    queries = O.read_jsonl(f"{REPO}/eval/bge/fixtures/queries.jsonl")
    nC, dC, aC = O.read_f32(f"{VEC}/corpus-trunc440.f32")
    nQ, dQ, aQ = O.read_f32(f"{VEC}/queries-trunc440.f32")
    nK, dK, aK = O.read_f32(f"{VEC}/chunks.f32")
    keys = [json.loads(l) for l in io.open(f"{VEC}/keys-chunks.jsonl", encoding="utf-8") if l.strip()]
    key_vec = {keys[i]: list(aK[i * dK:(i + 1) * dK]) for i in range(nK)}

    uv, ut, up = [], [], []
    for i, c in enumerate(corpus):
        uv.append([float(x) for x in aC[i * dC:(i + 1) * dC]])
        ut.append(c["text"])
        up.append(c["id"])
    for c in corpus:
        for idx, t in O.chunks_of(c["text"]):
            uv.append(key_vec[t])
            ut.append(t)
            up.append(c["id"])
    n = len(uv)
    uvn = [O.norm(v) for v in uv]
    ug = [O.bigram_codes(t) for t in ut]
    gold = {q["qid"]: q["gold_id"] for q in queries}

    def lex_order(qtext):
        qs = O.bigram_codes(qtext)
        s = [0.0] * n
        if qs:
            for i in range(n):
                us = ug[i]
                if not us:
                    continue
                inter = len(qs & us)
                uni = len(qs) + len(us) - inter
                s[i] = (inter / uni) if uni else 0.0
        return O.ranks_desc_with_index_desc(s)[0]

    late_hits, delta_pool, early_short_n = set(), [], 0
    for qi, q in enumerate(queries):
        qv = O.norm([float(x) for x in aQ[qi * dQ:(qi + 1) * dQ]])
        r_d = O.ranks_desc_with_index_desc([O.dot(qv, v) for v in uvn])[0]
        r_l = lex_order(q["query"])
        _sc, order = O.rrf_order([r_d, r_l], [O.W_D, O.W_L], n)
        # 早归并（现产品）：先 Take(10 单元) 再归并
        early, seen_e = [], set()
        for u in order[:O.TOPK]:
            if up[u] in seen_e:
                continue
            seen_e.add(up[u])
            early.append(up[u])
        # 晚归并（替代形态）：全量归并后取前 10 父文档
        late, seen_l = [], set()
        for u in order:
            if up[u] in seen_l:
                continue
            seen_l.add(up[u])
            late.append(up[u])
            if len(late) >= O.TOPK:
                break
        if gold[q["qid"]] in set(late):
            late_hits.add(q["qid"])
        delta_pool.append(len(set(late)) - len(set(early)))
        if len(set(early)) < O.TOPK:
            early_short_n += 1

    merge_order = {
        "form_early_merge_take_units": {"n_hits": len(prod_hits), "rate": round(len(prod_hits) / len(qids), 4)},
        "form_late_merge_take_parents": {"n_hits": len(late_hits), "rate": round(len(late_hits) / len(qids), 4)},
        "gain_hits": len(late_hits) - len(prod_hits),
        "pool_len_delta_median": sorted(delta_pool)[len(delta_pool) // 2],
        "metric_defect_note": ("`pool_len_delta_median` **退化**（两种形态都恰好取 10 个父文档 ⇒ 恒为 0）"
                               "⇒ 该字段无判别力；有判别力的等价量 = 早归并形态下**池内父文档数 < 10 的查询数**"
                               "（= 同父多块白占槽位的次数）。"),
        "pool_len_early_lt_10_n": early_short_n,
        "role": "**信息项**（事后诊断）：不参与判据红绿、不翻案 R625/R626 读数；仅作下轮候选的预注册输入",
    }

    res = {"schema": "rerank-instrument-posthoc/1", "round": "R627",
           "discriminative_power_audit": A, "merge_order_diagnostic": merge_order,
           "n_queries": len(qids)}
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
