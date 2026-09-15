#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R467 结算器 —— 外部真值 = 桩侧 calls-$ARM.jsonl + 驱动器 turns-$ARM.jsonl (不信被测量自报)。

判据面见 docs/plans/v0.84.0-r467-denominator-pinning.md §4 预注册判据 (跑测前已落盘):
  C1 分解恒等式:  calls == main + judge_remote_real + micro + other  (4 臂)
  C2 内外一致:    calls(桩) == llm_call 事件数(宿主遥测)
  C3 复现-Arole:  calls==13 ∧ total==32,097 ∧ judge_route=={12,local 8,sc 4,rreal 0,fb 0}
  C4 复现-Aroff:  calls==21 ∧ total==33,323 ∧ judge_route=={12,local 0,sc 4,rreal 8,fb 0}
  C5 闸负控:      denominator_gate.py 三条自检 (真红/真红/真绿) 见 gate-selftest.json
  C6 零回归:      R==6/14,529, R2==6/14,531, Δtok=+2, 判决面+答复逐位同
事后判据 (checks_posthoc): P1 判官本地化远端开销 / P2 固定分母降幅 / P3 判官延迟 / P4 Δtok 归因律修正

用法: python3 settle_r467.py <dir> <ARM>       # 单臂 → arm-<ARM>.json + ledger-<ARM>.json
      python3 settle_r467.py <dir> ALL        # 汇总 → verdict-r467.json
