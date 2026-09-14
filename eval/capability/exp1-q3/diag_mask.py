#!/usr/bin/env python3
"""定位 arm2 掩码器的状态失步点（哪一行起它开始吞真代码）。"""
import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("probe", REPO / "eval/capability/exp1-q3/probe_code_graph.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

rel = sys.argv[1] if len(sys.argv) > 1 else "src/agent/IndustrialAgentV2.cs"
raw = (REPO / rel).read_text(encoding="utf-8-sig", errors="replace")
masked = probe.mask_noncode(raw)

raw_lines = raw.split("\n")
m_lines = masked.split("\n")
assert len(raw_lines) == len(m_lines), (len(raw_lines), len(m_lines))

tre = probe.token_re("CapabilityScanner")
lost = []
for i, (a, b) in enumerate(zip(raw_lines, m_lines), 1):
    if tre.search(a) and not tre.search(b):
        lost.append(i)
print("lost occurrence lines:", lost)

# 状态失步点：找第一个「原行含非空白代码字符、掩码行全空白」的行
first = None
for i, (a, b) in enumerate(zip(raw_lines, m_lines), 1):
    if a.strip() and not b.strip() and not a.strip().startswith("//") and not a.strip().startswith("*"):
        first = i
        break
print("first over-masked non-comment line:", first)
for i in range(max(1, (first or 1) - 4), min(len(raw_lines), (first or 1) + 3) + 1):
    print(f"{i:5d} | raw={raw_lines[i-1].strip()[:90]!r}")
    print(f"      | msk={m_lines[i-1].strip()[:90]!r}")
