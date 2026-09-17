#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R540 题集构造 —— **同输入铁条件①** 的机械保证: 题面逐字节复用, 不重写。

t1 题面来源 = eval/rover/r539/taskset-r539.json (F2 toolkit-multimodule-v1)
g1 题面来源 = eval/rover/r531/taskset-r531.json (F1 games-longtask-v1, 58 隐藏用例)
两条 sha256 必须与 r536/r539/r531 三方一致; 不一致 ⇒ rc=3 fail-closed, 不产出题集。

同时产出 input-pins-r540.json (供报告与收口器引用)。
用法: python3 eval/rover/r540/build_taskset_r540.py
"""
from __future__ import annotations
import hashlib, io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
R = os.path.join(REPO, "eval/rover/r540")
SRC = {"t1": os.path.join(REPO, "eval/rover/r539/taskset-r539.json"),
       "g1": os.path.join(REPO, "eval/rover/r531/taskset-r531.json")}
XREF = [os.path.join(REPO, "eval/rover/r536/taskset-r536.json"),
        os.path.join(REPO, "eval/rover/r539/taskset-r539.json")]
OUT = os.path.join(R, "taskset-r540.json")
PINS = os.path.join(R, "input-pins-r540.json")


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    tasks, pins, bad = [], {}, []
    for tid, path in SRC.items():
        d = json.load(io.open(path, encoding="utf-8"))
        t = [x for x in d["tasks"] if x["tid"] == tid][0]
        p = t["prompt"]
        h = sha(p)
        if h != t["prompt_sha256"]:
            bad.append("%s: 源自洽失败 (sha=%s decl=%s)" % (tid, h[:16], (t["prompt_sha256"] or "")[:16]))
        xref = []
        for xp in XREF:
            if not os.path.isfile(xp):
                continue
            dx = json.load(io.open(xp, encoding="utf-8"))
            for tx in dx["tasks"]:
                if tx["tid"] == tid:
                    same = (sha(tx["prompt"]) == h)
                    xref.append({"taskset": os.path.relpath(xp, REPO), "same": same})
                    if not same:
                        bad.append("%s: 与 %s 题面不一致" % (tid, os.path.relpath(xp, REPO)))
        pins[tid] = {"src": os.path.relpath(path, REPO), "prompt_sha256": h, "bytes": len(p.encode("utf-8")),
                     "case_bytes": len(t["prompt"].encode("utf-8")), "hidden_cases": t["hidden_cases"],
                     "cases": t["cases"], "family": t["family"], "xref": xref}
        tasks.append(t)
        print("pin %s sha=%s bytes=%d hidden=%s src=%s" % (tid, h[:16], len(p.encode("utf-8")),
                                                           t["hidden_cases"], os.path.relpath(path, REPO)))
    for c in sorted(os.listdir(os.path.join(R, "cases"))):
        pass
    if bad:
        for b in bad:
            print("RED " + b)
        return 3
    json.dump({"round": "r540", "tasks": tasks}, io.open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    role = io.open(os.path.join(R, "role-r540.txt"), encoding="utf-8").read()
    pins["role"] = {"file": "eval/rover/r540/role-r540.txt", "md5": hashlib.md5(role.encode()).hexdigest(),
                    "bytes": len(role.encode("utf-8")),
                    "md5_equal_to_r539": hashlib.md5(role.encode()).hexdigest() ==
                    hashlib.md5(io.open(os.path.join(REPO, "eval/rover/r539/role-r539.txt"), encoding="utf-8").read().encode()).hexdigest()}
    if not pins["role"]["md5_equal_to_r539"]:
        print("RED role 文件与 R539 不一致")
        return 3
    json.dump(pins, io.open(PINS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("题集写出 %s (tasks=%d); pins => %s" % (os.path.relpath(OUT, REPO), len(tasks), os.path.relpath(PINS, REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
