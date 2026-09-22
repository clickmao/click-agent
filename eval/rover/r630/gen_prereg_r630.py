#!/usr/bin/env python3
"""R630 · 预注册生成（**先写后跑**：本件必须在任何真机臂之前落盘）。

单变量轴 = 既有 env `AGENTFRAMEWORK_R1_ACTION_PROMPT` 的**第四取值** `spec`
（T 档 = 缺省块 + 规格保真自检尾块；C 档 = unset = 产品缺省 = R617 现盘块逐位）。
判据阈值**引 baselines id**（RF0004 §4.1 引用义务）。
用法: python3 eval/rover/r630/gen_prereg_r630.py
"""
import io
import json
import os
import time

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r630/prereg-r630.json")

WIN0, NWIN = 211, 2

d = {
    "round": "R630",
    "written_before_run": True,
    "written_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "author": "cron capability-cycle (R630)",
    "protocol": "docs/plans/RF0005-completion-protocol.md §2 固定环 0–9 / §1 迭代单元七硬约束",
    "claim": (
        "R629 的 `wythoff` 族逐例归因把承重缺口定到「写产物前不做**规格保真自检**」"
        "（题面写明的那部分契约未逐条对照，产物只满足自述的 expect_stdout）。"
        "本轮把该缺口落成**恒前缀尾部追加块**（RF0004 §131 尾部载体原则）："
        "只加厚、默认块逐字节不变 ⇒ 轴关 = 旧行为逐位；轴开 = 同一二进制多一条自检纪律。"
    ),
    "single_variable": {
        "axis": "AGENTFRAMEWORK_R1_ACTION_PROMPT",
        "T": "spec ⇒ 生效前缀 = 缺省块正文 + <spec_fidelity> 尾块（16182 字符）",
        "C": "unset ⇒ 产品缺省（缺省块 15796 字符，**逐字节等于 R617 现盘 pin**）",
        "C1": "codex-cli 外部真值（同题面/同夹具；本轮为**跨窗并列**引用 baselines，不与本窗同跑）",
        "why_only_one": (
            "同一 AOT 二进制（sha 唯一）、同题面逐字节、同夹具、仅该 env 一个取值差异；"
            "前缀四条不变量（只加厚/四档互异/缺省块字节未变/闭合标签保留）已由 "
            "eval/rover/r630/gen_prefix_r630.py rc=0 机检。"
        ),
        "third_anchor": "沿用 r615 / legacy 两锚（本轴历史档可复现），本轮不用（未测即未测）。",
        "arm_convention_note": "轴门禁 fail-closed 生效于 R1Pipeline（EffectiveChars/EffectiveSha256Pinned 双档判定 ⇒ 无 rc=6 prefix_drift，AOT 双档冒烟已证）。",
    },
    "windows": {
        "set": ["w%d" % (WIN0 + i) for i in range(NWIN)],
        "disjoint_from_history": True,
        "history_up_to": "w210（R618 用 w208..w210；本轮起 w211，与历史窗集不相交）",
    },
    "criterion_version": "v3",
    "thresholds_cite_baselines": [
        "F_env.prefix.chars",
        "F_env.prefix.sha256",
        "F_env.prefix.r615_anchor",
        "F_merge.quality.cases_median_truth",
        "F_merge.cost.new_prompt_sum",
        "F_merge.cache.hit_v_all",
    ],
    "criteria": {
        "J0_arm_axis_effective": (
            "fail-closed 器具闸：T 档逐跑次 transcript `prefix_chars==16182` ∧ `prefix_sha256`==spec 档 sha；"
            "C 档逐跑次 ==15796 ∧ ==缺省 pin sha；两档**可区分**（不出现 T==C）。不成立 ⇒ 整轮 VOID（rc=2）。"
        ),
        "J1_mechanism_face": "T 档证据面出现新轴生效读数（prefix_chars 落 spec 档）跑次数 >= 1；C 档该读数恒缺省档。",
        "J2_quality_face": (
            "逐窗 T vs C 的用例通过数（同冻结题集 g1 隐藏用例）；判据 = T 不劣于 C（逐窗中位差 >= 0）"
            "且 T 的整题全对率不下降。外部真值列 = baselines id F_merge.quality.cases_median_truth（跨窗并列，标『参考』）。"
        ),
        "J3_cost_face": "逐臂分列（调用数 / 新算 prompt / completion）；判据 = T 的 completion 不得显著膨胀（> 1.5× C 中位 ⇒ 记膨胀）。",
        "J4_zero_regression": "C 档 transcript 前缀读数 == 缺省 pin（逐位）⇒ 轴关 = 旧行为；不成立 ⇒ 撤回未提交 src 改动（净产品改动 0）。",
    },
    "falsification": [
        "① J0 未过（T 档无 spec 档前缀读数）⇒ 机制面 PASS=0 ⇒ 撤回未提交 src/ 改动（净产品改动 0），只记失败与重开条件。",
        "② J2 未过（T 劣于 C 且逐窗同向）⇒ 尾块措辞证伪，v2 须**阈值不变**重注册并披露失败项。",
        "③ 有效窗 < 2（真值/臂自败窗剔除后）⇒ rc=3 停链先造窗，**禁下调阈值**。",
        "④ 摆动 >= 效应 ⇒ 该轴非承重变量、定案关闭（禁调阈值）。",
        "⑤ 任一跑次出现 `prefix_drift`(rc=6) ⇒ 轴门禁与钉值不同源 ⇒ rc=2 器具缺陷，禁改判据凑绿。",
    ],
    "evidence_scope": {
        "require": [
            "eval/rover/r630/prereg-r630.json",
            "eval/rover/r630/prefix-r630.json",
            "eval/rover/r630/aot_r630.sh",
            "eval/rover/r630/run_r630.sh",
            "eval/rover/r630/judge-r630.json",
            "eval/rover/r630/verdict-r630.json",
            "eval/rover/r630/report-r630.md",
        ],
        "foreign_forbidden": "codex 真值列只作**外部真值并列**；本窗未同跑 ⇒ 禁作 J2 主判据。",
    },
    "supersedes": "无（R617/R618 读数并列在档，不相减）",
    "revision": {"v1": "起臂前定稿，无修订。"},
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(d, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("WROTE %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
print("windows", d["windows"]["set"], "baselines", len(d["thresholds_cite_baselines"]), "require", len(d["evidence_scope"]["require"]))
