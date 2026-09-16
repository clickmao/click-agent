#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R492 · 付费量口径审计 v2: 中继真值 vs 宿主打点 (通用代码逻辑, 语言无关)

v2 修正 (v1 的错):
  v1 只按 point=='llm_call' 收集宿主行 ⇒ 把「截断续调用」误判成「漏记」。
  实况: 续调用记在 point=='llm_call_continue' (无 request_id, 且**不带** prompt/completion token 字段);
       空正文轮另有一条 point=='llm_call_empty_body' **同 request_id 的重复行** ⇒ 不去重会多算调用数。

口径 (fail-closed):
  - 付费量分母 = 中继真值 (usage 行 status==200)。
  - 宿主「调用数」= 去重后的 request_id 集合 ∪ {每个 llm_call_continue 行计 1 次}。
  - 宿主「token 汇总」只作第二列, 并显式报告覆盖不全的量 (不得用宿主行汇总替代中继真值)。
  - 反向差 (宿主 > 中继) 判红。

用法:
  python3 host_log_audit.py                    # 审计
  python3 host_log_audit.py --no-dedupe        # 负控1: 不去重 ⇒ 必报 host>relay
  python3 host_log_audit.py --ignore-continue  # 负控2: 忽略续调用点 ⇒ 必报 gap>=1
  python3 host_log_audit.py --drop-host-row    # 负控3: 人为删一行 ⇒ 必报 gap+1
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ROVER = os.path.join(ROOT, "eval", "rover")

CALL_POINTS = {"llm_call", "llm_call_empty_body"}
CONTINUE_POINT = "llm_call_continue"


def jl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in io.open(path, encoding="utf-8-sig") if l.strip()]


def discover():
    arms = {}
    if not os.path.isdir(ROVER):
        return arms
    for d in sorted(os.listdir(ROVER)):
        dpath = os.path.join(ROVER, d)
        if not os.path.isdir(dpath):
            continue
        for fn in sorted(os.listdir(dpath)):
            if not (fn.startswith("calls-") and fn.endswith(".jsonl")):
                continue
            arm = fn[len("calls-"):-len(".jsonl")]
            usage = os.path.join(dpath, f"usage-{arm}.jsonl")
            tel = os.path.join(dpath, f"tel-{arm}", "host.jsonl")
            if not os.path.exists(tel):
                tel = os.path.join(dpath, "tel", f"{arm}.jsonl")
            if os.path.exists(usage) and os.path.exists(tel):
                arms[f"{d}/{arm}"] = {"round": d, "arm": arm, "calls": os.path.join(dpath, fn),
                                      "usage": usage, "tel": tel}
    return arms


def paid_rows(usage):
    out = []
    for r in usage:
        if r.get("status", 200) == 200 and r.get("prompt_tokens") is not None:
            out.append(r)
    return out


def host_sets(tel, dedupe=True, use_continue=True, drop_last=False):
    """返回 (n_host_calls, n_id_groups, n_continue, n_dup, host_token_total)

    去重规则: 同一 request_id 只计一次调用; 若同 rid 有多行, token 取**带 token 字段**的那行
    (空正文诊断行 llm_call_empty_body 与 llm_call 同 rid 且不带 token ⇒ 不去重会多算调用, 盲取首行会少算 token)。
    旧格式 (无 request_id) 无法去重 ⇒ 每行即一次调用, 并单列 anonymous_rows。
    续调用点 llm_call_continue 无 rid: 每行计 1 次调用, token 只含 retry completion (其 prompt 量未落)。
    """
    rows = [r for r in tel if r.get("point") in CALL_POINTS | {CONTINUE_POINT}]
    if drop_last and rows:
        rows = rows[:-1]
    groups, n_cont, cont_tok, dup, anon = {}, 0, 0, 0, 0
    for r in rows:
        pt, kv = r.get("point"), (r.get("kv") or {})
        if pt == CONTINUE_POINT:
            if use_continue:
                n_cont += 1
                cont_tok += int(kv.get("retry_completion_tokens") or 0) if kv.get("retry_completion_tokens") is not None else 0
            continue
        ptok, ctok = kv.get("prompt_tokens"), kv.get("completion_tokens")
        tok = (int(ptok) + int(ctok)) if ptok is not None else None
        rid = kv.get("request_id")
        if rid is None:
            anon += 1
            groups[f"_anon{anon}"] = tok
            continue
        if rid in groups:
            dup += 1
            if groups[rid] is None and tok is not None:
                groups[rid] = tok                      # 补回被空正文行挡掉的 token
            if not dedupe:
                groups[f"_{rid}#{dup}"] = tok
            continue
        groups[rid] = tok
    host_tok = sum(t for t in groups.values() if t) + cont_tok
    return len(groups) + n_cont, len(groups), n_cont, dup, host_tok, anon


