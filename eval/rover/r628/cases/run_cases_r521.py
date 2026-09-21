#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R521 隐藏用例脚本 (铁律 11 前置器 project 布局的 `task["cases"]` 指向件)。

契约 (由 `eval/rover/r507pre/exec_precondition.py:run_case_script` 规定):
  · 由前置器以 `python3 -I -B <本文件>` 启动, **cwd = 被测产物树的独立物化副本**;
  · stdout 逐行 `CASE <name> PASS|FAIL`; 用例条数须 == 题集 `hidden_cases` (58);
  · rc=0 仅当**全部**用例通过 (否则前置器判 correct=False)。
语义与 `eval/rover/r519/grade_r519.py` 同源: 对每款游戏跑 `python3 -m games <game_id>`,
stdin 喂完整输入, 逐字节比对 stdout (尾换行归一)。语料取自仓内不可变副本 `cases-r521.json`
(== R519 题集 cases 字段, sha256 270128eb…), 不使用活目录/不读被测树以外的可变量。
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases-r521.json")
# 逐用例超时: 默认 60（与 R519 同源, 不设该 env 时行为不变）。R591 派生: 打超时的产物树
# (agent CLI rc=124 留下的部分树) 会在**每个**用例上挂满超时 ⇒ 60s×58 = 58min/树, 成本无界;
# 本轮以 AGENTFRAMEWORK_GRADE_TIMEOUT=10 起臂, 并把每例耗时写进 why 字段作口径控制读数
# (kpi 解析取 token[1] 为用例名 + 查 "PASS" 子串 ⇒ 追加耗时 token 不影响判读)。
TMO = float(os.environ.get("AGENTFRAMEWORK_GRADE_TIMEOUT", "60"))


def main():
    with open(CASES, encoding="utf-8") as fh:
        cases = json.load(fh)
    wd = os.getcwd()
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": wd,
           "PYTHONPATH": wd, "PYTHONDONTWRITEBYTECODE": "1"}
    npass = 0
    for i, c in enumerate(cases):
        name = "%s#%02d-%s" % (c["game"], i, c["vis"])
        ok, why = False, ""
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, "-B", "-m", "games", c["game"]], input=c["stdin"],
                               capture_output=True, text=True, timeout=TMO, cwd=wd, env=env)
            ok = (p.returncode == 0) and (p.stdout.strip("\n") == c["expected_stdout"].strip("\n"))
            if not ok:
                why = "rc=%d" % p.returncode if p.returncode else "stdout_mismatch"
        except Exception as e:  # noqa: BLE001
            why = type(e).__name__
        dt = time.time() - t0
        if ok:
            npass += 1
        print("CASE %s %s %s@%.2fs" % (name, "PASS" if ok else "FAIL", why or "ok", dt), flush=True)
    print("R521_CASES %d/%d" % (npass, len(cases)), flush=True)
    return 0 if npass == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
