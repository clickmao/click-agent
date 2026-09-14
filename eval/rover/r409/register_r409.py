#!/usr/bin/env python3
"""R409 登记 v3: verification-registry 新行 + updated_round + TaskPlan 节点（幂等）。
教训: ①只能补「前一行逗号」, 最后一行后不能加逗号; ②TaskPlan 是 1 空格缩进且 EOF 无换行 ——
追加前必须断言「序列化参数逐字节复现原文件」, 否则改为文本插入, 不得静默重排整份文件。"""
import json
import pathlib

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
REG = ROOT / "docs/verification-registry.json"
TP = ROOT / "docs/plans/v715_dev_plan.taskplan.json"
ROW_ID = "llamacpp.prompt.template_gate"
DOCREF = "docs/plans/v0.31.0-r409-local-prompt-template-gate.md"

ROW = {
    "id": ROW_ID,
    "capability": (
        "本地 prompt 模板闸门(结构性阻断手拼): 生成路径只接受由模型元数据内嵌 jinja 渲染的 prompt"
        "(POST /apply-template); 渲染产物字面含 BOS 或以 EOS 结尾一律判红; "
        "被使用计数 TemplateRenders/PromptGateRejections/LiteralPromptCalls"
    ),
    "level": "L4",
    "evidence_cmd": (
        "dotnet test src/agent.tests/agentframework.tests.csproj -c Release "
        "--filter FullyQualifiedName~LlamaCppPromptGateTests && "
        "agenthost --llamacpp --model <r1-q4km.gguf> --verify-template "
        '--chat-text "What is 12*12? Answer with the number." '
        "--prompt-file eval/rover/r409/prompt.txt --json eval/rover/r409/verify-template.json"
    ),
    "evidence_path": "eval/rover/r409/",
    "negative_control": (
        "① 96B 字面权串(含 BOS 文本)当渲染产物注入 ⇒ prompt_literal_special_token 判红; "
        "② 来源标 Literal(手拼) ⇒ prompt_not_templated 判红; ③ 以 EOS 文本结尾 ⇒ 判红; "
        "④ 空产物 ⇒ prompt_empty; ⑤ 反向防误拦: 多轮渲染含 EOS 轮分隔符、元数据 bos/eos 为 null 时必须判绿"
    ),
    "covers": [
        "src/agent.llamacpp/LocalPrompt.cs",
        "src/agent.llamacpp/LlamaCppProvider.cs",
        "src/agent.llamacpp/LlamaCppClient.cs",
        "src/agent.llamacpp/LlamaCppJson.cs",
        "src/agent.llamacpp/LlamaServerOptions.cs",
        "src/agent.host/LlamaCppCommand.cs",
        "src/agent.tests/LlamaCppPromptGateTests.cs",
    ],
    "owner_round": "R409",
}


def ensure_registry_row() -> None:
    src = REG.read_text(encoding="utf-8")
    before = json.loads(src)
    if any(r["id"] == ROW_ID for r in before["rows"]):
        print("[registry] 行已存在, 跳过")
        return
    block = json.dumps(ROW, ensure_ascii=False, indent=2)
    block = "\n".join("    " + ln for ln in block.splitlines())  # 基缩进 4, 字段落 6
    anchor = '\n    }\n  ],\n  "aot_check_policy"'
    assert src.count(anchor) == 1, "锚点不唯一"
    new = src.replace(anchor, "\n    },\n" + block + '\n  ],\n  "aot_check_policy"', 1)
    new = new.replace('"updated_round": "R408"', '"updated_round": "R409"', 1)
    after = json.loads(new)  # 先解析再落盘
    ids = [r["id"] for r in after["rows"]]
    assert len(ids) == len(before["rows"]) + 1 and len(set(ids)) == len(ids), "行数/唯一性异常"
    assert ids[-1] == ROW_ID and after["updated_round"] == "R409"
    REG.write_text(new, encoding="utf-8")
    print(f"[registry] rows {len(before['rows'])} -> {len(ids)}; updated_round={after['updated_round']}; 末行={ids[-1]}")


def ensure_taskplan_node() -> None:
    tp_src = TP.read_text(encoding="utf-8")
    tp = json.loads(tp_src)
    if any(n.get("DocRef") == DOCREF for n in tp["Nodes"]):
        print("[taskplan] 节点已存在, 跳过")
        return
    # 保真自检: 序列化参数必须逐字节复现原文件（含 EOF 无换行的特性）
    if json.dumps(tp, ensure_ascii=False, indent=1) != tp_src:
        raise SystemExit("[taskplan] 序列化参数不匹配 ⇒ 需改文本插入（拒绝静默重排）")
    node = dict(tp["Nodes"][-1])
    node["Id"] = "dev-local-prompt-template-gate"
    node["Text"] = "R409 本地 prompt 模板闸门(结构性阻断手拼)与 BOS 口径修正"
    node["DocRef"] = DOCREF
    tp["Nodes"].append(node)
    out = json.dumps(tp, ensure_ascii=False, indent=1)
    assert json.loads(out)["Nodes"][-1]["Id"] == "dev-local-prompt-template-gate"
    TP.write_text(out, encoding="utf-8")
    print(f"[taskplan] nodes {len(tp['Nodes'])-1} -> {len(tp['Nodes'])}; 末节点={node['Id']} -> {node['DocRef']}")


ensure_registry_row()
ensure_taskplan_node()
