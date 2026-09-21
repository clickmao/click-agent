#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R629 · 披露式负控（**新机检器首上线必跑**，三步成对，禁只跑一端）。

技能硬要求（判定卫生）：新机检器首次上线必须对**修前/对照窗口**跑一次并**判红**（负控），
命令与判定写入预注册文件；治疗臂被自身机检证伪时停臂、保留跑次、以 v2 **阈值不变**重注册
并披露 v1 失败项，**禁事后调阈值**。

三步（每步都要求**判决可读**，不只跑成功）：
  STEP1  修前窗口（R628 已落盘判决件）      ⇒ 必须 rc=2（D1/D1b/D2/D3 全命中）
  STEP2  修后窗口（R629 修正形态判决件）    ⇒ 必须 rc=0（四项全清）
  STEP3  候选④ 负控形态转正                 ⇒ 必须 teeth=true（旧形态在门上时判红）

只读、零产品源码改动、零远端 LLM。退出码 0 = 三步全按预期；1 = 有一步未按预期；3 = 输入缺失。
"""

import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _repo_root(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.isdir(os.path.join(p, "eval", "rover")) and os.path.isdir(os.path.join(p, "src")):
            return p
        p = os.path.dirname(p)
    return os.path.abspath(os.path.join(start, ".."))


REPO = _repo_root(HERE)


def run(args):
    pr = subprocess.run([sys.executable, "-B"] + args, cwd=REPO,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return pr.returncode, pr.stdout.decode("utf-8", "replace")


def main():
    for rel in ("eval/rover/r628/verdict-r628.json", "eval/rover/r628/prereg-r628.json",
                "eval/rover/r629/verdict-r629.json", "eval/rover/r629/prereg-r629.json"):
        if not os.path.exists(os.path.join(REPO, rel)):
            print("INPUT_MISSING %s" % rel)
            return 3
    steps = {}

    rc1, o1 = run(["eval/rover/r629/judge_r629.py",
                   "--out", "eval/rover/r629/evidence/judge-prefix-r628.json",
                   "--round-tag", "r628", "--controls"])
    try:
        v1 = json.load(io.open(os.path.join(REPO, "eval/rover/r629/evidence/judge-prefix-r628.json"),
                               encoding="utf-8"))
    except Exception:
        v1 = None
    ids1 = [d["id"] for d in ((v1 or {}).get("POS_recorded", {}).get("defects") or [])]
    teeth1 = ((v1 or {}).get("paired_controls") or {}).get("teeth")
    steps["STEP1_prefix_window"] = {
        "expect": "rc=2 ∧ D1,D1b,D2b,D3 全命中 ∧ teeth=true",
        "rc": rc1, "defect_ids": ids1, "teeth": teeth1,
        "pass": bool(rc1 == 2 and set(["D1", "D1b", "D2b", "D3"]).issubset(set(ids1)) and teeth1),
        "stdout_tail": o1.strip().splitlines()[-3:],
    }

    rc2, o2 = run(["eval/rover/r629/judge_r629.py",
                   "--out", "eval/rover/r629/judge-r629.json",
                   "--round-tag", "r629",
                   "--prereg", "eval/rover/r629/prereg-r629.json",
                   "--verdict", "eval/rover/r629/verdict-r629.json"])
    try:
        v2 = json.load(io.open(os.path.join(REPO, "eval/rover/r629/judge-r629.json"), encoding="utf-8"))
    except Exception:
        v2 = None
    p2 = (v2 or {}).get("POS_recorded", {})
    steps["STEP2_fixed_window"] = {
        "expect": "rc=0 ∧ 主判据落盘 ∧ 判决来源==主判据 ∧ 指针存在 ∧ 无缺陷",
        "rc": rc2,
        "primary_present": p2.get("primary_present_in_verdict_toplevel"),
        "verdict_source_is_primary": p2.get("verdict_source_is_primary"),
        "iron11_exists": (p2.get("iron11") or {}).get("exists"),
        "defect_ids": [d["id"] for d in (p2.get("defects") or [])],
        "pass": bool(rc2 == 0 and p2.get("primary_present_in_verdict_toplevel")
                     and p2.get("verdict_source_is_primary")
                     and (p2.get("iron11") or {}).get("exists")
                     and not (p2.get("defects") or [])),
        "stdout_tail": o2.strip().splitlines()[-3:],
    }

    rc3, o3 = run(["eval/rover/r629/nc_metric_r629.py",
                   "--out", "eval/rover/r629/nc-form-r629.json", "--controls"])
    try:
        v3 = json.load(io.open(os.path.join(REPO, "eval/rover/r629/nc-form-r629.json"), encoding="utf-8"))
    except Exception:
        v3 = None
    tv = ((v3 or {}).get("paired_controls") or {}).get("teeth")
    steps["STEP3_nc_form"] = {
        "expect": "rc=0 ∧ teeth=true（旧形态在门上判红 / 差异量平化判红 / 真盘判绿）",
        "rc": rc3, "teeth": tv,
        "pass": bool(rc3 == 0 and tv),
        "stdout_tail": o3.strip().splitlines()[-3:],
    }

    allpass = all(s["pass"] for s in steps.values())
    out = {
        "schema": "r629-negform/1", "round": "R629", "kind": "disclosed-negative-control",
        "rule": ("新机检器首上线：修前窗口必判红、修后窗口必判绿；负控形态转正须有牙。"
                 "阈值**不变**（判据 v3 主判据阈值 −0.34 与 R628 一致）；R628 已落盘判决**不翻案**。"),
        "steps": steps,
        "verdict": {"rc": 0 if allpass else 1,
                    "judge": "三步全按预期（修前红 / 修后绿 / 负控有牙）" if allpass else "有步骤未按预期"},
    }
    op = os.path.join(HERE, "negform-r629.json")
    io.open(op, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    for k, s in steps.items():
        print("%-22s rc=%s pass=%s" % (k, s["rc"], s["pass"]))
    print("rc=%d（%s）" % (out["verdict"]["rc"], out["verdict"]["judge"]))
    return out["verdict"]["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
