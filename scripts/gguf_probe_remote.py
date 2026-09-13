#!/usr/bin/env python3
"""远程 GGUF 兼容性预探 —— 只取文件头若干 MB, 解析 metadata + tensor 清单,
在下载整个模型前判定: arch / 量化类型是否引擎可实现 / 是否含引擎未实现的特性。

用途: 用户问"有没有更小/别的模型能用"时, 先探再下, 避免"下了才发现跑不了"。
用法: python3 scripts/gguf_probe_remote.py <repo_id> <file_in_repo> [head_bytes]
"""
import json
import struct
import subprocess
import sys
import tempfile
from collections import Counter

TYPE_SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
GGML = {0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 6: "Q5_0", 7: "Q5_1", 8: "Q8_0",
        9: "Q8_1", 10: "Q2_K", 11: "Q3_K", 12: "Q4_K", 13: "Q5_K", 14: "Q6_K",
        30: "BF16", 39: "MXFP4"}
# 引擎已实现反量化的类型 (权威源 src/agent.rover/quant/Dequant.cs 的 switch)
ENGINE_QUANTS = {"F32", "F16", "Q4_0", "Q8_0", "Q4_K", "Q6_K"}


def rd_str(f):
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8", "replace")


def skip_val(f, t):
    if t == 9:  # array
        et = struct.unpack("<I", f.read(4))[0]
        n = struct.unpack("<Q", f.read(8))[0]
        if et == 8:
            for _ in range(n):
                ln = struct.unpack("<Q", f.read(8))[0]
                f.seek(ln, 1)
        else:
            f.seek(n * TYPE_SIZE[et], 1)
    elif t == 8:
        ln = struct.unpack("<Q", f.read(8))[0]
        f.seek(ln, 1)
    else:
        f.seek(TYPE_SIZE[t], 1)


def main() -> int:
    repo, fn = sys.argv[1], sys.argv[2]
    head = int(sys.argv[3]) if len(sys.argv) > 3 else 24_000_000
    url = f"https://hf-mirror.com/{repo}/resolve/main/{fn}"
    with tempfile.NamedTemporaryFile() as tf:
        subprocess.run(["curl", "-sL", "-m", "180", "-r", f"0-{head}",
                        "-o", tf.name, url], check=True)
        f = open(tf.name, "rb")
        if f.read(4) != b"GGUF":
            print(f"NOT_GGUF {repo}/{fn}")
            return 1
        ver, = struct.unpack("<I", f.read(4))
        n_tensors, n_kv = struct.unpack("<QQ", f.read(16))
        kv, arch = {}, "?"
        for _ in range(n_kv):
            k = rd_str(f)
            t, = struct.unpack("<I", f.read(4))
            if t == 8:
                v = rd_str(f)
            elif t in (6,):
                v = struct.unpack("<f", f.read(4))[0]
            elif t in (4, 5):
                v = struct.unpack("<I" if t == 4 else "<i", f.read(4))[0]
            elif t in (10, 11):
                v = struct.unpack("<Q" if t == 10 else "<q", f.read(8))[0]
            elif t == 0:
                v = f.read(1)[0]
            elif t == 7:
                v = bool(f.read(1)[0])
            else:
                skip_val(f, t)
                v = None
            kv[k] = v
        arch = kv.get("general.architecture", "?")
        tensors = []
        for _ in range(n_tensors):
            name = rd_str(f)
            nd, = struct.unpack("<I", f.read(4))
            dims = struct.unpack("<" + "Q" * nd, f.read(8 * nd))
            tt, = struct.unpack("<I", f.read(4))
            f.seek(8, 1)
            tensors.append((name, dims, GGML.get(tt, f"T{tt}")))
        tnames = [t[0] for t in tensors]
        hist = Counter(t[2] for t in tensors)
        unsupported = sorted({t[2] for t in tensors if t[2] not in ENGINE_QUANTS})
        features = {
            "qk_norm": [n for n in tnames if "q_norm" in n or "k_norm" in n],
            "attn_bias": [n for n in tnames if n.endswith(".bias") and "attn" in n],
            "output_head": "output.weight" in tnames,
            "tied_head": "output.weight" not in tnames and "token_embd.weight" in tnames,
        }
        out = {
            "repo": repo, "file": fn, "gguf_version": ver, "arch": arch,
            "general_name": kv.get("general.name"),
            "block_count": kv.get(f"{arch}.block_count"),
            "head_count": kv.get(f"{arch}.attention.head_count"),
            "head_count_kv": kv.get(f"{arch}.attention.head_count_kv"),
            "rope_freq_base": kv.get(f"{arch}.rope.freq_base"),
            "rope_scaling": kv.get(f"{arch}.rope.scaling.type"),
            "sliding_window": kv.get(f"{arch}.attention.sliding_window"),
            "quant_hist": dict(hist),
            "unsupported_quants": unsupported,
            "features": features,
            "verdict": "RUNNABLE" if not unsupported and not features["qk_norm"]
                       else "BLOCKED",
        }
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
