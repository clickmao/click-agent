#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R626 · 面 4 召回面**逐例归因**（只读 · 独立 oracle · 零产品改动）

输入（**全部冻结在盘**）：
  eval/bge/fixtures/{corpus,queries}.jsonl          冻结题集（1299 文档 / 120 查询，单 gold）
  eval/rover/r624/vec/{corpus-trunc440,queries-trunc440,chunks}.f32   生产形态向量件（R624 产出）
  eval/rover/r624/vec/keys-chunks.jsonl             块文本查找键（顺序与 chunks.f32 行一致）
  eval/rover/r625/out/{B10,B50}.json + eval/rover/r624/out/{B2,B3}.json   已在盘的臂读数（只读派生）
输出：
  eval/rover/r626/attrib-r626.json

独立 oracle（与本仓被测 C# **零共享代码**，stdlib only）：
  D1 dense 面：cos 全序（unit = head 首块 ∪ chunk 块）
  D2 lexical 面：BM25(k1=1.2,b=0.75) 全文**不截断**
独立性边界：向量源**不独立**（被测侧产出，同源性由 R624 G0 覆盖）⇒ 只主张排序实现与单元映射独立。
单位纪律（承 R624）：C# String.Length/Substring = UTF-16 code unit ⇒ 切块重放必须在 UTF-16 上切片。
"""
import array
import io
import json
import math
import os
import re
import sys
import time
from operator import mul

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r626/attrib-r626.json")
VEC = os.path.join(REPO, "eval/rover/r624/vec")
MAXCH = 440


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


def u16_len(s):
    return len(s.encode("utf-16-le", "surrogatepass")) // 2


def chunks_of(text):
    """逐字复刻 RAGRecall 的切块（只取 chunkIdx >= 1），单位 = UTF-16 code unit。"""
    u = text.encode("utf-16-le", "surrogatepass")
    n_units = len(u) // 2
    if n_units <= MAXCH:
        return []
    out = []
    for pos in range(MAXCH, n_units, MAXCH):
        piece = u[pos * 2: min(pos + MAXCH, n_units) * 2]
        out.append(piece.decode("utf-16-le", "surrogatepass"))
    return out


def norm(v):
    s = math.sqrt(sum(x * x for x in v))
    return [x / s for x in v] if s > 0 else list(v)


TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[\u4e00-\u9fff]")


def tokens(text):
    raw = TOK.findall(text.lower())
    words, cjk = [], []
    for t in raw:
        (cjk if (len(t) == 1 and "\u4e00" <= t <= "\u9fff") else words).append(t)
    for i in range(len(cjk) - 1):
        words.append(cjk[i] + cjk[i + 1])
    words.extend(cjk)
    return words


def fisher_two_sided(a, b, c, d):
    n = a + b + c + d
    r1, r2, c1 = a + b, c + d, a + c

    def p(x):
        return (math.comb(r1, x) * math.comb(r2, c1 - x)) / math.comb(n, c1)

    obs = p(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs + 1e-12)


def main():
    t0 = time.time()
    corpus = read_jsonl(f"{REPO}/eval/bge/fixtures/corpus.jsonl")
    queries = read_jsonl(f"{REPO}/eval/bge/fixtures/queries.jsonl")
    nC, dC, aC = read_f32(f"{VEC}/corpus-trunc440.f32")
    nQ, dQ, aQ = read_f32(f"{VEC}/queries-trunc440.f32")
    nK, dK, aK = read_f32(f"{VEC}/chunks.f32")
    keys = [json.loads(l) for l in io.open(f"{VEC}/keys-chunks.jsonl", encoding="utf-8") if l.strip()]

    doc_ids = [c["id"] for c in corpus]
    idx_of = {d: i for i, d in enumerate(doc_ids)}
    u16 = [u16_len(c["text"]) for c in corpus]
    qids = [q["qid"] for q in queries]
    gold = {q["qid"]: q["gold_id"] for q in queries}

    # ── 锚定：切块重放 vs keys-chunks.jsonl 逐位 ────────────────────────────
    # 生产侧 gen_chunks_r624.py 对块文本**去重**（首次出现保留）⇒ 重放必须同规则，
    # 否则索引一旦错位，其后全部逐位比对失配（本轮实测：不去重 ⇒ bitexact 88/643）。
    replay, replay_parent, seen = [], [], set()
    n_total = 0
    for c in corpus:
        for t in chunks_of(c["text"]):
            n_total += 1
            if t in seen:
                continue
            seen.add(t)
            replay.append(t)
            replay_parent.append(c["id"])
    anchor = {"n_total_chunks": n_total, "n_unique_replay": len(replay), "n_keys": len(keys),
              "n_deduped": n_total - len(replay),
              "n_bitexact": sum(1 for x, y in zip(replay, keys) if x == y)}
    anchor["pass"] = len(replay) == len(keys) and anchor["n_bitexact"] == len(keys)
    log("ANCHOR", json.dumps(anchor))
    if not anchor["pass"]:
        return 3

    heads = [norm(list(aC[i * dC:(i + 1) * dC])) for i in range(nC)]
    chunks = [norm(list(aK[i * dK:(i + 1) * dK])) for i in range(nK)]
    qvecs = [norm(list(aQ[i * dQ:(i + 1) * dQ])) for i in range(nQ)]
    unit_vecs = heads + chunks
    unit_parent = doc_ids + replay_parent
    gold_units_of = {}
    for u_i, p in enumerate(unit_parent):
        gold_units_of.setdefault(p, []).append(u_i)

    def first_pos(order, wanted_set):
        for pos, i in enumerate(order):
            if i in wanted_set:
                return pos + 1
        return None

    def dense_q(qv):
        sims = [sum(map(mul, qv, v)) for v in unit_vecs]
        order = sorted(range(len(sims)), key=lambda i: (-sims[i], i))
        hsims = [sum(map(mul, qv, v)) for v in heads]
        horder = sorted(range(len(hsims)), key=lambda i: (-hsims[i], i))
        return order, horder

    # ── 冻结臂（只读派生）───────────────────────────────────────────────────
    def miss_set(p):
        d = json.load(io.open(p, encoding="utf-8"))
        return {r["qid"] for r in d["per_query"] if not r.get("gold_in_pool")}

    M10 = miss_set(f"{REPO}/eval/rover/r625/out/B10.json")
    M50 = miss_set(f"{REPO}/eval/rover/r625/out/B50.json")
    M200 = miss_set(f"{REPO}/eval/rover/r624/out/B2.json")
    M1299 = miss_set(f"{REPO}/eval/rover/r624/out/B3.json")
    band1, band2, band3 = sorted(M10 - M50), sorted(M50 - M200), sorted(M200 - M1299)
    hits10 = set(qids) - M10
    log("M10", len(M10), "bands", len(band1), len(band2), len(band3))

    # ── 词法面（独立实现；预建 doc tf）─────────────────────────────────────
    dtoks = [tokens(c["text"]) for c in corpus]
    dl = [len(t) for t in dtoks]
    avgdl = sum(dl) / len(dl)
    tf_list = []
    df = {}
    for t in dtoks:
        tf = {}
        for w in t:
            tf[w] = tf.get(w, 0) + 1
        tf_list.append(tf)
        for w in tf:
            df[w] = df.get(w, 0) + 1
    n = len(dtoks)
    idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
    lex_rank = {}
    for qi, q in enumerate(queries):
        qt = tokens(q["query"])
        sc = [0.0] * n
        for i in range(n):
            tf, L = tf_list[i], dl[i]
            s = 0.0
            for w in qt:
                f = tf.get(w)
                if f:
                    s += idf.get(w, 0.0) * (f * 2.2) / (f + 1.2 * (0.25 + 0.75 * L / avgdl))
            sc[i] = s
        order = sorted(range(n), key=lambda i: (-sc[i], i))
        lex_rank[q["qid"]] = {doc_ids[p]: k + 1 for k, p in enumerate(order)}
        if qi % 40 == 0:
            log("lex", qi)
    log("lex done", round(time.time() - t0, 1))

    # ── 逐例（miss + hit 一次过）───────────────────────────────────────────
    rows, hit_rows, all_rows, shift_hit = [], [], [], 0
    neg_hits = 0
    for qi, qid in enumerate(qids):
        qv = qvecs[qi]
        order, horder = dense_q(qv)
        g = gold[qid]
        gi = idx_of[g]
        gu = gold_units_of.get(g, [])
        rank_any = first_pos(order, set(gu)) if gu else None
        rank_doc = first_pos(horder, {gi}) or 99999
        rec = {"qid": qid, "gold": g, "gold_u16_len": u16[gi], "gold_gt_440": u16[gi] > MAXCH,
               "rank_doc_head_only": rank_doc, "rank_any_unit": rank_any,
               "n_gold_units": len(gu), "rank_lex_fulltext": lex_rank[qid][g]}
        if qid in M10:
            rec["band"] = ("(10,50]" if qid in set(band1) else
                           "(50,200]" if qid in set(band2) else "(200,1299]")
            rec["layer"] = ("L-C_index_missing" if not gu else
                            "L-A_unit_granularity" if (rank_any is not None and rank_any <= 10 and rank_doc > 10) else
                            "L-B_ranking_signal")
            rec["product_pool_has_gold"] = False
            rows.append(rec)
        else:
            rec["product_pool_has_gold"] = True
            hit_rows.append(rec)
        all_rows.append(rec)
        # 负控（同一循环内，配错 query 向量）：
        qv2 = qvecs[(qi + 1) % nQ]
        _o, h2 = dense_q(qv2)
        p2 = first_pos(h2, {gi})
        if p2 is not None and p2 <= 10:
            shift_hit += 1
        if qi % 20 == 0:
            log("perq", qi, round(time.time() - t0, 1))

    layers = {}
    for r in rows:
        layers[r["layer"]] = layers.get(r["layer"], 0) + 1
    n_miss = len(rows)
    n_la = layers.get("L-A_unit_granularity", 0)
    la_frac = n_la / n_miss if n_miss else 0.0

    def frac(bools):
        return (sum(1 for x in bools if x) / len(bools)) if bools else 0.0

    pos_any = frac([r["rank_any_unit"] is not None and r["rank_any_unit"] <= 10 for r in hit_rows])
    pos_doc = frac([r["rank_doc_head_only"] <= 10 for r in hit_rows])
    neg_frac = shift_hit / nQ
    miss_lex = frac([r["rank_lex_fulltext"] <= 10 for r in rows])
    hit_lex = frac([r["rank_lex_fulltext"] <= 10 for r in hit_rows])
    miss_gt = sum(1 for r in rows if r["gold_gt_440"])
    hit_gt = sum(1 for r in hit_rows if r["gold_gt_440"])
    p_fisher = fisher_two_sided(miss_gt, n_miss - miss_gt, hit_gt, len(hit_rows) - hit_gt)

    out = {
        "schema": "rerank-recall-attribution/1",
        "round": "R626",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
        "axis": "无（定因轮）：生产口径（vec × K=10 = B10）32 例未召回的逐例归属分层",
        "frozen": {"corpus_sha12": "fa7c448c505d", "queries_sha12": "b37fbe564e23",
                   "n_docs": len(corpus), "n_queries": len(queries),
                   "grading": "single-gold (grade 2 / else 0)"},
        "oracle": {
            "independence": "排序实现与单元映射独立（stdlib 纯 Python，零 import 本仓）；**向量源不独立**（冻结件，同源性由 R624 G0 覆盖）",
            "unit_universe": {"n_units": len(unit_vecs), "n_head": len(heads), "n_chunk": len(chunks)},
            "anchor_chunk_mapping_bitexact": anchor,
            "bm25": {"k1": 1.2, "b": 0.75, "field": "全文（**不截断**）"},
        },
        "rank_bands": {"M10_size": len(M10), "band1_(10,50]": len(band1), "band2_(50,200]": len(band2),
                       "band3_(200,1299]": len(band3),
                       "conservation": len(band1) + len(band2) + len(band3) == len(M10) == 32,
                       "band1_qids": band1, "band2_qids": band2, "band3_qids": band3},
        "layers": layers,
        "criteria": {
            "P1_band_conservation": {"pass": len(band1) + len(band2) + len(band3) == len(M10) == 32,
                                     "n_miss": len(M10)},
            "P2_main_attribution": {
                "n_miss": n_miss, "L_A": n_la, "L_B": layers.get("L-B_ranking_signal", 0),
                "L_C": layers.get("L-C_index_missing", 0), "L_A_fraction": round(la_frac, 4),
                "conservation": n_la + layers.get("L-B_ranking_signal", 0) + layers.get("L-C_index_missing", 0) == n_miss,
                "adopt_L_A_ge_030": la_frac >= 0.30,
                "pass": (n_la + layers.get("L-B_ranking_signal", 0) + layers.get("L-C_index_missing", 0) == n_miss
                         and layers.get("L-C_index_missing", 0) == 0)},
            "P3_truncation_and_lexical": {
                "miss_gt440_n": miss_gt, "miss_gt440_frac": round(miss_gt / n_miss, 4),
                "hit_gt440_n": hit_gt, "hit_gt440_frac": round(hit_gt / len(hit_rows), 4),
                "fisher_p": round(p_fisher, 8),
                "miss_lex_at10": round(miss_lex, 4), "hit_lex_at10": round(hit_lex, 4),
                "lex_verdict": ("Adopt" if miss_lex >= 0.30 else "Falsified" if miss_lex <= 0.10 else "Undetermined")},
            "P4_oracle_selfproof": {"pos_hit_rank_any_at10": round(pos_any, 4),
                                    "pos_hit_rank_doc_at10": round(pos_doc, 4),
                                    "neg_query_shift_hit_at10": round(neg_frac, 4),
                                    "anchor_pass": anchor["pass"],
                                    "teeth": (neg_frac <= 0.20) and anchor["pass"]},
            "P5_zero_regression": {"product_source_change": 0,
                                   "note": "本轮不构建、不重跑臂、不改 pin 器具；冻结件逐字节复用"},
        },
        "per_case_miss": sorted(rows, key=lambda r: r["qid"]),
        "per_case_hit": sorted(hit_rows, key=lambda r: r["qid"]),
        "union_oracle_exact": {
            "n_queries": len(all_rows),
            "dense_any_at10_n": sum(1 for r in all_rows if r["rank_any_unit"] is not None and r["rank_any_unit"] <= 10),
            "lex_at10_n": sum(1 for r in all_rows if r["rank_lex_fulltext"] <= 10),
            "union_at10_n": sum(1 for r in all_rows
                                if (r["rank_any_unit"] is not None and r["rank_any_unit"] <= 10)
                                or r["rank_lex_fulltext"] <= 10),
            "note": "两路独立信号（unit-grain dense / full-text bm25）的**并集天花板**；两侧逐例同表 ⇒ 可精确求并（无需区间）",
        },
        "per_case_hit_summary": {"n": len(hit_rows), "rank_any_at10": round(pos_any, 4),
                                 "rank_doc_at10": round(pos_doc, 4), "lex_at10": round(hit_lex, 4)},
        "rank_any_distribution_miss": {
            "min": min([r["rank_any_unit"] for r in rows if r["rank_any_unit"]] or [None]),
            "median": sorted([r["rank_any_unit"] for r in rows if r["rank_any_unit"]])[len(rows) // 2] if rows else None,
            "max": max([r["rank_any_unit"] for r in rows if r["rank_any_unit"]] or [None]),
        },
        "elapsed_s": round(time.time() - t0, 1),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1))
    log("WROTE", OUT)
    log(json.dumps(out["criteria"], ensure_ascii=False, indent=1))
    log("LAYERS", json.dumps(layers, ensure_ascii=False))
    log("BANDS", json.dumps(out["rank_bands"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
