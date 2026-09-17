#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R545 装配器 —— 复用 R544 的同题同输入夹具(逐字节同), 只改**被测开关的语义面**。

R545 是 R544 的**预注册修订轮**(revision 2): R544 的 J1 被同窗实测证伪
(`mechanism_on_arms_ran=False`: 3 个 on 臂只有 1 个走到回放点, 另 2 个在计划执行阶段就 rc=5)。
修法 = 触发面从 `exec.Rc==0` 扩到**全部「产物已在盘」的出口**(rc 0/5/8), 并让公开用例证据
优先回灌; 本装配器保证: 题面/用例/role 与 R544 **逐字节相同**(否则跨窗读数不可比)。

产出(全部落在 eval/rover/r545/):
  cases/run_cases_r521.py, cases/cases-r521.json   ← 从 r544 复制(逐字节校验 md5)
  role-r545.txt                                    ← 从 r544 复制(逐字节校验 md5)
  taskset-r545.json, input-pins-r545.json          ← 依 r544 现盘重算, 禁手抄数字
用法: python3 eval/rover/r545/setup_r545.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
R544 = os.path.join(REPO, "eval/rover/r544")
R545 = os.path.join(REPO, "eval/rover/r545")
FAIL = []


def md5(path: str) -> str:
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def note(ok: bool, what: str, got: str, exp: str) -> None:
    print("  %-34s got=%s exp=%s ok=%s" % (what, got[:24], exp[:24], ok))
    if not ok:
        FAIL.append(what)


def main() -> int:
    os.makedirs(os.path.join(R545, "cases"), exist_ok=True)

    # --- 1 夹具逐字节复制 + md5 交叉核对 (同环境同输入硬条件①) -----------------
    pairs = [
        ("cases/run_cases_r521.py", "cases/run_cases_r521.py"),
        ("cases/cases-r521.json", "cases/cases-r521.json"),
        ("role-r544.txt", "role-r545.txt"),
    ]
    for src_rel, dst_rel in pairs:
        s, d = os.path.join(R544, src_rel), os.path.join(R545, dst_rel)
        shutil.copyfile(s, d)
        note(md5(s) == md5(d), "byte-identical " + dst_rel, md5(d), md5(s))

    # --- 2 题面: 从 r544 现盘读, 重算 sha256 (禁手抄) --------------------------
    ts544 = json.load(io.open(os.path.join(R544, "taskset-r544.json"), encoding="utf-8"))
    t544 = [x for x in ts544["tasks"] if x["tid"] == "g1"][0]
    prompt = t544["prompt"]
    psha = sha256_text(prompt)
    pin544 = json.load(io.open(os.path.join(R544, "input-pins-r544.json"), encoding="utf-8"))["g1"]
    note(psha == t544.get("prompt_sha256") == pin544["prompt_sha256"],
         "g1 prompt 跨轮同 (sha256)", psha, pin544["prompt_sha256"])
    note(int(t544["hidden_cases"]) == int(pin544["hidden_cases"]),
         "hidden_cases 跨轮同", str(t544["hidden_cases"]), str(pin544["hidden_cases"]))
    note(t544["cases"] == "cases/run_cases_r521.py", "cases 脚本相对路径同", t544["cases"], "cases/run_cases_r521.py")

    task = dict(t544)
    task["prompt_sha256"] = psha
    ts545 = {"round": "r545", "window": ts544.get("window", "w1"),
             "source": "eval/rover/r544/taskset-r544.json (g1 单题面, 逐字节同)",
             "tasks": [task]}
    json.dump(ts545, io.open(os.path.join(R545, "taskset-r545.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # --- 3 输入钉 (全部现算) --------------------------------------------------
    pins = {"round": "r545", "recomputed_at_make_time": True,
            "g1": {
                "prompt_sha256": psha,
                "hidden_cases": int(t544["hidden_cases"]),
                "cases_script_md5": md5(os.path.join(R545, "cases/run_cases_r521.py")),
                "cases_json_md5": md5(os.path.join(R545, "cases/cases-r521.json")),
                "role_file_md5": md5(os.path.join(R545, "role-r545.txt")),
                "xref": [
                    {"what": "cases/run_cases_r521.py", "same": md5(os.path.join(R545, "cases/run_cases_r521.py"))
                     == md5(os.path.join(R544, "cases/run_cases_r521.py")),
                     "r544_md5": md5(os.path.join(R544, "cases/run_cases_r521.py"))},
                    {"what": "cases/cases-r521.json", "same": md5(os.path.join(R545, "cases/cases-r521.json"))
                     == md5(os.path.join(R544, "cases/cases-r521.json")),
                     "r544_md5": md5(os.path.join(R544, "cases/cases-r521.json"))},
                    {"what": "role-r545.txt", "same": md5(os.path.join(R545, "role-r545.txt"))
                     == md5(os.path.join(R544, "role-r544.txt")),
                     "r544_md5": md5(os.path.join(R544, "role-r544.txt"))},
                    {"what": "g1 prompt", "same": psha == pin544["prompt_sha256"],
                     "r544_sha256": pin544["prompt_sha256"]},
                ],
                "check": "run_r545.sh 起臂前逐项机检 sha256/md5 与上表一致, 不一致 ⇒ fail-closed rc=3 不起臂"}}
    json.dump(pins, io.open(os.path.join(R545, "input-pins-r545.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n装配结果: %s" % ("PASS" if not FAIL else "FAIL(%s)" % ",".join(FAIL)))
    return 0 if not FAIL else 3


if __name__ == "__main__":
    sys.exit(main())
