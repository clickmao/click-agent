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
    """解 (QᵀQ+λI)X = QᵀP 后 **返回 Xᵗ** —— 即"可直接乘"的映射 W (满足 p ≈ W·q)。

    约定说明 (真机缺陷固化, 两层):
      ① 拟合空间必须 == 应用空间 (`Adapter.encode(query_side=True)` 乘的是 λ^(-α) 缩放后的白化向量);
      ② 最小二乘的正规解 X=(QᵀQ+λI)⁻¹QᵀP 是 **列定向**解 (即 Wᵗ, 满足 p ≈ Xᵗ·q)。
         旧代码直接把 X 交给 `matvec(W, w)` (= W·w) → **转置错**, 真机表现 r@1=0.0/median_rank=999
         (比随机更差)。此处统一在**唯一出口**转置, 下游只有"行主序 + matvec"一种约定。
    """
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
    X = [row[r:] for row in M]                    # (QᵀQ+λI)⁻¹QᵀP  — 列定向 (Wᵗ)
    return [[X[j][i] for j in range(r)] for i in range(r)]   # → 可直接乘的 W


# ── 闸门 G3/G5 的**真实**判定件 ──────────────────────────────────────────────
# R395 修两个真缺陷:
#   ① G3 口径分叉: 文档 §5 写"延迟增幅 ≤15% ∧ 内存增幅 ≤15%", 代码却是静态算力占比,
#      两者不是同一件事 → 现按文档语义实装三项, 并把文档改成与代码**逐字同阈值**;
#   ② G5 空心闸门: 原文 g["G5"] = True (恒真) → 现真跑三条逐位判据 + 一枚负控。
MAC_BUDGET = 0.05      # G3a 算力增幅 (每次编码乘加数 / 24M 参数嵌入前向, 静态可复算)
LAT_BUDGET = 0.15      # G3b 延迟增幅 (适配器实测 ms/向量 ÷ **绕缓存**的真实前向 ms/向量)
MEM_BUDGET = 0.15      # G3c 内存增幅 (静态代理: 适配器对象字节 / 嵌入模型文件字节)

# R404 修第三个判定器真缺陷 (G1 阈值落"数学上不可能显著"区):
#   原文 `g["G1"] = best["r@10"] - base_metrics["r@10"] >= 0.025` —— 0.025×120 = **3 条**命中。
#   而 n=120 口径下, 净增 Δ 条时的最小配对 McNemar 双侧 p = 2^(1−Δ) ⇒ Δ=3 时 p≥0.25、
#   Δ=4 时 p≥0.125、Δ<6 **数学上不可能** p<0.05。(实测融合线 15:2 才得到 p=0.0023。)
#   ⇒ 原 G1 会把纯噪声当"提升"放行 (11 轮训练线正是 +2/+4 条被判为"方向对")。
#   现改为**配对检验 ∧ 净增条数**双判据, 阈值先注册、不事后调; AST 审计防漂移 (auto_cycle.py)。
G1_ALPHA = 0.05            # G1a: 配对 McNemar 精确检验双侧 p 上限
G1_MIN_GAIN_QUERIES = 6    # G1b: 净增命中查询数下限 (Δ=6 ⇒ min p=0.0312<0.05; Δ=5 ⇒ 0.0625>0.05)


def mcnemar_exact(b, c):
    """配对 McNemar **精确**检验 (双侧 p): b = 候选命中/基线未命中, c = 基线命中/候选未命中。

    口径: 只用不一致对 (b+c); 双侧 p = min(1, 2·Σ_{k≤min(b,c)} C(b+c,k)/2^(b+c))。
    与 `eval/bge/paired_test.py` 同式 (该脚本冻结值 15:2→0.0023 在此逐位复现, 见 test_gates.py)。
    """
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2 ** n))


def adapter_bytes(ad, dim):
    """适配器常驻字节 (**静态代理**: 对象数组字节数, 非进程 RSS 实测 —— 口径明示, 不冒充实测)。"""
    n = 4 * dim                                    # mean
    if ad.V is not None:
        n += 4 * dim * ad.r + 4 * ad.r             # V + lambdas
    if ad.W:
        n += 4 * ad.r * ad.r                       # W (行主序扁平)
    return n


def measure_forward_ms(corpus, n=24):
    """真实前向成本 (ms/向量)。**必须绕开缓存**: `embed_cached` 命中时返回 0.0 ms,
    拿它当分母会把延迟判据变成 0 分母的垃圾 (R395 实测坑)。"""
    texts = [c["text"][:1200] for c in corpus[:n]]
    t0 = time.time()
    L.embed(texts)
    return (time.time() - t0) * 1000 / max(1, len(texts))


