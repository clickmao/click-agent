#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R524 前缀稳定性机检 (用户 2026-09-17 定向: 「你往中间塞东西了？」+「上下文几乎不涨才是对的」)。

读**实发** adapter dump (full-*.json = 该次调用的 messages; side-*.json = usage), 不看代码行。
臂由调用序号区间界定 (--range A1-on=i0,i1, 与 run 脚本 logs/idx.txt 同源):
  M1 常量前缀: 处理臂 (缺省 A1-on) 在**全部窗口**的 system 段逐字节相同 (跨运行常量 ⇒ 服务端缓存前沿 = 全 system);
  M2 遥测外泄: 任何 system/user 段都不得出现 data/activity / prompt_audit / 工作区文件 标记 (R522 实测该块砍断前沿);
  M3 首调用: 每次运行首调用 cached_tokens >= 0.45 × system 字符数 且 新算 <= 2000 tok 且 cached > 2304 (R522 基线);
  M4 每步涨: 逐调用 prompt_tokens 步间增量中位 <= 700 tok (codex 同题基准 440; R522 我方 1,222 新算中位);
  M5 回灌: 工具回执字符中位 <= 400 且 p90 <= 1500, assistant 正文中位 == 0 (零过渡叙述)。
codex 只作参照列 (不参与 M1/M3/M4/M5 判定)。rc=0 仅当 M1..M5 全过; 全部读数照报。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import statistics as st
import sys

TELEMETRY_MARKERS = ("data/activity", "prompt_audit", "工作区文件", "Workspace Files")


def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def calls_of(adapter_dir: str):
    out = []
    for side_p in sorted(glob.glob(os.path.join(adapter_dir, "side-*.json"))):
        m = re.search(r"side-([a-z]+)-(\d+)\.json$", os.path.basename(side_p))
        if not m:
            continue
        side_name, idx = m.group(1), int(m.group(2))
        side = json.load(io.open(side_p, encoding="utf-8"))
        full_p = os.path.join(adapter_dir, "full-%s-%03d.json" % (side_name, idx))
        if not os.path.isfile(full_p):
            cands = glob.glob(os.path.join(adapter_dir, "full-*-%03d.json" % idx))
            if not cands:
                continue
            full_p = cands[0]
        msgs = json.load(io.open(full_p, encoding="utf-8"))
        if isinstance(msgs, dict):
            msgs = (msgs.get("request") or {}).get("messages") or []
        system = "\n".join(str(x.get("content") or "") for x in msgs if x.get("role") == "system")
        users = [str(x.get("content") or "") for x in msgs if x.get("role") == "user"]
        receipts = [len(str(x.get("content") or "")) for x in msgs if x.get("role") == "tool"]
        bodies = [len(str(x.get("content") or "")) for x in msgs
                  if x.get("role") == "assistant" and str(x.get("content") or "").strip()]
        u = ((side.get("response") or {}).get("usage") or {})
        cached = int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or u.get("prompt_cache_hit_tokens") or 0)
        prompt = int(u.get("prompt_tokens") or 0)
        comp = int(u.get("completion_tokens") or 0)
        out.append({"dir": os.path.basename(adapter_dir), "side": side_name, "idx": idx,
                    "system": system, "system_sha8": sha8(system), "users": users,
                    "receipt_chars": receipts, "body_chars": bodies,
                    "prompt": prompt, "cached": cached, "fresh": prompt - cached, "completion": comp})
    return sorted(out, key=lambda r: (r["dir"], r["side"], r["idx"]))


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else None


