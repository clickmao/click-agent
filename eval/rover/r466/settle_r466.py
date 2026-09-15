#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R466 结算器 —— 外部真值 = 桩侧 calls-$ARM.jsonl + 驱动器 turns-$ARM.jsonl (不信被测量自报)。

用法:  python3 settle_r466.py <dir> <ARM>     # 单臂 → arm-<ARM>.json
       python3 settle_r466.py <dir> ALL      # 汇总 → verdict-r466.json (预注册判据)
判据面见 docs/plans/v0.83.1-r466-repeat-priority.md §预注册判据 (跑测前已落盘):
  C1 降幅:  R.total_tokens vs Arole ≥30% 且 calls ≤ 8
  C2 质量:  12/12 ok; 复述轮 t6/t9 可见答复 == 上一条答复逐字; t6 长度 == 21 (R465 为 46)
  C3 零回归: 非复述 10 轮 (basis,verdict) 与 R465 R 同位置逐位同; skip kind 序列同; repeat 命中 2
  C4 负控:  NC(PRIORITY=0) t6 == R465 R 的 46 字符承接反问 且 != 上一条答复; NC calls == R calls
  C5 零假跳: prefilter_violations == 0
  C6 复跑:  R vs R2 判决面逐位同 且 Δtok == Δchar×2
