#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计划路由 KPI 汇总/对照 (v0.22.0 exp9 D6)

用途: 从遥测 (data/telemetry/host.jsonl) 抽出**计划级**真实数字, 支撑"优化前后同题对照":
  ① LLM 调用数        ② tokens (prompt+completion)        ③ 端到端 ms (计划窗口)
  ④ 前端可见节点数 (plan.created 公告的节点数)  ＋ 本地先行节点数 / 真重叠 µs

为什么需要它: 用户口径要求"评价一律看 KPI, 同题优化前后要对比"。散在 jsonl 里的
plan/plan_node/plan_route/llm_call 点位本身不构成对照表; 会话级汇总一直缺 (R381 缺口)。

用法:
  python3 scripts/kpi_plan_route.py                     # 汇总 data/telemetry/host.jsonl 里所有计划
  python3 scripts/kpi_plan_route.py --telemetry X.jsonl  # 指定文件
  python3 scripts/kpi_plan_route.py --compare A.jsonl B.jsonl  # 同题对照 (A=基线, B=优化后)
  python3 scripts/kpi_plan_route.py --selftest           # 机检: 合成数据 → 断言聚合正确

诚实边界: 归因靠**时间窗口** (plan_route.ts → plan.ts): 同窗口内若有别的并发请求的 llm_call,
会计入本计划 → 并发场景数字偏大, 故输出里给出窗口与被计入的 llm_call 数, 不藏。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

DEFAULT_TELEMETRY = os.path.join("data", "telemetry", "host.jsonl")


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_events(path: str) -> list[dict]:
    """读遥测 (utf-8-sig: host.jsonl 带 BOM —— R373 踩过)。"""
    events: list[dict] = []
    if not os.path.exists(path):
        return events
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _kv(ev: dict) -> dict:
    kv = ev.get("kv")
    return kv if isinstance(kv, dict) else {}


def aggregate(events: list[dict]) -> list[dict]:
    """按 plan_id 归集: 路由 → 节点 → 结论 → 窗口内 LLM 调用。"""
    plans: dict[str, dict] = {}
    llm_calls = [e for e in events if e.get("point") == "llm_call"]

    for ev in events:
        point = ev.get("point")
        if point not in ("plan_route", "plan", "plan_node", "plan_local_first", "plan_local_first_overlap"):
            continue
        kv = _kv(ev)
        pid = kv.get("plan_id")
        if not pid:
            continue
        rec = plans.setdefault(pid, {
            "plan_id": pid, "route": None, "summary": None, "nodes": [],
            "local_first": None, "overlap": None, "ts_first": None, "ts_last": None,
        })
        ts = ev.get("ts")
        if ts:
            rec["ts_first"] = ts if rec["ts_first"] is None or ts < rec["ts_first"] else rec["ts_first"]
            rec["ts_last"] = ts if rec["ts_last"] is None or ts > rec["ts_last"] else rec["ts_last"]
        if point == "plan_route":
            rec["route"] = kv
        elif point == "plan":
            rec["summary"] = kv
        elif point == "plan_node":
            rec["nodes"].append(kv)
        elif point == "plan_local_first":
            rec["local_first"] = kv
        elif point == "plan_local_first_overlap":
            rec["overlap"] = kv

    out = []
    for rec in plans.values():
        summary = rec["summary"] or {}
        route = rec["route"] or {}
        overlap = rec["overlap"] or {}
        local_first = rec["local_first"] or {}
        # 窗口 = 计划构建 → 执行结论; 窗口内的 llm_call 计入本计划 (并发时会偏大 → 输出明细)
        in_window = []
        if rec["ts_first"] and rec["ts_last"]:
            t0, t1 = _ts(rec["ts_first"]), _ts(rec["ts_last"])
            in_window = [e for e in llm_calls
                         if e.get("ts") and t0 <= _ts(e["ts"]) <= t1]
        # 结论点可能早于最后一个节点事件/晚于 —— 用宽窗口再兜一次 (plan 点本身即结论)
        kv_calls = [_kv(e) for e in in_window]
        ms = [c.get("ms", 0) or 0 for c in kv_calls]
        window_ms = 0
        if rec["ts_first"] and rec["ts_last"]:
            window_ms = int((_ts(rec["ts_last"]) - _ts(rec["ts_first"])).total_seconds() * 1000)
        out.append({
            "plan_id": rec["plan_id"],
            "nodes_total": summary.get("nodes", route.get("nodes", len(rec["nodes"]))),
            "local_nodes": route.get("local", 0),
            "hybrid_nodes": route.get("hybrid", 0),
            "remote_nodes": route.get("remote", 0),
            "local_ok": summary.get("local_ok", 0),
            "local_failed": summary.get("local_failed", 0),
            "skipped": summary.get("skipped", 0),
            "local_tokens": summary.get("local_tokens", 0),
            "local_first_nodes": (overlap.get("nodes", summary.get("local_first_nodes", 0))),
            "local_first_us": overlap.get("local_first_us", 0),
            "overlap_us": overlap.get("overlap_us", summary.get("overlap_us", 0)),
            "remote_wait_us": overlap.get("remote_wait_us", summary.get("remote_wait_us", 0)),
            "wait_nodes": summary.get("wait_nodes", 0),
            "wait_us": summary.get("wait_us", 0),
            "llm_calls": len(in_window),
            "prompt_tokens": sum(c.get("prompt_tokens", 0) or 0 for c in kv_calls),
            "completion_tokens": sum(c.get("completion_tokens", 0) or 0 for c in kv_calls),
            "cache_hit_tokens": sum(c.get("cache_hit_tokens", 0) or 0 for c in kv_calls),
            "llm_ms": sum(ms),
            "window_ms": window_ms,
            "plan_elapsed_ms": summary.get("elapsed_ms", 0),
            "local_first_state": local_first.get("state", ""),
            "nodes": rec["nodes"],
            "window": [rec["ts_first"], rec["ts_last"]],
        })
    out.sort(key=lambda r: r["window"][0] or "")
    return out


