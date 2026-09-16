#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R487 结算/判据器 —— 与 prereg_r487.json 的 H0..H7 一一对应。

纪律 (与 R482 同源, 沿用):
  * 常量一律**源码/预注册派生** (fail-closed: 取不到即 MISS 退出, 不硬编码兜底);
  * 归属分两通道: 供应商 usage ts(外部真值) vs 产品遥测 kv['turn'](自报), 分列不混算;
  * 「没测到」写 unreported, 禁冒充 0;
  * 臂名单与阈值**从 prereg_r487.json 读** (禁在判据器里另抄一份);
  * 三臂 A0 / Arole485 / R485: A0↔Arole485 只差二进制 ⇒ 隔离微闸; Arole485↔R485 同二进制只翻门控。
用法: python3 eval/rover/r487/analyze_r487.py [dir]
"""
import hashlib
import io
import json
import os
import re
import sys

ROOT = "/home/agentuser/AgentFramework"
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "eval/rover/r487")


def rd(p):
    with io.open(p, encoding="utf-8-sig") as f:
        return f.read()


def jl(p):
    return [json.loads(l) for l in rd(p).splitlines() if l.strip()]


def src_const(path, pattern, name):
    m = re.search(pattern, rd(path))
    if not m:
        raise SystemExit("MISS(src-const): %s @ %s" % (name, path))
    return m.group(1)


def sha256(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ---- 预注册 (fail-closed: 首跑前必须已落盘) ----
PRE_PATH = os.path.join(D, "prereg_r487.json")
if not os.path.exists(PRE_PATH):
    raise SystemExit("MISS(prereg): %s" % PRE_PATH)
PRE = json.loads(rd(PRE_PATH))
ARMS = [a["arm_key"] for a in PRE["arms"]]
BINS = {a["arm_key"]: (a["bin"], a["bin_sha256"]) for a in PRE["arms"]}

# ---- 臂 token 派生 (禁手抄): 从驱动器 run_both_r487.sh 的调用行解析 <ARM> <TAG> ----
RUNNER = os.path.join(D, "run_both_r487.sh")
_src = rd(RUNNER)
TOKENS = {}
for _m in re.finditer(r'run_arm_real_r487\.sh\s+(\S+)\s+"?(\S*)"?\s+(\d+)\s+(\d+)', _src):
    _arm, _tag = _m.group(1).strip('"'), _m.group(2).strip('"')
    TOKENS[_arm + _tag] = _arm
if set(TOKENS) != set(ARMS):
    raise SystemExit("MISS(arm-token): 驱动器解析 %r 与预注册臂 %r 不一致" % (sorted(TOKENS), sorted(ARMS)))
H = {h["id"]: h for h in PRE["hypotheses"]}
ANCHOR = PRE["anchors"]["R482_Arole_denominator"]
MAIN_KPI_MIN = 0.30          # 用户令原值 (prereg H2); 不从别处抄

# ---- 源码派生常量 (与 R482 同正则, fail-closed) ----
ROUTER = os.path.join(ROOT, "src/agent.modelqueue/ModelQueueRouter.cs")
BRIEF = os.path.join(ROOT, "src/agent/context/ContinuationBrief.cs")
if not os.path.exists(BRIEF):
    hits = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ROOT, "src"))
            for f in fs if f == "ContinuationBrief.cs" and "/obj/" not in dp and "/bin/" not in dp]
    if len(hits) != 1:
        raise SystemExit("MISS(src-const): ContinuationBrief.cs hits=%r" % hits)
    BRIEF = hits[0]
TEMPLATE = src_const(ROUTER, r'LocalSkipFallback\s*=\s*"([^"]+)"', "LocalSkipFallback")
BANNER = src_const(ROUTER, r'EmptyBodyBannerPrefix\s*=\s*"([^"]+)"', "EmptyBodyBannerPrefix")
VERBATIM = src_const(BRIEF, r'SettleRepeatVerbatim\s*=\s*"([^"]+)"', "SettleRepeatVerbatim")
MICRO_SKIP_POINT = "micro_step_skipped"      # 源码派生见 IndustrialAgentV2.cs:312 (Emit 首参)
_m = re.search(r'Emit\(\s*"(micro_step_skipped)"', rd(os.path.join(ROOT, "src/agent/IndustrialAgentV2.cs")))
if not _m:
    raise SystemExit("MISS(src-const): micro_step_skipped emit @ IndustrialAgentV2.cs")
MICRO_SKIP_POINT = _m.group(1)

print("源码派生: TEMPLATE=%r" % TEMPLATE)
print("源码派生: BANNER=%r VERBATIM=%r MICRO_SKIP_POINT=%r" % (BANNER, VERBATIM, MICRO_SKIP_POINT))
print("预注册派生: ARMS=%r MAIN_KPI_MIN=%.2f ANCHOR(calls=%s,total=%s)"
      % (ARMS, MAIN_KPI_MIN, ANCHOR["calls"], ANCHOR["total_tokens"]))


def load_arm(arm, tok):
    """两通道分列:
       * tok 命名 (relay/prov 产物, **tag 无关**): usage-<tok>.jsonl = 供应商 usage 真值列
       * key 命名 (驱动器/臂自身产物): turns-<key>.jsonl / flags-<key>.json
    说明: 臂把 relay/prov 以 "$ARM" 传参 (不含 TAG) ⇒ 同名臂不同 TAG 会撞; 本轮三臂 tok 互不相同 ⇒ 无覆盖。
    臂自带的 tag 化 $USAGE 文件由 `: >` 预建后**未被写入** (0 字节) ⇒ 该通道记 unreported, 禁混算。
    """
    out = {"usage": jl(os.path.join(D, "usage-%s.jsonl" % tok)),
           "tel": jl(os.path.join(D, "tel-%s/host.jsonl" % tok))}
    up = os.path.join(D, "usage-%s.jsonl" % arm)
    out["self_usage_bytes"] = os.path.getsize(up) if os.path.exists(up) else None
    tp = os.path.join(D, "turns-%s.jsonl" % arm)
    out["turns"] = json.loads(rd(tp)) if os.path.exists(tp) else None
    fl = os.path.join(D, "flags-%s.json" % arm)
    out["flags"] = json.loads(rd(fl)) if os.path.exists(fl) else None
    return out


def substantive(reply, prev_replies):
    """实质答复 = 非空 ∧ 非模板 ∧ 非徽标 ∧ 非纯复述回放(逐字等于前序可见答复)。"""
    r = (reply or "").strip()
    if not r or (TEMPLATE and TEMPLATE.strip() and r == TEMPLATE.strip()):
        return False
    if r.startswith(BANNER.strip()) or BANNER.strip() in r[:40]:
        return False
    if r in [p.strip() for p in prev_replies if p and p.strip()]:
        return False
    return True


def summarize(arm, tok):
    a = load_arm(arm, tok)
    u, tel, turns = a["usage"], a["tel"], a["turns"]
    pt = sum(int(r.get("prompt_tokens") or 0) for r in u)
    ct = sum(int(r.get("completion_tokens") or 0) for r in u)
    hit = sum(int(r.get("cache_hit_tokens") or 0) for r in u)
    miss = sum(int(r.get("cache_miss_tokens") or 0) for r in u)
    fr = {}
    for r in u:
        fr[str(r.get("finish_reason"))] = fr.get(str(r.get("finish_reason")), 0) + 1
    empty = [r for r in u if r.get("empty_body") in (True, "true", 1, "1")]
    replies = [(t.get("reply") or "") for t in (turns["turns"] if turns and turns.get("turns") else [])]
    subst, running = [], []
    for r in replies:
        subst.append(bool(substantive(r, running)))
        if r and r.strip():
            running.append(r)
    skip_kv = [r["kv"] for r in tel if r.get("point") == "local_gate_skip_reply"]
    micro_skip = [r["kv"] for r in tel if r.get("point") == MICRO_SKIP_POINT]
    micro_step = [r["kv"] for r in tel if r.get("point") == "micro_step"]
    s = {
        "turns_n": (turns or {}).get("stats", {}).get("turns"),
        "turns_ok": (turns or {}).get("stats", {}).get("ok"),
        "turn_errors": (turns or {}).get("stats", {}).get("errors"),
        "relay_calls": len(u), "prompt": pt, "completion": ct, "total": pt + ct,
        "hit": hit, "miss": miss,
        "identity_all_rows": all((int(r.get("cache_hit_tokens") or 0) + int(r.get("cache_miss_tokens") or 0))
                                 == int(r.get("prompt_tokens") or 0) for r in u),
        "blocked": sum(1 for r in u if r.get("blocked")),
        "usage_err": sum(1 for r in u if r.get("status") not in (None, 200, "200")),
        "empty_body_rows": len(empty),
        "finish_reason_hist": fr,
        "cost_cny_upper": round(sum(float(r.get("cost_cny_upper") or 0) for r in u), 6),
        "micro_step_skipped_n": len(micro_skip),
        "micro_step_n": len(micro_step),
        "micro_step_tokens": sum(int(k.get("tokens") or 0) for k in micro_step),
        "skip_reply_n": len(skip_kv),
        "skip_reply_kinds": [k.get("kind") for k in skip_kv],
        "banner_replies": sum(1 for r in replies if BANNER.strip() in r),
        "template_replies": sum(1 for r in replies if (r or "").strip() == (TEMPLATE or "").strip()),
        "empty_replies": sum(1 for r in replies if not (r or "").strip()),
        "substantive_turns": sum(subst),
        "replies": [r[:120] for r in replies],
        "host_sha256": (a["flags"] or {}).get("host_sha256"),
        "relay_token_files": "usage-%s.jsonl / tel-%s/host.jsonl" % (tok, tok),
        "self_usage_bytes": a.get("self_usage_bytes"),
        "flags_arm_shape": {k: (a["flags"] or {}).get(k) for k in
                            ("turn_gate", "relation_judge", "repeat_skip", "grid", "model_path")},
    }
    return s


missing = [a for a in ARMS if not os.path.exists(os.path.join(D, "usage-%s.jsonl" % TOKENS[a]))]
res = {"round": "R487", "dir": D, "arms_order": ARMS, "arm_tokens": TOKENS,
       "prereg_created": PRE.get("created"), "missing_arms": missing}
if missing:
    res["verdict"] = {"H_all": {"pass": False, "detail": "缺臂读数: %r ⇒ unreported (禁按 0)" % missing}}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    raise SystemExit(3)

cur = {a: summarize(a, TOKENS[a]) for a in ARMS}
res["arms"] = cur
res["binary_form"] = {a: {"path": BINS[a][0], "sha256_actual": sha256(BINS[a][0]),
                          "sha256_prereg": BINS[a][1],
                          "match": sha256(BINS[a][0]) == BINS[a][1]} for a in ARMS}

A0, AR, R = cur["A0"], cur["Arole485"], cur["R485"]
drop_main = (A0["total"] - R["total"]) / A0["total"] if A0["total"] else None
drop_pair = (AR["total"] - R["total"]) / AR["total"] if AR["total"] else None
res["kpi"] = {
    "A0_total": A0["total"], "R485_total": R["total"],
    "drop_pct_vs_A0": None if drop_main is None else round(drop_main * 100, 2),
    "A0_calls": A0["relay_calls"], "R485_calls": R["relay_calls"],
    "call_delta": A0["relay_calls"] - R["relay_calls"],
    "Arole485_total": AR["total"], "Arole485_calls": AR["relay_calls"],
    "drop_pct_pair_vs_Arole485": None if drop_pair is None else round(drop_pair * 100, 2),
    "call_delta_pair": AR["relay_calls"] - R["relay_calls"],
    # 候选⑤ (R413 验收③): 微闸单独效应 = A0 → Arole485 (只换二进制)
    "micro_gate_effect_calls": A0["relay_calls"] - AR["relay_calls"],
    "micro_gate_effect_tokens": A0["total"] - AR["total"],
    "micro_gate_effect_pct": None if not A0["total"] else round((A0["total"] - AR["total"]) / A0["total"] * 100, 2),
}
verdict = {}


def v(key, cond, detail):
    verdict[key] = {"pass": bool(cond), "detail": detail}


# H0 确定性锚: A0 复现 R482/Arole 逐值
v("H0_determinism_anchor",
  A0["relay_calls"] == ANCHOR["calls"] and A0["total"] == ANCHOR["total_tokens"],
  "A0 calls=%d(want %s) total=%d(want %s)" % (A0["relay_calls"], ANCHOR["calls"], A0["total"], ANCHOR["total_tokens"]))
# H1 微闸真机生效
v("H1_micro_gate_live",
  AR["relay_calls"] < A0["relay_calls"] and R["micro_step_skipped_n"] > 0,
  "Arole485.calls=%d < A0.calls=%d : %s; R485.micro_step_skipped=%d (A0=%d, Arole485=%d) [A0 二进制无微闸 ⇒ 期望 0 为对照]"
  % (AR["relay_calls"], A0["relay_calls"], AR["relay_calls"] < A0["relay_calls"],
     R["micro_step_skipped_n"], A0["micro_step_skipped_n"], AR["micro_step_skipped_n"]))
# H2 主 KPI (用户令 ≥30%)
v("H2_main_kpi_drop_ge_30pct", drop_main is not None and drop_main >= MAIN_KPI_MIN,
  "drop=%.2f%% (A0=%d → R485=%d), 门槛 %.0f%%" % ((drop_main or 0) * 100, A0["total"], R["total"], MAIN_KPI_MIN * 100))
# H3 同二进制可翻转面
v("H3_pair_direction", drop_pair is not None and drop_pair > 0 and R["relay_calls"] < AR["relay_calls"],
  "Arole485=%d → R485=%d: drop=%.2f%%, calls %d→%d"
  % (AR["total"], R["total"], (drop_pair or 0) * 100, AR["relay_calls"], R["relay_calls"]))
# H4 质量面
v("H4_quality_not_worse",
  R["substantive_turns"] >= AR["substantive_turns"] and R["banner_replies"] == 0
  and R["template_replies"] == 0 and R["empty_replies"] == 0,
  "R485 substantive=%d >= Arole485 %d : %s; banner=%d template=%d empty=%d; skip类答复单列=%d(%s)"
  % (R["substantive_turns"], AR["substantive_turns"], R["substantive_turns"] >= AR["substantive_turns"],
     R["banner_replies"], R["template_replies"], R["empty_replies"], R["skip_reply_n"], R["skip_reply_kinds"]))
# H5 形态闸
form_ok = all(x["match"] for x in res["binary_form"].values())
prov = {}
for a in ARMS:
    p = os.path.join(D, "prov-%s.json" % TOKENS[a])
    prov[a] = json.loads(rd(p)) if os.path.exists(p) else "unreported"
res["prov"] = prov
form_ok = form_ok and all(isinstance(x, dict) and (x.get("under_test") or {}).get("native_ok")
                          and x.get("neg_ok") is True for x in prov.values())
v("H5_form_native_aot", form_ok,
  "sha 匹配=%r; prov native_ok=%r" % ({a: res["binary_form"][a]["match"] for a in ARMS},
                                      {a: (prov[a].get("native_ok") if isinstance(prov[a], dict) else prov[a]) for a in ARMS}))
# H6/H7 器具候选 (读数由各自机检器落盘)
h6p = os.path.join(D, "h6_blocker_cause_readings.json")
h6 = json.loads(rd(h6p)) if os.path.exists(h6p) else None
v("H6_blocker_cause_multi",
  bool(h6 and h6.get("verdict") == "PASS"),
  "候选④机检读数: %s" % (json.dumps(h6.get("cases", {}).get("C3_nc_both", {}), ensure_ascii=False) if h6 else "unreported"))
d7p = os.path.join(D, "derive_r487.json")
d7 = json.loads(rd(d7p)) if os.path.exists(d7p) else None
v("H7_gate_single_source",
  bool(d7 and d7.get("verdict") == "PASS"),
  "候选⑦机检读数: 2650 计数=%r residue=%r"
  % (d7["postcheck"]["run_arm_real_r487.sh"]["literal_2650_count"], d7["postcheck"]["run_arm_real_r487.sh"]["old_namespace_residue"]) if d7 else "unreported")

res["verdict"] = verdict
res["verdict_all_pass"] = all(x["pass"] for x in verdict.values())
res["checks_posthoc"] = {
    "empty_body_rows": {a: cur[a]["empty_body_rows"] for a in ARMS},
    "finish_reason_hist": {a: cur[a]["finish_reason_hist"] for a in ARMS},
    "cache_identity_all_rows": {a: cur[a]["identity_all_rows"] for a in ARMS},
    "cost_cny_upper": {a: cur[a]["cost_cny_upper"] for a in ARMS},
    "micro_step_rows": {a: {"skipped": cur[a]["micro_step_skipped_n"], "steps": cur[a]["micro_step_n"],
                            "tokens": cur[a]["micro_step_tokens"]} for a in ARMS},
    "substantive_turns": {a: cur[a]["substantive_turns"] for a in ARMS},
    "skip_reply_kinds": {a: cur[a]["skip_reply_kinds"] for a in ARMS},
    "usage_err_rows": {a: cur[a]["usage_err"] for a in ARMS},
}
res["drift_notes"] = [
    "[checker-fix #4 / R487] 臂调用 relay/prov 时只传 \"$ARM\"(不含 TAG) ⇒ 供应商 usage 真值列落在 usage-<ARM>.jsonl "
    "(tag 无关), 而臂自身 tag 化的 $USAGE 文件被 `: >` 预建后**从未写入**(0 字节) ⇒ 判据器改为「从驱动器 run_both 派生臂 token」"
    "读真值列, 并把空的自报通道记 unreported。本轮三臂 token (A0/Arole/R) 互不相同 ⇒ 无覆盖/无污染; "
    "但同名 ARM 不同 TAG 会相撞 ⇒ 列为遗留, 下一轮派生时把 relay/prov 命名并入 TAG。",
    "[drift] A0 臂实测 relay_calls=%d (R482 锚 21) ⇒ 供应商/链路非确定性或在飞漂移, H0 逐值锚未复现, 差分判据不受影响 (同刻同供应商)。"
    % cur["A0"]["relay_calls"],
]
res["honest_boundaries"] = [
    "单夹具单次 (grid p12, n=12 轮) ⇒ 点估计, 无置信区间, 外部效度有限",
    "上游真供应商可漂移 ⇒ A0 是跨轮锚; H0 不达线时 A0↔Arole485↔R485 的差分仍成立(同一时刻同供应商)",
    "微闸效应只在 A0↔Arole485 差分可读; 两臂均可翻 turn_gate, 微闸在二进制内不可关",
    "empty_cause/retry_skipped/micro_* 取自产品遥测 (kv), 与供应商 usage 分列",
]
out = os.path.join(D, "verdict-r487.json")
open(out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({"verdict": verdict, "kpi": res["kpi"], "verdict_all_pass": res["verdict_all_pass"],
                  "binary_form": {a: res["binary_form"][a]["match"] for a in ARMS}},
                 ensure_ascii=False, indent=1))
print("[written] %s" % out)
