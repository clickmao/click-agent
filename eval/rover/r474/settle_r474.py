#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R474 结算器 —— 分母升级: 读数面 = 供应商 usage (中继捕获), 请求面 = 宿主实发 messages。

与 R467 结算器的关系: 复用同一宿主遥测解析与判官路由口径, 新增
  (a) usage-<arm>.jsonl → prompt/completion/cache_hit/cache_miss 真值 + 成本上/下界
  (b) 实发文本的前缀结构 → 与 provider 命中 token 的单调/相关性判据 (R472 定律首验)
预注册判据见 eval/rover/r474/prereg_r474.json (跑测前落盘)。
用法: python3 settle_r474.py <dir> <ARM|ALL>
"""
import io
import json
import os
import statistics
import sys

JUDGE_HEAD = "判定用户消息相对上一轮回答"
MICRO_HEAD = "[微步骤隔离问询]"
PRICE_IN, PRICE_OUT = 0.27, 1.10        # CNY / 1M (config/base/models.yaml deepseek-flash)
HIT_DISCOUNT = 0.10                     # 命中折价假设 (下界口径; 上界 = 不折价)


def jl(p):
    rows = []
    if not os.path.exists(p):
        return rows
    for line in io.open(p, encoding="utf-8-sig"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def cat_text(msgs):
    """messages → 全文 (按序拼接; content 支持 str 或 parts)。"""
    out = []
    for m in msgs or []:
        c = m.get("content")
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            for p in c:
                if isinstance(p, dict) and isinstance(p.get("text"), str):
                    out.append(p["text"])
    return "\n".join(out)


def est_tok(s):
    return max(1, len(s) // 2)          # 与 r430 桩同口径 (仅用于与桩臂可比; 真值取 usage)


def lcp(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


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


def tel_path(d, arm):
    for cand in (os.path.join(d, "tel-%s" % arm, "host.jsonl"),
                 os.path.join(d, "rundata-%s" % arm, "data", "telemetry", "host.jsonl")):
        if os.path.exists(cand):
            return cand
    return os.path.join(d, "rundata-%s" % arm, "data", "telemetry", "host.jsonl")


RETRY_MARKER = "直接输出最终答案正文本身"


def _agg(by, key, u):
    a = by.setdefault(key, {"calls": 0, "prompt_tokens": 0, "cache_hit_tokens": 0,
                            "cache_miss_tokens": 0, "completion_tokens": 0})
    a["calls"] += 1
    for f in ("prompt_tokens", "cache_hit_tokens", "cache_miss_tokens", "completion_tokens"):
        a[f] += int(u.get(f) or 0)
    a["total_tokens"] = a["prompt_tokens"] + a["completion_tokens"]


def decompose(d, arm, r):
    """把 20 次实发调用按 (类别 × 恢复态) 分解 —— 恢复调用是「远端真花销」但宿主单列点不在 llm_call 里。

    标记法 (确定性, 不看宿主自报):
      retry   = 实发 messages 里含 RETRY_MARKER 的调用 (宿主 empty_content 后追加的纠正 system 块, +32 tok)
      recover = 同一「末条 user 文本」下, retry 的前一条调用 (裸调用, 供应商侧确实计费)
    """
    calls = jl(os.path.join(d, "calls-%s.jsonl" % arm))
    umap = {u.get("seq"): u for u in jl(os.path.join(d, "usage-%s.jsonl" % arm)) if not u.get("blocked")}
    mark = {}
    for c in calls:
        if RETRY_MARKER in cat_text(c.get("messages")):
            mark[c.get("seq")] = "retry"
    prev = {}
    for c in calls:
        lu = last_user(c)
        if mark.get(c.get("seq")) == "retry" and lu in prev:
            mark[prev[lu]] = "recover"
        prev[lu] = c.get("seq")
    by_cls, by_kind = {}, {}
    for c in calls:
        u = umap.get(c.get("seq"), {})
        k = mark.get(c.get("seq"), "normal")
        _agg(by_kind, k, u)
        txt = cat_text(c.get("messages"))
        head = last_user(c)
        if head.startswith(JUDGE_HEAD):
            cls = "judge"
        elif head.startswith(MICRO_HEAD):
            cls = "micro"
        elif (c.get("n_messages") or 0) >= 2 and head:
            cls = "main"
        else:
            cls = "other"
        _agg(by_cls, cls, u)
    for a in list(by_cls.values()) + list(by_kind.values()):
        a["total_tokens"] = a["prompt_tokens"] + a["completion_tokens"]
    ex = {f: r["provider"][f] - by_kind.get("recover", {}).get(f, 0)
          for f in ("prompt_tokens", "completion_tokens", "cache_hit_tokens", "cache_miss_tokens")}
    ex["total_tokens"] = ex["prompt_tokens"] + ex["completion_tokens"]
    ex["calls"] = r["calls_relay"] - by_kind.get("recover", {}).get("calls", 0)
    r["decomposition"] = {"by_class": by_cls, "by_kind": by_kind,
                          "recover_seq": sorted(k for k, v in mark.items() if v == "recover"),
                          "retry_seq": sorted(k for k, v in mark.items() if v == "retry"),
                          "excl_recover": ex}
    return r


def read_arm(d, arm):
    calls = jl(os.path.join(d, "calls-%s.jsonl" % arm))
    usage = jl(os.path.join(d, "usage-%s.jsonl" % arm))
    fwd = [u for u in usage if not u.get("blocked")]
    blk = [u for u in usage if u.get("blocked")]
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
    gates = [(o.get("kv") or {}).get("value") or {} for o in trows if o.get("point") == "local_turn_gate"]
    judge_ev = [(o.get("kv") or {}) for o in trows if o.get("point") == "correction_judge"]
    llm_ev = [o for o in trows if o.get("point") == "llm_call"]

    # ---- 供应商真值 ----
    pt = sum(int(u.get("prompt_tokens") or 0) for u in fwd)
    ct = sum(int(u.get("completion_tokens") or 0) for u in fwd)
    hit = sum(int(u.get("cache_hit_tokens") or 0) for u in fwd)
    miss = sum(int(u.get("cache_miss_tokens") or 0) for u in fwd)
    cost_up = pt / 1e6 * PRICE_IN + ct / 1e6 * PRICE_OUT
    cost_lo = (miss / 1e6 * PRICE_IN + hit / 1e6 * PRICE_IN * HIT_DISCOUNT + ct / 1e6 * PRICE_OUT)
    ident_ok = all(int(u.get("prompt_tokens") or 0) ==
                   int(u.get("cache_hit_tokens") or 0) + int(u.get("cache_miss_tokens") or 0) for u in fwd)

    # ---- 请求面: 实发文本 + 与历史最长公共前缀 ----
    texts, seen = [], []
    pre = []
    for c in calls:
        t = cat_text(c.get("messages"))
        best, who = 0, -1
        for j, s in enumerate(texts):
            v = lcp(s, t)
            if v > best:
                best, who = v, j
        pre.append({"seq": c.get("seq"), "chars": len(t), "est_tokens": est_tok(t),
                    "lcp_chars_vs_any_prev": best, "lcp_src_seq": texts and (calls[who].get("seq") if who >= 0 else None),
                    "lcp_est_tokens": est_tok(t[:best]) if best else 0})
        texts.append(t)
    # 主调用序列 (与 usage 前向行对齐: 同一中继经历 ⇒ 顺序一致)
    main_idx = classify(calls)[1]["main"]
    umap = {u.get("seq"): u for u in fwd}      # 按 seq 对齐 (位置对齐会被 micro 调用错位 — 首版缺陷)
    main_rows = []
    for k, i in enumerate(main_idx):
        u = umap.get(calls[i].get("seq"))
        if not u:
            continue
        main_rows.append({
            "k": k, "seq": calls[i].get("seq"), "host_est_tokens": calls[i].get("prompt_tokens_est"),
            "prompt_tokens": u.get("prompt_tokens"), "hit": u.get("cache_hit_tokens"),
            "miss": u.get("cache_miss_tokens"), "completion": u.get("completion_tokens"),
            "hit_rate": round((u.get("cache_hit_tokens") or 0) / max(1, u.get("prompt_tokens") or 1), 4),
            "ms": u.get("ms"), "lcp_est_tokens": pre[i]["lcp_est_tokens"] if i < len(pre) else None,
            "lcp_chars": pre[i]["lcp_chars_vs_any_prev"] if i < len(pre) else None,
        })
    # provider 命中 vs 实发前缀 的相关性 (单调性证据, 不做因果断言)
    pear = None
    if len(main_rows) > 2:
        xs = [r["lcp_est_tokens"] or 0 for r in main_rows]
        ys = [r["hit"] or 0 for r in main_rows]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        dx = sum((a - mx) ** 2 for a in xs) ** 0.5
        dy = sum((b - my) ** 2 for b in ys) ** 0.5
        pear = round(num / (dx * dy), 4) if dx and dy else None

    eff = [{"turn": (o.get("kv") or {}).get("turn"),
            "effective_hit_rate": (o.get("kv") or {}).get("effective_hit_rate"),
            "cache_hit_rate": (o.get("kv") or {}).get("cache_hit_rate"),
            "cacheable_tokens": (o.get("kv") or {}).get("cacheable_tokens"),
            "prompt_tokens": (o.get("kv") or {}).get("prompt_tokens")} for o in llm_ev]
    ch = [e for e in eff if e.get("effective_hit_rate") not in (None, -1, "-1")]

    cls, cidx = classify(calls)
    secs = [float(t.get("secs") or 0) for t in turns]
    r = {
        "arm": arm,
        "turns": len(turns), "turns_ok": sum(1 for t in turns if t.get("ok")),
        "secs_median": round(statistics.median(secs), 2) if secs else None,
        "secs_total": round(sum(secs), 1),
        "calls_relay": len(fwd), "calls_request_side": len(calls), "blocked": len(blk),
        "provider": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct,
                     "cache_hit_tokens": hit, "cache_miss_tokens": miss,
                     "hit_share": round(hit / max(1, pt), 4),
                     "identity_prompt_eq_hit_plus_miss": ident_ok,
                     "cost_cny_upper": round(cost_up, 6), "cost_cny_lower": round(cost_lo, 6)},
        "stub_est": {"prompt_tokens": sum(int(c.get("prompt_tokens_est") or 0) for c in calls),
                     "calls": len(calls)},
        "calls_class": cls, "main_rows": main_rows,
        "prefix": {"pearson_lcpest_vs_hit": pear,
                   "rows": [{"seq": p["seq"], "chars": p["chars"], "lcp_chars": p["lcp_chars_vs_any_prev"],
                             "lcp_est_tokens": p["lcp_est_tokens"]} for p in pre]},
        "host_llm_events": len(llm_ev), "gate_events": len(gates),
        "effective_hit_rate_rows": eff, "effective_hit_rate_computable": len(ch),
        "judge_route": {
            "events": len(judge_ev),
            "local": sum(1 for j in judge_ev if (j.get("source") or "") == "local"),
            "shortcircuit": sum(1 for j in judge_ev if (j.get("source") or "") == "remote" and int(j.get("prompt_len") or 0) == 0),
            "remote_real": sum(1 for j in judge_ev if (j.get("source") or "") == "remote" and int(j.get("prompt_len") or 0) > 0),
            "remote_fallback": sum(1 for j in judge_ev if (j.get("source") or "").startswith("remote_fallback")),
            "local_ms": [round(float(j.get("ms") or 0), 1) for j in judge_ev if (j.get("source") or "") == "local"],
            "heads": [j.get("msg_head") for j in judge_ev],
        },
        "gate_verdicts": [g.get("verdict") for g in gates],
        "gate_bases": [g.get("basis") for g in gates],
        "replies": [t.get("reply") for t in turns], "texts": [t.get("text") for t in turns],
        "stats": stats,
    }
    return r


def pct(a, b):
    return None if not b else round((1 - a / b) * 100.0, 2)


def main():
    d, arm = sys.argv[1], sys.argv[2]
    if arm != "ALL":
        r = decompose(d, arm, read_arm(d, arm))
        io.open(os.path.join(d, "arm-%s.json" % arm), "w", encoding="utf-8").write(
            json.dumps(r, ensure_ascii=False, indent=1))
        p = r["provider"]
        print("[%s] turns_ok=%s/%s calls(relay=%s req=%s blocked=%s) 供应商: prompt=%s hit=%s miss=%s comp=%s total=%s hit_share=%s" % (
            arm, r["turns_ok"], r["turns"], r["calls_relay"], r["calls_request_side"], r["blocked"],
            p["prompt_tokens"], p["cache_hit_tokens"], p["cache_miss_tokens"], p["completion_tokens"],
            p["total_tokens"], p["hit_share"]))
        print("    恒等式 prompt==hit+miss: %s | 成本上界=%.6f 下界(命中折价10%%)=%.6f CNY | 桩口径 prompt=%s" % (
            p["identity_prompt_eq_hit_plus_miss"], p["cost_cny_upper"], p["cost_cny_lower"], r["stub_est"]["prompt_tokens"]))
        print("    内外一致 relay=%s == host_llm_call=%s ⇒ %s" % (
            r["calls_relay"], r["host_llm_events"], r["calls_relay"] == r["host_llm_events"]))
        print("    分类=%s 判官路由=%s 门事件=%s" % (json.dumps(r["calls_class"], ensure_ascii=False),
                                              json.dumps({k: r["judge_route"][k] for k in ("events", "local", "shortcircuit", "remote_real", "remote_fallback")}, ensure_ascii=False),
                                              r["gate_events"]))
        dc = r["decomposition"]
        print("    分解: 类别=" + json.dumps({kk: vv["calls"] for kk, vv in dc["by_class"].items()}, ensure_ascii=False)
              + " 按态=" + json.dumps({k2: {"calls": v2["calls"], "tok": v2["total_tokens"]} for k2, v2 in dc["by_kind"].items()}, ensure_ascii=False))
        print("    recover_seq=%s retry_seq=%s ; 扣除 recover 后: calls=%s total=%s" % (
            dc["recover_seq"], dc["retry_seq"], dc["excl_recover"]["calls"], dc["excl_recover"]["total_tokens"]))
        r2 = json.dumps(r, ensure_ascii=False, indent=1)
        io.open(os.path.join(d, "arm-%s.json" % arm), "w", encoding="utf-8").write(r2)
        print("    命中真值可算条数(effective_hit_rate != -1) = %d / %d ; Pearson(lcp_est, hit)=%s" % (
            r["effective_hit_rate_computable"], len(r["effective_hit_rate_rows"]), r["prefix"]["pearson_lcpest_vs_hit"]))
        for m in r["main_rows"]:
            print("      main#%d seq=%s prompt=%-5s hit=%-5s miss=%-5s hit_rate=%-6s comp=%-4s ms=%-6s lcp_est=%-5s" % (
                m["k"], m["seq"], m["prompt_tokens"], m["hit"], m["miss"], m["hit_rate"], m["completion"], m["ms"], m["lcp_est_tokens"]))
        return

    arms = {}
    for a in ("Arole", "R"):
        p = os.path.join(d, "arm-%s.json" % a)
        if os.path.exists(p):
            arms[a] = json.load(io.open(p, encoding="utf-8"))
    A, R = arms.get("Arole"), arms.get("R")
    checks = []
    if A and R:
        pa, pr = A["provider"], R["provider"]
        tot_red = pct(pr["total_tokens"], pa["total_tokens"])
        call_red = pct(R["calls_relay"], A["calls_relay"])
        prompt_red = pct(pr["prompt_tokens"], pa["prompt_tokens"])
        checks += [
            {"id": "C1_chain_ok", "pass": A["turns_ok"] == A["turns"] and R["turns_ok"] == R["turns"] and A["blocked"] == 0 and R["blocked"] == 0,
             "value": {"Arole": "%s/%s" % (A["turns_ok"], A["turns"]), "R": "%s/%s" % (R["turns_ok"], R["turns"]),
                       "blocked": [A["blocked"], R["blocked"]]}},
            {"id": "C2_internal_external_agree",
             "pass": A["calls_relay"] == A["host_llm_events"] and R["calls_relay"] == R["host_llm_events"],
             "value": {"Arole": [A["calls_relay"], A["host_llm_events"]], "R": [R["calls_relay"], R["host_llm_events"]]}},
            {"id": "C3_provider_truth", "pass": bool(A["provider"]["identity_prompt_eq_hit_plus_miss"] and R["provider"]["identity_prompt_eq_hit_plus_miss"]),
             "value": {"Arole": A["provider"]["identity_prompt_eq_hit_plus_miss"], "R": R["provider"]["identity_prompt_eq_hit_plus_miss"]}},
            {"id": "C4_cache_hit_samples", "pass": (A["provider"]["cache_hit_tokens"] > 0 or R["provider"]["cache_hit_tokens"] > 0),
             "value": {"Arole_hit": A["provider"]["cache_hit_tokens"], "R_hit": R["provider"]["cache_hit_tokens"],
                       "Arole_first_main_hit": A["main_rows"][0]["hit"] if A["main_rows"] else None,
                       "R_first_main_hit": R["main_rows"][0]["hit"] if R["main_rows"] else None}},
            {"id": "C5_kpi_total_tokens", "pass": tot_red is not None and tot_red >= 30.0,
             "value": {"Arole_total": pa["total_tokens"], "R_total": pr["total_tokens"], "降幅_pct": tot_red,
                       "调用次数降幅_pct": call_red, "prompt降幅_pct": prompt_red,
                       "桩口径对照": {"R467_R_total": 14529, "R467_Arole_total": 32097, "R467_降幅_pct": 54.74}}},
            {"id": "C6_effective_hit_rate_computable", "pass": (A["effective_hit_rate_computable"] + R["effective_hit_rate_computable"]) > 0,
             "value": {"Arole": A["effective_hit_rate_computable"], "R": R["effective_hit_rate_computable"],
                       "rows_Arole": A["effective_hit_rate_rows"], "rows_R": R["effective_hit_rate_rows"]}},
            {"id": "C7_budget", "pass": (pa["cost_cny_upper"] + pr["cost_cny_upper"]) <= 0.15,
             "value": {"Arole_upper": pa["cost_cny_upper"], "R_upper": pr["cost_cny_upper"],
                       "sum_upper": round(pa["cost_cny_upper"] + pr["cost_cny_upper"], 6)}},
            {"id": "C8_quality_no_regression", "pass": None,
             "value": {"Arole_replies_nonempty": sum(1 for x in A["replies"] if x),
                       "R_replies_nonempty": sum(1 for x in R["replies"] if x),
                       "Arole_asks": A["stats"].get("asks"), "R_asks": R["stats"].get("asks"),
                       "Arole_errors": A["stats"].get("errors"), "R_errors": R["stats"].get("errors"),
                       "identical_replies": sum(1 for x, y in zip(A["replies"], R["replies"]) if x == y),
                       "common_reply_slots": min(len(A["replies"]), len(R["replies"]))}},
        ]
    # ---- 事后判据 (预注册 C2 按字面被证伪 ⇒ 单列, 不改预注册文本) ----
    posthoc = []
    if A and R:
        da, dr = A["decomposition"], R["decomposition"]
        posthoc.append({"id": "P1_recover_attribution",
                        "note": "C2 按字面 20 != 16 失败 ⇒ 逐点归因: 差值全部来自 llm_call_recover(empty_content 重试) 的裸调用, "
                                "该点只记 first_completion_tokens, 不记 prompt/缓存 ⇒ 产品自记账漏计 recover 的 prompt 面",
                        "value": {"Arole_recover_calls": da["by_kind"].get("recover", {}).get("calls", 0),
                                  "Arole_recover_prompt": da["by_kind"].get("recover", {}).get("prompt_tokens", 0),
                                  "R_recover_calls": dr["by_kind"].get("recover", {}).get("calls", 0),
                                  "R_recover_prompt": dr["by_kind"].get("recover", {}).get("prompt_tokens", 0),
                                  "identity_calls": A["calls_relay"] == A["host_llm_events"] + da["by_kind"].get("recover", {}).get("calls", 0),
                                  "identity_calls_R": R["calls_relay"] == R["host_llm_events"] + dr["by_kind"].get("recover", {}).get("calls", 0)}})
        ea, er = da["excl_recover"], dr["excl_recover"]
        posthoc.append({"id": "P2_降幅分解",
                        "note": "把降幅拆成 (a) 门控减少的调用面 (b) 重试面 分别读数, 避免把「重试变少」记成「r1 增益」",
                        "value": {"Arole_excl_recover_total": ea["total_tokens"], "R_excl_recover_total": er["total_tokens"],
                                  "降幅_pct": pct(er["total_tokens"], ea["total_tokens"]),
                                  "Arole_calls_excl": ea["calls"], "R_calls_excl": er["calls"]}})
        posthoc.append({"id": "P3_effective_hit_rate_gt1",
                        "note": "产品 effective_hit_rate = hit / cacheable(=上轮 prompt) ⇒ 可 >1 (本臂 3 处); 红线 97% 的分母口径需固化 (R469 遗留)",
                        "value": {"Arole_gt1": [x for x in A["effective_hit_rate_rows"] if isinstance(x.get("effective_hit_rate"), (int, float)) and x["effective_hit_rate"] > 1],
                                  "R_gt1": [x for x in R["effective_hit_rate_rows"] if isinstance(x.get("effective_hit_rate"), (int, float)) and x["effective_hit_rate"] > 1]}})
    g = os.path.join(d, "selfcheck_guard.json")
    checks.append({"id": "C9_guard_instrument", "pass": (json.load(io.open(g, encoding="utf-8")).get("verdict") == "PASS") if os.path.exists(g) else False,
                   "value": json.load(io.open(g, encoding="utf-8")).get("verdict") if os.path.exists(g) else "missing"})
    ab = os.path.join(d, "budget-aborted.json")
    if os.path.exists(ab):
        checks.append({"id": "C10_aborted_pilot_cost_counted", "pass": True,
                       "value": json.load(io.open(ab, encoding="utf-8"))["cost_cny_upper"]})
    verdict = {
        "round": "R474", "dir": d,
        "arms": {a: {"calls": r["calls_relay"], "provider": r["provider"], "turns_ok": r["turns_ok"],
                     "hit_share": r["provider"]["hit_share"], "calls_class": r["calls_class"]} for a, r in arms.items()},
        "checks": checks,
        "posthoc": posthoc,
        "artifact_defects_found": ["flags 生成器把配置目录当文件 (IsADirectoryError) ⇒ 该轮 2 次真实调用被中止并单列记账",
                                  "端点改写正则误含 /user/balance ⇒ 已排除 (余额面非聊天面; dummy key 下只读 401 不计费)",
                                  "自检器正控首版把 max_cny 硬编码为 0.0 导致正控假红 ⇒ 已参数化"],
    }
    io.open(os.path.join(d, "verdict-r474.json"), "w", encoding="utf-8").write(
        json.dumps(verdict, ensure_ascii=False, indent=1))
    print(json.dumps(verdict["arms"], ensure_ascii=False, indent=1))
    for c in checks:
        print("%-40s pass=%-5s %s" % (c["id"], c["pass"], json.dumps(c["value"], ensure_ascii=False)[:220]))


if __name__ == "__main__":
    main()
