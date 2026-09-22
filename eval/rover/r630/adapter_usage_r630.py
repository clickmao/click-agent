#!/usr/bin/env python3
"""R630 · 中继（适配器）usage 时间轴聚合 —— KPI 的**权威口径**（transcript 的 cache_* 是**末次值**，
逐跑次相加会得出错误命中率，故 token/命中率一律取中继逐调用 dump）。

口径:
  · 逐调用一条 = `<adapter>/side-agent-NNN.json`（response.usage 原样来自上游）;
  · 臂归属 = 该调用的 request.messages 里 system 正文是否含 `<spec_fidelity>` 标记
    （T 档 = 含；C 档 = 不含）——**不采信调用方自报**，只用实发消息分类;
  · 三列分列: 调用数 | 新算 prompt(= cache_miss_tokens) | completion; 命中率 = Σhit / (Σhit+Σmiss);
    缺 usage 记 `unreported` 计数（**禁静默按 0 计入**、禁并入比率）。
用法: python3 eval/rover/r630/adapter_usage_r630.py --adapter <dir> --out eval/rover/r630/cost-r630.json
"""
import argparse
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_r630 import load_anchors  # noqa: E402  (同一目录的器具; 前缀锚唯一来源)


def sys_len(upstream_req):
    """实发 system 消息长度（中继 dump 只留 tail_messages 的 len/head，不放全文 ⇒ 用**长度**分类，
    与 prefix-r630.json 的两档锚比对；不用 head 子串——尾块在正文末尾，head 截断看不到）。"""
    for m in (upstream_req or {}).get("tail_messages") or []:
        if m.get("role") == "system":
            return m.get("len")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pd", default=os.path.join(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    anchors, err = load_anchors(a.pd)
    if err:
        print("DEFECT: %s" % err)
        return 2
    t_chars, c_chars = anchors["spec"][0], anchors["default"][0]
    files = sorted(glob.glob(os.path.join(a.adapter, "side-agent-*.json")))
    agg = {k: {"calls": 0, "prompt": 0, "hit": 0, "miss": 0, "completion": 0, "unreported": 0}
           for k in ("T", "C", "unknown")}
    percall = []
    for f in files:
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            agg["unknown"]["calls"] += 1
            agg["unknown"]["unreported"] += 1
            continue
        up = ((d.get("request") or {}).get("upstream_request") or {})
        ln = sys_len(up)
        arm = "T" if ln == t_chars else ("C" if ln == c_chars else "unknown")
        u = ((d.get("response") or {}).get("usage") or {})
        agg[arm]["calls"] += 1
        if not u:
            agg[arm]["unreported"] += 1
            percall.append({"file": os.path.basename(f), "arm": arm, "sys_len": ln, "usage": None})
            continue
        agg[arm]["prompt"] += int(u.get("prompt_tokens") or 0)
        agg[arm]["completion"] += int(u.get("completion_tokens") or 0)
        h = u.get("prompt_cache_hit_tokens")
        m = u.get("prompt_cache_miss_tokens")
        if h is None or m is None:
            agg[arm]["unreported"] += 1
        else:
            agg[arm]["hit"] += int(h)
            agg[arm]["miss"] += int(m)
        percall.append({"file": os.path.basename(f), "arm": arm, "sys_len": ln,
                        "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                        "cache_hit": h, "cache_miss": m})
    if agg["unknown"]["calls"]:
        print("DEFECT: %d 条 dump 的 system 长度既不等于治疗档也不等于缺省档锚 ⇒ 器具缺陷(禁计入)" %
              agg["unknown"]["calls"])
    ident_ok = all((pc.get("prompt_tokens") is None) or
                   (pc.get("cache_hit") is None) or
                   (pc["prompt_tokens"] == pc["cache_hit"] + pc["cache_miss"]) for pc in percall)
    out = {"round": "R630", "caliber": "中继逐调用 usage（权威口径；transcript.cache_* 为末次值不作比率）",
           "adapter_dir": a.adapter, "dumps": len(files), "anchors_sys_len": {"T": t_chars, "C": c_chars},
           "identity_total_eq_hit_plus_miss": ident_ok, "per_arm": agg, "per_call": percall}
    for arm in ("T", "C"):
        den = agg[arm]["hit"] + agg[arm]["miss"]
        out["per_arm"][arm]["hit_rate_v_all"] = round(agg[arm]["hit"] / float(den), 4) if den else None
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out["per_arm"][k] for k in ("T", "C", "unknown")}, ensure_ascii=False))
    print("IDENTITY prompt==hit+miss:", ident_ok, " DUMPS=%d" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
