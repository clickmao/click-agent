#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R1 结构化契约：单一真源。

设计依据（Fable 5.1 抽取）:
  · schema 是**机器可读契约**，不是散文 —— 这里 SCHEMA 一处定义, 同时用于
    (a) 渲染进 prompt 的 <output_contract> 段, (b) 校验器, (c) 管道准入闸。
  · 每个工具/字段自带**准入与排除判据**（"何时用 / 何时不用"），而非只描述功能。
  · 失败即 fail-closed：缺失必填 ⇒ 不得推进管道。
"""

SCHEMA = {
    "type": "object",
    "required": ["schema_version", "intent", "confidence", "entities", "constraints",
                 "missing_slots", "ambiguities", "plan", "done_when", "refusal"],
    "properties": {
        "schema_version": {"type": "string", "const": "r1.0"},
        "intent": {"type": "string", "enum": ["code_task", "question", "ops_task", "refusal"]},
        "confidence": {"type": "number", "min": 0, "max": 1},
        "entities": {"type": "array", "items": {
            "type": "object", "required": ["kind", "value"],
            "properties": {"kind": {"type": "string", "enum": ["path", "symbol", "command", "value", "language"]},
                           "value": {"type": "string"}}}},
        "constraints": {"type": "array", "items": {"type": "string"}},
        "missing_slots": {"type": "array", "items": {"type": "string"}},
        "ambiguities": {"type": "array", "items": {
            "type": "object", "required": ["span", "issue", "options"],
            "properties": {"span": {"type": "string"}, "issue": {"type": "string"},
                           "options": {"type": "array", "items": {"type": "string"}}}}},
        "plan": {"type": "array", "items": {
            "type": "object", "required": ["id", "tool", "args", "depends_on"],
            "properties": {"id": {"type": "string"},
                           "tool": {"type": "string", "enum": ["write_file", "run", "none"]},
                           "args": {"type": "object"},
                           "depends_on": {"type": "array", "items": {"type": "string"}}}}},
        "done_when": {"type": "array", "items": {"type": "string"}},
        "refusal": {"type": ["object", "null"], "required": ["reason", "category"],
                    "properties": {"reason": {"type": "string"}, "category": {"type": "string"}}},
    },
}

_HINT = {
    "intent": "code_task=要写/改可执行代码并跑验证; question=只要信息; ops_task=对已有环境做操作; refusal=应拒绝",
    "missing_slots": "推进管道**必需**但请求未给出的信息（不要臆造；没有就空数组）",
    "ambiguities": "指代不明/多种合理解读的片段。span=原文片段; options=可选项; 非空 ⇒ 管道必须停下要澄清",
    "plan": "可执行步骤; tool 仅 write_file|run; args: write_file={path,content} run={cmd,expect_stdout?}; depends_on 引用先前的 id",
    "done_when": "机械可判的完成条件（供外部校验，不是给你的自述）",
    "confidence": "0-1; <0.5 应改用 missing_slots/ambiguities 而不是猜",
}


def _nested_required(spec):
    """返回该属性下**子对象必填字段**（schema 嵌套 required 必须在 prompt 里显式出现, 否则与校验器不同源）。"""
    holder = spec
    if spec.get("type") == "array" and isinstance(spec.get("items"), dict):
        holder = spec["items"]
    if isinstance(holder.get("required"), list) and holder.get("required"):
        return holder["required"]
    return []


def _nested_enums(spec):
    """返回该属性下**子对象枚举**（schema 嵌套 enum 必须在 prompt 里显式出现：
    否则模型不知合法取值（R535 缺陷: 模型自造 kind=expected_stdout），而校验器按 enum 杀 ⇒ 契约与校验器不同源）。"""
    holder = spec
    if spec.get("type") == "array" and isinstance(spec.get("items"), dict):
        holder = spec["items"]
    props = holder.get("properties") or {}
    return ["%s ∈ %s" % (k, "|".join(v["enum"])) for k, v in props.items() if v.get("enum")]


def render_schema_text() -> str:
    """把 SCHEMA 渲染为 prompt 内的契约段（与校验器同源, 禁手工漂移）。"""
    import json
    lines = ["必填字段（缺一即无效）: " + ", ".join(SCHEMA["required"]), ""]
    for k, v in SCHEMA["properties"].items():
        t = v["type"] if isinstance(v["type"], str) else "|".join(v["type"])
        extra = ""
        if v.get("enum"):
            extra = " ∈ " + "|".join(v["enum"])
        elif v.get("const"):
            extra = " == %r" % v["const"]
        sub = _nested_required(v)
        if sub:
            extra += "；子字段必填: " + ", ".join(sub)
        ne = _nested_enums(v)
        if ne:
            extra += "；子字段取值: " + "; ".join(ne)
        lines.append("- %s (%s%s): %s" % (k, t, extra, _HINT.get(k, "")))
    lines.append("")
    lines.append("互斥规则（违反即无效）: refusal≠null ⇒ plan 必空; 有 missing_slots 或 ambiguities ⇒ plan 必空; "
                 "intent=code_task ⇒ plan 非空; depends_on 只能引用先前步骤的 id。")
    return "\n".join(lines)


def validate(o):
    """手写校验器（零依赖、fail-closed）：返回错误列表，空 = 通过。"""
    e = []
    if not isinstance(o, dict):
        return ["顶层必须是 JSON object"]
    for k in SCHEMA["required"]:
        if k not in o:
            e.append("缺必填字段: %s" % k)
    P = SCHEMA["properties"]

    def chk(key, val, spec):
        t = spec["type"]
        ok = isinstance(val, dict) if t == "object" else \
            isinstance(val, list) if t == "array" else \
            isinstance(val, (int, float)) and not isinstance(val, bool) if t == "number" else \
            isinstance(val, str) if t == "string" else True if t == "null" else True
        if isinstance(t, list):
            ok = (val is None and "null" in t) or (isinstance(val, str) and "string" in t) or \
                 (isinstance(val, dict) and "object" in t)
        if not ok:
            e.append("%s 类型错: 期望 %s, 实为 %s" % (key, t, type(val).__name__))
            return
        if "enum" in spec and val not in spec["enum"]:
            e.append("%s 取值非法: %r 不在 %s" % (key, val, spec["enum"]))
        if "const" in spec and val != spec["const"]:
            e.append("%s 常量不符: 期望 %r" % (key, spec["const"]))
        if key == "confidence" and isinstance(val, (int, float)) and not (0 <= val <= 1):
            e.append("confidence 越界: %r" % val)

    for k, spec in P.items():
        if k in o:
            chk(k, o[k], spec)

    # 嵌套必填（契约声明了就必须执行 —— 否则 prompt 与校验器不同源）
    for i, ent in enumerate(o.get("entities") or []):
        if isinstance(ent, dict):
            for k in ("kind", "value"):
                if k not in ent:
                    e.append("entities[%d] 缺子字段 %s" % (i, k))
    for i, amb in enumerate(o.get("ambiguities") or []):
        if isinstance(amb, dict):
            for k in ("span", "issue", "options"):
                if k not in amb:
                    e.append("ambiguities[%d] 缺子字段 %s" % (i, k))
    if isinstance(o.get("refusal"), dict):
        for k in (SCHEMA["properties"]["refusal"].get("required") or []):
            if k not in o["refusal"]:
                e.append("refusal 缺子字段 %s" % k)

    # 结构级语用约束（schema 表达不了的部分显式写死）
    if isinstance(o.get("refusal"), dict) and (o.get("plan") or []):
        e.append("refusal≠null 与 plan 非空互斥")
    plan = o.get("plan") or []
    seen = []
    for i, st in enumerate(plan):
        if not isinstance(st, dict):
            continue
        for k in ("id", "tool", "args", "depends_on"):
            if k not in st:
                e.append("plan[%d] 缺字段 %s" % (i, k))
        if st.get("tool") not in ("write_file", "run", "none"):
            e.append("plan[%d].tool 非法: %r" % (i, st.get("tool")))
        if st.get("tool") == "write_file":
            a = st.get("args") or {}
            if not a.get("path") or "content" not in a:
                e.append("plan[%d] write_file 需 args.path 与 args.content" % i)
        if st.get("tool") == "run":
            a = st.get("args") or {}
            if not a.get("cmd"):
                e.append("plan[%d] run 需 args.cmd" % i)
        for d in st.get("depends_on") or []:
            if d not in seen:
                e.append("plan[%d].depends_on 引用未出现的 id: %r" % (i, d))
        seen.append(st.get("id"))
    if len(set(seen)) != len(seen):
        e.append("plan id 重复")
    if o.get("intent") == "code_task" and not plan:
        e.append("intent=code_task 但 plan 为空")
    if (o.get("missing_slots") or o.get("ambiguities")) and o.get("intent") in ("code_task", "ops_task") and plan:
        e.append("既有缺失/歧义又给 plan ⇒ 语义冲突（禁猜）")
    return e


def repair_message(errors):
    return ("上一次输出未通过契约校验，逐条修正后**只输出**修正后的 JSON（不要解释、不要 markdown 围栏）：\n"
            + "\n".join("- " + x for x in errors))
