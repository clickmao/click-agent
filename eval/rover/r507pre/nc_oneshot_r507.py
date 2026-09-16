#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`external.contrast-exec-precondition` 的登记对：**缺陷注入必被检出**（一次一例，快）。

契约: 造一对合法夹具(两侧好码) ⇒ 绿; 把 agent 侧代码换成**错值**⇒ 器必须 rc=1 且点名 `agent/p001`。
检出 ⇒ 打印 `detect:NC_DETECTED` 且 rc=0; 没检出(器空心/恒绿) ⇒ 打印 `NC_MISSED` 且 rc=1。
"""
import io, json, os, subprocess, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "exec_precondition.py")
D = "/tmp/r507pre_nc1"

GOOD = "import sys\nn = list(map(int, sys.stdin.read().split()))\nprint(n[0] + n[1])\n"
BAD = "import sys\nn = list(map(int, sys.stdin.read().split()))\nprint(n[0] + n[1] + 1)\n"

TS = [{
    "tid": "p001", "family": "sum2", "kind": "program",
    "prompt": "读两个整数, 打印和",
    "public": [{"stdin": "2 3\n", "expected_stdout": "5\n"}],
    "hidden": [{"stdin": "2 3\n", "expected_stdout": "5\n"},
               {"stdin": "-1 7\n", "expected_stdout": "6\n"},
               {"stdin": "10 0\n", "expected_stdout": "10\n"}],
}]


def main():
    shutil.rmtree(D, ignore_errors=True)
    os.makedirs(D)
    io.open(os.path.join(D, "ts.json"), "w", encoding="utf-8").write(json.dumps(TS, ensure_ascii=False, indent=1) + "\n")
    io.open(os.path.join(D, "reply_codex.txt"), "w", encoding="utf-8").write("```python\n" + GOOD + "```\n")
    io.open(os.path.join(D, "reply_agent_bad.txt"), "w", encoding="utf-8").write("```python\n" + BAD + "```\n")
    for name, reply in (("cx.json", "reply_codex.txt"), ("agbad.json", "reply_agent_bad.txt"),
                        ("aggood.json", "reply_codex.txt")):
        io.open(os.path.join(D, name), "w", encoding="utf-8").write(json.dumps(
            {"per_task": [{"tid": "p001", "kind": "program", "family": "sum2", "mode": "ok",
                           "code_source": "transcript",
                           "reply_paths": [os.path.join(D, reply)],   # 必绝对路径(相对名会被判 no_code ⇒ 空心NC)
                           "artifacts": []}]},
            ensure_ascii=False, indent=1) + "\n")
    # ① 正控: 两侧同为好码 ⇒ 必须**绿**(否则器恒红 = 空心)
    p0 = subprocess.run([sys.executable, TOOL, "--taskset", os.path.join(D, "ts.json"),
                         "--codex", os.path.join(D, "cx.json"), "--agent", os.path.join(D, "aggood.json"),
                         "--out", os.path.join(D, "out0.json")], capture_output=True, text=True, timeout=120)
    sys.stdout.write(p0.stdout)
    print("NC0(正控) rc=%d" % p0.returncode)
    if p0.returncode != 0 or "EXECUTABLE_AND_CORRECT=True" not in p0.stdout:
        print("NC_HOLLOW: 正控未绿 ⇒ 器恒红, 负控无判别力")
        return 1
    args = [sys.executable, TOOL, "--taskset", os.path.join(D, "ts.json"),
            "--codex", os.path.join(D, "cx.json"), "--agent", os.path.join(D, "agbad.json"),
            "--out", os.path.join(D, "out.json")]
    p = subprocess.run(args, capture_output=True, text=True, timeout=120)
    t = p.stdout
    hit = (p.returncode == 1) and ("agent/p001" in t) and ("BLOCKED" in t.upper())
    sys.stdout.write(t)
    print("NC1 rc=%d hit=%s" % (p.returncode, hit))
    if hit:
        print("detect:NC_DETECTED")
        return 0
    print("NC_MISSED rc=%d" % p.returncode)
    return 1


if __name__ == "__main__":
    sys.exit(main())
