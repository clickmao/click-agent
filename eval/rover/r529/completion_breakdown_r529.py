#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 J4: completion 按类分解 + 天花板算式 (只出**记录列**, 阈值留待下轮; 见 prereg C4)。

三类 (逐调用机械分类, 取自 `adapter/side-<side>-NNN.json` 的 response):
  A 收尾正文 = 无 tool_calls 的调用 (最终答复正文)
  B 逐步叙述 = 有 tool_calls **且** 正文非空 (边聊边干)
  C 工具骨架 = 有 tool_calls 且正文为空 (纯调用, 不可再省)
工具回执回灌 (prompt 侧) = 请求 tail 含 role=tool 的调用的 new_prompt(=prompt-cached) 之和。

天花板算式: ceil_completion = 首呼 completion + 末呼 completion + (n_mid) × C_min
  C_min = 观测到的纯工具调用 completion 最小值 (一次工具调用的不可约底)。
输出: evidence/completion-breakdown-r529.json + 逐 (窗/臂/题族) 表。
"""
from __future__ import annotations
import argparse
import io
import json
import os

R = "/home/agentuser/AgentFramework/eval/rover/r529"
FAM = {"g1": "F1", "t1": "F2"}


def call_rows(dump_dir, side, i0, i1):
    rows = []
    for i in range(i0, i1 + 1):
        p = os.path.join(dump_dir, "side-%s-%03d.json" % (side, i))
        if not os.path.isfile(p):
            continue
        j = json.load(io.open(p, encoding="utf-8"))
        resp = j.get("response") or {}
        req = j.get("request") or {}
        up = req.get("upstream_request") or {}
        u = resp.get("usage") or {}
        tc = resp.get("tool_calls") or []
        text = (resp.get("text") or "")
        tail = up.get("tail_messages") or []
        rows.append({
            "i": i, "has_tool": bool(tc), "text_len": len(text.strip()),
            "completion": int(u.get("completion_tokens") or 0),
            "prompt": int(u.get("prompt_tokens") or 0),
            # 缓存命中数在 prompt_tokens_details / prompt_cache_hit_tokens (顶层无 cached_tokens)
            "cached": int(u.get("prompt_cache_hit_tokens") or (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0),
            "tail_tool": any((m or {}).get("role") == "tool" for m in tail),
            "request_id": j.get("request_id") or req.get("request_id"),
        })
    return rows


def classify(rows):
    A = sum(r["completion"] for r in rows if not r["has_tool"])
    B = sum(r["completion"] for r in rows if r["has_tool"] and r["text_len"] > 0)
    C = sum(r["completion"] for r in rows if r["has_tool"] and r["text_len"] == 0)
    cmin = min([r["completion"] for r in rows if r["has_tool"] and r["text_len"] == 0] or
               [r["completion"] for r in rows if r["has_tool"]] or [0])
    n = len(rows)
    first = rows[0]["completion"] if rows else 0
    last = rows[-1]["completion"] if rows else 0
    n_mid = max(0, n - 2)
    cmin_gap = min(rows, key=lambda r: r["completion"])["completion"] if rows else 0
    ceil = first + last + n_mid * min(cmin, cmin_gap)
    actual = A + B + C
    return {"calls": n, "A_final_text": A, "B_narration": B, "C_tool_skeleton": C,
            "C_min_per_call": cmin, "actual_completion": actual, "ceil_completion": ceil,
            "headroom_pct": round(100.0 * (1 - ceil / actual), 1) if actual else None,
            "narration_share_pct": round(100.0 * B / actual, 1) if actual else None,
            "tool_receipt_reprompt_new_prompt": sum(r["prompt"] - r["cached"] for r in rows if r["tail_tool"])}


def _dump_dir(win):
    """窗口的 adapter dump 目录 (索引每窗覆盖写, 故按 run-*-<win> 反查)。"""
    import glob
    c = sorted(glob.glob(os.path.join(R, "run-*-%s" % win)))
    return os.path.join(c[0], "adapter") if c else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=os.path.join(R, "evidence/index-r529.json"))
    ap.add_argument("--out", default=os.path.join(R, "evidence/completion-breakdown-r529.json"))
    a = ap.parse_args()
    import glob
    out = {"round": "R529", "source": "evidence/windows/*/report.json", "per_window": {}, "by_family": {}}
    for rp in sorted(glob.glob(os.path.join(R, "evidence", "windows", "*", "report.json"))):
        j = json.load(io.open(rp, encoding="utf-8"))
        win = j.get("window")
        dump = _dump_dir(win)
        rows = []
        for rec in j.get("rows", []):
            key = "%s/%s" % (rec.get("run"), rec.get("tid"))
            rng = rec.get("adapter_range") or [0, -1]
            side = "codex" if rec.get("side") == "codex" else "agent"
            cr = call_rows(dump, side, int(rng[0]), int(rng[1]))
            stat = classify(cr) if cr else {"calls": 0, "note": "no_dump_in_range"}
            stat.update({"run": rec.get("run"), "side": rec.get("side"), "family": FAM.get(rec.get("tid"), rec.get("tid")), "dump": dump})
            out["per_window"].setdefault(win, {})[key] = stat
            rows.append(stat)
        for fam in ("F1", "F2"):
            fr = [r for r in rows if r.get("family") == fam and r.get("calls")]
            if not fr:
                continue
            agg = {k: sum(r[k] for r in fr) for k in ("A_final_text", "B_narration", "C_tool_skeleton",
                                                      "actual_completion", "ceil_completion", "calls",
                                                      "tool_receipt_reprompt_new_prompt")}
            agg["headroom_pct"] = round(100.0 * (1 - agg["ceil_completion"] / agg["actual_completion"]), 1) if agg["actual_completion"] else None
            agg["narration_share_pct"] = round(100.0 * agg["B_narration"] / agg["actual_completion"], 1) if agg["actual_completion"] else None
            out["by_family"].setdefault(fam, {})[win] = agg
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("%-4s %-10s %-5s %5s %8s %8s %8s %10s %9s" % ("win", "arm/tid", "fam", "calls", "A末端", "B叙述", "C骨架", "actual", "headroom%"))
    for win, arms in sorted(out["per_window"].items()):
        for key, s in sorted(arms.items()):
            print("%-4s %-10s %-5s %5s %8s %8s %8s %10s %9s" % (
                win, key, s.get("family"), s.get("calls"), s.get("A_final_text"), s.get("B_narration"),
                s.get("C_tool_skeleton"), s.get("actual_completion"), s.get("headroom_pct")))
    for fam, wins in sorted(out["by_family"].items()):
        for win, s in sorted(wins.items()):
            print("FAM %-3s %-4s calls=%d A=%d B=%d C=%d actual=%d ceil=%d headroom=%s%% narration=%s%% receipt_reprompt=%d" % (
                fam, win, s["calls"], s["A_final_text"], s["B_narration"], s["C_tool_skeleton"], s["actual_completion"],
                s["ceil_completion"], s["headroom_pct"], s["narration_share_pct"], s["tool_receipt_reprompt_new_prompt"]))
    print("OUT=%s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
