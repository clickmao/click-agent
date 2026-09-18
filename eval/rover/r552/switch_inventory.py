#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R552 器具证据 ①: 开关清单机检 —— 判定候选①『交付闸轴（probe_failed>0 ⇒ 拒交付/降级；只翻既有开关）』
字面上是否可满足: 全仓 env 开关里是否存在任何「交付/拒绝/降级」语义的开关注册。"""
import glob
import io
import os
import re

REPO = "/home/agentuser/AgentFramework"
PAT = re.compile(r"AGENTFRAMEWORK_[A-Z0-9_]+")
SEM = re.compile(r"DELIVER|REFUSE|DEGRADE|REJECT|GATE_DELIVER|STRICT", re.I)

names = set()
for root, _, files in os.walk(os.path.join(REPO, "src")):
    if os.sep + "bin" in root or os.sep + "obj" in root:
        continue
    for f in files:
        if not f.endswith(".cs"):
            continue
        try:
            txt = io.open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        names.update(PAT.findall(txt))

r1 = sorted(n for n in names if n.startswith("AGENTFRAMEWORK_R1_"))
sem = sorted(n for n in names if SEM.search(n.replace("AGENTFRAMEWORK_", "")))
out = ["# R552 器具证据: 开关清单机检（候选① 可行性判定）",
       "# 命令等价: grep -rho 'AGENTFRAMEWORK_[A-Z0-9_]*' src/ --include=*.cs | sort -u",
       "# 判定: 交付/拒绝/降级 语义开关命中数 = %d ⇒ 候选①『只翻既有开关』字面不可满足" % len(sem),
       "# 全仓 env 开关总数 = %d" % len(names),
       "# R1 面既有开关（本轮剂量面用的是第 4 项）:"]
out += ["  " + n for n in r1]
out += ["# 语义命中项: %s" % (sem if sem else "(无)"),
        "# 结论: 交付闸必须落在**新分支**（改 rc/stage 分类 + 回执面）⇒ 按用户令『要动代码须先说明它改哪一格读数』留 R553 预注册,",
        "#       不夹带进 R552（R552 只翻既有开关: MAX_PROBE_REPAIR 0/1/2）。"]
io.open(os.path.join(REPO, "eval/rover/r552/gate-switch-inventory.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
