#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R425 结算器 — 「非实质轮占比 → 降幅」敏感性网格。

判据文本冻结于 docs/plans/v0.46.0-r425-ratio-sensitivity-grid.md（mtime 早于首臂）。
本脚本只做判据计算，不含事后放宽: 预注册判据失败 ⇒ 写入 pre_registered_failures，事后判据单列 checks_posthoc。

用法: python3 verdict_r425.py [-b2]
读数口径: 外部真值 = 桩侧 calls-*.jsonl 逐请求落盘（不是被测量代码自报计数器）。
逐轮归属: 顺序分区 [t_start_i, t_start_{i+1})（b1 曾用"首个覆盖窗口"，窗口重叠 ⇒ 全部落第 1 轮，已废弃）。
"""
import json, os, sys, glob, hashlib

D = os.path.dirname(os.path.abspath(__file__))
SFX = sys.argv[1] if len(sys.argv) > 1 else "-b2"
KS = [1, 2, 4, 6, 8]
TOL_LIN = 0.15      # C4 预注册容差（线性对账）
TOL_CTL = 0.02      # C7 预注册容差（负控臂）
S_POOL = {"谢谢，先这样。", "好，知道了。", "嗯。", "好，按这个来。", "明白了。", "好的，继续。", "嗯，可以。", "收到，谢谢。"}
STUB_MARK = "桩应答"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def load(arm, k):
    b = json.load(open(f"{D}/budget-{arm}-k{k}{SFX}.json", encoding="utf-8"))
    calls = [json.loads(l) for l in open(f"{D}/calls-{arm}-k{k}{SFX}.jsonl", encoding="utf-8") if l.strip()]
    turns = json.load(open(f"{D}/turns-{arm}-k{k}{SFX}.jsonl", encoding="utf-8"))["turns"]
    prov = json.load(open(f"{D}/prov-{arm}-k{k}{SFX}.json", encoding="utf-8"))
    return b, calls, turns, prov


def seq_attr(turns, calls):
    """顺序分区归因（唯一、无重叠）: [t_start_i, t_start_{i+1})；末轮取 +secs+5。"""
    turns = sorted(turns, key=lambda x: x["t_start"])
    if not turns:
        return {}, {}, {}, len(calls)
    starts = [t["t_start"] for t in turns] + [turns[-1]["t_start"] + turns[-1]["secs"] + 5]
    per = {t["turn"]: 0 for t in turns}
    tok = {t["turn"]: 0 for t in turns}
    ok = {t["turn"]: t.get("ok") for t in turns}
    unassigned = 0
    for c in calls:
        ts = c["ts"]
        j = None
        for i, t in enumerate(turns):
            if starts[i] <= ts < starts[i + 1]:
                j = t["turn"]
                break
        if j is None:
            unassigned += 1
        else:
            per[j] += 1
            tok[j] += c["prompt_tokens_est"] + c["completion_tokens_est"]
    return per, tok, ok, unassigned


def tot(calls):
    return (len(calls), sum(c["prompt_tokens_est"] + c["completion_tokens_est"] for c in calls))


def main():
    res = {"round": "R425", "suffix": SFX, "checks": {}, "readings": {}, "pre_registered_failures": [],
           "checks_posthoc": {}, "verdict": "FAIL"}
    data = {}
    # ---------- C0 输入面完整性 ----------
    c0 = {"tasks_ok": True, "detail": []}
    for k in KS:
        p = f"{D}/grid/task-k{k}.json"
        base = sha256(p)
        want = None
        for line in open(f"{D}/grid-sha-before.txt", encoding="utf-8"):
            if line.strip().endswith(os.path.basename(p)):
                want = line.split()[0]
        if want and want != base:
            c0["tasks_ok"] = False
        j = json.load(open(p, encoding="utf-8"))
        skips = [i + 1 for i, t in enumerate(j["turns"]) if t in S_POOL]
        ok = (len(j["turns"]) == 8 and skips == j["expected_skip_positions"] and j["ratio_k"] == k)
        c0["detail"].append({"k": k, "n_turns": len(j["turns"]), "skip_positions": skips,
                             "declared": j["expected_skip_positions"], "sha256": base, "consistent": ok})
        if not ok:
            c0["tasks_ok"] = False
    res["checks"]["C0_input_fidelity"] = c0

    # ---------- 载入 + C1 形态闸 ----------
    c1 = {"native_ok": True, "same_sha": True, "detail": []}
    for k in KS:
        for arm in ("A", "B"):
            b, calls, turns, prov = load(arm, k)
            data[(arm, k)] = (b, calls, turns, prov)
            u = prov.get("under_test", {})
            good = u.get("native_ok") is True and u.get("bare_rc") == 0 and u.get("needs_runtime") is False
            c1["detail"].append({"arm": arm, "k": k, "native_ok": u.get("native_ok"), "bare_rc": u.get("bare_rc"),
                                 "sha256": u.get("sha256"), "bytes": u.get("bytes"), "gate_ok": bool(good)})
            if not good:
                c1["native_ok"] = False
    b, calls, turns, prov = load("BP", 6)
    data[("BP", 6)] = (b, calls, turns, prov)
    shas = {d[3].get("under_test", {}).get("sha256") for d in data.values()}
    c1["same_sha"] = len(shas) == 1
    c1["distinct_shas"] = sorted(x for x in shas if x)
    res["checks"]["C1_binary_identity"] = c1

    # ---------- 读数（外部真值） ----------
    reads = {}
    for (arm, k), (b, calls, turns, prov) in data.items():
        per, tok, ok, un = seq_attr(turns, calls)
        nc, nt = tot(calls)
        reads[f"{arm}-k{k}"] = {"remote_calls": nc, "remote_tokens": nt,
                                "per_turn_calls": per, "per_turn_tokens": tok, "unassigned": un,
                                "turn_ok": ok, "turn_secs": {t["turn"]: t["secs"] for t in turns}}
    res["readings"] = reads

    # ---------- C-d 臂 A 全轮 ≥1 远端调用（calls==6 与 8 轮差异须为本地短路） ----------
    c_d = {"a_all_turns_called": True, "short_circuit_turns": []}
    for k in KS:
        per = reads[f"A-k{k}"]["per_turn_calls"]
        misses = sorted(int(t) for t, n in per.items() if n == 0)
        c_d["short_circuit_turns"].append({"k": k, "turns_without_remote_call": misses})
    res["checks"]["C_d_armA_calls_every_turn_or_short_circuit"] = c_d

    # ---------- C-a 单调性 ----------
    r = {}
    for k in KS:
        a_c, a_t = reads[f"A-k{k}"]["remote_calls"], reads[f"A-k{k}"]["remote_tokens"]
        b_c, b_t = reads[f"B-k{k}"]["remote_calls"], reads[f"B-k{k}"]["remote_tokens"]
        r[k] = {"calls": {"A": a_c, "B": b_c, "delta": a_c - b_c, "ratio": (a_c - b_c) / a_c if a_c else None},
                "tokens": {"A": a_t, "B": b_t, "delta": a_t - b_t, "ratio": (a_t - b_t) / a_t if a_t else None}}
    res["readings"]["deltas"] = r
    seq_r = [r[k]["tokens"]["ratio"] for k in [1, 2, 4, 6]]
    c_a = {"strictly_increasing_1_2_4_6": all(seq_r[i] < seq_r[i + 1] for i in range(3)),
           "monotone_full": all(r[KS[i]]["tokens"]["ratio"] <= r[KS[i + 1]]["tokens"]["ratio"] for i in range(4)),
           "ratios": {str(k): r[k]["tokens"]["ratio"] for k in KS}}
    res["checks"]["C_a_monotone"] = c_a

    # ---------- C-b 线性对账（闭式: D_k = k * c_hat, c_hat = D_8/8） ----------
    c_hat = r[8]["tokens"]["delta"] / 8.0
    lin = {}
    for k in [1, 2, 4, 6]:
        pred = k * c_hat
        got = r[k]["tokens"]["delta"]
        lin[str(k)] = {"D_k": got, "pred_k": pred, "rel_err": abs(got - pred) / pred if pred else None}
    c_b = {"c_hat": c_hat, "detail": lin,
           "all_within_tol": all(v["rel_err"] is not None and v["rel_err"] <= TOL_LIN for v in lin.values())}
    res["checks"]["C_b_linear_reconciliation"] = c_b

    # ---------- C-c 假阴性 = 0 / 跳过轮 0 调用 ----------
    c_c = {"fn": [], "skipped_with_calls": [], "ok": True}
    for k in KS:
        t = json.load(open(f"{D}/grid/task-k{k}.json", encoding="utf-8"))
        subs = [i + 1 for i, x in enumerate(t["turns"]) if x not in S_POOL]
        per = reads[f"B-k{k}"]["per_turn_calls"]
        for tn in subs:
            if per.get(str(tn), per.get(tn, 0)) == 0:
                c_c["fn"].append({"k": k, "turn": tn})
        for tn in t["expected_skip_positions"]:
            if per.get(str(tn), per.get(tn, 0)) != 0:
                c_c["skipped_with_calls"].append({"k": k, "turn": tn, "calls": per.get(tn, per.get(str(tn)))})
    c_c["ok"] = not c_c["fn"] and not c_c["skipped_with_calls"]
    res["checks"]["C_c_no_false_negative"] = c_c

    # ---------- C-g 跳过轮回复性质（与 C-c 配对） ----------
    c_g = {"ok": True, "detail": []}
    for k in KS:
        t = json.load(open(f"{D}/grid/task-k{k}.json", encoding="utf-8"))
        turns = {x["turn"]: x for x in data[("B", k)][2]}
        for tn in t["expected_skip_positions"]:
            rep = turns[tn]["reply"]
            good = bool(rep.strip()) and len(rep) <= 60 and STUB_MARK not in rep
            c_g["detail"].append({"k": k, "turn": tn, "len": len(rep), "stub_mark": STUB_MARK in rep, "ok": good})
            if not good:
                c_g["ok"] = False
    res["checks"]["C_g_skipped_reply_not_from_remote"] = c_g

    # ---------- C-e 归因负控 BP(k=6) ----------
    a_c, a_t = reads["A-k6"]["remote_calls"], reads["A-k6"]["remote_tokens"]
    p_c, p_t = reads["BP-k6"]["remote_calls"], reads["BP-k6"]["remote_tokens"]
    c_e = {"armA": {"calls": a_c, "tokens": a_t}, "armBP": {"calls": p_c, "tokens": p_t},
           "calls_equal": a_c == p_c, "tok_rel_diff": abs(a_t - p_t) / a_t if a_t else None,
           "gain_zero": (abs(a_t - p_t) / a_t if a_t else 1) <= TOL_CTL}
    res["checks"]["C_e_attribution_control"] = c_e

    # ---------- C-f k=8 边界 ----------
    p8 = reads["B-k8"]["per_turn_calls"]
    k8_skip = sum(1 for _, n in p8.items() if n == 0)
    res["checks"]["C_f_k8_boundary"] = {"expected_skips": 8, "effective_skips": k8_skip,
                                        "turns_with_remote_call": sorted(int(t) for t, n in p8.items() if n > 0),
                                        "note": "k=8 为边界格: 首轮无历史, 门是否跳过后验记录, 不并入 C-b"}

    # ---------- 事后（单列，不参与判决） ----------
    fn_ref, skip_saving = [], []
    for k in KS:
        t = json.load(open(f"{D}/grid/task-k{k}.json", encoding="utf-8"))
        pa, pb = reads[f"A-k{k}"]["per_turn_calls"], reads[f"B-k{k}"]["per_turn_calls"]
        ta, tb = reads[f"A-k{k}"]["per_turn_tokens"], reads[f"B-k{k}"]["per_turn_tokens"]
        g = (lambda d, i: d.get(i, d.get(str(i), 0)))
        for tn in [i + 1 for i, x in enumerate(t["turns"]) if x not in S_POOL]:
            if g(pa, tn) >= 1 and g(pb, tn) == 0:
                fn_ref.append({"k": k, "turn": tn})
        for tn in t["expected_skip_positions"]:
            skip_saving.append({"k": k, "turn": tn, "tok_A": g(ta, tn), "tok_B": g(tb, tn),
                                "calls_A": g(pa, tn), "calls_B": g(pb, tn)})
    ph = {"A_referenced_false_negative": fn_ref, "A_referenced_FN_zero": not fn_ref,
          "skipped_turn_saving": skip_saving,
          "skipped_turns_saving_all_positive": all(x["tok_A"] > x["tok_B"] for x in skip_saving),
          "per_skipped_turn_saving": {str(k): (r[k]["tokens"]["delta"] / k) for k in KS},
          "curve_ratio_vs_share": {str(k): {"share": k / 8.0, "token_ratio": r[k]["tokens"]["ratio"]} for k in KS}}
    xs = [k / 8.0 for k in KS]
    ys = [r[k]["tokens"]["ratio"] for k in KS]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    slope = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / den if den else None
    ph["linear_fit"] = {"slope": slope, "intercept": (my - slope * mx) if slope is not None else None}
    res["checks_posthoc"] = ph

    # ---------- 判决 ----------
    pre = {"C0_input_fidelity": c0["tasks_ok"], "C1_binary_identity": c1["native_ok"] and c1["same_sha"],
           "C_a_monotone": c_a["strictly_increasing_1_2_4_6"] and c_a["monotone_full"],
           "C_b_linear_reconciliation": c_b["all_within_tol"],
           "C_c_no_false_negative": c_c["ok"], "C_g_skipped_reply_not_from_remote": c_g["ok"],
           "C_e_attribution_control": c_e["calls_equal"] and c_e["gain_zero"]}
    res["pre_registered"] = pre
    res["pre_registered_failures"] = [k for k, v in pre.items() if not v]
    hard = ["C0_input_fidelity", "C1_binary_identity"]
    if any(not pre[h] for h in hard):
        res["verdict"] = "FAIL"
    elif not res["pre_registered_failures"]:
        res["verdict"] = "PASS"
    else:
        res["verdict"] = "PARTIAL"
    outp = f"{D}/verdict-r425{SFX}.json"
    json.dump(res, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"verdict": res["verdict"], "failures": res["pre_registered_failures"],
                      "ratios": c_a["ratios"], "c_hat": c_hat, "lin": lin,
                      "A6": reads["A-k6"]["remote_calls"], "BP6": reads["BP-k6"]["remote_calls"]},
                     ensure_ascii=False, indent=1))
    print("written:", outp)


if __name__ == "__main__":
    main()
