#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R467 分母可比性闸 (fail-closed) —— 判定「某臂读数能否当分母 / 能否与基线同题对比」。

动机 (R465→R466 真实事故): 同名臂 `Arole` 在两轮之间 relation_judge 由 false 变 true,
分母 21/33,323 静默变成 13/32,097, 台账里**没有路由字段** ⇒ 一整轮无人察觉,
任何以该分母计的降幅都可能不可比。本闸把「同名 ⇒ 标志必须逐键同」做成机检。

G1 分解恒等式:  calls == main + judge_remote + micro + other ∧ judge(calls) == remote_real + remote_fallback
G2 内外一致:    calls(桩侧外部真值) == llm_call 事件数(宿主遥测自报)
G3 路由干净:    relation_judge=true  ⇒ remote_fallback==0 ∧ local>0 ∧ remote_real==0
                relation_judge=false ⇒ local==0 ∧ remote_real>0  (「真走本地」不得含静默远端兜底)
G4 跨轮可比:    同名臂 ⇒ 两侧共同声明键逐键必须相同 (不同 ⇒ 红 = 分母漂移);
                异名同类 ⇒ 同样规则 (合法的重命名); 异名异类 ⇒ NA (拒绝背书, 不判红);
                仅一侧声明的键 ⇒ undeclared 列入 info (不可核 ≠ 相同, 但也不冒充实测);
                器具差异 (二进制 sha / 配置 sha / cwd 字面) ⇒ info, 不判红 (优化轮的独立变量)
G5 声明完备:    本轮台账必须声明全部行为键 (缺一 ⇒ 红): fail-closed, 未声明不得回退默认。

用法:
  python3 denominator_gate.py --baseline <ledger.json|arm-*.json> --arm <...> [--json out.json]
  python3 denominator_gate.py --selftest [--dir <round dir>]
