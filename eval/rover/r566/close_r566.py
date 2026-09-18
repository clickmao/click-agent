#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R566 收口写入: 前置器件 + kpi.jsonl 行 (幂等) + 最新状态块 + 计划尾部候选。全部读回校验。"""
import io, json, os, shutil, sys

REPO = "/home/agentuser/AgentFramework"
PDIR = os.path.join(REPO, "eval/rover/r566")
KPI = os.path.join(REPO, "eval/capability/kpi.jsonl")
DT = os.path.join(REPO, "docs/reports/dynamic-telemetry-eval-rollback-strategy.md")
MP = os.path.join(REPO, "docs/reports/iteration-master-plan.md")

ROW = {
    "round": "R566",
    "ts": "2026-09-19T03:10:00+0800",
    "kind": "主线对照轮 (同窗单变量: 既有开关 AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR 取值 0 vs 1 × 外部真值 codex, 6 新窗 w125..w130; 零产品源码改动 / 零新增夹具 / 零新增开关)",
    "artifact": "eval/rover/r566/{prereg-r566.json,run_r566.sh,setup_r566.py,port_r566.py,frozen-reuse-registration-r566.json,gate-margin-r566.json,gate-postcheck-r566.json,fingerprint-r566.json,kpi-table-r566.json,matrix_r566.py,percase-matrix-r566.json,adjudicate_r566.py,verdict-r566.json,summary-r566.json,taskset-r566.json,cases/,snapshots/} + eval/rover/r507pre/precondition-r566.json + docs/reports/r566-repair-dose-samewindow-and-precond.md",
    "change": "① 承重件 = 以**同窗单变量**回答 R565 遗留「预算不足 vs 生成/修复面不足」: 轴 0→1 中位 50.0→55.0(+5) / delta_median −7.5→−3.0 / named 窗 5/6→3/6, **两档均不过判据 v2**; 且方向与 R560 剂量轴 (dose3 中位 52.5 < dose0 54.0) **相反** ⇒ 臂效应落在跨窗摆动带内, 不得宣称增益; ② 失分结构 = 全三臂 always_fail 空、wobble 逐例集合恰为 wythoff#43–57, life/sub/nim 在全部臂全部窗全绿 ⇒ 失分归因生成面单族产物缺陷 (与 R562/R564 只读定因一致), 且**外部真值亦在 w127/w128 失 #43-public/#57-hidden** (truth range 2 即来自此); ③ RF0001.3 completion 压缩同窗读数: 轴关 ⇒ 调用 −45.5%(6 vs 11) / 新算 prompt −57.1% / completion −50.2%, 代价中位质量 −5 ⇒ 出口闸「双列不劣化 ∧ 质量不降」第二项判负, 不宣称降幅; ④ 自捕器具读法缺陷: 端口脚本漏替换**窗口名** ⇒ matrix 首跑 errors=18/18、adjudicate 首跑 rc=2 INSTRUMENT_DEFECT; 按「裁决器报 RED 第一假设=器具读法错」修窗口名后 errors=0 / xref=18/18 agree / rc=1, 首跑读数不采信",
    "readings": {
        "arms": {
            "C1_truth": {"cases_windows": [58, 58, 56, 56, 58, 58], "median": 58.0, "range": 2,
                         "calls": 135, "new_prompt": 65244, "completion": 44293,
                         "v_all_med": 0.9522, "v_incr_med": 0.9610,
                         "per_case": {"always_pass_n": 56, "always_fail_n": 0, "wobble": [43, 57]}},
            "R566B0_exec0": {"cases_windows": [58, 43, 45, 50, 50, 51], "median": 50.0, "range": 15,
                             "calls": 6, "new_prompt": 906, "completion": 13455,
                             "v_all_med": 0.9819, "v_incr_med": None,
                             "rc_windows": [0, 5, 5, 8, 5, 5], "stage": "expect_stdout ×5 / self_test_unmet ×1",
                             "per_case": {"always_pass_n": 43, "always_fail_n": 0, "wobble_n": 15, "wobble": "wythoff#43–57 全族"}},
            "R566B1_exec1": {"cases_windows": [58, 52, 43, 58, 58, 45], "median": 55.0, "range": 15,
                             "calls": 11, "new_prompt": 2113, "completion": 27003,
                             "v_all_med": 0.9789, "v_incr_med": 0.9755,
                             "rc_windows": [0, 5, 5, 0, 0, 5],
                             "per_case": {"always_pass_n": 43, "always_fail_n": 0, "wobble_n": 15, "wobble": "wythoff#43–57 全族"}},
        },
        "verdict": {"rc": 1, "verdict": "FAIL(被测/前提)", "blocked": ["quality_paired_shortfall:R566B0,R566B1"],
                    "delta_median": {"R566B0": -7.5, "R566B1": -3.0}, "delta_min": {"R566B0": -15, "R566B1": -13},
                    "named_windows": {"R566B0": ["w126", "w127", "w128", "w129", "w130"], "R566B1": ["w126", "w127", "w130"]},
                    "reliable_windows": 6, "truth_median": 58.0, "truth_range": 2, "selftest": "6/6"},
        "family_distribution_wythoff": {"C1": [15, 15, 13, 13, 15, 15], "R566B0": [15, 0, 2, 7, 7, 8], "R566B1": [15, 9, 0, 15, 15, 2]},
        "prev_round_side_by_side": {"R565B0_axis_unset": {"median": 52.0, "calls": 13, "new_prompt": 3732, "completion": 31071},
                                    "R560B0_axis0": {"median": 54.0, "calls": 6}, "R560B3_axis3": {"median": 52.5, "calls": 25}},
        "gate": {"prev_swing_mb": 68, "margin_mb": 68, "required_mb": 2718, "ceiling_mb": 2800, "slack_mb": 82,
                 "selftest": "6/6 teeth", "discriminating_pair": True, "postcheck_rc": 0,
                 "postcheck_swing_mb": 70, "next_required_mb": 2720},
        "fingerprint_C4": {"identity": {"calls": 6, "violations": 0}, "determinism_sha8": "b9068f56",
                           "nontrivial": "未行使 (B0 每窗仅 1 调用, 无 call2)"},
        "precond": {"acceptable_scoped": False, "blocked_n": 10, "arm_windows": 18, "rc": 1},
    },
    "honest_boundaries": [
        "铁律 11 rc=1 ⇒ 全部成本/降幅读数标「参考(未可验收)」, 不得作验收依据",
        "单轮 6 窗 / 每臂每窗 n=1; 臂效应(中位差 5)与跨窗摆动(同配置跨轮中位差 3 / 极差 15)同量级 ⇒ 不得宣称 arm 增益或损失",
        "C4-3 非平凡判据本轮未行使 (指纹点选 B0 每窗仅 1 调用); v_incr 对 B0 结构性缺失 ⇒ 记未行使不记 0",
        "起手闸窗口非随时可得: 本轮需 pid 定向回收本会话只读语言服务器 (179MB) 才开门; 下一轮 REQ=2720",
        "wythoff#43/#57 对外部真值同样失分 ⇒ 该族不可直接当本侧能力缺陷的单侧证据",
    ],
    "next": "① 契约加厚 v3 / 产物落点自验 (唯一直面手段, 待放行) ② 交付闸/停止条件 (待放行) ③ C4-3 换臂行使 + 起手闸 REQ=2720 行使 (零开发) ④ R560∪R566 剂量轴 12 窗并池只读复核 (零新臂)",
    "owner_round": "R566",
}

