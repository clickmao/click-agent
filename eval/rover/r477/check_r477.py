#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R477 结算/判据器 (与 prereg_r477.json 的 C1..C8 一一对应)。

纪律:
  * 常量一律**源码派生** (fail-closed: 取不到即抛, 不硬编码兜底);
  * 归属分两通道: 供应商 usage ts 窗口(外部真值) vs 产品遥测 kv['turn'](自报), 两列分列, 不混算;
  * 「没测到」显式写 unreported, 禁冒充 0。
"""
import hashlib
import io
import json
import os
import re
import sys

ROOT = "/home/agentuser/AgentFramework"
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "eval/rover/r477")
ARMS = ("Arole", "R")
BIN = "/tmp/pub_r476/agenthost"
PREREG_BIN_SHA16 = "db187e0eae7f26ea"
MAX_CNY_UPPER = 0.15


def rd(p):
    with io.open(p, encoding="utf-8-sig") as f:
        return f.read()


def jl(p):
    out = []
    for line in rd(p).splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def src_const(path, pattern, name):
    m = re.search(pattern, rd(path))
    if not m:
        raise SystemExit("MISS(src-const): %s @ %s" % (name, path))
    return m.group(1)


# ---- 源码派生常量 (fail-closed) ----
ROUTER = os.path.join(ROOT, "src/agent.modelqueue/ModelQueueRouter.cs")
REDLINE = os.path.join(ROOT, "src/agent.modelqueue/PromptCacheRedline.cs")
BRIEF = os.path.join(ROOT, "src/agent/context/ContinuationBrief.cs")
if not os.path.exists(BRIEF):  # 目录结构可能变 ⇒ 源码内检索定位 (fail-closed)
    hits = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ROOT, "src"))
            for f in fs if f == "ContinuationBrief.cs" and "/obj/" not in dp and "/bin/" not in dp]
    if len(hits) != 1:
        raise SystemExit("MISS(src-const): ContinuationBrief.cs hits=%r" % hits)
    BRIEF = hits[0]
TEMPLATE = src_const(ROUTER, r'LocalSkipFallback\s*=\s*"([^"]+)"', "LocalSkipFallback")
BANNER = src_const(ROUTER, r'EmptyBodyBannerPrefix\s*=\s*"([^"]+)"', "EmptyBodyBannerPrefix")
VERBATIM = src_const(BRIEF, r'SettleRepeatVerbatim\s*=\s*"([^"]+)"', "SettleRepeatVerbatim")
_band_body = re.search(r"BandFields\(int turn,[^)]*\)\s*\{(.*?)\n    \}", rd(REDLINE), re.S)
if not _band_body:
    raise SystemExit("MISS(src-const): BandFields body")
BAND_KEYS = re.findall(r'\("(cache_[a-z_]+)"', _band_body.group(1))
if len(BAND_KEYS) != 7:
    raise SystemExit("MISS(src-const): BandFields keys=%r" % BAND_KEYS)
_vb = re.search(r"class BandVerdict\s*\{(.*?)\n    \}", rd(REDLINE), re.S)
if not _vb:
    raise SystemExit("MISS(src-const): BandVerdict class body")
VERDICT_MAP = dict(re.findall(r'public const string (\w+)\s*=\s*"([^"]+)"', _vb.group(1)))
VERDICTS = set(VERDICT_MAP.values())
if len(VERDICTS) < 4:
    raise SystemExit("MISS(src-const): BandVerdict enum=%r" % VERDICT_MAP)

print("源码派生: TEMPLATE=%r BANNER=%r VERBATIM=%r" % (TEMPLATE, BANNER, VERBATIM))
print("源码派生: BAND_KEYS=%s" % BAND_KEYS)
print("源码派生: VERDICTS=%s" % sorted(VERDICTS))

# 与 prereg 字段名逐位比对 (差异必须显式登记, 不得静默改名)
PRE_BAND = ["cache_band", "cache_band_source", "cache_ceiling", "cache_band_target",
            "cache_margin", "cache_growth", "cache_band_verdict"]
drift = sorted(set(PRE_BAND) ^ set(BAND_KEYS))


def sha16(p):
    if not os.path.exists(p):
        return "absent"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


data = {}
for arm in ARMS:
    d = {"usage": jl(os.path.join(D, "usage-%s.jsonl" % arm)),
         "calls": jl(os.path.join(D, "calls-%s.jsonl" % arm)),
         "tel": jl(os.path.join(D, "tel-%s/host.jsonl" % arm)),
         # turns-<arm>.jsonl 实为**单份缩进 JSON**(非逐行), 按整体解析
         "turns": json.loads(rd(os.path.join(D, "turns-%s.jsonl" % arm)))}
    data[arm] = d

res = {}
res["binary_sha16"] = sha16(BIN)
res["source_consts"] = {"template": TEMPLATE, "banner": BANNER, "verbatim": VERBATIM,
                        "band_keys": BAND_KEYS, "band_verdicts": sorted(VERDICTS)}
res["prereg_band_key_drift"] = drift

per_arm = {}
for arm in ARMS:
    d = data[arm]
    u = d["usage"]
    tel = d["tel"]
    pt = sum(int(r.get("prompt_tokens") or 0) for r in u)
    ct = sum(int(r.get("completion_tokens") or 0) for r in u)
    hit = sum(int(r.get("cache_hit_tokens") or 0) for r in u)
    miss = sum(int(r.get("cache_miss_tokens") or 0) for r in u)
    pt_count = {k: sum(1 for r in tel if r["point"] == k) for k in
                ("llm_call", "llm_call_recover")}
    empty = [r for r in u if r.get("empty_body") in (True, "true", 1, "1")]
    fr = {}
    for r in u:
        fr[str(r.get("finish_reason"))] = fr.get(str(r.get("finish_reason")), 0) + 1
    skips = [r["kv"] for r in tel if r["point"] == "local_gate_skip_reply"]
    per_arm[arm] = {
        "turns_ok": d["turns"]["stats"].get("ok"),
        "turns_n": d["turns"]["stats"].get("turns"),
        "errors": d["turns"]["stats"].get("errors"),
        "relay_calls": len(u),
        "prompt": pt, "completion": ct, "total": pt + ct,
        "hit": hit, "miss": miss,
        "hit_rate": round(hit / (hit + miss), 4) if (hit + miss) else None,
        "cost_upper": round(sum(float(r.get("cost_cny_upper") or 0) for r in u), 6),
        "blocked_402": sum(1 for r in u if int(r.get("status") or 0) == 402),
        "llm_call_rows": pt_count["llm_call"], "recover_rows": pt_count["llm_call_recover"],
        "finish_reason": fr,
        "empty_body_n": len(empty),
        "empty_body_reasoning": [int(r.get("reasoning_tokens") or 0) for r in empty],
        "skip_reply_kinds": [s.get("kind") for s in skips],
        "tele_points": sorted({r["point"] for r in tel}),
    }
res["per_arm"] = per_arm

# ---- 空正文定因面 (C5 的「为什么」): usage.seq 与 calls.seq 一一对应 ----
forensics = {}
for arm in ARMS:
    calls = {r.get("seq"): r for r in data[arm]["calls"]}
    agg = {}
    for r in data[arm]["usage"]:
        s = (calls.get(r.get("seq")) or {}).get("sampling") or {}
        k = "empty_body" if r.get("empty_body") in (True, "true", 1) else "has_content"
        a = agg.setdefault(k, {"n": 0, "finish_reason": {}, "reasoning_tokens": [],
                               "tools_n": set(), "max_tokens": set(),
                               "reasoning_effort": set(), "content_len": []})
        a["n"] += 1
        fr = str(r.get("finish_reason"))
        a["finish_reason"][fr] = a["finish_reason"].get(fr, 0) + 1
        a["reasoning_tokens"].append(int(r.get("reasoning_tokens") or 0))
        a["content_len"].append(int(r.get("content_len") or 0))
        a["tools_n"].add(s.get("tools_n"))
        a["max_tokens"].add(s.get("max_tokens"))
        a["reasoning_effort"].add(s.get("reasoning_effort"))
    for a in agg.values():
        a["tools_n"] = sorted(map(str, a["tools_n"]))
        a["max_tokens"] = sorted(map(str, a["max_tokens"]))
        a["reasoning_effort"] = sorted(map(str, a["reasoning_effort"]))
        a["reasoning_tokens_max"] = max(a.pop("reasoning_tokens") or [0])
        a["content_len_max"] = max(a.pop("content_len") or [0])
    forensics[arm] = agg
res["empty_body_forensics"] = forensics

# ---- C1 链真跑通 ----
c1 = all(per_arm[a]["turns_ok"] == 12 and per_arm[a]["turns_n"] == 12 and not per_arm[a]["errors"]
         and per_arm[a]["relay_calls"] >= 1 and per_arm[a]["blocked_402"] == 0 for a in ARMS)
# ---- C2 KPI 降幅 ----
ta, tr = per_arm["Arole"]["total"], per_arm["R"]["total"]
drop = 1.0 - tr / ta if ta else None
c2 = drop is not None and drop >= 0.30
# ---- C3 t6 复述轮·不可回放 ⇒ 降级远端 (非模板/非横幅) ----
t6 = data["R"]["turns"]["turns"][5]
t6r = t6.get("reply") or ""
deg_ev = [r["kv"] for r in data["R"]["tel"] if r["point"] == "repeat_degrade_remote"]
dg_basis = [r["kv"] for r in data["R"]["tel"]
            if r["point"] == "local_turn_gate" and "repeat_no_replayable_prev" in (r["kv"].get("basis") or "")]
c3 = (t6r.strip() != TEMPLATE.strip()) and (BANNER not in t6r) and len(t6r.strip()) > 0 \
     and (len(deg_ev) >= 1 or len(dg_basis) >= 1)
# ---- C4 t9 复述轮·可回放 ⇒ 逐字回放 + 零远端 ----
t9 = data["R"]["turns"]["turns"][8]
t8 = data["R"]["turns"]["turns"][7]
t9r = (t9.get("reply") or "")
verbatim_ok = t9r == (t8.get("reply") or "") and len(t9r.strip()) > 0
turn9_telem = [r for r in data["R"]["tel"] if r["point"] == "llm_call" and str(r["kv"].get("turn")) == "9"]
w = (t9.get("t_start"), t9.get("t_end"))
u9 = [r for r in data["R"]["usage"] if w[0] is not None and w[0] <= float(r.get("ts") or 0) <= w[1]] if all(w) else []
c4 = verbatim_ok and len(turn9_telem) == 0 and len(u9) == 0
# ---- C5 空正文定因面 ----
FIELD5 = ("finish_reason", "choices_n", "content_len", "reasoning_len", "reasoning_tokens", "empty_body")
miss5 = {a: [f for f in FIELD5 if any(f not in r for r in data[a]["usage"])] for a in ARMS}
c5 = all(not v for v in miss5.values())
# ---- C6 R476 分档实发 ----
band_rows = {}
for a in ARMS:
    rows = [r["kv"] for r in data[a]["tel"] if r["point"] == "llm_call" and all(k in r["kv"] for k in BAND_KEYS)]
    band_rows[a] = rows
c6 = (len(band_rows["Arole"]) + len(band_rows["R"])) >= 1 and all(
    str(r.get("cache_band_verdict")) in VERDICTS for a in ARMS for r in band_rows[a]) and all(
    (float(r.get("cache_ceiling", 0)) == -1 or float(r.get("cache_ceiling", 0)) > 0)
    for a in ARMS for r in band_rows[a])
# ---- C7 记账闭合 ----
c7 = all(per_arm[a]["relay_calls"] == per_arm[a]["llm_call_rows"] + per_arm[a]["recover_rows"] for a in ARMS)
rec_rows = [r["kv"] for a in ARMS for r in data[a]["tel"]
            if r["point"] == "llm_call_recover" and "prompt_tokens" in r["kv"]]
c7b = bool(rec_rows) and all(str(r.get("prompt_tokens")) not in ("", "-1") for r in rec_rows)
c7 = c7 and c7b
# ---- C8 预算与形态 ----
cost_max = max(per_arm[a]["cost_upper"] for a in ARMS)
blocked = sum(per_arm[a]["blocked_402"] for a in ARMS)
c8 = cost_max <= MAX_CNY_UPPER and blocked == 0 and res["binary_sha16"] == PREREG_BIN_SHA16

res["criteria"] = {
    "C1_chain_ok": bool(c1),
    "C2_kpi_drop_pct": round((drop or 0) * 100, 2),
    "C2_drop_ge_30": bool(c2),
    "C3_t6_substantive_not_template": bool(c3),
    "C4_t9_verbatim_replay_zero_remote": {"verbatim": bool(verbatim_ok),
                                          "telem_calls_turn9": len(turn9_telem),
                                          "usage_rows_in_window": len(u9)},
    "C4_ok": bool(c4),
    "C5_empty_body_fields_present": {"ok": bool(c5), "missing_by_arm": miss5},
    "C6_band_fields_live": {"ok": bool(c6), "rows": {a: len(band_rows[a]) for a in ARMS},
                            "verdicts": sorted({str(r.get("cache_band_verdict")) for a in ARMS for r in band_rows[a]}),
                            "sources": sorted({str(r.get("cache_band_source")) for a in ARMS for r in band_rows[a]}),
                            "targets": sorted({str(r.get("cache_target")) for a in ARMS for r in band_rows[a]}),
                            "ceilings": sorted({str(r.get("cache_ceiling")) for a in ARMS for r in band_rows[a]})},
    "C7_accounting_closure": bool(c7),
    "C8_budget_and_form": {"ok": bool(c8), "cost_max": cost_max, "blocked": blocked,
                           "bin_sha16": res["binary_sha16"]},
    "C3_evidence": {"degrade_events": len(deg_ev), "repeat_no_replayable_prev": len(dg_basis),
                    "t6_reply_len": len(t6r), "t6_reply_head": t6r[:60]},
}
res["verdict_all_pass"] = bool(c1 and c2 and c3 and c4 and c5 and c6 and c7 and c8)

# =====================================================================
# 事后判据 (checks_posthoc) —— C3/C4 的**机制**假设被真机证伪后的收窄判据。
# 证伪事实: 预注册以为「t6 前驱是模板 ⇒ 无前驱可回放 ⇒ 必走 repeat_degrade_remote 降级」,
# 真机显示回放守卫会**继续回溯**到本会话最近一条可回放答复; t9 同理(t8 是空正文横幅, 不可回放)。
# 故机制子判据不成立, 而用户可见目标成立 —— 单列, 不并入 C1..C8, 不追溯改分。
# =====================================================================
import hashlib  # noqa: E402


def sha16s(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]


def replayable(rep):
    rep = rep or ""
    return rep.strip() != "" and rep.strip() != TEMPLATE and BANNER not in rep


Rt = data["R"]["turns"]["turns"]
Rby = {t["turn"]: t for t in Rt}
r6 = Rby.get(6, {}).get("reply") or ""
r8 = Rby.get(8, {}).get("reply") or ""
r9 = Rby.get(9, {}).get("reply") or ""
last_replay = max([t["turn"] for t in Rt if t["turn"] < 6 and replayable(t.get("reply"))] or [0])

# --- 三条证据链的器具 ---
GRID = json.load(io.open(os.path.join(ROOT, "eval/rover/r438/grid/task-p12.json"),
                         encoding="utf-8-sig"))["turns"]



def tel_epoch(r):
    """产品遥测 ts = ISO8601 UTC ('...8413084Z'); 供应商 usage ts = epoch 秒。统一到 epoch 秒。"""
    v = r.get("ts")
    if isinstance(v, (int, float)):
        return float(v)
    import datetime as _dt
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?", str(v))
    if not m:
        raise ValueError("无法解析遥测 ts: %r" % (v,))
    frac = (m.group(2) or "")[:7]
    return _dt.datetime.fromisoformat(m.group(1) + frac).replace(tzinfo=_dt.timezone.utc).timestamp()

def in_win(x, t):
    return bool(t.get("t_start") and t.get("t_end") and float(t["t_start"]) <= x <= float(t["t_end"]))


def usage_in(no):
    return [u for u in data["R"]["usage"] if in_win(float(u["ts"]), Rby[no])]


skips = [r["kv"] for r in data["R"]["tel"] if r["point"] == "local_gate_skip_reply"]
skip_of_input = {}
for s in skips:
    skip_of_input.setdefault(s.get("msg_sha16"), s)          # 输入指纹对齐 (源: LocalInputFingerprint.Sha16)
sk6, sk9 = skip_of_input.get(sha16s(GRID[5])), skip_of_input.get(sha16s(GRID[8]))
verb = [s for s in skips if s.get("kind") == VERBATIM]
tmpl = [s for s in skips if s.get("kind") == "template"]
# 归属漂移: 产品遥测把远端调用记到某轮, 而其 ts 不落在该轮窗口内
drift_n, drift_detail = 0, []
for r in data["R"]["tel"]:
    if r["point"] != "llm_call":
        continue
    no = r["kv"].get("turn")
    if no is None or str(no) not in {str(t["turn"]) for t in Rt}:
        continue
    try:
        ts = tel_epoch(r)
    except (TypeError, ValueError):
        continue
    t = Rby[int(no)]
    if not in_win(ts, t):
        drift_n += 1
        drift_detail.append({"turn": no, "ts": round(ts, 3), "t_start": t.get("t_start"),
                             "t_end": t.get("t_end"), "off_s": round(ts - float(t.get("t_end") or 0), 3)})
attr9 = [r for r in data["R"]["tel"] if r["point"] == "llm_call" and str(r["kv"].get("turn")) == "9"]
u9 = usage_in(9)
ph = {
    "P1_t6_非模板实质_且逐字等于最近可回放前驱": {
        "pass": bool(r6.strip() and r6.strip() != TEMPLATE and BANNER not in r6
                     and r6 == (Rby.get(last_replay, {}).get("reply") or "")),
        "replay_from_turn": last_replay, "t6_len": len(r6), "t6_sha16": sha16s(r6)},
    "P2_t9_可见回复=本地逐字回放_且零远端(因果归属)": {
        "pass": bool(r9 == r6 and not u9 and sk9 and sk9.get("kind") == VERBATIM
                     and int(sk9.get("chars") or -1) == len(r9)
                     and all(tel_epoch(r) > float(Rby[9]["t_end"]) for r in attr9)),
        "t9_eq_last_replayable": r9 == r6, "relay_rows_in_window": len(u9),
        "skip_kind_by_input_fp": (sk9 or {}).get("kind"),
        "skip_chars_vs_reply": [(sk9 or {}).get("chars"), len(r9)],
        "turn_attributed_calls": len(attr9),
        "attributed_calls_after_reply_emitted": all(tel_epoch(r) > float(Rby[9]["t_end"]) for r in attr9),
    },
    "P3_回放对象已从模板升级为实质答案(按输入指纹对齐遥测与用户所见)": {
        "pass": bool(len(verb) == 2 and len(tmpl) == 4 and r6 != TEMPLATE and r6 != r8
                     and r9 == r6 and sk6 and sk9 and sk6.get("kind") == VERBATIM
                     and sk9.get("kind") == VERBATIM
                     and int(sk6.get("chars") or -1) == len(r6) and int(sk9.get("chars") or -1) == len(r9)
                     and BANNER not in r6 and BANNER not in r9),
        "verbatim_skips": len(verb), "template_skips": len(tmpl),
        "t6_input_fp": sha16s(GRID[5]), "t9_input_fp": sha16s(GRID[8]),
        "skip_fps": [s.get("msg_sha16") for s in skips],
        "t6_len": len(r6), "t9_len": len(r9), "t8_len(banner)": len(r8)},
    "P4_归属漂移计数(单列, 不判红)": {
        "product_turn_attributed_calls_outside_turn_window": drift_n,
        "detail": drift_detail[:6],
        "note": "产品按 turn 记账, 但其 ts 落在该轮可见回复窗口之外 ⇒ 因果上不足以归因该轮回复; "
                "外部真值(供应商 usage ts)与因果(回复已产出)两通道为准。"},
}
res["checks_posthoc"] = ph
res["checks_posthoc_all_pass"] = bool(all(v.get("pass", True) for v in ph.values()))
res["posthoc_note"] = ("C3/C4 预注册的是**机制**子判据(repeat 轮必须出现降级事件 / t9 逐字等于 t8), "
                       "真机证伪: 守卫按「最近可回放」回溯, 恰好证明 R475 守卫修好了 R474 的模板回放缺陷; "
                       "P1..P3 为同一用户可见目标的收窄判据。")


with io.open(os.path.join(D, "verdict-r477.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("\n%-28s %-10s %-10s" % ("指标", "Arole", "R"))
for k, lbl in (("relay_calls", "远端调用数"), ("prompt", "prompt_tokens"), ("completion", "completion"),
               ("total", "total_tokens"), ("hit", "cache_hit"), ("hit_rate", "命中率"),
               ("cost_upper", "成本上界CNY"), ("turns_ok", "turns_ok")):
    print("%-28s %-10s %-10s" % (lbl, per_arm["Arole"][k], per_arm["R"][k]))
print("\nKPI 降幅 = %.2f%% (C2>=30%%: %s)" % (res["criteria"]["C2_kpi_drop_pct"], c2))
print("C1=%s C3=%s C4=%s C5=%s C6=%s C7=%s C8=%s" % (c1, c3, c4, c5, c6, c7, c8))
print("ALL_PASS=%s" % res["verdict_all_pass"])
print("\n空正文: Arole=%d R=%d | finish_reason: %s" % (
    per_arm["Arole"]["empty_body_n"], per_arm["R"]["empty_body_n"], per_arm["R"]["finish_reason"]))
banner = {}
for a in ARMS:
    ts = data[a]["turns"]["turns"]
    banner[a] = sum(1 for t in ts if BANNER in (t.get("reply") or ""))
print("用户可见横幅(空正文): Arole=%d/12 R=%d/12" % (banner["Arole"], banner["R"]))
print("空正文定因: %s" % json.dumps(forensics, ensure_ascii=False))
print("skip_reply kinds R=%s" % per_arm["R"]["skip_reply_kinds"])
print("分档字段漂移(预注册 vs 源码): %s" % (drift or "无"))
print("事后判据 checks_posthoc: %s ALL=%s" % (
    json.dumps({k: v.get("pass", "n/a") for k, v in ph.items()}, ensure_ascii=False),
    res["checks_posthoc_all_pass"]))
print("  P2 明细: %s" % json.dumps(ph["P2_t9_可见回复=本地逐字回放_且零远端(因果归属)"], ensure_ascii=False))
print("  P4 漂移: %s" % json.dumps(ph["P4_归属漂移计数(单列, 不判红)"], ensure_ascii=False))
print("[written] %s" % os.path.join(D, "verdict-r477.json"))
