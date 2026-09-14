#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R425 汇总器 — 机检取值, 供 README/台账引用 (禁手工转录)。"""
import json, os, hashlib, subprocess

D = "/home/agentuser/AgentFramework/eval/rover/r425"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def calls(p):
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    return len(rows), sum(r["prompt_tokens_est"] + r["completion_tokens_est"] for r in rows)


out = {"round": "R425", "batches": {}}
for sfx, label in (("", "b1-instrument-null-no-role"), ("-b2", "b2-pre-registered")):
    g = {}
    for k in (1, 2, 4, 6, 8):
        for arm in ("A", "B"):
            p = f"{D}/calls-{arm}-k{k}{sfx}.jsonl"
            if os.path.exists(p):
                c, t = calls(p)
                g[f"{arm}-k{k}"] = {"calls": c, "tokens": t}
    p = f"{D}/calls-BP-k6{sfx}.jsonl"
    if os.path.exists(p):
        c, t = calls(p)
        g["BP-k6"] = {"calls": c, "tokens": t}
    out["batches"][label] = g
    b2 = sfx == "-b2"
    if b2:
        out["batches"][label]["curve"] = {
            str(k): {"share": k / 8,
                     "tok_ratio": round((g[f"A-k{k}"]["tokens"] - g[f"B-k{k}"]["tokens"]) / g[f"A-k{k}"]["tokens"], 6),
                     "call_ratio": round((g[f"A-k{k}"]["calls"] - g[f"B-k{k}"]["calls"]) / g[f"A-k{k}"]["calls"], 6)}
            for k in (1, 2, 4, 6, 8)}
out["corpus"] = {"grid_sha_before": open(f"{D}/grid-sha-before.txt", encoding="utf-8").read().strip().split("\n"),
                 "grid_sha_after": open(f"{D}/grid-sha-after.txt", encoding="utf-8").read().strip().split("\n")
                 if os.path.exists(f"{D}/grid-sha-after.txt") else None}
out["fixtures"] = {os.path.basename(p): {"bytes": os.path.getsize(f"{D}/grid/{p}"), "sha256": sha256(f"{D}/grid/{p}")}
                   for p in sorted(os.listdir(f"{D}/grid"))}
out["artifact_shas"] = {os.path.basename(p): sha256(os.path.join(D, p))
                        for p in sorted(os.listdir(D))
                        if p.endswith((".json", ".sh", ".py")) and os.path.isfile(os.path.join(D, p))}
out["mechanism_source"] = {"file": "src/agent/IndustrialAgentV2.cs", "line": 1464,
                           "code": "if (_modelRouter is { TurnGateEnabled: true } && ActiveRole is not null)",
                           "implication": "门生效的必要条件含 ActiveRole!=null ⇒ 无 --role 的臂静默走未门路径 (b1 即此)"}
out["plan_doc_mtime"] = subprocess.run(["stat", "-c", "%y", "/home/agentuser/AgentFramework/docs/plans/v0.46.0-r425-ratio-sensitivity-grid.md"],
                                       capture_output=True, text=True).stdout.strip()
out["first_arm_mtime"] = subprocess.run(["stat", "-c", "%y", f"{D}/budget-A-k1-b2.json"], capture_output=True, text=True).stdout.strip()
json.dump(out, open(f"{D}/summary-r425.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(out["batches"], ensure_ascii=False, indent=1)[:2000])
