#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R552 读数汇总打印(仓内可复现): 预注册口径 vs 事后收窄口径并列 + 成本/命中 + 剂量行使面。"""
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
WINS = {"R552b0": [30, 31, 32, 39, 40, 41, 49, 50, 51],
        "R552b1": [33, 34, 35, 43, 44, 45, 52, 53, 54],
        "R552b2": [36, 37, 38, 46, 47, 48, 55, 56, 57]}
d = json.load(io.open(os.path.join(REPO, "eval/rover/r552/readings-r552.json"), encoding="utf-8"))


def med(xs):
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2.0


print("== 1. 逐窗 (有产物的窗; 预注册口径 void 列单列, 不删) ==")
for a, wins in WINS.items():
    for w in wins:
        r = d["windows"].get("w%d" % w, {}).get(a)
        if not r:
            continue
        if r["cases"] and r["cases"]["total"]:
            print("  %s w%-3d %2d/%-2d rc=%-2s stage=%-24s calls=%-2s probe=%s/%s prep=%-4s void_prereg=%-5s rate=%s" % (
                a, w, r["cases"]["pass"], r["cases"]["total"], r["rc"], r["stage"], r["calls"],
                r["public_probe_failed"], r["public_probe_total"], r["probe_repairs"], r["void"],
                (r["upstream"] or {}).get("rate")))
        else:
            print("  %s w%-3d 无产物 rc=%-2s stage=%-24s calls=%-2s rate=%s (真 VOID)" % (
                a, w, r["rc"], r["stage"], r["calls"], (r["upstream"] or {}).get("rate")))

print("\n== 2. 逐臂汇总 (两口径并列) ==")
for a, wins in WINS.items():
    art = [r for r in (d["windows"].get("w%d" % w, {}).get(a) for w in wins) if r and r["cases"] and r["cases"]["total"]]
    prereg = [r for r in art if not r["void"]]
    print("  %-7s 有产物窗 n=%d 质量=%s 中位=%s | 预注册有效窗 n=%d 质量=%s 中位=%s" % (
        a, len(art), ["%d/%d" % (r["cases"]["pass"], r["cases"]["total"]) for r in art], med([r["cases"]["pass"] for r in art]),
        len(prereg), ["%d/%d" % (r["cases"]["pass"], r["cases"]["total"]) for r in prereg], med([r["cases"]["pass"] for r in prereg])))

print("\n== 3. 成本/命中 (中继 dump 归属, 双口径) ==")
for a in WINS:
    h = d["hitrate"][a]
    ok = [r for r in h["rows"] if r.get("status") == "ok"]
    print("  %-7s dump_n=%-3d 可判窗=%s Σcalls=%s Σprompt=%s Σmiss=%s Σhit=%s v_all=%s v_incr=%s 恒等式违反=%d" % (
        a, h["dumps_n"], [(r["win"], r["calls_transcript"], r["dumps_in_window"]) for r in h["rows"]],
        sum(r["calls"] for r in ok), sum(r["sum_prompt_tok"] for r in ok), sum(r["sum_miss_tok"] for r in ok),
        sum(r["sum_hit_tok"] for r in ok), ["%.3f" % r["v_all"] for r in ok], ["%.3f" % r["v_incr"] for r in ok],
        len(h["identity_violations"])))

print("\n== 4. 剂量行使面 (J1) ==")
for a, wins in WINS.items():
    rows = [(w, d["windows"].get("w%d" % w, {}).get(a)) for w in wins]
    pf = [(w, r["public_probe_failed"]) for w, r in rows if r and r["public_probe_failed"] is not None]
    pr = [(w, r["probe_repairs"]) for w, r in rows if r and r["probe_repairs"]]
    print("  %-7s 探针跑过窗=%s | 探针失败窗=%s | probe_repairs>0 窗=%s" % (a, len(pf), pf, pr))

print("\n== 5. 上游退化面 ==")
tot = 0
rc4 = 0
for a, wins in WINS.items():
    for w in wins:
        r = d["windows"].get("w%d" % w, {}).get(a)
        if not r:
            continue
        tot += 1
        if r["rc"] == 4:
            rc4 += 1
print("  窗总数=%d rc=4(契约面)=%d (%.0f%%) | 上游闸触发窗=%d" % (
    tot, rc4, 100.0 * rc4 / tot,
    sum(1 for a in WINS for w in WINS[a] if (d["windows"].get("w%d" % w, {}).get(a) or {}).get("upstream", {}).get("void_upstream"))))
print("  上游闸自检: %s" % json.dumps(d.get("posthoc_selfcheck", {}), ensure_ascii=False))
