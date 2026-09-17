#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R518 规模面计划/范围生成器 (7 节点双包) —— **生成即机检, 非法不落盘**。

事故背景 (R517 自抓): 范围文件被生成器二次覆盖 (节点重复声明) ⇒ 编排器起手即 fail-closed
rc=2「范围文件非法」, 整臂零产物、整轮读数作废。旧流程「先生成, 跑起来才发现」。
本轮的修法: 生成器把产物写在内存/临时文件里, 先过 `check_plan_contract.py` 契约机检,
**全绿才 rename 落盘**; 任一条红 ⇒ rc=1 且不留任何产物 (fail-closed)。

节点结构 (双包 = 规模面 > 单轮硬顶 32 步):
  tasksvc (p4, 12 隐藏用例): n1 存储层 → n2 模型/时间 → n3 命令行+状态机+输出; n4=本地自测
  kvsvc   (p3, 12 隐藏用例): q1 持久化层 → q2 HTTP 服务;                         q3=本地自测
  远端节点 5 个 (n1,n2,n3,q1,q2) 必须逐节点声明写范围; 本地节点 (n4,q3) 禁声明
  (本地自测执行器不产文件 ⇒ 一旦声明范围即被判「零产物」假绿拦截)。
用法: python3 gen_plan_r518.py [--write] [--plan-out P] [--scope-out S]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r518")
TASKSET = os.path.join(OUT, "taskset-r518.json")

# 段切分: 每题的「本段职责」用哪些编号规则 (规则文本从题面里机械切出, 禁手抄)
SEGMENTS = {
    "p4": [
        ("n1", [], "tasksvc/__init__.py, tasksvc/store.py", "第 1 段 (存储层)", [1, 9, 10], "tasksvc"),
        ("n2", ["n1"], "tasksvc/model.py", "第 2 段 (模型/时间)", [2, 4], "tasksvc"),
        ("n3", ["n2"], "tasksvc/cli.py", "第 3 段 (命令行/状态机/输出)", [3, 5, 6, 7, 8], "tasksvc"),
    ],
    "p3": [
        ("q1", ["n3"], "kvsvc/__init__.py, kvsvc/store.py", "第 1 段 (持久化层)", [6, 7], "kvsvc"),
        ("q2", ["q1"], "kvsvc/server.py", "第 2 段 (HTTP 服务)", [1, 2, 3, 4, 5, 7], "kvsvc"),
    ],
}
LOCAL_NODES = [
    ("n4", ["n1"], "tasksvc/store.py", "本地自测: 存储层"),
    ("q3", ["q1"], "kvsvc/store.py", "本地自测: 持久化层"),
]

RULE_RE = re.compile(r"(?:^|\s)(\d{1,2})[)）.、]")


def split_rules(prompt: str) -> "dict[int, str]":
    """按「N) / N. / N、」切出编号规则。返回 {n: text}。"""
    marks = [(m.start(), int(m.group(1))) for m in RULE_RE.finditer(prompt)]
    out = {}
    for i, (pos, num) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(prompt)
        out[num] = prompt[pos:end].strip()
    return out


