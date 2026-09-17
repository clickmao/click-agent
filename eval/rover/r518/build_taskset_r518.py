#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R518 题集装配 (双包规模面): p3 (kvsvc, 12 隐藏用例) + p4 v2 (tasksvc, 12 隐藏用例)。

为什么这么装配:
  * 规模面 > 单轮硬顶 —— 双包 6 文件 / 24 用例, 单轮一次成型必超 32 步硬顶 (R515 遗留项)。
  * 逐字节继承已验题面: p3 取 R508 入库题面, p4 取 R513 修订后 v2 题面 (sha 与入库值比对),
    两侧臂共用同一 taskset 文件 ⇒ 同输入由构造保证 (不靠事后口头声明)。
  * cases/ref 逐文件 sha256 拷贝读回 (判分器与参考产物同源同字节)。

fail-closed:
  ① 源题面 sha256 与已入库值不一致 ⇒ rc=3 不写任何文件 (禁改题);
  ② cases/ref 拷贝后逐文件 sha256 读回不一致 ⇒ rc=3;
  ③ 输出已存在且要求 --force 未给 ⇒ rc=4 (禁覆盖)。
用法: python3 build_taskset_r518.py [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r518")

# (tid, 源 taskset, 源 sha256 入库值) —— 禁改题: 源 sha 必须逐位命中
SOURCES = {
    "p3": ("eval/rover/r508/taskset-r508.json", "efa48cb2ccef6b4760211910b8ae277f9a5ff41eae5a8d0fd0b4df029faa23eb"),
    "p4": ("eval/rover/r513/taskset-r513.json", "384fa7212378b5d734e9a98bbf134bc734142cef5a6049566c532bd611c622bd"),
}
# 题目件同源 (权威: 判分器 grade_r511.py 的 CASES 表 —— 必须与之一致, 否则两侧判分口径不同)
CASES_SRC = {
    "p3": "eval/rover/r508/cases/p3_cases.py",
    "p4": "eval/rover/r511/cases/p4_cases.py",
}
REF_SRC = {
    "p3": "eval/rover/r508/ref/p3",
    "p4": "eval/rover/r513/ref/p4",
}
PKG = {"p3": "kvsvc", "p4": "tasksvc"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 16), b""):
            h.update(blk)
    return h.hexdigest()


def copy_tree_verified(src: str, dst: str) -> int:
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, src)
        tgt = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(tgt, exist_ok=True)
        for f in sorted(files):
            if f.endswith((".pyc", ".pyo")):
                continue
            s, d = os.path.join(root, f), os.path.join(tgt, f)
            shutil.copy2(s, d)
            if sha256_file(s) != sha256_file(d):
                raise RuntimeError("拷贝读回不一致: %s" % s)
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="只校验: 题面 sha 未动 + 盘上 cases/ref 与源逐字节一致 (起臂前自检, 不写)")
    a = ap.parse_args()

    tasks, prov = [], []
    for tid, (ts_path, want_sha) in SOURCES.items():
        with io.open(os.path.join(REPO, ts_path), encoding="utf-8") as fh:
            ts = json.load(fh)
        t = next((x for x in ts["tasks"] if x["tid"] == tid), None)
        if t is None:
            print("[致命] %s 题面缺失于 %s" % (tid, ts_path))
            return 3
        got = sha256_bytes(t["prompt"].encode("utf-8"))
        if got != want_sha:
            print("[致命] %s 题面 sha 不匹配 (禁改题): got=%s want=%s" % (tid, got, want_sha))
            return 3
        row = dict(t)
        row["cases"] = "cases/%s_cases.py" % tid
        row["ref"] = "ref/%s" % tid
        row["fixture_src"] = {"taskset": ts_path, "cases": CASES_SRC[tid], "ref": REF_SRC[tid]}
        row["prompt_sha256"] = got
        tasks.append(row)
        prov.append({"tid": tid, "prompt_sha256": got, "cases_md5": hashlib.md5(
            io.open(os.path.join(REPO, CASES_SRC[tid]), "rb").read()).hexdigest()})

    ts_out = os.path.join(OUT, "taskset-r518.json")
    if a.check:
        bad = []
        for tid in SOURCES:
            cs, cd = os.path.join(REPO, CASES_SRC[tid]), os.path.join(OUT, "cases", "%s_cases.py" % tid)
            if not os.path.isfile(cd) or sha256_file(cs) != sha256_file(cd):
                bad.append("cases/%s_cases.py" % tid)
            sd, dd = os.path.join(REPO, REF_SRC[tid]), os.path.join(OUT, "ref", tid)
            for root, _d, fs in os.walk(sd):
                for f in fs:
                    sp = os.path.join(root, f)
                    dp = os.path.join(dd, os.path.relpath(sp, sd))
                    if not os.path.isfile(dp) or sha256_file(sp) != sha256_file(dp):
                        bad.append(os.path.relpath(sp, REPO))
        if not os.path.isfile(ts_out):
            bad.append("taskset-r518.json (缺失)")
        else:
            on_disk = json.load(io.open(ts_out, encoding="utf-8-sig"))
            want = {t["tid"]: t["prompt_sha256"] for t in tasks}
            got = {t["tid"]: t.get("prompt_sha256") for t in on_disk.get("tasks") or []}
            if want != got:
                bad.append("taskset prompt_sha256 漂移: %s" % got)
        if bad:
            print("[致命] 题集自检失败: %s" % bad[:5])
            return 3
        print("TASKSET_CHECK_OK tasks=%d" % len(tasks))
        for p in prov:
            print("  %s prompt_sha=%s cases_md5=%s" % (p["tid"], p["prompt_sha256"][:12], p["cases_md5"][:12]))
        return 0

    if not a.write:
        print(json.dumps({"tasks": [t["tid"] for t in tasks], "prov": prov}, ensure_ascii=False, indent=1))
        return 0

    ts_out = os.path.join(OUT, "taskset-r518.json")
    if os.path.exists(ts_out) and not a.force:
        print("[致命] %s 已存在 (禁覆盖, 需 --force)" % ts_out)
        return 4
    # 先拷件 (fail-closed: 拷件不过就不写题集)
    n_cases = 0
    for tid in SOURCES:
        cs, cd = os.path.join(REPO, CASES_SRC[tid]), os.path.join(OUT, "cases", "%s_cases.py" % tid)
        os.makedirs(os.path.dirname(cd), exist_ok=True)
        shutil.copy2(cs, cd)
        if sha256_file(cs) != sha256_file(cd):
            print("[致命] cases 拷贝读回不一致: %s" % tid)
            return 3
        n_cases += 1
        rd = os.path.join(OUT, "ref", tid)
        if os.path.isdir(rd):
            shutil.rmtree(rd)
        n_cases += copy_tree_verified(os.path.join(REPO, REF_SRC[tid]), rd)
    with io.open(ts_out, "w", encoding="utf-8") as fh:
        json.dump({"round": "R518", "kind": "project", "provenance": prov, "tasks": tasks},
                  fh, ensure_ascii=False, indent=1)
    print("TASKSET_WRITTEN %s tasks=%d files=%d" % (ts_out, len(tasks), n_cases))
    for t in tasks:
        print("  %s %s cases=%s ref=%s prompt_sha=%s" % (t["tid"], t["family"], t["cases"], t["ref"], t["prompt_sha256"][:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
