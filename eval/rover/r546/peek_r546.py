#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R546 中间检查: 台账/回复标记的机制面是否如声明。"""
import io
import json
import os

R = "/home/agentuser/AgentFramework/eval/rover/r546/run-w1"
for a in ["E0a", "E0b", "E0c", "E0d", "E0e", "E1a", "E1b", "E1c", "E1d", "E1e", "A1on", "A1onb", "A1onc"]:
    tp = os.path.join(R, a, "g1", "transcript.json")
    rp = os.path.join(R, a, "g1", "reply.txt")
    row = {"arm": a, "marker": 0, "t": None}
    if os.path.exists(rp):
        row["marker"] = io.open(rp, encoding="utf-8", errors="replace").read().count("R1_EARLY_STOP")
    if os.path.exists(tp):
        d = json.load(io.open(tp, encoding="utf-8"))
        row["t"] = {k: d.get(k) for k in ("rc", "stage", "calls", "early_stop_pfail", "early_stop_skipped",
                                          "public_probe_failed", "public_probe_ran", "exec_repairs")}
    print(json.dumps(row, ensure_ascii=False))
