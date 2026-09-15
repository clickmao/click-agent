#!/usr/bin/env python3
"""prompt 缓存命中率 KPI —— **首要 KPI** (口径用户钦定 R380, 2026-09-13)。

口径 (逐字依据: "将缓存命中率计算只计算需要命中的部分，当前轮新增不计入，因为肯定不触发缓存"):
  有效命中率 = cache_hit_tokens / min(本轮 prompt_tokens, 上一轮同会话 prompt_tokens)
  · 分母 = "需要命中的部分" = 上一轮已发前缀 (本轮新增**不计入**, 新增必然不命中)
  · 会话首轮无"需要命中"部分 → 不适用 (不并入比率)
  · 缺口 ≤64 token 属缓存单元边界对齐损耗 (正常)

红线 (用户钦定): 多轮会话**第 2 轮起** 有效命中率 ≥ 97% (R393 OOB 由 95% 提高; 目标 98~99%); 越线必须查因并修复。
  用户逐字: "一旦越过红线必然检查问题为什么发生并修复" → 本脚本对每个越线轮给出数值 + 诊断入口;
  代码侧闸门见 src/agent.modelqueue/PromptCacheRedline.cs (越线即 LogWarning + cache_redline_violation 遥测)。

参考值: 旧口径 hit/(hit+miss) 一并列出 (含本轮新增, 仅作参考, **不作判定口径**)。

分通道段 (R471, **只增不改**): 读**产品实发字段** `cache_channel` / `shared_prefix_hit_tokens` /
  `shared_prefix_hit_rate` (键名派生自 src/agent.modelqueue/PromptCacheKpi.cs:135-140 ChannelFields)。
  铁律 (fail-closed):
   ① 行内缺 `cache_channel` ⇒ 计入 `unreported.absent_field` —— **既不得算 0, 也不得冒充 shared_prefix**;
   ② `cache_channel` 落在三级之外 ⇒ `unreported.invalid_value`;
   ③ 非 `shared_prefix` 通道上的 `shared_prefix_*` 必须为 -1 (禁双计) ⇒ 否则 `violations[kind=double_count]` 判红;
   ④ `shared_prefix` 通道 hit=-1 (提供方未上报) ⇒ **不入命中求和**, 计 `hit_na` (不得当 0);
   ⑤ `derived_recompute` 列用同规则**离线重算** (对照 R470 派生读数), **禁止与实发列相加/混算** ——
      真实历史遥测 (R470 打点之前) 没有这三个字段, R470 报出的 shared_prefix=43 是**推导值**, 不是实发值。

数据源: data/telemetry/host.jsonl (point=llm_call, 字段在 kv 内)
用法: kpi_cache_hit.py [--since ISO8601] [--file PATH] [--json OUT]
退出码: 0 = 达标/无多轮数据; 1 = 存在越线 **或 R471 分通道判据判红**; 2 = 数据缺失
"""
import argparse, io, json, os, sys
from datetime import datetime

REDLINE = 0.97
DEFAULT_TEL = "data/telemetry/host.jsonl"


