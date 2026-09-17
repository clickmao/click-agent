#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R510 登记行写入 (幂等): frontend.task-progress-and-approval + mainline.selftest-clause-p3-ab。

形态纪律 (R507 铁律): 缩进/ensure_ascii 由「现盘文件」反解, 禁硬编码; 写入后立刻形式门禁。
"""
from __future__ import annotations
import json, os, re, sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")


def form_of(path):
    raw = open(path, "rb").read()
    head = raw[:4000].decode("utf-8", "replace")
    m = re.search(r"\n(\s+)\"", head)
    ind = len(m.group(1)) if m else 2
    ensure_ascii = not any(ord(c) > 127 for c in head)
    return ind, ensure_ascii


ROWS = [
    {
        "id": "frontend.task-progress-and-approval",
        "level": "L3",
        "capability": (
            "前端任务事件域第二段 (R510): task.progress 由**动作环真实步进**驱动 "
            "(ActionProgressObserver: AsyncLocal 绑定出站面, 未绑定零开销零副作用), 事件事实 = "
            "step_index/tool/ok/elapsed_ms, 文案面不在事件处二次实现; state.snapshot.tasks[] 同步 "
            "step_index/current_action; 审批通道由占位改**真实现** (approval.requested → 等 approval.respond → "
            "approval.responded 收口; 超时/拒绝/取消/被新审批覆盖一律不批准 = fail-closed); 路由 "
            "approval.respond 未知 id 显式 unknown_approval, 未挂接应答面回 channel_unavailable。"
            "本组件单测 10/10; AOT IL_warnings=0 (15,438,368 B, sha12 993d0fa548e9); 真机 E2E "
            "(AOT + frontend-api + 动作环开 + 真模型) 断言 A1–A6 全绿。"
        ),
        "covers": [
            "src/agent.modelqueue/ActionProgressObserver.cs",
            "src/agent.modelqueue/ActionLoop.cs",
            "src/agent.frontendapi/FrontendApiChatRouter.cs",
            "src/agent.frontendapi/FrontendPromptService.cs",
            "src/agent.frontendapi/ApprovalEnvelope.cs",
            "src/agent.frontendapi/FrontendEventHub.cs",
            "src/agent.host/Program.cs",
            "src/agent.tests/R510StepProgressAndApprovalTests.cs",
            "eval/rover/r510/probe_frontend_progress.py",
            "eval/rover/r510/assert_e2e_progress.py",
            "eval/rover/r510/run_e2e_frontend_progress.sh",
            "eval/rover/r510/evidence/frontend/e2e-assert.json",
        ],
        "evidence_cmd": "bash eval/rover/r510/run_e2e_frontend_progress.sh  (BIN=/tmp/pub_r510/agenthost)",
        "evidence_path": "eval/rover/r510/evidence/frontend/e2e-assert.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r510/assert_e2e_progress.py",
            "instrument_sha12": "4e85a8c9514c",
            "binding": "audit-pin",
            "audited_by_round": "R510",
        },
        "negative_control": (
            "本轮实测的负控/反伪造成对: ① A5 = 无待批审批时 approval.respond(apr-doesnotexist) 必须回 "
            "unknown_approval (静默当批准即判红, 实测命中该分支); ② A6 = 工作区真实出现 r510_progress.txt "
            "(禁止只信事件自报); ③ 单测: 观察者未绑定不得上报 (计数不变) / sink 抛异常必须计数且不得吞主链 / "
            "未知审批 id 拒收 / 二次应答 already_answered / 被新审批覆盖的旧请求必发 responded(superseded) 且结果不批准 / "
            "超时不予批准。"
        ),
        "owner_round": "R510",
    },
    {
        "id": "mainline.selftest-clause-p3-ab",
        "level": "L4",
        "capability": (
            "主线单点攻坚 (R510, 铁律 10): 「自检契约泛化」(SessionBaseline 二.3 增『契约承诺的每条非功能语义 —— "
            "重启后状态/持久化重放/并发原子性/过期清理 —— 要有独立用例, 只测主路径视为未自检』, 语言无关) 对 p3 "
            "隐藏用例 restart_drops_expired 的 A/B 读数 (同窗·同夹具 md5 8d13fd53…·同模型·每跑次独立 session, "
            "n=3/臂, 起手闸连续 2 PASS 才起臂, 预注册于起臂前): agentBefore (旧 AOT fe07205ba3b8) 1/3 全对 "
            "(24/36 用例, 靶点用例 1/3) vs agentAfter (新 AOT 993d0fa548e9) 3/3 全对 (36/36, 靶点用例 3/3); "
            "调用数 7.0 vs 7.0 持平; tokens/轮 91,252 vs 87,057 (adapter relay 真值, 标『参考（未可验收）』: "
            "exec_precondition rc=1)。机制归因**未成立**: after 臂 2/3 产物自带含 restart 自测, before 臂 1/3 "
            "(ab1 hits=4) 仍挂靶点用例 ⇒ 只记「条款+采样」共同结果, 不归因条款单独作用 (n=3)。"
        ),
        "covers": [
            "eval/rover/r510/run_ab_selftest_clause.sh",
            "eval/rover/r510/build_windows_r510.py",
            "eval/rover/r510/prereg-r510.json",
            "eval/rover/r510/taskset-r510.json",
            "eval/rover/r510/evidence/ab/ab-report.json",
            "eval/rover/r510/evidence/ab/hosts.json",
            "eval/rover/r510/evidence/ab/publish-r510.log.txt",
            "eval/rover/r507pre/precondition-r510.json",
            "docs/reports/r510-step-progress-and-approval-channel.md",
        ],
        "evidence_cmd": ("bash eval/rover/r510/run_ab_selftest_clause.sh ; "
                         "python3 eval/rover/r507pre/exec_precondition.py --round R510"),
        "evidence_path": "eval/rover/r507pre/precondition-r510.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r507pre/exec_precondition.py",
            "instrument_sha12": "cd2e864a87de",
            "binding": "audit-pin",
            "audited_by_round": "R510",
        },
        "negative_control": (
            "成对 (本轮实测): ① 正控 = 新 AOT 三窗全 12/12 rc=0 correct=True; ② 负控 = 注入缺陷（旧 AOT 无该条款）"
            "必失败且点名: r510ab1 11/12 rc=1 点名 restart_drops_expired, r510ab2 1/12 rc=1 点名 11 条 (含靶点), "
            "⇒ 判据器非空心 (面板全局 EXECUTABLE_AND_CORRECT=False, rc=1); ③ 自报 vs 机器复跑一致 "
            "SELF_REPORT_AGREES=True; ④ 起手闸单采样不可信 ⇒ 连续 2 PASS 才起臂 (gate-1/gate-2 落盘)。"
        ),
        "owner_round": "R510",
    },
]


def main() -> int:
    ind, ea = form_of(REG)
    d = json.load(open(REG, encoding="utf-8"))
    rows = d["rows"]
    before = len(rows)
    added, updated = [], []
    for r in ROWS:
        hit = [x for x in rows if x.get("id") == r["id"]]
        if hit:
            hit[0].update(r); updated.append(r["id"])
        else:
            rows.append(r); added.append(r["id"])
    d["updated_round"] = "R510"
    txt = json.dumps(d, ensure_ascii=ea, indent=ind)
    if not txt.endswith("\n"):
        txt += "\n"
    open(REG, "w", encoding="utf-8").write(txt)
    # 读回校验 (幂等 + 落盘非空)
    back = json.load(open(REG, encoding="utf-8"))
    got = [x["id"] for x in back["rows"] if x.get("owner_round") == "R510"]
    print(f"FORM ind={ind} ensure_ascii={ea} ROWS {before}->{len(back['rows'])} "
          f"added={added} updated={updated} readback_r510={got} updated_round={back['updated_round']}")
    return 0 if len(got) == 2 else 1


if __name__ == "__main__":
    sys.exit(main())
