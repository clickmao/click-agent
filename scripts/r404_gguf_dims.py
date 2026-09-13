#!/usr/bin/env python3
"""R404: 打印 GGUF 关键张量 dims / 类型 + 数据段偏移核对 (判定 C# 索引假设是否成立)。

GGML 约定: dims[0] = ne0 = 最快维。权重 W[in,out] 的元素 (i,o) 位于 i + o*ne0
⇒ 行 (固定 o) 在 ne0 方向连续。C# 的 MatMulAdd/embedding 查表都假设这个布局。
用法: python3 scripts/r404_gguf_dims.py <model.gguf>
"""
import struct
import sys

KV_SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
WANT = ("token_embd", "position_embd", "token_types", "token_embd_norm",
        "blk.0.attn_q", "blk.0.attn_output", "blk.0.ffn_up", "blk.0.ffn_down",
        "blk.11.ffn_down")


def main():
    path = sys.argv[1]
    f = open(path, "rb")
    assert f.read(4) == b"GGUF"
    ver = struct.unpack("<I", f.read(4))[0]
    n_tensors = struct.unpack("<Q", f.read(8))[0]
    n_kv = struct.unpack("<Q", f.read(8))[0]
    print(f"file={path} ver={ver} tensors={n_tensors} kv={n_kv}")

    def rstr():
        n = struct.unpack("<Q", f.read(8))[0]
        return f.read(n).decode("utf-8")

    alignment = 32
    n_vocab = None
    for _ in range(n_kv):
        k = rstr()
        t = struct.unpack("<I", f.read(4))[0]
        if t == 8:
            v = rstr()
        elif t == 9:
            et = struct.unpack("<I", f.read(4))[0]
            n = struct.unpack("<Q", f.read(8))[0]
            if et == 8:
                v = f"<str[{n}]>"
                if k == "tokenizer.ggml.tokens":
                    n_vocab = int(n)
                for _ in range(n):
                    rstr()
            else:
                f.read(n * KV_SIZES.get(et, 4))
                v = f"<t{et}[{n}]>"
        else:
            sz = KV_SIZES[t]
            raw = f.read(sz)
            v = int.from_bytes(raw, "little", signed=(t in (1, 3, 5)))
            if t == 6:
                v = struct.unpack("<f", raw)[0]
        if k in ("general.alignment", "tokenizer.ggml.tokens", "general.architecture",
                 "bert.embedding_length", "tokenizer.ggml.add_bos_token",
                 "tokenizer.ggml.add_eos_token", "tokenizer.ggml.model"):
            print(f"  kv {k} = {v}")
            if k == "general.alignment":
                alignment = int(v)

    for _ in range(n_tensors):
        name = rstr()
        nd = struct.unpack("<I", f.read(4))[0]
        dims = [struct.unpack("<q", f.read(8))[0] for _ in range(nd)]
        ggml = struct.unpack("<I", f.read(4))[0]
        off = struct.unpack("<q", f.read(8))[0]
        if any(w in name for w in WANT):
            print(f"  tensor {name} dims={dims} type={ggml} off={off}")

    pos = f.tell()
    aligned = (pos + alignment - 1) // alignment * alignment
    print(f"  data_section: raw_pos={pos} alignment={alignment} aligned={aligned} pad={aligned - pos}")
    print("  C# 假设: dims[0] 必须 == 每行长度 (ne0); 权重行在 ne0 方向连续")


if __name__ == "__main__":
    main()