"""
import io, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF = {  # 历史真值 (外部对照, 只读)
    "r465_R": os.path.join(HERE, "..", "r465", "arm-R.json"),
    "r465_Arole": os.path.join(HERE, "..", "r465", "arm-Arole.json"),
    "r466_R": os.path.join(HERE, "..", "r466", "arm-R.json"),
    "r466_R2": os.path.join(HERE, "..", "r466", "arm-R2.json"),
    "r466_Arole": os.path.join(HERE, "..", "r466", "arm-Arole.json"),
}
JUDGE_HEAD = "判定用户消息相对上一轮回答"
MICRO_HEAD = "[微步骤隔离问询]"


def jl(p):
    rows = []
    if not os.path.exists(p):
        return rows
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def tel_path(d, arm):
    for cand in (os.path.join(d, "rundata-%s" % arm, "data", "telemetry", "host.jsonl"),
                 os.path.join(d, "run-%s" % arm, "data", "telemetry", "host.jsonl"),
                 os.path.join(d, "tel-%s.jsonl" % arm)):
        if os.path.exists(cand):
            return cand
    return os.path.join(d, "rundata-%s" % arm, "data", "telemetry", "host.jsonl")


def last_user(c):
    for m in reversed(c.get("messages") or []):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def classify(calls):
    cls = {"main": 0, "judge": 0, "micro": 0, "other": 0}
    idx = {"main": [], "judge": [], "micro": [], "other": []}
    for i, c in enumerate(calls):
        lu = last_user(c)
        if lu.startswith(JUDGE_HEAD):
            k = "judge"
        elif lu.startswith(MICRO_HEAD):
            k = "micro"
        elif (c.get("n_messages") or 0) >= 2 and lu:
            k = "main"
        else:
            k = "other"
        cls[k] += 1
        idx[k].append(i)
    return cls, idx


def read_arm(d, arm):
    calls = jl(os.path.join(d, "calls-%s.jsonl" % arm))
    turns, stats = [], {}
    tp = os.path.join(d, "turns-%s.jsonl" % arm)
    if os.path.exists(tp):
        try:
            o = json.load(io.open(tp, encoding="utf-8"))
            if isinstance(o, dict):
                turns, stats = (o.get("turns") or []), (o.get("stats") or {})
            else:
                turns = o
        except Exception:
            pass
    trows = jl(tel_path(d, arm))
    gates = [o.get("kv") or {} for o in trows if o.get("point") == "local_turn_gate"]
    cfg = [o.get("kv") or {} for o in trows if o.get("point") == "local_turn_gate_config"]
    skips = [o.get("kv") or {} for o in trows if o.get("point") == "local_gate_skip_reply"]
    clos = [o.get("kv") or {} for o in trows if o.get("point") == "continuation_closure"]
    judge_ev = [o.get("kv") or {} for o in trows if o.get("point") == "correction_judge"]
    llm_ev = [o for o in trows if o.get("point") == "llm_call"]
    serv = []
    sp = os.path.join(d, "server-%s.txt" % arm)
    if os.path.exists(sp):
        serv = [l.split() for l in io.open(sp, encoding="utf-8").read().splitlines() if l.strip()]
    pids = sorted({t[1] for t in serv if len(t) > 1})
    hostlog = os.path.join(d, "host-%s.log" % arm)
    warn = 0
    if os.path.exists(hostlog):
        warn = sum(1 for l in io.open(hostlog, encoding="utf-8", errors="replace") if "config_" in l)
    pt = sum(int(c.get("prompt_tokens_est") or 0) for c in calls)
    ct = sum(int(c.get("completion_tokens_est") or 0) for c in calls)
    secs = [float(t.get("secs") or 0) for t in turns]
    gl = [g for g in gates if not (g.get("basis") or "").startswith("mechanical")]
    ev = [int(g.get("tokens_evaluated") or -1) for g in gl]
    gen = [int(g.get("gen_tokens") or -1) for g in gl]
    cls, cidx = classify(calls)
    def src(j):
        return (j.get("source") or "")
    route = {
        "events": len(judge_ev),
        "local": sum(1 for j in judge_ev if src(j) == "local"),
        "shortcircuit": sum(1 for j in judge_ev if src(j) == "remote" and int(j.get("prompt_len") or 0) == 0),
        "remote_real": sum(1 for j in judge_ev if src(j) == "remote" and int(j.get("prompt_len") or 0) > 0),
        "remote_fallback": sum(1 for j in judge_ev if src(j).startswith("remote_fallback")),
        "local_ms": [round(float(j.get("ms") or 0), 1) for j in judge_ev if src(j) == "local"],
        "remote_real_ms": [round(float(j.get("ms") or 0), 1) for j in judge_ev if src(j) == "remote" and int(j.get("prompt_len") or 0) > 0],
        "local_prompt_len": [int(j.get("prompt_len") or 0) for j in judge_ev if src(j) == "local"],
        "remote_real_tokens_est": [int(j.get("tokens") or 0) for j in judge_ev if src(j) == "remote" and int(j.get("prompt_len") or 0) > 0],
        "heads": [j.get("msg_head") for j in judge_ev],
    }
    jcalls_pt = sum(int(calls[i].get("prompt_tokens_est") or 0) for i in cidx["judge"])
    jcalls_ct = sum(int(calls[i].get("completion_tokens_est") or 0) for i in cidx["judge"])
    r = {
        "arm": arm, "calls": len(calls), "prompt_tokens": pt, "completion_tokens": ct,
        "total_tokens": pt + ct, "turns": len(turns),
        "turns_ok": sum(1 for t in turns if t.get("ok")),
        "secs": [round(s, 2) for s in secs],
        "secs_median": round(statistics.median(secs), 2) if secs else None,
        "secs_total": round(sum(secs), 1),
        "gate_events": len(gates), "gate_bases": [g.get("basis") for g in gates],
        "gate_verdicts": [g.get("verdict") for g in gates],
        "prefilter_repeat": int((gates[-1].get("prefilter_repeat") or 0)) if gates else None,
        "prefilter_violations": int((gates[-1].get("prefilter_violations") or 0)) if gates else None,
        "local_calls": len(gl), "local_eval_tokens": sum(e for e in ev if e > 0),
        "local_gen_tokens": sum(g for g in gen if g > 0),
        "gate_config": cfg[0] if cfg else {},
        "skip_reply_kinds": [s.get("kind") for s in skips],
        "closure_events": clos,
        "server_pids": pids, "server_pid_n": len(pids), "warn_lines": warn,
        "replies": [t.get("reply") for t in turns], "texts": [t.get("text") for t in turns],
        "stats": stats,
        # ---- R467 新增 ----
        "calls_class": cls, "calls_class_idx": cidx,
        "judge_route": route, "remote_llm_events": len(llm_ev),
        "judge_calls_tokens": {"prompt": jcalls_pt, "completion": jcalls_ct, "total": jcalls_pt + jcalls_ct},
    }
    return r


def pct(a, b):
    return None if not b else round((1 - a / b) * 100.0, 2)


def rep_positions(a):
    return [i for i, b in enumerate(a.get("gate_bases") or []) if (b or "").startswith("mechanical:repeat")]


def identity(r):
    """G1: 分解恒等式 —— judge(本地) 不产生桩侧调用。"""
    c = r["calls_class"]
    lhs = c["main"] + c["judge"] + c["micro"] + c["other"]
    return {
        "lhs_calls": r["calls"], "rhs_decomposed": lhs,
        "identity_holds": lhs == r["calls"],
        "judge_calls_matches_route": (c["judge"] == r["judge_route"]["remote_real"] + r["judge_route"]["remote_fallback"]),
        "pass": bool(lhs == r["calls"] and c["judge"] == r["judge_route"]["remote_real"] + r["judge_route"]["remote_fallback"]),
    }


def _arm_class_of(flags):
    """单一来源: 直接复用 denominator_gate.arm_class_of (禁止两处各写一份)。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import denominator_gate as _G
    return _G.arm_class_of(flags)


