#!/usr/bin/env python3
"""R410 登记（幂等）: verification-registry 新行 + updated_round + TaskPlan 节点。
教训（R409 实测）: ①插入行只能补「前一行逗号」，最后一行后不能加逗号；②TaskPlan 是 1 空格缩进
且 EOF 无换行 ⇒ 追加前断言「序列化参数逐字节复现原文件」，否则改为文本插入，不得静默重排。"""
import json
import pathlib

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
REG = ROOT / "docs/verification-registry.json"
TP = ROOT / "docs/plans/v715_dev_plan.taskplan.json"
ROW_ID = "llamacpp.session.prefix_reuse"
NODE_ID = "dev-session-prefix-reuse"
DOCREF = "docs/plans/v0.32.0-r410-session-prefix-reuse.md"


def ensure_registry_row():
    src = REG.read_text(encoding="utf-8")
    data = json.loads(src)
    if any(r["id"] == ROW_ID for r in data["rows"]):
        print("[registry] 行已存在, 跳过")
    else:
        row = {
            "id": ROW_ID,
            "capability": "本地生成的 K2b 前缀复用: 口径分离(Session 开 cache_prompt / Reconciliation 关) + 服务端 cache_n 记账 + 会话长前缀入口(--system-file) + 静默失效计数 SessionCacheMisses",
            "level": "L4",
            "evidence_cmd": "python3 eval/rover/r410/prefix_reuse_probe.py && agenthost --llamacpp --model <r1-q4km.gguf> --chat-text \"2+2=?\" --system-file eval/rover/r410/session-prefix.txt --reuse on --json eval/rover/r410/e2e-reuse-run1.json && dotnet test src/agent.tests/agentframework.tests.csproj -c Release --filter FullyQualifiedName~CompletionReuseTests",
            "evidence_path": "eval/rover/r410/",
            "negative_control": "① 前缀首 token 改变 ⇒ cache_n 必须归零(实测 0); ② cache_prompt=false ⇒ cache_n 恒 0(实测 0); ③ Reconciliation 口径映射必须关缓存、Session 必须开(单测负控); ④ 短独立 prompt 绝对复用 17 token << 4224 红线(结构不达标); ⑤ 跨进程(每次新起 server) ⇒ 复用 0% 且 SessionCacheMisses=1",
            "covers": [
                "src/agent.llamacpp/CompletionProfiles.cs",
                "src/agent.llamacpp/LlamaCppProvider.cs",
                "src/agent.llamacpp/LlamaCppClient.cs",
                "src/agent.llamacpp/LlamaCppJson.cs",
                "src/agent.host/LlamaCppCommand.cs",
                "src/agent.tests/CompletionReuseTests.cs",
                "eval/rover/r410/prefix-reuse.json",
            ],
            "owner_round": "R410",
        }
        block = "\n".join("    " + ln for ln in json.dumps(row, ensure_ascii=False, indent=2).splitlines())
        anchor = "  ],\n  \"aot_check_policy\""
        assert src.count(anchor) == 1, "rows 数组尾部锚点不唯一"
        tail = "\n    }\n" + anchor
        assert src.count(tail) == 1, "最后一行 row 的收尾锚点不唯一"
        src = src.replace(tail, "\n    },\n" + block + "\n" + anchor, 1)
        if '"updated_round": "R409"' in src:
            src = src.replace('"updated_round": "R409"', '"updated_round": "R410"', 1)
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
    node["Text"] = "R410 会话长前缀复用: 口径分离 + cache_n 记账 + 静默失效计数"
    node["DocRef"] = DOCREF
    nodes.append(node)
    TP.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    after = json.loads(TP.read_text(encoding="utf-8"))
    assert after["Nodes"][-1]["Id"] == NODE_ID and len(after["Nodes"]) == len(nodes)
    print(f"[taskplan] 已追加节点 {NODE_ID}, Nodes={len(after['Nodes'])}, DocRef={DOCREF}")


ensure_registry_row()
ensure_taskplan_node()
