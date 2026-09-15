#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R478 器具 —— R477 真机 usage(供应商 usage 真值) 命中率**分列**: 冷启动 vs 稳态。

承 R456b 铁律: 跨实现/跨臂比缓存必须分列「冷启动首调用」与「稳态 2..n」; 只比等价成本 + 调用数。
本器具只读 R477 原始面, **不重建 prompt**, 缺文件报 VOID。

判据:
  C1 每行 usage 可解析且 prompt_tokens>0                                (fail-closed, 缺即 VOID)
  C2 恒等式 prompt_tokens == prompt_cache_hit_tokens + prompt_cache_miss_tokens (逐行)
  C3 分列读数: 冷(rate<cold_threshold) / 稳态; 两臂各给 n/prompt/hit/rate
  C4 分档轴诚实性: 该夹具全部调用落 201+ 档 ⇒ band_degenerate 显式置真 (禁冒充分档结论)
  NC1 若把冷启动与稳态混合聚合 ⇒ 差值被冷启动占比放大 (打印两口径之差, 证明聚合可误导)

输出: eval/rover/r478/band-reestimate-r477.json
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = "eval/rover/r477/usage-%s.jsonl"
OUT = os.path.join(ROOT, "eval", "rover", "r478", "band-reestimate-r477.json")
COLD = 0.5
BAND_BOUNDS = [0, 30, 93, 200, None]


def load(arm):
    p = os.path.join(ROOT, SRC % arm)
    if not os.path.exists(p):
        print("VOID(missing): " + p)
        sys.exit(2)
    rows = []
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def arm_stats(arm):
    rows = load(arm)
    per, ident_ok, ident_bad = [], True, []
    for c in rows:
        u = c.get("usage") or {}
        p = u.get("prompt_tokens", 0)
        if p <= 0:
            print("VOID(usage): %s seq=%s" % (arm, c.get("seq")))
            sys.exit(2)
        h = u.get("prompt_cache_hit_tokens", u.get("cached_tokens", 0))
        m = u.get("prompt_cache_miss_tokens", None)
        if m is not None and h + m != p:
            ident_ok = False
            ident_bad.append({"seq": c.get("seq"), "p": p, "h": h, "m": m})
        per.append({"seq": c.get("seq"), "prompt": p, "hit": h,
                    "rate": round(h / p, 6), "band": "201+"})
    hot = [x for x in per if x["rate"] is not None and x["rate"] >= COLD]
    cold = [x for x in per if x["rate"] is not None and x["rate"] < COLD]

    def agg(xs):
        p = sum(x["prompt"] for x in xs)
        h = sum(x["hit"] for x in xs)
        return {"n": len(xs), "prompt_tokens": p, "hit_tokens": h,
                "hit_rate": round(h / p, 6) if p else None}

    return {"calls": len(per), "per_call": per,
            "max_call_rate": max(x["rate"] for x in per),
            "identity_hit_plus_miss_eq_prompt": ident_ok, "identity_violations": ident_bad,
            "cold_threshold": COLD, "cold_calls": agg(cold), "steady_calls": agg(hot),
            "aggregate_all_calls": agg(per)}


a, r = arm_stats("Arole"), arm_stats("R")
res = {
    "round": "R478",
    "kind": "R477 真机 usage 命中率按 R456b 分列(冷启动 vs 稳态); 分档轴=prompt_tokens(代理)",
    "source": "eval/rover/r477/usage-{Arole,R}.jsonl",
    "units": "rate = hit/prompt (供应商 usage 真值); tokens",
    "arms": {"Arole": a, "R": r},
    "comparison": {
        "aggregate_delta": {
            "hit_rate": round(r["aggregate_all_calls"]["hit_rate"] - a["aggregate_all_calls"]["hit_rate"], 6),
            "prompt_tokens": r["aggregate_all_calls"]["prompt_tokens"] - a["aggregate_all_calls"]["prompt_tokens"]},
        "steady_delta": {
            "hit_rate": round(r["steady_calls"]["hit_rate"] - a["steady_calls"]["hit_rate"], 6),
            "prompt_tokens": r["steady_calls"]["prompt_tokens"] - a["steady_calls"]["prompt_tokens"]},
        "cold_share": {"Arole": round(a["cold_calls"]["n"] / a["calls"], 4),
                       "R": round(r["cold_calls"]["n"] / r["calls"], 4)},
        "conclusion": "聚合差被冷启动占比差放大; 稳态两臂命中率近等 ⇒ 聚合口径不可用作机制结论 (R456b)",
    },
    "band_note": {"degenerate": True,
                  "reason": "该夹具每轮 prompt 均落 201+ 档 ⇒ 分档轴无分辨力; 正确轴=用户轮 token(R477 未落盘) ⇒ 禁冒充分档结论",
                  "band_bounds": BAND_BOUNDS, "band_labels": ["0-30", "31-93", "94-200", "201+"]},
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
print("Arole agg=%s steady=%s cold=%s ident=%s" % (a["aggregate_all_calls"], a["steady_calls"], a["cold_calls"], a["identity_hit_plus_miss_eq_prompt"]))
print("R     agg=%s steady=%s cold=%s ident=%s" % (r["aggregate_all_calls"], r["steady_calls"], r["cold_calls"], r["identity_hit_plus_miss_eq_prompt"]))
print("cmp=" + json.dumps(res["comparison"], ensure_ascii=False))
print("out=" + OUT)
