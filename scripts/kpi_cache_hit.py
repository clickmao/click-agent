#!/usr/bin/env python3
"""R377 (用户钦定): prompt 缓存命中率 KPI —— 从遥测离线聚合, 与 token 成本 KPI 同表。

口径 (与 src/agent.modelqueue/PromptCacheKpi.cs 严格一致):
  · 命中率 = cache_hit_tokens / (cache_hit_tokens + cache_miss_tokens), 保留 4 位;
  · 未上报 (provider 没给字段) 记 -1, **不并入比率**, 单独计数 —— "没测到" != "命中率 0%";
  · 分母为 0 同样不计入比率。
  · R379 新增: 按**会话 + 轮次**聚合, 并对用户钦定红线 (多轮会话第 2 轮起 ≥90%, 目标 98~99%) 出判定;
    轮次/会话来自 llm_call 打点的 agent_session / turn 字段 (无字段则记 unknown, 不臆造)。

用法:
  python3 scripts/kpi_cache_hit.py [遥测路径] [--json 输出路径] [--since ISO时间前缀]
默认遥测: data/telemetry/host.jsonl (UTF-8 BOM), 输出: eval/results/kpi_cache_hit_<UTC>.json
"""
import io
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEL = os.path.join(ROOT, "data", "telemetry", "host.jsonl")


def iter_rows(path):
    with io.open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def as_int(v):
    return v if isinstance(v, int) else None


def collect(path, since=None):
    agg = {"calls": 0, "reported": 0, "unreported": 0, "hit": 0, "miss": 0,
           "by_model": {}, "by_turn": {}, "by_session": {}, "samples": []}
    for row in iter_rows(path):
        if row.get("point") != "llm_call":
            continue
        ts = str(row.get("ts", ""))
        if since and ts < since:
            continue
        kv = row.get("kv") or {}
        agg["calls"] += 1
        hit, miss = as_int(kv.get("cache_hit_tokens")), as_int(kv.get("cache_miss_tokens"))
        if hit is None or miss is None or hit < 0 or miss < 0 or (hit + miss) <= 0:
            agg["unreported"] += 1
            continue
        agg["reported"] += 1
        agg["hit"] += hit
        agg["miss"] += miss
        model = str(kv.get("model") or "unknown")
        m = agg["by_model"].setdefault(model, {"calls": 0, "hit": 0, "miss": 0})
        m["calls"] += 1
        m["hit"] += hit
        m["miss"] += miss
        turn = kv.get("turn")
        turn = int(turn) if isinstance(turn, int) or (isinstance(turn, str) and turn.isdigit()) else 0
        sess = str(kv.get("agent_session") or "")
        t = agg["by_turn"].setdefault(turn, {"calls": 0, "hit": 0, "miss": 0})
        t["calls"] += 1
        t["hit"] += hit
        t["miss"] += miss
        if sess:
            s_ = agg["by_session"].setdefault(sess, {})
            st = s_.setdefault(turn, {"hit": 0, "miss": 0})
            st["hit"] += hit
            st["miss"] += miss
        agg["samples"].append({"ts": ts, "model": model, "hit": hit, "miss": miss, "turn": turn,
                               "session": sess, "rate": kv.get("cache_hit_rate")})
    total = agg["hit"] + agg["miss"]
    agg["cache_hit_rate"] = round(agg["hit"] / total, 4) if total > 0 else -1
    for m in agg["by_model"].values():
        t = m["hit"] + m["miss"]
        m["cache_hit_rate"] = round(m["hit"] / t, 4) if t > 0 else -1
    agg["by_turn"] = {str(k): dict(v, cache_hit_rate=round(v["hit"] / (v["hit"] + v["miss"]), 4)
                                   if (v["hit"] + v["miss"]) > 0 else -1)
                      for k, v in sorted(agg["by_turn"].items())}

    # R379 红线判定: 多轮会话 (轮次 ≥2 的调用) 命中率必须 ≥90%, 目标 98~99%
    REDLINE = 0.90
    multi = {k: v for k, v in agg["by_turn"].items() if int(k) >= 2 and (v["hit"] + v["miss"]) > 0}
    if multi:
        hit = sum(v["hit"] for v in multi.values())
        miss = sum(v["miss"] for v in multi.values())
        rate = round(hit / (hit + miss), 4)
        agg["redline"] = {"scope": "多轮会话第 2 轮起", "threshold": REDLINE, "target": "0.98~0.99",
                          "rate": rate, "hit": hit, "miss": miss,
                          "verdict": "PASS" if rate >= REDLINE else "FAIL",
                          "by_turn_min": min(v["cache_hit_rate"] for v in multi.values())}
    else:
        agg["redline"] = {"scope": "多轮会话第 2 轮起", "threshold": REDLINE, "verdict": "NO_DATA"}
    norm = {}
    for sk, turns in agg["by_session"].items():
        rated = {str(k): round(v["hit"] / (v["hit"] + v["miss"]), 4)
                 for k, v in sorted(turns.items()) if (v["hit"] + v["miss"]) > 0}
        t2 = {k: v for k, v in turns.items() if k >= 2 and (v["hit"] + v["miss"]) > 0}
        h = sum(v["hit"] for v in t2.values())
        ms = sum(v["miss"] for v in t2.values())
        norm[sk] = {"turns": rated, "multi_turn_rate": round(h / (h + ms), 4) if (h + ms) > 0 else -1}
    agg["by_session"] = norm
    return agg