def load(path, since=None):
    if not os.path.exists(path):
        print(f"数据缺失: {path}"); sys.exit(2)
    rows = []
    for line in io.open(path, encoding="utf-8-sig", errors="replace"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if since and str(r.get("ts", "")) < since:
            continue
        rows.append(r)
    return rows


def num(v, d=-1):
    try:
        return int(v)
    except Exception:
        return d


# ── R471: 分通道聚合 (只读产品实发字段; 缺字段 fail-closed, 禁推导冒充) ──────────
CHANNELS = ("same_session", "shared_prefix", "unknown")


def chan_of(prompt_tokens, last_prompt_tokens):
    """产品口径逐字移植 (PromptCacheKpi.Channel, src/agent.modelqueue/PromptCacheKpi.cs:117-118)。"""
    return "unknown" if prompt_tokens <= 0 else ("same_session" if last_prompt_tokens > 0 else "shared_prefix")


def aggregate_channels(calls):
    """按 llm_call 逐行读**实发**通道字段并聚合。

    返回 dict: emitted(实发) / unreported(缺字段或非法值) / derived_recompute(离线重算对照, 禁混算)
               / conservation(守恒) / violations(判红明细) / verdict。
    """
    emitted = dict.fromkeys(CHANNELS, 0)
    derived = dict.fromkeys(CHANNELS, 0)
    absent = invalid = 0
    hit_sum = miss_sum = hit_reported = hit_na = 0
    derived_hit_sum = 0
    violations = []
    last_prompt = {}
    for r in calls:
        kv = r.get("kv") or {}
        pt = num(kv.get("prompt_tokens"), 0)
        sk = kv.get("agent_session") or ""
        prev = last_prompt.get(sk, 0)
        dc = chan_of(pt, prev)                      # 派生列 (对照 R470, 独立重算)
        derived[dc] += 1
        if dc == "shared_prefix":
            h = num(kv.get("cache_hit_tokens"), -1)
            if h >= 0:
                derived_hit_sum += h
        if sk:
            last_prompt[sk] = pt
        # ── 实发列 ──
        if "cache_channel" not in kv:
            absent += 1
            continue
        ch = kv.get("cache_channel")
        if ch not in CHANNELS:
            invalid += 1
            continue
        emitted[ch] += 1
        sh = num(kv.get("shared_prefix_hit_tokens"), -2)     # -2 = 字段缺失/不可解析
        sr_raw = kv.get("shared_prefix_hit_rate", None)
        sr = num(sr_raw, -2) if sr_raw is not None else -2
        if ch != "shared_prefix":
            # 禁双计: 非该通道两字段必须显式为 -1
            if sh >= 0 or sr >= 0:
                violations.append({"kind": "double_count", "channel": ch, "ts": r.get("ts"),
                                   "shared_prefix_hit_tokens": sh, "shared_prefix_hit_rate": sr_raw,
                                   "why": "非 shared_prefix 通道的 shared_prefix_* 必须 -1 (禁双计)"})
            elif sh == -2 or sr == -2:
                violations.append({"kind": "wiring_hole", "channel": ch, "ts": r.get("ts"),
                                   "shared_prefix_hit_tokens": sh, "shared_prefix_hit_rate": sr_raw,
                                   "why": "非 shared_prefix 通道的两字段必须显式铺 -1 (缺失 = 接线不完整)"})
            continue
        if sh < 0:
            hit_na += 1                                      # 未上报: 不入求和, 不得当 0
        else:
            hit_sum += sh
            hit_reported += 1
            miss_sum += max(num(kv.get("cache_miss_tokens"), 0), 0)
    total = len(calls)
    emitted_rows = sum(emitted.values())
    conserved = emitted_rows + absent + invalid == total
    return {
        "semantics": "只读实发字段 cache_channel/shared_prefix_hit_tokens/shared_prefix_hit_rate; "
                     "缺字段 ⇒ unreported (禁 0 / 禁 shared_prefix 冒充); 非 shared_prefix 通道两字段须 -1 (禁双计)",
        "emitted": {
            "rows": emitted_rows,
            "by_channel": dict(emitted),
            "shared_prefix": {
                "calls": emitted["shared_prefix"],
                "hit_tokens": hit_sum,
                "hit_reported": hit_reported,
                "hit_na": hit_na,
                "rate_weighted": round(hit_sum / (hit_sum + miss_sum), 4) if (hit_sum + miss_sum) > 0 else -1,
                "unit": "token",
            },
        },
        "unreported": {"absent_field": absent, "invalid_value": invalid, "total": absent + invalid},
        "derived_recompute": {
            "rows": total, "by_channel": dict(derived), "shared_prefix_hit_tokens": derived_hit_sum,
            "note": "对照列 (R470 派生口径, 独立重算); **禁止与 emitted 相加/混算** —— 实发字段是 R470 起才铺的, "
                    "历史遥测 0 行含此字段",
        },
        "conservation": {"emitted_rows": emitted_rows, "unreported": absent + invalid, "calls": total,
                         "ok": conserved, "identity": "emitted.rows + unreported.total == calls"},
        "violations": violations,
        "verdict": "PASS" if (conserved and not violations) else "FAIL_CHANNEL_SEMANTICS",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="ISO8601 起始 (含)")
    ap.add_argument("--file", default=DEFAULT_TEL)
    ap.add_argument("--json", dest="json_out", default=None)
    a = ap.parse_args()

    rows = load(a.file, a.since)
    calls = [r for r in rows if r.get("point") == "llm_call"]
    viol_points = [r for r in rows if r.get("point") == "cache_redline_violation"]

    # 逐会话按时间流重建"需要命中的部分"
    sessions = {}
    order = []
    for r in calls:
        kv = r.get("kv") or {}
        sk = kv.get("agent_session") or kv.get("session") or "?"
        if sk not in sessions:
            sessions[sk] = {"calls": [], "last_prompt": 0}
            order.append(sk)
        s = sessions[sk]
        pt = num(kv.get("prompt_tokens"), 0)
        hit = num(kv.get("cache_hit_tokens"), -1)
        miss = num(kv.get("cache_miss_tokens"), -1)
        cacheable = min(pt, s["last_prompt"]) if s["last_prompt"] > 0 else 0
        eff = round(hit / cacheable, 4) if (cacheable > 0 and hit >= 0) else None
        turn = num(kv.get("turn"), 0)
        s["calls"].append({"ts": r.get("ts"), "turn": turn, "prompt": pt, "hit": hit, "miss": miss,
                           "cacheable": cacheable, "effective": eff})
        s["last_prompt"] = pt

    # 聚合
    by_turn = {}
    tot_hit = tot_cacheable = tot_rep_hit = tot_rep_miss = 0
    unreported = 0
    violations = []
    multi_sessions = 0
    for sk in order:
        s = sessions[sk]
        multi = len([c for c in s["calls"] if c["turn"] >= 2 or len(s["calls"]) > 1]) > 1
        if multi:
            multi_sessions += 1
        for c in s["calls"]:
            if c["hit"] < 0:
                unreported += 1
                continue
            tot_rep_hit += c["hit"]; tot_rep_miss += max(c["miss"], 0)
            if c["effective"] is not None:
                t = by_turn.setdefault(c["turn"], {"hit": 0, "cacheable": 0, "calls": 0})
                t["hit"] += c["hit"]; t["cacheable"] += c["cacheable"]; t["calls"] += 1
                tot_hit += c["hit"]; tot_cacheable += c["cacheable"]
                if c["turn"] >= 2 and c["effective"] < REDLINE:
                    violations.append({"session": sk, "turn": c["turn"], "prompt": c["prompt"],
                                       "cacheable": c["cacheable"], "hit": c["hit"],
                                       "miss": c["miss"], "effective": c["effective"],
                                       "growth": c["prompt"] - c["cacheable"],
                                       "gap": c["cacheable"] - c["hit"]})

    eff_all = round(tot_hit / tot_cacheable, 4) if tot_cacheable else -1
    rep_all = round(tot_rep_hit / (tot_rep_hit + tot_rep_miss), 4) if (tot_rep_hit + tot_rep_miss) else -1
    chan = aggregate_channels(calls)     # R471: 分通道 (实发字段)

    print("=" * 74)
    print("prompt 缓存命中率 KPI (口径: 只算需要命中的部分; 本轮新增不计入) — 首要 KPI")
    print("=" * 74)
    print(f"调用数 {len(calls)}  会话数 {len(order)} (多轮 {multi_sessions})  未上报 {unreported} (不并入比率)")
    print(f"\n[首要] 多轮会话有效命中率 (红线: 第 2 轮起 ≥{REDLINE:.0%})")
    print(f"{'轮次':<6}{'调用':<6}{'需要命中':<10}{'命中':<8}{'有效命中率':<12}{'判定'}")
    for t in sorted(by_turn):
        d = by_turn[t]
        rate = d["hit"] / d["cacheable"] if d["cacheable"] else -1
        verdict = "—(冷启动不适用)" if t < 2 else ("达标 ✓" if rate >= REDLINE else "**越线 ✗ 必查因修复**")
        print(f"{t:<6}{d['calls']:<6}{d['cacheable']:<10}{d['hit']:<8}{rate:<12.4f}{verdict}")
    print(f"{'合计':<6}{'':<6}{tot_cacheable:<10}{tot_hit:<8}{eff_all:<12.4f}"
          f"{'达标 ✓' if eff_all >= REDLINE or eff_all < 0 else '**越线 ✗**'}")
    print(f"\n[参考] 旧口径 hit/(hit+miss) = {rep_all:.4f}  (含本轮新增, 不作判定口径)")

    # ── R471: 分通道段 (实发字段; 缺字段不冒充) ──
    em, un, dv = chan["emitted"], chan["unreported"], chan["derived_recompute"]
    print(f"\n[分通道·实发] 有通道字段 {em['rows']}/{len(calls)} 行 "
          f"(缺字段 {un['absent_field']}, 非法值 {un['invalid_value']}) — 缺字段**不得**冒充 0 或 shared_prefix")
    for c in CHANNELS:
        print(f"  · {c:<14}{em['by_channel'][c]:>6} 行")
    sp = em["shared_prefix"]
    print(f"[分通道·shared_prefix] 调用 {sp['calls']} | 命中求和 {sp['hit_tokens']} tok "
          f"(已上报 {sp['hit_reported']} / 未上报 {sp['hit_na']} 不计入) | 占比 {sp['rate_weighted']}")
    print(f"[分通道·对照] 派生重算 (R470 口径, 禁与实发相加): shared_prefix {dv['by_channel']['shared_prefix']} 行, "
          f"命中求和 {dv['shared_prefix_hit_tokens']} tok")
    print(f"[分通道·守恒] {chan['conservation']['identity']} ⇒ "
          f"{chan['conservation']['emitted_rows']}+{chan['conservation']['unreported']}=={chan['conservation']['calls']} "
          f"{'✓' if chan['conservation']['ok'] else '✗'}; 判红 {len(chan['violations'])} 条 ⇒ {chan['verdict']}")
    for v in chan["violations"][:6]:
        print(f"  · {v['kind']}: {v['why']} (channel={v['channel']})")

    if viol_points:
        print(f"\n[代码闸门越线记录] {len(viol_points)} 条 (point=cache_redline_violation)")
        for v in viol_points[-3:]:
            kv = v.get("kv") or {}
            print(f"  · 轮 {kv.get('turn')} rate={kv.get('effective_hit_rate')} "
                  f"cacheable={kv.get('cacheable_tokens')} prompt={kv.get('prompt_tokens')}")
    if violations:
        print(f"\n[越线明细] {len(violations)} 条 (按实测根因排查: ①messages[0] 改写 ②历史重写/砍头 "
              f"③发送≠回放字节 ④增量过大; 缺口≤64 token 属单元对齐损耗)")
        for v in violations[:6]:
            print(f"  · {v['session']} 轮{v['turn']}: 有效 {v['effective']:.4f} "
                  f"(需要命中 {v['cacheable']} 命中 {v['hit']} 缺口 {v['gap']} 本轮新增 {v['growth']})")

    out = {"since": a.since, "calls": len(calls), "sessions": len(order), "unreported": unreported,
           "effective_hit_rate": eff_all, "reference_hit_rate": rep_all, "redline": REDLINE,
           "by_turn": {str(k): v for k, v in by_turn.items()}, "violations": violations,
           "redline_points": len(viol_points),
           "channels": chan,
           "channel_verdict": chan["verdict"],
           "verdict": ("PASS" if not violations else "FAIL_REDLINE")}

    # ── 按会话判定 (VERDICT 以**最新会话**为准: 历史越线单列, 不掩盖当前状态) ──
    per_sess = []
    for sk in order:
        cs = [c for c in sessions[sk]["calls"] if c["turn"] >= 2 and c["effective"] is not None]
        if not cs:
            continue
        cap_s = sum(c["cacheable"] for c in cs)
        per_sess.append((sessions[sk]["calls"][-1]["ts"] or "", sk, len(cs),
                         round(sum(c["hit"] for c in cs) / cap_s, 4) if cap_s else -1))
    if per_sess:
        per_sess.sort()
        print("\n[按会话判定] (只列轮≥2 的会话; 判定以最新会话为准)")
        for ts, sk, n, rate in per_sess:
            ok = "达标 ✓" if rate >= REDLINE else "越线 ✗"
            print(f"  {sk[:22]:<22} 轮数={n} 有效={rate:.4f} {ok} (末次 {ts[:19]})")
        _, latest_sk, _, lr = per_sess[-1]
        out["verdict"] = "PASS" if (lr < 0 or lr >= REDLINE) else "FAIL_REDLINE"
        out["latest_session"] = latest_sk
        out["by_session"] = [{"session": sk, "turns": n, "rate": r, "last_ts": ts} for ts, sk, n, r in per_sess]
        if violations:
            print(f"  (历史越线 {len(violations)} 条仍在上面列出 — 越线闸门不遗忘; 修复后新会话应达标)")
    if a.json_out:
        json.dump(out, io.open(a.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n落盘: {a.json_out}")
    else:
        default = "eval/results/kpi_cache_hit_%s.json" % datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        os.makedirs(os.path.dirname(default), exist_ok=True)
        json.dump(out, io.open(default, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n落盘: {default}")

    print(f"VERDICT: {out['verdict']}  |  通道判据: {out['channel_verdict']}")
    return 0 if (out["verdict"] == "PASS" and chan["verdict"] == "PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
