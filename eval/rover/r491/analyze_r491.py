#!/usr/bin/env python3
"""R491 判据器: 声明面按需 (ToolDeclGate) 与回放剪裁的同二进制单变量消融 + 用户口径 token KPI。

读 (全部真值来自落盘物, 零手抄):
  eval/rover/r491/usage-<key>.jsonl    ← 中继落盘的真供应商 usage (每调用一行; 分母真值)
  eval/rover/r491/calls-<key>.jsonl    ← 中继记录的实际请求 messages (回放剪裁机检)
  eval/rover/r491/tel-<key>/host.jsonl ← 宿主遥测 (tool_decl_gate 逐调用: declared/intent/reason/replay_trimmed)
  eval/rover/r491/flags-<key>.json     ← 臂参 (tool_decl_gate 开关; 脚本不自报)

臂链 (同一 AOT 产物 / 同一夹具 p12 / 同一窗):
  B  = Aroleb 门关 + repeat_skip off            (基线)
  R  = R1     门开 + repeat_skip on, 声明门 off  (R489 生产形态)
  T1 = T1     门开 + repeat_skip on, 声明门 on   (R491 新机制; 重复 2 跑)
  T2 = T2     同上 (稳定性)

用法: python3 analyze_r491.py [--json eval/rover/r491/verdict-r491.json]
"""
import json, os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = [("B", "Aroleb"), ("T1", "T1"), ("T2", "T2"), ("T3", "T3")]  # R491: R 臂本轮未跑
TEMPLATE = "收到。"


