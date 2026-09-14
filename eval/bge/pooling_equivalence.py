#!/usr/bin/env python3
"""池化口径一致性探针: 产品启动形态(不传 --pooling) vs 评测启动形态(--pooling cls)。

动机: 评测线(eval/bge)显式 --pooling cls; 产品线 LlamaServerHost 只传 --embeddings。
      若两者产出的向量不同 ⇒ 评测里量到的召回率不是产品实际召回率(口径错)。
判据(开跑前登记):
  P1 逐元素比较同一文本在两形态下的向量: 若字节级(max|Δ|) 为 0 ⇒ 同口径, 差异为零
  P2 若非零则算 cos 相似度: cos<0.999 判**口径不一致**(必须修产品线)
输出: eval/bge/pooling-equivalence.json
"""
import json
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

REPO = pathlib.Path("/home/agentuser/AgentFramework")
import os  # noqa: E402
BIN = os.environ["AGENTFRAMEWORK_LLAMA_BIN"]
MODEL = "/tmp/models/bge-base-zh-v1.5-q8.gguf"
PORT = 8952
TEXTS = ["检索增强生成的召回上限由嵌入质量决定。", "The quick brown fox jumps over the lazy dog.", "向量空间对齐"]
OUT = REPO / "eval/bge/pooling-equivalence.json"


def embed_all(with_pooling: bool, log_suffix: str):
    args = [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-c", "2048",
            "-t", "2", "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off",
            "--embeddings"]
    if with_pooling:
        args += ["--pooling", "cls"]
    log = open(f"/tmp/pool_{log_suffix}.log", "wb")
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3).read()
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/embeddings",
                                     data=json.dumps({"input": TEXTS}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())["data"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(1)


a = embed_all(True, "cls")
b = embed_all(False, "default")
res = {"model": MODEL, "texts": len(TEXTS), "arms": {}}
for i, (x, y) in enumerate(zip(a, b)):
    va, vb = x["embedding"], y["embedding"]
    dmax = max(abs(p - q) for p, q in zip(va, vb))
    dot = sum(p * q for p, q in zip(va, vb))
    na = sum(p * p for p in va) ** 0.5
    nb = sum(q * q for q in vb) ** 0.5
    res["arms"][f"text{i}"] = {"dims": len(va), "max_abs_diff": round(dmax, 8),
                               "cos": round(dot / (na * nb), 6),
                               "norm_cls": round(na, 6), "norm_default": round(nb, 6)}
worst = min(v["cos"] for v in res["arms"].values())
res["verdict"] = ("same_pooling" if worst > 0.999999 else "POOLING_MISMATCH")
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=2))
print("VERDICT:", res["verdict"])
