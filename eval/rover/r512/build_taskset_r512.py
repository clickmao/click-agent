#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R512 题集生成器: 由 R511 冻结题集**取题面**(逐字节) + 补全 project 布局字段。

为什么需要: R511 的 `taskset-r511.json` 里 p4 缺 `cases`/`ref`/`hidden_cases` 字段
(判分器 grade_r511 是**硬编码** p3/p4 路径的), 而铁律 11 的 project 布局前置器
(`eval/rover/r507pre/exec_precondition.py`) 需要从 taskset 读 `cases`/`hidden_cases`。
本器: 只做**字段补全 + 字节级复制**, 题面字符串一字不改 —— 补全后逐题 prompt sha256
必须 == R511 同 tid 的 prompt sha256, 不等即 fail-closed rc=3 (禁静默改题)。

用法: python3 eval/rover/r512/build_taskset_r512.py [--check]
退出码: 0 写/校验通过 · 3 fail-closed (题面漂移 / 源缺失)
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, shutil, sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval/rover/r512")
SRC511 = os.path.join(REPO, "eval/rover/r511/taskset-r511.json")

# 题面来源 (逐字节取), 隐藏用例/参考解来源 (字节复制)
PLAN = {
    "p3": {"family": "threaded-kv-service", "entry": "kvsvc/server.py",
           "cases_src": "eval/rover/r508/cases/p3_cases.py", "cases": "cases/p3_cases.py",
           "ref_src": "eval/rover/r508/ref/p3", "ref": "ref/p3", "hidden_cases": 12},
    "p4": {"family": "task-queue-cli", "entry": "tasksvc/cli.py",
           "cases_src": "eval/rover/r511/cases/p4_cases.py", "cases": "cases/p4_cases.py",
           "ref_src": "eval/rover/r511/ref/p4", "ref": "ref/p4", "hidden_cases": 12},
}


def sha256_file(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验现盘题集与源一致, 不写")
    a = ap.parse_args()

    src = json.load(io.open(SRC511, encoding="utf-8-sig"))
    by_tid = {t["tid"]: t for t in src["tasks"]}
    missing = [t for t in PLAN if t not in by_tid]
    if missing:
        print("[致命] R511 题集缺题: %s" % missing)
        return 3

    tasks, ev = [], {}
    for tid, pl in PLAN.items():
        prompt = by_tid[tid]["prompt"]
        psha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cs = os.path.join(REPO, pl["cases_src"])
        rs = os.path.join(REPO, pl["ref_src"])
        if not os.path.isfile(cs) or not os.path.isdir(rs):
            print("[致命] 源缺失 tid=%s cases=%s ref=%s" % (tid, os.path.exists(cs), os.path.exists(rs)))
            return 3
        ev[tid] = {"prompt_sha256": psha, "sources": {"cases": pl["cases_src"], "ref": pl["ref_src"]},
                   "cases_sha256": sha256_file(cs)}
        if not a.check:
            os.makedirs(os.path.join(HERE, "cases"), exist_ok=True)
            shutil.copy2(cs, os.path.join(HERE, pl["cases"]))
            dst = os.path.join(HERE, pl["ref"])
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(rs, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        tasks.append({"tid": tid, "kind": "project", "family": pl["family"], "entry": pl["entry"],
                      "cases": pl["cases"], "ref": pl["ref"], "hidden_cases": pl["hidden_cases"],
                      "prompt": prompt, "prompt_sha256": psha})

    # 复制后逐字节复核 (题面 + 用例脚本)
    for t in tasks:
        pl = PLAN[t["tid"]]
        cs = os.path.join(REPO, pl["cases_src"])
        cd = os.path.join(HERE, pl["cases"])
        if os.path.isfile(cd) and sha256_file(cd) != sha256_file(cs):
            print("[致命] 用例脚本复制后字节不一致 tid=%s" % t["tid"])
            return 3

    ts_path = os.path.join(HERE, "taskset-r512.json")
    if a.check:
        if not os.path.isfile(ts_path):
            print("[致命] 现盘缺 %s" % ts_path)
            return 3
        cur = json.load(io.open(ts_path, encoding="utf-8-sig"))
        now = {x["tid"]: hashlib.sha256(x["prompt"].encode("utf-8")).hexdigest() for x in cur["tasks"]}
        want = {k: v["prompt_sha256"] for k, v in ev.items()}
        if now != want:
            print("[致命] 题面漂移 now=%s want=%s" % (now, want))
            return 3
        print("TASKSET_CHECK_OK %s" % ts_path)
        print(json.dumps({"prompt_sha256": want}, ensure_ascii=False))
        return 0

    doc = {"taskset": "r512", "window": "R512",
           "derived_from": {"taskset": "eval/rover/r511/taskset-r511.json",
                            "sha256": sha256_file(SRC511),
                            "rule": "题面逐字节取自 R511; 本器只补 project 布局字段 (kind/family/entry/cases/ref/hidden_cases)"},
           "tasks": tasks}
    with io.open(ts_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print("WROTE %s sha256=%s" % (ts_path, sha256_file(ts_path)))
    print(json.dumps(ev, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
