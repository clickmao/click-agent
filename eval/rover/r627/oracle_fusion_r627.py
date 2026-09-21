#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R627 · 面 4 召回面 **器具面判据形态修法** —— 同形口径独立 oracle（零产品改动）

承 R626 单列器具缺陷 `P4-pos-prereg-form`：R626 的正控用**单路（dense-only）**口径去对
**融合池**读数，阈值 0.90 实测 0.8409 ⇒ 该阈值隐含「产品池 ≈ 独立 dense top-10」，而产品池是
dense 与 lexical 的 RRF 融合 top-10 ⇒ 单路与融合池本不必一致（R626 照原样 FAIL、不下调）。
本轮按 R626 下轮候选②：把正控改成**与产品同形口径**，并配两侧样例（单路形态必报 / 配错必报）。

输入（**全部冻结在盘**，本轮只读）：
  eval/bge/fixtures/{corpus,queries}.jsonl
  eval/rover/r624/vec/{corpus-trunc440,queries-trunc440,chunks}.f32 + keys-chunks.jsonl
  eval/rover/r625/out/B10.json（产品生产口径读数 gold_in_pool，只读派生）

独立 oracle（与本仓被测 C# **零共享代码**，stdlib only）：
  dense 路  : cos 全序（同分按索引降序 —— 复刻 FusionMath.AssignRanks 的 tie-break）
  lexical 路: 去空白字符二元组 Jaccard（同分按索引降序）
  RRF       : score = Σ w/(k0 + rank + 1)，k0=10，w_d=w_l=1.0（FusionOptions 源码右值）
  排序      : (分降, 索引升) —— 复刻 FusionRecall.Rank 的 tie-break（与 AssignRanks **故意不同**）
  池        : 前 10 单元 → 父 Id 集合（'#c' 归并，复刻 RAGRecall.cs:459-490）

单位纪律（承 R624）：.NET String.Length / Substring = **UTF-16 code unit** ⇒ 切块在 UTF-16 上做。

