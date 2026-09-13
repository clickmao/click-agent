#!/usr/bin/env python3
"""R407: 判定「ForwardPass 全层共用 blk.0 的 attn_{q,k,v,output}.bias」是否必然算错。

判据（预注册）:
  H0 (缺陷无害): blk.{l}.attn_*.bias 各层字节完全相同 ⇒ 复用 blk.0 与逐层读取**数值等价**。
  H1 (缺陷成立): 至少一个后缀存在 l 使 sha256(blk.l) != sha256(blk.0) ⇒ 复用 blk.0 必使第 l 层偏差,
                 且该偏差**不被任何形状检查捕获** (形状全对) ⇒ 静默算错。
  同时报告: 各层 bias 的 ||Δ||∞ 最大处 (量化偏差幅度), 用于估计影响强度。

用法: python3 scripts/r407_bias_alias_probe.py <model.gguf> [--json out.json]
"""
import hashlib
import json
import os
import struct
import sys

KV_SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
SUFFIXES = ("attn_q.bias", "attn_k.bias", "attn_v.bias", "attn_output.bias")
GGML_F32 = 0


def read_kv(f, t):
    """读一个 KV 值并返回其 python 值 (仅用于推进流与取 alignment)"""
    if t == 8:
        n = struct.unpack("<Q", f.read(8))[0]
        return f.read(n).decode("utf-8", "replace")
    if t == 9:
        et = struct.unpack("<I", f.read(4))[0]
        n = struct.unpack("<Q", f.read(8))[0]
        if et == 8:
            for _ in range(n):
                ln = struct.unpack("<Q", f.read(8))[0]
                f.read(ln)
            return f"<str[{n}]>"
        f.read(n * KV_SIZES.get(et, 4))
        return f"<t{et}[{n}]>"
    sz = KV_SIZES[t]
    raw = f.read(sz)
    if t == 6:
        return struct.unpack("<f", raw)[0]
    return int.from_bytes(raw, "little", signed=(t in (1, 3, 5)))


