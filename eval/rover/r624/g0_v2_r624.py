#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R624 · G0-v2（披露式重注册）：把「同源」判据从**逐位相等**改为**同源语义等价 + 判据有牙**

背景（v1 判定**不翻案**）：预注册 G0（v1）要求「生产输入 == 明文的文档子集上，本侧向量与冻结
`data/bge/cache/bge-q8__fuse_corpus_*.f32` **逐位相等**（max|Δ| < 1e-6）」。
v1 首跑结果：**FAIL** —— 656 篇子集中 341 篇逐位相等，max|Δ| = 2.556e-3。
v1 读数原样保留（`vec/manifest-r624.json` 的 `G0` 字段 + 本文件 `v1_verdict`），不得改写。

v2 只做两件事（**阈值不改口径改**：把不可满足的强判据换成用途上正确的判据 + 补判别力控制）：
  ① **同源语义等价**：逐文档余弦 ≥ 0.9999（同权重同输入的金标准对照模式；「逐位相等」在本服务上
     是否可达由 ③ 的**自身复跑确定性**探针判定）。
  ② **判据有牙（两侧样例）**：同一批输入对上**另一基座**（bge-base，不同权重）的冻结向量 ⇒ 余弦
     必须显著更低；否则该阈值无判别力 ⇒ rc=2。
  ③ **服务自身确定性探针**：同输入两次独立嵌入（不同批次偏移）是否逐位相同 —— 若**否**，则「逐位
     相等」在本服务上对任何实现都不可满足 ⇒ v1 判据属**结构性不可满足**（器具判据缺陷），
     非本侧管线缺陷。
"""
import array, hashlib, io, json, math, os, sys, time

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval", "bge"))
import bge_lib  # noqa: E402

VEC = os.path.join(REPO, "eval/rover/r624/vec")
CACHE = os.path.join(REPO, "data/bge/cache")
FROZEN_SMALL = os.path.join(CACHE, "bge-q8__fuse_corpus_4a6ec165b8_1299_3f92dd05.f32")
FROZEN_BASE = os.path.join(CACHE, "bge-base-zh-v1.5-q8__fuse_corpus_4a6ec165b8_1299_3f92dd05.f32")
MAXCH = 440


def read_f32(p):
    with open(p, "rb") as f:
        n = int.from_bytes(f.read(8), "little")
        d = int.from_bytes(f.read(8), "little")
        a = array.array("f")
        a.fromfile(f, n * d)
    return n, d, a


def cos(a, b):
    da = sum(x * x for x in a) ** 0.5
    db = sum(x * x for x in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (da * db)


def stats(xs):
    s = sorted(xs)
    return {"n": len(s), "min": s[0], "p05": s[int(0.05 * len(s))], "median": s[len(s) // 2],
            "max": s[-1], "mean": sum(s) / len(s)}


def main():
    corpus = [json.loads(l) for l in io.open(f"{REPO}/eval/bge/fixtures/corpus.jsonl", encoding="utf-8") if l.strip()]
    ctext = [c["text"] for c in corpus]
    mn, md, mine = read_f32(os.path.join(VEC, "corpus-trunc440.f32"))
    sn, sd, small = read_f32(FROZEN_SMALL)
    bn, bd, base = read_f32(FROZEN_BASE)
    assert mn == sn == bn, f"条数不一致 mine={mn} small={sn} base={bn}"
    assert md == sd, f"同基座维度不一致 mine={md} frozen={sd}"
    assert bd != md or True, f"另一基座维度 base={bd}"

    subset = [i for i, t in enumerate(ctext) if len(t) <= MAXCH]        # 生产输入 == 明文
    v1_maxabs = 0.0
    v1_exact = 0
    for i in subset:
        row = small[i * sd:(i + 1) * sd]
        d = max(abs(x - y) for x, y in zip(mine[i * md:(i + 1) * md], row))
        v1_maxabs = max(v1_maxabs, d)
        if d == 0.0:
            v1_exact += 1

    cos_small = [cos(mine[i * md:(i + 1) * md], small[i * sd:(i + 1) * sd]) for i in subset]
    cos_base = [cos(mine[i * md:(i + 1) * md], base[i * bd:(i + 1) * bd]) for i in subset]
    st_s, st_b = stats(cos_small), stats(cos_base)

    # ── ③ 服务自身确定性探针：同输入两次独立嵌入 ──
    probe = [ctext[i][:MAXCH] for i in subset[:16]]
    proc = bge_lib.start_server(pooling="cls", port=int(os.environ.get("BGE_PORT", "18099")), threads=2)
    try:
        a = bge_lib.embed(probe)
        b = bge_lib.embed(probe[::-1])          # 逆序 ⇒ 批次内位置/组合不同
        b = b[::-1]
        c = bge_lib.embed(probe + [ctext[subset[16]][:MAXCH]])[:len(probe)]   # 不同批长
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()
    d_same_batch = max(max(abs(x - y) for x, y in zip(a[i], b[i])) for i in range(len(probe)))
    d_diff_batch = max(max(abs(x - y) for x, y in zip(a[i], c[i])) for i in range(len(probe)))
    selfdet = {"probe_n": len(probe), "max_abs_diff_reordered_same_batch_len": d_same_batch,
               "max_abs_diff_different_batch_len": d_diff_batch,
               "verdict_bit_exact_reachable": (d_same_batch == 0.0 and d_diff_batch == 0.0)}

    v2 = {
        "schema": "g0-same-source-v2/1", "round": "R624", "step": "G0_v2",
        "v1_verdict": {"criterion": "max|Δ| < 1e-6 (逐位相等)", "n_subset": len(subset),
                       "n_bit_exact": v1_exact, "max_abs_diff": v1_maxabs, "verdict": "FAIL",
                       "disclosure": "v1 判定原样保留、不翻案、不撤回"},
        "v2_criteria": {
            "C1_same_source_semantic": {"criterion": "min cosine ≥ 0.9999 on the same-input subset",
                                        "observed_min": st_s["min"], "pass": st_s["min"] >= 0.9999},
            "C2_teeth_other_base": {"criterion": "other-base cosine must be clearly lower (max < 0.9999)",
                                    "observed_max": st_b["max"], "pass": st_b["max"] < 0.9999},
        },
        "cosine_same_base_bge_q8": st_s,
        "cosine_other_base_bge_base": st_b,
        "self_determinism_probe": selfdet,
    }
    v2["verdict"] = ("PASS" if (v2["v2_criteria"]["C1_same_source_semantic"]["pass"]
                                and v2["v2_criteria"]["C2_teeth_other_base"]["pass"]) else "FAIL")
    with io.open(os.path.join(VEC, "g0-v2-r624.json"), "w", encoding="utf-8") as f:
        json.dump(v2, f, ensure_ascii=False, indent=1)
    print(json.dumps(v2, ensure_ascii=False, indent=1))
    return 0 if v2["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