输出：eval/rover/r627/oracle-r627.json
"""
import array
import io
import json
import os
import time
from operator import mul

REPO = "/home/agentuser/AgentFramework"
VEC = os.path.join(REPO, "eval/rover/r624/vec")
OUT = os.path.join(REPO, "eval/rover/r627/oracle-r627.json")
PROD = os.path.join(REPO, "eval/rover/r625/out/B10.json")
MAXCH = 440          # src/agent.rag/RAGRecall.cs:604 maxEmbedChars = 440
K0 = 10              # FusionOptions.K0
W_D = 1.0            # FusionOptions.DenseWeight
W_L = 1.0            # FusionOptions.LexicalWeight
TOPK = 10            # 生产 MaxRecallResults = 10


def log(*a):
    print(*a, flush=True)


def read_jsonl(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]


def read_f32(p):
    with open(p, "rb") as f:
        n = int.from_bytes(f.read(8), "little")
        d = int.from_bytes(f.read(8), "little")
        a = array.array("f")
        a.fromfile(f, n * d)
    return n, d, a


def u16_units(s):
    return s.encode("utf-16-le", "surrogatepass")


def chunks_of(text):
    """逐字复刻 RAGRecall.cs:203-219 的切块（只取 chunkIdx >= 1），单位 = UTF-16 code unit。"""
    u = u16_units(text)
    n = len(u) // 2
    if n <= MAXCH:
        return []
    out = []
    idx = 0
    pos = 0
    while pos < n:
        cnt = min(MAXCH, n - pos)
        seg = u[pos * 2:(pos + cnt) * 2]
        if idx >= 1:
            out.append((idx, seg.decode("utf-16-le", "surrogatepass")))
        idx += 1
        pos += cnt
    return out


def bigram_codes(text):
    """去空白字符二元组集合；每个 gram 编成 c1*65536+c2（无碰撞）；与 FusionMath.CharacterBigrams 同口径。"""
    u = u16_units(text)
    out = set()
    prev = -1
    for i in range(0, len(u), 2):
        c = u[i] | (u[i + 1] << 8)
        if chr(c).isspace():
            continue
        if prev >= 0:
            out.add(prev * 65536 + c)
        prev = c
    return out


def norm(v):
    s = 0.0
    for x in v:
        s += x * x
    s = s ** 0.5
    return [x / s for x in v] if s > 0 else list(v)


def cos(a, b):
    d = 0.0
    na = 0.0
    nb = 0.0
    for i in range(len(a)):
        d += a[i] * b[i]
        na += a[i] * a[i]
        nb += b[i] * b[i]
    den = (na ** 0.5) * (nb ** 0.5)
    return 0.0 if den <= 0 else d / den


def dot(a, b):
    return sum(map(mul, a, b))


def ranks_desc_with_index_desc(scores):
    """复刻 FusionMath.AssignRanks：分降序、同分按**索引降序**。返回 rank[i]。"""
    n = len(scores)
    idx = sorted(range(n), key=lambda i: (-scores[i], -i))
    r = [0] * n
    for pos, i in enumerate(idx):
        r[i] = pos
    return r, idx


def rrf_order(rank_lists, weights, n):
    """复刻 FusionRecall.Rank：score = Σ w/(k0+rank+1)；排序 (分降, 索引升)。"""
    sc = [0.0] * n
    for rl, w in zip(rank_lists, weights):
        for d in range(n):
            sc[d] += w / (K0 + rl[d] + 1)
    order = sorted(range(n), key=lambda i: (-sc[i], i))
    return sc, order


def main():
    t0 = time.time()
    corpus = read_jsonl(f"{REPO}/eval/bge/fixtures/corpus.jsonl")
    queries = read_jsonl(f"{REPO}/eval/bge/fixtures/queries.jsonl")
    nC, dC, aC = read_f32(f"{VEC}/corpus-trunc440.f32")
    nQ, dQ, aQ = read_f32(f"{VEC}/queries-trunc440.f32")
    nK, dK, aK = read_f32(f"{VEC}/chunks.f32")
    keys = [json.loads(l) for l in io.open(f"{VEC}/keys-chunks.jsonl", encoding="utf-8") if l.strip()]

    doc_ids = [c["id"] for c in corpus]
    qids = [q["qid"] for q in queries]
    gold = {q["qid"]: q["gold_id"] for q in queries}

    # ── P0 锚定：块重放（首次出现保留去重）vs keys-chunks 逐位 ────────────────
    replay, seen, n_total = [], set(), 0
    for c in corpus:
        for _idx, t in chunks_of(c["text"]):
            n_total += 1
            if t in seen:
                continue
            seen.add(t)
            replay.append(t)
    anchor = {
        "n_total_chunks": n_total,
        "n_unique_replay": len(replay),
        "n_keys": len(keys),
        "n_deduped": n_total - len(replay),
        "n_bitexact": sum(1 for x, y in zip(replay, keys) if x == y),
    }
    anchor["pass"] = (len(replay) == len(keys) and anchor["n_bitexact"] == len(keys))
    log("ANCHOR", json.dumps(anchor))

    # ── 语料自证：内容去重会不会改变单元数（RAGRecall._contentDedup）──────────
    corp_seen, n_dup_doc = set(), 0
    for c in corpus:
        if c["text"] in corp_seen:
            n_dup_doc += 1
        corp_seen.add(c["text"])
    log("CORPUS_DUP_TEXT", n_dup_doc)

    # ── 单元域（产品同形口径：1299 head ∪ 643 chunk 文档）────────────────────
    key_vec = {}
    for i in range(nK):
        key_vec[keys[i]] = list(aK[i * dK:(i + 1) * dK])
    unit_vec, unit_text, unit_id, unit_parent = [], [], [], []
    head_pos = {d: i for i, d in enumerate(doc_ids)}
    for i, c in enumerate(corpus):
        unit_vec.append([float(x) for x in aC[i * dC:(i + 1) * dC]])
        unit_text.append(c["text"])
        unit_id.append(c["id"])
        unit_parent.append(c["id"])
    n_head = len(unit_vec)
    for c in corpus:
        for idx, t in chunks_of(c["text"]):
            unit_vec.append(key_vec[t])
            unit_text.append(t)
            unit_id.append(f'{c["id"]}#c{idx}')
            unit_parent.append(c["id"])
    n_unit = len(unit_vec)
    log("UNITS", n_head, n_unit - n_head, n_unit)
    if not anchor["pass"] or n_unit - n_head != n_total:
        return {"rc": 2, "reason": "P0 anchoring/universe failed", "anchor": anchor,
                "n_unit": n_unit, "n_head": n_head, "n_total_chunks": n_total}

    unit_vec_n = [norm(v) for v in unit_vec]
    qvec_raw = {}
    for i, q in enumerate(queries):
        qvec_raw[q["qid"]] = [float(x) for x in aQ[i * dQ:(i + 1) * dQ]]
    unit_grams = [bigram_codes(t) for t in unit_text]

    # ── 产品读数（只读派生）────────────────────────────────────────────────
    prod = json.load(io.open(PROD, encoding="utf-8"))
    prod_pool = {r["qid"]: bool(r["gold_in_pool"]) for r in prod["per_query"]}

    def dense_ranks(qv):
        s = [dot(qv, v) for v in unit_vec_n]
        r, _ = ranks_desc_with_index_desc(s)
        return r

    def lexical_ranks(qtext):
        qs = bigram_codes(qtext)
        n = len(unit_grams)
        s = [0.0] * n
        if qs:
            for i in range(n):
                us = unit_grams[i]
                if not us:
                    continue
                inter = len(qs & us)
                uni = len(qs) + len(us) - inter
                s[i] = (inter / uni) if uni else 0.0
        r, _ = ranks_desc_with_index_desc(s)
        return r

    def pool_parents(order):
        parents, seen_p = [], set()
        for u in order[:TOPK]:
            p = unit_parent[u]
            if p in seen_p:
                continue
            seen_p.add(p)
            parents.append(p)
        return parents

    arms = {}
    per_q = {}
    for qi, q in enumerate(queries):
        qid = q["qid"]
        qtext = q["query"]
        g = gold[qid]
        qv = norm(qvec_raw[qid])
        r_d = dense_ranks(qv)
        r_l = lexical_ranks(qtext)

        # POS：同形（融合）
        _sc, order_pos = rrf_order([r_d, r_l], [W_D, W_L], n_unit)
        # N1：单路（dense-only，= R626 旧判据形态）
        _sd, order_n1 = rrf_order([r_d], [W_D], n_unit)
        # N2：配错（查询向量移位一格，文本不变）
        qv2 = norm(qvec_raw[queries[(qi + 1) % len(queries)]["qid"]])
        r_d2 = dense_ranks(qv2)
        r_l2 = lexical_ranks(qtext)
        _s2, order_n2 = rrf_order([r_d2, r_l2], [W_D, W_L], n_unit)
        # N3：零向量（dense 路退化）
        r_d3 = dense_ranks([0.0] * len(qv))
        _s3, order_n3 = rrf_order([r_d3, r_l], [W_D, W_L], n_unit)

        per_q[qid] = {
            "gold": g,
            "product_in_pool": prod_pool[qid],
            "POS_in_pool": g in set(pool_parents(order_pos)),
            "N1_in_pool": g in set(pool_parents(order_n1)),
            "N2_in_pool": g in set(pool_parents(order_n2)),
            "N3_in_pool": g in set(pool_parents(order_n3)),
            "pool_len_POS": len(pool_parents(order_pos)),
        }
        for a, k in (("POS", "POS_in_pool"), ("N1", "N1_in_pool"), ("N2", "N2_in_pool"), ("N3", "N3_in_pool")):
            arms.setdefault(a, []).append(per_q[qid][k])
        if qi % 20 == 0:
            log("q", qi, qid, "prod", prod_pool[qid], "POS", per_q[qid]["POS_in_pool"])

    def agree(a):
        return sum(1 for qid in qids if arms[a][qids.index(qid)] == prod_pool[qid]) / len(qids)

    ag = {a: agree(a) for a in ("POS", "N1", "N2", "N3")}
    hit = {a: sum(1 for x in arms[a] if x) for a in arms}
    prod_hit = sum(1 for x in prod_pool.values() if x)
    # 非平凡：三形态归属向量互异
    vecs = {a: tuple(arms[a]) for a in ("POS", "N1", "N2", "N3")}
    nontrivial = len(set(vecs.values())) == 4
    # POS 与产品不一致的逐例
    disagree = [q for q in qids if per_q[q]["POS_in_pool"] != prod_pool[q]]

    res = {
        "schema": "rerank-recall-instrument-form/1",
        "round": "R627",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "axis": "无（器具轮）· 唯一自由度 = 判据比较形态（单路 → 同形融合）",
        "oracle": {
            "independence": "排序实现 / 单元映射 / 比较形态独立（stdlib 纯 Python，零 import 本仓）；**向量源不独立**（冻结件，同源性由 R624 G0 覆盖）",
            "unit_universe": {"n_units": n_unit, "n_head": n_head, "n_chunk": n_unit - n_head},
            "anchor_chunk_mapping_bitexact": anchor,
            "corpus_dup_text_docs": n_dup_doc,
            "params_from_source": {"k0": K0, "w_dense": W_D, "w_lexical": W_L, "topk": TOPK, "max_embed_chars": MAXCH},
        },
        "readings": {
            "agreement_vs_product_B10": ag,
            "oracle_hits": hit,
            "product_hits": prod_hit,
            "product_hits_gated": prod_hit,
            "n_queries": len(qids),
            "pool_len_POS_median": sorted(r["pool_len_POS"] for r in per_q.values())[len(per_q) // 2],
        },
        "per_query": per_q,
        "disagree_POS_vs_product": disagree,
        "non_trivial_four_arms_distinct": nontrivial,
        "elapsed_s": time.time() - t0,
    }
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(res, ensure_ascii=False, indent=1))
    log("AGREE", json.dumps(ag))
    log("HITS", json.dumps(hit), "prod", prod_hit)
    log("DISAGREE_N", len(disagree), disagree[:12])
    log("NONTRIVIAL", nontrivial, "elapsed", round(res["elapsed_s"], 1))
    return res


if __name__ == "__main__":
    r = main()
    if isinstance(r, dict) and r.get("rc") == 2:
        raise SystemExit(2)
