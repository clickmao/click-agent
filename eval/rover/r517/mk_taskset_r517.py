#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R517: 建 taskset-r517.json —— 用 R513 已修 v2 题面 (384fa7212378), 弃 R512/R511 v1 (678624f5d420, 已由 R512/R513 判为夹具缺陷)。"""
import json, os, sys, shutil, hashlib, traceback

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r517")
SRC = os.path.join(REPO, "eval/rover/r513")   # v2 源
try:
    t_v1 = {t["tid"]: t for t in json.load(open(f"{REPO}/eval/rover/r512/taskset-r512.json", encoding="utf-8"))["tasks"]}
    t_v2 = {t["tid"]: t for t in json.load(open(f"{SRC}/taskset-r513.json", encoding="utf-8"))["tasks"]}
    a, b = t_v1["p4"]["prompt"], t_v2["p4"]["prompt"]
    sa, sb = hashlib.sha256(a.encode()).hexdigest()[:12], hashlib.sha256(b.encode()).hexdigest()[:12]
    print(f"PROMPT_SHA12 v1={sa}(R512, 缺陷) v2={sb}(R513, 已修) 用v2={sb != sa}")
    assert sb != sa, "v2 与 v1 题面相同 ⇒ 夹具未修, 停手"
    os.makedirs(f"{R}/cases", exist_ok=True)
    shutil.copy(f"{SRC}/cases/p4_cases.py", f"{R}/cases/p4_cases.py")
    shutil.rmtree(f"{R}/ref", ignore_errors=True)
    shutil.copytree(f"{SRC}/ref/p4", f"{R}/ref/p4")
    task = {"tid": "p4", "kind": "project", "family": t_v2["p4"].get("family") or t_v1["p4"]["family"],
            "entry": t_v2["p4"].get("entry") or t_v1["p4"]["entry"],
            "cases": "cases/p4_cases.py", "ref": "ref/p4",
            "hidden_cases": t_v2["p4"].get("hidden_cases") or t_v1["p4"]["hidden_cases"],
            "prompt": b, "prompt_sha256": hashlib.sha256(b.encode()).hexdigest()}
    json.dump({"round": "R517", "fixture": "p4 v2 (R513)", "tasks": [task]},
              open(f"{R}/taskset-r517.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("WROTE taskset-r517.json bytes", os.path.getsize(f"{R}/taskset-r517.json"),
          "cases", sorted(os.listdir(f"{R}/cases")), "ref", sorted(os.listdir(f"{R}/ref/p4"))[:3])
except Exception:
    traceback.print_exc()
    sys.exit(3)
