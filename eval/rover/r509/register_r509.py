#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R509 登记行写入 (幂等): external.contrast-repeat-arms + frontend.task-events。

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
        "id": "external.contrast-repeat-arms",
        "level": "L3",
        "capability": ("同题重复臂对照 codex-cli 外部真值 (R509): p3 线程安全 KV+TTL+WAL 包, 每跑次独立会话 "
                       "(--arm <arm>-r<N> ⇒ session-id 唯一), n=3/臂; 判分吃 12 条隐藏用例真实行为 (铁律11)。"
                       "有效读数: 默认预算臂 2/3 整题全对 (35/36 用例, tokens 72831/80995/90167, 7 调用, 25.9s) vs "
                       "显式 3 步臂 0/3 全对 (22/36, 36207/39918/41941, 4 调用, 20.7s) vs codex n=2 2/2 全对 "
                       "(24/24, 104920/445211/785501, 24 调用, 69.3s) ⇒ token −81.8% / 调用 −70.8% / 墙钟 −62.6% (均值比); "
                       "跨轮不稳用例唯一 = restart_drops_expired (本侧 3/6 跑次失败, codex 0/2)。"),
        "covers": [
            "eval/rover/r509/run_repeats_fresh.sh",
            "eval/rover/r509/rerun_agent_arms.sh",
            "eval/rover/r509/aggregate_repeats_r509.py",
            "eval/rover/r509/evidence/repeat-arms/report-window-c.json",
            "eval/rover/r509/evidence/repeat-arms/report-window-b.json",
            "docs/reports/r509-repeat-arms-and-frontend-task-events.md",
        ],
        "evidence_cmd": ("bash eval/rover/r509/run_repeats_fresh.sh  (D=... PORT=... REPS=3 TASKS=p3) ; "
                         "python3 eval/rover/r509/aggregate_repeats_r509.py --run-dir DIR --tasks p3 --reps 3"),
        "evidence_path": "eval/rover/r509/evidence/repeat-arms/report-window-c.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r509/aggregate_repeats_r509.py",
            "instrument_sha12": "5e23ca994422",
            "binding": "audit-pin",
            "audited_by_round": "R509",
        },
        "negative_control": ("成对: ① 正控 = 参考解 12/12 (nc_r508 内建, 否则 NC_HOLLOW 弃权); "
                            "② 本轮实测的两处仪器假红/假绿 —— (a) cfg 嵌套 (mkdir 先造 $D/agent/cfg ⇒ cp 嵌套) 使全臂 "
                            "0 调用 (reply=模型目录为空), (b) 共享 session-id 使首跑继承前窗失败态 ⇒ 0/12 假失败; "
                            "两者均已定位修复 (形态守卫 base/models.yaml + 每跑次独立会话), 修复前后读数分列。"),
        "owner_round": "R509",
    },
    {
        "id": "frontend.task-events",
        "level": "L2",
        "capability": ("前端任务事件域 (路线 A 实施, 对标 codex 展示面): task.started / task.completed / task.failed "
                       "+ state.snapshot.tasks[] + chat.send 响应增量 task_id; 会话 id 可注入 "
                       "(AGENTFRAMEWORK_FRONTEND_SESSION, 默认 frontend-main 不破)。异常路径显式 task.failed 且快照 state=failed "
                       "(不会永远 running)。单测 7/7; 全量套件 1643/1643; AOT IL_warnings=0 (15,425,840 B, sha12 4087c90c4786); "
                       "真机 E2E 断言 A1–A8 全绿 (回复=真答)。"),
        "covers": [
            "src/agent.frontendapi/FrontendTaskEvents.cs",
            "src/agent.frontendapi/FrontendApiChatRouter.cs",
            "src/agent.host/Program.cs",
            "src/agent.tests/FrontendTaskEventsTests.cs",
            "eval/rover/r509/probe_frontend_tasks.py",
            "eval/rover/r509/assert_e2e_tasks.py",
            "eval/rover/r509/run_e2e_frontend_tasks.sh",
            "eval/rover/r509/evidence/frontend/e2e-assert.json",
        ],
        "evidence_cmd": "bash eval/rover/r509/run_e2e_frontend_tasks.sh  (BIN=/tmp/pub_r509b/agenthost)",
        "evidence_path": "eval/rover/r509/evidence/frontend/e2e-assert.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r509/assert_e2e_tasks.py",
            "instrument_sha12": "855f6726113c",
            "binding": "audit-pin",
            "audited_by_round": "R509",
        },
        "negative_control": ("A7 负控实测命中 (本轮): 共享 frontend-main 会话 ⇒ 事件面全绿但回复是上一轮续跑追问 "
                            "(0.01s 无模型调用) ⇒ 新增 A7「回复必须是真答 (含答数)」+ A8「响应 ok=true」后判红, 修隔离后转绿; "
                            "A6 事件载荷路径泄漏判红; 单测覆盖未知 task_id 拒绝 + 终态幂等不覆盖。"),
        "owner_round": "R509",
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
    d["updated_round"] = "R509"
    txt = json.dumps(d, ensure_ascii=ea, indent=ind)
    if not txt.endswith("\n"):
        txt += "\n"
    open(REG, "w", encoding="utf-8").write(txt)
    print(f"FORM ind={ind} ensure_ascii={ea} ROWS {before}->{len(rows)} added={added} updated={updated}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
