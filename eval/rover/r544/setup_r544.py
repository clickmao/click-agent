#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R544 器具装配 —— 把 g1 题面/用例面**逐字节**从 R542 复制到本轮命名空间, 并机取输入 pin。

为什么复制而不是引用: 轮次命名空间必须自洽(单轮内所有输入可核), 且复制后**md5 必须逐项等于
R542 的值**(不等 ⇒ 判分面被换过 ⇒ fail-closed 拒绝起臂)。本脚本自己断言这一点。
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r542")
DST = os.path.join(REPO, "eval/rover/r544")


def md5(path: str) -> str:
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def main() -> int:
    os.makedirs(os.path.join(DST, "cases"), exist_ok=True)
    os.makedirs(os.path.join(DST, "logs"), exist_ok=True)

    # 1 逐字节复制 (用例脚本 / 用例语料 / role 额外数据)
    for rel in ("cases/run_cases_r521.py", "cases/cases-r521.json"):
        shutil.copy2(os.path.join(SRC, rel), os.path.join(DST, rel))
    shutil.copy2(os.path.join(SRC, "role-r542.txt"), os.path.join(DST, "role-r544.txt"))

    # 2 题集: 题面正文逐字节复用, 只改 round 字段
    src_ts = json.load(io.open(os.path.join(SRC, "taskset-r542.json"), encoding="utf-8"))
    ts = dict(src_ts)
    ts["round"] = "r544"
    ts["note"] = ("g1 单题面(逐字节复用 r542/r540/r531/r536, sha256 已钉); "
                  "本轮为**产物侧公开用例独立回放**(单变量 AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK)对照, 不引入新题面")
    io.open(os.path.join(DST, "taskset-r544.json"), "w", encoding="utf-8").write(
        json.dumps(ts, ensure_ascii=False, indent=1) + "\n")

    # 3 pin 机取 + 与 R542 逐项对账 (任一不等 ⇒ rc=3)
    old = json.load(io.open(os.path.join(SRC, "input-pins-r542.json"), encoding="utf-8"))["g1"]
    prompt = ts["tasks"][0]["prompt"]
    cur = {
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "bytes": len(prompt.encode()),
        "hidden_cases": int(ts["tasks"][0]["hidden_cases"]),
        "cases_script_md5": md5(os.path.join(DST, "cases/run_cases_r521.py")),
        "cases_json_md5": md5(os.path.join(DST, "cases/cases-r521.json")),
        "role_file_md5": md5(os.path.join(DST, "role-r544.txt")),
    }
    bad = [k for k, v in cur.items() if old.get(k) != v]
    for k in sorted(cur):
        print("  %-18s cur=%s r542=%s %s" % (k, cur[k], old.get(k), "OK" if old.get(k) == cur[k] else "MISMATCH"))
    if bad:
        print("装配失败: 与 R542 不一致的项 %s ⇒ fail-closed" % bad)
        return 3

    pin = {
        "round": "r544",
        "g1": {
            **cur,
            "prompt_sha256_declared": ts["tasks"][0]["prompt_sha256"],
            "xref": [
                {"taskset": "eval/rover/r542/taskset-r542.json", "same": True},
                {"taskset": "eval/rover/r540/taskset-r540.json", "same": True},
                {"role": "eval/rover/r542/role-r542.txt", "same": True},
            ],
        },
    }
    io.open(os.path.join(DST, "input-pins-r544.json"), "w", encoding="utf-8").write(
        json.dumps(pin, ensure_ascii=False, indent=1) + "\n")
    print("装配完成: %s (逐项 == R542)" % os.path.relpath(DST, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
