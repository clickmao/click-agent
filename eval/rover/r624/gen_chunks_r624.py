#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R624 · 生产形态向量源（**补块**）：RAGRecall 对 >440ch 文档切 chunk（每块 ≤440ch 独立向量）

代码证据（`src/agent.rag/RAGRecall.cs`）：
  196  document.Embedding = GenerateEmbedding(document.Content)   // 首块 = 主文档向量（truncate 440）
  203  if (document.Content.Length > 440)
  205      var chunkSize = 440;
  207      for (var pos = 0; pos < document.Content.Length; pos += chunkSize)
  209          var chunkText = document.Content.Substring(pos, Math.Min(chunkSize, ...));
  210          if (chunkIdx == 0) { ... }                            // 首块不另建文档
  219          Id = $"{document.Id}#c{chunkIdx}"                     // 其余块各自成文档
  228          cd.Embedding = GenerateEmbedding(chunkText);          // 各自独立向量
  604  const int maxEmbedChars = 440;  embedInput = text[..440]     // 调用前截断

⇒ 生产形态的 dense 路**实收输入集合** = { 每文档首块(=text[..440]) } ∪ { 每文档 i≥1 块 } ∪ { query[..440] }。
  首块与 query 已由 gen_vectors_r624.py 生成；本脚本补 i≥1 的块（块文本天然 ≤440 ⇒ 不截断）。

产物：
  eval/rover/r624/vec/chunks.f32        （头 = u64 n + u64 d，小端 float32）
  eval/rover/r624/vec/keys-chunks.jsonl （逐行 = 一行一个块文本，顺序与 .f32 行一致；**查表键**）
  eval/rover/r624/vec/manifest-chunks.json
"""
import array, hashlib, io, json, os, sys, time

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval", "bge"))
import bge_lib  # noqa: E402

MAXCH = 440
OUTDIR = os.path.join(REPO, "eval", "rover", "r624", "vec")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_f32(p, vecs):
    n, d = len(vecs), len(vecs[0])
    with open(p, "wb") as f:
        f.write(n.to_bytes(8, "little"))
        f.write(d.to_bytes(8, "little"))
        array.array("f", [x for v in vecs for x in v]).tofile(f)
    return n, d


def chunks_of(text):
    """逐字复刻 RAGRecall 的切块规则，只取 chunkIdx >= 1 的块。

    **单位纪律（R624 实测）**：C# `String.Substring/Length` 以 **UTF-16 code unit** 计数，
    而 Python 以 **码点** 计数 ⇒ 文档含星面字符（如 U+1F4A1）时两侧边界错位 1，
    键集缺 3 条（实证：3 条残留 miss 的边界都落在 UTF-16 第 440 单元 = 码点第 439）。
    ⇒ 本函数在 UTF-16 编码上切片，与实现同单位；未配对代理用 surrogatepass 原样保留。
    """
    u = text.encode("utf-16-le", "surrogatepass")
    n_units = len(u) // 2
    out = []
    if n_units > 440:
        idx, pos = 0, 0
        while pos < n_units:
            if idx >= 1:
                out.append(u[pos * 2:(pos + 440) * 2].decode("utf-16-le", "surrogatepass"))
            pos += 440
            idx += 1
    return out


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    corpus = [json.loads(l) for l in io.open(f"{REPO}/eval/bge/fixtures/corpus.jsonl", encoding="utf-8") if l.strip()]
    texts, seen, per_doc = [], set(), []
    for c in corpus:
        ks = chunks_of(c["text"])
        per_doc.append(len(ks))
        for k in ks:
            if k not in seen:
                seen.add(k)
                texts.append(k)
    man = {"round": "R624", "step": "gen_chunks",
           "rule_evidence": "src/agent.rag/RAGRecall.cs:203-233 (chunkSize=440, chunkIdx>=1 独立向量)",
           "n_docs": len(corpus), "n_docs_gt_440": sum(1 for c in corpus if len(c["text"]) > MAXCH),
           "n_chunks_total": sum(per_doc), "n_unique_chunk_texts": len(texts),
           "max_chunk_len": max(len(t) for t in texts) if texts else 0}

    t0 = time.time()
    port = int(os.environ.get("BGE_PORT", "18098"))
    proc = bge_lib.start_server(pooling="cls", port=port, threads=2)
    man["server_start_s"] = round(time.time() - t0, 2)
    try:
        t1 = time.time()
        vecs = bge_lib.embed(texts, port=port) if texts else []   # 必须传同一端口（bge_lib.embed 默认读 BGE_PORT）
        man["embed_s"] = round(time.time() - t1, 2)
        man["dim"] = len(vecs[0]) if vecs else 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()

    vp = os.path.join(OUTDIR, "chunks.f32")
    kp = os.path.join(OUTDIR, "keys-chunks.jsonl")
    write_f32(vp, vecs)
    with io.open(kp, "w", encoding="utf-8") as f:
        for t in texts:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    man["files"] = {"chunks_f32": {"path": "eval/rover/r624/vec/chunks.f32", "sha256": sha256(vp),
                                   "n": len(vecs), "d": man["dim"]},
                    "keys_chunks": {"path": "eval/rover/r624/vec/keys-chunks.jsonl",
                                    "sha256": sha256(kp), "n": len(texts)}}
    with io.open(os.path.join(OUTDIR, "manifest-chunks.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print(json.dumps(man, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