def p90(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return round(st.quantiles(xs, n=10)[8], 1) if len(xs) >= 10 else xs[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter-dir", action="append", required=True)
    ap.add_argument("--range", action="append", default=[], help="<臂名>=<i0>,<i1> (side=agent)")
    ap.add_argument("--treatment", default="A1-on")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ranges = {}
    for r in a.range:
        name, sp = r.split("=", 1)
        i0, i1 = (int(x) for x in sp.split(","))
        ranges[name] = (i0, i1)
    all_calls = []
    for d in a.adapter_dir:
        all_calls.extend(calls_of(d))
    if not all_calls:
        print("FAIL: 无可用 dump")
        return 3

    def pick(name):
        i0, i1 = ranges.get(name, (1, 10 ** 9))
        return [c for c in all_calls if c["side"] == "agent" and i0 <= c["idx"] <= i1]

    treat = pick(a.treatment)
    codex = [c for c in all_calls if c["side"] == "codex"]

    m1 = len({c["system"] for c in treat}) == 1 and len(treat) > 0
    m2 = all(not any(mk in c["system"] for mk in TELEMETRY_MARKERS) for c in all_calls) and \
         all(not any(mk in u for mk in TELEMETRY_MARKERS) for c in all_calls for u in c["users"])

    firsts = {}
    for c in treat:
        firsts.setdefault(c["dir"], []).append(c)
    first_rows = [{"run": k, "system_chars": len(v[0]["system"]), "cached": v[0]["cached"],
                   "fresh": v[0]["fresh"], "prompt": v[0]["prompt"]} for k, v in sorted(firsts.items())]
    m3 = all(r["cached"] >= 0.45 * r["system_chars"] and r["fresh"] <= 2000 and r["cached"] > 2304 for r in first_rows) and bool(first_rows)

    growth, fresh_all, receipt_all, body_all = [], [], [], []
    for k, v in sorted(firsts.items()):
        for i in range(1, len(v)):
            growth.append(v[i]["prompt"] - v[i - 1]["prompt"])
        fresh_all.extend(c["fresh"] for c in v)
        receipt_all.extend(x for c in v for x in c["receipt_chars"])
        body_all.extend(x for c in v for x in c["body_chars"])
    g_med, g_p90, fresh_med = med(growth), p90(growth), med(fresh_all)
    m4 = (g_med is not None and g_med <= 700) and (fresh_med is not None and fresh_med <= 600)
    r_med, r_p, b_med, b_p = med(receipt_all), p90(receipt_all), med(body_all), p90(body_all)
    m5 = (r_med is not None and r_med <= 400 and (r_p is None or r_p <= 1500)) and (b_med in (None, 0, 0.0))

    # M6 (用户定向: user 轮只留题面 + 小追加): 处理臂 user 段 <= 3200 字符, 且常量材料 [技能知识参考] 不在 user 段 (须在常量前缀)。
    user_sizes = [len("\n".join(c["users"])) for c in treat]
    user_mat = any("技能知识参考" in u for c in treat for u in c["users"])
    m6 = bool(user_sizes) and max(user_sizes) <= 3200 and not user_mat

    ref = {"codex_calls": len(codex),
           "codex_first": ({"system_chars": len(codex[0]["system"]), "cached": codex[0]["cached"],
                            "fresh": codex[0]["fresh"], "prompt": codex[0]["prompt"]} if codex else None),
           "codex_step_growth_median": med([codex[i]["prompt"] - codex[i - 1]["prompt"] for i in range(1, len(codex))]),
           "codex_receipt_chars_median": med([x for c in codex for x in c["receipt_chars"]]),
           "codex_body_median": med([x for c in codex for x in c["body_chars"]])}

    verdict = {"M1_system_constant": m1, "M2_no_telemetry_in_prompt": m2, "M3_first_call_cache": m3,
               "M4_step_growth": m4, "M5_receipts_and_narration": m5, "M6_user_turn_task_only": m6}
    blob = {"round": "R524", "treatment": a.treatment, "ranges": ranges,
            "calls_total": len(all_calls), "calls_treatment": len(treat),
            "system_chars": len(treat[0]["system"]) if treat else None,
            "system_sha8_distinct": sorted({c["system_sha8"] for c in treat}),
            "first_rows": first_rows, "user_chars_max": max(user_sizes) if user_sizes else None,
            "user_has_constant_material": user_mat,
            "step_growth_median": g_med, "step_growth_p90": g_p90, "fresh_median": fresh_med,
            "receipt_chars_median": r_med, "receipt_chars_p90": r_p,
            "assistant_body_median": b_med, "assistant_body_p90": b_p,
            "reference_codex": ref, "verdict": verdict, "pass": all(verdict.values())}
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
    print("处理臂=%s 调用=%d system 字符=%s 不同 system 段=%d (%s)" %
          (a.treatment, len(treat), blob["system_chars"], len(blob["system_sha8_distinct"]),
           ",".join(blob["system_sha8_distinct"])))
    print("首调用:", json.dumps(first_rows, ensure_ascii=False))
    print("步间涨幅中位=%s p90=%s 新算中位=%s 回执中位=%s p90=%s 正文中位=%s" %
          (g_med, g_p90, fresh_med, r_med, r_p, b_med))
    print("codex 参照:", json.dumps(ref, ensure_ascii=False))
    print("verdict:", json.dumps(verdict, ensure_ascii=False))
    return 0 if blob["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
