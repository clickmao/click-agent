#!/usr/bin/env python3
"""R411 登记（幂等）: verification-registry 新行 + updated_round + TaskPlan 节点。

沿用 R410/R409 实测教训: ①插入行只能补「前一行逗号」，最后一行后不能加逗号；
②TaskPlan 是 1 空格缩进且 EOF 无换行 ⇒ 追加前断言「序列化参数逐字节复现原文件」。
"""
import json
import pathlib

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
REG = ROOT / "docs/verification-registry.json"
TP = ROOT / "docs/plans/v715_dev_plan.taskplan.json"
ROW_ID = "llamacpp.session.long_lived_generation"
NODE_ID = "dev-long-lived-generation"
DOCREF = "docs/plans/v0.33.0-r411-long-lived-generation-port.md"


def ensure_registry_row():
    src = REG.read_text(encoding="utf-8")
    data = json.loads(src)
    if any(r["id"] == ROW_ID for r in data["rows"]):
        print("[registry] 行已存在, 跳过")
        return
    row = {
        "id": ROW_ID,
        "capability": "本地生成**长驻**端口（补 R410 缺的第三条件）: 单例 LlamaCppTextGenerator 在进程内保活一个 llama-server 跨轮复用 + 逐轮喂本地 K2b 台账 LocalSessionCacheLedger（分母按本地引擎语义: 可复用上限 = 上一轮总长 + 上一轮生成，**不套远端 64 单元经验界**）+ **双条件判据**（携带复用率 ≥97% ∧ 前缀绝对长度 ≥4224）+ 口径独立对账钉死（tokens_evaluated = 总长，prompt_n = 重算数）",
        "level": "L4",
        "evidence_cmd": "AGENTFRAMEWORK_LLAMA_BIN=<llama-server> ./eval/rover/r411/run_e2e.sh && python3 eval/rover/r411/verify.py && python3 eval/rover/r411/semantics_probe.py && dotnet test src/agent.tests/agentframework.tests.csproj -c Release --filter FullyQualifiedName~LocalSessionCacheLedgerTests|FullyQualifiedName~LlamaCppPromptAccountingTests",
        "evidence_path": "eval/rover/r411/",
        "negative_control": "① 短前缀会话: 携带复用率 99.81% 达标但前缀 497 < 4224 ⇒ **必然判越线**（实测 exit 7，诊断点名绝对长度）—— 比值不是 KPI; ② 无 turns 请求 ⇒ 用法错 exit 2 且不 core dump（实测）; ③ 口径错（把 tokens_evaluated 当新评估数、总长再加 cache_n）⇒ 出现 >1 的物理不可能比率（单测机检 + 实测 1.0302）; ④ 命中 > 可复用上限 ⇒ 弃权记 -1，不出判决; ⑤ 命中未上报 ⇒ 记 Unknown(-1) **不判红**（缺失≠错误）; ⑥ 跨进程两次调用 ⇒ cache_n 归零（R410 实测，本端口不改变该性质）",
        "covers": [
            "src/agent.llamacpp/LlamaCppTextGenerator.cs",
            "src/agent.host/LlamaCppCommand.cs",
            "src/agent.modelqueue/LocalSessionCacheLedger.cs",
            "src/agent.tests/LocalSessionCacheLedgerTests.cs",
            "src/agent.tests/LlamaCppPromptAccountingTests.cs",
            "eval/rover/r411/",
        ],
        "owner_round": "R411",
    }
    block = "\n".join("    " + ln for ln in json.dumps(row, ensure_ascii=False, indent=2).splitlines())
    anchor = "  ],\n  \"aot_check_policy\""
    assert src.count(anchor) == 1, "rows 数组尾部锚点不唯一"
    tail = "\n    }\n" + anchor
    assert src.count(tail) == 1, "最后一行 row 的收尾锚点不唯一"
    src = src.replace(tail, "\n    },\n" + block + "\n" + anchor, 1)
    if '"updated_round": "R410"' in src:
        src = src.replace('"updated_round": "R410"', '"updated_round": "R411"', 1)
    after = json.loads(src)
    assert any(r["id"] == ROW_ID for r in after["rows"]), "插入后解析不到新行"
    assert len(after["rows"]) == len(data["rows"]) + 1, "行数不符"
    REG.write_text(src, encoding="utf-8")
    print(f"[registry] 已插入 {ROW_ID}, rows={len(after['rows'])}, updated_round={after['updated_round']}")


def ensure_taskplan_node():
    src = TP.read_text(encoding="utf-8")
    data = json.loads(src)
    nodes = data["Nodes"]
    if any(n["Id"] == NODE_ID for n in nodes):
        print("[taskplan] 节点已存在, 跳过")
        return
    assert json.dumps(data, ensure_ascii=False, indent=1) == src, "序列化参数无法复现原文件 ⇒ 改用文本插入"
    node = dict(nodes[-1])
    node["Id"] = NODE_ID
    node["Text"] = "R411 长驻生成端口 + 本地 K2b 台账（跨轮复用/口径换算/负控）"
    node["DocRef"] = DOCREF
    nodes.append(node)
    TP.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    after = json.loads(TP.read_text(encoding="utf-8"))
    assert after["Nodes"][-1]["Id"] == NODE_ID and len(after["Nodes"]) == len(nodes)
    print(f"[taskplan] 已追加节点 {NODE_ID}, Nodes={len(after['Nodes'])}, DocRef={DOCREF}")


ensure_registry_row()
ensure_taskplan_node()
