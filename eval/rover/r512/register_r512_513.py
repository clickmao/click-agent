#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R512/R513 入册: 往 docs/verification-registry.json 追加两行 (幂等; 已存在同名 id ⇒ 停手)。

字段纪律 (入册行): id / level('L2'|'L3') / capability / covers(纯路径) / evidence_cmd / evidence_path /
evidence_generated_with{instrument, instrument_sha12, audited_by_round} / negative_control / owner_round。
`audited_by_round` 取合法段 R512 / R513 (禁 R512pre 之类后缀)。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs", "verification-registry.json")


def sha12(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


ROWS = [
    {
        "id": "external.contrast-p3-p4-n2-fixture-defect",
        "level": "L3",
        "capability": "外部真值对照 (R512): 同环境·同输入·同模型 (deepseek-chat), 题集 p3+p4, 两侧各 n=2 + 预注册增补臂 B(预算 12) n=2; 逐窗口机检 C1–C5; 起手闸 2×PASS。读数: p3 两侧全 12/12, 本侧 4–14 调用 / 60k–263k tokens vs codex 43–46 调用 / 850k–1.27M tokens (调用 ↓87–91%, token ↓89–95%); p4 三臂失败集合逐字相同 (4/12) ⇒ 机检定位 **p4 夹具/题面缺陷**: 题面第 2 条未写 `--now` 缺省语义, 隐藏用例 8/12 条不带 `--now` 调用, 两侧 (含外部真值) 同败 ⇒ 判据丧失区分力。判据 C1/C2/C3/C4 PASS (token 比 max 0.6165 ≤ 0.70; 调用比 max 0.5714 ≤ 1.00), C5 FAIL (exec_precondition rc=1) ⇒ 本轮 token/调用降幅标『参考 (未可验收)』。",
        "covers": [
            "eval/rover/r512/taskset-r512.json",
            "eval/rover/r512/prereg-r512.json",
            "eval/rover/r512/prereg-r512-addendum.json",
            "eval/rover/r512/build_taskset_r512.py",
            "eval/rover/r512/run_contrast_r512.sh",
            "eval/rover/r512/aggregate_r512.py",
            "eval/rover/r512/freeze_snapshot_r512.py",
            "eval/rover/r512/check_criteria_r512.py",
            "eval/rover/r512/nc_r512.py",
            "eval/rover/r512/evidence/checks-r512.json",
            "eval/rover/r512/evidence/nc-r512.json",
            "eval/rover/r512/evidence/summary-r512.txt",
            "eval/rover/r512/evidence/excluded-dumps-r512.json",
            "eval/rover/r512/evidence/windows/w1/report.json",
            "eval/rover/r512/evidence/windows/w2/report.json",
            "eval/rover/r507pre/precondition-r512.json",
            "docs/reports/r512-external-contrast-p4-fixture-defect.md",
        ],
        "evidence_cmd": "bash eval/rover/r512/run_contrast_r512.sh ; python3 eval/rover/r512/aggregate_r512.py --run-dir DIR --json DIR/report.json ; python3 eval/rover/r512/check_criteria_r512.py --run-dir DIR --json eval/rover/r512/evidence/checks-r512.json --precond-json eval/rover/r507pre/precondition-r512.json ; python3 eval/rover/r507pre/exec_precondition.py --round R512",
        "evidence_path": "eval/rover/r512/evidence/checks-r512.json",
        "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "live",
                                    "pin_reason": "archived-per-round", "artifact_sha12": None,
                                    "instrument": "eval/rover/r512/aggregate_r512.py",
                                    "instrument_sha12": sha12(os.path.join(REPO, "eval/rover/r512/aggregate_r512.py")),
                                    "binding": "audit-pin", "audited_by_round": "R512"},
        "negative_control": "成对 (本轮实测, evidence/nc-r512.json, 判分器 = eval/rover/r511/grade_r511.py): ① 正控 = 参考解 p3/p4 各 12/12 (对**副本**判分, 不污染参考解树); ② 6 个指名缺陷变异体全检出 —— p3 三个沿用 R508 原串 (incr 非原子 ⇒ 精确点名 incr_concurrent_atomic; ttl 失效 ⇒ ttl_expire_and_count+stats_live_count; 无 WAL 重放 ⇒ restart_recovery+restart_drops_expired); p4 三个 (原地重写 ⇒ 精确点名 no_temp_residue; id 复用 ⇒ id_monotonic_no_reuse+4; ttl 失效 ⇒ ttl_expiry_uses_injected_clock+2) ⇒ `SELFTEST=OK`。③ 首次负控报 NC_NOT_DETECTED 系我方预期名口径写错 (用例名不带 test_ 前缀), 修正后转 OK —— 负控对本轮判据器口径同样有效。",
        "owner_round": "R512",
    },
    {
        "id": "external.contrast-p4-fixture-v2-acceptable",
        "level": "L3",
        "capability": "外部真值对照 (R513, p4 题面 v2): 按 R512 机检定位的夹具缺陷做**最小修法** —— 题面增补『未提供 `--now` 时必须回落到系统时钟 (time.time()), 不得报错、不得要求该选项必填』, 隐藏用例与参考解逐字节不变 (用例 sha 9105a116… 两侧同; diff -r 参考解树为空; v1 sha 678624f5… → v2 sha 384fa721…)。重测 (本侧 agent 默认 ×2 / codex 真值 ×2) **全部 12/12 整题全对**, 铁律 11 前置 `exec_precondition --round R513` **rc=0** (ACCEPTABLE_SCOPED=True, SELF_REPORT_AGREES=True) ⇒ 本窗口读数可作验收依据。判据 C1/C2/C4/C5 PASS, **C3 FAIL** (token 比 0.5719 / 1.1376) ⇒ 可稳定验收的是**远端调用数下降** (7 vs 14 / 8; 比 0.50–0.875), token 降幅只在 w1 达标 (↓43%)。同题 v1(4/12 三臂同败) → v2(12/12 四跑次全对) 证明缺陷归因于题面而非实现侧能力。",
        "covers": [
            "eval/rover/r513/taskset-r513.json",
            "eval/rover/r513/prereg-r513.json",
            "eval/rover/r513/build_taskset_r513.py",
            "eval/rover/r513/run_contrast_r513.sh",
            "eval/rover/r513/aggregate_r513.py",
            "eval/rover/r513/freeze_snapshot_r513.py",
            "eval/rover/r513/check_criteria_r513.py",
            "eval/rover/r513/evidence/checks-r513.json",
            "eval/rover/r513/evidence/summary-r513.txt",
            "eval/rover/r513/evidence/windows/w1/report.json",
            "eval/rover/r513/evidence/windows/w2/report.json",
            "eval/rover/r507pre/precondition-r513.json",
            "docs/reports/r513-p4-fixture-v2-acceptable.md",
        ],
        "evidence_cmd": "bash eval/rover/r513/run_contrast_r513.sh ; python3 eval/rover/r513/check_criteria_r513.py --run-dir DIR --json eval/rover/r513/evidence/checks-r513.json --precond-json eval/rover/r507pre/precondition-r513.json ; python3 eval/rover/r507pre/exec_precondition.py --round R513",
        "evidence_path": "eval/rover/r513/evidence/checks-r513.json",
        "evidence_generated_with": {"evidence_kind": "artifact", "pin_status": "live",
                                    "pin_reason": "archived-per-round", "artifact_sha12": None,
                                    "instrument": "eval/rover/r513/aggregate_r513.py",
                                    "instrument_sha12": sha12(os.path.join(REPO, "eval/rover/r513/aggregate_r513.py")),
                                    "binding": "audit-pin", "audited_by_round": "R513"},
        "negative_control": "判分器与 R512 同源 (eval/rover/r511/grade_r511.py, 用例文件与 R512 逐字节同), 负控沿用 R512 实测 `SELFTEST=OK` (evidence/nc-r512.json: 正控 12/12 + 6 变异体全检出); 另以 build_taskset_r513.py --check 作**修法自检** (用例 sha 未变 / 参考解树 diff 为空 / v2 题面含新增句且与 v1 不同 / sha 自洽), rc=0。",
        "owner_round": "R513",
    },
]


def main():
    doc = json.load(io.open(REG, encoding="utf-8-sig"))
    have = {r["id"] for r in doc["rows"]}
    dup = [r["id"] for r in ROWS if r["id"] in have]
    if dup:
        print("[致命] 已存在同名 id ⇒ 停手: %s" % dup)
        return 4
    doc["rows"].extend(ROWS)
    doc["updated_round"] = "R513"
    with io.open(REG, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    back = json.load(io.open(REG, encoding="utf-8-sig"))
    ids = [r["id"] for r in back["rows"]]
    print(json.dumps({"rows": len(back["rows"]), "updated_round": back["updated_round"],
                      "added": [r["id"] for r in ROWS], "readback_ok": all(i in ids for i in [r["id"] for r in ROWS])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
