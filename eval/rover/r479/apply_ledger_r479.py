#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R479 台账机派生刷新 (幂等): registry 3 行 + taskplan 1 节点; --check 只校验不写。

纪律:
  · 写入后立即回读并逐行断言形态 (id/level/capability/evidence_cmd/evidence_path/owner_round/covers 纯路径);
  · 保留原文缩进风格 (indent=1, ensure_ascii=False);
  · 缺真值文件 ⇒ 直接判红 (fail-closed), 不静默跳过。
"""
import hashlib
import json
import os
import sys

BASE = "/home/agentuser/AgentFramework"
REG = os.path.join(BASE, "docs/verification-registry.json")
TASK = os.path.join(BASE, "docs/plans/v715_dev_plan.taskplan.json")
R479 = os.path.join(BASE, "eval/rover/r479")
PLAN = "docs/plans/v0.95.0-r479-responses-wire-and-typed-semantics.md"
CHECK = "eval/rover/r479/check_r479.py"
VERDICT = "eval/rover/r479/verdict-r479.json"
APPLY = "--check" not in sys.argv


def sha12(rel):
    h = hashlib.sha256(open(os.path.join(BASE, rel), "rb").read()).hexdigest()
    return h[:12]


def ev():
    return {
        "evidence_kind": "artifact",
        "pin_status": "live",
        "pin_reason": "worktree-only",
        "artifact_sha12": None,
        "instrument": CHECK,
        "instrument_sha12": sha12(CHECK),
        "binding": "audit-pin",
        "audited_by_round": "R479",
    }


ROWS = [
    {
        "id": "r479.responses-io-wire",
        "level": "L2",
        "capability": (
            "真实 I/O 数据格式按 **Responses 协议** 落成 typed 面(`src/agent.modelqueue/ResponsesWire.cs`): "
            "① **字段分离** —— `instructions`(本地指示/权限类)与 `input[]`(用户输入)是**两个独立顶层字段**, 不再靠"
            "「传输的是 JSON」冒充结构化语义; ② 输入项 typed(`message` / `function_call_output`), 工具结果**独立成项**"
            "而非拼进 user 文本; ③ 请求手写 JSON(零反射/AOT), 恒带 `store:false`(无状态 ⇒ 前缀仍在我方可控面), "
            "可选 `prompt_cache_key`/`max_output_tokens`; ④ 解析用 `JsonDocument`(零反射), 未上报 usage **不等于 0**"
            "(`Present`/`CachedPresent` 双旗标, `NewTokens` 仅在两侧齐备时可得); ⑤ fail-closed: 不可解析 / 无状态无输出 / "
            "output 全为未知类型 ⇒ `Failure` 非空, 未知 item 计数不静默丢弃。"
            "真机: 本地 llama.cpp `/v1/responses` 200(cached 0→67/68), 远端 DeepSeek `/responses` 200。"
        ),
        "evidence_cmd": "python3 eval/rover/r479/check_r479.py",
        "evidence_path": VERDICT,
        "evidence_generated_with": ev(),
        "negative_control": (
            "NC1 用户任务文本若出现在 `instructions` 内 ⇒ 判红; NC2 请求体出现 `store:true` ⇒ 判红; "
            "NC3 请求体带 UTF-8 BOM ⇒ 判红; C1/C5 为源码派生断言(缺字段即红), C2 真机三读数(本地 answer/本地 tool/远端 answer) "
            "缺一即 FAIL —— 禁以推断代替读数。**不含**: 路由器接线(默认通道未变)。"
        ),
        "covers": [
            "src/agent.modelqueue/ResponsesWire.cs",
            "src/agent.tests/ResponsesWireTests.cs",
            CHECK,
        ],
        "owner_round": "R479",
    },
    {
        "id": "r479.local-decision-calibration",
        "level": "L2",
        "capability": (
            "**精准语义 = 校准 LLM 返回后本地该做什么的单一出口**(`src/agent.modelqueue/LocalDecisionMap.cs`): "
            "`FromResponses(result, actionLoopEnabled) -> LocalDecision{Action, Text, ToolCalls, Cause, Retryable, Banner, Reason}`; "
            "**本地 LLM 与远端 LLM 同用这一个函数**(协议同形 ⇒ 语义同一, 不为本地另立判据)。规则只取协议字段且顺序即优先级: "
            "Failure⇒Fatal; 工具调用>0 ⇒ 动作环开=`RunTools` / 关=`VisibleFailure(ToolCall, 禁重试)`; "
            "`completed`∧正文非空=`Answer`; `incomplete`∧`max_output_tokens`=`Retry(LengthExhausted)`; "
            "`completed`∧空正文=`VisibleFailure(UpstreamStop)`; 其余=`VisibleFailure(Unknown)`(fail-closed 禁猜)。"
            "失效文案**单源** `EmptyBodyDiagnosis.Banner`(本类 4 处调用、0 处自写字面量)。"
        ),
        "evidence_cmd": "python3 eval/rover/r479/check_r479.py",
        "evidence_path": VERDICT,
        "evidence_generated_with": ev(),
        "negative_control": (
            "C3 机检: 校准面 `EmptyBodyDiagnosis.Banner(` 调用 >=4 ∧ 失效文案字面量 = 0(出现第二处文案实现即红); "
            "单测 `F1`(`R479_E2E_DIR` 真机证据回放): 本地 3B 真机 `function_call` ⇒ 必须判 `RunTools`; "
            "远端真机 `incomplete/max_output_tokens` ⇒ 必须判 `Retry`; "
            "缺真机证据文件 ⇒ 该断言不判(禁伪造)—— 单测 `F1` 与环境变量 `R479_E2E_DIR` 绑定, 无证据时不冒充通过。"
        ),
        "covers": [
            "src/agent.modelqueue/LocalDecisionMap.cs",
            "src/agent.modelqueue/EmptyBodyDiagnosis.cs",
            "src/agent.tests/ResponsesWireTests.cs",
        ],
        "owner_round": "R479",
    },
    {
        "id": "r479.tool-decl-single-source",
        "level": "L3",
        "capability": (
            "工具声明面**单一事实源**(`src/agent.modelqueue/ActionToolSpec.cs`): 一份规格派生两种线格式 —— "
            "chat 嵌套形态与现有 `ActionToolDecl.ToolsJson` **逐字节相等**(单测 `A1` 锁死, 漂移即红), "
            "responses 平铺形态(顶层 `name`/`description`/`parameters`)由同源派生。真机证据: 本地 3B Q4 在 "
            "`/v1/responses` 下按产品自建声明面**原生发出** `function_call: read_file`(400+ token 前缀, 31 输出 token) "
            "⇒ 声明面与执行面(`IWorkspaceActionPort`)可同协议对接。"
        ),
        "evidence_cmd": "python3 eval/rover/r479/check_r479.py",
        "evidence_path": VERDICT,
        "evidence_generated_with": ev(),
        "negative_control": (
            "C4 机检: 必须存在 chat 形态与既有常量逐字节相等的断言, 否则判红(禁双份手写常量); "
            "B 组单测断言 responses 形态为平铺(含 `\"function\"` 嵌套即红); 真机工具臂若未出现 `function_call` ⇒ 只主张"
            "「协议接受声明面」, 不主张「模型必然调用」。"
        ),
        "covers": [
            "src/agent.modelqueue/ActionToolSpec.cs",
            "src/agent.modelqueue/ActionLoop.cs",
            "src/agent.tests/ResponsesWireTests.cs",
        ],
        "owner_round": "R479",
    },
]

NODE = {
    "Id": "dev-r479-responses-wire-and-typed-semantics",
    "Title": "R479 Responses 真实 I/O 数据格式(instructions/input 字段分离) + 精准语义单出口校准 + 工具声明面单源",
    "State": "done",
    "Round": "R479",
    "DocRef": PLAN,
    "Evidence": VERDICT,
    "Summary": (
        "用户口径纠正「传 JSON ≠ 结构化语义」⇒ instructions 与 input 拆成独立字段、输入项 typed; "
        "「LLM 返回后本地该做什么」收敛为单一函数(本地/远端同用), 判据只取协议字段、文案单源 R478; "
        "工具声明面一份规格派生 chat(逐字节相等)/responses(平铺)两形态; "
        "真机: 本地 llama /v1/responses 200(cached 0→67/68, 原生 function_call read_file), 远端 DeepSeek /responses 200"
        "(reasoning 吃满 128 预算 ⇒ incomplete/max_output_tokens ⇒ 判 Retry)。"
    ),
}

missing = [p for p in (PLAN, CHECK, VERDICT) if not os.path.exists(os.path.join(BASE, p))]
if missing:
    print("MISSING(fail-closed):", missing)
    sys.exit(2)

reg = json.load(open(REG, encoding="utf-8"))
before = len(reg["rows"])
reg["rows"] = [r for r in reg["rows"] if not str(r.get("id", "")).startswith("r479.")]
reg["rows"].extend(ROWS)
reg["updated_round"] = "R479"

task = json.load(open(TASK, encoding="utf-8"))
task["Nodes"] = [n for n in task["Nodes"] if n.get("Id") != NODE["Id"]]
task["Nodes"].append(NODE)

if APPLY:
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(task, open(TASK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- 回读 + 形态门 ----
reg2 = json.load(open(REG, encoding="utf-8"))
task2 = json.load(open(TASK, encoding="utf-8"))
r479 = [r for r in reg2["rows"] if str(r.get("id", "")).startswith("r479.")]
errs = []
if len(r479) != 3:
    errs.append("registry r479 rows=%d" % len(r479))
for r in r479:
    for k in ("id", "level", "capability", "evidence_cmd", "evidence_path", "owner_round", "covers"):
        if not r.get(k):
            errs.append("row %s missing %s" % (r.get("id"), k))
    if not isinstance(r["level"], str) or r["level"] not in ("L1", "L2", "L3", "L4"):
        errs.append("row %s level=%r" % (r["id"], r["level"]))
    for c in r["covers"]:
        if c.startswith("/") or ".." in c:
            errs.append("row %s covers abs: %s" % (r["id"], c))
    if not os.path.exists(os.path.join(BASE, r["evidence_path"])):
        errs.append("row %s evidence_path 不存在: %s" % (r["id"], r["evidence_path"]))
if reg2["updated_round"] != "R479":
    errs.append("updated_round=%s" % reg2["updated_round"])
node = [n for n in task2["Nodes"] if n.get("Id") == NODE["Id"]]
if len(node) != 1 or node[0]["State"] != "done" or not os.path.exists(os.path.join(BASE, node[0]["DocRef"])):
    errs.append("taskplan node 形态/ DocRef 检查失败")

print(json.dumps({"applied": APPLY, "registry_rows": [before, len(reg2["rows"])],
                  "r479_rows": len(r479), "taskplan_nodes": len(task2["Nodes"]),
                  "instrument_sha12": sha12(CHECK), "errors": errs}, ensure_ascii=False, indent=1))
sys.exit(1 if errs else 0)
