#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q46 fixup: 台账行 ts 精确化 (落盘时写了占位式「14:0x」)。

纪律: ts 由**产生侧**用真实时钟写; 本 fixup 取该行落地提交的**提交时刻**(带秒与时区)作权威值,
改写后: ① 仅改最后一个对象的 ts 字段 (其余键与值逐字节不变) ② 全文件逐行可解析 ③ 键集不变 ④ 幂等。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KPI = os.path.join(ROOT, "eval", "capability", "kpi.jsonl")
ROUND = "EXP1-Q46"

chrome = subprocess.run(["git", "log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%dT%H:%M:%S%z"],
                        cwd=ROOT, capture_output=True, text=True)
ts = chrome.stdout.strip()
if len(ts) < 15:
    print(f"FIXUP_EXIT=3 (无法取提交时刻: {ts!r})")
    sys.exit(3)

with open(KPI, encoding="utf-8-sig", errors="replace") as fh:
    lines = [l for l in fh.read().splitlines() if l.strip()]
if not lines:
    print("FIXUP_EXIT=3"); sys.exit(3)
last = json.loads(lines[-1])
if last.get("round") != ROUND:
    print(f"FIXUP_EXIT=2 (末行非本轮: {last.get('round')})"); sys.exit(2)

old_ts = last.get("ts")
if old_ts == ts:
    print(f"FIXUP_IDEMPOTENT=1 ts={ts}")
    print("FIXUP_EXIT=0"); sys.exit(0)

keys_before = list(last.keys())
last["ts"] = ts
if list(last.keys()) != keys_before:
    print("FIXUP_EXIT=2 (键集变化)"); sys.exit(2)

lines[-1] = json.dumps(last, ensure_ascii=False)
with open(KPI, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines) + "\n")

# 读回
with open(KPI, encoding="utf-8-sig", errors="replace") as fh:
    back = [l for l in fh.read().splitlines() if l.strip()]
bad = 0
for i, l in enumerate(back):
    try:
        json.loads(l)
    except Exception as exc:  # noqa: BLE001
        print(f"KPI_PARSE_FAIL line={i + 1} err={exc}"); bad += 1
print(f"CHK lines={len(back)} parse_fail={bad} last_ts={json.loads(back[-1])['ts']} old_ts={old_ts}")
print(f"FIXUP_EXIT={2 if (bad or len(back) != len(lines)) else 0}")
sys.exit(2 if (bad or len(back) != len(lines)) else 0)
