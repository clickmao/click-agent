#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力自检循环 · 状态探针 (用户令 2026-09-14: 每 60 分钟检查「还有任务吗」)。

判据全部机械可复核 (不靠感觉):
  ① 计划看板 `docs/plans/v0.22.0-longterm-backlog.md` 中状态列含「进行中/未开始/待定/部分」的行 ⇒ 未完成计划项;
  ② 主报告 §7 最新状态块中的「下轮候选 / 待确认 / 进行中」条目 ⇒ 未完成事项;
  ③ 若 ① ② 皆空 ⇒ 输出 mode=selfcheck (运行「py 随机程序 + 随机数学难题」能力自检循环)。

输出: 单行 JSON (cron 注入用), 字段: mode / open_count / open_items / last_probe / skills_hint
退出码: 0 正常; 2 读取失败 (不静默)。
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "docs", "plans", "v0.22.0-longterm-backlog.md")
MASTER = os.path.join(ROOT, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")
KPI = os.path.join(ROOT, "data", "probe", "kpi.jsonl")
SKILLS = os.path.join(ROOT, "skills")

DONE_MARKERS = ("已交付", "已完成", "已收口", "done", "DONE")


def backlog_open():
    open_rows = []
    if not os.path.exists(BACKLOG):
        return None
    for line in open(BACKLOG, encoding="utf-8"):
        line = line.rstrip()
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| 轮次") or line.startswith("| 轮 "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        row = cells[0]
        status = cells[2] if len(cells) > 2 else ""
        if not re.match(r"^R\d+", row):
            continue
        if any(m in status for m in DONE_MARKERS):
            continue
        if re.search(r"进行中|未开始|待定|部分|计划中", status):
            open_rows.append(f"{row}: {status[:60]}")
    return open_rows


def master_opens():
    if not os.path.exists(MASTER):
        return None
    txt = open(MASTER, encoding="utf-8").read()
    head = txt.split("## 7.")[-1][:4000]
    hits = []
    for m in re.finditer(r"^\s*>?\s*[-*]?\s*\*\*(下轮候选|待确认|本轮待办|进行中)\*\*[:：]?\s*(.{0,120})", head, re.M):
        hits.append(f"{m.group(1)}: {m.group(2).strip()}")
    return hits[:8]


def last_probe():
    info = {"kpi_lines": 0, "last": None}
    if os.path.exists(KPI):
        lines = [l for l in open(KPI, encoding="utf-8") if l.strip()]
        info["kpi_lines"] = len(lines)
        if lines:
            try:
                info["last"] = json.loads(lines[-1])
            except Exception:  # noqa: BLE001
                info["last"] = {"parse_error": True}
    return info


def skills_count():
    if not os.path.isdir(SKILLS):
        return 0
    return sum(1 for d in os.listdir(SKILLS) if os.path.exists(os.path.join(SKILLS, d, "SKILL.md")))


def main() -> int:
    b = backlog_open()
    m = master_opens()
    if b is None or m is None:
        print(json.dumps({"error": "docs 缺失", "backlog": BACKLOG, "master": MASTER}, ensure_ascii=False))
        return 2
    items = b + m
    info = last_probe()
    out = {
        "mode": "tasks" if items else "selfcheck",
        "open_count": len(items),
        "open_items": items,
        "backlog_open": len(b),
        "master_open": len(m),
        "kpi_lines": info["kpi_lines"],
        "skills_count": skills_count(),
        "rule": "mode=tasks ⇒ 推进计划项一步; mode=selfcheck ⇒ 跑 py 随机程序+随机数学题能力自检并沉淀通用性 skill",
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
