#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R511 登记行写入 (幂等): external.contrast-scale-boundary + action.delete-file-approval。

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
        "id": "external.contrast-scale-boundary",
        "level": "L3",
        "capability": (
            "规模探界 (R511): 同环境·同输入·同模型 (deepseek-chat), 单变量 = 步数预算 (默认 6 vs 显式 12); "
            "p3 逐字节复用 R508 题面 (sha efa48cb2ccef) + 新题 p4 (tasksvc 3 文件/636 行目标); 每跑次独立 session; "
            "起手闸连续 2 PASS; 窗口体检 56 调用 / unreported_usage=0 / 无『空正文且无 tool_calls』异常。"
            "读数: dflt 4/4 跑次整题全对 0 (6/6 步用尽, 落盘 2-3 文件), tokens/臂 137,004 · 133,747; "
            "s12 2/4 全对 (p4 12/12 636 行 步 11/12; p3 12/12 738 行 步 7/12), 另 1/4 跑次为模型『口述不落盘』"
            "(0 工具调用/0 文件), tokens/臂 168,237 · 169,539 ⇒ **上限由步数预算决定, 非模型能力**。"
            "跨窗同题 p3: R509 默认 2/3 (35/36) → R510 after 3/3 (36/36) → R511 dflt 0/2 (0/24) ⇒ 窗口摆动 > 臂间差异。"
        ),
        "covers": [
            "eval/rover/r511/taskset-r511.json",
            "eval/rover/r511/run_r511.sh",
            "eval/rover/r511/proj_run_side.py",
            "eval/rover/r511/aggregate_r511.py",
            "eval/rover/r511/grade_r511.py",
            "eval/rover/r511/cases/p4_cases.py",
            "eval/rover/r511/ref/p4/tasksvc/cli.py",
            "eval/rover/r511/ref/p4/tasksvc/store.py",
            "eval/rover/r511/ref/p4/tasksvc/model.py",
            "eval/rover/r511/evidence/report.json",
            "eval/rover/r511/evidence/window.json",
            "eval/rover/r511/evidence/nc-cases.txt",
            "docs/reports/r511-scale-boundary-and-delete-approval.md",
        ],
        "evidence_cmd": ("bash eval/rover/r511/run_r511.sh  (R511_AGENT_BIN=/tmp/pub_r511/agenthost R511_RUN_DIR=...) ; "
                         "python3 eval/rover/r511/aggregate_r511.py --run-dir DIR --json report.json"),
        "evidence_path": "eval/rover/r511/evidence/report.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r511/aggregate_r511.py",
            "instrument_sha12": None,  # 运行时实算
            "binding": "audit-pin",
            "audited_by_round": "R511",
        },
        "negative_control": (
            "成对 (本轮实测, evidence/nc-cases.txt): ① 正控 = 参考解 12/12 PASS (REFCTL_RC=0); "
            "② 三突变体全部判红且点名不重叠 —— 忽略 --now ⇒ 11/12 红; 非原子写 (原地重写) ⇒ **精确点名 no_temp_residue**"
            "(inode 未变); id 复用 ⇒ 点名 expire_removes_expired_tasks + list_filter_and_order ⇒ 判据器非空心。"
            "③ 探索性轮次未落盘预注册 (与 R509/R510 的 A/B 轮不同) ⇒ 数字只作探索读数。"
        ),
        "owner_round": "R511",
    },
    {
        "id": "action.delete-file-approval",
        "level": "L4",
        "capability": (
            "第 5 个工具 delete_file + 人工审批 fail-closed 真机闭环 (R511): 声明面与 Names 同源 "
            "(ActionToolDecl.DeleteFile; ToolsJson/ActionToolSpec 双侧同步), 执行面 WorkspaceActionPort.DeleteFileAsync "
            "= 边界解析 → 审批门 → 真删; 审批门未注入 ⇒ 一律拒绝 (ApprovalUnavailableExitCode=125), 审批拒绝/超时/取消/异常 "
            "⇒ 未执行 (ApprovalDeniedExitCode=124); 宿主 DI 把 IUserPromptService 接到审批门。"
            "单测 10/10; 全量 1663/1663; AOT IL_warnings=0 (15,467,520 B, sha12 139ac3bc986b1b03); "
            "真机 E2E (AOT + frontend-api + 真链真模型) E2E_APPROVAL_VERDICT=PASS 10/10: "
            "approve 臂磁盘证据 victim 文件真被删 (exists=False), deny 臂文件原封不动 (exists=True), "
            "approval.requested{kind=DeleteFile} → approval.responded{approved,answered_by=RealUser|Denied} 同 id 往返。"
        ),
        "covers": [
            "src/agent/action/WorkspaceActionPort.cs",
            "src/agent.modelqueue/ActionLoop.cs",
            "src/agent.modelqueue/ActionToolSpec.cs",
            "src/agent/extensions/ServiceCollectionExtensions.cs",
            "src/agent.tests/R511DeleteToolApprovalTests.cs",
            "src/agent.tests/ActionLoopTests.cs",
            "eval/rover/r511/probe_frontend_approval.py",
            "eval/rover/r511/assert_e2e_approval.py",
            "eval/rover/r511/run_e2e_approval.sh",
            "eval/rover/r511/evidence/e2e/approve.json",
            "eval/rover/r511/evidence/e2e/deny.json",
            "eval/rover/r511/evidence/e2e/e2e-assert.json",
        ],
        "evidence_cmd": "bash eval/rover/r511/run_e2e_approval.sh  (BIN=/tmp/pub_r511/agenthost)",
        "evidence_path": "eval/rover/r511/evidence/e2e/e2e-assert.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r511/assert_e2e_approval.py",
            "instrument_sha12": None,  # 运行时实算
            "binding": "audit-pin",
            "audited_by_round": "R511",
        },
        "negative_control": (
            "成对 (本轮实测): ① 未注入审批门 ⇒ delete_file 拒绝 (单测, 文件完好); ② 审批拒绝臂 (真机) ⇒ "
            "approval.responded{approved=false,answered_by=Denied} 且 victim 文件仍在 (exists=True) —— fail-closed 落地; "
            "③ 越界路径 (../) 在送审批门**之前**被边界拒绝 (单测断言审批门未被调用); ④ A7 沿用 R509 铁律: 回复必须真答 "
            "(approve 臂 5.62s / reply_len=15), 排除 0.01s 陈旧续跑假绿。"
        ),
        "owner_round": "R511",
    },
]


def main() -> int:
    ROWS[0]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r511/aggregate_r511.py")
    ROWS[1]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r511/assert_e2e_approval.py")
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
    d["updated_round"] = "R511"
    txt = json.dumps(d, ensure_ascii=ea, indent=ind)
    if not txt.endswith("\n"):
        txt += "\n"
    open(REG, "w", encoding="utf-8").write(txt)
    print(f"FORM ind={ind} ensure_ascii={ea} ROWS {before}->{len(rows)} added={added} updated={updated}")
    print("INSTR_SHA12", ROWS[0]["evidence_generated_with"]["instrument_sha12"],
          ROWS[1]["evidence_generated_with"]["instrument_sha12"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
