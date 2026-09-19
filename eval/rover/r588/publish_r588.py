#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R588 文档回填: 主线状态块「最近一轮」刷新 + 手册 §7 追加 R588 块与 R589 候选（幂等）。"""
from __future__ import annotations

import io
import json
import os
import re

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r588")
D = os.path.expanduser("~/.agentframework/harness/runs/r588")
STATUS = os.path.join(REPO, "docs/reports/dynamic-telemetry-eval-rollback-strategy.md")
PLAN = os.path.join(REPO, "docs/reports/iteration-master-plan.md")


def rd(p):
    return json.load(io.open(p, encoding="utf-8"))


def main():
    v = rd(os.path.join(PD, "verdict-r588.json"))
    t = rd(os.path.join(PD, "kpi-table-r588.json"))
    pre = rd(os.path.join(D, "precond-r588.json"))
    c2 = rd(os.path.join(PD, "timeout-cause-r588.json"))
    c3 = rd(os.path.join(PD, "noartifact-cause-r588.json"))
    c4 = rd(os.path.join(PD, "subspec-v2-r588.json"))
    arms = t["readings"]
    c1 = {r["win"]: r["cases_pass"] for r in arms if r["arm"] == "C1"}
    dp = [r["cases_pass"] for r in arms if r["arm"] == "R588D"]
    dw = {r["win"]: r["cases_pass"] for r in arms if r["arm"] == "R588D"}
    defs, pooled = v["C1_quality_paired"], v["C5b_swing_vs_effect"]
    a_c1 = v["arms"]["C1"]; a_p = v["arms"]["R588D"]
    c2h = c2["class_histogram"]
    line = ("> - **最近一轮（R588，2026-09-20 · cron 60min tick）**: **主线同件扩窗轮（第四窗集 `w163..w165`；"
            "同被测件 + 同冻结题集、只换窗集）＋ R587 五项候选并轮收口 = 外部真值 codex × 产品默认档（三枚剂量键显式 unset），"
            "3 窗、每窗 真值×1 ＋ 产品×3** —— 题集 sha `e0c667c2…`、二进制 sha `4b70fd7c…`（`bin_sha_stable=true`）；"
            "**质量（58 例）**：真值逐窗 `%s`（`%s` 真值自身失分 %s/58 ⇒ `unreliable` 剔除配对并单列）、产品逐窗中位 `%s`"
            "（逐跑次 `%s`）；**有效窗 %d、配对差 %s、中位 %s < 下限 %s ⇒ rc=1 FAIL（质量配对未过）**；"
            "**C5 = 「缺口跨窗复现」**（与 R587 D 集 `[0,−13]` 同号 ∧ 区间重叠；并列不相减）；"
            "**九窗并列池化（摆动/效应分离）**：有效窗 %d、D 中位 **%s**、极差 **%s**、符号 %s（neg/pos/zero）、双侧精确二项 **p=%s** ⇒ 按预注册 C5b 规则判 **「摆动 ≥ 效应 ⇒ 该轴非承重变量、定案关闭」**（符号面稳定但量级面摆动仍 ≥ 效应 ⇒ **单窗不作能力结论**）；"
            "C6 步数 9/9 PASS（`%s`）；**铁律 11 前置器 rc=1**（`executable_and_correct=false` / `acceptable_scoped=false`；未过臂窗 %d 个，含真值 `w165/codex 53/58` ⇒ 降幅读数一律标「参考（未可验收）」）。"
            "**候选①（第四窗集）**：有效窗 7→**9**，摆动 %s vs 效应 %s ⇒ 未分离。"
            "**候选②（`TIMEOUT` 定因）**：`w155-r2` 8 例在冻结快照物化副本上按产品同款调用协议复跑 → `%s`（T=10s 三连达上限 ∧ T=60s 仍达上限 ⇒ **不收敛**，非「慢」；4 例对照秒级 3 次同形；冻结树读前读后 sha 同值）。"
            "**候选③（臂级未交付产物定因）**：27 产品跑次分类 `%s`，`NO_ARTIFACT` **单例** = `r587/w162/agentD-r3`；定因 = **契约块结构不闭合**（字符串感知括号扫描无法归零）⇒ 严格解析在读至 **byte 6455** 的 `{` 处落「期望属性名」，与产品自报 `BytePositionInLine: 6455` **逐字节对齐（delta=0）** ⇒ `stage=contract`/`rc=4`（谓词落点 `src/agent/r1/R1Pipeline.cs:147`）⇒ `steps=0` ⇒ 工作区零文件；两侧成对控制 `has_teeth=true`（正控 rc=0 块解析 OK；负控删一个 `}` ⇒ FAIL）。"
            "**候选④（`PHI_DIFF` 边界处理加厚）**：轴 A v1 标记集**恒等复刻通过**（在 r585–r587 原语料上逐标签复现 R587 已登记直方图）；轴 B 二阶段子类把 `UNCLASSIFIED` %d→**%d**，**但对照组判别力 gap=%s**（v1-已分类组命中率 %s vs 未分类组 %s）⇒ 只作**描述性登记**、不改判据、不宣称能力。"
            "**候选⑤（分母口径）**：判据面定稿 `eval/rover/r588/noartifact-denominator-spec-r588.md` —— `NO_ARTIFACT` 的 `0/58` **计入配对**（剔除即抬高我方读数）＋ 同窗记 `denominator_class` 并**单列点名**（1/27=%.1f%%）；`unreliable` **只保留给真值自身失分窗**，两者不得混用；**不动前置器语义**（避免器具身份漂移）。"
            "**成本三列（标「参考（未可验收）」）**：调用 %s vs %s / 新算 prompt %s vs %s / completion %s vs %s（按跑次归一 %s vs %s / %s vs %s / %s vs %s；两侧 9 vs 3 ⇒ 禁比总量）/ 命中率 v_all %s vs %s、v_incr %s vs %s（**真值臂本轮 66 调用 vs R587 17**：codex 侧长命令 `write_stdin` 120s yield 轮询（`side-codex-0xx.json` 逐调用落盘可见）⇒ 其成本与 `w165` 自身失分同窗，成本列只作**指示性**）。"
            "**自捕**：① 首跑 `noartifact_cause` 正控翻红（提取口径过贪：取到 reply 末尾 ⇒ rc=0 块读成 `Extra data`）⇒ 改**平衡括号切读**后 `has_teeth=true`，**首跑读数留档不翻案**；② R587 读数件 `missing_wythoff_py` 字段用 `c.get(...,'')` 判缺失而键仅在缺件时建立 ⇒ 36/36 全列（真缺仅 1）⇒ 口径修正为「键存在性」并在新器具内登记，**R587 读数只加注不翻案**。"
            "**诚实边界**：① 铁律 11 rc≠0 ⇒ 调用/token 降幅不得作验收依据；② 候选④ 子类与**结果面**交叉（per-tag `cases_pass` 均值差 max |gap|）已落盘，判别力≈0；③ 候选③ 的**字符级**病因未定因（残余入档）；④ 摆动 ≥ 效应 ⇒ 本轴定案关闭，**不再以加窗求效应**。"
            "轮志 `eval/rover/r588/report-r588.md`、预注册 `eval/rover/r588/prereg-r588.json`、台账 `eval/capability/kpi.jsonl`（R588）。") % (
        [c1[w] for w in sorted(c1)], v["C0_truth_reliability"]["unreliable"][0],
        [r.get("cases_pass") for r in arms if r["arm"] == "C1" and r["win"] == v["C0_truth_reliability"]["unreliable"][0]][0],
        [dw[w] for w in sorted(dw)], dp, len(defs["D_list"]),
        defs.get("D_per_window") or defs.get("D_map"), defs["D_median"], defs["median_floor"],
        pooled["pooled_n_valid_windows"], pooled["pooled_median_effect"], pooled["pooled_range_swing"],
        pooled["sign_count"], pooled["sign_test_p_two_sided"], v["C6_steps_face"]["steps"],
        len(pre["blocked"]), v["C5_gap_reproduction"]["prev_median"], pooled["pooled_median_effect"],
        c2["class_histogram"], c3["class_distribution"], c4["unclassified_before"],
        c4["unclassified_after_residual"], c4["discrimination"]["gap"],
        c4["discrimination"]["rate_tagged_on_v1_classified_control"],
        c4["discrimination"]["rate_tagged_on_v1_unclassified"],
        c3["denominator_policy_candidate5"]["share"] * 100,
        a_c1["calls"], a_p["calls"], a_c1["new_prompt"], a_p["new_prompt"],
        a_c1["completion"], a_p["completion"],
        round(a_c1["calls"] / 3, 2), round(a_p["calls"] / 9, 2),
        round(a_c1["new_prompt"] / 3), round(a_p["new_prompt"] / 9),
        round(a_c1["completion"] / 3), round(a_p["completion"] / 9),
        a_c1["v_all_med"], a_p["v_all_med"], a_c1["v_incr_med"], a_p["v_incr_med"])

    sl = io.open(STATUS, encoding="utf-8").read().split("\n")
    if any("最近一轮（R588" in x for x in sl):
        print("STATUS: R588 行已存在 ⇒ 跳过")
    else:
        i = next(k for k, x in enumerate(sl) if "最近一轮（R587，2026-09-20" in x)
        sl[i] = sl[i].replace("（R587，2026-09-20 · cron 60min tick）**:",
                              "（R587，2026-09-20 · cron 60min tick）【历史快照，已被上方 R588 行取代】**:")
        sl.insert(i, line)
        io.open(STATUS, "w", encoding="utf-8").write("\n".join(sl))
        print("STATUS: 已插入 R588 行 (行号 %d), R587 行转历史快照" % (i + 1))

    pb = ["",
          "- **R588（主线**同件扩窗轮 · 第四窗集** + R587 五项候选并轮收口：`w163..w165`；零产品源码改动 / 零新夹具语义 / 零新开关）**: "
          "**修改点** ① 驱动器 `run_r588.sh` 派生自 `run_r587.sh`（轮号/窗口段 160→163/端口 49571→49591/**起手闸摆动余量 130→65 = R587 实测振幅**（`min(65, cap=151)` 不夹））；"
          "② 判据器 `kpi_r588.py` 派生自 `kpi_r587.py`（C5 前序集指向 R587 + **C5b 四窗集池化段**：逐集并列 + 池化中位/极差 + 双侧精确二项 + 三态规则）；"
          "③ 候选② 器具 `timeout_cause_r588.py`；④ 候选③⑤ 器具 `noartifact_cause_r588.py` + 判据面 `noartifact-denominator-spec-r588.md`；"
          "⑤ 候选④ 器具 `subspec_v2_r588.py`（轴 A 恒等 + 轴 B 加厚 + 对照组判别力 + 结果面交叉）；⑥ 收口器 `finish_r588.py`（台账行原地替换 ⇒ 幂等 + 轮志生成）。"
          "**真机读数**（3 窗 `w163..w165`、每窗 真值×1 ＋ 产品默认档×3；题集 sha `e0c667c2…`、二进制 sha `4b70fd7c…`、`bin_sha_stable=true`）："
          "**质量（58 例）** 真值逐窗 `%s`（`%s` 自身失分 ⇒ `unreliable` 剔除并单列）vs 产品逐窗中位 `%s`（逐跑次 `%s`）。"
          "**判据裁定 rc=1 FAIL**：C1 有效窗 %d、配对差 %s、中位 **%s** < 下限 %s；C0 FAIL（`%s`）；C5 = **「缺口跨窗复现」**；C6 PASS（步数 9/9 `%s`）。"
          "**候选①(第四窗集)**：有效窗 7→**9**；池化 D 中位 **%s**、极差 **%s**、符号 %s、**p=%s** ⇒ 预注册 C5b 规则判 **「摆动 ≥ 效应 ⇒ 该轴非承重变量、定案关闭」**（符号面稳定、量级面未分离 ⇒ **不再加窗求效应**）。"
          "**候选②**：`TIMEOUT` 8 例（`w155-r2` 单跑次）三阶复跑 ⇒ `%s`（T=10s 3/3 达上限 ∧ T=60s 仍达上限 ⇒ **不收敛**，非「慢」；对照 4 例秒级、3 次同形；冻结快照读前读后 sha 同值）。"
          "**候选③**：27 产品跑次分类 `%s`；`NO_ARTIFACT` **单例** `r587/w162/agentD-r3` 定因 = **契约块结构不闭合** ⇒ 严格解析在读至 **byte 6455** 的 `{` 处落「期望属性名」，与产品自报 `BytePositionInLine: 6455` **逐字节对齐（delta=0）** ⇒ `stage=contract`/`rc=4`（`src/agent/r1/R1Pipeline.cs:147`）⇒ `steps=0` ⇒ 零文件；成对控制 `has_teeth=true`。"
          "**候选④**：轴 A **恒等复刻通过**；轴 B 把 `UNCLASSIFIED` %d→**%d**，但**对照组判别力 gap=%s**（%s vs %s）⇒ 只作描述性登记。"
          "**候选⑤**：`NO_ARTIFACT` 的 `0/58` **计入配对** + 同窗 `denominator_class` 单列点名（1/27=%.1f%%）；`unreliable` 只留给真值自身失分窗；**改判据面写法而不动前置器语义**。"
          "**C2 成本三列（一律标「参考（未可验收）」）**：调用 %s vs %s / 新算 prompt %s vs %s / completion %s vs %s（按跑次归一 %s vs %s / %s vs %s / %s vs %s；9 vs 3 ⇒ 禁比总量）/ 命中率 v_all %s vs %s、v_incr %s vs %s。"
          "**自捕 2 件（均未放宽判据）**：① 首跑 `noartifact_cause` 正控翻红（提取口径过贪 ⇒ rc=0 块读成 `Extra data`）⇒ 改平衡括号切读，首跑留档不翻案；② R587 `missing_wythoff_py` 口径（键存在性 ≠ 值缺失）⇒ 修正并登记。"
          "**诚实边界**：① 铁律 11 rc≠0 ⇒ 成本列不得作验收依据；② 候选④ 与结果面交叉 max|gap| 已入档；③ 候选③ 字符级病因未定因（残余）；④ 本轴定案关闭，不再加窗。"
          "轮志 `eval/rover/r588/report-r588.md`、预注册/DAG：`eval/rover/r588/{prereg-r588.json,dag-r588.md}`、台账 `eval/capability/kpi.jsonl`（R588）。" % (
              [c1[w] for w in sorted(c1)], v["C0_truth_reliability"]["unreliable"][0],
              [dw[w] for w in sorted(dw)], dp, len(defs["D_list"]),
              defs.get("D_per_window") or defs.get("D_map"), defs["D_median"], defs["median_floor"],
              v["C0_truth_reliability"]["unreliable"][0], v["C6_steps_face"]["steps"],
              pooled["pooled_median_effect"], pooled["pooled_range_swing"], pooled["sign_count"],
              pooled["sign_test_p_two_sided"], c2["class_histogram"], c3["class_distribution"],
              c4["unclassified_before"], c4["unclassified_after_residual"], c4["discrimination"]["gap"],
              c4["discrimination"]["rate_tagged_on_v1_classified_control"],
              c4["discrimination"]["rate_tagged_on_v1_unclassified"],
              c3["denominator_policy_candidate5"]["share"] * 100,
              a_c1["calls"], a_p["calls"], a_c1["new_prompt"], a_p["new_prompt"],
              a_c1["completion"], a_p["completion"],
              round(a_c1["calls"] / 3, 2), round(a_p["calls"] / 9, 2),
              round(a_c1["new_prompt"] / 3), round(a_p["new_prompt"] / 9),
              round(a_c1["completion"] / 3), round(a_p["completion"] / 9),
              a_c1["v_all_med"], a_p["v_all_med"], a_c1["v_incr_med"], a_p["v_incr_med"]),
          "",
          "- **下轮候选 (R589)**: ① **本轴（产品 vs 外部真值质量缺口）定案关闭的处置裁定**（预注册规则已触发「摆动 ≥ 效应」；三种续法会产出不同交付物: (a) 换判据面=**整题全对率/按族分列**后同件复跑 (b) 停止加窗、直进产品侧修复（须用户放行产品改动）(c) 换更长的真任务题面（同件不可比 ⇒ 新基线））—— **须用户裁定**；"
          "② 候选③ **字符级**最小化复现（把契约块按元素二分定位首个使解析器偏离的元素；若归因到模型侧转义，A 类占比给出「加厚哪一段 prompt」的收益上界）；"
          "③ 真值臂成本异常定因（本轮 66 调用 vs R587 17；用 adapter per-call dump 时间轴 + `finish_reason` 分布，判「长命令 yield 轮询」占比；只读）；"
          "④ 「自报期待 vs 外部用例」脱钩量化（`w164-r2` 拿到 58/58 却 `rc=5`；统计 27 跑次里 `rc≠0 ∧ cases_pass=58` 的占比，只读）；"
          "⑤ 候选④ 子类的**结果面判别力**：per-tag `cases_pass` gap 已落盘（max |gap| 见 `subspec-v2-r588.json`），若 ≈0 则该分类轴整体降为描述项。"]
    lb = io.open(PLAN, encoding="utf-8").read().split("\n")
    if any("R588（主线**同件扩窗轮 · 第四窗集" in x for x in lb):
        print("PLAN: R588 块已存在 ⇒ 跳过")
    else:
        # 追加到文件末尾（§7 末尾 = 下轮候选 R588 行之后）
        while lb and not lb[-1].strip():
            lb.pop()
        lb += pb
        io.open(PLAN, "w", encoding="utf-8").write("\n".join(lb) + "\n")
        print("PLAN: 已追加 R588 块 + R589 候选 (%d 行) ⇒ 总 %d 行" % (len(pb), len(lb)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
