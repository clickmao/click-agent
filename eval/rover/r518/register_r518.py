#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R518 登记行写入 (幂等): 4 行 —— ② 节点预算自适应 / ②' 运行期缓存排除 / ③ 契约机检器 / ① 双包规模面对照。

形态纪律 (R507 铁律): 缩进/ensure_ascii 由「现盘文件」反解, 禁硬编码; instrument_sha12 由现盘文件实算。
"""
from __future__ import annotations
import hashlib, json, os, re, sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")


def sha12(rel):
    return hashlib.sha256(open(os.path.join(REPO, rel), "rb").read()).hexdigest()[:12]


def form_of(path):
    raw = open(path, "rb").read()
    head = raw[:4000].decode("utf-8", "replace")
    m = re.search(r"\n(\s+)\"", head)
    ind = len(m.group(1)) if m else 2
    return ind, not any(ord(c) > 127 for c in head)


ROWS = [
    {
        "id": "agent.node-budget-escalation",
        "level": "L3",
        "capability": (
            "编排节点**预算自适应** (R518): 远端节点因「零产物」被假绿防护判 Failed 时, 自动把单节点动作预算 "
            "翻倍重试 (上界 MaxNodeBudget=32, 次数上界 Options.MaxBudgetEscalations 0..3, **缺省 0 = 旧行为逐字不动**); "
            "仅 no_artifact 触发 (越界 out_of_scope / 抛异常**不**升预算, 不掩盖真失败), 仅远端 (本地执行器不升); "
            "重试前撤销同因记账 (同因只记一条); 遥测逐节点新增 BudgetSteps/Escalations/Attempts, 运行级新增 "
            "BudgetCeilingEffective/EscalationCount, 报告新增 budget_steps/escalations/attempts/"
            "budget_ceiling_effective/node_escalations_max/escalations_total。"
            "真机 liveness (AOT + adapter 真值 + deepseek-chat): n3 attempts=['6:Failed','12:Completed'] "
            "budget_steps 6→12 ⇒ 该次重试直接决定了 tasksvc 整包隐藏用例 12/12; 运行级预算上界 24→36, 升预算 2 次。"
        ),
        "covers": [
            "src/agent/intent/TaskOrchestrator.cs",
            "src/agent.host/OrchestrateCommand.cs",
            "src/agent.tests/TaskOrchestratorBudgetTests.cs",
            "eval/rover/r518/plan-p3p4-r518.txt",
            "eval/rover/r518/scope-p3p4-r518.txt",
            "eval/rover/r518/run_r518.sh",
            "eval/rover/r518/run_r518_orch.sh",
            "eval/rover/r518/evidence/orch-report-r518.json",
            "docs/reports/r518-mainline-scale-arm-and-node-budget-escalation.md",
        ],
        "evidence_cmd": ("R518_AGENT_BIN=/tmp/pub_r518b/agenthost R518_WINDOW=w2 bash eval/rover/r518/run_r518_orch.sh ; "
                         "python3 -c \"import json;d=json.load(open('eval/rover/r518/evidence/orch-report-r518.json'));"
                         "print(d['escalations_total'], d['budget_ceiling_effective'],[ (n['node_id'],n['attempts']) for n in d['nodes']])\""),
        "evidence_path": "eval/rover/r518/evidence/orch-report-r518.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r518/run_r518_orch.sh",
            "instrument_sha12": None,
            "binding": "audit-pin",
            "audited_by_round": "R518",
        },
        "negative_control": (
            "成对 (`src/agent.tests/TaskOrchestratorBudgetTests.cs` 12 例): ① 前态锚 —— 缺省 MaxBudgetEscalations=0 时"
            "零产物节点**只跑一次**且 Failed (旧行为逐字不动); ② 负控 —— 越界写入 (out_of_scope) **不**触发升预算"
            "(假失败不得被重试掩盖); ③ 有界 —— 恒零产物时调用次数恰为 1+上限, 且步数序列 [4,8] 不无界; "
            "④ 封顶 —— 20→32 (非 40); ⑤ 本地节点不升预算; ⑥ 同因违规只记一条 (重试前撤销记账)。"
        ),
        "owner_round": "R518",
    },
    {
        "id": "agent.workspace-runtime-cache-filter",
        "level": "L3",
        "capability": (
            "工作区**运行期缓存排除** (R518, 真机自抓缺陷修复): 节点按题面「写自测并运行」时解释器自动落 "
            "`__pycache__/*.pyc` ⇒ 旧快照差把它算成越界写入 ⇒ 整链 fail-closed (真实产物 cli.py 尚未写就被判死)。"
            "现在 Snapshot 只排除运行期自动生成的字节码/缓存 (路径段 `__pycache__`/`.pytest_cache`/`.mypy_cache`/"
            "`.ruff_cache`, 后缀 `.pyc`/`.pyo`); 源码与数据文件一律照旧纳入写范围契约。"
            "真机: 修复前 w2 首跑 n3 Failed(out_of_scope ×3 pyc) ⇒ 整包 0/12; 修复后同一计划 n3 Completed ⇒ tasksvc 12/12。"
        ),
        "covers": [
            "src/agent/intent/TaskOrchestrator.cs",
            "src/agent.tests/TaskOrchestratorCacheFilterTests.cs",
            "eval/rover/r518/evidence/orch-report-r518.json",
            "docs/reports/r518-mainline-scale-arm-and-node-budget-escalation.md",
        ],
        "evidence_cmd": ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "
                         "$HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Debug "
                         "--filter FullyQualifiedName~TaskOrchestratorCacheFilterTests"),
        "evidence_path": "eval/rover/r518/evidence/tests-full-r518.txt",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "src/agent.tests/TaskOrchestratorCacheFilterTests.cs",
            "instrument_sha12": None,
            "binding": "audit-pin",
            "audited_by_round": "R518",
        },
        "negative_control": (
            "4 例成对, 其中**负控 3 条**: ① 真实越界写 (kvsvc/server.py 落在 tasksvc 范围外) **仍**判 Failed 且点名路径, "
            "同一场景下的 pyc 不出现在违规清单 (排除不得变成整类豁免); ② **只有缓存写入**的节点仍算「零产物」⇒ Failed + "
            "no_artifact + 升预算重试 (缓存不得当产物顶包); ③ 裸 `.pyc` 后缀排除而普通文件 (`tasksvc/notes.md` 在文件级范围外) "
            "**仍**判越界。正控: 缓存 + 范围内真实产物 ⇒ Completed 且 NodeArtifacts 只含真实产物。"
        ),
        "owner_round": "R518",
    },
    {
        "id": "eval.plan-scope-contract-checker",
        "level": "L3",
        "capability": (
            "计划/写范围契约**起臂前机检器** (R518, 修 R517 事故: 范围文件被生成器二次覆盖含重复节点声明 ⇒ "
            "编排器起手 fail-closed rc=2 ⇒ 整臂零产物、整轮读数作废)。三件套: ① 镜像判据 "
            "(计划 P1-P10 字段/重复/未知依赖/位置/空文本/环; 范围 S1-S8 字段/重复声明/未知节点/空范围/绝对路径/上跳/兄弟重叠; "
            "H1 远端节点覆盖) ② **生成器生成即机检, 非法不落盘** + 落盘后回读再检 (原子替换, 不留半成品) "
            "③ 库内自检入口 `--check` (盘上文件复核, 起臂脚本硬前门)。夹具保真闸: 节点文本必须以题面原文结尾 (禁改写字符, 含 `|`) "
            "⇒ 生成器不得偷改题面。"
        ),
        "covers": [
            "eval/rover/r518/check_plan_contract.py",
            "eval/rover/r518/gen_plan_r518.py",
            "eval/rover/r518/build_taskset_r518.py",
            "eval/rover/r518/run_r518.sh",
            "eval/rover/r518/evidence/nc-contract-r518.json",
            "docs/reports/r518-mainline-scale-arm-and-node-budget-escalation.md",
        ],
        "evidence_cmd": ("python3 eval/rover/r518/check_plan_contract.py --plan eval/rover/r518/plan-p3p4-r518.txt "
                         "--scope eval/rover/r518/scope-p3p4-r518.txt --full-coverage --nc "
                         "--authority /tmp/pub_r518b/agenthost --out /tmp/r518/nc.json"),
        "evidence_path": "eval/rover/r518/evidence/nc-contract-r518.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r518/check_plan_contract.py",
            "instrument_sha12": None,
            "binding": "audit-pin",
            "audited_by_round": "R518",
        },
        "negative_control": (
            "12 条变异 × **双源** (镜像判据 ∧ 真二进制权威) 全绿: 每条变异镜像报红 **且** AOT `agent.host --orchestrate` "
            "在**校验期** rc=2 拒收 (validation_error=True, 工作区故意不存在 ⇒ 漏检会暴露为 workspace 错误 ⇒ 不可能误判 PASS); "
            "含 R517 事故本体 (S2 范围重复声明, 变异落在**数据行**而非注释行) 与 S5/S5b/S1/S4/S8/P2/P7/P4/P3/P9; "
            "变异有效性自检 (文本未变 ⇒ 判 FAIL, 防 NC 空转)。正控: 盘上真实计划/范围为 clean=True ⇒ PLAN_ON_DISK_CONTRACT_OK。"
        ),
        "owner_round": "R518",
    },
    {
        "id": "external.contrast-double-package-w2-r518",
        "level": "L3",
        "capability": (
            "主线对照 (R518, 窗口 w2 三臂同环境·同输入·同模型): 双包 p3 kvsvc(12 隐藏用例)+p4 v2 tasksvc(12) —— "
            "A 本侧单轮(默认预算) **24/24** 用例 · 远端调用 **13** · total **143,206** tok · 51.9 s; "
            "C codex 外部真值 21/24 · **36** 调用 · **501,207** tok · 128.7 s ⇒ 调用 ↓**63.9%**, total token ↓**71.4%**, "
            "新增 prompt ↓42.1%, 质量不降反升 (codex 在 p3 丢 3 条: incr_semantics_and_409/incr_concurrent_atomic/restart_drops_expired); "
            "O 编排臂 7 节点(5 远端+2 本地自测) 6/7 完成, tasksvc **12/12**、kvsvc 0/12 (q1 两次零产物)。"
            "**规模面结论 (反 R515 假设)**: 本侧单轮已覆盖双包 24 用例 ⇒ 「双包超出单轮硬顶」在此规模不成立, 编排器必要性本轮未证明。"
        ),
        "covers": [
            "eval/rover/r518/taskset-r518.json",
            "eval/rover/r518/prereg-r518.json",
            "eval/rover/r518/cases/p3_cases.py",
            "eval/rover/r518/cases/p4_cases.py",
            "eval/rover/r518/run_r518.sh",
            "eval/rover/r518/freeze_snapshot_r518.py",
            "eval/rover/r518/freeze_orch_r518.py",
            "eval/rover/r518/evidence/w2-aggregate-report.json",
            "eval/rover/r518/evidence/precondition-r518.json",
            "docs/reports/r518-mainline-scale-arm-and-node-budget-escalation.md",
        ],
        "evidence_cmd": ("R518_WINDOW=w2 bash eval/rover/r518/run_r518.sh ; "
                         "python3 eval/rover/r507pre/exec_precondition.py --round R518"),
        "evidence_path": "eval/rover/r518/evidence/precondition-r518.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r507pre/exec_precondition.py",
            "instrument_sha12": None,
            "binding": "audit-pin",
            "audited_by_round": "R518",
        },
        "negative_control": (
            "前置器 (铁律 11) `exec_precondition --round R518` **rc=1 ⇒ 本轮对比读数标「参考(未可验收)」** "
            "(要求面 w2/agentA 12/12+12/12 ✓ 但 w2/codex p3 仅 9/12 ✗, 而同一 p3 在 w1 跑次为 12/12 ⇒ 外部真值跨跑次方差); "
            "作废窗 w1 留痕不删 (臂 A 未 export AGENTFRAMEWORK_CONFIG ⇒ 绕过计量 adapter = 无读数; 编排臂 cwd 落在节点工作区内 "
            "⇒ 宿主自写 data/** 被判 out_of_scope ⇒ 链 fail-closed) ⇒ 全窗标 NONREQUIRED。两条自抓器具缺陷当轮修: "
            "范围模式语法 (`w2/agentA/*` → `w2/agentA`, 匹配键不含题号) 与 cwd 纪律。"
        ),
        "owner_round": "R518",
    },
]


def main() -> int:
    # R2e: pin_status=live 行**禁带** artifact_sha12 (仅 pin/repin 行可带) ⇒ 只钉器具 sha
    ROWS[0]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r518/run_r518_orch.sh")
    ROWS[1]["evidence_generated_with"]["instrument_sha12"] = sha12("src/agent.tests/TaskOrchestratorCacheFilterTests.cs")
    ROWS[2]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r518/check_plan_contract.py")
    ROWS[3]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r507pre/exec_precondition.py")
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
    d["updated_round"] = "R518"
    txt = json.dumps(d, ensure_ascii=ea, indent=ind)
    if not txt.endswith("\n"):
        txt += "\n"
    open(REG, "w", encoding="utf-8").write(txt)
    print(f"FORM ind={ind} ensure_ascii={ea} ROWS {before}->{len(rows)} added={added} updated={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