def flat(s: str) -> str:
    """计划 DSL 是行式记录 (每节点一行) ⇒ 文本字段必须压成单行。

    注意: **不得**改写 '|' —— 计划解析器按 `Split('|', 5)` 只切前 4 个分隔符,
    节点文本里的 '|' (真实契约文本常含 `open|done|expired|all`) 必须逐字节保留,
    否则等于偷偷改了题面夹具 (同输入条件被破坏)。
    """
    s = re.sub(r"\s*\r?\n\s*", " ", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="起臂前自检: 只对**盘上**计划/范围跑契约机检 (防 R517 事故: 生成后被人手改坏)")
    ap.add_argument("--plan-out", default=os.path.join(OUT, "plan-p3p4-r518.txt"))
    ap.add_argument("--scope-out", default=os.path.join(OUT, "scope-p3p4-r518.txt"))
    a = ap.parse_args()

    if a.check:
        for p in (a.plan_out, a.scope_out):
            if not os.path.isfile(p):
                print("[致命] 缺盘上契约文件 %s" % p)
                return 3
        chk = subprocess.run([sys.executable, os.path.join(OUT, "check_plan_contract.py"),
                              "--plan", a.plan_out, "--scope", a.scope_out, "--full-coverage"],
                             capture_output=True, text=True)
        sys.stdout.write(chk.stdout)
        sys.stderr.write(chk.stderr)
        if chk.returncode != 0:
            print("[致命] 盘上契约机检未过 rc=%d ⇒ 禁起臂" % chk.returncode)
            return 1
        print("PLAN_ON_DISK_CONTRACT_OK")
        return 0

    with io.open(TASKSET, encoding="utf-8") as fh:
        ts = json.load(fh)
    prompts = {t["tid"]: t["prompt"] for t in ts["tasks"]}
    rules = {tid: split_rules(p) for tid, p in prompts.items()}

    plan, scope = [], []
    for tid in ("p4", "p3"):
        for nid, deps, files, title, nums, pkg in SEGMENTS[tid]:
            missing = [n for n in nums if n not in rules[tid]]
            if missing:
                print("[致命] %s 规则切分缺编号 %s (禁手抄, 必须机械切出)" % (tid, missing))
                return 3
            body = " ".join(rules[tid][n] for n in nums)
            text = ("%s: %s。只写本段声明的文件, 禁越界实现其他段。本段职责 = %s。整包规格 (只读): %s"
                    % (title, files.replace(", ", " + "), body, prompts[tid]))
            # 夹具保真闸: 节点文本必须以**题面原文**结尾 (只许压空白, 禁改写字符)
            if not flat(text).endswith(flat(prompts[tid])):
                print("[致命] %s 节点文本未逐字包含题面原文 (夹具被改写) ⇒ 停手" % nid)
                return 3
            plan.append("%s | %s | remote | | %s" % (nid, ",".join(deps), flat(text)))
            scope.append("%s | %s" % (nid, files))
    for nid, deps, f, title in LOCAL_NODES:
        plan.append("%s | %s | local | python.selftest | %s" % (nid, ",".join(deps), f))

    plan_txt = "# R518 规模面双包计划 (7 节点) | 远端 5 + 本地 2 | 生成器: eval/rover/r518/gen_plan_r518.py\n" \
               + "\n".join(plan) + "\n"
    scope_txt = "# R518 兼容 R515 范围 DSL: 每节点一行 (远端节点必声明; 本地节点不产文件⇒禁声明)\n" \
                + "\n".join(scope) + "\n"

    # ── 生成即机检 (fail-closed: 全绿才落盘) ──────────────────────────────
    tmpd = tempfile.mkdtemp(prefix="r518gen-")
    pt, st = os.path.join(tmpd, "plan.txt"), os.path.join(tmpd, "scope.txt")
    io.open(pt, "w", encoding="utf-8").write(plan_txt)
    io.open(st, "w", encoding="utf-8").write(scope_txt)
    chk = subprocess.run([sys.executable, os.path.join(OUT, "check_plan_contract.py"),
                          "--plan", pt, "--scope", st, "--full-coverage"],
                         capture_output=True, text=True)
    sys.stdout.write(chk.stdout)
    sys.stderr.write(chk.stderr)
    if chk.returncode != 0:
        print("[致命] 契约机检未过 rc=%d ⇒ 不落盘 (fail-closed)" % chk.returncode)
        return 1

    if a.write:
        for src, dst in ((pt, a.plan_out), (st, a.scope_out)):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)   # 原子落盘 (不留半成品)
        print("WROTE %s (%d 节点)" % (a.plan_out, len(plan)))
        print("WROTE %s (%d 行)" % (a.scope_out, len(scope)))
        # 落盘后立刻回读机检 (防「生成器写盘与内存不一致」)
        re_chk = subprocess.run([sys.executable, os.path.join(OUT, "check_plan_contract.py"),
                                 "--plan", a.plan_out, "--scope", a.scope_out,
                                 "--full-coverage"],
                                capture_output=True, text=True)
        sys.stdout.write(re_chk.stdout)
        if re_chk.returncode != 0:
            print("[致命] 落盘后回读机检未过 rc=%d" % re_chk.returncode)
            return 1
        print("READBACK_CONTRACT_OK")
    else:
        print("DRY_RUN (加 --write 才落盘)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
