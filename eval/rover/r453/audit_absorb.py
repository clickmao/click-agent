#!/usr/bin/env python3
"""R453 审计器 — 真实分布上唯一有量级的省远端调用通道（「吞并轮」）的读数与缺陷形态。

背景（R452 实测）: 真实 51 轮里 7 轮（13.7%）**远端调用 = 0**，其回复文本含
`续跑计划` / `等你回答`（settle 的 ASK_MARK）⇒ 产品把该轮**吸收**进既有计划，未发远端请求。

本器只做**可机检的形态分类与计数**，不做质量裁决：
  * 形状: param_slot_fill（`答复落到参数槽`）/ clarify_ask（`等你回答`）
  * 信号: 消息长度、是否驱动类短语、下一轮是否**重复同一条消息**（用户被迫重发）、
          下一轮是否含抱怨词（"啥也没有/没有/为什么没"）
  * 台账: 省下的远端调用数 × 本 run 实测均值 ⇒ 省 token 估计（区间口径标注）

口径纪律: 证据全部来自产品自身落盘（turns-/verdict-/stub calls-），不重建 prompt。
"""
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
R452 = ROOT / "eval/rover/r452"
OUT = ROOT / "eval/rover/r453"

ASK_MARK = ("续跑计划", "没有落地", "等你回答")
SLOT_MARK = "答复落到参数槽"
ASK_MARK_Q = "等你回答"
DRIVER_RE = ("继续", "好的", "收到", "嗯", "ok", "OK")
COMPLAIN = ("啥也没有", "没有", "为什么没", "为何没", "怎么没", "没看到", "不对")


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


def overlap(a, b):
    """字符 3-gram Jaccard —— 判定「下一轮是否重复同一条消息」。"""
    ga = {a[i:i + 3] for i in range(max(1, len(a) - 2))}
    gb = {b[i:i + 3] for i in range(max(1, len(b) - 2))}
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def kpi_channels(per, turns, mt):
    """真实分布上的 token 通道台账（全部取自 R452 产品自身遥测 / 已收口读数）。"""
    rp = load(R452 / "verdict-RP-REAL-p1.json", {})
    rj = load(R452 / "verdict-RJ-REAL-j1.json", {})
    r1 = rj.get("r1_records") or []
    r1_tok = sum(int(r.get("tokens_evaluated") or 0) + int(r.get("gen_tokens") or 0) for r in r1)
    return {
        "remote_api": {"calls": sum(int(q['G_calls']) for q in per),
                       "tokens": sum(int(q['G_tokens']) for q in per)},
        "local_r1_gate": {"calls_production": int(rp.get("gate_r1_n") or 0),
                          "calls_if_prefilter_off": int(rj.get("gate_r1_n") or 0),
                          "calls_if_prefilter_off_tokens": r1_tok,
                          "note": "前置门(机械认可族)把 ¬Ack 挡在 r1 之前 ⇒ 真实轮省下的本地 r1 调用"},
        "skip_channel": {"skips_production": int(rp.get("skips") or 0),
                         "skips_judge_forced": int(rj.get("skips") or 0),
                         "judge_S_votes_vetoed": len([r for r in r1 if "skip_rejected" in str(r.get("basis"))]),
                         "note": "真实流量可跳面 = 0（三臂独立佐证）"},
        "absorb_channel": {"turns": len([q for q in per if any(m in str(q.get("reply_head") or "") for m in ASK_MARK)]),
                           "remote_calls_saved": len([q for q in per if any(m in str(q.get("reply_head") or "") for m in ASK_MARK)]),
                           "note": "真实分布上唯一有量级的省远端调用通道（与门无关）"},
        "prefix_cache": {"claim": "K2b 命中 ≥97%（R4xx 已收口, 非本轮实测）", "billed_note": "计费口径的降幅主项; 本轮未重测"},
    }


