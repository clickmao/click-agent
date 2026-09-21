#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R624 · 向量源同源闸 + 生产形态向量生成

目的：为「召回 dense 路向量源」形态轴生成**生产形态**向量（bge-q8.gguf ∧ 输入截断 440ch，
与 RAGRecall.GenerateEmbedding 的调用契约逐字一致 —— `text[..440]` 后交给 EmbeddingFunction）。

同源闸 G0（预注册 eval/rover/r624/prereg-r624.json）：
  对**全部 ≤440ch 的文档**（生产输入 == 明文 ⇒ 与冻结 cache 同一输入），本侧自算向量必须与
  `data/bge/cache/bge-q8__fuse_corpus_*.f32` 对应行**逐位相等**（最大绝对差 < 1e-6）。
  不通过 ⇒ rc=2，形态臂不得开跑。

产物（轮工件，非夹具）：
  eval/rover/r624/vec/corpus-trunc440.f32 / queries-trunc440.f32（头 = u64 n + u64 d，小端 float32）
  eval/rover/r624/vec/manifest-r624.json（sha256 逐文件 + G0 读数 + 计数）
"""
import array, hashlib, io, json, os, sys, time

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval", "bge"))
import bge_lib  # noqa: E402

MAXCH = 440          # = RAGRecall.GenerateEmbedding 的 maxEmbedChars
OUTDIR = os.path.join(REPO, "eval", "rover", "r624", "vec")
FROZEN = os.path.join(REPO, "data", "bge", "cache",
                      "bge-q8__fuse_corpus_4a6ec165b8_1299_3f92dd05.f32")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_f32(p):
    with open(p, "rb") as f:
        n = int.from_bytes(f.read(8), "little")
        d = int.from_bytes(f.read(8), "little")
        a = array.array("f")
        a.fromfile(f, n * d)
    return n, d, a


def write_f32(p, vecs):
    n, d = len(vecs), len(vecs[0])
    with open(p, "wb") as f:
        f.write(n.to_bytes(8, "little"))
        f.write(d.to_bytes(8, "little"))
        a = array.array("f", [x for v in vecs for x in v])
        a.tofile(f)
    return n, d


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    corpus = [json.loads(l) for l in io.open(f"{REPO}/eval/bge/fixtures/corpus.jsonl", encoding="utf-8") if l.strip()]
    queries = [json.loads(l) for l in io.open(f"{REPO}/eval/bge/fixtures/queries.jsonl", encoding="utf-8") if l.strip()]
    ctext = [c["text"] for c in corpus]
    qtext = [q["query"] for q in queries]
    # 生产输入 = 截断 440ch（GenerateEmbedding 在调用 EmbeddingFunction 之前截断）
    ctr = [t[:MAXCH] for t in ctext]
    qtr = [t[:MAXCH] for t in qtext]

    manifest = {
        "round": "R624", "max_embed_chars": MAXCH,
        "model": bge_lib.MODEL, "model_sha256": sha256(bge_lib.MODEL) if os.path.exists(bge_lib.MODEL) else None,
        "n_corpus": len(ctr), "n_queries": len(qtr),
        "n_docs_gt_440": sum(1 for t in ctext if len(t) > MAXCH),
    }

    # ── 启动嵌入服务（懒启动；失败即异常，禁静默兜底）──
    t0 = time.time()
    proc = bge_lib.start_server(pooling="cls", port=int(os.environ.get("BGE_PORT", "18099")), threads=2)
    manifest["server_start_s"] = round(time.time() - t0, 2)
    try:
        t1 = time.time()
        cv = bge_lib.embed(ctr)
        qv = bge_lib.embed(qtr)
        manifest["embed_s"] = round(time.time() - t1, 2)
        manifest["dim"] = len(cv[0]) if cv else 0
        assert all(len(v) == manifest["dim"] for v in cv + qv), "维度不一致"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()

    cp = os.path.join(OUTDIR, "corpus-trunc440.f32")
    qp = os.path.join(OUTDIR, "queries-trunc440.f32")
    write_f32(cp, cv)
    write_f32(qp, qv)

    # ── G0 同源闸：生产输入 == 明文 的文档（len<=440）逐位比对冻结 cache ──
    fn, fd, fa = read_f32(FROZEN)
    assert fn == len(ctr) and fd == manifest["dim"], f"冻结件形状不符 {fn}x{fd}"
    idx = [i for i, t in enumerate(ctext) if len(t) <= MAXCH]
    maxabs = 0.0
    exact = 0
    for i in idx:
        fd_row = fa[i * fd:(i + 1) * fd]
        d = max(abs(a - b) for a, b in zip(cv[i], fd_row))
        maxabs = max(maxabs, d)
        if d == 0.0:
            exact += 1
    manifest["G0"] = {
        "subset": "docs with len(text) <= max_embed_chars (生产输入 == 明文)",
        "n_subset": len(idx), "n_bit_exact": exact,
        "max_abs_diff": maxabs, "threshold": 1e-6,
        "verdict": "PASS" if maxabs < 1e-6 else "FAIL",
        "note": "截断输入与明文输入**相同**的子集上，本侧管线与冻结 bge 口径必须逐位一致",
    }
    # 对照读数（非闸）：受影响子集（>440ch）本侧向量 vs 冻结 cache 只是**输入不同** ⇒ 差异无判据含义
    diff_idx = [i for i, t in enumerate(ctext) if len(t) > MAXCH]
    dmax = 0.0
    for i in diff_idx[:200]:
        fd_row = fa[i * fd:(i + 1) * fd]
        dmax = max(dmax, max(abs(a - b) for a, b in zip(cv[i], fd_row)))
    manifest["info_truncated_subset_max_abs_diff_sample200"] = dmax

    manifest["files"] = {"corpus_trunc440": {"path": "eval/rover/r624/vec/corpus-trunc440.f32",
                                             "sha256": sha256(cp), "n": len(cv), "d": manifest["dim"]},
                         "queries_trunc440": {"path": "eval/rover/r624/vec/queries-trunc440.f32",
                                              "sha256": sha256(qp), "n": len(qv), "d": manifest["dim"]}}
    with io.open(os.path.join(OUTDIR, "manifest-r624.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, ensure_ascii=False, indent=1))
    print("FILES", json.dumps(manifest["files"], ensure_ascii=False))
    return 0 if manifest["G0"]["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
