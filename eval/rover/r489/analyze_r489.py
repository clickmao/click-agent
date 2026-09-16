#!/usr/bin/env python3
"""R489 判据器: 主臂稳定性三跑 + 同窗基线 (按 prereg_r489.json 逐条机检, 零手抄)。

真值来源:
  eval/rover/r489/usage-<key>.jsonl   ← 中继落盘真供应商 usage (每调用一行; 分母真值)
  eval/rover/r489/tel-<key>/host.jsonl ← 宿主遥测 (仅经 posthoc_quality_r489.py 读)
  eval/rover/r488/usage-Aroleb.jsonl   ← 跨轮锚 (R488 B 臂, 同夹具)

用法: python3 analyze_r489.py [--json out.json] [--force-swap] [--force-degrade]
退出: 0=全部成立 / 1=存在 FAIL / 3=缺输入
"""
import io, json, os, statistics, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
R488 = os.path.join(os.path.dirname(HERE), "r488")
ARMS = [("B", "Aroleb", False, False), ("R1", "R1", True, True), ("R2", "R2", True, True), ("R3", "R3", True, True)]
ACK_TURNS_IN_GRID = 4
ANCHOR_TOTAL = 70944          # R488 B 臂 (同夹具); 运行时用文件复算并与该值比对
ANCHOR_TOL = 0.10


def read_usage(path):
    rows = []
    if not os.path.exists(path):
        return rows
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def agg(rows):
    if not rows:
        return None
    d = {"calls": len(rows)}
    for k in ("prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_miss_tokens"):
        d[k] = sum(r.get(k) or 0 for r in rows)
    d["total_tokens"] = d["prompt_tokens"] + d["completion_tokens"]
    d["empty_body"] = sum(1 for r in rows if r.get("empty_body"))
    d["http_err"] = sum(1 for r in rows if str(r.get("status")) != "200" or r.get("err"))
    d["identity_ok"] = all(r.get("identity_ok") for r in rows)
    d["prompt_per_call"] = round(d["prompt_tokens"] / d["calls"], 1)
    d["total_per_call"] = round(d["total_tokens"] / d["calls"], 1)
    d["finish_reason_hist"] = dict(Counter(str(r.get("finish_reason")) for r in rows))
    d["route_hist"] = dict(Counter(str(r.get("routed_to")) for r in rows))
    return d


