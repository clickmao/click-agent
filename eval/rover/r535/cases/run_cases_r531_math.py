#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 F3 隐藏用例脚本 (铁律 11 前置器 project 布局的 `task["cases"]` 指向件)。

契约 (由 `eval/rover/r507pre/exec_precondition.py:run_case_script` 规定):
  · 由前置器以 `python3 -I -B <本文件>` 启动, **cwd = 被测产物树的独立物化副本**;
  · stdout 逐行 `CASE <name> PASS|FAIL`; 用例条数须 == 题集 `hidden_cases`;
  · rc=0 仅当**全部**用例通过。

**双判分器 (非同源)** —— 本脚本不信任落盘期望值:
  · 判据 A = 夹具落盘值 (由 `tasks.MATH_FAMILIES[fam]["ref"]` 产出, 见 build_fixture_r531.py);
  · 判据 B = 判分时刻用 `tasks.MATH_FAMILIES[fam]["check"]` **独立重算** (与 ref 不同实现);
  · A != B ⇒ 该用例记 `FAIL ORACLE_DRIFT` (fail-closed, 宁可判红也不放过);
  · 提交物须与 A、B **同时**逐字节相等 (答案唯一性由 A==B 保证)。

验收形态 = 工作根下 `python3 -m mathkit <op>` (题面写明的唯一入口), 参数 = stdin 上的 JSON 对象。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases-r531-f3.json")
REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r531"))
sys.path.insert(0, os.path.join(REPO, "eval/probe"))


def main():
    try:
        import tasks  # noqa: PLC0415
        import op_contract_r531 as C  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        print("R531_CASES_FATAL oracle_import:%s" % type(e).__name__, flush=True)
        return 3
    with open(CASES, encoding="utf-8") as fh:
        cases = json.load(fh)
    wd = os.getcwd()
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": wd,
           "PYTHONPATH": wd, "PYTHONDONTWRITEBYTECODE": "1"}
    npass = npair = 0
    for i, c in enumerate(cases):
        op = c["op"]
        name = "%s/%s#%02d-%s" % (c["mod"], op, i, c["vis"])
        # --- 判分器 B: 独立重算 (非同源) ---
        drift = ""
        try:
            fam = C.OP_TABLE[op]["family"]
            f = tasks.MATH_FAMILIES[fam]
            params = C.to_params(op, c["args"])
            exp_b = f["fmt"](params, f["check"](params))
            if exp_b == c["expected_stdout"]:
                npair += 1
            else:
                drift = "ORACLE_DRIFT(a=%r b=%r)" % (c["expected_stdout"], exp_b)
        except Exception as e:  # noqa: BLE001
            drift = "ORACLE_ERROR:%s" % type(e).__name__
        # --- 提交物实跑 ---
        ok, why = False, drift
        try:
            p = subprocess.run([sys.executable, "-B", "-m", "mathkit", op],
                               input=json.dumps(c["args"], ensure_ascii=False),
                               capture_output=True, text=True, timeout=60, cwd=wd, env=env)
            ok = (not drift) and p.returncode == 0 and p.stdout.strip("\n") == c["expected_stdout"].strip("\n")
            if not ok and not drift:
                why = ("rc=%d:%s" % (p.returncode, (p.stderr or "").strip()[-80:])) if p.returncode \
                    else "stdout_mismatch(got=%r)" % p.stdout.strip("\n")[:60]
        except Exception as e:  # noqa: BLE001
            why = type(e).__name__
        if ok:
            npass += 1
        print("CASE %s %s %s" % (name, "PASS" if ok else "FAIL", why), flush=True)
    print("R531_ORACLE_PAIRS %d/%d" % (npair, len(cases)), flush=True)
    print("R531_CASES %d/%d" % (npass, len(cases)), flush=True)
    return 0 if (npass == len(cases) and npair == len(cases)) else 1


if __name__ == "__main__":
    sys.exit(main())
