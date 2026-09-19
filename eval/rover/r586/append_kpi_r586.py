import io
import json
import os
import subprocess

REPO = "/home/agentuser/AgentFramework"
p = os.path.join(REPO, "eval/capability/kpi.jsonl")
ts = subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True, text=True,
                    check=True).stdout.strip()

row = {
    "round": "R586",
    "ts": ts,
    "kind": "主线对照轮 (同被测件 + 同冻结题集、只换窗集的复跑；判定 R585 质量缺口是否跨窗复现；零产品源码改动/零新夹具语义/零新开关)",
    "change": (
        "① 驱动器 run_r586.sh 派生自 run_r585.sh (轮号/臂集合/窗口段替换 + 二进制 sha 运行前后一致性断言 + 起手闸条款); "
        "② 判据器 kpi_r586.py 派生自 kpi_r585.py (主线段 C0/C1/C2 + C5 缺口复现段[与 R585 D 集同号∧区间重叠的三态判定] "
        "+ C6 步数列面段 + 汇总打印面补 steps 列); "
        "③ 判据器影子自检 eval/rover/r586/shadow_selftest_r586.py (零被测执行 7 例: 可判绿 / 异轮臂名缺侧 fail-closed rc=3 / "
        "R585 读数投影后逐值复现其判决 / floor 有牙 / 有效窗不足判红 / 步数缺档 rc=2 / bad_dumps rc=2); "
        "④ 只读定因器 eval/rover/r586/wythoff_cause_r586.py (派生自 r562 同族器具, 增 --only-idx/--timeout/--reclassify); "
        "⑤ 自捕 3 件 (R585 报告面 steps 误写未测 / 判据器打印面缺 steps 列 / 影子自检用例未做臂名投影 ⇒ 修用例不改判据)"
    ),
    "readings": {
        "arms": ["C1(codex 外部真值)", "R586D(产品默认档, 剂量键全 unset)"],
        "windows": ["w157", "w158", "w159"],
        "reps_per_window": 3,
        "quality_cases_pass_58": {
            "C1_truth_per_window": {"w157": 58, "w158": 58, "w159": 58},
            "R586D_median_per_window": {"w157": 58, "w158": 55, "w159": 43},
            "R586D_per_rep": {"w157": [47, 58, 58], "w158": [55, 58, 49], "w159": [48, 43, 43]},
            "R586D_median": 49, "R586D_range_across_windows": 15, "C1_median": 58, "C1_range": 0,
        },
        "paired_quality": {"D_per_window_product_minus_truth": [0, -3, -15], "D_median": -3,
                           "valid_windows": 3, "prereg_median_floor": -2, "prereg_per_window_floor": -15,
                           "verdict": "FAIL (中位越下限 ∧ w159 触底)", "unreliable_windows": []},
        "gap_reproduction_C5": {"prev_round": "R585", "prev_D": [-8, -3], "prev_median": -5.5,
                                "this_D": [0, -3, -15], "this_median": -3,
                                "same_sign": True, "interval_overlap": True,
                                "state": "缺口跨窗复现", "rule": "跨轮并列不相减"},
        "cost_three_columns": {
            "runs_product": 9, "runs_truth": 3,
            "calls": {"product": 19, "truth": 51, "per_run_product": 2.11, "per_run_truth": 17.0},
            "new_prompt": {"product": 4058, "truth": 25012, "per_run_product": 451, "per_run_truth": 8337},
            "completion": {"product": 44380, "truth": 24561, "per_run_product": 4931, "per_run_truth": 8187},
            "hit_rate_v_all": {"product": 0.97, "truth": 0.95},
            "hit_rate_v_incr": {"product": 0.97, "truth": 0.96},
            "label": "参考(未可验收) — 铁律11 rc=1; 两侧跑次数不等(9 vs 3) ⇒ 只可读按跑次归一列",
        },
        "failure_families": {"wythoff": "全部失败例 100% 集中此单族 (15 例/族)",
                             "classes": {"MOVE_NOT_COLD": 38, "EMPTY_OR_ERROR": 12, "LOSE_FOR_WIN": 7, "WIN_FOR_LOSE": 6},
                             "family_pass_by_arm_window": {"w157": [4, 15, 15], "w158": [12, 15, 6], "w159": [5, 0, 0]},
                             "cross_check": "族内通过数加回非族 43 例后与铁律11 前置器逐臂窗 9/9 一致 ⇒ 非采集侧假红",
                             "oscillation_same_case_pass_and_fail_across_windows": {"agentD-r1": 11, "agentD-r2": 15, "agentD-r3": 15},
                             "timeouts": 0},
        "gates": {"A1": "PASS(2835MB)", "A2": "PASS(2840MB)", "REQ_mb": 2755, "margin_mb": 105,
                  "discrimination_pair": {"base": "GATE_BLOCKED", "clause": "GATE_BLOCKED",
                                          "in_band": True, "true_discrimination": False, "rc": 3,
                                          "note": "判别力未行使 (已如实登记), 不得读成闸已行使"},
                  "leak_selfcheck_rc": 0},
        "iron11_precondition": {"rc": 1, "executable_and_correct": False, "acceptable_scoped": False,
                                "self_report_agrees": True,
                                "blocked_arm_windows": ["w157/agentD-r1 47/58", "w158/agentD-r1 55/58",
                                                        "w158/agentD-r3 49/58", "w159/agentD-r1 48/58",
                                                        "w159/agentD-r2 43/58", "w159/agentD-r3 43/58"]},
        "bin": {"path": "~/.agentframework/artifacts/pub_r585/agenthost",
                "sha256": "4b70fd7cdb39f1c72c22db131a0ab36ad1bcafc54153c6aa5cc4070868ecb1ce",
                "same_artifact_as_R585": True, "stable_across_run": True},
        "taskset_sha_ref": "e0c667c2 (与 R559-R585 同件)",
        "steps_executed": [7, 7, 7, 13, 8, 7, 7, 7, 7],
        "plan_steps_total": [10, 10, 17, 14, 9, 10, 10, 11, 11],
        "steps_face_note": "C6 PASS (9/9 非空); 附 R585 纠偏: 该列在 verdict-r585.json 里本就在档 [8,15,7,14,7,7,7,7,7], R585 报告/§7 写未测 = 报告面缺陷, 首跑读数不撤",
        "shadow_selftest": {"path": "eval/rover/r586/shadow-selftest-r586.json", "cases": 7, "all_agree": True},
        "verdict": {"rc": 1, "judge": "FAIL(质量配对未过)", "blocked": ["C1_quality_paired:R586D"]},
    },
    "artifact": (
        "eval/rover/r586/{dag-r586.md,prereg-r586.json,run_r586.sh,kpi_r586.py,shadow_selftest_r586.py,"
        "shadow-selftest-r586.json,wythoff_cause_r586.py,wythoff-cause-r586.json,report-r586.md,"
        "kpi-table-r586.json,verdict-r586.json,snapshots/} ; 运行根 ~/.agentframework/harness/runs/r586/ "
        "(logs/,gate-*.json,leak-selfcheck.json,precond-r586.json,bin-sha-check.json) ; "
        "主线状态块 docs/reports/dynamic-telemetry-eval-rollback-strategy.md §7 ; 轮志 docs/reports/iteration-master-plan.md"
    ),
}

lines = [l for l in io.open(p, encoding="utf-8").read().splitlines() if l.strip()]
assert all(k in row for k in ("round", "ts", "kind", "change", "readings", "artifact"))
assert set(row.keys()) == set(json.loads(lines[-1]).keys()), "键集必须与同族既有行逐字相同"
kept = [l for l in lines if json.loads(l).get("round") != "R586"]
kept.append(json.dumps(row, ensure_ascii=False))
io.open(p, "w", encoding="utf-8").write("\n".join(kept) + "\n")
back = [json.loads(l) for l in io.open(p, encoding="utf-8").read().splitlines() if l.strip()]
m = [r for r in back if r.get("round") == "R586"]
print("lines", len(lines), "->", len(back), "| R586 rows", len(m), "| rc", m[0]["readings"]["verdict"]["rc"],
      "| ts", m[0]["ts"])
