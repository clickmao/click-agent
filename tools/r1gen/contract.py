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
            "type": "object", "required": ["span", "issue", "options", "chosen"],
            "properties": {"span": {"type": "string"}, "issue": {"type": "string"},
                           "options": {"type": "array", "items": {"type": "string"}},
                           "chosen": {"type": "string"}}}},
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
    "intent": "code_task=要写/改可执行代码并跑验证; question=只要信息; ops_task=对已有环境做操作; refusal=应拒绝（仅当请求本身不可接受: 有害/越权/需真实凭据, 或**在任何解读下都无法推进**）。**交付形态差异不构成 refusal**: 请求若要求把代码放在单个围栏代码块/直接粘贴, 仍按本契约产出 plan(含 write_file 写出全部文件), 产物落入沙箱即满足其意图 —— 不得因「输出形态与请求写法不一致」而拒答",
    "missing_slots": "推进管道**必需**但请求未给出的信息（不要臆造；没有就空数组）。**自包含任务**（请求已含全部输入, 如「按下面规格写出完整程序」）不得以「缺少验证用例/测试数据/环境细节」为由填入——这些细节按请求给定的规格自行合理实现, 并在产物内写明你的约定",
    "ambiguities": "指代不明/多种合理解读的片段。span=原文片段; options=2-4 个互斥选项; chosen=采用的解读（必填，取 options 之一）—— **不停链**：按 chosen 解读继续",
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
    lines.append("互斥与优先级（违反即无效）: refusal≠null ⇒ plan 必空; missing_slots 非空 ⇒ plan 必空（管道停在澄清）; "
                 "ambiguities **不阻塞** ⇒ 每条必须给 chosen（取 options 之一）并按 chosen 继续; "
                 "intent=code_task|ops_task 且 missing_slots 空 且 refusal=null ⇒ plan 必非空; "
                 "depends_on 只能引用先前步骤的 id。")
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
    # R536: 子字段清单**由 SCHEMA 派生**（此前硬编码 3 项, 与 schema 两处真源 ⇒ chosen 加进来会静默漏检）
    amb_required = list((SCHEMA["properties"]["ambiguities"]["items"].get("required") or []))
    ent_required = list((SCHEMA["properties"]["entities"]["items"].get("required") or []))
    for i, ent in enumerate(o.get("entities") or []):
        if isinstance(ent, dict):
            for k in ent_required:
                if k not in ent:
                    e.append("entities[%d] 缺子字段 %s" % (i, k))
    for i, amb in enumerate(o.get("ambiguities") or []):
        if isinstance(amb, dict):
            for k in amb_required:
                if k not in amb:
                    e.append("ambiguities[%d] 缺子字段 %s" % (i, k))
            opts = amb.get("options")
            chosen = amb.get("chosen")
            if isinstance(opts, list) and chosen is not None and chosen not in opts:
                e.append("ambiguities[%d].chosen 不在 options: %r" % (i, chosen))
    if isinstance(o.get("refusal"), dict):
        for k in (SCHEMA["properties"]["refusal"].get("required") or []):
            if k not in o["refusal"]:
                e.append("refusal 缺子字段 %s" % k)

    # 结构级语用约束（schema 表达不了的部分显式写死）—— R536: 与渲染出的「互斥与优先级」段**逐条对应**
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
    # R536 修（死路分支）：旧规则对 <contract.py 记> `(missing_slots or ambiguities) and plan ⇒ 冲突` 与
    # `intent=code_task and not plan ⇒ 冲突` **同时成立** ⇒ `code_task ∧ 任一歧义` 在原理上不可满足
    # （实测 R535 挂 role 臂两次补全皆 plan=[] ⇒ rc=4）。新规则按「缺信息 vs 多义」二分：
    #   缺信息（missing_slots）⇒ 停链要澄清, plan 必空; 多义（ambiguities）⇒ 给 chosen 后继续, plan 必非空。
    if o.get("missing_slots") and plan:
        e.append("missing_slots 非空又给 plan ⇒ 语义冲突（缺信息不得猜）")
    if (o.get("intent") in ("code_task", "ops_task") and not plan
            and not o.get("missing_slots") and not isinstance(o.get("refusal"), dict)):
        e.append("intent=code_task 但 plan 为空（无 missing_slots/refusal ⇒ 不得靠歧义清空 plan）")
    return e


def repair_message(errors):
    return ("上一次输出未通过契约校验，逐条修正后**只输出**修正后的 JSON（不要解释、不要 markdown 围栏）：\n"
            + "\n".join("- " + x for x in errors))


def _sample_entities():
    return [{"kind": "path", "value": "toolkit/vm.py"}, {"kind": "language", "value": "python3"}]


