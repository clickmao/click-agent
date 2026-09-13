#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bge 闭环共享库: llama-server 控制 / 嵌入 / 缓存 / 指标 / 适配器。

设计约束:
- 纯 stdlib (本机无 numpy/torch), 512 维下矩阵运算用行主序一维数组 + 手写循环, 规模受控;
- 零 shell 依赖之外部调用: 进程用 subprocess 参数数组 (无 shell=True);
- 确定性: 缓存文件名带 model+mtime; 训练用固定随机种子。
"""
import os, sys, json, math, time, array, hashlib, subprocess, socket, urllib.request
from operator import mul

REPO = os.environ.get("BGE_REPO", "/home/agentuser/AgentFramework")
FIX = os.path.join(REPO, "eval", "bge", "fixtures")
DATA = os.path.join(REPO, "data", "bge")
CACHE = os.path.join(DATA, "cache")
# R380 修复: 模型路径曾写死 <repo>/.agentframework/... 而真机文件在 ~/.agentframework/... → llama-server 秒退,
# 脚本却傻等 900s 超时 (每次 cron 白烧 15 分钟, versions/ 一直空)。改为**按序回退**, 全部缺失则快速失败。
_MODEL_CANDIDATES = [
    os.environ.get("BGE_MODEL", ""),
    os.path.join(REPO, ".agentframework", "models", "bge-q8.gguf"),
    os.path.expanduser("~/.agentframework/models/bge-q8.gguf"),
    "/tmp/models/bge-base-zh-v1.5-q8.gguf",
    "/tmp/p3probe/models/bge-q8.gguf",
]
DEFAULT_MODEL = next((c for c in _MODEL_CANDIDATES if c and os.path.exists(c)), _MODEL_CANDIDATES[1])
MODEL = os.environ.get("BGE_MODEL", DEFAULT_MODEL)
PORT = int(os.environ.get("BGE_PORT", "18099"))

def model_tag():
    """模型身份短名 (缓存键必须含它: 否则 bge-small 的缓存会被 bge-base 误用)。"""
    return os.path.basename(MODEL).replace(".gguf", "")


def tag(prefix, texts, model=None):
    """确定性缓存 tag = 模型身份 + 前缀 + 文本指纹 + 条数。

    R370 修的真实缺陷: 原 tag 只有 prefix+指纹+条数, 同语料不同模型会命中同一缓存文件,
    指标会变成"张冠李戴"(且静默)。缓存键必须包含一切影响向量值的输入 —— 模型首当其冲。
    """
    m = model or model_tag()
    h = hashlib.sha1(("\n".join(texts)).encode("utf-8")).hexdigest()[:10]
    return f"{m}__{prefix}_{h}_{len(texts)}"


_SEARCH = [os.environ.get("LLAMA_SERVERBIN", ""),
           "/tmp/llama-full/build/bin/llama-server",
           "/tmp/llama.cpp/build/bin/llama-server",
           os.path.expanduser("~/llama.cpp/build/bin/llama-server")]


def find_server():
    for c in _SEARCH:
        if c and os.path.exists(c):
            return c
    raise RuntimeError("llama-server 未找到 (设 LLAMA_SERVERBIN)")


def server_libdir(binpath):
    return os.path.dirname(binpath)


# ── llama-server ────────────────────────────────────────────────────────────
def start_server(pooling="cls", port=None, model=None, threads=2):
    binp = find_server()
    mdl = model or MODEL
    if not os.path.exists(mdl):
        raise RuntimeError(f"嵌入模型缺失: {mdl} (设 BGE_MODEL 或放到 ~/.agentframework/models/)")
    port = port or PORT
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = server_libdir(binp) + ":" + env.get("LD_LIBRARY_PATH", "")
    log = open(os.path.join("/tmp", f"bge_srv_{port}.log"), "w")
    proc = subprocess.Popen(
        [binp, "-m", model or MODEL, "--embeddings", "--pooling", pooling,
         "--threads", str(threads), "--port", str(port), "-c", "512", "-b", "512"],
        stdout=log, stderr=subprocess.STDOUT, env=env)
    t0 = time.time()
    logpath = os.path.join("/tmp", f"bge_srv_{port}.log")
    while time.time() - t0 < 900:
        if proc.poll() is not None:            # R380: 进程已退出 → 立即失败并带上日志尾 (不再傻等 900s)
            tail = ""
            try:
                tail = "".join(open(logpath, encoding="utf-8", errors="replace").readlines()[-6:])
            except Exception:
                pass
            raise RuntimeError(f"llama-server 启动即退出 (code={proc.returncode}) model={model or MODEL}\n{tail}")
        try:
            with socket.create_connection(("127.0.0.1", port), 1):
                # 端口可连 ≠ 模型已加载完: 必须用**真实嵌入请求**确认就绪,
                # 否则首个请求 503 (R370 实测踩坑: qwen3/m3 因此掉队)
                try:
                    embed(["ready"], port=port)
                    return proc
                except Exception:
                    time.sleep(2)
                    continue
        except OSError:
            time.sleep(1)
    proc.kill()
    raise RuntimeError("llama-server 启动超时")


def _post(port, path, payload, timeout=900):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                data=json.dumps(payload).encode("utf-8"),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def embed(texts, port=None, batch=8):
    """批量嵌入, 返回 [[float]]。"""
    port = port or PORT
    out = []
    for i in range(0, len(texts), batch):
        d = _post(port, "/v1/embeddings", {"model": "local", "input": texts[i:i + batch]})
        vecs = [None] * len(d["data"])
        for it in d["data"]:
            vecs[it["index"]] = it["embedding"]
        out.extend(vecs)
    return out


# ── 缓存 (二进制 float32) ───────────────────────────────────────────────────
def _cache_path(tag):
    h = hashlib.sha1(f"{MODEL}:{os.path.getmtime(MODEL) if os.path.exists(MODEL) else 0}".encode()).hexdigest()[:8]
    return os.path.join(CACHE, f"{tag}_{h}.f32")


def cache_load(tag, n_expected, dim_expected=None):
    p = _cache_path(tag)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        n = int.from_bytes(f.read(8), "little")
        d = int.from_bytes(f.read(8), "little")
        if n != n_expected or (dim_expected and d != dim_expected):
            return None
        a = array.array("f")
        a.fromfile(f, n * d)
    return [list(a[i * d:(i + 1) * d]) for i in range(n)]


def cache_save(tag, vecs):
    os.makedirs(CACHE, exist_ok=True)
    p = _cache_path(tag)
    n, d = len(vecs), len(vecs[0])
    with open(p, "wb") as f:
        f.write(n.to_bytes(8, "little")); f.write(d.to_bytes(8, "little"))
        a = array.array("f", [x for v in vecs for x in v])
        a.tofile(f)
    return p


def embed_cached(tag, texts, port=None):
    v = cache_load(tag, len(texts))
    if v is not None:
        return v, 0.0
    t0 = time.time()
    v = embed(texts, port=port)
    cache_save(tag, v)
    return v, (time.time() - t0) * 1000 / max(1, len(texts))


# ── 向量工具 ────────────────────────────────────────────────────────────────
def normalize(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def mean_vec(vecs):
    d = len(vecs[0]); m = [0.0] * d
    for v in vecs:
        m = [a + b for a, b in zip(m, v)]
    return [x / len(vecs) for x in m]


def sub(v, m):
    return [v[i] - m[i] for i in range(len(v))]


def dot(a, b):
    """C 级循环点积 (sum+map 比 Python 层 for 快 3~5×)"""
    return sum(map(mul, a, b))


def matvec(M, v):
    """行主序矩阵 (r×d) 乘 d 维向量 → r 维。

    接受两种形状: 扁平行主序 [r*d] 或嵌套行 [[d]] —— **统一按扁平行主序处理**。
    (真机缺陷: solve_ridge 产出的 W 是嵌套行, 而本函数/save 假设扁平 → 首次真跑才炸;
     形状不一致属"静默语义错", 故在此显式归一 + 断言, 不留两种解释。)
    """
    if M and isinstance(M[0], (list, tuple)):
        M = [x for row in M for x in row]
    d = len(v)
    assert d > 0 and len(M) % d == 0, "matvec: 形状不匹配 len(M)=%d d=%d" % (len(M), d)
    r = len(M) // d
    return [dot(M[i * d:(i + 1) * d], v) for i in range(r)]


def power_iteration(cov_rows, d, iters=24, seed=13):
    """协方差矩阵 top-1 特征向量 (定长迭代 + 固定起点 → 确定性)。"""
    x = normalize([(1.0 + (seed * (i + 1)) % 7) / 8.0 for i in range(d)])
    for _ in range(iters):
        y = matvec(cov_rows, x)
        n = math.sqrt(dot(y, y))
        if n == 0.0:
            break
        x = [t / n for t in y]
    return dot(x, matvec(cov_rows, x)), x


def matvec_row(M, d, i):
    return M[i * d:(i + 1) * d]


def deflate(cov_rows, d, v, lam):
    """从协方差中扣除 v 方向 (M -= lam·v vᵀ), 切片列表推导实现 (热路径)"""
    M = cov_rows
    for i in range(d):
        vi = lam * v[i]
        if vi == 0.0:
            continue
        b = i * d
        M[b:b + d] = [a - vi * c for a, c in zip(M[b:b + d], v)]
    return M


def covariance(vecs, d, lam_ridge=0.0):
    """Σ = (1/n)·Σ xxᵀ + λI (输入应已中心化), d×d 扁平行主序。"""
    M = [0.0] * (d * d)
    n = len(vecs)
    for v in vecs:
        for i in range(d):
            vi = v[i]
            if vi == 0.0:
                continue
            b = i * d
            M[b:b + d] = [a + vi * c for a, c in zip(M[b:b + d], v)]
    inv = 1.0 / n
    M = [x * inv for x in M]
    if lam_ridge:
        for i in range(d):
            M[i * d + i] += lam_ridge
    return M


def top_components(centered, d, k, iters=20):
    """前 k 个主成分 (幂迭代 + 收缩), 返回 [(lam, v)]"""
    C = covariance(centered, d)
    comps = []
    for t in range(k):
        lam, v = power_iteration(C, d, iters=iters, seed=13 + t * 7)
        if lam <= 1e-9:
            break
        comps.append((lam, v))
        C = deflate(C, d, v, lam)
    return comps


# ── 适配器 (T1) ─────────────────────────────────────────────────────────────
class Adapter:
    """x' = normalize( scale * (Vᵀ (x - μ)) ⊙ lam^{-α} )  [r 维白化子空间]
    可选 query 侧额外线性映射 W (r×r)。"""

    def __init__(self, mean, V, lambdas, alpha=0.5, W=None, meta=None):
        self.d = len(mean)
        self.r = len(lambdas) if lambdas else self.d
        if W is not None and W and isinstance(W[0], (list, tuple)):
            # 形状归一: 嵌套行 → 扁平行主序 (save/load/matvec 只有一种约定)
            W = [x for row in W for x in row]
        if W:
            assert len(W) == self.r * self.r, "Adapter: W 形状 %d ≠ r²=%d" % (len(W), self.r * self.r)
        self.mean, self.V, self.lambdas, self.alpha, self.W = mean, V, lambdas, alpha, W
        self.meta = meta or {}

    def _base(self, x):
        z = sub(x, self.mean)
        if self.V is None:          # 恒等: 仅中心化
            return z
        return [dot(self.V[i], z) for i in range(self.r)]

    def encode(self, x, query_side=False):
        z = self._base(x)
        if self.V is None:
            return normalize(z)
        w = [zi / (self.lambdas[i] ** self.alpha) for i, zi in enumerate(z)]
        if query_side and self.W:
            w = matvec(self.W, w)
        return normalize(w)

    def encode_all(self, vecs, query_side=False):
        return [self.encode(v, query_side) for v in vecs]

    def save(self, path):
        with open(path, "wb") as f:
            f.write(b"BGA1")
            f.write(self.d.to_bytes(4, "little")); f.write(self.r.to_bytes(4, "little"))
            f.write(array.array("f", self.mean).tobytes())
            has_v = 0 if self.V is None else 1
            f.write(bytes([has_v]))
            if self.V:
                f.write(array.array("f", [x for row in self.V for x in row]).tobytes())
                f.write(array.array("f", self.lambdas).tobytes())
            f.write(struct_f(self.alpha))
            has_w = 0 if not self.W else 1
            f.write(bytes([has_w]))
            if self.W:
                f.write(array.array("f", self.W).tobytes())
            j = json.dumps(self.meta, ensure_ascii=False).encode("utf-8")
            f.write(len(j).to_bytes(4, "little")); f.write(j)

    @staticmethod
    def load(path):
        import struct
        with open(path, "rb") as f:
            assert f.read(4) == b"BGA1"
            d = int.from_bytes(f.read(4), "little"); r = int.from_bytes(f.read(4), "little")
            mean = list(array.array("f", f.read(4 * d)))
            has_v = f.read(1)[0]
            V, lam = None, None
            if has_v:
                V = array.array("f", f.read(4 * r * d))
                V = [list(V[i * d:(i + 1) * d]) for i in range(r)]
                lam = list(array.array("f", f.read(4 * r)))
            alpha = struct.unpack("<f", f.read(4))[0]
            has_w = f.read(1)[0]
            W = None
            if has_w:
                W = list(array.array("f", f.read(4 * r * r)))
            n = int.from_bytes(f.read(4), "little")
            meta = json.loads(f.read(n).decode("utf-8"))
        return Adapter(mean, V, lam, alpha, W, meta)


def struct_f(x):
    import struct
    return struct.pack("<f", x)


# ── 指标 ────────────────────────────────────────────────────────────────────
def cos(a, b):
    return dot(a, b)


def recall_metrics(corpus_vecs, gold_ids, query_vecs, corpus_ids, topk=(1, 5, 10, 20)):
    ranks = []
    for qi, qv in enumerate(query_vecs):
        sims = sorted(((dot(qv, cv), i) for i, cv in enumerate(corpus_vecs)), reverse=True)
        gid = gold_ids[qi]
        for rank, (_, i) in enumerate(sims[:50], start=1):
            if corpus_ids[i] == gid:
                ranks.append(rank); break
        else:
            ranks.append(999)
    n = len(ranks)
    rs = sorted(ranks)
    m = {f"r@{k}": round(sum(1 for r in ranks if r <= k) / n, 4) for k in topk}
    m["mrr@10"] = round(sum(1.0 / r for r in ranks if r <= 10) / n, 4)
    m["median_rank"] = rs[n // 2]
    m["mean_rank"] = round(sum(ranks) / n, 2)
    return m, ranks


def load_fixtures():
    corpus = [json.loads(l) for l in open(os.path.join(FIX, "corpus.jsonl"), encoding="utf-8")]
    queries = [json.loads(l) for l in open(os.path.join(FIX, "queries.jsonl"), encoding="utf-8")]
    return corpus, queries


def lexical_baseline(corpus, queries):
    def grams(s):
        s = "".join(ch for ch in s if not ch.isspace())
        return {s[i:i + 2] for i in range(len(s) - 1)}
    cg = [grams(c["text"]) for c in corpus]
    ranks = []
    for q in queries:
        qg = grams(q["query"])
        sims = sorted(((len(qg & g) / (len(qg | g) or 1), i) for i, g in enumerate(cg)), reverse=True)
        for rank, (_, i) in enumerate(sims[:50], start=1):
            if corpus[i]["id"] == q["gold_id"]:
                ranks.append(rank); break
        else:
            ranks.append(999)
    n = len(ranks)
    return {"r@1": round(sum(1 for r in ranks if r == 1) / n, 4),
            "r@10": round(sum(1 for r in ranks if r <= 10) / n, 4),
            "mrr@10": round(sum(1.0 / r for r in ranks if r <= 10) / n, 4)}, ranks


def lexical_ranks(corpus, queries):
    """词法秩向量 (与 lexical_baseline 同口径), 供互补性分析使用。"""
    return lexical_baseline(corpus, queries)[1]


def load_versions():
    p = os.path.join(DATA, "versions", "index.json")
    if not os.path.exists(p):
        return {"versions": []}
    return json.load(open(p, encoding="utf-8"))


def save_versions(idx):
    p = os.path.join(DATA, "versions", "index.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
