#!/usr/bin/env python3
"""R404 跨实现对账探针: 本仓 C# 托管 BERT 前向 vs Python/llama.cpp 冻结向量。

判据 (预注册): 同文本、同模型下 cos(C# 向量, llama.cpp 向量) ≥ 0.99 ⇒ 两个独立实现同源。
用法: DOTNET_ROOT=~/.dotnet PATH=$DOTNET_ROOT:$PATH python3 scripts/r404_bge_parity_probe.py [--n 3]
"""
import argparse
import json
import math
import os
import struct
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(REPO, "src", "agent.rover", "bin", "Release", "net10.0", "agent.rover.dll")
HOME = os.path.expanduser("~")
MODELS = [
    ("small", os.path.join(HOME, ".agentframework/models/bge-q8.gguf"),
     os.path.join(REPO, "data/bge/cache/bge-q8__fuse_queries_11a09e25cb_120_3f92dd05.f32")),
    ("base", os.path.join(HOME, ".agentframework/models/bge-base-zh-v1.5-q8.gguf"),
     os.path.join(REPO, "data/bge/cache/bge-base-zh-v1.5-q8__fuse_queries_11a09e25cb_120_3f92dd05.f32")),
]


def load_vecs(path):
    """与 bge_lib.cache_save 同格式: n,d (int64 LE) + n*d float32 LE。"""
    b = open(path, "rb").read()
    n, d = struct.unpack("<qq", b[:16])
    a = struct.unpack("<%df" % (n * d), b[16:16 + n * d * 4])
    return [list(a[i * d:(i + 1) * d]) for i in range(n)]


def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def csharp_embed(model, texts, out_path):
    args = ["dotnet", BIN, "embed", "--model", model]
    for t in texts:
        args += ["--text", t]
    args += ["--dump-vec", out_path]
    r = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    lines = [l for l in r.stdout.splitlines() if l.startswith(("arch{", "dumpvec{", "done{"))]
    for l in lines:
        print("    ", l)
    if r.returncode != 0:
        print("     STDERR:", r.stderr[-500:], file=sys.stderr)
    return load_vecs(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args()

    if not os.path.exists(BIN):
        print("FATAL: agent.rover.dll 未构建")
        return 2
    qs = [json.loads(l)["query"] for l in
          open(os.path.join(REPO, "eval/bge/fixtures/queries.jsonl"), encoding="utf-8")][:args.n]

    verdict = {}
    for name, model, cache in MODELS:
        if not (os.path.exists(model) and os.path.exists(cache)):
            print(f"[{name}] SKIP (model/cache missing)")
            continue
        print(f"[{name}] model={os.path.basename(model)}")
        vecs = csharp_embed(model, qs, f"/tmp/r404_cs_{name}.f32")
        ref = load_vecs(cache)
        per = [round(cos(vecs[i], ref[i]), 6) for i in range(len(qs))]
        worst = min(per)
        verdict[name] = {"dim": len(vecs[0]), "cos": per, "worst": worst,
                         "pass": worst >= 0.99}
        print(f"[{name}] dim={len(vecs[0])} cos={per} worst={worst} "
              f"=> {'PASS' if worst >= 0.99 else 'FAIL'}")

    out = os.path.join(REPO, "eval/bge/r404/parity-probe.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"kind": "r404_parity_probe", "n_texts": len(qs), "models": verdict},
              open(out, "w"), ensure_ascii=False, indent=1)
    print("evidence ->", out)
    return 0 if all(v["pass"] for v in verdict.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