def determinism_checks(ad, cvecs, qvecs, golds, cids, ranks_recorded, probe_n=12):
    """G5 判定器 (三条逐位判据 + 一枚负控; 机检可注入非确定性来验证它有判别力)。

    ① encode_repeat      同输入两次编码逐位一致 (定长迭代/无随机源的实跑证据);
    ② order_invariant    中间插入异质编码后再编码同一向量, 结果不变 (抓"编码器改自身状态");
    ③ ranks_reproducible 用再编码向量重算 recall_metrics, 秩向量与择优时逐位相同;
    ④ negative_control   扰动一个输入分量 → 判定器必须判"不一致" (否则判定器恒真=空心)。
    """
    det = {}
    s = cvecs[:probe_n]
    det["encode_repeat"] = [ad.encode(v) for v in s] == [ad.encode(v) for v in s]
    a1 = [ad.encode(v) for v in s]
    [ad.encode(v, query_side=True) for v in qvecs[:probe_n]]
    det["order_invariant"] = a1 == [ad.encode(v) for v in s]
    cv = [ad.encode(v) for v in cvecs]
    qv = [ad.encode(v, query_side=True) for v in qvecs]
    _, rk = L.recall_metrics(cv, golds, qv, cids)
    det["ranks_reproducible"] = (rk == ranks_recorded)
    m = list(s[0]); m[0] = m[0] + 1e-3
    det["negative_control"] = ([ad.encode(v) for v in s] !=
                               [ad.encode(m)] + [ad.encode(v) for v in s[1:]])
    return det


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

    # R404: 这两个名字原先只在 try/循环内赋值, 静态检查判 "possibly unbound";
    # G1 配对判据要求它们在到闸门那段时**必然有绑定**, 故提前初始化。
    base_ranks = None
    ranks_by_cfg = {}
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
        fwd_ms_per_vec = measure_forward_ms(corpus)   # G3b 分母: 绕缓存的真实前向
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
            # R380 真缺陷修复: 拟合空间必须 == 应用空间。
            # `Adapter.encode(query_side=True)` 是把 W 乘在 **λ^(-α) 缩放后**的向量上
            # (`w = _base/λ^α`), 而旧代码拿 **未缩放** 的 `_base` 去拟合 → 输入被逐维缩放
            # 后再乘 W, 等于用了一个错误的映射 (真机: r@1=0.0 / median_rank=999, 比随机更差)。
            # 现按"应用时所处空间"(λ 缩放后的白化向量) 拟合, 与语料侧 `normalize(w)` 同空间。
            def _apply_space(v):
                z = base_w._base(v)
                return [zi / (base_w.lambdas[i] ** base_w.alpha) for i, zi in enumerate(z)]
            Qr = [_apply_space(v) for v in tqv]
            Pr = [_apply_space(v) for v in tpv]
            W = solve_ridge(Qr, Pr, k, args.ridge_lambda)
            cfgs.append((f"whiten_r{k}_a0.5+ridge", L.Adapter(mu, V, lams, alpha=0.5, W=W,
                                                              meta={"method": "whiten+ridge", "r": k,
                                                                    "lambda": args.ridge_lambda})))

        ranks_by_cfg = {}
        for name, ad in cfgs:
            t0 = time.time()
            cvec_a = [ad.encode(v) for v in cvecs]
            qvec_a = [ad.encode(v, query_side=True) for v in qvecs]
            m, ranks = L.recall_metrics(cvec_a, golds, qvec_a, cids)
            ranks_by_cfg[name] = ranks
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
    g, gd = {}, {}
    if results:
        results.sort(key=lambda r: (-r.get("r@10", 0), -r.get("r@1", 0)))
        best = results[0]
        g = {}
        # G1 = 配对检验 ∧ 净增条数 (R404; 原料 = 逐查询整数秩, 999=未命中)
        assert base_ranks is not None, "G1 配对检验缺基线逐查询秩 (base_ranks 未赋值)"
        _base_r = base_ranks
        _cand_r = ranks_by_cfg.get(best["config"], [])
        _b = _c = 0
        for _br, _cr in zip(_base_r, _cand_r):
            _bh, _ch = _br <= 10, _cr <= 10
            _b += 1 if (_ch and not _bh) else 0
            _c += 1 if (_bh and not _ch) else 0
        gd["G1_detail"] = {"gained": _b, "lost": _c, "net": _b - _c,
                           "p": round(mcnemar_exact(_b, _c), 6),
                           "min_gain": G1_MIN_GAIN_QUERIES, "alpha": G1_ALPHA,
                           "old_rule_hits": round((best["r@10"] - base_metrics["r@10"]) * len(golds), 2)}
        g["G1"] = (gd["G1_detail"]["net"] >= G1_MIN_GAIN_QUERIES
                   and mcnemar_exact(_b, _c) < G1_ALPHA)
        g["G2"] = best["r@1"] >= base_metrics["r@1"] - 0.0083
        mac = 2 * dim * (best["adapter"].r or dim)      # 每次编码的乘加数
        gd["mac_ratio"] = round(mac / (24_000_000 * 2), 5)
        gd["fwd_ms_per_vec"] = round(fwd_ms_per_vec, 3)
        gd["latency_ratio"] = round(best["ms_per_vec"] / fwd_ms_per_vec, 5) if fwd_ms_per_vec else None
        gd["mem_ratio"] = round(adapter_bytes(best["adapter"], dim) / max(1, os.path.getsize(L.MODEL)), 5)
        g["G3"] = ((gd["mac_ratio"] <= MAC_BUDGET)
                   and (gd["latency_ratio"] is not None and gd["latency_ratio"] <= LAT_BUDGET)
                   and (gd["mem_ratio"] <= MEM_BUDGET))
        g["G4"] = abs(best.get("r@10_train", best["r@10"]) - best["r@10"]) <= 0.15
        gd["G5_detail"] = determinism_checks(best["adapter"], cvecs, qvecs, golds, cids,
                                             ranks_by_cfg.get(best["config"], []))
        g["G5"] = all(v is True for v in gd["G5_detail"].values())
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
                   "gates": g, "gate_detail": gd,
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
                     best, verdict, reason, entry, len(pairs), g, gd)
    print(json.dumps({"version": vnum, "verdict": verdict, "reason": reason,
                      "config": best["config"] if best else "-",
                      "base": {k: base_metrics[k] for k in ("r@1", "r@10", "mrr@10")},
                      "gates": g, "gate_detail": gd,
                      "best": {k: best[k] for k in ("r@1", "r@10", "mrr@10", "median_rank")} if best else None,
                      "all": [{k: r[k] for k in ("config", "r@1", "r@10", "mrr@10")} for r in results],
                      "corpus_ms": round(c_ms, 1), "elapsed_s": round(time.time() - t_all, 1)},
                  ensure_ascii=False))
    return 0


