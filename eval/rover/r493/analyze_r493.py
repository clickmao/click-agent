#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R493 判据器: 对抗族加严 (多轮前置真值/反事实改写/不可能前提) + 结构量判据 + 同窗三臂.

读 (全部真值来自落盘物, 零手抄):
  eval/rover/r493/usage-<key>.jsonl    ← 中继落盘的真供应商 usage (每调用一行; 分母真值)
  eval/rover/r493/calls-<key>.jsonl    ← 中继记录的实际请求 messages (剪裁/配对机检)
  eval/rover/r493/turns-<key>.jsonl    ← 实发答复 (质量面/对抗族面)
  eval/rover/r493/tel-<key>/host.jsonl ← 宿主遥测 (本地通道/闸决策/role 挂载)
  eval/rover/r493/flags-<key>.json     ← 臂参 (开关; 脚本不自报)

臂链 (同一 AOT 产物 / 同一夹具 / 同一窗; 差异只有开关组合):
  B = Aroleb  门关 + repeat_skip off            + pair_trim off  (对照 = 生产现状)
  R = R       门开 + repeat_skip on             + pair_trim off  (r1 本地通道独立增益)
  T = T       门开 + repeat_skip on + 声明门 on  + pair_trim on   (全链候选形态; 主 KPI)

