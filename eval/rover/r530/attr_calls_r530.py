#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R530 归因器具: 对 R529 三窗冻结的 adapter 逐调用落盘件做**按类分解**（只读, 不重跑臂）。

用途: R529 报告 §6 候选 3「F1 锚族为何 A1-on 更贵(w1/w2 calls 3.7x/4.7x)」+ 候选 2「降步数/合批」的
      量测前提 —— 先把「调用数」按**调用类别**拆开, 才谈得上选杠杆（skill: 优化靶点的天花板先验）。

归属纪律（承 skill: 归属必须顺序分区）:
  · 每个调用序号 → (arm, tid) 的映射**只**取自该窗 `evidence/windows/<w>/report.json` 的
    `adapter_range`（外部真值: 生成侧记录的区间）, 不做任何猜测式归属;
  · 逐调用数据取自适配器落盘件 `adapter/side-{agent|codex}-NNN.json`（= 每调用的 request/response.usage）;
  · 类别判定只读请求**结构**(n_messages / 尾消息 role 与长度 / tools_n), 不用文本启发式贴标签。

类别定义（互斥, 按尾消息形态）:
  S1   起始调用  (n_messages == 2: system + 任务 prompt)
  S2   工具回灌轮 (尾消息 role == 'tool')
  S3   注入轮     (尾消息 role == 'user' 且长度/内容与任务 prompt 不同 ⇒ 运行期注入的提示)
  S4   其它       (尾消息 role == 'assistant' 等)
输出: stdout 汇总表 + `eval/rover/r530/evidence/call-attribution-r530.json`
"""
from __future__ import annotations

import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ROUND = os.path.join(REPO, "eval/rover/r529")
OUT = os.path.join(REPO, "eval/rover/r530/evidence/call-attribution-r530.json")
SIDE = {"agent": "side-agent-%03d.json", "codex": "side-codex-%03d.json"}


def classify(rec, task_head):
    req = rec.get("request") or {}
    up = req.get("upstream_request") or {}
    tail = up.get("tail_messages") or []
    n = int(req.get("n_messages") or up.get("n_messages") or 0)
    if n <= 2 and len(tail) <= 2:
        return "S1_start", ""
    last = tail[-1] if tail else {}
    role = last.get("role")
    if role == "tool":
        return "S2_after_tool", ""
    if role == "user":
        head = (last.get("head") or "")
        if task_head and head[:60] == task_head[:60]:
            return "S3_inject", "user_tail_is_task"
        return "S3_inject", head[:60].replace("\n", " ")
    if role == "assistant":
        return "S4_other", ""
    return "S4_other", ""


def main():
    blob = {"round": "R530", "source_round": "R529", "kind": "call-attribution",
            "attribution_rule": "seq -> (arm,tid) 取自 report.json:adapter_range（顺序分区, 无猜测）",
            "windows": {}, "classes": ["S1_start", "S2_after_tool", "S3_inject", "S4_other"]}
    for w in ("w1", "w2", "w3"):
        rp = os.path.join(ROUND, "evidence/windows", w, "report.json")
        if not os.path.isfile(rp):
            blob["windows"][w] = {"error": "report.json 缺失"}
            continue
        rows = (json.load(io.open(rp, encoding="utf-8")) or {}).get("rows") or []
        adir = os.path.join(ROUND, "run-0917-2012-" + w, "adapter")
        wres = {}
        for r in rows:
            rng = r.get("adapter_range") or [0, -1]
            side = r.get("side") or "agent"
            arm, tid = r.get("arm"), r.get("tid")
            task_head = ""
            calls = []
            for seq in range(int(rng[0]), int(rng[1]) + 1):
                fp = os.path.join(adir, SIDE[side] % seq)
                if not os.path.isfile(fp):
                    calls.append({"seq": seq, "missing": True})
                    continue
                rec = json.load(io.open(fp, encoding="utf-8", errors="replace"))
                if not task_head:
                    up = (rec.get("request") or {}).get("upstream_request") or {}
                    tl = up.get("tail_messages") or []
                    for m in tl:
                        if m.get("role") == "user":
                            task_head = m.get("head") or ""
                            break
                cls, note = classify(rec, task_head)
                up = (rec.get("request") or {}).get("upstream_request") or {}
                resp = rec.get("response") or {}
                usage = resp.get("usage") or {}
                tcs = resp.get("tool_calls") or []
                calls.append({
                    "seq": seq, "cls": cls, "note": note,
                    "n_messages": (rec.get("request") or {}).get("n_messages"),
                    "tools_n": (rec.get("request") or {}).get("tools_n"),
                    "last_role": ((up.get("tail_messages") or [{}])[-1] or {}).get("role"),
                    "last_len": ((up.get("tail_messages") or [{}])[-1] or {}).get("len"),
                    "tool_calls_n": len(tcs),
                    "tool_names": sorted({str(t.get("name")) for t in tcs if isinstance(t, dict)}),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens")
                    if isinstance(usage.get("prompt_tokens_details"), dict) else None,
                    "completion_tokens": usage.get("completion_tokens"),
                    "finish_reason": resp.get("finish_reason"),
                })
            agg = {}
            for c in calls:
                k = c.get("cls") or "missing"
                a = agg.setdefault(k, {"n": 0, "prompt": 0, "completion": 0, "tool_calls": 0})
                a["n"] += 1
                a["prompt"] += int(c.get("prompt_tokens") or 0)
                a["completion"] += int(c.get("completion_tokens") or 0)
                a["tool_calls"] += int(c.get("tool_calls_n") or 0)
            wres["%s/%s" % (arm, tid)] = {"calls": len(calls), "by_class": agg, "detail": calls}
        blob["windows"][w] = wres
        print("== %s ==" % w)
        hdr = "%-14s %-4s %5s | %s" % ("arm/tid", "n", "tools", "  ".join("%-14s" % c for c in blob["classes"]))
        print(hdr)
        for k, v in wres.items():
            bc = v["by_class"]
            cells = []
            for c in blob["classes"]:
                a = bc.get(c) or {"n": 0, "prompt": 0, "completion": 0}
                cells.append("%d/%dtok" % (a["n"], a["prompt"] // 1000))
            tc = sum(a.get("tool_calls", 0) for a in bc.values())
            print("%-14s %-4d %5d | %s" % (k, v["calls"], tc, "  ".join("%-14s" % x for x in cells)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
    print("OUT=%s" % os.path.relpath(OUT, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
