#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R512 判据器负控 (判别力证据) —— 判分器 = eval/rover/r511/grade_r511.py (本轮唯一判分入口)。

① 正控: 两侧参考解 (p3 ref / p4 ref) 必须全过; 不过 ⇒ NC_HOLLOW (判据器空心 ⇒ 本轮读数弃权)。
② 负控: 对参考解注入**指名缺陷** ⇒ 整题必须变红, 且**预期用例必须真失败** (未命中 ⇒ NC_NOT_DETECTED;
   补丁没打上 ⇒ PATCH_NOT_APPLIED, fail-closed)。
用法: python3 nc_r512.py [--json out.json]   退出码 0 全绿 / 1 有未检出 / 3 空心。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GRADE = os.path.join(HERE, "..", "r511", "grade_r511.py")
REF = {"p3": os.path.join(HERE, "..", "r508", "ref", "p3"),
       "p4": os.path.join(HERE, "..", "r511", "ref", "p4")}

MUTANTS = []

# p3 的突变体**直接复用** R508 已入册的 (mid, task, rel, old, new, expect) 六元组 ⇒ 逐字节同源, 不重写不猜。
sys.path.insert(0, os.path.join(HERE, "..", "r508"))
import nc_r508  # noqa: E402

MUTANTS = [(m[0], m[1], [(m[2], m[3], m[4])], m[5]) for m in nc_r508.MUTANTS if m[1] == "p3"]
MUTANTS += [
    ("p4_inplace_write", "p4", [("tasksvc/store.py",
      "        os.replace(tmp, path)",
      "        with open(path, \"w\", encoding=\"utf-8\", newline=\"\\n\") as fh2:\n"
      "            json.dump(state, fh2, ensure_ascii=False, sort_keys=True)\n"
      "            fh2.write(\"\\n\")")],
     ["no_temp_residue"]),
    ("p4_id_reuse", "p4", [("tasksvc/cli.py",
      "            state[\"next_id\"] = int(state[\"next_id\"]) + 1",
      "            pass")],
     ["id_monotonic_no_reuse"]),
    ("p4_ttl_never_expires", "p4", [("tasksvc/model.py",
      "    return exp is not None and float(now) >= float(exp)",
      "    return False")],
     ["expire_removes_expired_tasks"]),
]


def grade(task, d):
    out = os.path.join(d, "_grade.json")
    p = subprocess.run([sys.executable, GRADE, "--task", task, "--dir", d, "--json", out],
                       capture_output=True, text=True, timeout=900)
    data = {}
    if os.path.exists(out):
        with open(out, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    data["_rc"] = p.returncode
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    report = {"round": "R512", "grader": "eval/rover/r511/grade_r511.py", "hollow": False,
              "positive": {}, "mutants": []}

    for task in sorted(REF):
        pdir = tempfile.mkdtemp(prefix="r512-nc-pos-")
        shutil.copytree(os.path.join(HERE, REF[task]), pdir, dirs_exist_ok=True)
        r = grade(task, pdir)   # 只对**副本**判分 ⇒ 不污染参考解树 (R512 教训: _grade.json 会落在被判目录里)
        shutil.rmtree(pdir, ignore_errors=True)
        report["positive"][task] = {"all_pass": bool(r.get("ok")), "pass": r.get("cases_passed"),
                                    "of": r.get("cases_total"), "rc": r.get("_rc")}
        if not r.get("ok"):
            report["hollow"] = True
    if report["hollow"]:
        report["verdict"] = "NC_HOLLOW"
        _emit(report, a.json)
        return 3

    all_ok = True
    for mid, task, edits, expect in MUTANTS:
        tmp = tempfile.mkdtemp(prefix="r512-nc-")
        shutil.copytree(os.path.join(HERE, REF[task]), tmp, dirs_exist_ok=True)
        applied = True
        for rel, old, new in edits:
            path = os.path.join(tmp, rel)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            if old not in text:
                report["mutants"].append({"id": mid, "task": task, "expect_fail": expect,
                                          "detected": False, "patch": "PATCH_NOT_APPLIED", "file": rel})
                applied = False
                all_ok = False
                break
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace(old, new, 1))
        if not applied:
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        r = grade(task, tmp)
        failed = [c["name"] for c in r.get("failed", [])]
        missed = [c for c in expect if c not in failed]
        detected = (not r.get("ok")) and not missed
        all_ok = all_ok and detected
        report["mutants"].append({"id": mid, "task": task, "expect_fail": expect,
                                  "failed_cases": failed, "missed": missed,
                                  "all_pass_after_mutation": bool(r.get("ok")), "detected": detected})
        shutil.rmtree(tmp, ignore_errors=True)

    report["verdict"] = "SELFTEST=OK" if all_ok else "NC_NOT_DETECTED"
    _emit(report, a.json)
    return 0 if all_ok else 1


def _emit(report, path):
    blob = json.dumps(report, ensure_ascii=False, indent=1)
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(blob)
    print("POSITIVE", json.dumps(report["positive"], ensure_ascii=False))
    for m in report["mutants"]:
        print("MUTANT %-22s detected=%s failed=%s missed=%s" % (m["id"], m["detected"],
                                                               m.get("failed_cases"), m.get("missed")))
    print("VERDICT", report["verdict"])


if __name__ == "__main__":
    raise SystemExit(main())
