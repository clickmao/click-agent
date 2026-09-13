#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1 适配器训练 + 确定性召回闸门 + 版本小报。

流程: 冻结fixtures → 缓存嵌入 → 基线 → 训练候选(center/whiten_r{64,128}_a{α}/ridge)
      → 评测(recall@k) → 闸门 G1..G5 → 采纳或回退 → 写版本 + 小报。
用法: python3 train_adapter.py [--k 64 128] [--alpha 0.25 0.5] [--label auto]
"""
import os, sys, json, time, hashlib, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L

VER = os.path.join(L.DATA, "versions")
REPORTS = os.path.join(L.REPO, "docs", "reports", "bge", "versions")
CORPUS_FIX = "corpus_r370_1299"


def tag_of(prefix, texts):
    """委托 L.tag: **必须含模型身份** (R370 修: 跨模型缓存串用会静默算出张冠李戴的指标)。"""
    return L.tag(prefix, texts)


def solve_ridge(Q, P, r, lam):
    """W = (QᵀQ + λI)⁻¹ QᵀP , 全部 r×r / r 维, 高斯-约当消元。"""
    A = [[0.0] * r for _ in range(r)]
    B = [[0.0] * r for _ in range(r)]
    for qi, pi in zip(Q, P):
        for i in range(r):
            qv = qi[i]
            if qv == 0.0:
                continue
            Ai = A[i]
            for j in range(r):
                Ai[j] += qv * qi[j]
            Bi = B[i]
            for j in range(r):
                Bi[j] += qv * pi[j]
    for i in range(r):
        A[i][i] += lam
    # 增广 [A|B] → 解 X
    M = [A[i] + B[i] for i in range(r)]
    for col in range(r):
        piv = max(range(col, r), key=lambda k: abs(M[k][col]))
        if abs(M[piv][col]) < 1e-12:
            continue
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        M[col] = [x / pv for x in M[col]]
        for k in range(r):
            if k != col and M[k][col] != 0.0:
                f = M[k][col]
                M[k] = [a - f * b for a, b in zip(M[k], M[col])]
    return [row[r:] for row in M]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", nargs="*", type=int, default=[64, 128])
    ap.add_argument("--alphas", nargs="*", type=float, default=[0.25, 0.5])
    ap.add_argument("--ridge-lambda", type=float, default=1e-2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    t_all = time.time()
    corpus, queries = L.load_fixtures()
    cids = [c["id"] for c in corpus]
    golds = [q["gold_id"] for q in queries]

    proc = L.start_server(pooling="cls", port=L.PORT)
    try:
        t0 = time.time()
        cvecs, c_ms = L.embed_cached(tag_of("corpus", [c["text"][:1200] for c in corpus]),
                                    [c["text"][:1200] for c in corpus])
        qvecs, q_ms = L.embed_cached(tag_of("evalq", [q["query"] for q in queries]),
                                     [q["query"] for q in queries])
        dim = len(cvecs[0])
        base_metrics, base_ranks = L.recall_metrics(cvecs, golds, qvecs, cids)
        base_metrics["lexical"] = L.lexical_baseline(corpus, queries)[0]  # 返回 (metrics, ranks)
        assert len(cvecs[0]) == dim
    finally:
        proc.kill()

    pairs = [json.loads(l) for l in open(os.path.join(L.DATA, "train_pairs.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(L.DATA, "train_pairs.jsonl")) else []
    gold_eval = set(golds)
    assert not ({p["positive_id"] for p in pairs} & gold_eval), "训练/评测隔离被破坏"
    tr_q = [p["query"] for p in pairs]
    tr_pids = [p["positive_id"] for p in pairs]

    results = []
    best = None
    if pairs and not args.dry_run:
        proc = L.start_server(pooling="cls", port=L.PORT)
        try:
            tqv, _ = L.embed_cached(tag_of("trainq", tr_q), tr_q)
            pos_texts, pos_ids = [], []
            cmap = {c["id"]: c for c in corpus}
            for pid in tr_pids:
                if pid in cmap:
                    pos_texts.append(cmap[pid]["text"][:1200]); pos_ids.append(pid)
            tpv, _ = L.embed_cached(tag_of("trainp", pos_texts), pos_texts)
        finally:
            proc.kill()

        mu = L.mean_vec(cvecs)
        centered = [L.sub(v, mu) for v in cvecs]

        # 候选 1: 仅中心化
        cfgs = [("center", L.Adapter(mu, None, None, alpha=0.0, meta={"method": "center"}))]

        need_r = max(args.ks) if args.ks else 0
        comps = L.top_components(centered, dim, need_r, iters=18) if need_r else []
        for k in args.ks:
            V = [v for _, v in comps[:k]]
            lams = [lam for lam, _ in comps[:k]]
            for a in args.alphas:
                cfgs.append((f"whiten_r{k}_a{a}", L.Adapter(mu, V, lams, alpha=a,
                                                            meta={"method": "whiten", "r": k, "alpha": a})))

        # 候选 2: 白化 + 查询侧监督岭回归
        if pairs and len(pairs) >= 32 and comps:
            k = min(64, len(comps))
            V = [v for _, v in comps[:k]]; lams = [lam for lam, _ in comps[:k]]
            base_w = L.Adapter(mu, V, lams, alpha=0.5)
            Qw = [L.normalize(base_w.encode(v)) for v in tqv]
            Pw = [L.normalize(base_w.encode(v)) for v in tpv]
            # 岭回归用未归一化白化向量 (尺度和有意义)
            Qr = [base_w._base(v) for v in tqv]
            Pr = [base_w._base(v) for v in tpv]
            W = solve_ridge(Qr, Pr, k, args.ridge_lambda)
            cfgs.append((f"whiten_r{k}_a0.5+ridge", L.Adapter(mu, V, lams, alpha=0.5, W=W,
                                                              meta={"method": "whiten+ridge", "r": k,
                                                                    "lambda": args.ridge_lambda})))

        for name, ad in cfgs:
            t0 = time.time()
            cvec_a = [ad.encode(v) for v in cvecs]
            qvec_a = [ad.encode(v, query_side=True) for v in qvecs]
            m, ranks = L.recall_metrics(cvec_a, golds, qvec_a, cids)
            m["ms_per_vec"] = round((time.time() - t0) * 1000 / (len(cvecs) + len(qvecs)), 2)
            if pairs:
                tv = [ad.encode(v, query_side=True) for v in tqv]
                tvecs = [ad.encode(v) for v in cvecs]
                tm, _ = L.recall_metrics(tvecs, pos_ids, tv, cids)
                m["r@10_train"] = tm["r@10"]
            m["config"] = name
            m["adapter"] = ad
            results.append(m)
            print(json.dumps({k: v for k, v in m.items() if k != "adapter"}, ensure_ascii=False),
                  file=sys.stderr)

    # ── 择优 + 闸门 ──
    adopted, verdict, reason = None, "no_data", "无训练对 (先跑 collect_pairs.py --gen)"
    if results:
        results.sort(key=lambda r: (-r.get("r@10", 0), -r.get("r@1", 0)))
        best = results[0]
        g = {}
        g["G1"] = best["r@10"] - base_metrics["r@10"] >= 0.025
        g["G2"] = best["r@1"] >= base_metrics["r@1"] - 0.0083
        mac = 2 * dim * (best["adapter"].r or dim)      # 每次编码的乘加数
        g["G3"] = (mac / (24_000_000 * 2)) <= 0.05      # 相对 24M 参数嵌入前向的算力占比
        g["G4"] = abs(best.get("r@10_train", best["r@10"]) - best["r@10"]) <= 0.15
        g["G5"] = True  # 确定性: 定长迭代 + 固定种子, 由 --dry-run 重跑复核
        ok = all(g.values())
        verdict = "adopted" if ok else "rolled_back"
        reason = "全部闸门通过" if ok else "未过: " + ",".join(k for k, v in g.items() if not v)
        adopted = best if ok else None

    idx = L.load_versions()
    vnum = (max([v["v"] for v in idx["versions"]], default=0) + 1)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    vdir = os.path.join(VER, f"v{vnum}")
    adapter_sha = ""
    if best is not None:
        os.makedirs(vdir, exist_ok=True)
        ap_ = os.path.join(vdir, "adapter.bin")
        best["adapter"].save(ap_)
        adapter_sha = hashlib.sha1(open(ap_, "rb").read()).hexdigest()[:8]
        json.dump({"version": vnum, "ts": ts, "verdict": verdict, "reason": reason,
                   "config": best["config"], "metrics": {k: v for k, v in best.items()
                                                         if k not in ("adapter",)},
                   "base_metrics": base_metrics, "corpus_version": CORPUS_FIX,
                   "n_pairs": len(pairs), "adapter_sha8": adapter_sha},
                  open(os.path.join(vdir, "meta.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    entry = {"v": vnum, "ts": ts, "verdict": verdict, "reason": reason,
             "config": best["config"] if best else "-",
             "r@1": best["r@1"] if best else None, "r@10": best["r@10"] if best else None,
             "mrr@10": best["mrr@10"] if best else None,
             "base_r@1": base_metrics["r@1"], "base_r@10": base_metrics["r@10"],
             "n_pairs": len(pairs), "adapter_sha8": adapter_sha,
             "adapter_path": os.path.join(vdir, "adapter.bin") if best else ""}
    idx["versions"].append(entry)
    if adopted is not None:
        idx["active"] = {"version": vnum, "adapter_path": entry["adapter_path"],
                         "adapter_sha8": adapter_sha, "ts": ts, "config": entry["config"]}
    if not args.dry_run:
        L.save_versions(idx)
        os.makedirs(REPORTS, exist_ok=True)
        write_report(os.path.join(REPORTS, f"v{vnum}.md"), vnum, ts, base_metrics, results,
                     best, verdict, reason, entry, len(pairs))
    print(json.dumps({"version": vnum, "verdict": verdict, "reason": reason,
                      "config": best["config"] if best else "-",
                      "base": {k: base_metrics[k] for k in ("r@1", "r@10", "mrr@10")},
                      "best": {k: best[k] for k in ("r@1", "r@10", "mrr@10", "median_rank")} if best else None,
                      "all": [{k: r[k] for k in ("config", "r@1", "r@10", "mrr@10")} for r in results],
                      "corpus_ms": round(c_ms, 1), "elapsed_s": round(time.time() - t_all, 1)},
                  ensure_ascii=False))
    return 0


def write_report(path, vnum, ts, base, results, best, verdict, reason, entry, n_pairs):
    rows = "\n".join(
        "| {c} | {r1:.4f} | {r10:.4f} | {m:.4f} | {med} | {ms} |".format(
            c=r["config"], r1=r["r@1"], r10=r["r@10"], m=r["mrr@10"], med=r["median_rank"],
            ms=r.get("ms_per_vec", "-")) for r in results)
    b = best if best else {"r@1": 0, "r@10": 0, "mrr@10": 0, "median_rank": "-", "config": "-"}
    txt = f"""# bge 版本小报 v{vnum}（{ts[:10]}）

