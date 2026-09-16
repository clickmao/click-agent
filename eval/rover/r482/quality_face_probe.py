#!/usr/bin/env python3
"""R482-Q: R482 真机双臂的『常量兜底』归属与质量面量化 (只读既有产物, 不重跑真链)。

语言无关: 不依赖被分析语料的文件后缀/语言; 常量由源码正则派生 (取不到 ⇒ rc=3 弃权)。
三态: rc=0 测量完成 (判定如实输出) / rc=2 内部一致性断言失败 (fail-closed) / rc=3 缺输入或常量派生失败 (弃权)。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R482 = ROOT / "eval" / "rover" / "r482"
PREREG = R482 / "prereg_quality_face.json"
CONST_SRC = ROOT / "src" / "agent.modelqueue" / "ModelQueueRouter.cs"
CONST_FIELD = "LocalSkipFallback"
OUT = R482 / "quality-face.json"


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def load_multi_json(p: Path):
    """容忍: 单行 JSONL 与 逐对象 pretty-print 两种形态。"""
    txt = p.read_text(encoding="utf-8-sig")
    dec = json.JSONDecoder()
    out, i = [], 0
    while True:
        j = txt.find("{", i)
        if j < 0:
            break
        obj, k = dec.raw_decode(txt, j)
        out.append(obj)
        i = k
    return out


def derive_const(force_miss: bool) -> str:
    if force_miss:
        return ""
    if not CONST_SRC.is_file():
        return ""
    m = re.search(rf'{CONST_FIELD}\s*=\s*"([^"]*)"', CONST_SRC.read_text(encoding="utf-8-sig"))
    return m.group(1) if m else ""


def load_usage(p: Path):
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    return rows


def load_turns(p: Path):
    docs = load_multi_json(p)
    if not docs or "turns" not in docs[0]:
        return None
    return docs[0]


def attribute(calls, turns):
    """按 ts ∈ [t_start, t_end] 归属; 落不进区间的调用单列。"""
    per = {t["turn"]: [] for t in turns}
    unattributed = []
    for c in calls:
        ts = c.get("ts")
        hit = None
        for t in turns:
            lo, hi = t.get("t_start"), t.get("t_end")
            if lo is None or hi is None or ts is None:
                continue
            if lo <= ts <= hi:
                hit = t["turn"]
                break
        if hit is None:
            unattributed.append(c.get("seq"))
        else:
            per[hit].append(c)
    return per, unattributed


def totals(calls):
    return sum(int(c["usage"]["total_tokens"]) for c in calls)


def repeat_groups(turns):
    groups = {}
    for t in turns:
        groups.setdefault((t.get("reply") or "").encode(), []).append(t["turn"])
    return {k: v for k, v in groups.items() if len(v) >= 2}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-miss", action="store_true", help="负控 NC2: 常量派生失败路径")
    ap.add_argument("--swap", action="store_true", help="负控 NC1: 交换两臂")
    a = ap.parse_args(argv)

    if not PREREG.is_file():
        print("MISS prereg:", PREREG)
        return 3
    const = derive_const(a.force_miss)
    if not const:
        print("MISS: 常量派生失败 (", CONST_SRC, "/", CONST_FIELD, ") ⇒ 弃权 rc=3")
        return 3

    arm_A, arm_R = ("R", "Arole") if a.swap else ("Arole", "R")
    usage = {x: R482 / f"usage-{x}.jsonl" for x in ("Arole", "R")}
    turns_f = {x: R482 / f"turns-{x}.jsonl" for x in ("Arole", "R")}
    for p in list(usage.values()) + list(turns_f.values()):
        if not p.is_file():
            print("MISS:", p)
            return 3

    cu = {x: load_usage(usage[x]) for x in usage}
    ct = {x: load_turns(turns_f[x]) for x in turns_f}
    if any(v is None for v in ct.values()):
        print("MISS: turns 结构异常")
        return 3

    ta, tr = totals(cu[arm_A]), totals(cu[arm_R])
    att = {x: attribute(cu[x], ct[x]["turns"]) for x in cu}

    # 常量兜底轮 (逐臂: 答复 == 常量)
    const_turns = {x: [t["turn"] for t in ct[x]["turns"] if (t.get("reply") or "") == const] for x in ct}
    const_set = set(const_turns[arm_R])
    cost_A = {t["turn"]: totals(att[arm_A][0].get(t["turn"], [])) for t in ct[arm_A]["turns"]}
    a_mean = ta / len(cu[arm_A]) if cu[arm_A] else 0.0
    missing = [t for t in const_turns[arm_R] if cost_A.get(t, 0) == 0]
    add = sum(cost_A.get(t, 0) for t in const_turns[arm_R]) + a_mean * len(missing)
    r_cf = tr + add
    base_delta = (ta - tr) / ta
    cf_delta = (ta - r_cf) / ta

    groups = repeat_groups(ct[arm_R]["turns"])
    distinct_R = len({(t.get("reply") or "").encode() for t in ct[arm_R]["turns"]})
    distinct_A = len({(t.get("reply") or "").encode() for t in ct[arm_A]["turns"]})

    # 内部一致性断言 (fail-closed): 分臂调用数须等于记录数; 归属不得丢调用
    for x in cu:
        if len(att[x][1]) != 0:
            print("ASSERT: 存在未归属调用", x, att[x][1])
            return 2
    if a.swap:
        print("NC1 swap: base_delta=%.4f cf_delta=%.4f (符号应翻转)" % (base_delta, cf_delta))
        return 0

    res = {
        "round": "R482-Q",
        "inputs": {str(p.relative_to(ROOT)): sha16(p) for p in list(usage.values()) + list(turns_f.values()) + [PREREG, CONST_SRC]},
        "const": {"source": str(CONST_SRC.relative_to(ROOT)), "field": CONST_FIELD, "value": const, "sha16": sha16(CONST_SRC)},
        "calls": {"Arole": len(cu["Arole"]), "R": len(cu["R"])},
        "total_tokens": {"Arole": ta, "R": tr},
        "base_delta_pct": round(base_delta * 100, 4),
        "per_turn": {
            x: [{"turn": t["turn"], "calls": len(att[x][0][t["turn"]]), "tok": totals(att[x][0][t["turn"]]),
                 "reply_bytes": len((t.get("reply") or "").encode())} for t in ct[x]["turns"]]
            for x in ("Arole", "R")
        },
        "const_fallback_turns_R": const_turns[arm_R],
        "const_cost_proxy_A": {str(t): cost_A.get(t, 0) for t in const_turns[arm_R]},
        "R_counterfactual_no_const": r_cf,
        "cf_delta_pct": round(cf_delta * 100, 4),
        "reply_repetition_R": {"distinct": distinct_R, "total_turns": len(ct["R"]["turns"]),
                               "identical_groups": {str(k[:24], "utf-8", "replace"): v for k, v in groups.items()}},
        "reply_repetition_Arole": {"distinct": distinct_A, "total_turns": len(ct["Arole"]["turns"])},
        "verdict": {
            "base_kpi_reproduced": f"{(ta - tr) / ta * 100:.2f}% (报告 32.21%)",
            "cf_kpi_no_const": f"{cf_delta * 100:.2f}%",
            "cf_below_30": bool(cf_delta < 0.30),
            "const_turns": len(const_turns[arm_R]),
            "assumption": "R 臂常量轮若真答 ⇒ 成本≈A 臂同轮 (代理假设, 非实测)",
        },
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(res["verdict"], ensure_ascii=False, indent=1))
    print("calls", res["calls"], "totals", res["total_tokens"], "base%", res["base_delta_pct"], "cf%", res["cf_delta_pct"])
    print("per_turn_R", json.dumps(res["per_turn"]["R"]))
    print("per_turn_A", json.dumps(res["per_turn"]["Arole"]))
    print("const_turns_R", const_turns[arm_R], "proxy", res["const_cost_proxy_A"])
    print("repetition R", distinct_R, "distinct /", len(ct["R"]["turns"]), "groups", {k[:12]: v for k, v in ((g[:24].decode('utf-8', 'replace'), vv) for g, vv in groups.items())})
    print("out", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
