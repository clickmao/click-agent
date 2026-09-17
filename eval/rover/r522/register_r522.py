#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R522 登记行 (克隆上一行键形状 ⇒ 只改 id/capability/covers/evidence_*/owner_round)。追加 2 行:
  ① 动作环上下文纪律的单变量消融 (如实收窄: 无增益)
  ② 前置器 blocked fail-closed 修复 (R522 真机自抓的假绿)
"""
import json, os, sys

REPO = "/home/agentuser/AgentFramework"
P = os.path.join(REPO, "docs/verification-registry.json")
reg = json.load(open(P, encoding="utf-8"))
rows = reg["rows"] if isinstance(reg, dict) and "rows" in reg else reg
last = rows[-1]
print("上一行键:", sorted(last.keys()), "总行数", len(rows))

NEW = [
    {
        "id": "internal.ablation-action-loop-context-discipline-r522",
        "capability": (
            "**动作环上下文纪律 · 同窗单变量消融 (结论: 无增益, 如实收窄)** —— 改动: `ActionLoopDiscipline` "
            "(① 验证合并为一次 run_command ② 探针不落盘 ③ 收尾从简) 仅注入动作环 system 提示尾部, 环境轴 "
            "`AGENTFRAMEWORK_ACTION_DISCIPLINE` (缺省开, off/0/false 关)。挂载证明 (实发 prompt, 非代码行): "
            "A1-on system=5456 vs A0-off 5234 (+222), 纪律锚只在 A1, 两组 prompt_sha8 互斥 ⇒ MOUNT_OK=True。"
            "读数 (题面/判据器同源 sha256 d9b373d8…/md5 f54889d7…, 上游两侧 deepseek-chat): A0-off 56/58 · 4 调用 · "
            "新算 9075 · completion 3850; A1-on 58/58 · 4 调用 · 新算 10128 · completion 4973; codex 58/58 · 5 调用 · "
            "新算 3775 · completion 2659。预注册 C3/C4/C5 (调用/新算/completion 各降 ≥30/30/40%) 三条全否 ⇒ "
            "**不宣称任何 token 或调用降幅**; R521 的 19 次调用本轮两臂均不复现 (各 4) ⇒ 主因非纪律, 单窗禁作能力结论。"
            "口径 = (调用数, 新算 prompt, completion) 分列, 主判据 = 调用数; 名义 total 只留档不作判据。"
        ),
        "covers": [
            "docs/reports/r522-action-loop-context-discipline.md",
            "src/agent.modelqueue/ActionLoopDiscipline.cs",
            "src/agent/modelqueue/ModelQueueAdapter.cs",
            "src/agent.tests/R522ContextDisciplineTests.cs",
            "eval/rover/r522/run_r522.sh",
            "eval/rover/r522/mount_check_r522.py",
            "eval/rover/r522/kpi_r522.py",
            "eval/rover/r522/prereg-r522.json",
            "eval/rover/r522/evidence/postfix-r522.txt",
        ],
        "evidence_cmd": "bash eval/rover/r522/run_r522.sh (同窗三臂: A0-off 纪律关 / A1-on 纪律开 / C-codex 参照; 单变量=env)",
        "evidence_path": "eval/rover/r522/evidence/windows/w1/report.json",
        "owner_round": "R522",
    },
    {
        "id": "eval.precondition-blocked-failclosed-r522",
        "capability": (
            "**前置器 `BLOCKED` 非空时禁 rc=0 (fail-closed)** —— R522 真机自抓器具缺陷: `exec_precondition.py` 原以 "
            "`return 0 if out[\"acceptable_scoped\"] else 1` 结尾, 而 `acceptable_scoped` 只统计**已执行且错误**的臂; "
            "未执行/缺判据件的臂进 `out[\"blocked\"]` 却被 rc 忽略 ⇒ 存在「可验收」假绿 (R522 首跑实测 rc=0, 同行打印 "
            "`BLOCKED: …missing_case_script`)。修: rc 前置要求 `out[\"blocked\"]` 为空。配套: r522 用例语料 "
            "`cases-r521.json` 逐字节副本 (sha256 270128eb…) 使前置器可真正重放三个快照 (agentA0 56/58 rc=1 · "
            "agentA1 58/58 rc=0 · codex 58/58 rc=0)。"
        ),
        "covers": [
            "eval/rover/r507pre/exec_precondition.py",
            "eval/rover/r522/cases/run_cases_r521.py",
            "eval/rover/r522/cases/cases-r521.json",
            "eval/rover/r522/evidence/postfix-r522.txt",
        ],
        "evidence_cmd": "python3 eval/rover/r507pre/exec_precondition.py --round r522 (期望 rc=1: A0-off 56/58 ⇒ BLOCKED; 修前同器 rc=0)",
        "evidence_path": "eval/rover/r522/evidence/postfix-r522.txt",
        "owner_round": "R522",
    },
]

added = []
for spec in NEW:
    if any(r.get("id") == spec["id"] for r in rows):
        print("已存在, 跳过:", spec["id"])
        continue
    row = dict(last)                     # 克隆上一行键形状 (含 level / evidence_generated_with 对象形状)
    row.update(spec)
    rows.append(row)
    added.append(spec["id"])
if isinstance(reg, dict) and "updated_round" in reg:
    reg["updated_round"] = "R522"
json.dump(reg, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("WROTE 行数", len(rows), "新增", added)