def main():
    v = load(R452 / "verdict-RP-REAL-p1.json")
    if not v:
        print("[致命] 缺 verdict-RP-REAL-p1.json（R452 产物）")
        return 3
    turns = load(R452 / "grid/task-REAL.json", {}).get("turns") or []
    mt = load(R452 / "grid/meta.json", {}).get("turns") or []
    per = v["per_turn"]
    calls = rows(R452 / "calls-RP-REAL-p1.jsonl")

    n_turns = len(per)
    absorbed = [q for q in per if any(m in str(q.get("reply_head") or "") for m in ASK_MARK)]
    g_zero = [q for q in per if int(q.get("G_calls") or 0) == 0]
    # 机检: 吸收轮必须 G_calls==0（否则「吸收」定义被破坏）
    absorbed_viol = [q["turn"] for q in absorbed if int(q.get("G_calls") or 0) != 0]
    gz_extra = [q["turn"] for q in g_zero if q not in absorbed]

    items = []
    for q in absorbed:
        t = int(q["turn"])
        n = t - 1
        msg = turns[n] if n < len(turns) else ""
        rep = str(q.get("reply_head") or "")
        nxt = turns[t] if t < len(turns) else ""
        shape = "param_slot_fill" if SLOT_MARK in rep else ("clarify_ask" if ASK_MARK_Q in rep else "other")
        items.append({
            "turn": t, "shape": shape,
            "session": (mt[n].get("session") if n < len(mt) else None),
            "rule_label": (mt[n].get("rule_label") if n < len(mt) else None),
            "msg_len": len(msg), "msg_head": msg[:60],
            "reply_head": rep[:90],
            "G_calls": int(q.get("G_calls") or 0), "G_tokens": int(q.get("G_tokens") or 0),
            "next_msg_overlap": round(overlap(msg, nxt), 3), "next_msg_head": nxt[:40],
            "next_is_repeat": bool(msg and nxt and (nxt == msg or overlap(msg, nxt) >= 0.8)),
            "next_has_complaint": bool(nxt and any(c in nxt for c in COMPLAIN)),
            "driver_head": bool(msg and any(msg.strip().startswith(d) for d in DRIVER_RE)),
        })

    # 远端调用均价（本 run 实测; 只用于**估计**省下量, 不当作真值）
    g_turns = [q for q in per if int(q.get("G_calls") or 0) > 0]
    g_calls = sum(int(q["G_calls"]) for q in g_turns)
    g_tokens = sum(int(q["G_tokens"]) for q in g_turns)
    avg = (g_tokens / g_calls) if g_calls else None
    saved_est = (avg * len(absorbed)) if avg else None

    out = {
        "round": "R453",
        "source": "R452 RP 臂（真实 51 轮·生产配置·产品自身遥测）",
        "channel": "吞并轮（产品吸收该轮进既有计划 ⇒ 远端调用 0）",
        "kpi_channels": kpi_channels(per, turns, mt),
        "counts": {
            "turns_total": n_turns,
            "absorbed_n": len(absorbed), "absorbed_rate": round(len(absorbed) / n_turns, 4),
            "g_zero_n": len(g_zero),
            "absorbed_with_G_calls_violation": absorbed_viol,
            "g_zero_not_marked_absorbed": gz_extra,
            "shapes": dict(Counter(i["shape"] for i in items)),
            "remote_calls": g_calls, "remote_tokens": g_tokens,
            "avg_remote_tokens_per_call": round(avg, 1) if avg else None,
            "saved_remote_tokens_est": round(saved_est, 1) if saved_est else None,
            "saved_rate_vs_remote_total": round(saved_est / g_tokens, 4) if saved_est else None,
        },
        "defect_signals": {
            "next_is_repeat": [i["turn"] for i in items if i["next_is_repeat"]],
            "next_has_complaint": [i["turn"] for i in items if i["next_has_complaint"]],
            "driver_head_absorbed": [i["turn"] for i in items if i["driver_head"]],
            "long_msg_absorbed": [i["turn"] for i in items if i["msg_len"] > 200],
        },
        "items": items,
        "scope_note": ("只做形态与计数; **不作质量裁决**（「吸收是否误吞用户诉求」需独立预注册轮次, "
                       "因本轮桩回复非真回复, 参数槽语义不可判）"),
    }
    checks = {
        "P1_absorbed_implies_no_remote_call": {"pass": absorbed_viol == [], "detail": absorbed_viol},
        "P2_absorbed_subset_of_g_zero": {"pass": all(q["turn"] in [x["turn"] for x in g_zero] for q in absorbed)},
        "P3_saved_upper_bound_16pct": {"pass": (saved_est / g_tokens) <= 0.16 if (saved_est and g_tokens) else False},
        "P4_no_quality_claim": {"pass": True, "detail": "quality_claim=false（桩回复非真回复 ⇒ 参数槽语义不可判）"},
    }
    out["checks"] = checks
    out["quality_claim"] = False
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verdict-r453.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "ledger-r453.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    c = out["counts"]
    print(f"吞并轮 {c['absorbed_n']}/{c['turns_total']} = {c['absorbed_rate']:.1%} | 形状 {c['shapes']} | "
          f"G=0 轮 {c['g_zero_n']} | 违规 {c['absorbed_with_G_calls_violation']}")
    print(f"远端 {c['remote_calls']} 调用 / {c['remote_tokens']} tok | 均价 {c['avg_remote_tokens_per_call']} | "
          f"省估计 {c['saved_remote_tokens_est']} tok = {c['saved_rate_vs_remote_total']:.1%}")
    print("缺陷信号:", json.dumps(out["defect_signals"], ensure_ascii=False))
    print("判据:", json.dumps({k: v["pass"] for k, v in checks.items()}, ensure_ascii=False))
    bad = [k for k, v in checks.items() if not v["pass"]]
    if bad:
        print("[fail-closed] 违例:", bad)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
