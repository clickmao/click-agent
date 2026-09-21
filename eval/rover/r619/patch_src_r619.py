#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R619 产品侧最小改动（M3 第三刀 = 空执行面回退）—— **幂等**、字节级、转义形式由文件自身派生。

纪律（承 skill「写入通道会改写手打字面量」）:
  · 一切替换串**由目标行自身派生**（行内 token），不手打含引号/反斜杠的字面量；
  · 脚本幂等（重跑不重复插入）；
  · 改后由调用方 read 回核对 + 编译验证。
"""
import io
import os
import re
import sys

SRC = "src/agent/r1/R1Pipeline.cs"
TRANS = "src/agent/r1/R1Transcript.cs"


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def patch_pipeline():
    s = read(SRC)
    orig = s
    changed = []

    # --- ① 接线块：新增回退变量 + 回退分支 -------------------------------------
    old_head = ('            var execSource = "plan";\n'
                '            var acUnmapped = 0;\n'
                '            var acExpect = 0;\n'
                '            var execPlan = sem.Plan;\n'
                '            if (ActionExecPlan.IsEnabled())\n'
                '            {\n'
                '                var map = ActionExecPlan.Build(ac.AcceptedActions, sem.Plan);\n'
                '                execSource = "candidates";\n'
                '                acUnmapped = map.Unmapped;\n'
                '                acExpect = map.ExpectInherited;\n'
                '                execPlan = map.Steps;\n'
                '            }\n')
    new_head = ('            var execSource = "plan";\n'
                '            var execFallback = "";\n'
                '            var acUnmapped = 0;\n'
                '            var acExpect = 0;\n'
                '            var execPlan = sem.Plan;\n'
                '            if (ActionExecPlan.IsEnabled())\n'
                '            {\n'
                '                var map = ActionExecPlan.Build(ac.AcceptedActions, sem.Plan);\n'
                '                execSource = "candidates";\n'
                '                acUnmapped = map.Unmapped;\n'
                '                acExpect = map.ExpectInherited;\n'
                '                execPlan = map.Steps;\n'
                '                // R619 (RF0004.2 · M3 第三刀): **空执行面回退** —— 采纳面映射出的执行面为空\n'
                '                //   而 `plan` 非空 ⇒ 执行面退回 `plan`（不是「什么都不做」）。\n'
                '                //   动因 = R618 D1 形态实测（`w210/agentT-r1`: 候选键未到达 ⇒ 采纳面为空 ⇒\n'
                '                //   零步执行，而同题对照档会跑 plan 的 10 步）⇒ 换载体不得把「有活可干」\n'
                '                //   变成「什么都没跑」。触发面 = 复用**既有**空面条件（非新增预言分支）。\n'
                '                if (execPlan.Count == 0 && sem.Plan.Count > 0)\n'
                '                {\n'
                '                    execSource = "plan_fallback";\n'
                '                    execFallback = !ac.Present\n'
                '                        ? "candidates_absent"\n'
                '                        : (ac.Accepted == 0 ? "accepted_empty" : "unmapped_all");\n'
                '                    acUnmapped = 0;\n'
                '                    acExpect = 0;\n'
                '                    execPlan = sem.Plan;\n'
                '                }\n'
                '            }\n')
    if old_head in s:
        s = s.replace(old_head, new_head, 1)
        changed.append("pipeline.head")
    elif new_head in s:
        pass
    else:
        raise SystemExit("[致命] 接线块锚点未命中（现盘形态已变）")

    # --- ② 空面文案三态 --------------------------------------------------------
    old_note = ('                var emptyNote = execSource == "plan"\n'
                '                    ? " (plan 空 ⇒ 不执行)"\n'
                '                    : " (采纳候选可执行面为空 ⇒ 不执行)";\n')
    new_note = ('                // R619: 三态文案（plan / candidates / plan_fallback）—— 两臂之外新增回退档，\n'
                '                //   三态互异 ⇒ 「执行面为空」的三种成因在回执文本上可区分（机检用台账字段，不靠文本）。\n'
                '                var emptyNote = execSource == "plan"\n'
                '                    ? " (plan 空 ⇒ 不执行)"\n'
                '                    : (execSource == "candidates"\n'
                '                        ? " (采纳候选可执行面为空 ⇒ 不执行)"\n'
                '                        : " (回退 plan 后执行面仍空 ⇒ 不执行)");\n')
    if old_note in s:
        s = s.replace(old_note, new_note, 1)
        changed.append("pipeline.emptyNote")
    elif new_note in s:
        pass
    else:
        raise SystemExit("[致命] 空面文案锚点未命中")

    # --- ③ 六处 R1RunResult 构造点补 ExecFallback（替换串 = 既有行内 token） -----
    tok_old = "ExecSource: execSource,"
    tok_new = "ExecSource: execSource, ExecFallback: execFallback,"
    n = s.count(tok_old)
    if n:
        s = s.replace(tok_old, tok_new)
        changed.append("pipeline.result_sites=%d" % n)

    if s != orig:
        write(SRC, s)
    print("[R1Pipeline] changed=%s sites6=%d" % (changed, s.count(tok_new)))


def patch_transcript():
    """在两处发射块里插入 exec_fallback —— 新行**由既有行派生**（字段名替换 + 值表达式替换），
    从而沿用文件自身的转义形式（不手打反斜杠/引号字面量）。"""
    lines = io.open(TRANS, encoding="utf-8").read().split("\n")
    out = []
    inserted = 0
    for ln in lines:
        out.append(ln)
        if "action_candidates_expect_inherited" not in ln:
            continue
        if "exec_fallback" in ln:
            continue
        indent = ln[:len(ln) - len(ln.lstrip())]
        derived = ln.replace("action_candidates_expect_inherited", "exec_fallback") \
                    .replace("r.ActionCandidatesExpectInherited", "r.ExecFallback") \
                    .replace("R1Json.Num", "R1Json.Quote")
        out.append(indent + "// R619 (M3 第三刀): 回退原因码 —— 只在回退发生时落（未回退 ⇒ 字段不出现 ⇒"
                   " 与 R618 逐字节同）。")
        out.append(indent + "if (!string.IsNullOrEmpty(r.ExecFallback))")
        out.append(indent + "{")
        out.append(indent + "    " + derived.strip())
        out.append(indent + "}")
        inserted += 1
    if inserted:
        write(TRANS, "\n".join(out))
    print("[R1Transcript] inserted_blocks=%d (expect 2)" % inserted)


if __name__ == "__main__":
    patch_pipeline()
    patch_transcript()
