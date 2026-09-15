#!/usr/bin/env python3
"""R452 分析器 — 三臂(产品原生)读数汇总 + 预注册判据 P1–P4 机检。

输入: verdict-<arm>-<GRID><NS>.json (settle 产出) + calls-<arm>-<GRID><NS>.jsonl (桩逐请求)
      + grid/meta.json (轮标签/长度) + grid/task-<GRID>.json (轮文本)
输出: summary-r452.json + 文本摘要(落 stdout)

口径铁律:
  * 判官真值只取**产品自身遥测**(local_turn_gate 记录) —— 零重建路线下不存在失配的中间环节;
  * 吞并轮(actual=consumed, 0 远端调用) 单独计, 不得混入门增益;
  * 未测到/缺字段 ⇒ n/a, 不记 0。
"""
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
DIR = ROOT / "eval/rover/r452"
ARMS = [("RC", "M20", "-c1"), ("RP", "REAL", "-p1"), ("RJ", "REAL", "-j1")]


def load(p, default=None):
    p = pathlib.Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def rows(p):
    p = pathlib.Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8-sig", errors="replace").splitlines() if l.strip()]


def arm_stats(arm, grid, ns):
    v = load(DIR / f"verdict-{arm}-{grid}{ns}.json")
    if not v:
        return {"arm": arm, "status": "verdict 缺失"}
    st = rows(DIR / f"calls-{arm}-{grid}{ns}.jsonl")
    per = v.get("per_turn") or []
    actual = Counter(str(q.get("actual")) for q in per)
    r1 = v.get("r1_records") or []
    recs = v.get("gate_records") or []
    return {
        "arm": arm, "grid": grid, "ns": ns, "status": "ok",
        "turns_total": len(per), "turns_actual": dict(actual),
        "tokens_total": v.get("tokens_total"), "G_tokens": v.get("G_tokens"), "J_tokens": v.get("J_tokens"),
        "gate_events": len(recs), "gate_r1_n": v.get("gate_r1_n"), "gate_mech_n": v.get("gate_mech_n"),
        "gate_nonack_n": v.get("gate_nonack_n"), "gate_prefilter_violations": v.get("gate_prefilter_violations"),
        "gate_prefilter_flag": v.get("gate_prefilter_flag"),
        "gate_truth_prompt": v.get("gate_truth_prompt"), "gate_truth_gen": v.get("gate_truth_gen"),
        "r1_decided": dict(Counter(str(r.get("decided")) for r in r1)),
        "r1_verdict": dict(Counter(str(r.get("verdict")) for r in r1)),
        "r1_basis": dict(Counter(str(r.get("basis")).split(":")[0] for r in r1)),
        "r1_prompt_len": [r.get("gate_prompt_len") for r in r1],
        "r1_gen_tokens": [r.get("gen_tokens") for r in r1],
        "r1_errors": [r.get("error") for r in r1 if r.get("error")],
        "judge_source_count": v.get("judge_source_count"),
        "cross_check_S2": v.get("cross_check_S2"),
        "stub_calls": len(st),
        "stub_match_turns": [x.get("match_turn") for x in st],
        "stub_align_gap": dict(Counter(str(x.get("align_gap")) for x in st)),
        "stub_used": dict(Counter(str(x.get("used")) for x in st)),
        "per_turn": per,
    }


def main():
    out = {"round": "R452", "arms": {}}
    meta = load(DIR / "grid/meta.json") or {}
    for arm, grid, ns in ARMS:
        out["arms"][arm] = arm_stats(arm, grid, ns)

    rp, rj, rc = (out["arms"][k] for k in ("RP", "RJ", "RC"))

    # P1: 真实流量生产行为 ⇒ r1=0 且 skip=0
    if rp.get("status") == "ok":
        sk = (rp["turns_actual"].get("skip") or 0)
        out["P1_real_traffic_no_skip"] = {
            "gate_r1_n": rp["gate_r1_n"], "mech_n": rp["gate_mech_n"], "nonack_n": rp["gate_nonack_n"],
            "drive_skip": sk, "drive_consumed": rp["turns_actual"].get("consumed") or 0,
            "verdict": "PASS" if (rp["gate_r1_n"] == 0 and sk == 0) else "FAIL(一等发现)",
        }
    # P3: 桩对齐
    for k in out["arms"]:
        a = out["arms"][k]
        if a.get("status") == "ok":
            gaps = {int(g) for g in a["stub_align_gap"] if str(g).lstrip("-").isdigit()} if a["stub_align_gap"] else set()
            a["align_ok"] = bool(gaps) and max(gaps) <= 1 and (a["stub_used"].get("default", 0) == 0 or k == "RC")
    # P2: RJ 判官 S 票 × 真实消息规则标签 —— 用**产品自落盘的门判 prompt**（dump）对齐, 不用下标硬取
    if rj.get("status") == "ok":
        turns = load(DIR / "grid/task-REAL.json", {}).get("turns") or []
        mt = (meta.get("turns") or [])
        vm = load(DIR / "verdict-RJ-REAL-j1.json") or {}
        dump = rows(DIR / "dump-RJ-REAL-j1.jsonl")

        def msg_of(p):
            i = p.find("【用户消息】")
            j = p.rfind("答案:")
            return p[i + len("【用户消息】"):j].strip() if i >= 0 and j > i else ""

        pairs, unmapped = [], 0
        for k, x in enumerate(dump, 1):
            m = msg_of(x.get("prompt", ""))
            hit = [i for i in range(len(turns)) if m and m.startswith(turns[i][:64])]
            g = mt[hit[0]] if hit and hit[0] < len(mt) else {}
            if not hit:
                unmapped += 1
            pairs.append({"call": k, "prompt_len": x.get("len"), "msg_len": len(m), "msg_head": m[:40],
                          "turn": (hit[0] + 1) if hit else None,
                          "rule_label": g.get("rule_label"), "measured": g.get("measured")})
        cross = {}
        for p in pairs:
            cross.setdefault(str(p["rule_label"]), Counter())[p["msg_head"]] += 1
        out["P2_judge_on_real_pairs"] = {
            "note": "判官 prompt 为 S/P 二字母; 落到 r1 记录的一律是 S(被机械认可族守卫否决 ⇒ skip_rejected_nonack)",
            "n_dump_calls": len(dump), "n_r1_gate_records": rj.get("gate_r1_n"),
            "n_turns": len(turns), "unmapped": unmapped,
            "s_votes_by_rule_label": {k: sum(v.values()) for k, v in cross.items()},
            "distinct_msgs": {k: dict(v) for k, v in cross.items()},
            "gate_coverage": {"gate_events": rj.get("gate_events"), "turns_total": rj.get("turns_total")},
            "pairs": pairs,
        }

    (DIR / "summary-r452.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, a in out["arms"].items():
        if a.get("status") != "ok":
            print(f"[{k}] {a['status']}")
            continue
        print(f"[{k}] turns={a['turns_total']} actual={a['turns_actual']} r1={a['gate_r1_n']} mech={a['gate_mech_n']} "
              f"nonack={a['gate_nonack_n']} tok={a['tokens_total']} (G={a['G_tokens']} J={a['J_tokens']}) "
              f"decided={a['r1_decided']} align={a.get('align_ok')} gap={a['stub_align_gap']} used={a['stub_used']}")
    for key in ("P1_real_traffic_no_skip", "P2_judge_on_real_pairs"):
        if key in out:
            print(key, "=", json.dumps({k: v for k, v in out[key].items() if k != "pairs"}, ensure_ascii=False))
    print("→ summary-r452.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
