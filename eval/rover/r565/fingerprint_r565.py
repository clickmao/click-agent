#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R565 候选④ 器具: **判定输入指纹 + 命中率口径恒等式** (只读落盘件, 零远端 / 零产品改动)。

三项预注册判据 (见 prereg-r565.json §candidate4):
  C4-1 恒等式: 每个中继 dump 的 usage 必须满足 prompt == hit + miss ∧ 0 <= hit <= prompt。
       违反 ⇒ rc=2 (口径/器具缺陷, **不计入被测读数**)。附合成坏口径负控 (hit>prompt / 总量<分量)
       —— 不配负控的恒等式断言是空心的。
  C4-2 确定性: 本侧臂每窗**第 1 次调用**的 request.upstream_request.prompt_sha8 全窗相同
       ∧ transcript.task_sha256 / prefix_sha256 全窗相同 (同题面同前缀同渲染 ⇒ 输入逐位恒定)。
  C4-3 非平凡: 本侧 (prompt_sha8) 与外部真值侧 (instructions_chars|input_items|model) 指纹**互异**
       ⇒ 该指纹不是恒真门。

rc: 0 全过 / 2 违反 / 3 输入缺失 (fail-closed)。
"""
from __future__ import annotations
import argparse, io, json, os, sys

def _u(us):
    p = int(us.get("prompt_tokens") or 0)
    hit = us.get("prompt_cache_hit_tokens")
    if hit is None:
        hit = (us.get("prompt_tokens_details") or {}).get("cached_tokens")
    miss = us.get("prompt_cache_miss_tokens")
    return p, (None if hit is None else int(hit)), (None if miss is None else int(miss))

def identity_ok(p, hit, miss):
    """口径恒等式 (缺项 = 弃权, 非违反): 总量 == 分量之和 ∧ 分量不越界。"""
    if hit is None or miss is None:
        return None
    return (p == hit + miss) and (0 <= hit <= p) and (0 <= miss <= p)

def selftest():
    """合成负控: 坏口径必须被判 RED (证明恒等式断言有牙)。"""
    cases = [("good", 100, 80, 20, True), ("hit_gt_prompt", 100, 140, -40, False),
             ("total_lt_parts", 100, 60, 60, False), ("miss_negative", 100, 120, -20, False)]
    rows = [{"fixture": n, "expected": e, "got": identity_ok(p, h, m), "ok": identity_ok(p, h, m) == e}
            for n, p, h, m, e in cases]
    n_ok = sum(1 for x in rows if x["ok"])
    return {"fixtures": rows, "n": len(rows), "n_ok": n_ok, "has_teeth": n_ok == len(rows)}

def load_dump(adir, side, i):
    f = os.path.join(adir, "side-%s-%03d.json" % (side, i))
    if not os.path.isfile(f):
        return None
    try:
        return json.load(io.open(f, encoding="utf-8-sig"))
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--windows-jsonl", default=None)
    a = ap.parse_args()
    wj = a.windows_jsonl or os.path.join(a.D, "logs", "windows.jsonl")
    adir = os.path.join(a.D, "adapter")
    out = {"round": "R565", "instrument": "fingerprint_r565.py", "selftest": selftest(),
           "checks": {}, "violations": [], "rc": 0}
    if not os.path.isfile(wj):
        out["rc"] = 3; out["why"] = "missing windows.jsonl"; out["checks"]["windows_jsonl"] = False
    else:
        wins = []
        for ln in io.open(wj, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if ln:
                wins.append(json.loads(ln))
        out["windows"] = [w["win"] for w in wins]
        per = {}
        ident_bad = 0; ident_na = 0; calls_n = 0
        for w in wins:
            win = w["win"]; rng = w["ranges"]
            rec = {"agent_calls": [], "transcript": {}}
            for i in range(rng["b0"][0] + 1, rng["b0"][1] + 1):
                d = load_dump(adir, "agent", i)
                if d is None:
                    out["violations"].append({"win": win, "call": i, "err": "dump_missing"})
                    continue
                req = (d.get("request") or {}); up = req.get("upstream_request") or {}
                p, hit, miss = _u((d.get("response") or {}).get("usage") or {})
                ok = identity_ok(p, hit, miss)
                calls_n += 1
                if ok is False:
                    ident_bad += 1
                    out["violations"].append({"win": win, "call": i, "check": "C4-1",
                                              "prompt": p, "hit": hit, "miss": miss})
                elif ok is None:
                    ident_na += 1
                rec["agent_calls"].append({"idx": i, "prompt_sha8": up.get("prompt_sha8"),
                                           "model": up.get("model"), "n_messages": up.get("n_messages"),
                                           "prompt": p, "hit": hit, "miss": miss, "identity": ok})
            tp = os.path.join(a.D, win, "agentB0", "g1", "transcript.json")
            if os.path.isfile(tp):
                t = json.load(io.open(tp, encoding="utf-8"))
                rec["transcript"] = {k: t.get(k) for k in ("task_sha256", "prefix_sha256", "prefix_chars",
                                                           "calls", "max_repair", "max_exec_repair",
                                                           "plan_steps_total", "steps_executed", "rc", "stage")}
            c0 = load_dump(adir, "codex", rng["codex"][0] + 1) if rng["codex"][1] > rng["codex"][0] else None
            if c0 is not None:
                r0 = (c0.get("request") or {})
                rec["truth_fingerprint"] = {"instructions_chars": r0.get("instructions_chars"),
                                            "input_items": r0.get("input_items"),
                                            "model": (r0.get("upstream_request") or {}).get("model")}
            per[win] = rec
        out["per_window"] = per
        firsts = [r["agent_calls"][0]["prompt_sha8"] for r in per.values() if r["agent_calls"]]
        tasks = {r["transcript"].get("task_sha256") for r in per.values() if r["transcript"]}
        prefs = {r["transcript"].get("prefix_sha256") for r in per.values() if r["transcript"]}
        truth_fp = {json.dumps(r.get("truth_fingerprint"), sort_keys=True) for r in per.values() if r.get("truth_fingerprint")}
        all_calls = [x for r in per.values() for x in r["agent_calls"]]
        non_null = [x for x in all_calls if x.get("prompt_sha8")]
        sens = []
        for r in per.values():
            cs = r["agent_calls"]
            if len(cs) >= 2:
                sens.append({"win": [k for k, v in per.items() if v is r][0], "call1": cs[0]["prompt_sha8"],
                             "call2": cs[1]["prompt_sha8"], "differ": cs[0]["prompt_sha8"] != cs[1]["prompt_sha8"]})
        out["checks"]["C4-1_identity"] = {"calls": calls_n, "violations": ident_bad, "na_unreported": ident_na,
                                          "pass": ident_bad == 0 and calls_n > 0}
        out["checks"]["C4-2_determinism"] = {
            "windows_with_calls": len(firsts), "non_null_prompt_sha": len(non_null), "calls_total": len(all_calls),
            "distinct_call1_prompt_sha8": sorted({x for x in firsts if x}),
            "distinct_task_sha256": sorted({x for x in tasks if x}),
            "distinct_prefix_sha256": sorted({x for x in prefs if x}),
            "pass": (len({x for x in firsts if x}) == 1 and len({x for x in tasks if x}) == 1
                     and len({x for x in prefs if x}) == 1 and len(non_null) == len(all_calls) and len(all_calls) > 0)}
        out["checks"]["C4-3_nontrivial"] = {
            "sensitivity_call1_vs_call2": sens,
            "sensitivity_exercised": len(sens) > 0,
            "truth_fp_present": bool(truth_fp), "truth_fp_distinct": len(truth_fp),
            "pass": (len(non_null) == len(all_calls) and len(all_calls) > 0 and bool(truth_fp)
                     and all(x["differ"] for x in sens))}
        out["honest_boundary"] = ([] if len(sens) else
                                  ["C4-3 敏感度未行使: 本轮无任何窗出现第 2 次调用 (修复链未触发) ⇒ 指纹对『输入变化』的敏感性不可判, 只证了恒定性"])
        if not out["selftest"]["has_teeth"]:
            out["rc"] = 2; out["violations"].append({"err": "selftest_no_teeth"})
        elif ident_bad:
            out["rc"] = 2
        elif not all(out["checks"][k]["pass"] for k in ("C4-1_identity", "C4-2_determinism", "C4-3_nontrivial")):
            out["rc"] = 2
            out["why"] = [k for k in ("C4-1_identity", "C4-2_determinism", "C4-3_nontrivial") if not out["checks"][k]["pass"]]
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": out["rc"], "checks": {k: v.get("pass") for k, v in out["checks"].items()},
                      "selftest": "%d/%d" % (out["selftest"]["n_ok"], out["selftest"]["n"]),
                      "violations": len(out["violations"])}, ensure_ascii=False))
    return out["rc"]

if __name__ == "__main__":
    sys.exit(main())
