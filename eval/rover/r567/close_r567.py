#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R567 收口写入: 前置器件 + kpi.jsonl 行 (幂等) + 最新状态块 + 计划尾部候选。全部读回校验。

读数一律机取自 eval/rover/r567/{verdict,summary,kpi-table,fingerprint,gate-*}-r567.json (禁手抄)。
"""
import io, json, os, shutil, sys

REPO = "/home/agentuser/AgentFramework"
PDIR = os.path.join(REPO, "eval/rover/r567")
KPI = os.path.join(REPO, "eval/capability/kpi.jsonl")
DT = os.path.join(REPO, "docs/reports/dynamic-telemetry-eval-rollback-strategy.md")
MP = os.path.join(REPO, "docs/reports/iteration-master-plan.md")


def J(p):
    return json.load(io.open(os.path.join(PDIR, p), encoding="utf-8"))


def wf(fam, arm):
    """族逐窗 [pass,total] → pass 序列"""
    d = J("verdict-r567.json")["family_distribution"][arm][fam]
    return [d[w][0] for w in sorted(d)]


def build_row():
    v, s, m = J("verdict-r567.json"), J("summary-r567.json"), J("kpi-table-r567.json")
    fp, gm = J("fingerprint-r567.json"), J("gate-postcheck-r567.json")
    pre = J("precond-r567.json")
    A = {a: s["arms"][a] for a in ("C1", "R567B0", "R567B3")}
    pcs = J("verdict-r567.json")["per_case_stability"]
    wins = v["manipulation"]["windows"]
    rc_w = {a: [w.get("rc") for w in m["arms"][a]["windows"]] for a in m["arms"]}
    return {
        "round": "R567",
        "ts": "2026-09-19T03:31:00+0800",
        "kind": "主线对照轮 (同窗单变量第二窗集: 既有开关 AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR 取值 0 vs 3 × 外部真值 codex, 6 新窗 w131..w136; 零产品源码改动 / 零新增夹具 / 零新增开关)",
        "artifact": "eval/rover/r567/{prereg-r567.json,run_r567.sh,setup_r567.py,port_r567.py,port_summary_r567.py,frozen-reuse-registration-r567.json,gate-margin-r567.json,gate-postcheck-r567.json,fingerprint-r567.json,kpi-table-r567.json,matrix_r567.py,percase-matrix-r567.json,adjudicate_r567.py,verdict-r567.json,summary-r567.json,taskset-r567.json,cases/,snapshots/} + eval/rover/r507pre/precondition-r567.json + docs/reports/r567-dose-axis-second-window-and-c4-exercise.md",
        "change": "① 承重件 = 同窗单变量**第二窗集**把剂量档位从 1 提到 3: 中位 52.5 (B0, 轴0) vs 54.5 (B3, 轴3) ⇒ delta_median −4.5 / −2.5、named 窗 4/6 / 3/6, **两档仍均不过判据 v2**; 与 R566 (轴 0 vs 1: 50.0 vs 55.0, −7.5/−3.0) **并列不相减**后可见: 剂量 0→1 差 +5、0→3 差 +2 ⇒ **非单调且同量级于跨窗摆动 (极差 13–16)** ⇒ 剂量档位不是承重变量, 不得宣称增益; ② 失分结构 = 全臂 always_fail 空, wythoff#43–57 为共同 wobble 集合 (life/nim 全臂全窗全绿; sub 仅 B0 在 w134 掉 5 例) ⇒ 与 R562/R564/R566 只读定因一致 (生成面单族), 本轮**不修** (未放行); ③ 轴关 (B0) ⇒ 调用 −73.9% (6 vs 23) / 新算 prompt −86.9% / completion −69.0%, 代价中位质量 −2 ⇒ 同 R566 结论 (省成本方向与质量方向相反), 出口闸第二项仍判负; ④ **候选④ C4 换臂行使成功**: 行使臂由 B0 换 B3 后 C4-1 (23 调用 0 违反) / C4-2 (call1 指纹 b9068f56 全 6 窗唯一) / **C4-3 sensitivity_exercised=True** (5 窗 call1≠call2) 全部真实行使, rc=0 selftest 4/4 —— 补齐 R566 的 C4-3 空缺; ⑤ 起手闸按上一轮实测振幅派生 MARGIN=70/REQ=2720, 真机 ceiling 2861/slack +141, 判别带**真行使** (同态 2650 PASS vs 2720 BLOCKED), 后置 rc=0 (in_min 2751 ≥ 2650, swing 103 ⇒ 下轮 REQ=2753)。",
        "readings": {
            "arms": {
                "C1_truth": {"cases_windows": A["C1"]["cases_windows"], "median": A["C1"]["median"], "range": A["C1"]["range"],
                             "calls": A["C1"]["calls"], "new_prompt": A["C1"]["new_prompt"], "completion": A["C1"]["completion"],
                             "v_all_med": round(A["C1"]["v_all_med"], 4), "v_incr_med": round(A["C1"]["v_incr_med"], 4),
                             "per_case": {"always_pass_n": len(pcs["C1"]["always_pass"]), "always_fail_n": 0, "wobble": pcs["C1"]["wobble"]}},
                "R567B0_exec0": {"cases_windows": A["R567B0"]["cases_windows"], "median": A["R567B0"]["median"], "range": A["R567B0"]["range"],
                                 "calls": A["R567B0"]["calls"], "new_prompt": A["R567B0"]["new_prompt"], "completion": A["R567B0"]["completion"],
                                 "v_all_med": round(A["R567B0"]["v_all_med"], 4), "v_incr_med": A["R567B0"]["v_incr_med"],
                                 "rc_windows": rc_w["R567B0"], "stage": "expect_stdout ×5 / done ×1",
                                 "per_case": {"always_pass_n": len(pcs["R567B0"]["always_pass"]), "always_fail_n": 0,
                                              "wobble_n": len(pcs["R567B0"]["wobble"]), "wobble_families": "wythoff#43–57 + sub#14/15/22/24/26"}},
                "R567B3_exec3": {"cases_windows": A["R567B3"]["cases_windows"], "median": A["R567B3"]["median"], "range": A["R567B3"]["range"],
                                 "calls": A["R567B3"]["calls"], "new_prompt": A["R567B3"]["new_prompt"], "completion": A["R567B3"]["completion"],
                                 "v_all_med": round(A["R567B3"]["v_all_med"], 4), "v_incr_med": round(A["R567B3"]["v_incr_med"], 4),
                                 "rc_windows": rc_w["R567B3"], "stage": "expect_stdout_exhausted ×4 / self_test_unmet ×1 / done ×1",
                                 "per_case": {"always_pass_n": len(pcs["R567B3"]["always_pass"]), "always_fail_n": 0,
                                              "wobble_n": len(pcs["R567B3"]["wobble"]), "wobble_families": "wythoff#43–57 全族"}},
            },
            "verdict": {"rc": v["rc"], "verdict": v["verdict"], "blocked": v["blocked"],
                        "delta_median": {a: v["arms"][a]["delta_median"] for a in ("R567B0", "R567B3")},
                        "delta_min": {a: v["arms"][a]["delta_min"] for a in ("R567B0", "R567B3")},
                        "named_windows": {a: v["arms"][a]["named_windows"] for a in ("R567B0", "R567B3")},
                        "reliable_windows": len(v["reliable_windows"]), "truth_median": v["truth_median"], "truth_range": v["truth_range"],
                        "selftest": "%d/%d" % (v["selftest"]["n_ok"], v["selftest"]["n"])},
            "family_distribution_wythoff": {"C1": wf("wythoff", "C1"), "R567B0": wf("wythoff", "R567B0"), "R567B3": wf("wythoff", "R567B3"),
                                            "life_nim_all_full": True},
            "prev_round_side_by_side": {"R566_axis_0_vs_1": {"median": [50.0, 55.0], "calls": [6, 11], "new_prompt": [906, 2113],
                                                             "completion": [13455, 27003], "delta_median": [-7.5, -3.0],
                                                             "windows": "w125..w130"},
                                        "R567_axis_0_vs_3": {"median": [52.5, 54.5], "calls": [6, 23], "new_prompt": [906, 6903],
                                                             "completion": [16364, 52749], "delta_median": [-4.5, -2.5],
                                                             "windows": "w131..w136"},
                                        "R560_dose_axis": {"median": [54.0, 52.5], "calls": [6, 25], "windows": "w107..w112"}},
            "gate": {"prev_swing_mb": 70, "margin_mb": 70, "required_mb": 2720, "ceiling_mb": 2861, "slack_mb": 141,
                     "selftest": "6/6 teeth", "discriminating_pair": True, "postcheck_rc": 0,
                     "postcheck_in_min_mb": gm["in_min_mb"], "postcheck_swing_mb": gm["swing_mb"],
                     "next_required_mb": 2650 + max(60, gm["swing_mb"])},
            "fingerprint_C4": {"rc": fp["rc"], "exercise_arm": "R567B3 (轴=3)",
                               "identity": {"calls": fp["checks"]["C4-1_identity"]["calls"], "violations": fp["checks"]["C4-1_identity"]["violations"],
                                            "na_unreported": fp["checks"]["C4-1_identity"]["na_unreported"]},
                               "determinism_call1_sha8": fp["checks"]["C4-2_determinism"]["distinct_call1_prompt_sha8"],
                               "nontrivial": {"sensitivity_exercised": fp["checks"]["C4-3_nontrivial"]["sensitivity_exercised"],
                                              "pairs": len(fp["checks"]["C4-3_nontrivial"]["sensitivity_call1_vs_call2"]),
                                              "example": fp["checks"]["C4-3_nontrivial"]["sensitivity_call1_vs_call2"][:2]},
                               "cross_round_call1_sha8_R566_B1": "b9068f56 (R566 summary; 与本轮同值 ⇒ 跨轮同前缀可比)"},
            "precond": {"acceptable_scoped": pre["acceptable_scoped"], "blocked_n": len(pre["blocked"]),
                        "blocked_scoped_n": len(pre["blocked_scoped"]), "arm_windows": 18, "windows_n": pre["windows_n"],
                        "self_report_agrees": pre["self_report_agrees"], "rc": 1},
        },
        "honest_boundaries": [
            "铁律 11 rc=1 ⇒ 全部成本/质量读数标「参考(未可验收)」, 不得作验收依据",
            "单窗集 6 窗 / 每臂每窗 n=1; 臂效应 (中位差 2–5) 小于跨窗摆动 (极差 13–16) ⇒ 不得宣称 arm 增益或损失",
            "剂量档位结论只覆盖 0/1/3 三档 × 2 窗集 (12 窗); 更高档位与并池复核未做",
            "wythoff#43/#57 对外部真值同样失分 (C1 本轮 w131/w135) ⇒ 该族不可当本侧单侧能力缺陷证据",
            "起手闸窗口非随时可得: 本轮仍需 pid 定向回收本会话只读语言服务器 + 停构建服务方得窗口; 下一轮 REQ=2753",
        ],
        "next": "① 契约加厚 v3 / 产物落点自验 (wythoff 族唯一直面手段, 待放行) ② 交付闸/停止条件 (rc=5/8 仍交付 = 静默降级, 待放行) ③ R560∪R566∪R567 剂量轴并池只读复核 (18 窗 × 3 档, 零新臂) ④ 起手闸 REQ=2753 行使 (零开发)",
        "owner_round": "R567",
    }


DT_NEW = ("> - **最近一轮（R567，2026-09-19 · cron 60min tick）**: **主线对照轮（同窗单变量第二窗集 = 既有开关 "
           "`AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR` 取值 0 vs 3 × 外部真值 codex）** —— 冻结题集逐字节复用（`taskset` sha "
           "`e0c667c2…`，与 R559/R560/R563/R565/R566 同件）+ 6 新窗 `w131..w136`；全臂同一枚 AOT 二进制（sha `320d0eb1…`）。读数："
           "`C1`（真值）逐窗 56/58/58/58/56/58 ⇒ 中位 **58.0**/极差 2、41 调用、新算 26,918；`R567B0`（轴=0）52/58/53/42/55/44 ⇒ 中位 "
           "**52.5**/极差 16、6 调用、新算 906、completion 16,364；`R567B3`（轴=3）47/58/58/45/51/58 ⇒ 中位 **54.5**/极差 13、23 调用、"
           "新算 6,903、completion 52,749。判据 v2 判决 **rc=1 FAIL(被测/前提)**、`blocked=[quality_paired_shortfall:R567B0,R567B3]`、"
           "`delta_median` −4.5 / −2.5、6/6 真值窗 reliable。**承重结论**：与 R566（轴 0 vs 1：50.0 vs 55.0，−7.5/−3.0）**并列不相减**后，"
           "剂量 0→1 差 +5 而 0→3 差 +2 —— **非单调且与跨窗摆动同量级** ⇒ 剂量档位不是承重变量，两档仍均不过判据；失分结构 = 全臂 "
           "`always_fail` 空、`wobble` 共同集合 `wythoff#43–57`（`life`/`nim` 全臂全窗全绿，`sub` 仅 B0 在 w134 掉 5 例）⇒ 与 R562/R564 "
           "只读定因一致，本轮不修（未放行）。轴关（B0）成本读数：调用 −73.9% / 新算 prompt −86.9% / completion −69.0%，代价中位质量 −2 ⇒ "
           "出口闸「双列不劣化 ∧ 质量不降」第二项仍判负，**不宣称降幅**。**候选④ C4 换臂行使成功**（行使臂 B0→B3）：C4-1 23 调用 0 违反、"
           "C4-2 call1 指纹 `b9068f56` 六窗唯一、**C4-3 `sensitivity_exercised=True`**（5 窗 call1≠call2）、rc=0 / selftest 4/4 —— 补齐 R566 "
           "的 C4-3 空缺。起手闸按上一轮实测振幅派生 `MARGIN=70`/`REQ=2720`，真机 `ceiling=2861/slack=+141`、判别带**真行使**"
           "（同态 2650 PASS vs 2720 BLOCKED）、后置 `rc=0`。**未可验收**：铁律 11 前置器 `rc=1`（18 臂窗中 10 项未过）⇒ 成本读数只作**参考**。"
           "细节 `docs/reports/r567-dose-axis-second-window-and-c4-exercise.md`。\n")

MP_TAIL = ("- **下轮候选 (R567)**: ① 契约加厚 v3 / 产物**落点自验**（wythoff 族唯一直面手段；须动契约/产品分支 ⇒ **待放行**）"
           " ② 交付闸/停止条件（`rc=5`/`rc=8` 仍交付 = 静默降级 ⇒ 新增产品分支 ⇒ **待放行**）"
           " ③ 剂量轴**并池只读复核**（R560 ∪ R566 ∪ R567 = 18 窗 × 3 档：0/1/3，逐例稳定性池化；零新臂）"
           " ④ 起手闸 `REQ=2753` 行使（零开发）"
           " ⑤ 本轮已闭合：R566-③ C4-3 换臂行使（rc=0，`sensitivity_exercised=True`）、R566-④ 剂量轴第二窗集单变量（0 vs 3，两档均不过判据）。\n")


def main():
    # 1 前置器件入库 (round 目录 + r507pre 归档, 幂等)
    src = "/tmp/r567/precond-r567.json"
    for dst in (os.path.join(PDIR, "precond-r567.json"),
                os.path.join(REPO, "eval/rover/r507pre/precondition-r567.json")):
        if os.path.exists(src):
            shutil.copyfile(src, dst)
    print("[1] precond-r567.json = %d B" % os.path.getsize(os.path.join(PDIR, "precond-r567.json")))

    # 2 kpi.jsonl 幂等追加 (先跑形式门禁)
    ROW = build_row()
    txt = io.open(KPI, encoding="utf-8").read()
    if '"round": "R567"' in txt:
        print("[2] kpi.jsonl 已含 R567 ⇒ 幂等跳过")
    else:
        if not txt.endswith("\n"):
            txt += "\n"
        txt += json.dumps(ROW, ensure_ascii=False) + "\n"
        io.open(KPI, "w", encoding="utf-8").write(txt)
    rows = [json.loads(l) for l in io.open(KPI, encoding="utf-8") if l.strip()]
    hit = [r for r in rows if r.get("round") == "R567"]
    assert len(hit) == 1, len(hit)
    assert hit[0]["readings"]["verdict"]["rc"] == 1
    print("[2] kpi.jsonl rows=%d, R567 ×%d, next=%s" % (len(rows), len(hit), hit[0]["next"][:40]))

    # 3 最新状态块: 插入 R567 行 + 把 R566 行标历史快照
    dt = io.open(DT, encoding="utf-8").read()
    if "最近一轮（R567" in dt:
        print("[3] DT 已含 R567 ⇒ 幂等跳过")
    else:
        anchor = "> - **最近一轮（R566，2026-09-19 · cron 60min tick）**"
        assert dt.count(anchor) == 1, dt.count(anchor)
        dt = dt.replace(anchor, "> - **最近一轮（R566，2026-09-19 · cron 60min tick）【历史快照，已被上方 R567 行取代】**")
        head = "> ### ⏱ 最新状态（2026-09-17 主线定义更正：外部对照自检；R413 KPI 降为其判据之一 — 恢复迭代先读这里；下方为历史快照）\n>\n"
        assert dt.count(head) == 1, dt.count(head)
        dt = dt.replace(head, head + DT_NEW)
        io.open(DT, "w", encoding="utf-8").write(dt)
    dt2 = io.open(DT, encoding="utf-8").read()
    assert dt2.count("最近一轮（R567") == 1 and dt2.count("【历史快照，已被上方 R567 行取代】") == 1
    print("[3] DT ok: R567 行 ×1, R566 行已标历史快照 ×1")

    # 4 计划尾部候选 (增量追加)
    mp = io.open(MP, encoding="utf-8").read()
    if "下轮候选 (R567)" in mp:
        print("[4] 主计划已含 R567 候选 ⇒ 幂等跳过")
    else:
        if not mp.endswith("\n"):
            mp += "\n"
        mp += MP_TAIL
        io.open(MP, "w", encoding="utf-8").write(mp)
    mp2 = io.open(MP, encoding="utf-8").read()
    assert mp2.count("下轮候选 (R567)") == 1 and mp2.count("下轮候选 (R566)") == 1
    print("[4] 主计划 ok: lines=%d, R566 候选行保留 ×1, R567 候选行 ×1" % len(mp2.splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
