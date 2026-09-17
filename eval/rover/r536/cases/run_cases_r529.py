#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 F2 隐藏用例脚本 (铁律 11 前置器 project 布局的 `task["cases"]` 指向件)。

契约 (由 `eval/rover/r507pre/exec_precondition.py:run_case_script` 规定):
  · 由前置器以 `python3 -I -B <本文件>` 启动, **cwd = 被测产物树的独立物化副本**;
  · stdout 逐行 `CASE <name> PASS|FAIL`; 用例条数须 == 题集 `hidden_cases`;
  · rc=0 仅当**全部**用例通过。

语料取自仓内不可变副本 `cases-r529-f2.json` (由 `build_fixture_r529.py` 从
`eval/probe/tasks.py`( seed 20260917 ) 双路径校验生成器落盘, 不含活目录读数)。
验收形态 = 工作根下 `python3 -m toolkit <vm|jsonmini>` (题面写明的唯一入口)。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases-r529-f2.json")


def main():
    with open(CASES, encoding="utf-8") as fh:
        cases = json.load(fh)
    wd = os.getcwd()
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": wd,
           "PYTHONPATH": wd, "PYTHONDONTWRITEBYTECODE": "1"}
    npass = 0
    for i, c in enumerate(cases):
        name = "%s#%02d-%s" % (c["mod"], i, c["vis"])
        ok, why = False, ""
        try:
            p = subprocess.run([sys.executable, "-B", "-m", "toolkit", c["mod"]], input=c["stdin"],
                               capture_output=True, text=True, timeout=60, cwd=wd, env=env)
            ok = (p.returncode == 0) and (p.stdout.strip("\n") == c["expected_stdout"].strip("\n"))
            if not ok:
                why = ("rc=%d:%s" % (p.returncode, (p.stderr or "").strip()[-80:])) if p.returncode \
                    else "stdout_mismatch"
        except Exception as e:  # noqa: BLE001
            why = type(e).__name__
        if ok:
            npass += 1
        print("CASE %s %s %s" % (name, "PASS" if ok else "FAIL", why), flush=True)
    print("R529_CASES %d/%d" % (npass, len(cases)), flush=True)
    return 0 if npass == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
