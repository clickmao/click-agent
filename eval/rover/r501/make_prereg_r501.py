#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R501 预注册机生成 (先于首跑; 哈希一律机取, 禁手抄)。

R501 = **唯一一次 src 改动** (`src/agent/IndustrialAgentV2.cs:1636`, 改写族豁免) + 同形四臂复测。
继承面: 臂矩阵形状/网格/判据器与 R499 **逐字节相同** ⇒ 唯一变量 = 二进制字节。
"""
import hashlib
import io
import json
import os
import subprocess
import sys

ROOT = "/home/agentuser/AgentFramework"
DST = os.path.join(ROOT, "eval/rover/r501/prereg_r501.json")
BIN = "/tmp/pub_r501/agenthost"


def sha16(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:16]


def sha12(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:12]


def src_change_pin():
    """机取本轮改动行范围 (唯一改动入口 = 表达式豁免)"""
    diff = subprocess.run(["git", "diff", "-U0", "--", "src/agent/IndustrialAgentV2.cs"],
                          cwd=ROOT, capture_output=True, text=True).stdout
    added = [l for l in diff.split("\n") if l.startswith("+") and not l.startswith("+++")]
    removed = [l for l in diff.split("\n") if l.startswith("-") and not l.startswith("---")]
    return {"added_lines": len(added), "removed_lines": len(removed),
            "diff_sha12": sha12(diff), "added_text_sha12": sha12("\n".join(added))}


prereg = {
    "round": "R501",
    "title": "改写族豁免 (R444 后置否决不再吞改写吸收) —— 同形四臂复测",
    "prereg_time_local": subprocess.run(["date", "+%F %T %z"], capture_output=True, text=True).stdout.strip(),
    "source_of_candidate": "R500 真机根因 (eval/rover/r500/rootcause_check_r500.py, K1-K5 全过): "
                           "吸收支生效 (r1_raw_len==21==len('mechanical:paraphrase')) 后被 1636 支否决",
    "src_change": src_change_pin(),
    "inherited_from_r499": {
        "arms": "C(改写关,1 跑) + P1,P2,P3(改写开,n=3)",
        "grid_sha16": sha16(os.path.join(ROOT, "eval/rover/r501/grid/task-p17-code.json")),
        "runner_sha16": sha16(os.path.join(ROOT, "eval/rover/r501/run_arm_real_r501.sh")),
        "judge_sha16": sha16(os.path.join(ROOT, "eval/rover/r499/judge_paraphrase_r499.py")),
        "note": "判据器逐字节继承 r499 名与字节 ⇒ 跨轮读数不被判据改版污染",
    },
    "binary": {"path": BIN, "sha16": sha16(BIN), "il_warn": 0},
    "gate_policy": {"min_mem_available_mb": 2650, "consecutive_pass": 2,
                    "rationale": "R499 实测单采样不可信 (2208↔2654 穿越, 6 采 1 过)"},
    "hypotheses": {
        "H1p": "P 臂 t8 basis **含 paraphrase** (∈ mechanical:paraphrase / gate:paraphrase_no_replayable_prev / "
               "gate:paraphrase_guard_rejected) 且**不再是** gate:skip_rejected_nonack —— 期望 3/3",
        "H1n": "P 臂 local_turn_gate_reject == 0 且 gate_prefilter_invariant_violation == 0 —— 期望 3/3",
        "H2": "C 臂 t8 basis == mechanical:nonack→remote 且 reject/violation == 0 (闸关时逐位不变的正控)",
        "H3": "t8 的远端调用: basis==mechanical:paraphrase ⇒ 0 次 (本地生成); degrade 支 ⇒ 1 次且必带 reason。"
              "**只有前者可宣称本地生成**",
        "H4": "P 臂 t8 答复非空 ∧ 非上一条逐字复读 (J2b); 每个 paraphrase_degrade_remote 必带 reason",
    },
    "falsified_if": "H1p 3/3 均不成立 ⇒ 本轮回滚判定, 记 NOT_RUN, **不得宣称任何改写收益**",
    "honest_bounds": [
        "n=3 为重复跑, 非独立样本; 跨轮禁相减 (R500 的 C 仅作方向对照)",
        "节省口径不变 (中继 usage 真值); 本轮回读数**不**用于宣称 ≥30% 主线达标",
        "改写通道只覆盖「同义改写族」单轮, 覆盖率贡献须单列",
    ],
    "artifacts": ["run_arm_real_r501.sh", "grid/task-p17-code.json", "prereg_r501.json",
                  "run_matrix_r501.sh", "publish_and_il_check_r501.sh", "build_r501_harness.py",
                  "test_all_r501.sh"],
}

if not os.path.isfile(BIN):
    print("[致命] 二进制不存在 ⇒ 未发布就写预注册 = 违规: " + BIN)
    sys.exit(2)
io.open(DST, "w", encoding="utf-8", newline="\n").write(json.dumps(prereg, ensure_ascii=False, indent=1) + "\n")
print("[ok] 预注册落盘 %s (%d 字节); binary_sha16=%s; grid_sha16=%s; judge_sha16=%s"
      % (DST, os.path.getsize(DST), prereg["binary"]["sha16"],
         prereg["inherited_from_r499"]["grid_sha16"], prereg["inherited_from_r499"]["judge_sha16"]))
