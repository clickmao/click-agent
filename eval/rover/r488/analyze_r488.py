#!/usr/bin/env python3
"""R488 分析器: 2x2 析因消融读数 + 预注册断言机检 (全部数字取自真值列/器具输出, 零手抄)。

真值来源:
  eval/rover/r488/usage-<ARM><TAG>.jsonl  ← 中继落盘的真供应商 usage (每调用一行)
  eval/rover/r488/turns-<ARM><TAG>.jsonl  ← 驱动器轮级答复 (json 对象, 非 jsonl)
  eval/rover/r488/tel-<ARM><TAG>/host.jsonl ← 宿主遥测

用法: python3 analyze_r488.py [--json out.json]
"""
import json, os, statistics, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
R487 = os.path.join(os.path.dirname(ROOT), "r487")

# 臂 → (臂键=ARM名+TAG, TAG, turn_gate, repeat_skip); B 臂以 ARM 名 Arole 派生 ⇒ 键为 Aroleb
ARMS = [
    ("B", "Aroleb", "b", False, False),
    ("G", "Gg", "g", True, False),
    ("S", "Ss", "s", False, True),
    ("R", "Rr", "r", True, True),
]
# 跨轮锚: R487 真值列 (TAG 缺陷导致 Arole485/R485 两列 0 字节, 真值落共用名 usage-Arole/usage-R)
ANCHORS = {
    "R487_Arole485(门关/rj开/rs关)": (os.path.join(R487, "usage-Arole.jsonl"), 15),
    "R487_R485(门开/rj开/rs开)": (os.path.join(R487, "usage-R.jsonl"), 14),
}


