#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R513 题集生成器 = R512 的 p4 题面 **v2 修订** (只改题面缺省语义, 不动隐藏用例, 不动参考解)。

起因 (R512 机检实证): p4 题面第 2 条只写「全局选项 `--now <epoch 秒>` 注入当前时间」, **未写缺省语义**;
隐藏用例 12 条里有 8 条(含第 1 条)不带 `--now` 调用 ⇒ 判据依赖一个题面没写明的约定。
R512 三个臂 (agentA×2 / agentB×2 / codex×2) 全部把它实现成**必填**, 于是两侧同分 4/12 —— 判据丧失区分力。
证据: R512 跑器日志 + `report.json` (p4 failed 集合两侧逐字相同) + 手工复现:
  `cd <C-r1>/p4/work && python3 -B -m tasksvc.cli --db /tmp/t1.json add 买菜` → rc=2 {"error":"bad_request"}
  加 `--now 1000` → rc=0 正常返回。
修法 (最小、可机检): 把「缺省 = 系统时钟」写进题面 v2; 用例与参考解**逐字节不变** (参考解本就实现缺省)。
  检查: R513 用例 sha == R512 用例 sha; R513 ref 树与 R512 ref 树逐字节同。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_TASKSET = os.path.join(HERE, "..", "r512", "taskset-r512.json")
SRC_CASES = os.path.join(HERE, "..", "r512", "cases", "p4_cases.py")
SRC_REF = os.path.join(HERE, "..", "r512", "ref", "p4")
OUT = os.path.join(HERE, "taskset-r513.json")

OLD = "2) 时钟：全局选项 `--now <epoch 秒>` 注入当前时间（浮点或整数）。所有时间判定只准用该时钟，禁止 sleep。"
NEW = ("2) 时钟：全局选项 `--now <epoch 秒>` 注入当前时间（浮点或整数）。所有时间判定只准用该时钟，禁止 sleep。"
       "**未提供 `--now` 时必须回落到系统时钟（time.time()），不得报错、不得要求该选项必填。**")


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build():
    src = json.load(open(SRC_TASKSET, encoding="utf-8-sig"))
    t = [x for x in src["tasks"] if x["tid"] == "p4"][0]
    v1_prompt = t["prompt"]
    if OLD not in v1_prompt:
        print("[致命] v1 题面里找不到待修订句 ⇒ fail-closed")
        return 3
    v2_prompt = v1_prompt.replace(OLD, NEW, 1)
    tasks = [{"tid": "p4", "family": t.get("family") or "task-queue-cli",
              "entry": "tasksvc/cli.py", "cases": "cases/p4_cases.py", "ref": "ref/p4",
              "hidden_cases": 12, "kind": t.get("kind") or "project", "prompt": v2_prompt,
              "prompt_sha256": hashlib.sha256(v2_prompt.encode("utf-8")).hexdigest()}]
    doc = {
        "taskset": "r513", "fixture_version": 2,
        "derived_from": {"round": "r512", "taskset_sha256": sha(SRC_TASKSET),
                         "prompt_sha256_v1": t.get("prompt_sha256") or hashlib.sha256(v1_prompt.encode()).hexdigest()},
        "amendment": {
            "field": "tasks[0].prompt",
            "clause_added": "未提供 `--now` 时必须回落到系统时钟（time.time()），不得报错、不得要求该选项必填。",
            "removed_text": OLD, "added_text": NEW,
            "why": "R512 实证: 题面未写 --now 缺省 ⇒ 两侧实现都判为必填 ⇒ 12 条用例中 8 条两侧同败, 判据无区分力",
            "unchanged": {"cases_sha256": sha(SRC_CASES), "ref_tree": "逐字节同 (diff -r 为空)"},
        },
        "tasks": tasks,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"out": OUT, "prompt_sha256_v2": tasks[0]["prompt_sha256"],
                      "prompt_len_v2": len(v2_prompt), "prompt_len_v1": len(v1_prompt),
                      "cases_sha256": sha(SRC_CASES)}, ensure_ascii=False))
    return 0


def check():
    if not os.path.isfile(OUT):
        print("[致命] 缺 %s" % OUT)
        return 3
    doc = json.load(open(OUT, encoding="utf-8-sig"))
    ok = True
    if sha(SRC_CASES) != doc["amendment"]["unchanged"]["cases_sha256"]:
        print("[致命] 用例文件被改动 ⇒ 与 R512 不再逐字节同"); ok = False
    if not shutil.which("diff"):
        print("[告警] 无 diff 可执行")
    else:
        import subprocess
        p = subprocess.run(["diff", "-r", SRC_REF, os.path.join(HERE, "ref", "p4")], capture_output=True, text=True)
        if p.returncode != 0:
            print("[致命] 参考解树与 R512 不同 ⇒ 判据换面"); print(p.stdout[:400]); ok = False
    p2 = doc["tasks"][0]["prompt"]
    if NEW not in p2 or doc["tasks"][0]["prompt_sha256"] != hashlib.sha256(p2.encode()).hexdigest():
        print("[致命] v2 题面缺新增句或 sha 不自洽"); ok = False
    if p2 == json.load(open(SRC_TASKSET, encoding="utf-8-sig"))["tasks"][0]["prompt"]:
        print("[致命] v2 题面与 v1 相同 ⇒ 修订没生效"); ok = False
    print(json.dumps({"check": "OK" if ok else "FAIL", "prompt_sha256_v2": doc["tasks"][0]["prompt_sha256"],
                      "cases_sha256": sha(SRC_CASES), "tasks": [t["tid"] for t in doc["tasks"]]}, ensure_ascii=False))
    return 0 if ok else 3


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    raise SystemExit(check() if a.check else build())
