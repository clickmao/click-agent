#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R482 结算/判据器 —— 与 prereg_r482.json 的 H1..H6 一一对应。

纪律:
  * 常量一律**源码派生** (fail-closed: 取不到即抛 MISS, 不硬编码兜底);
  * 归属分两通道: 供应商 usage ts(外部真值) vs 产品遥测 kv['turn'](自报), 分列不混算;
  * 「没测到」写 unreported, 禁冒充 0;
  * 基线 = 本轮 Arole 臂实测(同网格/同夹具/同二进制/仅门控不同); R477 只作**跨二进制**参考列。
用法: python3 eval/rover/r482/check_r482.py [dir]
"""
import hashlib
import io
import json
import os
import re
import sys

ROOT = "/home/agentuser/AgentFramework"
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "eval/rover/r482")
REF_D = os.path.join(ROOT, "eval/rover/r477")          # 跨二进制参考列
ARMS = ("Arole", "R")


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
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ---- 预注册 (fail-closed: 首跑前必须已落盘) ----
PRE_PATH = os.path.join(D, "prereg_r482.json")
if not os.path.exists(PRE_PATH):
    raise SystemExit("MISS(prereg): %s" % PRE_PATH)
pre = json.loads(rd(PRE_PATH))
BIN = pre["binary"]["path"]
PREREG_BIN_SHA16 = pre["binary"]["sha256_16"]
H1_MIN = 0.30
H2_MIN_CALLS = 5
H3_MAX_AROLE_CALLS = 21          # 严格小于该值 ⇒ 判 H3
H4_MAX_R_CALLS = 10

# ---- 源码派生常量 ----
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
DIAG = os.path.join(ROOT, "src/agent.modelqueue/EmptyBodyDiagnosis.cs")
if not os.path.exists(DIAG):
    raise SystemExit("MISS(src-const): EmptyBodyDiagnosis.cs")
# Banner() 方法体必须定位到**方法内**再取文案 (CauseName() 里同名枚举有别的字符串, 直接全局正则会取错)
_banner_body = re.search(r"public static string Banner\([^)]*\)\s*\{(.*?)\n    \}", rd(DIAG), re.S)
if not _banner_body:
    raise SystemExit("MISS(src-const): Banner() body @ %s" % DIAG)
_b = _banner_body.group(1)
_m_tc = re.search(r'EmptyBodyCause\.ToolCall\s*=>\s*([^,\n]+)', _b)
_m_le = re.search(r'EmptyBodyCause\.LengthExhausted\s*=>\s*([^,\n]+)', _b)
if not _m_tc or not _m_le:
    raise SystemExit("MISS(src-const): Banner() ToolCall/LengthExhausted arms: %r" % _b[:200])


def _lit(expr, name):
    """从 "+ ..." 三目/拼接表达式里取第一个字符串字面量 (fail-closed)。"""
    m = re.search(r'"([^"]{4,})"', expr)
    if not m:
        raise SystemExit("MISS(src-const): %s literal in %r" % (name, expr))
    return m.group(1)


TOOLCALL_TEXT = _lit(_m_tc.group(1), "ToolCallBanner")
LENEXH_TEXT = _lit(_m_le.group(1), "LengthExhaustedBanner")
OLD_MISDIAG = LENEXH_TEXT      # 旧误诊文案 = 当前 LengthExhausted 档文案(源码派生, 非硬编码)

print("源码派生: TEMPLATE=%r" % TEMPLATE)
print("源码派生: BANNER=%r VERBATIM=%r" % (BANNER, VERBATIM))
print("源码派生: TOOLCALL_TEXT=%r" % TOOLCALL_TEXT)
print("源码派生: LENEXH_TEXT=%r" % LENEXH_TEXT)


def load_arm(d, arm):
    out = {"usage": jl(os.path.join(d, "usage-%s.jsonl" % arm)),
           "tel": jl(os.path.join(d, "tel-%s/host.jsonl" % arm))}
    tp = os.path.join(d, "turns-%s.jsonl" % arm)
    out["turns"] = json.loads(rd(tp)) if os.path.exists(tp) else None
    fl = os.path.join(d, "flags-%s.json" % arm)
    out["flags"] = json.loads(rd(fl)) if os.path.exists(fl) else None
    return out


def substantive(reply, prev_replies):
    """实质答复 = 非空 ∧ 非模板 ∧ 非徽标 ∧ 非纯复述回放(逐字等于前序可见答复)。"""
    r = (reply or "").strip()
    if not r or TEMPLATE and TEMPLATE.strip() and r == TEMPLATE.strip():
        return False
    if r.startswith(BANNER.strip()) or BANNER.strip() in r[:40]:
        return False
    if r in [p.strip() for p in prev_replies if p and p.strip()]:
        return False
    return True


def summarize(d, arm):
    a = load_arm(d, arm)
    u, tel, turns = a["usage"], a["tel"], a["turns"]
    pt = sum(int(r.get("prompt_tokens") or 0) for r in u)
    ct = sum(int(r.get("completion_tokens") or 0) for r in u)
    hit = sum(int(r.get("cache_hit_tokens") or 0) for r in u)
    miss = sum(int(r.get("cache_miss_tokens") or 0) for r in u)
    fr = {}
    for r in u:
        k = str(r.get("finish_reason"))
        fr[k] = fr.get(k, 0) + 1
    empty = [r for r in u if r.get("empty_body") in (True, "true", 1, "1")]
    skips = [r["kv"] for r in tel if r["point"] == "local_gate_skip_reply"]
    llm = [r["kv"] for r in tel if r["point"] in ("llm_call", "llm_call_recover")]
    cause = {}
    for k in llm:
        if "empty_cause" in k:
            cause[str(k["empty_cause"])] = cause.get(str(k["empty_cause"]), 0) + 1
    rs_true = sum(1 for k in llm if str(k.get("retry_skipped")).lower() == "true")
    # [checker-fix #1] retry_skipped 实际落在 point='llm_call_empty_body' 行(非 llm_call) —— 先前只扫
    # llm_call/llm_call_recover ⇒ 恒 0 假阴性; 此处按「全 point 扫 kv 键」取值, 与 R478 遥测形状对齐。
    rs_vals = [str(r["kv"].get("retry_skipped")) for r in tel if "retry_skipped" in (r.get("kv") or {})]
    rs_true = sum(1 for x in rs_vals if x.lower() == "true")
    replies = [(t.get("reply") or "") for t in (turns["turns"] if turns else [])]
    subst, running = [], []
    for r in replies:
        subst.append(bool(substantive(r, running)))
        if r and r.strip():
            running.append(r)
    s = {
        "turns_n": (turns or {}).get("stats", {}).get("turns"),
        "turns_ok": (turns or {}).get("stats", {}).get("ok"),
        "turn_errors": (turns or {}).get("stats", {}).get("errors"),
        "relay_calls": len(u), "prompt": pt, "completion": ct, "total": pt + ct,
        "hit": hit, "miss": miss,
        "identity_all_rows": all((int(r.get("cache_hit_tokens") or 0) + int(r.get("cache_miss_tokens") or 0))
                                 == int(r.get("prompt_tokens") or 0) for r in u),
        "blocked": sum(1 for r in u if r.get("blocked")),
        "usage_err": sum(1 for r in u if str(r.get("status")) != "200"),
        "empty_body_rows": len(empty),
        "finish_reason_hist": fr,
        "cost_cny_upper": round(sum(float(r.get("cost_cny_upper") or 0) for r in u), 6),
        "llm_call_rows": len(llm),
        "retry_skipped_true": rs_true,
        "tel_kv_retry_skipped": rs_vals,
        "empty_cause_hist": cause,
        "skip_reply_n": len(skips),
        "skip_reply_kinds": [s.get("kind") for s in skips],
        "banner_replies": sum(1 for r in replies if BANNER.strip() in r),
        "old_misdiag_replies": sum(1 for r in replies if OLD_MISDIAG in r),
        "toolcall_text_replies": sum(1 for r in replies if TOOLCALL_TEXT.strip() and TOOLCALL_TEXT.strip() in r),
        "lenezxh_text_replies": sum(1 for r in replies if LENEXH_TEXT.strip() and LENEXH_TEXT.strip() in r),
        "substantive_turns": sum(subst),
        "empty_replies": sum(1 for r in replies if not (r or "").strip()),
        "replies": [r[:120] for r in replies],
        "host_sha256": (a["flags"] or {}).get("host_sha256"),
        "flags_arm_shape": {k: (a["flags"] or {}).get(k) for k in ("turn_gate", "relation_judge", "repeat_skip", "role_fixture", "grid", "model_path")},
    }
    return s


res = {"round": "R482", "dir": D, "binary": BIN, "binary_sha16_actual": sha256(BIN)[:16] if os.path.exists(BIN) else "absent",
       "binary_sha16_prereg": PREREG_BIN_SHA16,
       "binary_match": (os.path.exists(BIN) and sha256(BIN)[:16] == PREREG_BIN_SHA16)}
ref = {a: summarize(REF_D, a) for a in ARMS} if os.path.exists(os.path.join(REF_D, "usage-R.jsonl")) else None
cur = {a: summarize(D, a) for a in ARMS}
res["arms"] = cur
res["ref_r477_cross_binary"] = ref

A, R = cur["Arole"], cur["R"]
drop = (A["total"] - R["total"]) / A["total"] if A["total"] else None
res["kpi"] = {"a_total": A["total"], "r_total": R["total"],
              "drop_pct": None if drop is None else round(drop * 100, 2),
              "call_delta": A["relay_calls"] - R["relay_calls"],
              "a_calls": A["relay_calls"], "r_calls": R["relay_calls"]}
if ref:
    res["kpi_vs_r477"] = {
        "a_total_delta_pct": round((A["total"] - ref["Arole"]["total"]) / ref["Arole"]["total"] * 100, 2),
        "r_total_delta_pct": round((R["total"] - ref["R"]["total"]) / ref["R"]["total"] * 100, 2),
        "a_calls_delta": A["relay_calls"] - ref["Arole"]["relay_calls"],
        "r_calls_delta": R["relay_calls"] - ref["R"]["relay_calls"],
    }

# H6 逐条对齐 prereg 原文 (prereg H6 = 「复述/确认轮可见答复非空且为前序**实质**答复逐字回放(≥1 例)」 ∧
# 「不出现旧误诊文案」)。口径修正留痕 [checker-fix #2]: 先前实现把 (a) 写成「tool_call 因由必须出现新文案」,
# (b) 写成「t9==t6」—— 两条都**严于** prereg 原文, 属实现偏离而非判据收窄; 此处按 prereg 复原,
# 同时把更严的变体结果原样保留在 checks_posthoc 里 (含 R 臂 t2-t5 模板化答复 = prereg 未覆盖的质量面)。
def turn_replies(d, arm):
    t = load_arm(d, arm)["turns"]
    return [(x.get("turn"), x.get("reply") or "") for x in (t["turns"] if t else [])]


tr = dict(turn_replies(D, "R"))
trA = dict(turn_replies(D, "Arole"))
REPLAY_MIN = 40  # 逐字回放的可见答复下界(低于此长度的模板/寒暄不认作「实质答复」)


def replay_examples(tr_map):
    """∃ i<j: reply_j 非空 ∧ r_j == r_i 逐字 ∧ r_i 为实质答复(非模板 ∧ 长度≥REPLAY_MIN)。"""
    out = []
    seen = {}
    for tno in sorted(k for k in tr_map if isinstance(k, int)):
        r = (tr_map[tno] or "").strip()
        if not r:
            continue
        for pno, pr in seen.items():
            if r == pr.strip() and len(r) >= REPLAY_MIN and r != (TEMPLATE or "").strip():
                out.append((tno, pno, len(r)))
        seen.setdefault(tno, r)
    return out


_replay = replay_examples(tr)
_replay_all = []
_seen = {}
for _tno in sorted(k for k in tr if isinstance(k, int)):
    _r = (tr[_tno] or "").strip()
    if _r:
        for _pno, _pr in _seen.items():
            if _r == _pr.strip():
                _replay_all.append((_tno, _pno, len(_r)))
        _seen.setdefault(_tno, _r)

verdict = {}

def v(key, cond, detail):
    verdict[key] = {"pass": bool(cond), "detail": detail}

v("H1_drop_ge_30pct", drop is not None and drop >= H1_MIN, "drop=%.2f%% A=%d R=%d" % ((drop or 0) * 100, A["total"], R["total"]))
v("H2_r1_call_gain", (A["relay_calls"] - R["relay_calls"]) >= H2_MIN_CALLS, "A=%d R=%d delta=%d" % (A["relay_calls"], R["relay_calls"], A["relay_calls"] - R["relay_calls"]))
v("H3_arole_calls_below_r477", A["relay_calls"] < H3_MAX_AROLE_CALLS, "A=%d (R477 A=21) ⇒ prereg fail_action: 记「修复在真链上无可测效果」单列, 不重跑凑数" % A["relay_calls"])
v("H4_r_calls_not_worse", R["relay_calls"] <= H4_MAX_R_CALLS, "R=%d (R477 R=10)" % R["relay_calls"])
v("H5_identity_all_rows", A["identity_all_rows"] and R["identity_all_rows"], "A=%s R=%s" % (A["identity_all_rows"], R["identity_all_rows"]))
# H6a (prereg 原文): R 臂可见答复中**不出现**旧文案「推理过程占满输出预算」
v("H6a_no_old_misdiagnosis_banner", cur["R"]["old_misdiag_replies"] == 0,
  "R 旧文案出现=%d (可见 banner 总数=%d, empty_cause 分布=%s)"
  % (cur["R"]["old_misdiag_replies"], cur["R"]["banner_replies"], cur["R"]["empty_cause_hist"]))
# H6b (prereg 原文): ≥1 例逐字回放 ∧ 回放目标为实质答复 ∧ 回放答复非空
v("H6b_replay_verbatim", len(_replay) >= 1,
  "实质逐字回放例=%s; 全部逐字重复(含模板)=%s" % (_replay, _replay_all))
verdict["H6_overall"] = {"pass": bool(verdict["H6a_no_old_misdiagnosis_banner"]["pass"] and verdict["H6b_replay_verbatim"]["pass"]),
                         "detail": "H6(prereg 原文) = a ∧ b"}
res["verdict"] = verdict
res["verdict_all_pass"] = all(x["pass"] for k, x in verdict.items())
res["checks_posthoc"] = {
    "r477_cross_binary": res.get("kpi_vs_r477"),
    "template_replies_R": sum(1 for r in cur["R"]["replies"] if (r or "").strip() == (TEMPLATE or "").strip()),
    "template_replies_A": sum(1 for r in cur["Arole"]["replies"] if (r or "").strip() == (TEMPLATE or "").strip()),
    "substantive_turns": {"R": R["substantive_turns"], "A": A["substantive_turns"]},
    "quality_verdict_H6c_strict_variant": {"pass": bool(R["substantive_turns"] >= A["substantive_turns"]),
                                           "detail": "严于 prereg 的变体: R 实质轮 %d < A %d ⇒ R 臂有轮次由模板兜底, 非逐字回放"
                                                     % (R["substantive_turns"], A["substantive_turns"])},
    "empty_body_upstream_drift": {"r477_Arole": 15, "r482_Arole": A["empty_body_rows"],
                                  "note": "上游漂移: 空正文基数 15→%d ⇒ R478 修复的调用数收益headroom被压缩" % A["empty_body_rows"]},
    "retry_skipped_rows_by_arm": {a: {"rows": cur[a]["retry_skipped_true"],
                                      "tel_kv_all_points": sum(1 for rr in cur[a]["tel_kv_retry_skipped"]),
                                      "values": cur[a]["tel_kv_retry_skipped"]} for a in ARMS},
    "banner_by_arm": {a: cur[a]["banner_replies"] for a in ARMS},
}
res["drift_notes"] = [
    "[checker-fix #1] retry_skipped 取值: 遥测落在 point='llm_call_empty_body' 行; 先前只扫 llm_call/llm_call_recover ⇒ 恒 0 假阴性 ⇒ 改为全 point 扫 kv 键。",
    "[checker-fix #2] H6 口径**复原为 prereg 原文**: (a) = 「R 臂不出现旧误诊文案」; (b) = 「≥1 例逐字回放且回放目标为实质答复」。"
    "先前实现要求「tool_call 因由必须出现新文案」且「t9==t6」, 两条均**严于** prereg ⇒ 判为**实现偏离**、非判据收窄;"
    "更严变体(H6c)结果原样保留在 checks_posthoc, 未用于 alter H6 verdict。",
    "[checker-fix #3] 起手闸 false-negative 归因修正: 占用源含本方 Roslyn 编译服务器 VBCSCompiler(RSS 206MB, "
    "dotnet test 遗留), 不止 llama-server ⇒ 见 eval/rover/r482/run_arm_R_only_r482.sh 注释与 report。",
]
res["honest_boundaries"] = [
    "单夹具单次, 点估计, 无置信区间",
    "跨二进制对比(R477 db187e0eae7f26ea vs 本轮 %s)非同分布复现, 只作参考列" % res["binary_sha16_actual"],
    "上游真供应商可漂移 ⇒ Arole 非恒定基线 (本轮 Arole 空正文 %d 行 vs R477 15 行 = 实测漂移)" % A["empty_body_rows"],
    "empty_cause/retry_skipped 取自产品遥测(kv), 与供应商 usage 分列",
    "R 臂 t2-t5 由模板兜底(4 轮), 降幅 %s%% 中含该部分; prereg H6 未覆盖此质量面 ⇒ 列 posthoc" % res["kpi"]["drop_pct"],
]
out = os.path.join(D, "verdict-r482.json")
open(out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({"verdict": verdict, "kpi": res["kpi"], "kpi_vs_r477": res.get("kpi_vs_r477"),
                  "binary_match": res["binary_match"], "arms_summary": {a: {k: cur[a][k] for k in
                  ("relay_calls", "prompt", "completion", "total", "empty_body_rows", "finish_reason_hist",
                   "retry_skipped_true", "empty_cause_hist", "skip_reply_kinds", "substantive_turns",
                   "banner_replies", "old_misdiag_replies", "turn_errors", "blocked")} for a in ARMS}},
                 ensure_ascii=False, indent=1))
print("[written] %s" % out)
print("[verdict_all_pass] %s" % res["verdict_all_pass"])