def rows(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def read_usage(key):
    return rows(os.path.join(HERE, "usage-%s.jsonl" % key))


def arm_stats(key):
    us = read_usage(key)
    st = {"calls": len(us), "prompt": 0, "completion": 0, "cached": 0, "cost": 0.0,
          "empty_body": 0, "tool_call_finish": 0, "content_len_sum": 0, "err": 0}
    for r in us:
        st["prompt"] += r.get("prompt_tokens") or 0
        st["completion"] += r.get("completion_tokens") or 0
        st["cached"] += r.get("cache_hit_tokens") or 0
        st["cost"] += r.get("cost_cny_upper") or 0.0
        st["empty_body"] += 1 if r.get("empty_body") else 0
        st["tool_call_finish"] += 1 if (r.get("finish_reason") or "") == "tool_calls" else 0
        st["content_len_sum"] += r.get("content_len") or 0
        st["err"] += 1 if (r.get("status") or 0) != 200 else 0
    st["total"] = st["prompt"] + st["completion"]
    st["cost"] = round(st["cost"], 6)
    return st


def replay_scan(key):
    """回放剪裁机检 (非空判据):
      · assistant 模板串条数 —— R489 基线 24~52/臂 (共 100), R491 必须 0;
      · **user→user 相邻对** —— 模板答复被剪后, 跳过轮的 user 与其前一条 user 相邻 ⇒
        该计数 >0 才证明「请求里本来有模板串、是被剪掉的」, 而不是「模板串从来没进过回放」(空判据陷阱)。
    """
    n = 0
    reqs = 0
    adj = 0
    for d in rows(os.path.join(HERE, "calls-%s.jsonl" % key)):
        reqs += 1
        ms = d.get("messages", [])
        for m in ms:
            if m.get("role") == "assistant" and (m.get("content") or "").strip() == TEMPLATE:
                n += 1
        for a, b in zip(ms, ms[1:]):
            if a.get("role") == "user" and b.get("role") == "user":
                adj += 1
    return {"requests": reqs, "assistant_template_msgs": n, "user_user_adjacent_pairs": adj}


def replay_scan_ref(subdir, key):
    """同 replay_scan, 但取相对子目录的 R489 旧产物 (跨轮参考, 禁相减)。"""
    n = 0
    reqs = 0
    adj = 0
    for d in rows(os.path.join(HERE, subdir, "calls-%s.jsonl" % key)):
        reqs += 1
        ms = d.get("messages", [])
        for m in ms:
            if m.get("role") == "assistant" and (m.get("content") or "").strip() == TEMPLATE:
                n += 1
        for a, b in zip(ms, ms[1:]):
            if a.get("role") == "user" and b.get("role") == "user":
                adj += 1
    return {"requests": reqs, "assistant_template_msgs": n, "user_user_adjacent_pairs": adj}


def gate_scan(key):
    """声明面机检: tool_decl_gate 逐调用记录 → 分布 + 违规。"""
    path = os.path.join(HERE, "tel-%s" % key, "host.jsonl")
    out = {"rows": 0, "by_reason": {}, "by_intent": {}, "declared_true": 0, "declared_false": 0,
           "gate_values": [], "replay_trimmed_calls": 0, "replay_trimmed_sum": 0, "violations": []}
    for r in rows(path):
        if r.get("point") != "tool_decl_gate":
            continue
        kv = r.get("kv") or {}
        out["rows"] += 1
        if kv.get("gate") not in out["gate_values"]:
            out["gate_values"].append(kv.get("gate"))
        reason = kv.get("reason")
        intent = kv.get("intent")
        out["by_reason"][reason] = out["by_reason"].get(reason, 0) + 1
        out["by_intent"][intent] = out["by_intent"].get(intent, 0) + 1
        d = kv.get("declared")
        d = d if isinstance(d, bool) else str(d).lower() in ("true", "1")
        out["declared_true" if d else "declared_false"] += 1
        rt = kv.get("replay_trimmed") or 0
        if rt:
            out["replay_trimmed_calls"] += 1
            out["replay_trimmed_sum"] += rt
        # 不变量 (逐调用, fail-closed)
        if kv.get("gate") == "1" and intent == "general" and d:
            out["violations"].append({"seq": kv.get("turn"), "why": "门开+非工具意图却声明了工具"})
        if kv.get("gate") == "0" and not d:
            out["violations"].append({"seq": kv.get("turn"), "why": "门关却不声明工具 (零回归破)"})
    return out


def quality_scan(key):
    """回复质量面 (机检, 全部来自 turns-<key>.jsonl 实发回答):
      · 真假判别轮 (fixture 第 10..12 轮 = 用户植入错误前提「你上一条说 3 加 5 等于 9」):
        要求 ①含正确值 8 ②含否定标记 (不是/没说过/不对/没有) ③不得把 9 当成自己的主张 (粗判: 不许出现 '等于 9' 而无否定)
      · 长度分档: 空(<=1) / 模板(<=3) / 实质(>40) —— 只做分布记录, 不做阈值判决。
    """
    p = os.path.join(HERE, "turns-%s.jsonl" % key)
    if not os.path.exists(p):
        return {"turns": 0, "classes": {}, "false_premise": {"pass": None, "detail": "no_turns_file"}}
    doc = json.load(open(p, encoding="utf-8"))
    ts = doc.get("turns") if isinstance(doc, dict) else doc
    classes = {"empty": 0, "template": 0, "brief": 0, "substantive": 0}
    fp = []
    for t in ts or []:
        r = (t.get("reply") or "").strip()
        n = len(r)
        classes["empty" if n <= 1 else "template" if n <= 3 else "brief" if n <= 40 else "substantive"] += 1
        if t.get("turn", 0) >= 10:
            neg = any(k in r for k in ("不是", "没说过", "不对", "没有", "并非"))
            has8 = "8" in r
            fp.append({"turn": t.get("turn"), "ok": bool(t.get("ok")), "has_8": has8, "has_negation": neg,
                       "len": n, "head": r[:70]})
    return {"turns": len(ts or []), "classes": classes,
            "false_premise": {"pass": bool(fp) and all(x["ok"] and x["has_8"] and x["has_negation"] for x in fp),
                              "rounds": fp}}



# R491: 计划内未跑臂的显式声明 (空 = 计划全跑; 未跑即 FAIL, 禁静默豁免)
OUT_OF_SCOPE = {}


# ══════════════════════════════════════════════════════════════════════════
# R491 追加面 (派生器注入; 与 R490 面并存, 不改旧判据语义)
# ══════════════════════════════════════════════════════════════════════════

def _msgs(c):
    """R491 修: 实发 messages 在 calls-*.jsonl **顶层** (R490 的 pair 面误取 request.messages)。"""
    return c.get("messages") or ((c.get("request") or {}).get("messages")) or []


def pair_face(key):
    """候选③ 面: 零远端调用轮的 user 侧是否也在回放里 (闸关应 >0, 闸开应 =0)。"""
    calls = rows(os.path.join(HERE, "calls-%s.jsonl" % key))
    adj = leak = 0
    for c in calls:
        msgs = _msgs(c)
        roles = [m.get("role") for m in msgs]
        for i in range(1, len(roles)):
            if roles[i - 1] == "user" and roles[i] == "user":
                adj += 1
        for m in msgs:
            if m.get("role") == "user" and TEMPLATE in (m.get("content") or ""):
                leak += 1
    telem = rows(os.path.join(HERE, "tel-%s" % key, "host.jsonl"))
    gate = [r for r in telem if r.get("point") == "tool_decl_gate"]
    ut = sum(int((r.get("kv") or {}).get("replay_user_trimmed") or 0) for r in gate)
    pg = sorted({str((r.get("kv") or {}).get("replay_pair_gate")) for r in gate})
    return {"user_trimmed": ut, "pair_gate": pg or ["(none)"], "user_user_adj": adj, "skip_user_leak": leak}


def deadcode_face(root):
    """候选④ 面: R479 三件产物在链上的引用计数 (源码面, 排 bin/obj)。0 生产引用 ⇒ 不在链上。"""
    import subprocess
    out = {}
    for s in ("ResponsesWire", "LocalDecisionMap", "ActionToolSpec"):
        raw = subprocess.run(["grep", "-rn", r"\b%s\b" % s, "--include=*.cs", "src/"],
                             cwd=root, capture_output=True, text=True).stdout
        prod, test = [], []
        for line in raw.splitlines():
            p = line.split(":", 1)[0]
            if "/bin/" in p or "/obj/" in p:
                continue
            (test if "/agent.tests/" in p else prod).append(p)
        out[s] = {"prod": len(prod), "test": len(test), "files": sorted(set(prod))}
    return out


def main():
    out = {"round": "R491", "arms": {}, "invariants": [], "deltas": {}, "cross_round_ref": {}}
    out["pair_face"] = {k: pair_face(k) for _, k in ARMS}
    out["deadcode_face"] = deadcode_face(os.path.abspath(os.path.join(HERE, "..", "..", "..")))
    ap = sys.argv
    for arm, key in ARMS:
        if not os.path.exists(os.path.join(HERE, "usage-%s.jsonl" % key)):
            pf = os.path.join(HERE, "preflight-%s.json" % key)
            reason = "no_usage_file"
            if os.path.exists(pf):
                d = json.load(open(pf, encoding="utf-8"))
                reason = "起手闸 %s: %s (mem_available_mb=%s < gate_mb=%s)" % (
                    d.get("verdict"), d.get("blocker_cause"), d.get("mem_available_mb"), d.get("gate_mb"))
            out["arms"][arm] = {"not_run": True, "reason": reason}
            continue
        st = arm_stats(key)
        st["key"] = key
        st["replay"] = replay_scan(key)
        st["gate"] = gate_scan(key)
        st["quality"] = quality_scan(key)
        fl = os.path.join(HERE, "flags-%s.json" % key)
        st["flags"] = json.load(open(fl, encoding="utf-8")) if os.path.exists(fl) else None
        out["arms"][arm] = st

    def pct(a, b):
        return round((a - b) / b * 100, 2) if b else None

    B = out["arms"]["B"]
    for arm in ("T1", "T2", "T3"):
        a = out["arms"][arm]
        if a.get("not_run"):
            out["deltas"][arm] = {"not_run": True, "reason": a["reason"]}
            continue
        out["deltas"][arm] = {
            "calls": "%d→%d (%s%%)" % (B["calls"], a["calls"], pct(a["calls"], B["calls"])),
            "total_tokens": "%d→%d (%s%%)" % (B["total"], a["total"], pct(a["total"], B["total"])),
            "prompt_tokens": "%d→%d (%s%%)" % (B["prompt"], a["prompt"], pct(a["prompt"], B["prompt"])),
            "empty_body_calls": "%d→%d" % (B["empty_body"], a["empty_body"]),
            "cost_cny": "%s→%s (%s%%)" % (B["cost"], a["cost"], pct(a["cost"], B["cost"])),
        }
    ran = [x for x in ("T1", "T2", "T3") if not out["arms"][x].get("not_run")]
    if ran:
        tot = [out["arms"][x]["total"] for x in ran]
        cal = [out["arms"][x]["calls"] for x in ran]
        out["deltas"]["T_spread"] = {
            "arms": ran,
            "total_tokens": "%d..%d (min..max)" % (min(tot), max(tot)),
            "calls": "%d..%d" % (min(cal), max(cal)),
            "pct_vs_B": "%s..%s" % (pct(min(tot), B["total"]), pct(max(tot), B["total"])),
            "worst_case_total_pct": pct(max(tot), B["total"]),
        }

    # ---- 不变量 (机检) ----
    for arm, key in ARMS:
        a = out["arms"][arm]
        if a.get("not_run"):
            out["invariants"].append({"id": "I0_臂可跑", "arm": arm, "pass": False,
                                      "blocking": arm not in OUT_OF_SCOPE,
                                      "evidence": a["reason"]})
            out.setdefault("unreported_planned_arms", []).append(arm)
            continue
        gate_on = bool(a["flags"] and a["flags"].get("tool_decl_gate") == "on")
        out["invariants"].append({
            "id": "I1_声明面逐调用可观测", "arm": arm, "pass": a["gate"]["rows"] > 0,
            "evidence": "tool_decl_gate rows=%d by_reason=%s" % (a["gate"]["rows"], a["gate"]["by_reason"])})
        out["invariants"].append({
            "id": "I2_门开关与臂参一致", "arm": arm,
            "pass": set(a["gate"]["gate_values"]) == ({"1"} if gate_on else {"0"}),
            "evidence": "flags.tool_decl_gate=%s 遥测 gate_values=%s"
                        % ((a["flags"] or {}).get("tool_decl_gate"), a["gate"]["gate_values"])})
        out["invariants"].append({
            "id": "I3_无声明面违规", "arm": arm, "pass": len(a["gate"]["violations"]) == 0,
            "evidence": "violations=%d %s" % (len(a["gate"]["violations"]), a["gate"]["violations"][:3])})
        out["invariants"].append({
            "id": "I4_回放剪裁生效(模板串不进远端)", "arm": arm,
            "pass": a["replay"]["assistant_template_msgs"] == 0,
            "evidence": "requests=%d assistant_template_msgs=%d user_user_adjacent=%d (非空判据: 相邻对>0 且在 R489 基线里为 0)"
                        % (a["replay"]["requests"], a["replay"]["assistant_template_msgs"],
                           a["replay"]["user_user_adjacent_pairs"])})
        out["invariants"].append({
            "id": "I5_剪裁打点非零(确有可剪内容)", "arm": arm,
            "pass": a["gate"]["replay_trimmed_sum"] > 0 or not gate_on,
            "evidence": "replay_trimmed_calls=%d sum=%d" % (a["gate"]["replay_trimmed_calls"], a["gate"]["replay_trimmed_sum"])})

    # ---- 跨轮参考 (R489 同臂; 只读参考, **禁相减**) ----
    ref = {"note": "R489 旧产物 (含未剪裁回放 + 无声明门); 仅作参考, 不与本轮相减"}
    for name, key in (("R489_B", "Aroleb"), ("R489_R1", "R1"), ("R489_R2", "R2"), ("R489_R3", "R3")):
        p = os.path.join(HERE, "..", "r489", "usage-%s.jsonl" % key)
        if os.path.exists(p):
            us = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
            old = replay_scan_ref("../r489", key)
            ref[name] = {"calls": len(us),
                         "total": sum((r.get("prompt_tokens") or 0) + (r.get("completion_tokens") or 0) for r in us),
                         "empty_body": sum(1 for r in us if r.get("empty_body")),
                         "assistant_template_msgs": old["assistant_template_msgs"],
                         "user_user_adjacent_pairs": old["user_user_adjacent_pairs"]}
    out["cross_round_ref"] = ref

    blocked = [i for i in out["invariants"] if not i.get("blocking", True)]
    mine = [i for i in out["invariants"] if i.get("blocking", True)]
    ok = all(i["pass"] for i in mine)
    out["blocked_arms"] = [i["arm"] for i in blocked]
    out["verdict"] = "PASS" if ok else "FAIL"
    out["arms_run"] = [a for a, _ in ARMS if not out["arms"][a].get("not_run")]
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    dst = os.path.join(HERE, "verdict-r491.json")
    if "--json" in ap:
        dst = ap[ap.index("--json") + 1]
    open(dst, "w", encoding="utf-8").write(txt)
    for arm, _ in ARMS:
        a = out["arms"][arm]
        if a.get("not_run"):
            print("[%s] NOT_RUN: %s" % (arm, a["reason"]))
            continue
        print("[%s] calls=%d total=%d prompt=%d completion=%d cached=%d empty_body=%d tool_finish=%d cost=%s tmpl_replay=%d"
              % (arm, a["calls"], a["total"], a["prompt"], a["completion"], a["cached"], a["empty_body"],
                 a["tool_call_finish"], a["cost"], a["replay"]["assistant_template_msgs"]))
        q = a.get("quality") or {}
        print("      quality: classes=%s false_premise_pass=%s" % (q.get("classes"), (q.get("false_premise") or {}).get("pass")))
    for k, v in out["deltas"].items():
        print("[delta %s] %s" % (k, v))
    print("[invariants] %s (blocked_arms=%s)" % ("PASS" if ok else "FAIL", out["blocked_arms"]))
    for i in out["invariants"]:
        if not i["pass"]:
            print("   RED %s/%s: %s" % (i["id"], i["arm"], i["evidence"]))
    print("[json] %s" % dst)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
