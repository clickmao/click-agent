#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R469 器具(离线): 命中率**理论上限分档** —— 把「用户轮长度」从命中率分母里剥离。

模型 (与产品同形, 见 R467 `calls-*.jsonl` 实测):
  prompt_k = prefix_k + new_k
  new_k    = 用户轮 (不可压) + 本地/远端承接 (实测 15~21 字符) + 本轮注入 (预算锁内)
  命中上限 = prefix / (prefix + new)          [前缀逐字节稳定 ⇒ 可缓存]
判据 (预注册):
  C1 逐字节 tail-only 稳定率 = 1.0 (R467 六主调用实测 100%)
  C2 短轮档 (用户轮 ≤ 93.5 tok) 命中上限 ≥ 97% 当且仅当 prefix ≥ 3,023 tok
  C3 长轮档命中上限结构性 < 97% (用户轮单独超 93.5 tok) ⇒ 必须分档声明
输入: eval/rover/r468/real-traffic.json (真实用户轮 1,179 条, R468 机检)
输出: eval/rover/r469/hit-ceiling.json
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IN = os.path.join(HERE, "..", "r468", "real-traffic-corpus.jsonl")
OUT = os.path.join(HERE, "hit-ceiling.json")

CPS = 1.0          # 中文 ~1 token/字 (R461 `FormalPromptContract` 口径)
REDLINE = 0.97
PREFIX_BANDS = [2110, 3000, 4000]   # R467 实测前缀 2,110 tok 起
LEN_BANDS = [(0, 30), (31, 93), (94, 200), (201, 10000)]


def main():
    rows = [json.loads(l) for l in io.open(IN, encoding="utf-8") if l.strip()]
    rows = [r for r in rows if "src" not in r]   # 真实轮 = 无 src 标记 (grid/inline 另有标记)
    lens = sorted(len(r["text"]) for r in rows)
    n = len(lens)
    res = {"n_turns": n, "cps": CPS, "redline": REDLINE, "bands": [], "exact_needed_prefix": {}}
    for lo, hi in LEN_BANDS:
        sel = [L for L in lens if lo <= L <= hi]
        if not sel:
            continue
        mid = sorted(sel)[len(sel) // 2]
        band = {"band_chars": [lo, hi], "turns": len(sel), "share": round(len(sel) / n, 4),
                "median_user_tok": round(mid * CPS, 1), "ceilings": {}}
        for pref in PREFIX_BANDS:
            c = pref / (pref + mid * CPS + 21 + 0)
            band["ceilings"]["prefix_%d" % pref] = round(c, 4)
        band["reachable_97"] = (mid * CPS + 21) <= (1 - REDLINE) / REDLINE * PREFIX_BANDS[-1]
        res["bands"].append(band)
    # 使 97% 成立所需最小前缀 (按各档中位数用户轮)
    for lo, hi in LEN_BANDS:
        sel = [L for L in lens if lo <= L <= hi]
        if not sel:
            continue
        mid = sorted(sel)[len(sel) // 2]
        need = (mid * CPS + 21) * REDLINE / (1 - REDLINE)
        res["exact_needed_prefix"]["%d-%d" % (lo, hi)] = round(need, 1)
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