DT_NEW = ("> - **最近一轮（R566，2026-09-19 · cron 60min tick）**: **主线对照轮（同窗单变量 = 既有开关 "
          "`AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 取值 0 vs 1 × 外部真值 codex）** —— 冻结题集逐字节复用（`taskset` sha "
          "`e0c667c2…`，与 R559/R560/R563/R565 同件）+ 6 新窗 `w125..w130`；全臂同一枚 AOT 二进制（sha `320d0eb1…`）。读数："
          "`C1`（真值）逐窗 58/58/56/56/58/58 ⇒ 中位 **58.0**/极差 2、135 调用、新算 65,244；`R566B1`（轴=1）58/52/43/58/58/45 ⇒ 中位 "
          "**55.0**/极差 15、11 调用、新算 2,113、completion 27,003；`R566B0`（轴=0）58/43/45/50/50/51 ⇒ 中位 **50.0**/极差 15、6 调用、"
          "新算 906、completion 13,455。判据 v2 判决 **rc=1 FAIL(被测/前提)**、`blocked=[quality_paired_shortfall:R566B0,R566B1]`、"
          "`delta_median` −7.5 / −3.0、6/6 真值窗 reliable。**承重结论**：R565 遗留的「预算不足 vs 生成/修复面不足」已被同窗单变量回答 —— "
          "轴 0→1 中位 +5 但**两档均不过判据**，且方向与 R560 剂量轴（dose 3 中位 52.5 < dose 0 中位 54.0）**相反** ⇒ 臂效应落在跨窗摆动带内；"
          "失分结构 = 全三臂 `always_fail` 空、`wobble` 逐例集合**恰为 wythoff#43–57**（`life`/`sub`/`nim` 全臂全窗全绿）⇒ 归因生成面单族产物缺陷，"
          "且**外部真值亦在 w127/w128 失 #43-public/#57-hidden**。RF0001.3（completion 压缩）同窗读数：轴关 ⇒ 调用 −45.5% / 新算 prompt −57.1% / "
          "completion −50.2%，代价中位质量 −5 ⇒ 出口闸「双列不劣化 ∧ 质量不降」第二项判负，**不宣称降幅**。自捕器具读法缺陷：端口脚本漏替换**窗口名** ⇒ "
          "matrix 首跑 `errors=18/18`、adjudicate 首跑 `rc=2 INSTRUMENT_DEFECT`（按「RED 第一假设=器具读法错」修后 `errors=0` / `xref=18/18 agree` / `rc=1`）。"
          "起手闸：`prev_swing=68` ⇒ `REQ=2718`，真机 `ceiling=2800/slack=+82`、判别力成对控制 `true_discrimination`、后置 `rc=0`（`swing_mb=70` ⇒ 下轮 `REQ=2720`）；"
          "**新边界** = 起臂前需 pid 定向回收本会话只读语言服务器（179MB）方得窗口。**未可验收**：铁律 11 前置器 `rc=1`（18 臂窗中 10 项未过）⇒ 全部降幅只作**参考**。"
          "细节 `docs/reports/r566-repair-dose-samewindow-and-precond.md`。\n")

