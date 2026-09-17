#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 J1b: **第二判分器** (`grade_f2_r529.py`) 的正/负控 —— 与前置器所用用例脚本非同源, 必须同样有牙。

oracle = 生成器 ref+fmt (`eval/probe/tasks.py`) ⇒ 期望 30/30 rc=0;
变异体 (与 J1 同族: 非法态不报 ERR / 对象键序降序 / 空包) ⇒ 期望 rc=1 且读数 < 30 (判分器不是恒绿)。
题面取自已落盘的 `taskset-r529.json` (只读; 不重跑生成器 ⇒ 不动任何输入件)。
输出写成 `eval/rover/r529/evidence/nc-fixture-r529.json` 的 `j1b_grader` 键 (J1 段落原样保留)。
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r529")
sys.path.insert(0, R)
import build_fixture_r529 as bf  # noqa: E402  只借用 oracle_tree 构造器 (不触发其 main)

GRADER = os.path.join(R, "grade_f2_r529.py")
ts = json.load(io.open(os.path.join(R, "taskset-r529.json"), encoding="utf-8"))
f2_prompt = [t for t in ts["tasks"] if t["tid"] == "t1"][0]["prompt"]
tmp = tempfile.mkdtemp(prefix="r529-j1b-")
rows = []
for tag, mut in (("oracle", None), ("nc_vm_noerr", "vm_noerr"), ("nc_json_desc", "json_desc"), ("nc_empty", None)):
    root = os.path.join(tmp, tag)
    if tag == "nc_empty":
        os.makedirs(root, exist_ok=True)
    else:
        bf.oracle_tree(root, f2_prompt, mut)
    g = os.path.join(tmp, "grade-%s.json" % tag)
    p = subprocess.run([sys.executable, GRADER, "--dir", root, "--out", g], capture_output=True, text=True)
    j = json.load(io.open(g, encoding="utf-8"))
    rows.append({"tree": tag, "grader_rc": p.returncode, "passed": j["passed"], "total": j["total"],
                 "public": j["public"], "hidden": j["hidden"]})
    print("%-14s grader_rc=%d cases=%s/%s public=%s hidden=%s" % (tag, p.returncode, j["passed"], j["total"],
                                                                  j["public"], j["hidden"]))
shutil.rmtree(tmp, ignore_errors=True)
oracle = [x for x in rows if x["tree"] == "oracle"][0]
bad = [x for x in rows if x["tree"] != "oracle"]
ok = oracle["grader_rc"] == 0 and oracle["passed"] == oracle["total"] and all(
    x["grader_rc"] == 1 and x["passed"] < x["total"] for x in bad)
p = os.path.join(R, "evidence/nc-fixture-r529.json")
blob = json.load(io.open(p, encoding="utf-8"))
blob["j1b_grader"] = {"grader": "eval/rover/r529/grade_f2_r529.py", "rows": rows, "all_ok": bool(ok),
                      "note": "第二判分器与前置器用例脚本为两条独立实现; oracle 绿 ∧ 三变异体红 ⇒ 有牙",
                      "grader_sha256": hashlib.sha256(open(GRADER, "rb").read()).hexdigest()}
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
print("J1B_ALL_OK=%s" % ok)
sys.exit(0 if ok else 1)
