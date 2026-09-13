#!/usr/bin/env python3
"""R407 独立 oracle: numpy qwen2 前向 (GGUF 直读), 用于与 C# 引擎逐位/逐层对账。

独立性声明 (跨实现交叉对账铁律):
  * GGUF 解析 + 反量化 = **第三方 gguf-py** (gguf.quants.dequantize), 不是本仓 C# 反量化代码;
  * 前向 = numpy 独立重写 (RMSNorm / NEOX-RoPE / GQA / SwiGLU / untied head);
  * prompt token id 由调用方给定, 与 C# 引擎是**同一串 id** (不接受"重新分词"充当对账)。

判据 (预注册, 跑之前定死):
  P1 端到端: 同 id 序列 greedy N 步, oracle 的**文本**必须与 llama.cpp b1-4df29be 同 prompt 读数一致
     (llama.cpp: `[Start thinking]` -> `To calculate 12 multiplied by 12, I can use the standard
      multiplication method. First, I`); 若 oracle 与 llama.cpp 不符 => 先修 oracle, 不许拿它当判据。
  P2 逐位: 每 step 的 logits 与 C# 引擎 cos >= 0.9999 ∧ argmax 相同 ∧ top-20 交集 >= 19。
  P3 定位: 首个不满足 P2 的 step = 「第一处偏差」; 该 step 的 cos / max|dz| 落盘。
输出: dump 目录 (与 C# --dump-logits 同格式 logits_%03d.f32) + JSON。
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

BLOCK = {0: (1, 4), 1: (1, 2), 2: (32, 18), 3: (32, 20), 8: (32, 34), 12: (256, 144), 13: (256, 176), 14: (256, 210)}


class GgufWeights:
    """按需反量化 (块级切片), 峰值内存受 chunk 控制; 反量化实现来自 gguf-py。"""

    def __init__(self, path: str):
        from gguf import GGUFReader
        from gguf import quants as Q
        self._Q = Q
        self.r = GGUFReader(path)
        self.by = {t.name: t for t in self.r.tensors}
        self.f = self.r.fields

    def field(self, name, default=None):
        if name not in self.f:
            return default
        v = self.f[name].contents()
        return v

    def _flat(self, name):
        t = self.by[name]
        return t, np.asarray(t.data).reshape(-1)

    def _bpr(self, t) -> int:
        ne0 = int(t.shape[0])
        q = int(t.tensor_type)
        bn, bb = BLOCK[q]
        assert ne0 % bn == 0, f"tensor {t.name}: ne0={ne0} not multiple of block {bn}"
        return (ne0 // bn) * bb

    def row(self, name: str, idx: int) -> np.ndarray:
        """(ne0, ne1) 张量的第 idx 列 = 第 idx 个输出向量 (embedding 查表); 1-D 张量 (norm/bias) 取整个。"""
        t, raw = self._flat(name)
        nd = len(t.shape)
        q = int(t.tensor_type)
        if nd == 1:
            assert idx == 0, f"1-D tensor {name} 只有 idx=0, got {idx}"
            v = raw.astype(np.float32) if q == 0 else self._Q.dequantize(raw, t.tensor_type)
            return np.ascontiguousarray(v.astype(np.float32))
        ne0, ne1 = int(t.shape[0]), int(t.shape[1])
        assert 0 <= idx < ne1, f"row out of range: {name}[{idx}] ne1={ne1}"
        bpr = self._bpr(t)
        seg = raw[idx * bpr:(idx + 1) * bpr]
        q = int(t.tensor_type)
        v = seg.astype(np.float32) if q == 0 else self._Q.dequantize(seg, t.tensor_type)
        return np.ascontiguousarray(v[:ne0].astype(np.float32))

    def matvec(self, name: str, x: np.ndarray, chunk: int = 8192) -> np.ndarray:
        """(ne0, ne1) @ x(ne0,) -> (ne1,), 分块反量化以限内存。"""
        t, raw = self._flat(name)
        ne0, ne1 = int(t.shape[0]), int(t.shape[1])
        assert x.shape[0] == ne0, f"{name}: x={x.shape} ne0={ne0}"
        q = int(t.tensor_type)
        out = np.empty(ne1, dtype=np.float32)
        if q == 0:
            W = raw.astype(np.float32).reshape(ne1, ne0)
            return W @ x.astype(np.float32)
        bpr = self._bpr(t)
        for a in range(0, ne1, chunk):
            b = min(ne1, a + chunk)
            Wc = self._Q.dequantize(raw[a * bpr:b * bpr], t.tensor_type).astype(np.float32).reshape(b - a, ne0)
            out[a:b] = Wc @ x
        return out


def rms_norm(x: np.ndarray, w: np.ndarray, eps: float) -> np.ndarray:
    ms = float(np.mean(np.square(x, dtype=np.float64)))
    return (x / np.float32(math.sqrt(ms + eps))) * w


def rope_neox(x: np.ndarray, n_head: int, head_dim: int, pos: int, theta: float) -> np.ndarray:
    half = head_dim // 2
    i = np.arange(half, dtype=np.float64)
    ang = pos * np.power(theta, -(i / half))
    cos = np.cos(ang).astype(np.float32)
    sin = np.sin(ang).astype(np.float32)
    v = x.reshape(n_head, head_dim)
    x1 = v[:, :half].copy()
    x2 = v[:, half:].copy()
    o = np.concatenate([x1 * cos - x2 * sin, x1 * sin + x2 * cos], axis=1)
    return o.reshape(-1)


def softmax(z: np.ndarray) -> np.ndarray:
    m = np.max(z)
    e = np.exp((z - m).astype(np.float64))
    return (e / e.sum()).astype(np.float32)


class Qwen2Oracle:
    def __init__(self, path: str, log=None):
        self.log = log or (lambda s: None)
        self.w = GgufWeights(path)
        f = self.w.f
        self.arch = str(f["general.architecture"].contents())
        a = self.arch
        self.n_layer = int(f[f"{a}.block_count"].contents())
        self.n_head = int(f[f"{a}.attention.head_count"].contents())
        self.n_kv = int(f[f"{a}.attention.head_count_kv"].contents())
        self.hidden = int(f[f"{a}.embedding_length"].contents())
        self.ffn = int(f[f"{a}.feed_forward_length"].contents())
        self.eps = float(f[f"{a}.attention.layer_norm_rms_epsilon"].contents())
        self.theta = float(f[f"{a}.rope.freq_base"].contents())
        kl = f.get(f"{a}.attention.key_length")
        self.head_dim = int(kl.contents()) if kl is not None else self.hidden // self.n_head
        self.vocab = int(f[f"{a}.vocab_size"].contents()) if f"{a}.vocab_size" in f else int(self.w.by["token_embd.weight"].shape[1])
        self.group = self.n_head // self.n_kv
        self.scale = 1.0 / math.sqrt(self.head_dim)
        self.log(f"cfg{{arch={a} layers={self.n_layer} hidden={self.hidden} ffn={self.ffn} "
                 f"heads={self.n_head}/{self.n_kv} head_dim={self.head_dim} theta={self.theta:g} "
                 f"eps={self.eps:g} vocab={self.vocab} group={self.group}}}")
        self.kcache = [[] for _ in range(self.n_layer)]
        self.vcache = [[] for _ in range(self.n_layer)]

    def forward(self, tok: int, pos: int, layer_rms: list | None = None) -> np.ndarray:
        w = self.w
        W = w.matvec
        x = w.row("token_embd.weight", tok)
        for l in range(self.n_layer):
            p = f"blk.{l}."
            xn = rms_norm(x, w.row(p + "attn_norm.weight", 0), self.eps)
            q = W(p + "attn_q.weight", xn)
            k = W(p + "attn_k.weight", xn)
            v = W(p + "attn_v.weight", xn)
            q = q + w.row(p + "attn_q.bias", 0)
            k = k + w.row(p + "attn_k.bias", 0)
            v = v + w.row(p + "attn_v.bias", 0)
            q = rope_neox(q, self.n_head, self.head_dim, pos, self.theta)
            k = rope_neox(k, self.n_kv, self.head_dim, pos, self.theta)
            self.kcache[l].append(k)
            self.vcache[l].append(v)
            K = np.stack(self.kcache[l]).reshape(-1, self.n_kv, self.head_dim)
            V = np.stack(self.vcache[l]).reshape(-1, self.n_kv, self.head_dim)
            attn = np.empty(self.hidden, dtype=np.float32)
            for h in range(self.n_head):
                kv = h // self.group
                sc = (K[:, kv, :] @ q[h * self.head_dim:(h + 1) * self.head_dim]) * np.float32(self.scale)
                pr = softmax(sc)
                attn[h * self.head_dim:(h + 1) * self.head_dim] = pr @ V[:, kv, :]
            ob = w.by.get(p + "attn_output.bias")
            o = W(p + "attn_output.weight", attn)
            if ob is not None:
                o = o + w.row(p + "attn_output.bias", 0)
            x = x + o
            xn2 = rms_norm(x, w.row(p + "ffn_norm.weight", 0), self.eps)
            gate = W(p + "ffn_gate.weight", xn2)
            up = W(p + "ffn_up.weight", xn2)
            act = (gate / (1.0 + np.exp(-gate.astype(np.float32)))) * up
            x = x + W(p + "ffn_down.weight", act)
            if layer_rms is not None:
                layer_rms.append(float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))))
        xn = rms_norm(x, w.row("output_norm.weight", 0), self.eps)
        head = "output.weight" if "output.weight" in w.by else "token_embd.weight"
        logits = self.w.matvec(head, xn, chunk=16384)
        return logits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gguf")
    ap.add_argument("--ids", required=True, help="与 C# 引擎同一串 token id, 逗号分隔")
    ap.add_argument("--steps", type=int, default=24)
    ap.add_argument("--dump-dir", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--layers-step0", default=None, help="落 step0 每层 hidden RMS (逐层对账锚点)")
    args = ap.parse_args()

    w = GgufWeights(args.gguf)
    ids = [int(s) for s in args.ids.split(",") if s.strip() != ""]
    if args.dump_dir:
        Path(args.dump_dir).mkdir(parents=True, exist_ok=True)

    starts = []
    def log(s): print(s, flush=True); starts.append(s)
    m = Qwen2Oracle(args.gguf, log=log)

    pick = []
    t0 = time.time()
    layer_rms = []
    for i, tok in enumerate(ids):
        logits = m.forward(tok, i, layer_rms if (i == 0 and args.layers_step0) else None)
    log(f"prefill{{tokens={len(ids)} seconds={time.time()-t0:.2f} per_token={(time.time()-t0)/len(ids):.3f}}}")
    if args.layers_step0 and layer_rms:
        Path(args.layers_step0).write_text(json.dumps({"layer_rms_after": layer_rms}), encoding="utf-8")
        log(f"layers{{n={len(layer_rms)} first={layer_rms[0]:.6f} last={layer_rms[-1]:.6f}}}")

    def dump(step: int, lg: np.ndarray) -> str | None:
        if not args.dump_dir:
            return None
        f = Path(args.dump_dir) / f"logits_{step:03d}.f32"
        lg.astype("<f4").tofile(f)
        return str(f)

    for step in range(args.steps):
        a = int(np.argmax(logits))
        pick.append(a)
        dump(step, logits)
        top = np.argsort(-logits)[:5]
        log(f"step{step}{{argmax={a} logit={float(logits[a]):.6f} top5={[(int(t), round(float(logits[t]),4)) for t in top]}}}")
        if a == int(w.field("tokenizer.ggml.eos_token_id", 151643)):
            log(f"eos_at_step{step}")
            break
        logits = m.forward(a, len(ids) + step)

    el = time.time() - t0
    log(f"done{{steps={len(pick)} seconds={el:.2f} ids={pick}}}")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "impl": "numpy+gguf-py", "gguf": args.gguf, "ids_in": ids, "ids_out": pick,
            "blocks": len(pick), "seconds": el, "lines": starts,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
