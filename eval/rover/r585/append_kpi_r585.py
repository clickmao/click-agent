import io, json, os, subprocess
REPO = "/home/agentuser/AgentFramework"
p = os.path.join(REPO, "eval/capability/kpi.jsonl")

row = {
    "round": "R585",
    "ts": "2026-09-19T23:00:00+0800",
    "kind": "主线对照轮 (外部真值 codex 同窗对照; 器具环境恢复后首次可起臂; 零产品源码改动)",
    "change": (
        "① 器具环境自恢复: 前置件落点由仅 /tmp 改为稳定路径 ~/.agentframework/harness/runs/r585 "
        "(R584 前工件只存 /tmp 且已被回收 ⇒ 本轮为恢复动作; 见 eval/rover/r585/restore_env_r585.py); "
        "② 驱动器派生自 run_r571.sh (轮号/臂集合/前置自恢复/剂量键三枚显式 unset/二进制 sha 运行前后一致性断言); "
        "③ 判据器派生自 kpi_r571.py, 主线段改为 C0/C1/C2 (无剂量轴); "
        "④ 起手闸条款 = 阈值+观测振幅余量+连续2次 (swing 取自 R571 实测 105MB) 经既有 --gate-mb 行使; "
        "⑤ 自捕器具 2 件: (a) 闸 stdout 读契约 (pretty JSON + 尾行 'out <path>' ⇒ 须读 --out 落盘件, 首版 json.load(stdin) "
        "被吞成空串 ⇒ 起手闸读成未过并 exit 2, 未起臂零污染; 失败跑次留痕); (b) kpi 判据器残留 R585M1/M3 引用 ⇒ 汇总 KeyError, "
        "修后仅重跑后处理(不重测), 读数和原始 readings 一致"
    ),
    "readings": {
        "arms": ["C1(codex 外部真值)", "R585D(产品默认档, 剂量键全 unset)"],
        "windows": ["w154", "w155", "w156"],
        "reps_per_window": 3,
        "quality_cases_pass_58": {
            "C1_truth_per_window": {"w154": 56, "w155": 58, "w156": 58},
            "R585D_median_per_window": {"w154": 58, "w155": 50, "w156": 55},
            "R585D_per_rep": {"w154": [58, 58, 58], "w155": [53, 50, 47], "w156": [58, 48, 55]},
            "R585D_median": 55, "R585D_range_across_windows": 8, "C1_median": 58, "C1_range": 2,
        },
        "paired_quality": {"D_per_window_product_minus_truth": [-8, -3], "D_median": -5.5,
                           "valid_windows": 2, "prereg_median_floor": -2, "prereg_per_window_floor": -15,
                           "verdict": "FAIL (中位越下限)", "unreliable_windows": ["w154"]},
        "cost_three_columns": {
            "calls": {"product": 20, "truth": 74},
            "new_prompt": {"product": 5601, "truth": 28392},
            "completion": {"product": 48941, "truth": 23907},
            "hit_rate_v_all": {"product": 0.97, "truth": 0.97},
            "hit_rate_v_incr": {"product": 0.96, "truth": 0.97},
            "label": "参考(未可验收) — 铁律11 rc=1",
        },
        "failure_families": {"wythoff": "全部失败例 100% 集中此单族",
                             "kinds": {"stdout_mismatch": "主", "TimeoutExpired": 8, "rc=1": 2},
                             "timeout_cross_check": "在跑自报 8 例超时 ∧ 铁律11 前置器独立物化重跑同跑次 rc=124 (50/56) ⇒ 非采集侧假红"},
        "gates": {"A1": "PASS(2768MB)", "A2": "PASS(2761MB)", "REQ_mb": 2713,
                  "discrimination_pair_rc": 0, "leak_selfcheck_rc": 0},
        "iron11_precondition": {"rc": 1, "executable_and_correct": False,
                                "self_report_agrees": True, "self_report_mismatch": []},
        "bin": {"path": "~/.agentframework/artifacts/pub_r585/agenthost",
                "sha256": "4b70fd7cdb39f1c72c22db131a0ab36ad1bcafc54153c6aa5cc4070868ecb1ce",
                "stable_across_run": True},
        "taskset_sha_ref": "e0c667c2 (与 R559-R583 同件)",
        "steps_executed": "未测",
        "verdict": {"rc": 1, "judge": "FAIL(质量配对未过)", "blocked": ["C1_quality_paired:R585D"]},
    },
    "artifact": (
        "eval/rover/r585/{dag-r585.md,prereg-r585.json,run_r585.sh,restore_env_r585.py,kpi_r585.py,"
        "report-r585.md,kpi-summary-r585.json,kpi-table-r585.json,per-case-failures-r585.json,"
        "analyze_failures.py,bins-r585.json,snapshots/} ; 运行根 ~/.agentframework/harness/runs/r585/ "
        "(logs/,gate-*.json,leak-selfcheck.json,precond-r585.json,bin-sha-check.json)"
    ),
}

# 幂等: 同 round 已存在则原地更新
lines = [l for l in io.open(p, encoding="utf-8").read().splitlines() if l.strip()]
assert all(k in row for k in ("round", "ts", "kind", "change", "readings", "artifact"))
assert set(row.keys()) == set(json.loads(lines[-1]).keys()), "键集必须与同族既有行逐字相同"
kept = [l for l in lines if json.loads(l).get("round") != "R585"]
kept.append(json.dumps(row, ensure_ascii=False))
io.open(p, "w", encoding="utf-8").write("\n".join(kept) + "\n")
# 回读校验
back = [json.loads(l) for l in io.open(p, encoding="utf-8").read().splitlines() if l.strip()]
m = [r for r in back if r["round"] == "R585"]
print("lines", len(lines), "->", len(back), "| R585 rows", len(m), "| rc", m[0]["readings"]["verdict"]["rc"])