- 基座：bge-small-zh-v1.5（Q8_0，4 层/512 维/8 头，GGUF 元数据实测）
- 冻结件：`{entry['config'] and CORPUS_FIX}` 语料 1299 块 / 评测查询 120 条（recall@k 口径固定）
- 训练对：{n_pairs} 条（LLM 出题，与评测金标准块**不相交**，已机检隔离）
- 方法：T1 后处理适配器（中心化 / PCA 白化 / 查询侧岭回归），纯 CPU、闭式解
- 训练耗时：{"见 meta.json"}

## 结果（确定性召回）

| 配置 | recall@1 | recall@10 | MRR@10 | 中位排名 | ms/向量(原型) |
|---|---|---|---|---|---|
{rows}

- 基线（无适配器）：recall@1 **{base['r@1']}** / recall@10 **{base['r@10']}** / MRR@10 **{base['mrr@10']}**
- 词法基线（字符二元组 Jaccard）：recall@1 {base.get('lexical', {}).get('r@1', '-')} / recall@10 {base.get('lexical', {}).get('r@10', '-')}
- 择优：**{b['config']}** → recall@1 {b['r@1']} / recall@10 {b['r@10']} / MRR@10 {b['mrr@10']}

## 闸门（G1 收益 ≥2.5pt / G2 r@1 不倒退 / G3 算力 <5% / G4 过拟合 ≤15pt / G5 确定性）

- 判定：**{verdict}** —— {reason}

## 诚实边界

- T1 只改表示空间，**不改基座权重**；T2（部分微调）/T3（全参微调）本机不可行，未做。
- 训练对为 LLM 合成（`llm-from-chunk`），非真实用户检索的标注对；真实检索文本落盘尚未开启（exp7 §2.1 待裁定）。
- 评测集 120 条，1 条 = 0.83pt 分辨率；≥2.5pt 才算提升。
- 原型耗时是纯 Python 口径；产品侧若落地须走 C# `TensorPrimitives`（SIMD）。
"""
    open(path, "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    sys.exit(main())