def audit(dedupe=True, use_continue=True, drop_last=False, nc=None):
    arms = discover()
    rep = {"round": "R492", "kind": "host_log_gap_audit_v2", "nc": nc or "none", "arms": {}}
    for name, a in arms.items():
        paid = paid_rows(jl(a["usage"]))
        ids, n_groups, n_cont, dup, host_tok, anon = host_sets(jl(a["tel"]), dedupe, use_continue, drop_last)
        n_host_calls = ids
        relay_tok = sum(int(p["prompt_tokens"]) + int(p["completion_tokens"]) for p in paid)
        entry = {
            "round_dir": a["round"],
            "relay_paid_calls": len(paid),
            "host_calls_dedup": n_host_calls,
            "host_id_rows": n_groups, "host_continue_rows": n_cont, "host_dup_rows_collapsed": dup,
            "host_anonymous_rows": anon,
            "gap_calls": len(paid) - n_host_calls,
            "relay_total_tokens": relay_tok,
            "host_token_field_total": host_tok,
            "host_token_field_missing": relay_tok - host_tok,
            "verdict": ("RED_host_exceeds_relay" if n_host_calls > len(paid) else
                        ("GAP" if n_host_calls < len(paid) else "OK")),
        }
        entry["token_missing_pct"] = round(100.0 * entry["host_token_field_missing"] / max(1, relay_tok), 2)
        rep["arms"][name] = entry

    # 口径影响量: 基线臂 vs 最快 T 臂, 用「宿主 token 字段口径」当分母会偏移多少
    impacts = []
    by_round = {}
    for name, e in rep["arms"].items():
        by_round.setdefault(e["round_dir"], []).append((name, e))
    for rd, lst in by_round.items():
        base = [x for x in lst if "role" in x[0].lower() or x[0].endswith("/B")]
        cands = [x for x in lst if x not in base]
        if not base or not cands:
            continue
        bn, be = base[0]
        tn, te = min(cands, key=lambda x: x[1]["relay_total_tokens"])
        if be["host_token_field_missing"] == 0:
            continue
        d_truth = 1.0 - te["relay_total_tokens"] / be["relay_total_tokens"]
        d_hostonly = 1.0 - te["relay_total_tokens"] / max(1, be["host_token_field_total"])
        impacts.append({"round_dir": rd, "baseline": bn, "best_arm": tn,
                        "delta_relay_truth": round(d_truth, 4),
                        "delta_if_host_token_rows_used": round(d_hostonly, 4),
                        "bias_pp": round((d_hostonly - d_truth) * 100, 2),
                        "direction": "宿主口径低估降幅" if d_hostonly < d_truth else "宿主口径高估降幅"})
    rep["caliber_impact"] = impacts

    # 判据
    vals = list(rep["arms"].values())
    rep["judgement"] = {
        "H1_host_calls_match_relay": all(e["gap_calls"] == 0 for e in vals),
        "H2_no_host_exceeds_relay": not any(e["verdict"] == "RED_host_exceeds_relay" for e in vals),
        "H3_token_field_coverage_full": all(e["host_token_field_missing"] == 0 for e in vals),
        "H4_dedupe_required_nonzero": any(e["host_dup_rows_collapsed"] > 0 for e in vals),
    }
    return rep


def main():
    a = sys.argv[1:]
    nc = None
    kw = {}
    if "--no-dedupe" in a:
        kw["dedupe"] = False; nc = "no-dedupe"
    if "--ignore-continue" in a:
        kw["use_continue"] = False; nc = "ignore-continue"
    if "--drop-host-row" in a:
        kw["drop_last"] = True; nc = "drop-host-row"
    rep = audit(nc=nc, **kw)
    print(json.dumps(rep["judgement"], ensure_ascii=False))
    for n, e in rep["arms"].items():
        print(f"{n:20s} relay={e['relay_paid_calls']:2d} host={e['host_calls_dedup']:2d} "
              f"gap={e['gap_calls']:+d} dup={e['host_dup_rows_collapsed']} cont={e['host_continue_rows']} "
              f"tok_relay={e['relay_total_tokens']:6d} tok_host={e['host_token_field_total']:6d} "
              f"missing={e['host_token_field_missing']:5d} ({e['token_missing_pct']:5.2f}%) {e['verdict']}")
    for i in rep["caliber_impact"]:
        print(f"[impact] {i['round_dir']} {i['baseline']}→{i['best_arm']}: 中继真值 {i['delta_relay_truth']:.4f} "
              f"vs 宿主 token 字段口径 {i['delta_if_host_token_rows_used']:.4f} ⇒ 偏 {i['bias_pp']:+.2f} pp ({i['direction']})")
    if nc is None:
        out = os.path.join(HERE, "host_log_audit.json")
        io.open(out, "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
        print(f"[write] {out}")
        return 0
    red = any(e["verdict"] != "OK" for e in rep["arms"].values())
    print(f"[NC:{nc}] detected_inconsistency={red}")
    return 0 if red else 2


if __name__ == "__main__":
    sys.exit(main())
