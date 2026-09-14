#!/usr/bin/env python3
"""优化版 bge（产品现役量化权重）经 llama.cpp 的吞吐量实测。

被测: /tmp/models/bge-base-zh-v1.5-q8.gguf  (110 MB, q8, sha256 893a0f07…)
通路: llama-server 的 /v1/embeddings（与产品 LlamaCppTextEmbedder 同端点、同启动参数）
启动参数(与产品逐字对齐): -m <model> --host 127.0.0.1 --port P -c 2048 [-t N]
                        --cache-type-k f32 --cache-type-v f32 --flash-attn off --embeddings

判据(开跑前登记):
  M1 token 计数不靠估: 每个文本先经 /tokenize 取**精确** token 数, tokens/s 由它算
  M2 冷/热分开: 同一批次连发两次, 第二次的加速只记为缓存效应, 不计入稳态吞吐
  M3 线程对照: -t 1 与 -t 2 各测一遍(本机 2 vCPU = 1 物理核 + SMT)
  M4 批量可扩: 同一长度下 B ∈ {1, 8, 32} 的 tokens/s 趋势
输出: eval/bge/throughput-llama.json（逐臂增量落盘, 便于中途读取）
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

_ap = argparse.ArgumentParser()
_ap.add_argument("--arms", default=None, help='分号分隔的 "tokens,batch" 列表; 省略则跑全表')
_ap.add_argument("--model", default=None, help="被测 GGUF (默认 110MB 的 bge-base-q8)")
_ap.add_argument("--out", default=None, help="产物路径 (默认 eval/bge/throughput-llama.json)")
_ap.add_argument("--merge", action="store_true", help="与已有产物并账(同臂覆盖)")
_ap.add_argument("--reserve", type=int, default=10, help="每个输入编号前缀占用的 token 预留")
_ARGS = _ap.parse_args()

REPO = pathlib.Path("/home/agentuser/AgentFramework")
MODEL = _ARGS.model or "/tmp/models/bge-base-zh-v1.5-q8.gguf"
BIN = os.environ["AGENTFRAMEWORK_LLAMA_BIN"]
OUT = pathlib.Path(_ARGS.out) if _ARGS.out else REPO / "eval/bge/throughput-llama.json"
LOG = REPO / "eval/bge/throughput-llama.server.log"
PORT = 8951
CTX = 2048

UNIT = ("检索增强生成需要把问题与文档映射到同一向量空间；嵌入模型的质量直接决定召回上限。"
        "The quick brown fox jumps over the lazy dog. ")

ARMS = [
    (32, 1), (32, 8), (32, 32),     # 短文本: 看批量与调度开销
    (256, 1), (256, 8),             # 中文本
    (500, 1), (500, 4),             # 长文本: 模型 n_ctx_train=512 ⇒ 留编号前缀余量后取 500
]
if _ARGS.arms:
    ARMS = [tuple(int(x) for x in a.split(",")) for a in _ARGS.arms.split(";")]

# 量程校正(实测取证, 不是猜): llama-server 日志明确
#   n_ctx_train (512) ⇒ slot ctx 被 cap 到 512; n_batch 2048>ubatch 512 ⇒ 强制 512;
#   输入超 512 token 直接 500: "input (1029 tokens) is too large to process"
#   ⇒ 1024 臂无效(超出模型物理上限), 已换成 512 上限臂。
NOTES = {
    "n_ctx_train": 512,
    "server_warnings": [
        "embeddings enabled with n_batch (2048) > n_ubatch (512) -> setting n_batch = n_ubatch = 512",
        "n_ctx_seq (2048) > n_ctx_train (512) -> capping",
        "n_slots = 4 (llama-server 默认并行槽; 冷/热同批次可能落在不同槽)",
    ],
    "arm_1024_status": "invalid_on_model (input 1029 tokens is too large; 模型上限 512)",
}


def post(path, body, timeout=600):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path, timeout=60):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def build_text(target_tokens: int) -> str:
    """按需重复 UNIT 逼近目标 token 数（真实 token 数随后由 /tokenize 精确测出）。"""
    body = UNIT * (target_tokens // 16 + 4)
    toks = post("/tokenize", {"content": body})["tokens"]
    # 二分裁剪到 <= target
    lo, hi = 0, len(body)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        n = len(post("/tokenize", {"content": body[:mid]})["tokens"])
        if n <= target_tokens:
            lo = mid
        else:
            hi = mid - 1
    text = body[:lo]
    return text


records = []
sha = hashlib.sha256(pathlib.Path(MODEL).read_bytes()).hexdigest()


def dump():
    """落盘; --merge 时与旧产物并账(同臂以本次为准, 失败的臂不覆盖旧成功值)。"""
    recs = records
    if _ARGS.merge and OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))["records"]
        except Exception:  # noqa: BLE001
            prev = []
        done = {(r.get("threads"), r.get("target_tokens"), r.get("batch"))
                for r in recs if "error" not in r}
        recs = [r for r in prev
                if (r.get("threads"), r.get("target_tokens"), r.get("batch")) not in done] + recs
    OUT.write_text(json.dumps({"model": MODEL, "sha256": sha, "ctx": CTX,
                               "notes": NOTES, "records": recs},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def start(threads: int):
    return subprocess.Popen(
        [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-c", str(CTX),
         "-t", str(threads), "--cache-type-k", "f32", "--cache-type-v", "f32",
         "--flash-attn", "off", "--embeddings"],
        stdout=LOG.open("ab"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)


for threads in (2, 1):
    proc = start(threads)
    try:
        for _ in range(180):
            try:
                get("/health"); break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        else:
            raise SystemExit("server 未就绪")

        for target, batch in ARMS:
            base = build_text(max(1, target - _ARGS.reserve))
            exact = len(post("/tokenize", {"content": base})["tokens"])
            # 每个输入加不同编号前缀 ⇒ 各自独立前缀, 避免互相命中缓存
            texts = [f"[{i}] " + base for i in range(batch)]
            toks = [len(post("/tokenize", {"content": t})["tokens"]) for t in texts]

            t0 = time.perf_counter()
            try:
                resp = post("/v1/embeddings", {"input": texts})
            except urllib.error.HTTPError as exc:      # 单臂失败不许掀掉整轮
                detail = exc.read().decode("utf-8", "replace")[:200]
                records.append({"threads": threads, "target_tokens": target, "batch": batch,
                                "error": f"HTTP {exc.code}: {detail}"})
                print(f"t={threads} L={target:4d} B={batch:2d} | FAILED HTTP {exc.code}: {detail}", flush=True)
                dump()
                continue
            d1 = time.perf_counter() - t0
            usage = resp.get("usage", {})
            total_tok = usage.get("prompt_tokens") or sum(toks)

            t0 = time.perf_counter()          # 第二次(热): 同批次重发 ⇒ 只记缓存效应
            post("/v1/embeddings", {"input": texts})
            d2 = time.perf_counter() - t0

            rec = {
                "threads": threads, "target_tokens": target, "batch": batch,
                "tokens_per_text": exact, "total_tokens_measured": sum(toks),
                "total_tokens_reported": total_tok, "dims": len(resp["data"][0]["embedding"]),
                "cold_s": round(d1, 4), "warm_s": round(d2, 4),
                "cold_tokens_per_s": round(total_tok / d1, 2), "warm_tokens_per_s": round(total_tok / d2, 2),
                "cold_texts_per_s": round(batch / d1, 2), "cold_ms_per_text": round(d1 / batch * 1000, 2),
            }
            records.append(rec)
            print(f"t={threads} L={exact:4d} B={batch:2d} | 冷 {d1:7.3f}s {rec['cold_tokens_per_s']:8.2f} tok/s "
                  f"{rec['cold_ms_per_text']:8.2f} ms/条 | 热 {d2:7.3f}s {rec['warm_tokens_per_s']:8.2f} tok/s", flush=True)
            dump()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(1)

print("\nDONE ->", OUT)
