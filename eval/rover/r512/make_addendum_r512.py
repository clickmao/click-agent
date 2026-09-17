#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R512 预注册**增补**(addendum): 主 prereg 起臂后新增 B 臂(预算 12) —— 必须在 B 臂开跑**之前**落盘。

动机(留痕, 免问询令): 主 prereg 的验收面 = A(出厂默认预算 6) vs C(codex 真值)。R511 已观测到
默认预算在项目级题上质量不稳(0/12 ~ 11/12 摆), 若 A 质量不达则「token ↓≥30%」只能标「参考(未可验收)」,
无法回答用户 KPI 的核心问题: **在质量平价点上, 本侧是否仍省 30% 以上**。
故增补单一变量臂 B = 同环境/同输入/同模型, 仅 **步数预算 12**(R511 候选 1 的最小可判子集, 而非全网格 24 跑次)。

纪律(硬):
 - 本文件在 B 臂开跑前写入, 逐条阈值继承主 prereg, **不得**因看到 B 的读数再改阈值。
 - B 是**增补**, 不替换 A: 报告必须同时给出 A 与 B, 主验收面仍为 A; 若 B 达标而 A 不达标,
   结论只能写「默认预算质量不达 ⇒ 主验收未过; 12 步预算为增补平价点」, 禁用 B 冒名宣称验收通过。
"""
from __future__ import annotations
import hashlib, io, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
INSTR = {
    "agent_side_runner": "eval/rover/r511/proj_run_side.py",
    "aggregate": "eval/rover/r512/aggregate_r512.py",
    "freeze": "eval/rover/r512/freeze_snapshot_r512.py",
    "criteria_checker": "eval/rover/r512/check_criteria_r512.py",
    "taskset": "eval/rover/r512/taskset-r512.json",
    "main_prereg": "eval/rover/r512/prereg-r512.json",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap_out = os.path.join(HERE, "prereg-r512-addendum.json")
    if len(sys.argv) > 1 and sys.argv[1] != "--write":
        print("用法: make_addendum_r512.py [--write]"); return 2
    write = len(sys.argv) > 1
    main_pre = json.load(io.open(os.path.join(HERE, "prereg-r512.json"), encoding="utf-8-sig"))
    d = {
        "round": "R512", "kind": "prereg_addendum",
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "super": "prereg-r512.json",
        "super_criteria": sorted(main_pre["criteria"].keys()),
        "new_arms": [
            {"run": "B-r1", "side": "agent", "max_steps": 12, "window": "w1", "pairs_with": "C-r1"},
            {"run": "B-r2", "side": "agent", "max_steps": 12, "window": "w2", "pairs_with": "C-r2"},
        ],
        "state_at_write": {
            "A-r1": "done", "A-r2": "done", "C-r1": "in_flight", "C-r2": "not_started",
            "B-r1": "中止尝试已弃用(见 aborted_prior_attempts); 保留跑次尚未开跑",
            "B-r2": "中止尝试已弃用(见 aborted_prior_attempts); 保留跑次尚未开跑",
        },
        "aborted_prior_attempts": {
            "note": "本文件写入时刻 = 10:03:44; 其前已有 B 臂**中止尝试**(10:02:35 起), 因两臂并发交叠导致 adapter 落盘索引交织(读数不可归因) ⇒ 全部弃用并从读数排除; 保留下来的 B-r1/B-r2 = 本文件写入之后串行重跑",
            "b_r1_0": "10:02:35 起, ~10:02:50 被误杀 (rc=143), 弃用",
            "b_r2_1": "10:02:50 起, 10:04:11 完成但与 b_r1_2 交叠, 弃用",
            "b_r1_2": "10:03:45 起, 10:04:15 主动中止 (rc=143), 弃用",
            "excluded_agent_dump_indices": "29..57 (不属于任何保留跑次的 adapter_range)",
            "log": "run_dir/logs/aborted-b-attempts.json",
        },
        "motivation": "主验收面 A=出厂默认预算 6; 质量不达则 token 降幅只能标参考 ⇒ 增补预算维度的平价对照点(单变量: 仅步数预算)",
        "criteria": {k: v for k, v in main_pre["criteria"].items()
                     if k in ("C2_quality_not_lower", "C3_token_down", "C4_remote_calls_down")},
        "scope_note": "B 臂在主 prereg 的 evidence_scope 之外(不受 require 约束); 报告须单列, 禁以 B 替换 A 宣称验收",
        "instruments": {k: {"path": v, "sha256": sha(os.path.join(REPO, v))} for k, v in INSTR.items()},
    }
    txt = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    if write:
        with io.open(ap_out, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        print("WROTE " + ap_out)
    print("新增臂: %s" % json.dumps(d["new_arms"], ensure_ascii=False))
    print("写入时刻: %s (B 臂未开跑 = 预注册成立)" % d["written_at"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