退出码: 0=绿; 3=红; 4=用法错。
"""
import io, json, os, re, sys

BEHAVIOR_KEYS = ["turn_gate", "relation_judge", "repeat_skip", "repeat_priority", "warmup",
                 "gpu_layers", "context_size", "parallel", "max_tokens", "max_prompt_tokens",
                 "allow_general", "model_path", "allowed_kinds", "grid", "role_sha256"]
INSTRUMENT_KEYS = ["host_bin", "host_sha256", "config_sha256", "rundir_cwd"]
NORM = {"(unset=on)": "on", "(unset=off)": "off", "(unset)": "unset", "1": "on", "0": "off",
        "true": "true", "false": "false"}
HERE = os.path.dirname(os.path.abspath(__file__))


def arm_class_of(flags):
    """臂类别的唯一来源 (settle_r467 直接 import 本函数 —— 禁止两处各写一份)。
    gate_off_judge_remote = r1 接入前的历史管道 (KPI 分母应取此类)
    gate_off_judge_local  = 仅判官本地化 (单变量对照)
    gate_on_judge_local   = 生产等价 (门 + 判官本地化, repeat_skip 随生产默认)"""
    f = flags or {}
    g = str(f.get("turn_gate") or "").lower()
    rj = str(f.get("relation_judge") or "").lower()
    rs = str(f.get("repeat_skip") or "")
    if g == "true" and rj == "true":
        return "gate_on_judge_local(repeat_skip=%s)" % rs
    if g == "false" and rj == "true":
        return "gate_off_judge_local"
    if g == "false" and rj == "false":
        return "gate_off_judge_remote(pre_r1_baseline)"
    if g == "true" and rj == "false":
        return "gate_on_judge_remote(repeat_skip=%s)" % rs
    return "undeclared(turn_gate=%r,relation_judge=%r)" % (f.get("turn_gate"), f.get("relation_judge"))


def norm(v):
    if v is None:
        return None
    return NORM.get(str(v), str(v))


def jload(p):
    return json.load(io.open(p, encoding="utf-8"))


def to_ledger(o):
    """接受 ledger-*.json 或 arm-*.json (旧 arm-*.json 无分解字段 ⇒ 相关检查计未声明)。"""
    if "identity" in o and "flags" in o:
        return o
    return {"round": o.get("round"), "arm": o.get("arm"), "arm_class": None, "flags": {},
            "calls": o.get("calls"), "total_tokens": o.get("total_tokens"),
            "turns": o.get("turns"), "turns_ok": o.get("turns_ok"),
            "calls_class": o.get("calls_class"), "judge_route": o.get("judge_route"),
            "judge_calls_tokens": o.get("judge_calls_tokens"), "remote_llm_events": o.get("remote_llm_events"),
            "identity": o.get("identity"), "gate_events": o.get("gate_events"), "local_calls": o.get("local_calls")}


def g1(L):
    c, jr = L.get("calls_class"), L.get("judge_route") or {}
    if not c or not L.get("calls"):
        return {"id": "G1_identity", "pass": False, "reason": "未声明 calls_class (旧臂 JSON) ⇒ fail-closed 红",
                "value": {"calls": L.get("calls"), "calls_class": c}}
    rhs = c["main"] + c["judge"] + c["micro"] + c["other"]
    jm = (c["judge"] == (jr.get("remote_real", 0) + jr.get("remote_fallback", 0)))
    return {"id": "G1_identity", "pass": bool(rhs == L["calls"] and jm),
            "value": {"calls": L["calls"], "rhs": rhs, "judge_calls": c["judge"],
                      "route_remote": jr.get("remote_real", 0) + jr.get("remote_fallback", 0)},
            "reason": "恒等式 %s=%s 且 judge 调用两侧一致=%s" % (L["calls"], rhs, jm)}


def g2(L):
    if L.get("remote_llm_events") is None:
        return {"id": "G2_internal_external", "pass": False, "reason": "未声明 remote_llm_events ⇒ fail-closed 红", "value": {}}
    ok = L["calls"] == L["remote_llm_events"]
    return {"id": "G2_internal_external", "pass": bool(ok),
            "value": {"calls_stub": L["calls"], "llm_call_events": L["remote_llm_events"]},
            "reason": "桩侧 %s == 宿主遥测 %s" % (L["calls"], L["remote_llm_events"])}


def g3(L):
    jr = L.get("judge_route") or {}
    f = L.get("flags") or {}
    rj = norm(f.get("relation_judge"))
    if not jr or rj is None:
        return {"id": "G3_route_clean", "pass": False, "reason": "路由或 relation_judge 未声明 ⇒ fail-closed 红",
                "value": {"relation_judge": rj, "judge_route": jr or None}}
    if rj == "true":
        ok = (jr.get("remote_fallback", 0) == 0) and (jr.get("local", 0) > 0) and (jr.get("remote_real", 0) == 0)
        why = "rj=true ⇒ local=%s>0 ∧ remote_real=%s==0 ∧ remote_fallback=%s==0" % (
            jr.get("local"), jr.get("remote_real"), jr.get("remote_fallback"))
    else:
        ok = (jr.get("local", 0) == 0) and (jr.get("remote_real", 0) > 0)
        why = "rj=false ⇒ local=%s==0 ∧ remote_real=%s>0" % (jr.get("local"), jr.get("remote_real"))
    return {"id": "G3_route_clean", "pass": bool(ok),
            "value": {"relation_judge": rj, **{k: jr.get(k) for k in ("events", "local", "shortcircuit", "remote_real", "remote_fallback")}},
            "reason": why}


def g5(L):
    f = L.get("flags") or {}
    if not f or f.get("origin", "").startswith("reconstructed"):
        return {"id": "G5_declaration_complete", "pass": True, "applicable": False,
                "value": {"origin": f.get("origin")}, "reason": "历史重建台账不适用 (仅约束本轮台账)"}
    miss = [k for k in BEHAVIOR_KEYS if not f.get(k)]
    return {"id": "G5_declaration_complete", "pass": not miss, "value": {"missing": miss},
            "reason": "本轮台账行为键 %d/%d 已声明; 缺=%s" % (len(BEHAVIOR_KEYS) - len(miss), len(BEHAVIOR_KEYS), miss or "无")}


def g4(base, arm):
    fb = {k: norm(v) for k, v in (base.get("flags") or {}).items()}
    fa = {k: norm(v) for k, v in (arm.get("flags") or {}).items()}
    cb, ca = base.get("arm_class"), arm.get("arm_class")
    same_name = (base.get("arm") == arm.get("arm")) and base.get("arm") is not None
    same_class = bool(cb and ca and cb == ca)
    applicable = bool(same_name or same_class)
    diffs, undeclared = {}, {}
    for k in BEHAVIOR_KEYS:
        vb, va = fb.get(k), fa.get(k)
        nb, na = vb in (None, "", "None"), va in (None, "", "None")
        if nb and na:
            undeclared[k] = ["<未声明>", "<未声明>"]
        elif nb or na:
            undeclared[k] = [vb if not nb else "<未声明>", va if not na else "<未声明>"]
        elif vb != va:
            diffs[k] = [vb, va]
    info = {k: [fb.get(k), fa.get(k)] for k in INSTRUMENT_KEYS if fb.get(k) != fa.get(k)}
    mode = "同名臂(必须逐键同)" if same_name else ("异名同类(合法重命名)" if same_class else "异名异类")
    return {"id": "G4_cross_round_comparable", "pass": bool(applicable and not diffs),
            "applicable": applicable,
            "value": {"mode": mode, "same_name": same_name, "same_class": same_class,
                      "baseline_class": cb, "arm_class": ca, "diffs": diffs,
                      "undeclared": undeclared, "instrument_info": info},
            "reason": "%s ⇒ 可比=%s; 标志差异=%s; 仅一侧声明=%s; 器具差异(不判红)=%s" % (
                mode, applicable and not diffs, diffs or "无", undeclared or "无", info or "无")}


def run_gate(base, arm):
    checks = [g1(arm), g2(arm), g3(arm), g5(arm), g4(base, arm)]
    red = [c["id"] for c in checks if not c["pass"]]
    if red:
        verdict = "VOID_NOT_COMPARABLE"
    elif not checks[4].get("applicable", True):
        verdict = "NA_NOT_SAME_DENOMINATOR"
    else:
        verdict = "OK_COMPARABLE"
    return {"baseline_arm": base.get("arm"), "baseline_round": base.get("round"),
            "arm": arm.get("arm"), "arm_round": arm.get("round"),
            "verdict": verdict, "red": red, "checks": checks,
            "delivered_calls": arm.get("calls"), "delivered_tokens": arm.get("total_tokens")}


# ---------------- 真实历史台账重建 (外部对照; 机器派生自该轮真实产物, 非手写) ----------------
def _arm_line(sh, arm):
    for m in re.finditer(r"(?m)^\s*([A-Za-z0-9\|]+)\)\s*(.*)$", sh):
        alts = [a.strip() for a in m.group(1).split("|")]
        if arm in alts:
            return m.group(2)
    return ""


def recon(round_name, arm="Arole"):
    """从该轮**真实产物**重建台账: arm-*.json(读数) + calls-*.jsonl(桩) + 遥测(路由) + run_arm.sh(标志)。"""
    d = os.path.join(HERE, "..", round_name)
    a = jload(os.path.join(d, "arm-%s.json" % arm))
    calls = [json.loads(l) for l in io.open(os.path.join(d, "calls-%s.jsonl" % arm), encoding="utf-8") if l.strip()]
    cls = {"main": 0, "judge": 0, "micro": 0, "other": 0}
    jpt = jct = 0
    for c in calls:
        lu = ""
        for m in reversed(c.get("messages") or []):
            if m.get("role") == "user":
                lu = m.get("content") or ""
                break
        if lu.startswith("判定用户消息相对上一轮回答"):
            cls["judge"] += 1
            jpt += int(c.get("prompt_tokens_est") or 0)
            jct += int(c.get("completion_tokens_est") or 0)
        elif lu.startswith("[微步骤隔离问询]"):
            cls["micro"] += 1
        elif lu:
            cls["main"] += 1
        else:
            cls["other"] += 1
    tel = os.path.join(d, "run-%s" % arm, "data", "telemetry", "host.jsonl")
    if not os.path.exists(tel):
        tel = os.path.join(d, "rundata-%s" % arm, "data", "telemetry", "host.jsonl")
    jev, lln = [], 0
    for l in io.open(tel, encoding="utf-8"):
        if '"correction_judge"' in l:
            jev.append((json.loads(l).get("kv") or {}))
        if '"llm_call"' in l:
            lln += 1
    src = lambda j: j.get("source") or ""
    jr = {"events": len(jev), "local": sum(1 for j in jev if src(j) == "local"),
          "shortcircuit": sum(1 for j in jev if src(j) == "remote" and int(j.get("prompt_len") or 0) == 0),
          "remote_real": sum(1 for j in jev if src(j) == "remote" and int(j.get("prompt_len") or 0) > 0),
          "remote_fallback": sum(1 for j in jev if src(j).startswith("remote_fallback"))}
    sh = io.open(os.path.join(d, "run_arm.sh"), encoding="utf-8").read()
    line = _arm_line(sh, arm)
    def rgx(pat, s):
        m = re.search(pat, s)
        return m.group(1) if m else None
    def tmpl(k):
        m = re.search(r"(?m)^\s*%s:\s*(\S+)" % k, sh)
        v = m.group(1) if m else None
        if v and "{" in v:  # 模板占位 (如 {model}) ⇒ 沿脚本真实变量链解析 (MP=$M3B ⇒ M3B=...)
            m2 = re.search(r"MP=\$?(\w+)", line)
            if m2:
                cand = rgx(r"(?m)^\s*%s=(\S+)" % m2.group(1), sh)
                v = cand if cand and os.path.isabs(cand) else v
        return v
    role = rgx(r"ROLE_GROWTH=(\S+)", sh)
    import hashlib
    rsha = hashlib.sha256(open(role, "rb").read()).hexdigest() if role and os.path.exists(role) else None
    L = {"round": round_name, "arm": arm, "arm_class": None,
         "flags": {"turn_gate": norm(rgx(r"GATE=(\w+)", line)), "relation_judge": norm(rgx(r"RJ=(\w+)", line)),
                   "repeat_skip": rgx(r"RS=(\w+)", line), "repeat_priority": norm(rgx(r"PRIO=(\w+)", line)),
                   "warmup": norm(rgx(r"WARM=(\w+)", line)), "gpu_layers": tmpl("gpu_layers"),
                   "context_size": tmpl("context_size"), "parallel": tmpl("parallel"),
                   "max_tokens": tmpl("max_tokens"), "max_prompt_tokens": tmpl("max_prompt_tokens"),
                   "allow_general": tmpl("allow_general"), "model_path": tmpl("model_path"),
                   "allowed_kinds": (re.search(r"(?m)^\s*allowed_kinds:\s*(.+)$", sh) or [None, None])[1],
                   "grid": (rgx(r"GRID=(\w+)", sh) or "p12"), "role_sha256": rsha,
                   "rundir_cwd": "eval/rover/%s/run-%s" % (round_name, arm),
                   "origin": "reconstructed_from_%s_artifacts" % round_name},
         "calls": a["calls"], "total_tokens": a["total_tokens"], "prompt_tokens": a["prompt_tokens"],
         "completion_tokens": a["completion_tokens"], "turns": a["turns"], "turns_ok": a["turns_ok"],
         "calls_class": cls, "judge_route": jr, "remote_llm_events": lln,
         "judge_calls_tokens": {"prompt": jpt, "completion": jct, "total": jpt + jct},
         "gate_events": a.get("gate_events"), "local_calls": a.get("local_calls")}
    L["identity"] = {"pass": (cls["main"] + cls["judge"] + cls["micro"] + cls["other"]) == a["calls"]}
    L["arm_class"] = arm_class_of(L["flags"])
    return L


def selftest(d):
    cases = []
    p = os.path.join(d, "ledger-Arole.json")
    if not os.path.exists(p):
        print("缺 %s ⇒ 先跑臂" % p)
        return 4
    cur = to_ledger(jload(p))
    # S1 真实历史负控: 同名臂 Arole, r465(RJ=false) 当 r467(RJ=true) 的分母 ⇒ 必须红 (真事故复现)
    r1 = run_gate(recon("r465", "Arole"), cur)
    cases.append({"id": "S1_real_drift_r465_Arole_vs_r467_Arole", "expect": "RED", "got": r1["verdict"],
                  "pass": r1["verdict"] == "VOID_NOT_COMPARABLE", "detail": r1["checks"][4]["reason"]})
    # S2 构造负控: 破坏恒等式 (calls+1) ⇒ G1 必须红
    doc = json.loads(json.dumps(cur))
    doc["calls"] = (doc["calls"] or 0) + 1
    r2 = run_gate(cur, doc)
    cases.append({"id": "S2_doctored_identity", "expect": "RED", "got": r2["verdict"],
                  "pass": r2["verdict"] == "VOID_NOT_COMPARABLE", "detail": r2["checks"][0]["reason"]})
    # S3 正控: 同名臂, 只有器具 sha 变化 ⇒ 必须绿 (不把二进制换代误判成分母漂移)
    twin = json.loads(json.dumps(cur))
    twin["arm"] = cur["arm"]
    twin["arm_class"] = cur["arm_class"]
    for k in INSTRUMENT_KEYS:
        twin["flags"][k] = "different_" + str(twin["flags"].get(k))
    r3 = run_gate(cur, twin)
    cases.append({"id": "S3_instrument_only_diff_must_pass", "expect": "GREEN", "got": r3["verdict"],
                  "pass": r3["verdict"] == "OK_COMPARABLE",
                  "detail": "器具差异=%s (不判红)" % r3["checks"][4]["value"]["instrument_info"]})
    out = {"cases": cases, "all_pass": all(c["pass"] for c in cases),
           "summary": "%d/%d 通过 (%s)" % (sum(1 for c in cases if c["pass"]), len(cases),
                                           "; ".join("%s→%s" % (c["id"].split("_")[0], c["got"]) for c in cases))}
    io.open(os.path.join(d, "gate-selftest.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["all_pass"] else 3


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest(args[args.index("--dir") + 1] if "--dir" in args else HERE))
    if "--baseline" not in args or "--arm" not in args:
        print(__doc__)
        sys.exit(4)
    base = to_ledger(jload(args[args.index("--baseline") + 1]))
    arm = to_ledger(jload(args[args.index("--arm") + 1]))
    res = run_gate(base, arm)
    if "--json" in args:
        io.open(args[args.index("--json") + 1], "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: res[k] for k in ("baseline_arm", "arm", "verdict", "red", "delivered_calls", "delivered_tokens")}, ensure_ascii=False))
    for c in res["checks"]:
        print("%-32s pass=%-5s %s" % (c["id"], c["pass"], c.get("reason", "")))
    sys.exit(0 if res["verdict"] != "VOID_NOT_COMPARABLE" else 3)


if __name__ == "__main__":
    main()
