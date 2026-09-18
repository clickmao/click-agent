#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R563 台账行追加 (幂等; 键集与同族既有行**逐字相同**)。

用法: python3 eval/rover/r563/append_ledger_r563.py
不改写其它行; 已存在同轮行 ⇒ 幂等跳过。
"""
import io
import json
import os
import time

REPO = "/home/agentuser/AgentFramework"
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")

row = {
    "round": "R563",
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
    "kind": "判据 v2 首次作预注册判据的真机对照轮 + 起手闸振幅余量条款行使 (产品默认档 × 外部真值; 零产品源码改动 / 零新增夹具 / 零新增开关)",
    "artifact": "eval/rover/r563/{run_r563.sh,prereg-r563.json,ingest_r563.py,kpi_r563.py,kpi-table-r563.json,matrix_r563.py,percase-matrix-r563.json,adjudicate_r563.py,verdict-r563.json,gate_margin_r563.py,gate-margin-r563.json,gate-margin-r563-v1-blocked.json,gate-postcheck-r563.json} + eval/rover/r507pre/precondition-r563.json + docs/reports/r563-judge-v2-prereg-and-gate-margin.md",
    "change": "① 判据 v2 (docs/external-reference-harness.md §12) **首次作为预注册验收判据**行使于 6 个新窗 (w113..w118), 判决由 R561 装置产出 (adjudicate_r563.py 只喂数据, 零逻辑复制, 器具文件 sha 前后相同); ② 起手闸**振幅余量条款**落地并行使: v1 常量 200MB (跨区制振幅) 首跑拒起臂 (留档 gate-margin-r563-v1-blocked.json) ⇒ v2 = MARGIN max(60MB, 上一轮运行中实测振幅), 以既有闸 --gate-mb 生效; ③ 臂集 3→2 (去剂量档 B3, R561 已收口); ④ 轮目录规范布局补齐 (taskset-r563.json 与 cases/ 复用冻结件逐字节拷贝) 使铁律11 前置器可按轮号发现",
    "readings": {
        "criterion": "v2 (逐窗并列 + 真值崩窗 unreliable + 配对判据 n>=3)",
        "judge_rc": 1,
        "fail_arms": ["R563B0"],
        "per_window_cases": {"C1": [58, 58, 58, 58, 58, 58], "R563B0": [50, 58, 43, 58, 58, 55]},
        "truth_median": 58.0, "truth_range": 0, "reliable_windows": 6, "unreliable_windows": [],
        "delta_median": {"R563B0": -1.5}, "delta_min": {"R563B0": -15}, "named_windows": {"R563B0": ["w115"]},
        "tokens": {"C1": {"calls": 34, "new_prompt": 22418, "completion": 18653, "v_all": 0.9244, "v_incr": 0.952},
                   "R563B0": {"calls": 6, "new_prompt": 906, "completion": 13379, "v_all": 0.9819, "v_incr": None}},
        "gate_clause": {"v1": {"rc": 2, "ceiling_mb": 2610, "required_mb": 2850, "outcome": "未起臂"},
                        "v2": {"required_mb": 2710, "A1_mem_mb": 2793, "A2_mem_mb": 2798, "leak_selfcheck_rc": 0},
                        "postcheck": {"rc": 0, "in_min_mb": 2734, "swing_mb": 64, "window_drift": False},
                        "selftest": "6/6 (2 正控 + 4 负控)"},
        "iron11": {"rc": 1, "blocked_arm_windows": 3, "cmd": "exec_precondition.py --round r563"},
        "instrument": {"matrix_xref": "12/12 agree", "matrix_errors": 0, "judge_shadow_selftest": "6/6",
                       "device_file_unchanged": True}
    },
    "honest_boundaries": "铁律11 rc=1 (blocked 3 臂窗) ⇒ 全部读数标「参考(未可验收)」; 单窗 w115 差 -15 是分歧主源 (n=6 窗, 与 w104..w112 旧窗**并列不相减**); 真值本轮 6/6 窗全可靠 (无 unreliable 窗) ⇒ v2 的崩窗分支本轮未被行使; 起手闸条款 v1 常量 200MB 在本宿主结构性不可达 (清残留后顶棚 2808 < 2850) ⇒ v1 读数原样留档不作废; 语言服务器 (RSS 191MB) 不在既有闸 blocker 模式内 (沉默占用, 仅登记未修); 前一轮作业收尾 (22:55:44) 重写了 R562 台账行与 verdict-r562.json, 本侧未做该改写 (归属=前轮 tick)",
    "owner_round": "R563",
    "next": "① wythoff 族修复 (须动契约/产品分支 ⇒ 待放行) ② 交付闸/停止条件 (rc=8/rc=5 仍交付 ⇒ 新增产品分支 ⇒ 待放行) ③ 振幅余量条款下轮由本轮实测 swing=64MB 派生行使 (--prev-swing-mb 64 ⇒ REQ=2714) ④ w115 单窗 -15 的**族级只读定因** (复用 r562/wythoff_cause 器具; 零产品改动)",
}

rows = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8", errors="replace") if l.strip()]
if any(r.get("round") == "R563" for r in rows):
    print("ALREADY_PRESENT round=R563 (幂等跳过)")
else:
    assert set(row.keys()) == set(rows[-1].keys()), (sorted(row.keys()), sorted(rows[-1].keys()))
    with io.open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8", errors="replace") if l.strip()]
    print("APPENDED rows=%d last_round=%s" % (len(rows), rows[-1]["round"]))