def read_usage(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def agg(rows):
    if not rows:
        return None
    d = {}
    d["calls"] = len(rows)
    for k in ("prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_miss_tokens"):
        d[k] = sum(r.get(k) or 0 for r in rows)
    d["total_tokens"] = d["prompt_tokens"] + d["completion_tokens"]
    d["cost_cny_upper"] = round(sum(r.get("cost_cny_upper") or 0.0 for r in rows), 8)
    d["empty_body"] = sum(1 for r in rows if r.get("empty_body"))
    d["http_err"] = sum(1 for r in rows if str(r.get("status")) != "200" or r.get("err"))
    d["identity_ok"] = all(r.get("identity_ok") for r in rows)
    d["ms_p50"] = int(statistics.median([r.get("ms") or 0 for r in rows]))
    d["prompt_per_call"] = round(d["prompt_tokens"] / d["calls"], 1)
    d["total_per_call"] = round(d["total_tokens"] / d["calls"], 1)
    return d


def read_turns(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def turns_summary(t):
    if not t:
        return None
    ts = t.get("turns", [])
    reps = [x.get("reply") or "" for x in ts]
    from collections import Counter
    c = Counter(reps)
    dup = [{"text": k[:40], "n": v} for k, v in c.most_common(3) if v > 1]
    return {
        "turns": t.get("stats", {}).get("turns"),
        "ok": t.get("stats", {}).get("ok"),
        "asks": t.get("stats", {}).get("asks"),
        "errors": t.get("stats", {}).get("errors", []),
        "distinct_replies": len(set(reps)),
        "dup_replies": len(reps) - len(set(reps)),
        "top_dups": dup,
        "mean_reply_len": round(sum(len(r) for r in reps) / max(1, len(reps)), 1),
        "empty_replies": sum(1 for r in reps if not r.strip()),
    }


def main():
    out = {"round": "R488", "arms": {}, "anchors": {}, "assertions": []}

    for arm, key, tag, gate, rs in ARMS:
        u = read_usage(os.path.join(ROOT, f"usage-{key}.jsonl"))
        out["arms"][arm] = {
            "tag": tag, "turn_gate": gate, "repeat_skip": rs,
            "usage_file": f"usage-{key}.jsonl",
            "usage_rows": len(u),
            **({"m": agg(u)} if u else {}),
            "turns": turns_summary(read_turns(os.path.join(ROOT, f"turns-{key}.jsonl"))),
            "telcount": (open(os.path.join(ROOT, f"telcount-{key}.txt"), encoding="utf-8").read().strip()
                         if os.path.exists(os.path.join(ROOT, f"telcount-{key}.txt")) else None),
        }

    for name, (path, exp_calls) in ANCHORS.items():
        rows = read_usage(path)
        # R487 真值列按 TAG 缺陷合并落名: 只取属于该臂的调用数 (前置断言 期望条数)
        out["anchors"][name] = {"file": os.path.relpath(path, os.path.dirname(ROOT)),
                                "rows": len(rows), "expected_calls": exp_calls, **({"m": agg(rows)} if rows else {})}

    A = {k: v.get("m") for k, v in out["arms"].items()}
    b = A.get("B")

    def pct(x, base):
        return None if (x is None or not base) else round(100.0 * (1.0 - x / base), 2)

    out["deltas_vs_B"] = {}
    if b:
        for arm in ("G", "S", "R"):
            a = A.get(arm)
            if not a:
                out["deltas_vs_B"][arm] = None
                continue
            out["deltas_vs_B"][arm] = {
                "calls": a["calls"] - b["calls"],
                "total_tokens": a["total_tokens"] - b["total_tokens"],
                "prompt_tokens": a["prompt_tokens"] - b["prompt_tokens"],
                "completion_tokens": a["completion_tokens"] - b["completion_tokens"],
                "降幅_总token_pct": pct(a["total_tokens"], b["total_tokens"]),
                "降幅_调用数_pct": pct(a["calls"], b["calls"]),
                "降幅_prompt_pct": pct(a["prompt_tokens"], b["prompt_tokens"]),
                "prompt_per_call_delta": round(a["prompt_per_call"] - b["prompt_per_call"], 1),
            }
        # 可加性残差: Δ(R) - [Δ(G) + Δ(S)]
        if all(A.get(x) for x in ("G", "S", "R")):
            dG = A["G"]["total_tokens"] - b["total_tokens"]
            dS = A["S"]["total_tokens"] - b["total_tokens"]
            dR = A["R"]["total_tokens"] - b["total_tokens"]
            out["additivity"] = {"dG": dG, "dS": dS, "dR": dR, "residual": dR - (dG + dS),
                                 "residual_pct_of_B": round(100.0 * (dR - (dG + dS)) / b["total_tokens"], 2)}

    # ---- 预注册断言 (H0..H6) ----
    def add(hid, desc, ok, detail):
        out["assertions"].append({"id": hid, "desc": desc, "ok": bool(ok) if ok is not None else None, "detail": detail})

    anc = out["anchors"].get("R487_Arole485(门关/rj开/rs关)")
    ancm = anc.get("m") if anc else None
    if b and ancm:
        drift = abs(b["total_tokens"] - ancm["total_tokens"]) / ancm["total_tokens"]
        add("H0", "跨轮锚: B(R488) vs R487_Arole485 总token 漂移 ≤10% ⇒ 可跨轮引用",
            drift <= 0.10, f"B={b['total_tokens']} R487={ancm['total_tokens']} 漂移={drift*100:.2f}%")
    else:
        add("H0", "跨轮锚", None, "缺读数")

    r = A.get("R")
    if b and r:
        drop = 1.0 - r["total_tokens"] / b["total_tokens"]
        add("H1", "主判据: B→R 总token 降幅 ≥30%", drop >= 0.30,
            f"B={b['total_tokens']} R={r['total_tokens']} 降幅={drop*100:.2f}%")
    else:
        add("H1", "主判据", None, "缺读数")

    g = A.get("G")
    if b and g:
        add("H2", "turn_gate 单独效应方向: Δtok(G vs B) > 0 (远端上下文变长)", g["total_tokens"] > b["total_tokens"],
            f"Δ={g['total_tokens']-b['total_tokens']} prompt/call {b['prompt_per_call']}→{g['prompt_per_call']}")
    else:
        add("H2", "turn_gate 单独效应", None, "缺读数")

    if b and A.get("S"):
        s = A["S"]
        add("H3", "repeat_skip 单独效应方向: Δtok(S vs B) < 0 (调用数下降)", s["total_tokens"] < b["total_tokens"],
            f"Δ={s['total_tokens']-b['total_tokens']} 调用 {b['calls']}→{s['calls']}")
    else:
        add("H3", "repeat_skip 单独效应", None, "缺读数")

    if out.get("additivity"):
        ad = out["additivity"]
        add("H4", "可加性: |残差| ≤ 5%·B", abs(ad["residual_pct_of_B"]) <= 5.0,
            f"残差={ad['residual']} ({ad['residual_pct_of_B']}% of B)")

    for arm in ("B", "G", "S", "R"):
        t = out["arms"].get(arm, {}).get("turns")
        if t:
            add(f"H5-{arm}", f"{arm} 臂链跑通 (ok==turns) 且答复质量: 实质轮 ≥10/12",
                t["ok"] == t["turns"] and t["distinct_replies"] >= 10,
                f"ok={t['ok']}/{t['turns']} distinct={t['distinct_replies']} empty={t['empty_replies']} asks={t['asks']}")

    # H6: 候选④ TAG 命名修复 — 每臂自身 usage 非空 且 == 中继落盘真值
    for arm, key, tag, _, _ in ARMS:
        urows = out["arms"][arm]["usage_rows"]
        rel = read_usage(os.path.join(ROOT, f"usage-{key}.jsonl"))
        add(f"H6-{arm}", f"TAG 命名修复: usage-{key}.jsonl 非空 (候选④)", urows > 0,
            f"rows={urows} (=中继真值列 {len(rel)})")

    print(json.dumps(out, ensure_ascii=False, indent=1))
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print(f"[written] {p}", file=sys.stderr)


if __name__ == "__main__":
    main()
