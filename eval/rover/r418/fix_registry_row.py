#!/usr/bin/env python3
"""修 R418 登记行: evidence_path 必须是**单个真实存在的路径**(R2)。用 roundtrip 校验后写回。"""
import json
import pathlib

P = pathlib.Path("/home/agentuser/AgentFramework/docs/verification-registry.json")
raw = P.read_text(encoding="utf-8")
d = json.loads(raw)
assert raw == json.dumps(d, indent=2, ensure_ascii=False) + "\n", "roundtrip 不一致，先修基线"

row = d["rows"][-1]
assert row["id"] == "r418.probe-process-kpi", row["id"]
DATA = [
    "eval/rover/r418/README-evidence.md",
    "data/probe/process-metrics-r418.json",
    "data/probe/probe-r418-agent.json",
    "data/probe/probe-r418-json-mut.json",
    "data/probe/replies/agents20260916-p001.txt",
    "data/probe/replies/agents20260916-p002.txt",
    "data/probe/replies/agents20260916-p003.txt",
]
root = P.parent.parent
for p in DATA:
    assert (root / p).exists(), "缺文件: %s" % p
row["evidence_path"] = "eval/rover/r418/README-evidence.md"
covers = [c for c in row["covers"]]
for p in DATA:
    if p not in covers:
        covers.append(p)
row["covers"] = covers
P.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("evidence_path =", row["evidence_path"])
print("covers(%d) = %s" % (len(covers), covers))
print("rows =", len(d["rows"]))
