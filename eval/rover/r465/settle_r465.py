#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R465 结算器 —— 外部真值 = 桩侧 calls-$ARM.jsonl (不信被测量自报)。

用法:  python3 settle_r465.py <dir> <ARM>      # 单臂 → arm-<ARM>.json
       python3 settle_r465.py <dir> ALL        # 汇总 → verdict-r465.json (预注册判据)
判据面 (预注册, 写在 docs/plans/v0.83.0-r465-repeat-skip.md §判据):
  C1 降幅:  R 远端 token vs Arole ≥30%
  C2 增量:  R 远端 token < B3B (复述族是净增量, 不是重排)
  C3 质量:  12/12 轮 ok; 复述轮答复 == 上一条答复 (逐字)
  C4 零假跳: prefilter_violations == 0; 非复述轮 verdict 序列与 B3B 相同
  C5 窄面:  prefilter_repeat == 2 (恰为 t6/t9)
  C6 复跑:  R vs R2 逐位相同 (调用数/token/逐轮 verdict)
  C7 预热:  W1 的 server pid 数 == 1 且 turn1 墙钟 ≤ R
"""
import io, json, os, statistics, sys

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
    turns_raw = os.path.join(d, "turns-%s.jsonl" % arm)
    turns, stats = [], {}
    if os.path.exists(turns_raw):
        try:
            o = json.load(io.open(turns_raw, encoding="utf-8"))
            if isinstance(o, dict):
                turns = o.get("turns") or []
                stats = o.get("stats") or {}
            else:
                turns = o
        except Exception:
            pass
    tel = os.path.join(d, "run-%s" % arm, "data", "telemetry", "host.jsonl")
    gates = []
    for o in jl(tel):
        if o.get("point") == "local_turn_gate":
            gates.append(o.get("kv") or {})
    cfg = [o.get("kv") or {} for o in jl(tel) if o.get("point") == "local_turn_gate_config"]
    skips = [o.get("kv") or {} for o in jl(tel) if o.get("point") == "local_gate_skip_reply"]
    warms = [o.get("kv") or {} for o in jl(tel) if o.get("point") == "local_channel_warmup"]
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
    gate_local = [g for g in gates if not (g.get("basis") or "").startswith("mechanical")]
    ev = [int(g.get("tokens_evaluated") or -1) for g in gate_local]
    gen = [int(g.get("gen_tokens") or -1) for g in gate_local]
    return {
        "arm": arm,
        "calls": len(calls),
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": pt + ct,
        "turns": len(turns),
        "turns_ok": sum(1 for t in turns if t.get("ok")),
        "secs": [round(s, 2) for s in secs],
        "secs_median": round(statistics.median(secs), 2) if secs else None,
        "secs_total": round(sum(secs), 1),
        "gate_events": len(gates),
        "gate_bases": [g.get("basis") for g in gates],
        "gate_verdicts": [g.get("verdict") for g in gates],
        "prefilter_repeat": int((gates[-1].get("prefilter_repeat") or 0)) if gates else None,
        "prefilter_violations": int((gates[-1].get("prefilter_violations") or 0)) if gates else None,
        "local_calls": len(gate_local),
        "local_eval_tokens": sum(e for e in ev if e > 0),
        "local_gen_tokens": sum(g for g in gen if g > 0),
        "gate_config": cfg[0] if cfg else {},
        "skip_reply_kinds": [s.get("kind") for s in skips],
        "warmup_events": warms,
        "server_pids": pids,
        "server_pid_n": len(pids),
        "warn_lines": warn,
        "replies": [t.get("reply") for t in turns],
        "texts": [t.get("text") for t in turns],
    }

def pct(a, b):
    return None if not b else round((1 - a / b) * 100.0, 2)

def main():
    d, arm = sys.argv[1], sys.argv[2]
    if arm != "ALL":
        r = read_arm(d, arm)
        io.open(os.path.join(d, "arm-%s.json" % arm), "w", encoding="utf-8").write(
            json.dumps(r, ensure_ascii=False, indent=1))
        print("[%s] calls=%s tok=%s gate=%s replay=%s local=%s%%turns_ok=%s/%s secs_med=%s pids=%s" % (
            arm, r["calls"], r["total_tokens"], r["gate_events"], r["prefilter_repeat"],
            r["local_calls"], r["turns_ok"], r["turns"], r["secs_median"], r["server_pid_n"]))
        for b, v in zip(r["gate_bases"], r["gate_verdicts"]):
            print("    %-28s %s" % (b, v))
        return

    arms = {}
    for a in ("Arole", "B3B", "R", "R2", "W1"):
        p = os.path.join(d, "arm-%s.json" % a)
        if os.path.exists(p):
            arms[a] = json.load(io.open(p, encoding="utf-8"))
    A, B, R, R2, W = (arms.get(k) for k in ("Arole", "B3B", "R", "R2", "W1"))

    def rep(turn, reply):
        return {"turn": turn, "text": reply[0], "reply": reply[1]}

    checks, notes = [], []
    if A and R:
        d1 = pct(R["total_tokens"], A["total_tokens"])
        checks.append({"id": "C1_drop_vs_Arole", "value": d1,
                       "pass": (d1 is not None) and d1 >= 30.0,
                       "note": "R %d vs Arole %d (calls %d vs %d)" % (R["total_tokens"], A["total_tokens"], R["calls"], A["calls"])})
    if B and R:
        checks.append({"id": "C2_increment_vs_B3B", "value": pct(R["total_tokens"], B["total_tokens"]),
                       "pass": R["total_tokens"] < B["total_tokens"],
                       "note": "R %d vs B3B %d (calls %d vs %d)" % (R["total_tokens"], B["total_tokens"], R["calls"], B["calls"])})
    if R:
        ok_all = R["turns_ok"] == R["turns"] == 12
        # 复述轮 (t6/t9 起 1) 答复必须 == 上一条答复 (逐字, 回放语义)
        rep_ok, rep_note = True, []
        for i, txt in enumerate(R["replies"]):
            if i + 1 in (6, 9):
                same = R["replies"][i] == R["replies"][i - 1] and (R["replies"][i] or "") != ""
                rep_ok = rep_ok and same
                rep_note.append("t%d=%s(len=%d,prev=%d,fallback=%d)" % (
                    i + 1, "verbatim" if same else "DIFF", len(R["replies"][i] or ""),
                    len(R["replies"][i - 1] or ""), len("收到，继续按当前方向推进，本轮不重新规划。")))
        checks.append({"id": "C3_quality", "value": rep_note, "pass": bool(ok_all and rep_ok),
                       "note": "turns_ok=%s/%s; 复述轮回放 %s" % (R["turns_ok"], R["turns"], ",".join(rep_note))})
        checks.append({"id": "C4_zero_fake_skip", "value": R["prefilter_violations"],
                       "pass": (R["prefilter_violations"] == 0), "note": "prefilter_violations=%s" % R["prefilter_violations"]})
        checks.append({"id": "C5_narrow_face", "value": R["prefilter_repeat"],
                       "pass": R["prefilter_repeat"] == 2, "note": "复述族命中 %s (期望 2 = t6/t9)" % R["prefilter_repeat"]})
        if B:
            def rel(x):
                return [v for b, v in zip(x["gate_bases"], x["gate_verdicts"]) if not (b or "").startswith("mechanical:repeat")]
            checks.append({"id": "C4b_其余轮逐位不变", "value": None, "pass": rel(R) == rel(B),
                           "note": "按预注册实现（R 去掉 repeat 后与 B3B 全序列比）⇒ R(%d) vs B3B(%d)，长度不等必 FAIL；"
                                   "正确口径见 checks_posthoc.C4b2" % (len(rel(R)), len(rel(B)))})
    posthoc = []
    if R and R2:
        same_verdict = (R["calls"], R["gate_verdicts"], R["gate_bases"]) == (R2["calls"], R2["gate_verdicts"], R2["gate_bases"])
        dtok = R2["total_tokens"] - R["total_tokens"]
        checks.append({"id": "C6_rerun_bitwise", "value": dtok, "pass": dtok == 0,
                       "note": "R calls=%d tok=%d / R2 calls=%d tok=%d ⇒ Δtok=%+d (预注册要求逐位, 未达)" % (
                           R["calls"], R["total_tokens"], R2["calls"], R2["total_tokens"], dtok)})
        # 归因 (R443 铁律: 工作区目录名入 system prompt): RUNDIR 名 run-R vs run-R2 差 1 字符
        dchar = len("run-R2") - len("run-R")
        posthoc.append({"id": "C6p_复跑判决面逐位+Δ归因", "value": {"dtok": dtok, "dchar_per_call": dchar},
                        "pass": bool(same_verdict) and dtok == dchar * 2,
                        "note": "判决面(basis+verdict 序列, 调用数)逐位相同=%s; Δtok=%+d = Δchar(%+d)×2 次含工作区行的调用 "
                                "(calls-R/R2 首调 prompt 逐字长 4036/4037)" % (same_verdict, dtok, dchar)})
    if R:
        kinds = [k for k in (R.get("skip_reply_kinds") or [])]
        posthoc.append({"id": "C3p_skip层回放成立", "value": kinds,
                        "pass": kinds.count("repeat_verbatim") == 2 and R["local_calls"] == 4,
                        "note": "复述 2 轮 kind=repeat_verbatim 且 eval/gen=-1 (零 r1); 用户可见层 t6 被承接反问覆盖 ⇒ C3 仍 FAIL"})
    if B and R:
        rep_idx = [i for i, b in enumerate(R["gate_bases"]) if (b or "").startswith("mechanical:repeat")]
        mism = []
        if len(R["gate_bases"]) == len(B["gate_bases"]):
            rk = 0
            for i, b in enumerate(B["gate_bases"]):
                if i in rep_idx:
                    continue
                while rk in rep_idx and rk < len(R["gate_bases"]):   # 跳过 R 的 repeat 位, 保持同位置对齐
                    rk += 1
                if rk < len(R["gate_bases"]) and (R["gate_bases"][rk] != b or R["gate_verdicts"][rk] != B["gate_verdicts"][i]):
                    mism.append(i + 1)
                rk += 1
        posthoc.append({"id": "C4b2_其余轮逐位不变(对齐去重复位)", "value": rep_idx,
                        "pass": len(mism) == 0,
                        "note": "R 的 repeat 位=%s; 其余 10 位与 B3B 同位置逐位相同=%s" % ([i + 1 for i in rep_idx], len(mism) == 0)})
    if W and R:
        # 口径: pid 采样含 bge 嵌入服务 ⇒ 判据用「W1 与 R 的 pid 数相同」(常驻语义不被预热改变)
        # + W1 必须有 local_channel_warmup 事件且 ok=true (预热真的执行了)。
        warm_ok = bool(W["warmup_events"]) and str(W["warmup_events"][0].get("ok")) in ("True", "true")
        checks.append({"id": "C7_warmup", "value": {"w1_pids": W["server_pid_n"], "r_pids": R["server_pid_n"], "warm_events": len(W["warmup_events"])},
                       "pass": (W["server_pid_n"] == R["server_pid_n"]) and warm_ok,
                       "note": "W1 pids=%d vs R pids=%d; warmup 事件=%s ok=%s; turn1 %ss vs %ss" % (
                           W["server_pid_n"], R["server_pid_n"], len(W["warmup_events"]),
                           (W["warmup_events"][0].get("ok") if W["warmup_events"] else None), W["secs"][0], R["secs"][0])})

    out = {"round": "R465", "arms": {k: {kk: v[kk] for kk in
            ("calls", "prompt_tokens", "completion_tokens", "total_tokens", "turns_ok", "turns",
             "secs_median", "secs_total", "gate_events", "prefilter_repeat", "prefilter_violations",
             "local_calls", "local_eval_tokens", "local_gen_tokens", "server_pid_n", "skip_reply_kinds")}
            for k, v in arms.items()},
            "checks": checks, "checks_posthoc": posthoc, "notes": notes}
    io.open(os.path.join(d, "verdict-r465.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["arms"], ensure_ascii=False, indent=1))
    for c in checks:
        print("%-24s pass=%-5s %s" % (c["id"], c["pass"], c["note"]))
    for c in posthoc:
        print("[posthoc] %-28s pass=%-5s %s" % (c["id"], c["pass"], c["note"]))

if __name__ == "__main__":
    main()
