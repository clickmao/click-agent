#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R552 文档改动校验(承「文档严谨性铁律」): ① R552 段内引用的仓内路径**存在性** ② 标题/内容对齐
(improvements.md 顶部=R552 且 R551 紧随) ③ master plan 轮节位置与结尾自洽。只读, 不改文件。"""
import io
import os
import re

REPO = "/home/agentuser/AgentFramework"
pat = re.compile(r"`([^`\s]+)`")
prefix = re.compile(r"^(?:docs/|eval/|src/|scripts/|data/|tools/|\./)")
bad, tot = [], 0
for d in ("docs/reports/r552-dose-surface.md", "docs/improvements.md", "docs/reports/iteration-master-plan.md"):
    txt = io.open(os.path.join(REPO, d), encoding="utf-8").read()
    if d != "docs/reports/r552-dose-surface.md":
        i = txt.find("## R552")
        txt = txt[i:i + 9000] if i >= 0 else ""
    for m in sorted(set(pat.findall(txt))):
        if not prefix.match(m):
            continue
        tot += 1
        p = m.split(":")[0].split("(")[0].rstrip("/")
        if not os.path.exists(os.path.join(REPO, p)):
            bad.append((d, m))
print("① 引用路径检查: 候选 %d 条, 不存在 %d 条" % (tot, len(bad)))
for b in bad[:20]:
    print("   MISS", b)

im = io.open(os.path.join(REPO, "docs/improvements.md"), encoding="utf-8").read()
i552, i551 = im.find("## R552"), im.find("## R551")
print("② improvements: R552@%d < R551@%d ⇒ 新节在顶 = %s | 表格存在 = %s" % (
    i552, i551, bool(0 < i552 < i551), "| 臂 (轴值) |" in im))

mp = io.open(os.path.join(REPO, "docs/reports/iteration-master-plan.md"), encoding="utf-8").read()
print("③ master plan: R552 轮节存在 = %s | 文件末尾为本节候选行 = %s | R552 出现在 R551 之后 = %s" % (
    "## R552 (2026-09-18)" in mp, mp.rstrip().endswith("codex token 接 adapter。"),
    mp.find("## R552 (2026-09-18)") > mp.find("## R551 (2026-09-18)")))
