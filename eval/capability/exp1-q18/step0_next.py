#!/usr/bin/env python3
"""第 0 步·判据与下轮候选: 从权威文档取(有界)。"""
import pathlib
import re

ROOT = pathlib.Path("/home/agentuser/AgentFramework")


def hits(path, pats, limit=14, width=170):
    txt = pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    n = 0
    print(f"--- {pathlib.Path(path).name}")
    for i, ln in enumerate(txt, 1):
        if any(re.search(p, ln) for p in pats):
            print(f"  {i}: {ln.strip()[:width]}")
            n += 1
            if n >= limit:
                break


hits(ROOT / "docs/plans/v0.81.0-r462-recall-reality-gate.md",
     [r"下轮", r"R46[3-9]", r"诚实边界", r"剩余", r"debt"])
print()
hits(ROOT / "docs/reports/iteration-master-plan.md",
     [r"当前主线|主线一句话|下一轮|下轮候选|判据:"], limit=12)
print()
hits(ROOT / "docs/plans/v0.22.0-longterm-backlog.md",
     [r"进行中|未开始|计划项"], limit=14, width=120)
