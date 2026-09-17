#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R515 登记行写入 (幂等): agent.long-task-orchestrator + external.contrast-orchestrator-vs-single-turn。

形态纪律 (R507 铁律): 缩进/ensure_ascii 由「现盘文件」反解, 禁硬编码; instrument_sha12 由现盘文件实算。
"""
from __future__ import annotations
import hashlib, json, os, re, sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")


def sha12(rel):
    p = os.path.join(REPO, rel)
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def form_of(path):
    raw = open(path, "rb").read()
    head = raw[:4000].decode("utf-8", "replace")
    m = re.search(r"\n(\s+)\"", head)
    ind = len(m.group(1)) if m else 2
    return ind, not any(ord(c) > 127 for c in head)


ROWS = [
    {
        "id": "agent.long-task-orchestrator",
        "level": "L3",
        "capability": (
            "长任务编排器 V1 (R515): 把「节点」提升为一次真实执行单元 —— 远端节点由宿主注入真实 agent 轮次 "
            "(每节点独立 AGENTFRAMEWORK_ACTION_MAX_STEPS ⇒ 总步数 = 节点数 × 单节点预算, 突破单次动作环 6/32 封顶), "
            "本地节点走零 LLM 子进程执行器 (python.selftest), 同层本地/远端并发 (墙钟重叠 85/127/178 ms 实测), "
            "逐节点产物归属 (工作区快照差分: n1→tasksvc/__init__.py+store.py / n2→model.py / n3→cli.py), "
            "预算上界 BudgetCeiling 机读 (18/36 步), 检查点复用 TaskPlanExecutor, 计划文件 DSL + fail-closed 校验 "
            "(字段数/id 唯一/依赖存在/成环/local 无执行器/remote 带执行器/空计划), 计划事件 plan.node。 "
            "真机 E2E (AOT + adapter 真值 + 真模型): 4/4 节点 Completed, RC=0; 单测 21/21; 全量 1684/1684; "
            "AOT IL_warnings=0 (15,555,120 B, sha12 a32116b4d373b8c0)。 "
            "本轮修掉两个真实缺陷: ① 远端节点必须先 InitializeAsync (否则 Failed: Agent is not in ready state) "
            "② 同层并发 + 全契约提示词 ⇒ 双写者互相覆盖 (v1 3/12) ⇒ v2 改串行依赖 + 硬文件范围 + 契约按规则切分。"
        ),
        "covers": [
            "src/agent/intent/TaskOrchestrator.cs",
            "src/agent/intent/TaskPlanFile.cs",
            "src/agent.host/OrchestrateCommand.cs",
            "src/agent.host/Program.cs",
            "src/agent.tests/TaskOrchestratorTests.cs",
            "eval/rover/r515/plan-p4.txt",
            "eval/rover/r515/plan-p4-v2.txt",
            "eval/rover/r515/plan-p3p4.txt",
            "eval/rover/r515/run_orchestrator_e2e.sh",
            "eval/rover/r515/run_scale_e2e.sh",
            "eval/rover/r515/prereg-r515.json",
            "eval/rover/r515/evidence/report-orch-v2-6step.json",
            "eval/rover/r515/evidence/report-orch-v1-6step.json",
            "eval/rover/r515/evidence/report-orch-v2-12step.json",
            "docs/plans/v0.99.0-r515-long-task-orchestrator.md",
            "docs/reports/r515-long-task-orchestrator.md",
        ],
        "evidence_cmd": ("bash eval/rover/r515/run_orchestrator_e2e.sh  (R515_AGENT_BIN=/tmp/pub_r515/agenthost "
                         "R515_PLAN=eval/rover/r515/plan-p4-v2.txt) ; python3 eval/rover/r515/summarize_r515.py --run-dir DIR"),
        "evidence_path": "eval/rover/r515/evidence/report-orch-v2-6step.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r515/summarize_r515.py",
            "instrument_sha12": None,
            "binding": "audit-pin",
            "audited_by_round": "R515",
        },
        "negative_control": (
            "成对 (本轮实测): ① v1 计划 (同层双写者 + 全契约) ⇒ 3/12, 产物归属显示 n1/n2 各写整包 (互相覆盖) —— 计划形态错即判红; "
            "② 缺 InitializeAsync ⇒ 全部远端节点 Failed (Agent is not in ready state), 首跑 0/12 (已作废); "
            "③ 非法计划 fail-closed: 字段数不足/缺节点 ⇒ rc=2 (实测 rc=2 两次); "
            "④ **已知假绿未修**: 每节点 12 步跑次 n3 5 ms 完成、0 产物却记 Completed ⇒ 节点成功判据尚未绑磁盘证据 (下轮必修, 该跑次不作机制证据)。"
        ),
        "owner_round": "R515",
    },
    {
        "id": "external.contrast-orchestrator-vs-single-turn",
        "level": "L3",
        "capability": (
            "编排器 vs 单轮同窗对照 (R515, p4 题面 v2 逐字节同输入, adapter 落盘 usage 真值, 同模型 deepseek-chat): "
            "single 6 步 12/12 (6 调用/69,070 tok, 10:43) → single 6 步 4/12 (6 调用/70,052 tok, 10:48) → "
            "single 12 步 4/12 (12 调用/253,809 tok, 10:52); orch v1 3/12 (57 调用/280,083 tok) → "
            "orch v2 (串行+硬文件范围+契约切分) 9/12 (16 调用/331,586 tok, 10:48) → orch v2 每节点 12 步 0/12 (23 调用/454,208 tok, 假绿)。 "
            "判据机检: C1 PASS · C3 PASS (仅 10:48 窗 9>4) · C4 PASS (重叠 85/127/178 ms) · C5 PASS (18/36 步) · "
            "C6 PASS (归属干净) · **C2 FAIL (最好 9/12 ⇒ 铁律 11 前置未满足)**。 "
            "结论: 机制打通且首次在同窗内以 9/12 > 4/12 超过单轮臂; 但同臂跨跑次摆动 12/12↔4/12 ⇒ 单跑次不可判优劣, "
            "4 节点/636 行题面不足以稳定判别编排必要性 ⇒ 需规模臂 (双包 24 用例, 已入仓未跑)。"
        ),
        "covers": [
            "eval/rover/r515/prereg-r515.json",
            "eval/rover/r515/summarize_r515.py",
            "eval/rover/r515/evidence/summary-v1-6step.txt",
            "eval/rover/r515/evidence/summary-v2-6step.txt",
            "eval/rover/r515/evidence/summary-v2-12step.txt",
            "eval/rover/r515/evidence/grade-single-6step-a.json",
            "eval/rover/r515/evidence/grade-single-6step-b.json",
            "eval/rover/r515/evidence/grade-single-12step.json",
            "eval/rover/r515/evidence/grade-orch-v2-6step.json",
            "eval/rover/r515/evidence/grade-orch-v2-12step.json",
            "eval/rover/r515/evidence/fixture.json",
            "eval/rover/r515/evidence/gate.json",
            "docs/reports/r515-long-task-orchestrator.md",
        ],
        "evidence_cmd": ("bash eval/rover/r515/run_orchestrator_e2e.sh (plan-p4-v2.txt) ; "
                         "python3 eval/rover/r511/grade_r511.py --task p4 --dir <副本> --json grade.json"),
        "evidence_path": "eval/rover/r515/evidence/summary-v2-6step.txt",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r511/grade_r511.py",
            "instrument_sha12": None,
            "binding": "audit-pin",
            "audited_by_round": "R515",
        },
        "negative_control": (
            "成对 (本轮实测): ① 判分只判副本 (R512 教训) + 每臂独立 session (R509 铁律); "
            "② 起手闸首跑 GATE_BLOCKED (mem_available_mb=2610 < 2650) ⇒ 不起臂, 已作废; 后续连续 2 次 PASS (2929/2782) 才起臂; "
            "③ 同臂同输入跨跑次 12/12↔4/12 ⇒ 单跑次禁作判据; ④ 与 R511/R512/R513 窗口题面版本不同 ⇒ 禁相减; "
            "⑤ 规模臂未跑 ⇒ 不作读数 (禁未跑充数)。"
        ),
        "owner_round": "R515",
    },
]


def main() -> int:
    ROWS[0]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r515/summarize_r515.py")
    ROWS[1]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r511/grade_r511.py")
    ind, ea = form_of(REG)
    d = json.load(open(REG, encoding="utf-8"))
    rows = d["rows"]
    before = len(rows)
    added, updated = [], []
    for r in ROWS:
        hit = [x for x in rows if x.get("id") == r["id"]]
        if hit:
            hit[0].update(r)
            updated.append(r["id"])
        else:
            rows.append(r)
            added.append(r["id"])
    d["updated_round"] = "R515"
    txt = json.dumps(d, ensure_ascii=ea, indent=ind)
    if not txt.endswith("\n"):
        txt += "\n"
    open(REG, "w", encoding="utf-8").write(txt)
    print(f"FORM ind={ind} ensure_ascii={ea} ROWS {before}->{len(rows)} added={added} updated={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
