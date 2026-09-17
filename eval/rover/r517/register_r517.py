#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R517: 登记行 (克隆上一行键形状) —— 只改 id/capability/evidence_*/owner_round/covers。"""
import json, os, sys, subprocess, hashlib

REPO = "/home/agentuser/AgentFramework"
P = os.path.join(REPO, "docs/verification-registry.json")
reg = json.load(open(P, encoding="utf-8"))
rows = reg["rows"] if isinstance(reg, dict) and "rows" in reg else reg
last = rows[-1]
print("上一行键:", sorted(last.keys()), "总行数", len(rows), "updated_round", (reg.get("updated_round") if isinstance(reg, dict) else None))
if any(r.get("id") == "external.contrast-orchestrator-vs-codex-r517" for r in rows):
    print("已存在, 跳过"); sys.exit(0)
row = dict(last)
row["id"] = "external.contrast-orchestrator-vs-codex-r517"
row["capability"] = "主线回归: 同窗三臂 (单轮6步 / 编排器3节点×6步+--scope / codex 外部真值) 于 p4 v2 题面; R516 假绿防护真机生效 (n3 no_artifact)"
row["evidence_cmd"] = "bash eval/rover/r517/run_r517.sh"
row["evidence_path"] = "eval/rover/r517/run-0917-121736/summary.txt"
row["owner_round"] = "R517"
if "covers" in row:
    row["covers"] = ["docs/reports/r517-mainline-contrast-orchestrator-vs-codex.md",
                     "eval/rover/r517/run_r517.sh", "eval/rover/r517/plan-p4-v3.txt",
                     "eval/rover/r517/scope-p4.txt", "eval/rover/r517/prereg-r517.json"]
for k in ("level", "status"):
    if k in row and k in ("status",):
        row[k] = last.get(k)
rows.append(row)
if isinstance(reg, dict) and "updated_round" in reg:
    reg["updated_round"] = "R517"
json.dump(reg, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("WROTE 行数", len(rows), "新行 id", row["id"])
print(json.dumps({k: row[k] for k in ("id", "level", "owner_round") if k in row}, ensure_ascii=False))