def main():
    force_swap = "--force-swap" in sys.argv
    force_degrade = "--force-degrade" in sys.argv
    out = {"round": "R489", "arms": {}, "assertions": [], "negative_controls": [], "checks_posthoc": []}

    missing = []
    A = {}
    for arm, key, gate, rs in ARMS:
        p = os.path.join(HERE, f"usage-{key}.jsonl")
        rows = read_usage(p)
        if not rows:
            missing.append(p)
        A[arm] = agg(rows)
        out["arms"][arm] = {"key": key, "turn_gate": gate, "repeat_skip": rs,
                            "usage_file": f"usage-{key}.jsonl", "usage_rows": len(rows),
                            **(A[arm] or {})}
    if missing:
        print(json.dumps({"error": "缺输入 fail-closed", "missing": missing}, ensure_ascii=False))
        sys.exit(3)

    if force_swap:   # NC2-a: 交换 B 与 R1 的 total ⇒ H1 必翻红
        A["B"], A["R1"] = A["R1"], A["B"]
        out["negative_controls"].append({"id": "NC2-swap", "applied": True,
                                         "note": "B/R1 total 互换后 H1 方向必翻"})

    b = A["B"]
    reps = [A[k] for k in ("R1", "R2", "R3")]

    def pct(x, base):
        return round(100.0 * (1.0 - x / base), 2)

    out["deltas_vs_B"] = {k: {"calls": A[k]["calls"] - b["calls"],
                              "total_tokens": A[k]["total_tokens"] - b["total_tokens"],
                              "降幅_总token_pct": pct(A[k]["total_tokens"], b["total_tokens"]),
                              "降幅_调用数_pct": pct(A[k]["calls"], b["calls"]),
                              "prompt_per_call": A[k]["prompt_per_call"]}
                          for k in ("R1", "R2", "R3")}

    # ---- H0 锚 ----
    anchor_rows = read_usage(os.path.join(R488, "usage-Aroleb.jsonl"))
    anchor = agg(anchor_rows)
    if anchor:
        drift = abs(b["total_tokens"] / (anchor["total_tokens"] or 1) - 1.0)
        out["anchors"] = {"R488_B": {"file": "eval/rover/r488/usage-Aroleb.jsonl",
                                     "total_tokens": anchor["total_tokens"],
                                     "declared_anchor": ANCHOR_TOTAL,
                                     "anchor_selfcheck_ok": anchor["total_tokens"] == ANCHOR_TOTAL,
                                     "drift_vs_r489_B": round(drift * 100, 2)}}
        out["assertions"].append({"id": "H0", "desc": f"锚: |B.total/R488B − 1| ≤ {ANCHOR_TOL:.0%} ⇒ 可跨轮引用 (FAIL 不否定 H1)",
                                  "ok": drift <= ANCHOR_TOL,
                                  "detail": f"B={b['total_tokens']} R488B={anchor['total_tokens']} 漂移={drift*100:.2f}%"})

    # ---- H1 主判据 ----
    drops = {k: 1.0 - A[k]["total_tokens"] / b["total_tokens"] for k in ("R1", "R2", "R3")}
    worst = min(drops.values())
    worst_arm = min(drops, key=drops.get)
    out["assertions"].append({"id": "H1", "desc": "主 KPI 稳健: min_i(1 − R_i.total/B.total) ≥ 0.30 (i=1..3)",
                              "ok": worst >= 0.30,
                              "detail": f"B={b['total_tokens']} " +
                                        " ".join(f"{k}={A[k]['total_tokens']}({drops[k]*100:.2f}%)" for k in drops) +
                                        f" ⇒ 最差={worst_arm} {worst*100:.2f}%"})

    # ---- H2 稳定性 ----
    tots = [A[k]["total_tokens"] for k in ("R1", "R2", "R3")]
    spread = (max(tots) - min(tots)) / statistics.median(tots)
    out["stability"] = {"totals": tots, "min": min(tots), "max": max(tots),
                        "median": statistics.median(tots), "spread_pct": round(spread * 100, 2),
                        "stdev": round(statistics.stdev(tots), 1)}
    out["assertions"].append({"id": "H2", "desc": "主臂稳定性: (max−min)/median ≤ 0.15",
                              "ok": spread <= 0.15,
                              "detail": f"totals={tots} spread={spread*100:.2f}%"})

    # ---- H3/H5 质量面 (读 posthoc-quality-r489.json; 缺 ⇒ 未判) ----
    qpath = os.path.join(HERE, "posthoc-quality-r489.json")
    if os.path.exists(qpath):
        q = json.load(io.open(qpath, encoding="utf-8-sig"))
        if force_degrade:
            for arm in q["arms"]:
                q["arms"][arm]["template_chars_ok"] = False
            out["negative_controls"].append({"id": "NC2-degrade", "applied": True,
                                             "note": "注入 template_chars_ok=False ⇒ H3 必翻红"})
        bad = {a: d["verdict"] for a, d in q["arms"].items() if d["verdict"] != "PASS"}
        src_ok = all(c["ok"] for c in q["template_source_checks"])
        out["quality"] = {"source_checks": q["template_source_checks"],
                          "arms": {a: {"skip_rows": d["skip_rows"], "template_replies": d["template_replies"],
                                       "repeat_verbatim_replies": d["repeat_verbatim_replies"],
                                       "skip_basis_hist": d["skip_basis_hist"], "verdict": d["verdict"]}
                                   for a, d in q["arms"].items()}}
        out["assertions"].append({"id": "H3", "desc": "质量面(类别感知): 每臂非法模板 0/12 且 template 绑定源码字符数",
                                  "ok": (not bad) and src_ok, "detail": f"非法臂={bad} 源码检查={[c['ok'] for c in q['template_source_checks']]}"})
        tmpl_ok = all(q["arms"][a]["template_replies"] == ACK_TURNS_IN_GRID for a in ("B", "R1", "R2", "R3"))
        out["assertions"].append({"id": "H5", "desc": f"文案裁决可机检: template 轮数 == 确认类轮数 ({ACK_TURNS_IN_GRID}) 且常量单源",
                                  "ok": tmpl_ok,
                                  "detail": {a: q["arms"][a]["template_replies"] for a in q["arms"]}})
    else:
        out["assertions"].append({"id": "H3", "desc": "质量面", "ok": None, "detail": "缺 posthoc-quality-r489.json"})
        out["assertions"].append({"id": "H5", "desc": "文案裁决", "ok": None, "detail": "缺输入"})

    # ---- H4 调用面 ----
    calls = [A[k]["calls"] for k in ("R1", "R2", "R3")]
    ok4 = all(c <= b["calls"] for c in calls) and (max(calls) - min(calls) <= 2)
    out["assertions"].append({"id": "H4", "desc": "调用面一致: 每 R_i.calls ≤ B.calls 且 max−min ≤ 2",
                              "ok": ok4, "detail": f"B={b['calls']} R={calls}"})

    out["all_ok"] = all(a["ok"] for a in out["assertions"] if a["ok"] is not None)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print("[written]", p, file=sys.stderr)
    sys.exit(0 if out["all_ok"] else 1)


if __name__ == "__main__":
    main()
