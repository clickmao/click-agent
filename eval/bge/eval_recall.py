#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性召回率评测 (冻结语料 + 冻结查询 + 冻结指标) — bge 版本择优的**唯一裁判**。

用法:
  python3 eval/bge/eval_recall.py                                  # 基线 (无适配器)
  python3 eval/bge/eval_recall.py --adapter data/bge/versions/v3.bin --label v3
  python3 eval/bge/eval_recall.py --model /tmp/models/bge-base-zh-v1.5-q8.gguf --label bge-base

产物:
  eval/bge/results/<label>.json   指标 (含 lexical 对照)
  eval/bge/ranks/<label>.json     {qid: gold_rank} —— 供 complementarity.py 算互补性

口径纪律 (与 exp7 一致):
- 语料/查询/指标三者冻结; 任何跨版本比较必须同一 fixtures;
- 向量一律显式 L2 归一化 (cos = dot), 不依赖 server 端的隐含归一化;
- ranks 上限 999 = "未进 top50", 是**截断值**不是真实排名。
"""
import os
import sys
import json
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L  # noqa: E402


def l2_norms(vecs, take=5):
    return [round(L.dot(v, v) ** 0.5, 4) for v in vecs[:take]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="GGUF 路径 (默认 bge_lib.MODEL)")
    ap.add_argument("--adapter", default=None, help="适配器 .bin (T1)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--no-lexical", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    if args.model:
        L.MODEL = args.model
    port = args.port or L.PORT
    label = args.label or (L.model_tag() + ("+" + os.path.basename(args.adapter).replace(".bin", "") if args.adapter else ""))

    corpus, queries = L.load_fixtures()
    cids = [c["id"] for c in corpus]
    golds = [q["gold_id"] for q in queries]
    assert len(set(cids)) == len(cids), "语料 id 重复 → 评测无效"
    assert all(g in set(cids) for g in golds), "存在金标准不在语料内 → 评测无效"

    out = {"label": label, "model": os.path.basename(L.MODEL), "adapter": args.adapter,
           "n_corpus": len(corpus), "n_queries": len(queries), "ts": int(time.time())}

    proc = L.start_server(pooling="cls", port=port, threads=2)
    try:
        t0 = time.time()
        ctexts = [c["text"][:1200] for c in corpus]
        cvecs, c_ms = L.embed_cached(L.tag("corpus", ctexts), ctexts, port=port)
        qtexts = [q["query"] for q in queries]
        qvecs, q_ms = L.embed_cached(L.tag("evalq", qtexts), qtexts, port=port)
        out["embed_ms"] = {"corpus": round(c_ms, 1), "queries": round(q_ms, 1),
                           "per_chunk": round(c_ms / len(ctexts), 2)}
        out["raw_norms"] = l2_norms(cvecs)  # 验证 server 是否已归一化 (口径证据)
        cvecs = [L.normalize(v) for v in cvecs]
        qvecs = [L.normalize(v) for v in qvecs]
        base_m, base_ranks = L.recall_metrics(cvecs, golds, qvecs, cids)
        out["baseline"] = base_m
        out["baseline_ranks"] = base_ranks
    finally:
        proc.kill()
        proc.wait()

    if args.adapter:
        ad = L.Adapter.load(args.adapter)
        cv = [L.normalize(v) for v in ad.encode_all(cvecs, query_side=False)]
        qv = [L.normalize(v) for v in ad.encode_all(qvecs, query_side=True)]
        m, ranks = L.recall_metrics(cv, golds, qv, cids)
        out["adapter_metrics"] = m
        out["adapter_ranks"] = ranks
        out["adapter_meta"] = getattr(ad, "meta", None)

    if not args.no_lexical:
        out["lexical"] = L.lexical_baseline(corpus, queries)
    print(json.dumps(out, ensure_ascii=False))

    if not args.no_save:
        rd = os.path.join(L.REPO, "eval", "bge", "results")
        kd = os.path.join(L.REPO, "eval", "bge", "ranks")
        os.makedirs(rd, exist_ok=True)
        os.makedirs(kd, exist_ok=True)
        with open(os.path.join(rd, f"{label}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        with open(os.path.join(kd, f"{label}.json"), "w", encoding="utf-8") as f:
            json.dump({"label": label, "qids": [q["qid"] for q in queries],
                       "ranks": out.get("adapter_ranks") or out["baseline_ranks"]}, f, ensure_ascii=False)
        print(f"[saved] eval/bge/results/{label}.json + eval/bge/ranks/{label}.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