def main(argv):
    tel = DEFAULT_TEL
    out = None
    since = None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            i += 1
            out = argv[i]
        elif a == "--since":
            i += 1
            since = argv[i]
        else:
            tel = a
        i += 1

    if not os.path.exists(tel):
        print("遥测文件不存在: %s" % tel)
        return 2

    agg = collect(tel, since)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    agg["telemetry"] = tel
    agg["generated_at"] = stamp
    agg["since"] = since

    if out is None:
        d = os.path.join(ROOT, "eval", "results")
        os.makedirs(d, exist_ok=True)
        out = os.path.join(d, "kpi_cache_hit_%s.json" % stamp)
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=1)

    rate = agg["cache_hit_rate"]
    rate_s = ("%.2f%%" % (rate * 100)) if rate >= 0 else "未上报(n/a)"
    print("prompt 缓存命中率 KPI: %s  (hit=%d miss=%d, 上报 %d/%d 次调用, %d 次未上报)"
          % (rate_s, agg["hit"], agg["miss"], agg["reported"], agg["calls"], agg["unreported"]))
    for model, m in sorted(agg["by_model"].items()):
        r = m["cache_hit_rate"]
        print("  · %-18s calls=%-3d hit=%-7d miss=%-7d rate=%s"
              % (model, m["calls"], m["hit"], m["miss"], ("%.2f%%" % (r * 100)) if r >= 0 else "n/a"))
    for turn, v in agg["by_turn"].items():
        r = v["cache_hit_rate"]
        mark = "  ← 红线内(第2轮起)" if int(turn) >= 2 else ""
        print("  · turn=%-3s calls=%-3d hit=%-7d miss=%-7d rate=%s%s"
              % (turn, v["calls"], v["hit"], v["miss"], ("%.2f%%" % (r * 100)) if r >= 0 else "n/a", mark))
    rl = agg["redline"]
    if rl["verdict"] == "NO_DATA":
        print("红线判定 (多轮第2轮起 ≥90%%): 无数据 (遥测里没有 turn≥2 的上报调用)")
    else:
        print("红线判定 (多轮第2轮起 ≥90%%): %s — 实测 %.2f%% (hit=%d miss=%d, 最低轮 %.2f%%), 目标 98~99%%"
              % (rl["verdict"], rl["rate"] * 100, rl["hit"], rl["miss"], rl["by_turn_min"] * 100))
    for sk, v in sorted(agg["by_session"].items()):
        print("  · 会话 %s 逐轮命中率: %s (多轮合计 %.2f%%)"
              % (sk, ", ".join("t%s=%.1f%%" % (k, r * 100) for k, r in v["turns"].items()),
                 v["multi_turn_rate"] * 100))
    print("落盘: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
