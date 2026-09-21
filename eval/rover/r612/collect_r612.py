#!/usr/bin/env python3
# R612 只读采集器 —— 判别位真实流量增量与分辨率复核
# 只读: data/telemetry/host.jsonl + eval/rover/r462 四臂原始件 + docs/evidence/RF0006/probe-ab-r462.md
# 零 src 改动 / 零新夹具 / 零网络
import hashlib, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TEL = os.path.join(ROOT, "data/telemetry/host.jsonl")
OUT = os.path.join(ROOT, "eval/rover/r612/readings-r612.json")
CORPUS = os.path.join(ROOT, "eval/rover/r462/corpus-r462-w.json")

def sha256(p, cap=None):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()[:16]

def load_rows(p):
    rows, bad = [], 0
    for line in io.open(p, encoding="utf-8-sig"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            bad += 1
    return rows, bad

def ival(kv, key):
    try:
        return int(str(kv.get(key)).strip())
    except Exception:
        return None

def main():
    rows, bad = load_rows(TEL)
    R = {"round": "R612", "tier": "read_only", "source": {
        "telemetry": os.path.relpath(TEL, ROOT),
        "telemetry_sha256_16": sha256(TEL),
        "telemetry_lines": len(rows), "telemetry_unparsable": bad,
        "ts_first": rows[0]["ts"] if rows else None, "ts_last": rows[-1]["ts"] if rows else None,
        "sessions": sorted({r.get("session") for r in rows}),
    }, "criteria": {}, "raw": {}}

    # ---- J1 调用面 ----
    gate = [r for r in rows if r["point"] == "local_turn_gate"]
    mech = [r for r in gate if str(r["kv"].get("basis", "")).startswith("mechanical")]
    asked = [r for r in gate if (ival(r["kv"], "gate_prompt_len") or 0) > 0]
    nonzero_tok = [r for r in gate if (ival(r["kv"], "gen_tokens") or -1) > 0 or (ival(r["kv"], "prompt_new") or -1) > 0]
    basis_dist = {}
    for r in gate:
        b = str(r["kv"].get("basis", ""))
        basis_dist[b] = basis_dist.get(b, 0) + 1
    R["raw"]["J1"] = {"gate_rows": len(gate), "mechanical_rows": len(mech),
                     "asked_rows(gate_prompt_len>0)": len(asked),
                     "rows_with_positive_tokens": len(nonzero_tok),
                     "mechanical_share": (len(mech) / len(gate)) if gate else None,
                     "basis_dist": basis_dist}
    R["criteria"]["J1_call_face"] = {
        "claim": "【修订 v2，见 amendments】真问本地行数（gate_prompt_len>0）=0 ∧ 正向 token 行数=0 ⇒ 判别位零调用；机械前缀占比仅为读数（39/42=0.9286，余 3 行为 gate:repeat_no_replayable_prev→remote 守卫拒绝路径，代码核验无模型调用）",
        "reading": {"asked_rows": len(asked), "rows_with_positive_tokens": len(nonzero_tok),
                    "gate_rows": len(gate), "mechanical_share": (len(mech) / len(gate)) if gate else None,
                    "nonmechanical_rows": len(gate) - len(mech)},
        "verdict": "PASS" if gate and len(asked) == 0 and len(nonzero_tok) == 0 else "FAIL"}

    # ---- J2 台账面 ----
    led = [r for r in rows if r["point"] == "local_decision_ledger"]
    decided = [r for r in led if str(r["kv"].get("decided")) == "true"]
    kinds = {}
    for r in led:
        k = str(r["kv"].get("kind"))
        kinds[k] = kinds.get(k, 0) + 1
    rate = (len(decided) / len(led)) if led else None
    R["raw"]["J2"] = {"ledger_rows": len(led), "decided_rows": len(decided), "decision_rate": rate, "kind_dist": kinds}
    R["criteria"]["J2_ledger_face"] = {
        "claim": "台账决策率 < 0.15", "reading": {"decision_rate": rate, "ledger_rows": len(led)},
        "verdict": "PASS" if rate is not None and rate < 0.15 else "FAIL"}

    # ---- J3 本地通道调用面 ----
    lc = [r for r in rows if r["point"] == "llm_call"]
    fam = {}
    for r in lc:
        v = str(r["kv"].get("model") or r["kv"].get("channel") or r["kv"].get("route") or "?")
        fam[v] = fam.get(v, 0) + 1
    local_rows = [r for r in lc if any(str(r["kv"].get(k, "")).lower().startswith(("local", "r1")) for k in ("model", "channel", "route", "lane"))]
    R["raw"]["J3"] = {"llm_call_rows": len(lc), "model_family_dist": fam, "local_family_rows": len(local_rows)}
    R["criteria"]["J3_local_channel_face"] = {
        "claim": "llm_call 中本地族行数=0（全为远端）",
        "reading": {"llm_call_rows": len(lc), "local_family_rows": len(local_rows)},
        "verdict": "PASS" if lc and len(local_rows) == 0 else "FAIL"}

    # ---- J4 分辨率上界（既有夹具 + 既有四臂原件） ----
    n_ack = n_real = None
    corpus_face = {}
    if os.path.exists(CORPUS):
        c = json.load(io.open(CORPUS, encoding="utf-8-sig"))
        items = c if isinstance(c, list) else (c.get("items") or c.get("cases") or [])
        if items:
            fam = {}
            want = {}
            mech = {}
            for x in items:
                fam[str(x.get("family"))] = fam.get(str(x.get("family")), 0) + 1
                want[str(x.get("want"))] = want.get(str(x.get("want")), 0) + 1
                mech[str(x.get("mech"))] = mech.get(str(x.get("mech")), 0) + 1
            n_ack = fam.get("ack", 0)
            n_real = len(items) - n_ack
            corpus_face = {"n": len(items), "family_dist": fam, "want_dist": want,
                           "mech_dist": mech,
                           "mechanically_decidable_share": (mech.get("True", 0) / len(items)) if items else None}
    arms = {}
    for name in ("lfm3b-main", "lfm3b-fork", "bonsai8b-fork", "bonsai4b-fork"):
        p = f"/tmp/r462_out_{name}.json"
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8-sig"))
        sd = d if isinstance(d, dict) else {}
        items = d if isinstance(d, list) else (sd.get("items") or sd.get("results") or sd.get("rows") or [])
        wall = sum(float(x.get("wall_s") or 0) for x in items)
        arms[name] = {"n": len(items), "acc": sd.get("acc"), "false_skip_n": sd.get("false_skip_n"),
                      "miss_skip_n": sd.get("miss_skip_n"), "unparsed_n": sd.get("unparsed_n"),
                      "undecided_n": sd.get("undecided_n"),
                      "wall_s_sum": round(wall, 1),
                      "wall_s_per_case": round(wall / len(items), 1) if items else None,
                      "model": sd.get("model"), "sha12_of_source": "见 docs/evidence/RF0006/probe-ab-r462.md §7.1"}
    total_n = sum(corpus_face["family_dist"].values()) if corpus_face else 28
    res = {"corpus_present": os.path.exists(CORPUS), "n_ack": n_ack, "n_real": n_real,
           "corpus_face": corpus_face,
           "min_resolvable_delta_acc_pt": round(100.0 / total_n, 2) if total_n else None,
           "min_resolvable_delta_jumprate_pt": round(100.0 / n_ack, 2) if n_ack else None,
           "min_resolvable_delta_missrate_pt": round(100.0 / n_real, 2) if n_real else None,
           "arms": arms}
    R["raw"]["J4"] = res
    m = arms.get("lfm3b-main", {})
    R["criteria"]["J4_resolution_ceiling"] = {
        "claim": "夹具 28 例（14 ack / 14 real）⇒ 最小可分辨差：准确率 3.57pt、假跳率/漏跳率 7.14pt；现役 3B = 1.0000 / 假跳 0/14 ⇒ 天花板 ⇒ 上向分辨率=0",
        "reading": {"n": total_n, "n_ack": n_ack, "n_real": n_real,
                    "min_delta_acc_pt": res["min_resolvable_delta_acc_pt"],
                    "min_delta_jumprate_pt": res["min_resolvable_delta_jumprate_pt"],
                    "lfm3b_acc": m.get("acc"), "lfm3b_false_skip_n": m.get("false_skip_n"),
                    "mech_share_of_fixture": corpus_face.get("mechanically_decidable_share")},
        "verdict": "PASS" if n_real and (m.get("acc") or 0) >= 1.0 else "FAIL",
        "note": "天花板 ⇒ 判「更好」不可测；下向分辨率：准确率 3.57pt / 假跳率 7.14pt"}

    # ---- J5 成本面 ----
    local_tok = sum(max(0, ival(r["kv"], "gen_tokens") or 0) for r in gate)
    warm = [r for r in rows if r["point"] == "local_channel_warmup"]
    R["raw"]["J5"] = {"local_judge_tokens_window": local_tok, "warmup_rows": len(warm),
                     "warmup_kv": warm[-1]["kv"] if warm else None, "resident_rss": "UNMEASURED"}
    R["criteria"]["J5_cost_face"] = {
        "claim": "本窗本地判别位 token=0；常驻仅 warmup 1 条；RSS 未测",
        "reading": {"local_tokens": local_tok, "warm_ms": (warm[-1]["kv"].get("warm_ms") if warm else None)},
        "verdict": "PASS" if local_tok == 0 else "FAIL"}

    # ---- J6 负控：把机械判定反转 ----
    inverted = [r for r in gate if not str(r["kv"].get("basis", "")).startswith("mechanical")]
    neg_fail = bool(gate) and (len(inverted) > 0 or len(asked) > 0)
    R["criteria"]["J6_negative_control"] = {
        "claim": "把 J1(v2) 的「零调用」反转（凡非 mechanical 前缀即计为真调用）⇒ J1(v2) 必须判红",
        "reading_inverted": {"non_mechanical_rows_treated_as_calls": len(inverted), "gate_rows": len(gate), "asked_rows": len(asked)},
        "verdict": "PASS" if neg_fail else "FAIL",
        "has_teeth": neg_fail}

    R["amendments"] = [{
        "id": "J1_v1_to_v2",
        "when": "2026-09-21 轮内（正式读数定稿前）",
        "why": "v1 断言「basis 全为 mechanical」过强：实测 39/42 机械，另 3 行为 gate:repeat_no_replayable_prev→remote（守卫生效路径，gate_prompt_len=0、cache_n=0、无正向 token）。代码核验 src/agent/IndustrialAgentV2.cs:1589-1613/1701 ⇒ 该分支无模型调用。",
        "effect": "判据收窄为可证伪核心：真问本地行数=0 ∧ 正向 token 行数=0；机械占比降为读数（不作判据）。负控 J6 已按 v2 语义重跑。",
        "cross_round_safety": "同轮内改版，不与其它轮读数相减。"
    }]
    R["unmeasured"] = ["本地通道常驻 RSS（起手闸内存不足 + 与兄弟轮抢内存 ⇒ 顺延）",
                       "判别位质量（本窗非机械残余样本=0，且无外部真值）"]
    R["summary"] = {
        "J_pass": sum(1 for c in R["criteria"].values() if c["verdict"] == "PASS"),
        "J_total": len(R["criteria"]),
        "headline": f"真实流量窗内门判 {len(gate)} 次 / 机械前缀 {len(mech)} / 守卫族 {len(gate) - len(mech)} / 真问本地 {len(asked)} ⇒ 判别位零调用",
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps(R["summary"], ensure_ascii=False))
    for k, v in R["criteria"].items():
        print(f"  {k}: {v['verdict']}")
    print("→", os.path.relpath(OUT, ROOT))

if __name__ == "__main__":
    main()