"""
import io, json, os, statistics, sys

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "r465", "arm-R.json")
REF_A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "r465", "arm-Arole.json")


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
    tel = os.path.join(d, "run-%s" % arm, "data", "telemetry", "host.jsonl")
    gates = [o.get("kv") or {} for o in jl(tel) if o.get("point") == "local_turn_gate"]
    cfg = [o.get("kv") or {} for o in jl(tel) if o.get("point") == "local_turn_gate_config"]
    skips = [o.get("kv") or {} for o in jl(tel) if o.get("point") == "local_gate_skip_reply"]
    clos = [o.get("kv") or {} for o in jl(tel) if o.get("point") == "continuation_closure"]
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
    return {
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
    }


def pct(a, b):
    return None if not b else round((1 - a / b) * 100.0, 2)


def rep_positions(a):
    return [i for i, b in enumerate(a.get("gate_bases") or []) if (b or "").startswith("mechanical:repeat")]


def main():
    d, arm = sys.argv[1], sys.argv[2]
    if arm != "ALL":
        r = read_arm(d, arm)
        io.open(os.path.join(d, "arm-%s.json" % arm), "w", encoding="utf-8").write(
            json.dumps(r, ensure_ascii=False, indent=1))
        print("[%s] calls=%s tok=%s gate=%s repeat=%s local=%s turns_ok=%s/%s secs_med=%s pids=%s" % (
            arm, r["calls"], r["total_tokens"], r["gate_events"], r["prefilter_repeat"],
            r["local_calls"], r["turns_ok"], r["turns"], r["secs_median"], r["server_pid_n"]))
        for i, (b, v) in enumerate(zip(r["gate_bases"], r["gate_verdicts"])):
            print("    t%-2d %-28s %s" % (i + 1, b, v))
        for i, rp in enumerate(r["replies"]):
            print("    t%-2d len=%-4d %s" % (i + 1, len(rp or ""), (rp or "").replace("\n", " ")[:70]))
        return

    arms = {}
    for a in ("Arole", "R", "NC", "R2"):
        p = os.path.join(d, "arm-%s.json" % a)
        if os.path.exists(p):
            arms[a] = json.load(io.open(p, encoding="utf-8"))
    A, R, NC, R2 = (arms.get(k) for k in ("Arole", "R", "NC", "R2"))
    ref = json.load(io.open(REF, encoding="utf-8")) if os.path.exists(REF) else None
    refA = json.load(io.open(REF_A, encoding="utf-8")) if os.path.exists(REF_A) else None

    checks, posthoc = [], []
    if A and R:
        dd = pct(R["total_tokens"], A["total_tokens"])
        checks.append({"id": "C1_drop_vs_Arole", "value": dd,
                       "pass": (dd is not None) and dd >= 30.0 and R["calls"] <= 8,
                       "note": "R %d vs Arole %d tokens (calls %d vs %d, 降幅 %s%%)" % (
                           R["total_tokens"], A["total_tokens"], R["calls"], A["calls"], dd)})
    if R:
        rep_note, rep_ok = [], True
        for i, txt in enumerate(R["replies"]):
            if i + 1 in (6, 9):
                same = (txt == R["replies"][i - 1]) and bool(txt)
                rep_ok = rep_ok and same
                rep_note.append("t%d=%s(len=%d)" % (i + 1, "verbatim" if same else "DIFF", len(txt or "")))
        t6len = len(R["replies"][5] or "") if len(R["replies"]) > 5 else -1
        checks.append({"id": "C2_quality", "value": rep_note,
                       "pass": bool(R["turns_ok"] == R["turns"] == 12 and rep_ok and t6len == 21),
                       "note": "turns_ok=%s/%s; 复述轮 %s; t6 长度=%d (R465=46 被覆盖)" % (
                           R["turns_ok"], R["turns"], ",".join(rep_note), t6len)})
        checks.append({"id": "C5_zero_fake_skip", "value": R["prefilter_violations"],
                       "pass": R["prefilter_violations"] == 0,
                       "note": "prefilter_violations=%s; repeat 命中=%s (期望 2)" % (
                           R["prefilter_violations"], R["prefilter_repeat"])})
    if ref and R:
        rp = rep_positions(ref)
        same_seq = (len(ref["gate_bases"]) == len(R["gate_bases"]))
        mism = []
        if same_seq:
            for i, b in enumerate(ref["gate_bases"]):
                if i in rp:
                    continue
                if R["gate_bases"][i] != b or R["gate_verdicts"][i] != ref["gate_verdicts"][i]:
                    mism.append(i + 1)
        kinds_ok = R["skip_reply_kinds"] == ref["skip_reply_kinds"]
        checks.append({"id": "C3_zero_regression_vs_R465", "value": {"mismatch_turns": mism, "repeat_pos": [i + 1 for i in rp]},
                       "pass": bool(same_seq and not mism and kinds_ok and R["prefilter_repeat"] == 2),
                       "note": "非复述 10 位与 R465 R 逐位同=%s (mismatch=%s); skip kinds 同=%s; repeat=%s" % (
                           same_seq and not mism, mism, kinds_ok, R["prefilter_repeat"])})
        dtok = R["total_tokens"] - ref["total_tokens"]
        posthoc.append({"id": "C3p_token_delta_vs_R465", "value": {"dtok": dtok, "dchar_dir": len("r466") - len("r465")},
                        "pass": None,
                        "note": "Δtok=%+d (R465 %d → R466 %d); 目录名等长 ⇒ 差异只来自 t6 答复长度(-25 字符)进入后续轮历史。"
                                "不得当回归, 也不得当增益 (C1 只在 r466 内部比 Arole)" % (
                                    dtok, ref["total_tokens"], R["total_tokens"])})
    if NC and R and ref:
        ref_t6 = ref["replies"][5] if len(ref["replies"]) > 5 else ""
        nc_t6 = NC["replies"][5] if len(NC["replies"]) > 5 else ""
        injectable = (nc_t6 == ref_t6) and (nc_t6 != (NC["replies"][4] if len(NC["replies"]) > 4 else None))
        checks.append({"id": "C4_negctl_injectable", "value": {"nc_t6_len": len(nc_t6 or ""), "ref_t6_len": len(ref_t6 or ""), "same_calls": NC["calls"] == R["calls"]},
                       "pass": bool(injectable and len(nc_t6 or "") == 46 and NC["calls"] == R["calls"]),
                       "note": "NC(PRIORITY=0) t6 == R465 缺陷答复(46 字符)=%s 且 != 上一条答复; NC calls=%d vs R calls=%d "
                               "⇒ 判据绑机制(同二进制/同网格/单变量)" % (nc_t6 == ref_t6, NC["calls"], R["calls"])})
    if R and R2:
        same_v = (R["calls"], R["gate_verdicts"], R["gate_bases"], R["replies"]) == \
                 (R2["calls"], R2["gate_verdicts"], R2["gate_bases"], R2["replies"])
        dt = R2["total_tokens"] - R["total_tokens"]
        dc = len("run-R2") - len("run-R")
        checks.append({"id": "C6_rerun", "value": {"dtok": dt, "expected": dc * 2},
                       "pass": bool(same_v and dt == dc * 2),
                       "note": "判决面+答复逐位同=%s; Δtok=%+d (RUNDIR 归因律 Δchar×2=%d)" % (same_v, dt, dc * 2)})
    if R:
        posthoc.append({"id": "C2p_closure_events", "value": R["closure_events"],
                        "pass": None,
                        "note": "收口面事件数=%d (承接轮才有); suppressed=真 ⇒ 优先级生效且可见" % len(R["closure_events"])})

    out = {"round": "R466", "arms": {k: {kk: v[kk] for kk in
            ("calls", "prompt_tokens", "completion_tokens", "total_tokens", "turns_ok", "turns",
             "secs_median", "secs_total", "gate_events", "prefilter_repeat", "prefilter_violations",
             "local_calls", "local_eval_tokens", "local_gen_tokens", "server_pid_n", "skip_reply_kinds")}
            for k, v in arms.items()},
            "refs": {"r465_R_total_tokens": (ref or {}).get("total_tokens"),
                     "r465_Arole_total_tokens": (refA or {}).get("total_tokens")},
            "checks": checks, "checks_posthoc": posthoc}
    io.open(os.path.join(d, "verdict-r466.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["arms"], ensure_ascii=False, indent=1))
    for c in checks:
        print("%-30s pass=%-5s %s" % (c["id"], c["pass"], c["note"]))
    for c in posthoc:
        print("[posthoc] %-28s %s" % (c["id"], c["note"]))


if __name__ == "__main__":
    main()