def main():
    path = sys.argv[1]
    out_json = None
    if "--json" in sys.argv:
        out_json = sys.argv[sys.argv.index("--json") + 1]

    f = open(path, "rb")
    if f.read(4) != b"GGUF":
        print("error{kind=not_gguf}")
        return 2
    ver = struct.unpack("<I", f.read(4))[0]
    n_tensors = struct.unpack("<Q", f.read(8))[0]
    n_kv = struct.unpack("<Q", f.read(8))[0]
    base = path.replace("\\", "/").rsplit("/", 1)[-1]
    print(f"gguf{{file={base} ver={ver} tensors={n_tensors} kv={n_kv}}}")

    n_layer = 0
    alignment = 32
    arch = "?"
    for _ in range(n_kv):
        klen = struct.unpack("<Q", f.read(8))[0]
        key = f.read(klen).decode("utf-8", "replace")
        t = struct.unpack("<I", f.read(4))[0]
        val = read_kv(f, t)
        if key == "general.alignment":
            alignment = int(val)
        elif key.endswith(".block_count"):
            n_layer = int(val)
        elif key == "general.architecture":
            arch = val
    print(f"cfg{{arch={arch} block_count={n_layer} alignment={alignment}}}")

    tensors = {}
    order = []
    for _ in range(n_tensors):
        nlen = struct.unpack("<Q", f.read(8))[0]
        name = f.read(nlen).decode("utf-8", "replace")
        nd = struct.unpack("<I", f.read(4))[0]
        dims = [struct.unpack("<q", f.read(8))[0] for _ in range(nd)]
        ggml = struct.unpack("<I", f.read(4))[0]
        off = struct.unpack("<q", f.read(8))[0]
        tensors[name] = (dims, ggml, off)
        order.append(name)

    raw_pos = f.tell()
    data_off = (raw_pos + alignment - 1) // alignment * alignment
    data_len = os.path.getsize(path) - data_off
    print(f"data{{raw_pos={raw_pos} aligned={data_off} pad={data_off - raw_pos} blob={data_len}}}")

    def read_at(off, n):
        f.seek(data_off + off)
        return f.read(n)

    # 数据段的实际大小: 各张量末字节的最大值 (校验索引假设)
    end_max = max((tensors[n][2] + _nbytes(tensors[n][0], tensors[n][1]) for n in order), default=0)
    print(f"data{{max_tensor_end={end_max} blob_ge={data_len >= end_max}}}")

    result = {"arch": arch, "n_layer": n_layer, "suffixes": {}}
    verdict_fail = []
    for suf in SUFFIXES:
        names = [f"blk.{l}.{suf}" for l in range(n_layer)]
        present = [n for n in names if n in tensors]
        if not present:
            print(f"bias{{suffix={suf} present=0}}  (该模型无此 bias ⇒ 复用 blk.0 无害)")
            result["suffixes"][suf] = {"present": 0}
            continue
        hashes, firsts, dims0, types = [], [], None, set()
        for n in names:
            d, ty, off = tensors[n]
            nbytes = _nbytes(d, ty)
            raw = read_at(off, nbytes)
            h = hashlib.sha256(raw).hexdigest()
            hashes.append(h)
            types.add(ty)
            dims0 = dims0 or d
            fv = struct.unpack("<f", raw[:4])[0] if ty == GGML_F32 else None
            firsts.append(fv)
        distinct = len(set(hashes))
        same_as_0 = sum(1 for h in hashes if h == hashes[0])
        # 逐层与第 0 层的最大绝对差 (仅 F32 可直读)
        maxdiff = 0.0
        if types == {GGML_F32}:
            ref = struct.unpack(f"<{dims0[0]}f", read_at(tensors[names[0]][2], 4 * dims0[0]))
            for n in names[1:]:
                off = tensors[n][2]
                cur = struct.unpack(f"<{dims0[0]}f", read_at(off, 4 * dims0[0]))
                maxdiff = max(maxdiff, max(abs(a - b) for a, b in zip(cur, ref)))
        print(f"bias{{suffix={suf} present={len(present)}/{n_layer} dims={dims0} types={sorted(types)} "
              f"distinct_sha256={distinct} same_as_blk0={same_as_0} max_absdiff_vs_blk0={maxdiff:.6g}}}")
        result["suffixes"][suf] = {
            "present": len(present), "dims": dims0, "types": sorted(types),
            "distinct_sha256": distinct, "same_as_blk0": same_as_0,
            "max_absdiff_vs_blk0": maxdiff, "sha256": hashes,
        }
        if distinct > 1:
            verdict_fail.append(suf)

    if verdict_fail:
        suf_list = ",".join(verdict_fail)
        print(f"VERDICT=H1_DEFECT_CONFIRMED suffixes_with_layer_variation={suf_list}")
        print("  ⇒ 全层复用 blk.0 的 bias 必使这些层的 q/k/v/o 投影整体偏移, 形状检查放行 ⇒ 静默算错")
    else:
        print("VERDICT=H0_HARMLESS 各层 bias 逐字节相同 ⇒ 复用 blk.0 数值等价")
    result["verdict"] = "H1_DEFECT_CONFIRMED" if verdict_fail else "H0_HARMLESS"
    if out_json:
        with open(out_json, "w") as g:
            json.dump(result, g, indent=1)
        print(f"json_out={out_json}")
    return 0


BLOCK = {0: 4, 1: 2, 2: 18, 3: 20, 6: 22, 7: 24, 8: 34, 9: 36, 10: 84, 11: 110, 12: 144, 13: 176, 14: 210}

def _nbytes(dims, ty):
    """按 ggml 类型算一个张量的字节数 (支持本项目出现的 F32/F16/Q4_0/Q8_0/Q4_K/Q6_K)"""
    n = 1
    for d in dims:
        n *= d
    if ty == 0:
        return n * 4
    if ty == 1:
        return n * 2
    if ty == 12:
        return (n // 256) * 144
    if ty == 14:
        return (n // 256) * 210
    if ty == 8:
        return (n // 32) * 34
    if ty == 2:
        return (n // 32) * 18
    raise SystemExit(f"error{{kind=unsupported_type type={ty} elems={n}}}")


if __name__ == "__main__":
    sys.exit(main())
