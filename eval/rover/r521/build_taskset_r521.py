#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R521 题集生成器: 输入面**逐字节复用 R519/R520** (games-longtask-v1, 题面 sha 钉死),
只补 project 布局字段 (供铁律 11 前置器 `exec_precondition.py` 的 project 布局自动发现):
  · cases          = 仓内隐藏用例脚本相对路径 (输出 `CASE <name> PASS|FAIL`)
  · hidden_cases   = 58 (public 8 + hidden 50, 该任务只发一套用例)
  · kind/family    = project / games-longtask-v1

禁改题面: 题面 sha256 与 R519 逐字节相同才落盘 (不同 ⇒ rc=2 拒写)。
用法: `build_taskset_r521.py [--check]`  --check: 只校验盘上件与派生件逐字节一致。
"""
import hashlib
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r521")
SRC = os.path.join(REPO, "eval/rover/r519/taskset-r519.json")
PROMPT_SHA = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3"
OUT = os.path.join(R, "taskset-r521.json")


def derive():
    src = json.load(io.open(SRC, encoding="utf-8"))
    t = src["tasks"][0]
    prompt = t["prompt"]
    sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if sha != PROMPT_SHA:
        print("[致命] 题面漂移: 期望 %s 实得 %s ⇒ 拒写 (禁改题)" % (PROMPT_SHA, sha))
        raise SystemExit(2)
    cases = t["cases"]
    n_pub = sum(1 for c in cases if c["vis"] == "public")
    n_hid = sum(1 for c in cases if c["vis"] == "hidden")
    doc = {"round": "R521", "family": "games-longtask-v1",
           "source": "eval/rover/r519/taskset-r519.json (题面逐字节复用)",
           "tasks": [{"tid": "g1", "kind": "project", "family": "games-longtask-v1",
                      "prompt": prompt, "prompt_sha256": sha,
                      "cases": "cases/run_cases_r521.py", "hidden_cases": len(cases),
                      "meta": {"n_games": 4, "n_cases": len(cases), "public": n_pub, "hidden": n_hid},
                      "fixture_src": {"taskset": "eval/rover/r519/taskset-r519.json",
                                      "plan": "eval/rover/r519/plan-games-longtask.txt",
                                      "scope": "eval/rover/r519/scope-games-longtask.txt"}}]}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n", sha


def main():
    check = "--check" in sys.argv[1:]
    text, sha = derive()
    if check:
        if not os.path.isfile(OUT):
            print("[致命] 缺 %s ⇒ fail-closed rc=3" % OUT)
            return 3
        on = io.open(OUT, encoding="utf-8").read()
        if on != text:
            print("[致命] 盘上题集与派生件不一致 ⇒ rc=2")
            return 2
        print("TASKSET_OK tid=g1 cases=58 prompt_sha256=%s (== R519 逐字节)" % sha)
        return 0
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("WROTE %s prompt_sha256=%s" % (os.path.relpath(OUT, REPO), sha))
    return 0


if __name__ == "__main__":
    sys.exit(main())