def format_table(rows: list[dict]) -> str:
    head = f"{'plan_id':<14}{'节点':>4}{'本地':>5}{'远程':>5}{'本地OK':>7}{'先行':>5}{'重叠µs':>9}{'等待':>5}{'LLM次':>6}{'tokens':>9}{'窗口ms':>8}"
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r['plan_id']:<14}{r['nodes_total']:>4}{r['local_nodes']:>5}{r['remote_nodes']:>5}"
            f"{r['local_ok']:>7}{r['local_first_nodes']:>5}{r['overlap_us']:>9}{r['wait_nodes']:>5}{r['llm_calls']:>6}"
            f"{r['prompt_tokens'] + r['completion_tokens']:>9}{r['window_ms']:>8}")
    return "\n".join(lines)


def compare(base_path: str, new_path: str) -> int:
    base, new = aggregate(load_events(base_path)), aggregate(load_events(new_path))
    if not base or not new:
        print(f"对照失败: 基线 {len(base)} 个计划 / 优化后 {len(new)} 个计划 (都要 ≥1)", file=sys.stderr)
        return 2
    b, n = base[-1], new[-1]
    metrics = [
        ("LLM 调用数", b["llm_calls"], n["llm_calls"], "越低越好"),
        ("tokens(prompt+completion)", b["prompt_tokens"] + b["completion_tokens"],
         n["prompt_tokens"] + n["completion_tokens"], "越低越好"),
        ("端到端 ms (计划窗口)", b["window_ms"], n["window_ms"], "越低越好"),
        ("前端可见节点数", b["nodes_total"], n["nodes_total"], "越多越好=细分被看见"),
        ("本地先行节点数", b["local_first_nodes"], n["local_first_nodes"], "越多越好=零 token 先跑"),
        ("真重叠 µs", b["overlap_us"], n["overlap_us"], "越大越好=真并行"),
        ("本地 tokens", b["local_tokens"], n["local_tokens"], "恒 0 即本地未花模型"),
        ("运行时依赖等待节点数", b["wait_nodes"], n["wait_nodes"], "等待是『必须等』的事实, 非越多越好"),
        ("运行时依赖等待 µs", b["wait_us"], n["wait_us"], "同上 (有界等待, 超限即失败)"),
    ]
    print(f"基线 {base_path}  plan={b['plan_id']}  窗={b['window'][0]} → {b['window'][1]}")
    print(f"新版 {new_path}  plan={n['plan_id']}  窗={n['window'][0]} → {n['window'][1]}\n")
    print(f"{'指标':<28}{'基线':>12}{'优化后':>12}{'Δ':>12}  方向")
    print("-" * 78)
    for name, bv, nv, direction in metrics:
        print(f"{name:<28}{bv:>12}{nv:>12}{nv - bv:>+12}  {direction}")
    return 0


