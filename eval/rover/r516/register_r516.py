#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R516 登记行写入 (幂等): agent.node-artifact-scope-contract。

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
        "id": "agent.node-artifact-scope-contract",
        "level": "L3",
        "capability": (
            "节点产物契约 (R516): ① 节点成功**必须绑磁盘证据** —— 声明了写范围的节点若本次运行在工作区内"
            "无任何范围内增改文件 ⇒ 判 Failed「假绿防护」; ② 节点写范围契约为**机检**: 范围文件 DSL "
            "`nodeId | 路径[,路径]` (尾部 / = 目录前缀, * = 字面前缀通配, 段边界判定 ⇒ `out` 不匹配 `out2/x`), "
            "越界写 ⇒ 判 Failed 并逐条点名路径; ③ **同层 (会并发) 写范围重叠 ⇒ 宿主在建立 agent 之前 rc=2 拒收** "
            "(零 LLM 调用); ④ 产物归属由编排器快照差负责 (单一权威源, 宿主侧实现删除)。"
            "真机 E2E (AOT + adapter 真值 + 真模型 deepseek-chat): 5 臂 6 判据全绿 "
            "(RED 旧AOT 同计划无范围机制 / A5 前态锚 n3,n4 Completed∧0产物 / G1 零产物 ⇒ Failed+no_artifact / "
            "G2 真干活 ⇒ Completed+A out/hello.py / G3 越界 ⇒ Failed+out_of_scope / N 同层重叠 ⇒ rc=2 且 adapter 调用 24→24 零新增); "
            "单测 22/22 (新) · 全量 1706/1706 rc=0 · AOT IL_warnings=0 (15592688 B, sha12 b31af1d94da1)。"
        ),
        "covers": [
            "src/agent/intent/NodeScopeFile.cs",
            "src/agent/intent/TaskOrchestrator.cs",
            "src/agent.host/OrchestrateCommand.cs",
            "src/agent.tests/TaskOrchestratorScopeTests.cs",
            "eval/rover/r516/plan-red.txt",
            "eval/rover/r516/plan-write.txt",
            "eval/rover/r516/plan-outside.txt",
            "eval/rover/r516/plan-overlap.txt",
            "eval/rover/r516/scope-red.txt",
            "eval/rover/r516/scope-write.txt",
            "eval/rover/r516/scope-overlap.txt",
            "eval/rover/r516/run_scope_e2e.sh",
            "eval/rover/r516/check_r516.py",
            "docs/plans/v1.00.0-r516-node-scope-contract.md",
            "docs/reports/r516-node-artifact-scope-contract.md",
        ],
        "evidence_cmd": ("bash eval/rover/r516/run_scope_e2e.sh (R516_RUN_DIR=<DIR>) ; "
                         "python3 eval/rover/r516/check_r516.py --run-dir <DIR> --json <DIR>/verdict.json"),
        "evidence_path": "eval/rover/r516/evidence/verdict.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "archived-per-round",
            "artifact_sha12": None,
            "instrument": "eval/rover/r516/check_r516.py",
            "instrument_sha12": None,
            "binding": "audit-pin",
            "audited_by_round": "R516",
        },
        "negative_control": (
            "成对 (本轮真机实测, 同计划文件逐字节 md5 一致): ① RED 旧 AOT (R515 二进制) 对同一计划 rc=0 · "
            "节点 Completed · 报告**无 scope 字段** ⇒ 前态确实无机制; ② 前态锚 (冻结归档) "
            "`eval/rover/r515/evidence/report-orch-v2-12step.json` 中 n3 (5 ms) / n4 (178 ms) 均 Completed 且 0 产物 = 本轮要闭合的假绿现场; "
            "③ G2 正控: 真干活节点未被误杀 (Completed + A out/hello.py); ④ N 负控: 同层重叠 ⇒ rc=2 · 报告未生成 · "
            "adapter 调用 24→24 (零 LLM); ⑤ 判定器只读落盘产物 + 退出码, 无模型裁判。"
        ),
        "owner_round": "R516",
    },
]


def main() -> int:
    ROWS[0]["evidence_generated_with"]["instrument_sha12"] = sha12("eval/rover/r516/check_r516.py")
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
    d["updated_round"] = "R516"
    txt = json.dumps(d, ensure_ascii=ea, indent=ind)
    if not txt.endswith("\n"):
        txt += "\n"
    open(REG, "w", encoding="utf-8").write(txt)
    print(f"FORM ind={ind} ensure_ascii={ea} ROWS {before}->{len(rows)} added={added} updated={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
