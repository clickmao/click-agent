#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R507pre 可验收前置器具的 L2 自检（正控 + 负控 + 真读数），产出冻结证据件。

做的事（每一步都真跑，禁自报）:
  1. 跑 `nc_precond_r507.py`（9 例：正控/确定性/错值/语法错/运行即崩/死循环/非程序题/缺输入/产物缺失）
  2. 用**真读数**（R502/R503/R504 两侧 probe 摘要 + 题集）复算前置结论 ⇒ 三行结论写进证据件
  3. 断言「两侧产出物可实际执行且正确」在 R502 为真、R503/R504 为假（与器具判据一致）
  4. 写出 `eval/rover/r507pre/evidence/precondition-selftest.json` 并打印 PRECOND_SELFTEST=OK

用法: python3 eval/rover/r507pre/selfcheck_r507.py   （rc=0 = 自检通过）
"""
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
D = os.path.join(REPO, "eval/rover/r507pre")
PY = sys.executable
OUT = os.path.join(D, "evidence/precondition-selftest.json")

REAL = [
    ("R502", "eval/rover/r502/taskset-r502.json", "data/probe/probe-cmd:fdde7b645013-seed0-codex-r502.json",
     "data/probe/probe-agent-seed0-agent-r502.json", True),
    ("R503", "eval/rover/r503/taskset-r503.json", "data/probe/probe-cmd:04ea38a941b0-seed0-codex-r503.json",
     "data/probe/probe-agent-seed0-agent-r503.json", False),
    ("R504", "eval/rover/r504/taskset-r504.json", "data/probe/probe-cmd:d05904a7b1ef-seed0-codex-r504.json",
     "data/probe/probe-agent-seed0-agent-r504.json", False),
]


def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    return {"cmd": " ".join(cmd), "rc": p.returncode, "stdout_tail": p.stdout.strip().splitlines()[-6:],
            "stdout_full_len": len(p.stdout)}


def main():
    ev = {"round": "R507pre", "rule": "对比数据可验收前置: 两侧产出物须可实际执行且正确 (用户 2026-09-17 令)"}
    r1 = sh([PY, "eval/rover/r507pre/nc_precond_r507.py"])
    ev["nc_suite"] = r1
    ok_nc = r1["rc"] == 0 and any("NC_TOTAL=OK" in l for l in r1["stdout_tail"])

    rows, rows_ok = [], True
    for tag, ts, cx, ag, expect in REAL:
        outp = "eval/rover/r507pre/precondition-%s.json" % tag.lower()
        r = sh([PY, "eval/rover/r507pre/exec_precondition.py", "--taskset", ts, "--codex", cx,
                "--agent", ag, "--label", tag, "--out", outp])
        d = json.load(io.open(os.path.join(REPO, outp), encoding="utf-8"))
        got = bool(d["executable_and_correct"])
        rows.append({"tag": tag, "rc": r["rc"], "executable_and_correct": got, "expected": expect,
                     "blocked": d["blocked"], "out": outp,
                     "sides": {s: {"program": v["program_tasks"], "exec_ok": v["exec_ok"], "correct": v["correct_n"]}
                               for s, v in d["sides"].items()}})
        rows_ok &= (got is expect) and (r["rc"] == (0 if expect else 1))
    ev["real_readings"] = rows
    ev["verdict"] = "OK" if (ok_nc and rows_ok) else "FAIL"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(ev, ensure_ascii=False, indent=1) + "\n")
    for r in rows:
        print("%-5s EXECUTABLE_AND_CORRECT=%-5s (expect %-5s) blocked=%s" % (r["tag"], r["executable_and_correct"], r["expected"], r["blocked"]))
    print("NC_TOTAL=%s" % ("OK" if ok_nc else "FAIL"))
    print("PRECOND_SELFTEST=%s" % ("OK" if ev["verdict"] == "OK" else "FAIL"))
    print("EVIDENCE=" + OUT)
    return 0 if ev["verdict"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