MP_TAIL = ("- **下轮候选 (R566)**: ① 契约加厚 v3 / 产物**落点自验**（wythoff 族唯一直面手段；须动契约/产品分支 ⇒ **待放行**）"
           " ② 交付闸/停止条件（`rc=5`/`rc=8` 仍交付 = 静默降级 ⇒ 新增产品分支 ⇒ **待放行**）"
           " ③ C4-3 非平凡判据**换臂行使**（点选 ≥2 调用臂）+ 起手闸 `REQ=2720` 行使（零开发）"
           " ④ R560∪R566 剂量轴并池只读复核（w107..w112 ∪ w125..w130 = 12 窗 × 3 剂量档，逐例稳定性池化；零新臂）"
           " ⑤ 本轮已闭合：R565-② 预算轴单变量（同窗 exec 0 vs 1）、R565-④ 指纹/口径双口径新窗复核（C4-1/2 rc=0，C4-3 未行使）。\n")


def main():
    # 1 前置器件入库
    shutil.copyfile("/tmp/r566/precond-r566.json", os.path.join(REPO, "eval/rover/r507pre/precondition-r566.json"))
    print("[1] precondition-r566.json <= %d B" % os.path.getsize(os.path.join(REPO, "eval/rover/r507pre/precondition-r566.json")))

    # 2 kpi.jsonl 幂等追加
    txt = io.open(KPI, encoding="utf-8").read()
    if '"round": "R566"' in txt:
        print("[2] kpi.jsonl 已含 R566 ⇒ 幂等跳过")
    else:
        if not txt.endswith("\n"):
            txt += "\n"
        txt += json.dumps(ROW, ensure_ascii=False) + "\n"
        io.open(KPI, "w", encoding="utf-8").write(txt)
    rows = [json.loads(l) for l in io.open(KPI, encoding="utf-8") if l.strip()]
    hit = [r for r in rows if r.get("round") == "R566"]
    assert len(hit) == 1, len(hit)
    print("[2] kpi.jsonl rows=%d, R566 ×%d, next=%s" % (len(rows), len(hit), hit[0]["next"][:40]))

    # 3 最新状态块: 插入 R566 行 + 把 R565 行标历史快照
    dt = io.open(DT, encoding="utf-8").read()
    if "最近一轮（R566" in dt:
        print("[3] DT 已含 R566 ⇒ 幂等跳过")
    else:
        anchor = "> - **最近一轮（R565，2026-09-19 · cron 60min tick）**"
        assert dt.count(anchor) == 1, dt.count(anchor)
        dt = dt.replace(anchor, "> - **最近一轮（R565，2026-09-19 · cron 60min tick）【历史快照，已被上方 R566 行取代】**")
        dt = dt.replace("【历史快照，已被上方 R566 行取代】**", "【历史快照，已被上方 R566 行取代】**", 1)
        dt = dt.replace("> ### ⏱ 最新状态（2026-09-17 主线定义更正：外部对照自检；R413 KPI 降为其判据之一 — 恢复迭代先读这里；下方为历史快照）\n>\n",
                        "> ### ⏱ 最新状态（2026-09-17 主线定义更正：外部对照自检；R413 KPI 降为其判据之一 — 恢复迭代先读这里；下方为历史快照）\n>\n"
                        + DT_NEW)
        io.open(DT, "w", encoding="utf-8").write(dt)
    dt2 = io.open(DT, encoding="utf-8").read()
    assert dt2.count("最近一轮（R566") == 1 and dt2.count("【历史快照，已被上方 R566 行取代】") == 1
    print("[3] DT ok: R566 行 ×1, R565 行已标历史快照 ×1")

    # 4 计划尾部候选 (增量追加)
    mp = io.open(MP, encoding="utf-8").read()
    if "下轮候选 (R566)" in mp:
        print("[4] 主计划已含 R566 候选 ⇒ 幂等跳过")
    else:
        if not mp.endswith("\n"):
            mp += "\n"
        mp += MP_TAIL
        io.open(MP, "w", encoding="utf-8").write(mp)
    mp2 = io.open(MP, encoding="utf-8").read()
    assert mp2.count("下轮候选 (R566)") == 1 and mp2.count("下轮候选 (R565)") == 1
    print("[4] 主计划 ok: lines=%d, R565 候选行保留 ×1, R566 候选行 ×1" % len(mp2.splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