def write_report(path, vnum, ts, base, results, best, verdict, reason, entry, n_pairs,
                 gates=None, gd=None):
    rows = "\n".join(
        "| {c} | {r1:.4f} | {r10:.4f} | {m:.4f} | {med} | {ms} |".format(
            c=r["config"], r1=r["r@1"], r10=r["r@10"], m=r["mrr@10"], med=r["median_rank"],
            ms=r.get("ms_per_vec", "-")) for r in results)
    b = best if best else {"r@1": 0, "r@10": 0, "mrr@10": 0, "median_rank": "-", "config": "-"}
    if gd:
        g5 = gd.get("G5_detail", {})
        gates_txt = ("- G1 明细：净增 {n} 条（得 {b} / 失 {c}），配对 McNemar 精确 p={p}"
                     "（阈值：净增 ≥{mg} 条 ∧ p<{al}；旧式 2.5pt 阈值在此只值 {old} 条）\n"
                     "- G3 明细：算力增幅 {m}% / 延迟增幅 {l}%（真前向 {f} ms/向量）/ 内存增幅 {c2}%\n"
                     "- G5 明细：{d5}（负控=True 表示判定器有判别力）").format(
            n=gd.get("G1_detail", {}).get("net"), b=gd.get("G1_detail", {}).get("gained"),
            c=gd.get("G1_detail", {}).get("lost"), p=gd.get("G1_detail", {}).get("p"),
            mg=G1_MIN_GAIN_QUERIES, al=G1_ALPHA, old=gd.get("G1_detail", {}).get("old_rule_hits"),
            m=round(100 * gd.get("mac_ratio", 0), 2), l=round(100 * (gd.get("latency_ratio") or 0), 2),
            f=gd.get("fwd_ms_per_vec"), c2=round(100 * gd.get("mem_ratio", 0), 2),
            d5=" ".join(f"{k}={v}" for k, v in g5.items()) or "-")
    else:
        gates_txt = "- （本次无候选，无闸门明细）"
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

## 闸门（G1 净增 ≥6 条 ∧ 配对 McNemar p<0.05 / G2 r@1 不倒退 / G3 算力 ≤5% ∧ 延迟 ≤15% ∧ 内存 ≤15% / G4 过拟合 ≤15pt / G5 确定性×3+负控）

- 判定：**{verdict}** —— {reason}
{gates_txt}

## 诚实边界

- T1 只改表示空间，**不改基座权重**；T2（部分微调）/T3（全参微调）本机不可行，未做。
- 训练对为 LLM 合成（`llm-from-chunk`），非真实用户检索的标注对；真实检索文本落盘尚未开启（exp7 §2.1 待裁定）。
- 评测集 120 条，1 条 = 0.83pt 分辨率；≥2.5pt 才算提升。
- 原型耗时是纯 Python 口径；产品侧若落地须走 C# `TensorPrimitives`（SIMD）。
"""
    open(path, "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    sys.exit(main())