def selftest() -> int:
    """机检: 合成遥测 → 断言聚合 (含"本地先行真重叠>0"与"无先行时必须为 0"两条)。"""
    synth = [
        {"ts": "2026-01-01T00:00:00.000Z", "point": "plan_route",
         "kv": {"plan_id": "p1", "nodes": 3, "local": 2, "hybrid": 0, "remote": 1}},
        {"ts": "2026-01-01T00:00:00.000Z", "point": "plan_local_first",
         "kv": {"plan_id": "p1", "state": "started", "nodes": 1}},
        {"ts": "2026-01-01T00:00:01.000Z", "point": "llm_call",
         "kv": {"prompt_tokens": 1000, "completion_tokens": 500, "cache_hit_tokens": 900,
                "ms": 90000, "success": True}},
        {"ts": "2026-01-01T00:00:01.200Z", "point": "plan_local_first_overlap",
         "kv": {"plan_id": "p1", "nodes": 1, "local_first_us": 800, "overlap_us": 800,
                "remote_wait_us": 1200}},
        {"ts": "2026-01-01T00:00:01.300Z", "point": "plan_node",
         "kv": {"plan_id": "p1", "plan_node": "n1", "loc": "local", "exec": "text.process",
                "state": "Completed", "elapsed_ms": 0, "tokens": 0}},
        {"ts": "2026-01-01T00:00:01.400Z", "point": "plan_node",
         "kv": {"plan_id": "p1", "plan_node": "n2", "loc": "local", "exec": "python.selftest",
                "state": "Completed", "elapsed_ms": 34, "tokens": 0}},
        {"ts": "2026-01-01T00:00:01.500Z", "point": "plan",
         "kv": {"plan_id": "p1", "nodes": 3, "local_ok": 2, "local_failed": 0, "skipped": 0,
                "local_tokens": 0, "elapsed_ms": 40}},
        {"ts": "2026-01-01T00:10:00.000Z", "point": "plan_route",
         "kv": {"plan_id": "p2", "nodes": 2, "local": 1, "hybrid": 0, "remote": 1}},
        {"ts": "2026-01-01T00:10:02.000Z", "point": "plan",
         "kv": {"plan_id": "p2", "nodes": 2, "local_ok": 1, "local_failed": 0, "skipped": 0,
                "local_tokens": 0, "elapsed_ms": 30}},
    ]
    rows = aggregate(synth)
    fail: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            fail.append(msg)

    check(len(rows) == 2, f"应聚出 2 个计划, 实得 {len(rows)}")
    p1 = next((r for r in rows if r["plan_id"] == "p1"), None)
    p2 = next((r for r in rows if r["plan_id"] == "p2"), None)
    check(p1 is not None and p2 is not None, "计划 p1/p2 必须都在")
    if p1:
        check(p1["llm_calls"] == 1, f"p1 LLM 调用数应为 1, 实得 {p1['llm_calls']}")
        check(p1["prompt_tokens"] == 1000 and p1["completion_tokens"] == 500,
              f"p1 tokens 应为 1000/500, 实得 {p1['prompt_tokens']}/{p1['completion_tokens']}")
        check(p1["nodes_total"] == 3, f"p1 前端可见节点数应为 3, 实得 {p1['nodes_total']}")
        check(p1["local_first_nodes"] == 1, f"p1 本地先行节点数应为 1, 实得 {p1['local_first_nodes']}")
        check(p1["overlap_us"] == 800, f"p1 真重叠应为 800µs, 实得 {p1['overlap_us']}")
        check(p1["local_tokens"] == 0, f"p1 本地 tokens 应为 0, 实得 {p1['local_tokens']}")
        check(p1["window_ms"] == 1500, f"p1 窗口 ms 应为 1500, 实得 {p1['window_ms']}")
    if p2:
        # 负向控制: 没有本地先行 → 重叠必须为 0, 不许凭空冒出来
        check(p2["local_first_nodes"] == 0, f"p2 无先行节点, 实得 {p2['local_first_nodes']}")
        check(p2["overlap_us"] == 0, f"p2 无先行则重叠必须 0, 实得 {p2['overlap_us']}")
        check(p2["llm_calls"] == 0, f"p2 窗口内无 llm_call, 实得 {p2['llm_calls']}")

    if fail:
        print("KPI 脚本机检 失败:")
        for f in fail:
            print("  ✗", f)
        return 1
    print("KPI 脚本机检 通过 (7 项断言: 聚合/窗口/重叠/负向控制)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="计划路由 KPI 汇总 (v0.22.0 exp9 D6)")
    ap.add_argument("--telemetry", default=DEFAULT_TELEMETRY, help="遥测 jsonl (默认 data/telemetry/host.jsonl)")
    ap.add_argument("--compare", nargs=2, metavar=("基线", "优化后"), help="同题对照: 两个遥测文件")
    ap.add_argument("--json", action="store_true", help="输出 JSON (喂别的脚本)")
    ap.add_argument("--selftest", action="store_true", help="机检聚合逻辑")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.compare:
        return compare(args.compare[0], args.compare[1])

    rows = aggregate(load_events(args.telemetry))
    if not rows:
        print(f"(无计划点位: {args.telemetry})")
        return 0
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print(format_table(rows))
    last = rows[-1]
    print(f"\n最近计划 {last['plan_id']}: 本地先行 {last['local_first_nodes']} 节点 / "
          f"真重叠 {last['overlap_us']}µs / 远程等待 {last['remote_wait_us']}µs / "
          f"本地 tokens {last['local_tokens']} / LLM {last['llm_calls']} 次")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
