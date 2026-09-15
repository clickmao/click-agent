#!/usr/bin/env python3
# R470 证据生成 + 机检判据 (独立复算面: 与 C# PromptCacheKpi 同规则、不同实现 ⇒ 互为对照)
#
# 用法: python3 eval/rover/r470/real_calls.py [--neg-control]
# 产出: eval/rover/r470/real-calls.json   (真值夹具, 供 C# PromptCacheChannelTests 回放)
#       eval/rover/r470/asserts.json      (C1..C6 逐条判据 + 取值)
#       eval/rover/r470/negctl.json       (负控: 反写归因规则后的取值)
# 退出码: 0 = 全部判据通过; 1 = 有判据未通过 (门禁可用)
import json, io, os, sys, hashlib, datetime, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(ROOT, "data", "telemetry", "host.jsonl")
OUT = os.path.join(ROOT, "eval", "rover", "r470")
UNIT = 64

def load_rows():
    """逐行读取遥测; utf-8-sig 剥 BOM (utf-8 会静默吞掉首行 —— 预检实踩)。"""
    raw = open(SRC, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    rows = []
    for line in io.open(SRC, encoding="utf-8-sig"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("point") != "llm_call":
            continue
        rows.append((d.get("ts"), d["kv"]))
    rows.sort(key=lambda x: x[0])
    seen, out = collections.Counter(), []
    for ts, kv in rows:
        s = kv.get("agent_session") or ""
        has_prev = bool(s) and seen[s] > 0
        if s:
            seen[s] += 1
        out.append({
            "ts": ts, "session": s, "turn": kv.get("turn"),
            "prompt_tokens": kv.get("prompt_tokens"),
            "cache_hit_tokens": kv.get("cache_hit_tokens"),
            "cache_miss_tokens": kv.get("cache_miss_tokens"),
            "cache_hit_rate": kv.get("cache_hit_rate"),
            "cacheable_tokens": kv.get("cacheable_tokens"),
            "effective_hit_rate": kv.get("effective_hit_rate"),
            "has_same_session_predecessor": has_prev,
            "provider": kv.get("provider"), "model": kv.get("model"),
            "success": kv.get("success"), "intent": kv.get("intent"),
        })
    return sha, out

# ---- C# PromptCacheKpi 同规则的双实现 (反写版用于负控) ----
def channel(prompt, last, reversed_rule=False):
    if prompt <= 0:
        return "unknown"
    if reversed_rule:                     # 负控: 条件反写 ("有前驱才算共享前缀")
        return "shared_prefix" if last > 0 else "same_session"
    return "same_session" if last > 0 else "shared_prefix"

def shared_hit(hit, prompt, last, reversed_rule=False):
    if channel(prompt, last, reversed_rule) != "shared_prefix":
        return -1
    return -1 if hit is None else hit

def hit_rate(hit, miss):
    if hit is None or miss is None:
        return -1
    tot = hit + miss
    return -1 if tot <= 0 else round(hit / tot, 4)

def main():
    neg = "--neg-control" in sys.argv
    sha, rows = load_rows()
    checks, fails = [], []

    def chk(cid, desc, ok, value):
        checks.append({"id": cid, "desc": desc, "ok": bool(ok), "value": value})
        if not ok:
            fails.append(cid)

    # C1 计数
    chk("C1", "真实 llm_call 行数 = 43 (BOM 行不得被吞)", len(rows) == 43, len(rows))

    # C2 归因守恒
    g = collections.Counter(channel(r["prompt_tokens"], 1 if r["has_same_session_predecessor"] else 0) for r in rows)
    chk("C2", "归因守恒: shared_prefix=43 ∧ same_session=0 ∧ 总数=43",
        g.get("shared_prefix") == 43 and g.get("same_session", 0) == 0 and sum(g.values()) == 43,
        dict(g))

    # C3 通道非空 + 命中直方图
    hits = collections.Counter(r["cache_hit_tokens"] for r in rows if r["cache_hit_tokens"] > 0)
    chk("C3", "shared_prefix 通道命中>0 的调用 ≥30",
        sum(hits.values()) >= 30, sum(hits.values()))
    chk("C3b", "命中直方图 = {2048:19, 2176:7, 2304:2, 256:2, 127:2}",
        dict(sorted(hits.items())) == {127: 2, 256: 2, 2048: 19, 2176: 7, 2304: 2},
        dict(sorted(hits.items())))

    # C4 对齐例外逐条列出
    unaligned = [{"hit": r["cache_hit_tokens"], "prompt": r["prompt_tokens"], "session": r["session"]}
                 for r in rows if r["cache_hit_tokens"] > 0 and r["cache_hit_tokens"] % UNIT != 0]
    chk("C4", "非 64 对齐命中必须逐条列出 (实测 2 条, hit=127)",
        len(unaligned) == 2 and all(u["hit"] == 127 for u in unaligned), unaligned)

    # C5 K2b 可测性裁定
    same_sess = sum(1 for r in rows if r["has_same_session_predecessor"])
    eff_minus1 = sum(1 for r in rows if r["effective_hit_rate"] == -1)
    chk("C5", "K2b 有效命中率对真实流量结构性不可测: 同会话前驱=0 ⇒ eff=-1 43/43",
        same_sess == 0 and eff_minus1 == len(rows), {"same_session_predecessors": same_sess, "eff_-1": eff_minus1})

    # C6 负控 (双实现对照 + 反写必须变红)
    nc = {
        "a_有前驱时shared字段必须-1": shared_hit(2048, 5553, 5400) == -1 and hit_rate is not None,
        "b_未上报记-1不得0": shared_hit(None, 5553, 0) == -1,
        "c_prompt0记unknown": channel(0, 0) == "unknown" and shared_hit(0, 0, 0) == -1,
    }
    rev = collections.Counter(channel(r["prompt_tokens"], 1 if r["has_same_session_predecessor"] else 0, True) for r in rows)
    nc["d_反写规则下C2必红"] = rev.get("shared_prefix", 0) != 43
    chk("C6", "负控 a/b/c 全绿 ∧ d 反写后原判据不成立", all(nc.values()), nc)

    # 共享前缀通道的实得占比 (仅该通道)
    sp = [r for r in rows if channel(r["prompt_tokens"], 0) == "shared_prefix" and r["cache_hit_tokens"] > 0 and r["cache_miss_tokens"] > 0]
    rates = sorted(round(r["cache_hit_tokens"] / (r["cache_hit_tokens"] + r["cache_miss_tokens"]), 4) for r in sp)
    med = rates[len(rates) // 2] if rates else None

    art = {
        "round": "R470", "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "data/telemetry/host.jsonl", "source_sha256": sha,
        "filter": "point==llm_call", "n_calls": len(rows),
        "n_with_same_session_predecessor": same_sess,
        "channels": dict(g),
        "shared_prefix_hit_histogram": dict(sorted(hits.items())),
        "unaligned_hits": unaligned,
        "shared_prefix_hit_rate_min_med_max": [rates[0] if rates else None, med, rates[-1] if rates else None],
        "k2b_effective_hit_rate": {"minus_one": eff_minus1, "applicable": len(rows) - eff_minus1,
                                   "verdict": "真实流量 100% 不适用 (无同会话前驱) ⇒ 既有 K2b 通道对真实流量不可测"},
        "checks": checks, "failed": fails,
    }
    os.makedirs(OUT, exist_ok=True)
    json.dump(art, io.open(os.path.join(OUT, "asserts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"reversed_rule_channels": dict(rev), "negctl_booleans": nc},
              io.open(os.path.join(OUT, "negctl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if not neg:
        json.dump({"source": "data/telemetry/host.jsonl", "source_sha256": sha,
                   "extracted_at": art["generated_at"], "filter": "point==llm_call",
                   "n_calls": len(rows), "n_with_same_session_predecessor": same_sess, "calls": rows},
                  io.open(os.path.join(OUT, "real-calls.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for c in checks:
        print(f"[{'OK ' if c['ok'] else 'RED'}] {c['id']} {c['desc']} → {json.dumps(c['value'], ensure_ascii=False)[:200]}")
    print(f"shared_prefix hit-rate min/med/max = {art['shared_prefix_hit_rate_min_med_max']}")
    print(f"sha256(host.jsonl) = {sha}")
    print(f"FAILED = {fails}")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