def fixture_cases():
    """契约差分语料（单一真源 = 本文件 SCHEMA 渲染 + 校验规则）。

    用途：产品侧校验器（C#）与生成器侧规则（Python）**逐条一致**的机检语料 ——
    任一侧单独改规则 ⇒ 该侧与语料不符 ⇒ 差分测试红（禁「两处真源静默漂移」，R468 同族纪律）。
    R536: 语料含 R535 真机 raw（挂 role 臂 plan=[] 死路样本），作为「死路分支已修」的反事实控制。
    """
    r535_raw = {
        "schema_version": "r1.0", "intent": "code_task", "confidence": 0.9,
        "entities": [{"kind": "path", "value": "toolkit/__init__.py"},
                     {"kind": "path", "value": "toolkit/vm.py"},
                     {"kind": "path", "value": "toolkit/jsonmini.py"},
                     {"kind": "path", "value": "toolkit/__main__.py"},
                     {"kind": "language", "value": "python3"}],
        "constraints": ["只允许标准库",
                        "不得打印任何多余文字、提示或调试信息（stderr 亦须静默）",
                        "产物必须落在工作根下（toolkit/ 直接位于工作根）",
                        "python3 -m toolkit <vm|jsonmini>",
                        "每个子命令模块导出 solve(text: str) -> str，末尾不带换行",
                        "收尾前的自验必须在工作根执行同一验收形态"],
        "missing_slots": [],
        "ambiguities": [{"span": "python3 -m toolkit <vm|jsonmini>",
                         "issue": "CLI 子命令名与模块名不一致（模块为 vm.py/jsonmini.py，而规格中家族名为 vm_run/json_mini），入口接受的参数拼写有二义",
                         "options": ["按结构要求用 vm / jsonmini",
                                     "按子命令规格用 vm_run / json_mini",
                                     "同时接受两组别名"]}],
        "plan": [], "done_when": [], "refusal": None,
    }
    r535_fixed = dict(r535_raw)
    r535_fixed = {**r535_raw,
                  "ambiguities": [dict(r535_raw["ambiguities"][0], chosen="按结构要求用 vm / jsonmini")],
                  "plan": [{"id": "s1", "tool": "write_file",
                            "args": {"path": "toolkit/vm.py", "content": "# ...\n"}, "depends_on": []}]}
    kadane = {
        "schema_version": "r1.0", "intent": "code_task", "confidence": 0.9,
        "entities": [{"kind": "path", "value": "sols/kadane.py"}, {"kind": "language", "value": "python"}],
        "constraints": ["只用标准库", "从 stdin 读一行整数"],
        "missing_slots": [], "ambiguities": [],
        "plan": [{"id": "s1", "tool": "write_file",
                  "args": {"path": "sols/kadane.py", "content": "<源码>"}, "depends_on": []},
                 {"id": "s2", "tool": "run",
                  "args": {"cmd": "echo '-2 1 -3 4 -1 2 1 -5 4' | python3 sols/kadane.py",
                           "expect_stdout": "6"}, "depends_on": ["s1"]}],
        "done_when": ["s2 的 stdout == 6"], "refusal": None,
    }
    ask = {
        "schema_version": "r1.0", "intent": "question", "confidence": 0.85,
        "entities": [], "constraints": [],
        "missing_slots": ["缺「它」的指代对象（哪个文件/任务）", "缺验收标准"],
        "ambiguities": [{"span": "把它改好", "issue": "指代不明",
                         "options": ["上一轮的某产物", "仓库内某文件", "外部粘贴的代码"],
                         "chosen": "上一轮的某产物"}],
        "plan": [], "done_when": [], "refusal": None,
    }

    def c(name, obj, expect_valid, subs=(), source=""):
        return {"name": name, "object": obj, "expect_valid": bool(expect_valid),
                "expect_substrings": list(subs), "source": source}

    return [
        c("kadane_prefix_example", kadane, True, source="prefix <examples> #1"),
        c("ask_with_slots_and_chosen", ask, True, source="prefix <examples> #2 + chosen"),
        c("r535_role_arm_raw_deadend", r535_raw, False,
          ["缺子字段 chosen", "plan 为空"],
          source="R535 真机 raw: eval/rover/r535/run-w1/R1r/t1/reply.txt"),
        c("r535_shape_after_chosen_and_plan", r535_fixed, True,
          source="同一带歧义请求: 给 chosen + plan ⇒ 可推进（死路已修的反事实控制）"),
        c("ambiguity_chosen_not_in_options", {**r535_fixed, "ambiguities": [
            dict(r535_fixed["ambiguities"][0], chosen="不存在的选项")]}, False,
          ["chosen 不在 options"], source="chosen 必须取自 options"),
        c("missing_slots_with_plan", {**kadane, "missing_slots": ["缺验收标准"]}, False,
          ["missing_slots 非空又给 plan"], source="缺信息不得猜"),
        c("code_task_empty_plan_no_slots", {**kadane, "plan": []}, False,
          ["plan 为空"], source="无缺信息/拒答时不得清空 plan"),
        c("missing_slots_empty_plan_is_valid", {**ask, "intent": "code_task"}, True,
          source="缺信息 ⇒ 合法空 plan（管道停在澄清, 非契约错）"),
        c("refusal_with_plan", {**kadane, "refusal": {"reason": "越权", "category": "policy"}}, False,
          ["互斥"], source="refusal 与 plan 互斥"),
        c("refusal_ok", {**kadane, "plan": [], "refusal": {"reason": "越权", "category": "policy"}}, True,
          source="拒答合法形态"),
        c("confidence_out_of_range", {**kadane, "confidence": 1.2}, False, ["confidence 越界"]),
        c("entity_missing_kind", {**kadane, "entities": [{"value": "sols/kadane.py"}]}, False,
          ["缺子字段 kind"]),
        c("plan_tool_illegal", {**kadane, "plan": [{"id": "s1", "tool": "shell",
                                                    "args": {}, "depends_on": []}]}, False,
          ["tool 非法"]),
        c("missing_required_field", {k: v for k, v in kadane.items() if k != "done_when"}, False,
          ["缺必填字段: done_when"]),
    ]
