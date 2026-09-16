#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`exec_precondition.py` 的负控/正控（L2 证据：注入缺陷必失败，且必点名）。

七例：NC1 正控(两侧好码⇒绿) · NC2 错值(⇒红+点名, 用例级少) · NC3 语法错(⇒可执行面红) ·
NC4 死循环(⇒超时红) · NC5 非程序题(⇒exec=not-applicable, 只核正确性) ·
NC6 缺输入(⇒rc=3 fail-closed) · NC7 产物缺失(⇒no_code 红, 不冒充通过) + 确定性(两次跑逐字节同)。

用法: python3 eval/rover/r507pre/nc_precond_r507.py    （退出码 0 = 全例符合预期）
"""
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
TOOL = os.path.join(REPO, "eval/rover/r507pre/exec_precondition.py")
D = "/tmp/r507pre_nc"
PY = sys.executable

GOOD = 'import sys\na,b=map(int,sys.stdin.read().split())\nprint(a+b)\n'
OFF1 = 'import sys\na,b=map(int,sys.stdin.read().split())\nprint(a+b+1)\n'
SYNTAX = 'import sys\ndef f(:\n    return 1\n'
HANG = 'while True:\n    pass\n'


def w(rel, text):
    p = os.path.join(D, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(text)
    return p


def fence(path, code):
    return w(path, "```python\n%s```\n" % code)


def summary(path, reply_rel, mode="ok", kind="program", tid="p001"):
    return w(path, json.dumps({"n_tasks": 1, "per_task": [
        {"tid": tid, "family": "sum2", "kind": kind, "mode": mode, "code_source": "transcript",
         "reply_paths": [os.path.join(D, reply_rel)], "artifacts": []}]}, ensure_ascii=False) + "\n")


def taskset(path):
    return w(path, json.dumps([{
        "tid": "p001", "family": "sum2", "kind": "program", "prompt": "两数之和",
        "public": [{"stdin": "2 3\n", "expected_stdout": "5\n"}],
        "hidden": [{"stdin": "2 3\n", "expected_stdout": "5\n"},
                   {"stdin": "-1 7\n", "expected_stdout": "6\n"},
                   {"stdin": "10 0\n", "expected_stdout": "10\n"}],
    }, {
        "tid": "m001", "family": "witness_x", "kind": "math", "prompt": "见证",
        "public": [], "hidden": [],
    }], ensure_ascii=False) + "\n")


def run(ts, cx, ag, out, timeout=None):
    cmd = [PY, TOOL, "--taskset", ts, "--codex", cx, "--agent", ag, "--out", out]
    if timeout:
        cmd += ["--timeout", str(timeout)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    txt = p.stdout + p.stderr
    return p.returncode, txt


def main():
    os.makedirs(D, exist_ok=True)
    ts = taskset("ts.json")
    good = fence("good.txt", GOOD)
    fence("off1.txt", OFF1)
    fence("syntax.txt", SYNTAX)
    fence("hang.txt", HANG)
    fence("crash.txt", 'import sys\nraise SystemExit("boom")\n')
    res = []

    def chk(name, cond, detail):
        res.append(cond)
        print("%-28s %s  %s" % (name, "PASS" if cond else "FAIL", detail))

    # NC1 正控
    cx, ag = summary("cx.json", "good.txt"), summary("ag.json", "good.txt")
    o1 = os.path.join(D, "o1.json")
    rc, t = run(ts, cx, ag, o1)
    chk("NC1 正控(两侧好码)", rc == 0 and "EXECUTABLE_AND_CORRECT=True" in t, "rc=%d" % rc)
    rc2, t2 = run(ts, cx, ag, os.path.join(D, "o1b.json"))
    same = io.open(o1, encoding="utf-8").read() == io.open(os.path.join(D, "o1b.json"), encoding="utf-8").read()
    chk("NC1b 确定性(两次逐字节同)", same and rc2 == rc, "same=%s" % same)

    # NC2 错值
    summary("cx.json", "good.txt"); ag = summary("ag.json", "off1.txt")
    rc, t = run(ts, cx, ag, os.path.join(D, "o2.json"))
    chk("NC2 错值⇒红+点名", rc == 1 and "agent/p001" in t and "cases=0/3" in t, "rc=%d" % rc)
    # NC3a 语法错（抽取层即拒 ⇒ 记不可执行）
    ag = summary("ag.json", "syntax.txt")
    rc, t = run(ts, cx, ag, os.path.join(D, "o3.json"))
    chk("NC3a 语法错⇒仍拦下(抽取层救回可编译前缀⇒按运行结果判红)", rc == 1 and "agent/p001" in t and "correct=False" in t, "rc=%d" % rc)
    # NC3b 可编译但运行即崩（真正打「可执行面」）
    ag = summary("ag.json", "crash.txt")
    rc, t = run(ts, cx, ag, os.path.join(D, "o3b.json"))
    chk("NC3b 运行即崩⇒exec 红", rc == 1 and "exec=rc=1" in t, "rc=%d" % rc)
    # NC4 死循环
    ag = summary("ag.json", "hang.txt")
    rc, t = run(ts, cx, ag, os.path.join(D, "o4.json"), timeout=2)
    chk("NC4 死循环⇒超时红", rc == 1 and "exec=rc=124" in t, "rc=%d" % rc)
    # NC5 非程序题（题集侧 kind=math ⇒ 无执行面）
    ts_math = w("ts_math.json", io.open(ts, encoding="utf-8").read().replace('"tid": "p001", "family": "sum2", "kind": "program"', '"tid": "p001", "family": "sum2", "kind": "math"'))
    cx, ag = summary("cx.json", "good.txt"), summary("ag.json", "good.txt")
    for f in ("cx.json", "ag.json"):
        d = json.load(io.open(os.path.join(D, f), encoding="utf-8"))
        d["per_task"][0]["mode"] = "ok"
        io.open(os.path.join(D, f), "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
    rc, t = run(ts_math, cx, ag, os.path.join(D, "o5.json"))
    d5 = json.load(io.open(os.path.join(D, "o5.json"), encoding="utf-8"))
    napp = all(r.get("exec") == "not-applicable" for s in ("codex", "agent") for r in d5["sides"][s]["rows"])
    chk("NC5 非程序题⇒无执行面", rc == 0 and napp and d5["executable_and_correct"] is True, "rc=%d napp=%s" % (rc, napp))
    # NC6 缺输入
    rc, t = run(ts, "/nonexistent.json", ag, os.path.join(D, "o6.json"))
    chk("NC6 缺输入⇒rc=3", rc == 3 and "fail-closed" in t, "rc=%d" % rc)
    # NC7 产物缺失
    cx = summary("cx.json", "good.txt")
    d = json.load(io.open(os.path.join(D, "ag.json"), encoding="utf-8"))
    d["per_task"][0].update({"kind": "program", "mode": "ok", "reply_paths": [os.path.join(D, "missing.txt")]})
    io.open(os.path.join(D, "ag.json"), "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
    rc, t = run(ts, cx, os.path.join(D, "ag.json"), os.path.join(D, "o7.json"))
    chk("NC7 产物缺失⇒no_code 红", rc == 1 and "no_code" in t, "rc=%d" % rc)

    ok = all(res)
    print("NC_CASES=%d/%d" % (sum(1 for x in res if x), len(res)))
    print("NC_TOTAL=%s" % ("OK" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