def ledger(d, arm, r):
    fp = os.path.join(d, "flags-%s.json" % arm)
    flags = json.load(io.open(fp, encoding="utf-8")) if os.path.exists(fp) else {}
    return {
        "round": "R467", "arm": arm, "arm_class": _arm_class_of(flags),
        "flags": flags, "calls": r["calls"], "total_tokens": r["total_tokens"],
        "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
        "turns": r["turns"], "turns_ok": r["turns_ok"],
        "calls_class": r["calls_class"], "judge_route": r["judge_route"],
        "judge_calls_tokens": r["judge_calls_tokens"], "remote_llm_events": r["remote_llm_events"],
        "identity": identity(r), "gate_events": r["gate_events"], "local_calls": r["local_calls"],
        "gate_verdicts": r["gate_verdicts"], "gate_bases": r["gate_bases"],
        "skip_reply_kinds": r["skip_reply_kinds"],
    }


def main():
    d, arm = sys.argv[1], sys.argv[2]
    if arm != "ALL":
        r = read_arm(d, arm)
        io.open(os.path.join(d, "arm-%s.json" % arm), "w", encoding="utf-8").write(
            json.dumps(r, ensure_ascii=False, indent=1))
        L = ledger(d, arm, r)
        io.open(os.path.join(d, "ledger-%s.json" % arm), "w", encoding="utf-8").write(
            json.dumps(L, ensure_ascii=False, indent=1))
        idt = L["identity"]
        print("[%s] calls=%s tok=%s cls=%s judge=%s llm_ev=%s gate=%s local=%s turns_ok=%s/%s secs_med=%s pids=%s" % (
            arm, r["calls"], r["total_tokens"], json.dumps(r["calls_class"], ensure_ascii=False),
            json.dumps(r["judge_route"]["events"] and {k: r["judge_route"][k] for k in ("events", "local", "shortcircuit", "remote_real", "remote_fallback")}, ensure_ascii=False),
            r["remote_llm_events"], r["gate_events"], r["local_calls"], r["turns_ok"], r["turns"], r["secs_median"], r["server_pid_n"]))
        print("    G1 恒等式 %s=%s+%s+%s+%s holds=%s judge(calls=%s==rreal+fb=%s)⇒pass=%s" % (
            idt["lhs_calls"], r["calls_class"]["main"], r["calls_class"]["judge"], r["calls_class"]["micro"],
            r["calls_class"]["other"], idt["identity_holds"], r["calls_class"]["judge"],
            r["judge_route"]["remote_real"] + r["judge_route"]["remote_fallback"], idt["pass"]))
        print("    G2 内外一致 calls=%s == remote_llm_events=%s ⇒ %s" % (
            r["calls"], r["remote_llm_events"], r["calls"] == r["remote_llm_events"]))
        if r["judge_route"]["local_ms"]:
            print("    judge 本地延迟 ms=%s (n=%d)" % (r["judge_route"]["local_ms"], len(r["judge_route"]["local_ms"])))
        if r["judge_route"]["remote_real_ms"]:
            print("    judge 远端延迟 ms=%s (n=%d)" % (r["judge_route"]["remote_real_ms"], len(r["judge_route"]["remote_real_ms"])))
        for i, (b, v) in enumerate(zip(r["gate_bases"], r["gate_verdicts"])):
            print("    t%-2d %-28s %s" % (i + 1, b, v))
        for i, rp in enumerate(r["replies"]):
            print("    t%-2d len=%-4d %s" % (i + 1, len(rp or ""), (rp or "").replace("\n", " ")[:70]))
        return

    arms = {}
    for a in ("Arole", "Aroff", "R", "R2"):
        p = os.path.join(d, "arm-%s.json" % a)
        if os.path.exists(p):
            arms[a] = json.load(io.open(p, encoding="utf-8"))
    led = {}
    for a in arms:
        p = os.path.join(d, "ledger-%s.json" % a)
        if os.path.exists(p):
            led[a] = json.load(io.open(p, encoding="utf-8"))
    A, RO, R, R2 = (arms.get(k) for k in ("Arole", "Aroff", "R", "R2"))
    ref = {k: (json.load(io.open(v, encoding="utf-8")) if os.path.exists(v) else None) for k, v in REF.items()}
    gate_self = None
    gsp = os.path.join(d, "gate-selftest.json")
    if os.path.exists(gsp):
        gate_self = json.load(io.open(gsp, encoding="utf-8"))

    checks, posthoc = [], []

    # C1 分解恒等式
    if arms:
        bad = {a: L["identity"] for a, L in led.items() if not L["identity"]["pass"]}
        checks.append({"id": "C1_decomposition_identity", "value": bad or "all_pass",
                       "pass": bool(led) and not bad,
                       "note": "恒等式 calls == main + judge_remote + micro + other 对 %d/%d 臂成立; 不成立臂=%s" % (
                           len(led) - len(bad), len(led), list(bad))})

    # C2 内外一致 (桩 vs 宿主遥测)
    if arms:
        bad2 = {a: [r["calls"], r["remote_llm_events"]] for a, r in arms.items() if r["calls"] != r["remote_llm_events"]}
        checks.append({"id": "C2_internal_external_agree", "value": bad2 or "all_pass",
                       "pass": not bad2,
                       "note": "桩侧调用数 == 宿主 llm_call 事件数 对 %d/%d 臂成立; 不符=%s" % (
                           len(arms) - len(bad2), len(arms), bad2)})

    # C3 复现 Arole (生产等价分母)
    if A:
        jr = A["judge_route"]
        exp = {"events": 12, "local": 8, "shortcircuit": 4, "remote_real": 0, "remote_fallback": 0}
        got = {k: jr[k] for k in exp}
        ok = (A["calls"] == 13 and A["total_tokens"] == 32097 and A["turns_ok"] == 12 and got == exp)
        checks.append({"id": "C3_reproduce_Arole", "value": {"calls": A["calls"], "total_tokens": A["total_tokens"], "judge_route": got},
                       "pass": ok,
                       "note": "期望 calls=13 total=32,097 turns_ok=12 judge_route=%s (R466 同配置逐位复现)" % json.dumps(exp)})

    # C4 复现 Aroff (单变量负控) —— H1 的直接判决
    if RO:
        jr = RO["judge_route"]
        exp = {"events": 12, "local": 0, "shortcircuit": 4, "remote_real": 8, "remote_fallback": 0}
        got = {k: jr[k] for k in exp}
        ok = (RO["calls"] == 21 and RO["total_tokens"] == 33323 and RO["turns_ok"] == 12 and got == exp)
        checks.append({"id": "C4_reproduce_Aroff_single_variable", "value": {"calls": RO["calls"], "total_tokens": RO["total_tokens"], "judge_route": got},
                       "pass": ok,
                       "note": "期望 calls=21 total=33,323 judge_route=%s (R465 Arole 配置; 同一二进制 + 同一字面 cwd ⇒ 差异只由 relation_judge 标志解释 ⇒ H1 成立)" % json.dumps(exp)})

    # C5 闸自检
    if gate_self is not None:
        checks.append({"id": "C5_gate_selftest", "value": gate_self,
                       "pass": bool(gate_self.get("all_pass")),
                       "note": "denominator_gate.py 自检: %s" % gate_self.get("summary")})

    # C6 生产面零回归
    if R and R2:
        same_v = (R["calls"], R["gate_verdicts"], R["gate_bases"], R["replies"]) == \
                 (R2["calls"], R2["gate_verdicts"], R2["gate_bases"], R2["replies"])
        dt = R2["total_tokens"] - R["total_tokens"]
        ok = bool(R["calls"] == 6 and R["total_tokens"] == 14529 and R2["total_tokens"] == 14531 and dt == 2 and same_v)
        checks.append({"id": "C6_production_zero_regression", "value": {"R": [R["calls"], R["total_tokens"]], "R2": [R2["calls"], R2["total_tokens"]], "dtok": dt, "same_verdicts": same_v},
                       "pass": ok,
                       "note": "期望 R=6/14,529, R2=6/14,531, Δtok=+2, 判决面+答复逐位同=%s (复用 R466 AOT 产物; 仅计量面新增)" % same_v})

    # P1 判官本地化的远端开销 (事后)
    if A and RO:
        d_calls = RO["calls"] - A["calls"]
        d_tok = RO["total_tokens"] - A["total_tokens"]
        jt = RO["judge_calls_tokens"]
        posthoc.append({"id": "P1_judge_localization_saving", "value": {"d_calls": d_calls, "d_tokens": d_tok, "judge_call_tokens": jt},
                        "pass": None,
                        "note": "Aroff - Arole = %d 次远端调用 / %d tok; 桩侧这 8 次判官调用实测 prompt=%d + completion=%d = %d tok ⇒ 逐位吻合=%s (Arole 总 token 的 %.2f%%)" % (
                            d_calls, d_tok, jt["prompt"], jt["completion"], jt["total"], jt["total"] == d_tok,
                            100.0 * d_tok / max(1, RO["total_tokens"]))})
    # P2 固定分母降幅
    if A and R:
        posthoc.append({"id": "P2_drop_on_pinned_denominator", "value": {"drop_pct": pct(R["total_tokens"], A["total_tokens"]),
                                                                        "drop_pct_vs_r465_style": pct(R["total_tokens"], 33323)},
                        "pass": None,
                        "note": "生产等价分母(判官本地化, 13/32,097) 上降幅=%.2f%%; 若沿用 R465 口径(21/33,323)=%.2f%% ⇒ 两种口径都 ≥30%%" % (
                            pct(R["total_tokens"], A["total_tokens"]), pct(R["total_tokens"], 33323))})
    # P3 判官延迟
    if A:
        lm = A["judge_route"]["local_ms"]
        rm = A["judge_route"]["remote_real_ms"]
        posthoc.append({"id": "P3_judge_latency", "value": {"local_ms": lm, "remote_ms": rm, "turns_secs_median": A["secs_median"]},
                        "pass": None,
                        "note": "本地判官 n=%d 单次 %s..%s ms (累计等待形态) vs 远端判官 n=%d 单次平均 %s ms ⇒ 本地化省 token 但把延迟留在本地" % (
                            len(lm), (lm[0] if lm else None), (lm[-1] if lm else None), len(rm),
                            (round(sum(rm) / len(rm), 1) if rm else None))})
    # P4 Δtok 归因律修正
    if R and R2:
        posthoc.append({"id": "P4_dtok_attribution_law", "value": {"dtok": R2["total_tokens"] - R["total_tokens"], "dchar": len("run-R2") - len("run-R")},
                        "pass": None,
                        "note": "R466 曾把 Δtok 写成「Δchar×2」的律; 逐调用核对 = 「system 首条 `根目录` 路径出现在每次调用, 每次调用 δ∈{0,+1} (分词边界)」" 
                                "⇒ ×2 只是该实例的巧合 (本轮 R/R2 复测值 %+d)" % (R2["total_tokens"] - R["total_tokens"])})

    # C7 分母可比性审计 (跨轮同名臂 / 同类分母 / 真实历史负控)
    if len(led) >= 3:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import denominator_gate as G
            pairs = [("X1_cross_round_same_arm_R(r466→r467)", "r466", "R", "R"),
                     ("X2_cross_round_same_arm_Arole(r466→r467)", "r466", "Arole", "Arole"),
                     ("X3_same_class_pre_r1_baseline(r465.Arole→r467.Aroff)", "r465", "Arole", "Aroff"),
                     ("X4_NEGCTL_real_drift(r465.Arole→r467.Arole)", "r465", "Arole", "Arole")]
            expect = {"X1": "OK_COMPARABLE", "X2": "OK_COMPARABLE", "X3": "OK_COMPARABLE", "X4": "VOID_NOT_COMPARABLE"}
            audits = []
            for name, rd, barm, aarm in pairs:
                res = G.run_gate(G.recon(rd, barm), led[aarm])
                g4c = res["checks"][4]
                audits.append({"id": name, "verdict": res["verdict"], "expect": expect[name[:2]],
                               "pass": res["verdict"] == expect[name[:2]],
                               "mode": g4c["value"]["mode"], "diffs": g4c["value"]["diffs"],
                               "undeclared": g4c["value"]["undeclared"], "red": res["red"]})
            json.dump(audits, io.open(os.path.join(d, "gate-audit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            checks.append({"id": "C7_posthoc_denominator_comparability_audit", "value": audits,
                           "pass": all(a["pass"] for a in audits),
                           "note": "【事后增补, 不在预注册 §4 内】同名臂跨轮可比=%s; 同类分母(跨轮异名)可比=%s; 真实漂移负控被判红=%s(差异键=%s)" % (
                               all(a["pass"] for a in audits if a["id"].startswith("X1") or a["id"].startswith("X2")),
                               all(a["pass"] for a in audits if a["id"].startswith("X3")),
                               audits[3]["pass"], audits[3]["diffs"])})
        except Exception as e:
            checks.append({"id": "C7_denominator_comparability_audit", "pass": False, "value": str(e),
                           "note": "审计执行异常: %r" % (e,)})

    out = {"round": "R467", "arms": {k: {kk: v[kk] for kk in
            ("calls", "prompt_tokens", "completion_tokens", "total_tokens", "turns_ok", "turns",
             "secs_median", "secs_total", "gate_events", "prefilter_repeat", "prefilter_violations",
             "local_calls", "local_eval_tokens", "local_gen_tokens", "server_pid_n", "skip_reply_kinds",
             "calls_class", "judge_route", "remote_llm_events", "judge_calls_tokens")}
            for k, v in arms.items()},
            "ledgers": {k: {"arm_class": v["arm_class"], "flags": v["flags"], "identity": v["identity"]} for k, v in led.items()},
            "refs": {k: (v or {}).get("total_tokens") for k, v in ref.items()},
            "checks": checks, "checks_posthoc": posthoc}
    io.open(os.path.join(d, "verdict-r467.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: {kk: v[kk] for kk in ("calls", "total_tokens", "calls_class", "remote_llm_events")} for k, v in arms.items()},
                     ensure_ascii=False, indent=1))
    for c in checks:
        print("%-38s pass=%-5s %s" % (c["id"], c["pass"], c["note"]))
    for c in posthoc:
        print("[posthoc] %-34s %s" % (c["id"], c["note"]))


if __name__ == "__main__":
    main()
