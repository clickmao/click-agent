#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q46 台账行追加 (幂等: 同 round 已存在则跳过; 键集取自既有末行)。"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KPI = os.path.join(ROOT, "eval", "capability", "kpi.jsonl")
ROUND = "EXP1-Q46"

row = {
    "round": ROUND,
    "ts": "2026-09-17T14:0x+0800",
    "kind": ("记录面假开放项闭合 (route.first 指向的「另一本台账 R404–R416 轮节」项在盘面已为假: "
             "EXP1-Q45 已回填 ∧ 机检 rc=0) + 时效字段登记 (最近一轮/HEAD 字段滞后主线 9 轮, 归主线轮收口)。"
             "命名空间 eval/capability/exp1-q46/ = 本作业器具目录, 与主线轮号无关。本 tick 不改产品源码/不跑真机臂/不占轮号; "
             "窗口 = 对侧(30m 作业) R518 提交(13:29)后无 dotnet 活体。"),
    "artifact": ("eval/capability/exp1-q46/{prereg_q46.json,edit_block_q46.py,marker_pair_q46.py,capture_q46.sh,"
                 "verify_q46.py,status_pre.json,status_post.json,status_nc_prestate.json,nc_prestate_doc.md,"
                 "nc_anchor_marks.txt,marker_pair.txt,edit_dryrun.txt,edit_apply.txt,edit_apply_v2.txt,edit_idem.txt,"
                 "scan_now.txt,selftest_post.txt,verdict_q46.txt}; "
                 "docs/reports/dynamic-telemetry-eval-rollback-strategy.md §7 最新块 (1 行替换)"),
    "change": ("① edit_block_q46.py: 锚点**由产物自身派生**（前态行独有串）∧ 唯一性 fail-closed(rc=2) ∧ 幂等(二次跑 IDEMPOTENT_SKIP) "
               "∧ 行级不变量(其余行逐字节保留, 行数 307 不变) ∧ 读回校验; ② marker_pair_q46.py: 用探针自身判定函数跑三臂 "
               "(前态行 hits=1 / 后态行 hits=0 / 真开放项行 hits=2 ⇒ 防「凡改即绿」); ③ verify_q46.py: 14 条预注册判据机检; "
               "④ 前态锚臂钉**不可变提交** 32125b7 的 blob (断言是 HEAD 祖先 ∧ 与现盘不同) ⇒ 复现 master_open=1。"),
    "readings": ("route.primary master-block→**backlog**; route.first→`exp1`; open_count 9→**8**; master_open 1→**0**; "
                 "backlog_open 8→8 (8 条逐字不变); block_fields 29→29; close_fenced 3→3 / quoted_fenced 1→1 (新行零围栏命中); "
                 "探针自检 **34/34** (rc=0); 覆盖机检 scan_round_sections.py **rc=0, C1 MISSING n=0, ZONE 21**; "
                 "预注册判据 **14/14 PASS** (VERIFY_EXIT=0); 成对负控 3 臂 (1/0/2); 形式门禁见 honest_boundaries。"),
    "honest_boundaries": (
        "① **自捕器具缺陷 (1 条)**: 首跑 edit_block_q46.py 用「另一本台账」当锚点键, 而该串在新文本里也出现 ⇒ 读回 "
        "`readback_anchor_gone` 恒假 ⇒ rc=2 READBACK_MISMATCH **而改写其实已落盘**（rc 与行为分离）。修法 = 锚点键换成前态行独有串; "
        "首跑读数 edit_apply.txt **原样保留**（不覆盖），修后复跑 edit_apply_v2.txt = IDEMPOTENT_SKIP rc=0。"
        "② 时限口径: 块内「最近一轮(R509)/HEAD 0b88277」字段滞后现盘 HEAD 29f75c3(R518) **9 轮** —— 本 tick **只登记不代写**: "
        "该字段刷新归主线轮收口, 代写会与对侧写者撞车（共用工作树, unattended-job-reliability §11）。"
        "③ 覆盖: 本轮改的是**记录面**（陈述与机检读数对齐），不改产品源码、不跑真机臂 —— 不构成能力面读数。"
        "④ 归属: 回填动作 = EXP1-Q45（本循环上一 tick, `1ef590a`）; 主线侧更正 = R518; 本轮只做闭合与登记。"),
    "next": ("(①) 走 backlog 首项 exp1（本地索引/代码引用图, 进行中）: 其自陈的下一问 = 按 Q2 被证伪后的收窄靶点推进 "
             "（探索题, 零产品代码, 可零冲突推进）; (②) 记录面时效字段的**自动刷新**若要机制化, 须先量「字段过时率 × 每 tick 成本」"
             "再决定是否立机制（禁预防性机制轮）; (③) 对侧 R519 起臂窗口内不跑 dotnet。"),
    "owner_round": ROUND,
}

lines = []
if os.path.exists(KPI):
    with open(KPI, encoding="utf-8-sig", errors="replace") as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
if any(json.loads(l).get("round") == ROUND for l in lines):
    print(f"KPI_SKIP=1 (round {ROUND} 已存在, 幂等)")
else:
    prev_keys = list(json.loads(lines[-1]).keys()) if lines else list(row.keys())
    if list(row.keys()) != prev_keys:
        print(f"KPI_EXIT=2 KEY_SET_MISMATCH prev={prev_keys} new={list(row.keys())}")
        raise SystemExit(2)
    with open(KPI, "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"KPI_APPENDED=1 lines_before={len(lines)}")

with open(KPI, encoding="utf-8-sig", errors="replace") as fh:
    back = [l for l in fh.read().splitlines() if l.strip()]
print(f"KPI_LINES_NOW={len(back)} last_round={json.loads(back[-1])['round']}")
for i, l in enumerate(back):
    try:
        json.loads(l)
    except Exception as exc:  # noqa: BLE001
        print(f"KPI_PARSE_FAIL line={i + 1} err={exc}")
        raise SystemExit(2)
print("KPI_EXIT=0")