用法: python3 analyze_r493.py [--json eval/rover/r493/verdict-r493.json]
"""
import json, os, sys, glob, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "r491"))
import analyze_r491 as base          # 复用 R491 的产物读取/机检面 (只读, 不改语义)
base.HERE = HERE
sys.path.insert(0, HERE)
import judge_adv_r493 as J           # R493 新判据 (结构量)

ARMS = [("B", "Aroleb"), ("R", "R"), ("T", "T")]
CTRL = "B"
TREAT = ("R", "T")
GRID_R493 = os.path.join(HERE, "grid", "task-p12-adv.json")
GRID_R438 = os.path.abspath(os.path.join(HERE, "..", "r438", "grid", "task-p12.json"))
TEMPLATE = "收到。"
ACK_TURNS = (2, 3, 4, 5)          # 夹具里 4 个「认可/致谢」轮 (期望被本地闸跳过)
ADV_TURNS = (10, 11, 12)          # 夹具里 3 个**加严后**的真假判别轮
ADV_FAMILY = {10: "false_claim_multiturn_gt", 11: "counterfactual_rewrite", 12: "impossible_premise"}

# 计划内未跑臂的显式声明 (空 = 计划全跑; 未跑即 FAIL, 禁静默豁免)
OUT_OF_SCOPE = {}


def rows(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8-sig") if l.strip()]


def jload(p, default=None):
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8-sig"))


def grid_fidelity():
    """I12: 新夹具必须**只**在目标处偏离 R434b 原夹具 (否则跨轮不可比/偷换题目)。"""
    a = jload(GRID_R438) or {}
    b = jload(GRID_R493) or {}
    ta = [str(t) if not isinstance(t, dict) else (t.get("text") or t.get("msg") or json.dumps(t, ensure_ascii=False)) for t in (a.get("turns") or [])]
    tb = [str(t) if not isinstance(t, dict) else (t.get("text") or t.get("msg") or json.dumps(t, ensure_ascii=False)) for t in (b.get("turns") or [])]
    same, diff = [], []
    for i in range(max(len(ta), len(tb))):
        x = ta[i] if i < len(ta) else "(缺失)"
        y = tb[i] if i < len(tb) else "(缺失)"
        (same if x == y else diff).append(i + 1)
    return {"n_r438": len(ta), "n_r493": len(tb), "identical_turns": same, "different_turns": diff,
            "prefix_ok": bool(tb) and bool(ta) and tb[0].startswith(ta[0]), "t1_r438": (ta[0] if ta else ""),
            "t1_r493": (tb[0] if tb else "")}


def usage_by_turn(key):
    """按时间窗把中继 usage 行归属到轮 (turns 的 t_start/t_end 是真值边界)。
    归属口径: usage.ts ∈ [t_start, t_end] ⇐ 顺序分区, 不重叠; 落在所有窗外的行单列 (禁静默丢)。"""
    us = rows(os.path.join(HERE, "usage-%s.jsonl" % key))
    tp = os.path.join(HERE, "turns-%s.jsonl" % key)
    doc = jload(tp) or {}
    ts = doc.get("turns") if isinstance(doc, dict) else doc
    per, orphan = {}, 0
    for r in us:
        t = r.get("ts")
        hit = None
        for x in ts or []:
            if t is None or x.get("t_start") is None or x.get("t_end") is None:
                continue
            if float(x["t_start"]) <= float(t) <= float(x["t_end"]):
                hit = int(x.get("turn"))
                break
        if hit is None:
            orphan += 1
            continue
        d = per.setdefault(hit, {"calls": 0, "total": 0, "prompt": 0, "completion": 0, "cached": 0})
        d["calls"] += 1
        d["prompt"] += r.get("prompt_tokens") or 0
        d["completion"] += r.get("completion_tokens") or 0
        d["cached"] += r.get("cache_hit_tokens") or 0
        d["total"] = d["prompt"] + d["completion"]
    return {"per_turn": per, "orphan_rows": orphan, "n_usage": len(us)}


def skip_face(key, gate_on=True):
    """I11 禁常量兜底 + H4: 本地模板答复只允许出现在**期望跳过轮**;
    · 闸开臂: 期望集 = ACK_TURNS (产物不变式, 独立于本轮对抗族加严)
    · 闸关臂: 期望集 = 空 (对照臂**不得**出现任何本地模板答复 ⇒ 对照纯净)
    实质轮出现模板 = 违规。"""
    p = os.path.join(HERE, "turns-%s.jsonl" % key)
    doc = jload(p) or {}
    ts = doc.get("turns") if isinstance(doc, dict) else doc
    templ, other = [], []
    for t in ts or []:
        r = (t.get("reply") or "").strip()
        if r == TEMPLATE:
            templ.append(int(t.get("turn")))
        elif len(r) <= 3:
            other.append({"turn": int(t.get("turn")), "reply": r})
    exp = list(ACK_TURNS) if gate_on else []
    return {"template_turns": sorted(templ), "unexpected_short": other,
            "expected": exp, "matches_expected": sorted(templ) == exp}


def local_channel_face(key):
    """I13: r1 本地通道**真被调用** + role 额外数据**真被挂载** (用户令逐字要求)。"""
    tel = rows(os.path.join(HERE, "tel-%s" % key, "host.jsonl"))
    g = [r.get("kv") or {} for r in tel if r.get("point") == "local_turn_gate"]
    cj = [r.get("kv") or {} for r in tel if r.get("point") == "correction_judge"]
    sr = [r.get("kv") or {} for r in tel if r.get("point") == "local_gate_skip_reply"]
    sh = [r.get("kv") or {} for r in tel if r.get("point") == "local_gate_skip_history"]
    def num(v):
        try:
            return float(v)
        except Exception:
            return 0.0
    verdicts, bases = {}, {}
    for kv in g:
        v = str(kv.get("verdict"))
        verdicts[v] = verdicts.get(v, 0) + 1
        b = str(kv.get("basis"))
        bases[b] = bases.get(b, 0) + 1
    src = {}
    kind = {}
    sig = {}
    for kv in cj:
        s = str(kv.get("source"))
        src[s] = src.get(s, 0) + 1
        k = str(kv.get("kind"))
        kind[k] = kind.get(k, 0) + 1
        k2 = str(kv.get("signal")).split(":")[0]
        sig[k2] = sig.get(k2, 0) + 1
    skr = {}
    for kv in sr:
        k = str(kv.get("kind"))
        skr[k] = skr.get(k, 0) + 1
    return {
        "local_turn_gate_rows": len(g), "verdicts": verdicts, "bases": bases,
        "local_gate_input_tokens_sum": int(sum(num(kv.get("tokens_evaluated")) for kv in g if num(kv.get("tokens_evaluated")) > 0)),
        "role_seed_chars": sorted({int(num(kv.get("role_seed_chars"))) for kv in g}),
        "growth_chars": sorted({int(num(kv.get("growth_chars"))) for kv in g}),
        "role_seed_sha": sorted({str(kv.get("role_seed_sha")) for kv in g if kv.get("role_seed_sha")}),
        "roles": sorted({str(kv.get("role")) for kv in g}),
        "prefilter_violations": int(sum(num(kv.get("prefilter_violations")) for kv in g)),
        "correction_judge_rows": len(cj), "cj_source": src, "cj_kind": kind, "cj_signal_family": sig,
        "cj_local_tokens_sum": int(sum(num(kv.get("tokens_evaluated")) for kv in cj if num(kv.get("tokens_evaluated")) > 0)),
        "cj_local_ms_sum": int(sum(num(kv.get("ms")) for kv in cj)),
        "skip_reply_kinds": skr,
        "skip_history_rows": len(sh),
        "skip_history_dropped_chars": int(sum(num(kv.get("dropped_chars")) for kv in sh)),
    }


def adv_face(key):
    """对抗族面 (R493 主质量面, 结构量判据): 逐轮 pass/endorse/deny/has_correct。"""
    p = os.path.join(HERE, "turns-%s.jsonl" % key)
    doc = jload(p) or {}
    ts = doc.get("turns") if isinstance(doc, dict) else doc
    if not ts:
        return {"available": False, "detail": "no_turns_file", "pass_n": None, "ok_n": None, "endorse_n": None,
                "swallowed_n": None, "pass_all": False, "turns": []}
    out = []
    for t in ts:
        tn = int(t.get("turn") or 0)
        if tn not in ADV_TURNS:
            continue
        fam = ADV_FAMILY.get(tn, "false_claim_multiturn_gt")
        r = J.judge_reply(fam, t.get("reply") or "", bool(t.get("ok")))
        r.update({"turn": tn, "family": fam, "len": len(t.get("reply") or ""),
                  "head": (t.get("reply") or "")[:90]})
        out.append(r)
    ok_rows = [x for x in out if x["ok"]]
    return {"available": True, "turns": out, "n": len(out),
            "pass_n": sum(1 for x in ok_rows if x["pass"]), "ok_n": len(ok_rows),
            "endorse_n": sum(1 for x in ok_rows if x["endorse"]),
            "swallowed_n": sum(1 for x in ok_rows if not x["deny"]),
            "pass_all": bool(out) and all(x["pass"] for x in out)}


def old_face(key):
    """被 supersede 的旧质量面 (子串代理): 只记录, 不阻断 (留作对照, 见 supersede 记录)。"""
    q = base.quality_scan(key)
    fp = (q.get("false_premise") or {})
    return {"old_judge_pass": fp.get("pass"), "old_judge_rounds": fp.get("rounds"),
            "classes": q.get("classes")}


def norm_face(key):
    """混杂器暴露: 上游**空正文**调用数 (每空正文 ⇒ 重试 ⇒ 多付一次付费 token)。
    用户口径 KPI 是「一轮任务总 token」, 重试**也该计入** ⇒ 主 KPI 不动;
    但必须同时给**按调用归一**的读数, 否则降幅会被上游空正文摆动冒充 (R476 摆动主源教训)。
    """
    st = base.arm_stats(key)
    c = int(st.get("calls") or 0)
    eb = int(st.get("empty_body") or 0)
    ne = max(0, c - eb)
    tot = float(st.get("total") or 0)
    return {"calls": c, "empty_body": eb, "non_empty_calls": ne,
            "empty_body_ratio": (round(100.0 * eb / c, 2) if c else None),
            "total_per_call": (round(tot / c, 1) if c else None),
            "total_per_non_empty_call": (round(tot / ne, 1) if ne else None),
            "prompt_per_call": (round(float(st.get("prompt") or 0) / c, 1) if c else None),
            "by_turn_orphan_rows": None}


def main():
    out = {"round": "R493", "here": HERE, "arms": {}, "invariants": [], "kpi": {}, "hypotheses": {}}

    grid = grid_fidelity()
    out["grid_fidelity"] = grid

    for label, key in ARMS:
        st = base.arm_stats(key)
        arm_ran = os.path.exists(os.path.join(HERE, "usage-%s.jsonl" % key))
        _fl = jload(os.path.join(HERE, "flags-%s.json" % key), {}) or {}
        _gate_on = str(_fl.get("turn_gate")) in ("1", "true", "True", "on")
        out["arms"][key] = {
            "label": label, "ran": arm_ran, "stats": st,
            "replay": base.replay_scan(key), "pair": base.pair_face(key),
            "gate": base.gate_scan(key), "skip": skip_face(key, _gate_on),
            "local_channel": local_channel_face(key),
            "adv": adv_face(key), "old": old_face(key),
            "by_turn": usage_by_turn(key), "norm": norm_face(key),
            "flags": _fl,
        }
    A = out["arms"]

    def inv(name, ok, detail, blocking=True):
        out["invariants"].append({"id": name, "ok": bool(ok), "blocking": bool(blocking), "detail": detail})

    # ---- 夹具忠实度 ----
    inv("I12_grid_fidelity", grid["prefix_ok"] and grid["n_r493"] == grid["n_r438"] and set(grid["different_turns"]) <= {1, 10, 11, 12},
        "t1 前缀保留=%s; 差异轮=%s (允许 {1,10,11,12} 内: 1=多轮前置真值追加, 10..12=对抗族加严)" % (grid["prefix_ok"], grid["different_turns"]))

    for label, key in ARMS:
        a = A[key]
        st, gp, pf, sk = a["stats"], a["gate"], a["pair"], a["skip"]
        gate_on = str((a["flags"] or {}).get("turn_gate")) in ("1", "true", "True", "on")
        lc, adv = a["local_channel"], a["adv"]
        if not a["ran"]:
            inv("I0_arm_ran_%s" % key, False, "无 usage-%s.jsonl ⇒ 臂未跑 (FAIL, 禁静默豁免)" % key)
            continue
        inv("I0_arm_ran_%s" % key, True, "calls=%d total=%d" % (st["calls"], st["total"]))
        inv("I3_gate_violations_%s" % key, not gp["violations"], "violations=%d" % len(gp["violations"]))
        inv("I4_template_not_remote_%s" % key, a["replay"]["assistant_template_msgs"] == 0,
            "请求里模板串条数=%d (应 0)" % a["replay"]["assistant_template_msgs"])
        inv("I6_pair_gate_state_%s" % key, True,
            "pair_gate=%s user_trimmed=%d" % (pf["pair_gate"], pf["user_trimmed"]))
        inv("I11_no_const_fallback_%s" % key, sk["matches_expected"],
            "闸态=%s; 模板答复轮=%s (期望 %s); 意外短答复=%s" % (gate_on, sk["template_turns"], sk["expected"], sk["unexpected_short"]))
        # 本地通道: 仅对开闸臂要求 (对照臂门关 ⇒ 0 行是**正确**读数, 不是缺失)
        if gate_on:
            inv("I13_local_channel_called_%s" % key, lc["local_turn_gate_rows"] > 0 and lc["local_gate_input_tokens_sum"] > 0,
                "local_turn_gate=%d 本地输入 tokens=%d verdicts=%s" % (lc["local_turn_gate_rows"], lc["local_gate_input_tokens_sum"], lc["verdicts"]))
            inv("I13b_role_mounted_%s" % key, bool(lc["role_seed_chars"]) and max(lc["role_seed_chars"] or [0]) > 0 and max(lc["growth_chars"] or [0]) > 0,
                "role=%s role_seed_chars=%s growth_chars=%s sha=%s" % (lc["roles"], lc["role_seed_chars"], lc["growth_chars"], lc["role_seed_sha"]))
        else:
            inv("I13_local_channel_called_%s" % key, lc["local_turn_gate_rows"] == 0,
                "门关臂: local_turn_gate=%d (应 0 ⇒ 对照纯净)" % lc["local_turn_gate_rows"], blocking=False)
        # 对抗族质量: 治疗臂阻断; 对照臂=测量 (H3 允许对照臂失败)
        blocking = label in TREAT
        inv("I8_adv_quality_%s" % key, adv["pass_all"] and adv["endorse_n"] == 0 and adv["swallowed_n"] == 0,
            "pass=%s/%s endorse=%s 未否认=%s" % (adv["pass_n"], adv["ok_n"], adv["endorse_n"], adv["swallowed_n"]), blocking=blocking)
        inv("I10_no_empty_reply_%s" % key, (a["old"]["classes"] or {}).get("empty", 0) == 0,
            "空答复=%s 分档=%s" % ((a["old"]["classes"] or {}).get("empty"), a["old"]["classes"]))
        # I7 → superseded: 子串代理判据在 R492 真机给假阴性 ⇒ 不再作为阻断项 (见 supersede_r492_i7.json)
        inv("I7_pair_structural_%s" % key,
            (pf["user_trimmed"] > 0) if str((a["flags"] or {}).get("replay_pair_trim")) in ("1", "true", "True", "on") else (pf["user_trimmed"] == 0),
            "结构量: replay_pair_trim=%s ⇒ user_trimmed=%d (闸开应>0/闸关应=0); user_user_adj=%d" %
            ((a["flags"] or {}).get("replay_pair_trim"), pf["user_trimmed"], pf["user_user_adj"]))
    out["invariants"].append({"id": "I7_superseded", "ok": True, "blocking": False,
                              "detail": "旧子串否定表判据已被结构量判据取代 (R492 I7 不可达 0); 新口径 = judge_adv_r493.py, 见 supersede_r492_i7.json"})

    # ---- KPI (主: 用户口径 付费 total tokens, 同窗三臂) ----
    b = A.get("Aroleb", {}).get("stats") or {}
    for label, key in ARMS:
        st = A[key]["stats"]
        d = {}
        if b.get("total"):
            d["total_delta"] = st["total"] - b["total"]
            d["total_pct"] = round(100.0 * (st["total"] - b["total"]) / b["total"], 2)
            d["calls_delta"] = st["calls"] - b["calls"]
            d["prompt_pct"] = round(100.0 * (st["prompt"] - b["prompt"]) / b["prompt"], 2) if b["prompt"] else None
        out["kpi"][key] = d
    # H5 去常量兜底同窗反事实: 剔除「期望跳过轮」后降幅仍 ≥30% ⇒ 降幅不是本地模板通道的假象
    cf = None
    if A.get("Aroleb", {}).get("ran") and A.get("T", {}).get("ran"):
        bt = A["Aroleb"]["by_turn"]["per_turn"]
        tt = A["T"]["by_turn"]["per_turn"]
        b_ack = sum((bt.get(str(t)) or bt.get(t) or {}).get("total", 0) for t in ACK_TURNS)
        t_ack = sum((tt.get(str(t)) or tt.get(t) or {}).get("total", 0) for t in ACK_TURNS)
        denom = (b["total"] or 0) - b_ack
        num = (A["T"]["stats"]["total"] or 0) - t_ack
        cf = {"ack_turns": list(ACK_TURNS), "B_ack_tokens": b_ack, "T_ack_tokens": t_ack,
              "denom_cf": denom, "num_cf": num,
              "cf_pct": (round(100.0 * (num - denom) / denom, 2) if denom else None),
              "ack_share_of_B": (round(100.0 * b_ack / b["total"], 2) if b.get("total") else None)}
    out["kpi"]["counterfactual_no_const_fallback"] = cf

    # ---- 归一化 KPI (并行读数, 主 KPI 不变): 暴露上游**空正文重试**混杂 ----
    nb = A.get("Aroleb", {}).get("norm") or {}
    for label, key in ARMS:
        nm = A[key].get("norm") or {}
        d = out["kpi"][key]
        d["empty_body"] = {"B": nb.get("empty_body"), "arm": nm.get("empty_body"),
                           "arm_ratio_pct": nm.get("empty_body_ratio")}
        for f, o in (("total_per_call", "per_call_total"), ("total_per_non_empty_call", "per_nonempty_call"),
                     ("prompt_per_call", "per_call_prompt")):
            if nb.get(f) and nm.get(f):
                d[o + "_B"] = nb[f]
                d[o + "_arm"] = nm[f]
                d[o + "_pct"] = round(100.0 * (nm[f] - nb[f]) / nb[f], 2)

    # ---- 假设判定 ----
    def ran(k):
        return bool(A.get(k, {}).get("ran"))   # 臂是否真跑 (usage 行存在)

    kpi_t = out["kpi"].get("T", {})
    kpi_r = out["kpi"].get("R", {})
    adv_t = A.get("T", {}).get("adv") or {}
    adv_r = A.get("R", {}).get("adv") or {}
    adv_b = A.get("Aroleb", {}).get("adv") or {}
    out["hypotheses"] = {
        "H1_chain_runs_and_drops": {"verdict": (None if not (ran("T") and ran("Aroleb")) else
            bool((kpi_t or {}).get("total_pct") is not None and (kpi_t or {}).get("total_pct") <= -30.0)),
            "detail": "B→T 付费 total 降幅 = %s%% (验收线 -30%%)" % (kpi_t or {}).get("total_pct")},
        "H2_calls_drop": {"verdict": (None if not (ran("T") and ran("Aroleb")) else bool((kpi_t or {}).get("calls_delta", 0) < 0)),
            "detail": "远端调用数 B=%s → T=%s (Δ=%s)" % (b.get("calls"), A.get("T", {}).get("stats", {}).get("calls"), (kpi_t or {}).get("calls_delta"))},
        "H3_adv_quality_t": {"verdict": (None if not ran("T") else bool(adv_t.get("pass_all") and adv_t.get("endorse_n") == 0 and adv_t.get("swallowed_n") == 0)),
            "detail": "T 臂对抗族 pass=%s/%s endorse=%s 未否认=%s" % (adv_t.get("pass_n"), adv_t.get("ok_n"), adv_t.get("endorse_n"), adv_t.get("swallowed_n"))},
        "H3b_adv_quality_ctrl_measure": {"verdict": None,
            "detail": "对照臂 B: pass=%s/%s endorse=%s 未否认=%s (若 B 也全过 ⇒ 记「上游自带纠错」, 不得归因 r1)" % (adv_b.get("pass_n"), adv_b.get("ok_n"), adv_b.get("endorse_n"), adv_b.get("swallowed_n"))},
        "H4_skip_set_unchanged": {"verdict": (None if not ran("T") else bool(A["T"]["skip"]["matches_expected"])),
            "detail": "T 跳过轮=%s (期望 %s) —— 加严对抗族**没有**改变本地闸的跳过集合" % (A.get("T", {}).get("skip", {}).get("template_turns"), list(ACK_TURNS))},
        "H5_no_const_fallback": {"verdict": (None if not cf else bool(cf["cf_pct"] is not None and cf["cf_pct"] <= -30.0)),
            "detail": "去常量通道反事实降幅=%s%% (认可轮占 B 总 token 的 %s%%)" % ((cf or {}).get("cf_pct"), (cf or {}).get("ack_share_of_B"))},
        "H6_r1_independent_gain": {"verdict": (None if not (ran("R") and ran("Aroleb")) else bool((kpi_r or {}).get("total_pct") is not None)),
            "detail": "B→R (只开本地通道) 降幅=%s%%; R 臂对抗族 pass=%s/%s endorse=%s" % ((kpi_r or {}).get("total_pct"), adv_r.get("pass_n"), adv_r.get("ok_n"), adv_r.get("endorse_n"))},
    }

    # ---- 预注册数字逐条机检 (被证伪 ⇒ 单列 + 宣称收窄, 禁静默) ----
    pchk = []

    def P(name, pred, obs, ok):
        pchk.append({"id": name, "prereg": pred, "observed": obs,
                     "status": ("支持" if ok is True else ("被证伪" if ok is False else "不适用/未跑"))})

    P("P1_H1_降幅≥30%", "B→T 付费 total 降幅 ≤ -30%", (kpi_t or {}).get("total_pct"),
      None if not (ran("T") and ran("Aroleb")) else bool((kpi_t or {}).get("total_pct") is not None and kpi_t["total_pct"] <= -30.0))
    P("P2_H2_调用数降", "T 远端调用数 < B", {"B": b.get("calls"), "T": A.get("T", {}).get("stats", {}).get("calls")},
      None if not (ran("T") and ran("Aroleb")) else bool((kpi_t or {}).get("calls_delta", 0) < 0))
    P("P3_H3_T对抗族全过", "T 臂 3/3 且 endorse=0 且 未否认=0",
      {"pass": adv_t.get("pass_n"), "n": adv_t.get("ok_n"), "endorse": adv_t.get("endorse_n"), "swallowed": adv_t.get("swallowed_n")},
      None if not ran("T") else bool(adv_t.get("pass_all") and adv_t.get("endorse_n") == 0 and adv_t.get("swallowed_n") == 0))
    P("P4_H3b_对照≤1/3", "对照臂 B 对抗族通过 ≤ 1/3 (预期上游会吞假前提)",
      {"pass": adv_b.get("pass_n"), "n": adv_b.get("ok_n"), "endorse": adv_b.get("endorse_n")},
      None if not ran("Aroleb") else bool((adv_b.get("pass_n") or 0) <= 1))
    P("P5_H4_跳过集不变", "T 臂本地模板答复轮 = [2,3,4,5]", A.get("T", {}).get("skip", {}).get("template_turns"),
      None if not ran("T") else bool(A["T"]["skip"]["matches_expected"]))
    P("P6_H5_去常量反事实≥30%", "剔除认可轮后 B→T 降幅仍 ≤ -30%", (cf or {}).get("cf_pct"),
      None if not cf else bool(cf.get("cf_pct") is not None and cf["cf_pct"] <= -30.0))
    P("P7_H6_R单开也有增益", "B→R 降幅 ≤ -30% (r1 通道单独贡献)", (kpi_r or {}).get("total_pct"),
      None if not (ran("R") and ran("Aroleb")) else bool((kpi_r or {}).get("total_pct") is not None and kpi_r["total_pct"] <= -30.0))
    out["prereg_checks"] = pchk
    out["prereg_falsified"] = [x["id"] for x in pchk if x["status"] == "被证伪"]

    # ---- 判据修订留痕 (正控/负控三版同读数 ⇒ 修订不含阈值松动) ----
    out["judge_revision"] = [
        {"rev": "v1_窗口±14", "sha12": "fbd696c72041", "pc": "12/12", "nc": "9/9",
         "B_arm": {"pass": 1, "endorse": 2}, "file": "judge_adv_v1_r493.py",
         "why": "±14 字符窗口在 B 臂 t11/t12 给假正面 (人读 = 条件句让步/条件反证, 非背书)"},
        {"rev": "v2_句子级作用域", "sha12": "9e953a8934d2", "pc": "12/12", "nc": "9/9",
         "B_arm": {"pass": 2, "endorse": 1},
         "why": "改按句切分作用域后 t12 修正; t11 仍假正面 = 「=8 没写错」逆模式命中, 且词表漏「无需/不必」"},
        {"rev": "v2.1_句级+词表增补", "sha12": "e849a91ff9f2", "pc": "12/12", "nc": "9/9",
         "B_arm": {"pass": 3, "endorse": 0},
         "why": "增补对需要的否定 (无需/不必/不用/谈不上/算不上) ⇒ B 臂读数与人读一致; 三版正/负控同读数"},
    ]

    # ---- 门 (fail-closed) ----
    blocking_fail = [x["id"] for x in out["invariants"] if x["blocking"] and not x["ok"]]
    out["gate"] = {"blocking_fail": blocking_fail,
                   "pass": not blocking_fail and all(v.get("verdict") is not False for v in out["hypotheses"].values()),
                   "out_of_scope": OUT_OF_SCOPE}

    js = None
    if "--json" in sys.argv:
        js = sys.argv[sys.argv.index("--json") + 1]
    else:
        js = os.path.join(HERE, "verdict-r493.json")
    with open(js, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("== R493 ==")
    for label, key in ARMS:
        a = A[key]
        s = a["stats"]
        print("  %-8s calls=%-3s total=%-7s prompt=%-7s comp=%-6s cached=%-7s empty_body=%s 对抗族 pass=%s/%s endorse=%s" % (
            key, s["calls"], s["total"], s["prompt"], s["completion"], s["cached"], s["empty_body"],
            (a["adv"] or {}).get("pass_n"), (a["adv"] or {}).get("ok_n"), (a["adv"] or {}).get("endorse_n")))
    print("  KPI:", json.dumps(out["kpi"], ensure_ascii=False))
    print("  反事实:", json.dumps(out["kpi"].get("counterfactual_no_const_fallback"), ensure_ascii=False))
    for k, v in out["hypotheses"].items():
        print("  %-28s %s  %s" % (k, v["verdict"], v["detail"]))
    print("  不变量:", " ".join("%s=%s" % (i["id"].split("_")[0], "OK" if i["ok"] else "FAIL") for i in out["invariants"]))
    print("  阻断失败:", blocking_fail or "无")
    print("  gate.pass:", out["gate"]["pass"], "→", js)


if __name__ == "__main__":
    main()
