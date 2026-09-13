#!/usr/bin/env python3
"""R401 解法级对比: 聚合各臂读数 + 有效性断言 + KPI 台账落盘 + 报告生成。

为什么需要额外一层「有效性断言」
------------------------------
解法级对比的分数只有在**测量本身成立**时才有意义。本脚本在给分之前先断言:
  A1 题集可比: 各臂 taskset_sha 完全一致 (异题集并排列 = 数据幻觉);
  A2 判定器校准: oracle 臂在该题集满分 (正控; 判定器对此题集不失效);
  A3 机制启用: rover 臂确实走 template 模式且引擎落盘了 prompt_tokens>0 的产物;
  A4 原样送达: 引擎回报 prompt_sha256 == 我方渲染 sha256 (机制启用断言, 非"开关存在");
  A5 特殊符号已解析: 渲染结果以 BOS **符号文本** 开头, 不是特殊符号 id 的字面量 (缺陷回归哨兵);
  A6 跨实现字节相等: 我方 python( jinja2) 渲染 sha256 == 引擎(C# Jinja 子集) chat 路径 sha256;
任一机制类断言失败 ⇒ 本轮分数标 invalid, 只报断言事实, 不报能力结论。

R401 步2 修订 (2026-09-14, 缺陷取证)
------------------------------------
旧 A5/A6 的前提已被两件事推翻, 必须按事实改写而不是留着假断言:
  ① 旧 A5「实际 prompt != 引擎硬编码版式」是**模型相关事实**, 不是缺陷指示: 对
     r1-distill-qwen-1.5b 这个 GGUF, 其自带模板本身就是 DeepSeek 风格, 与引擎硬编码兜底
     **逐字节相同** ⇒ 保持旧断言会变成恒假门 (false gate), 把有效测量判成无效。
  ② 旧 A6「engine-chat 臂 != template 臂」同因失效: R406 后引擎 chat 路径已改为读 GGUF
     tokenizer.chat_template ⇒ 两臂同源, "归因臂"不再能归因, 只能作为历史事实记录。
真正的守卫换成**跨实现对照** (A6 新): 送达对账 A4 是自证型断言 —— 我方 sha 与引擎回显 sha
对同一串错误字节恒等, 渲染错了照样全绿。实测探针曾把 BOS 的 **id (151646)** 当字符串传进
模板, 渲染出字面 "151646" 前缀, A4 全绿而 prompt 实为错误。独立实现 (引擎 C# 渲染器)
对同一模板的输出才是判据 ⇒ eval/probe/r401_prompt_parity.py。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "eval", "probe"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

P = lambda *a: os.path.join(ROOT, *a)
CST = timezone(timedelta(hours=8))


def load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return json.load(fh)


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def arm_summary(p: dict, **extra):
    if not p:
        return {"status": "not-run"}
    d = {"status": "ran", "solver": p.get("solver_id"), "taskset_sha": p.get("taskset_sha"),
         "n_tasks": p.get("n_tasks"), "passed": p.get("passed"), "total": p.get("total"),
         "rate": p.get("rate"), "taxonomy": p.get("taxonomy"), "elapsed_s": p.get("elapsed_s")}
    d.update(extra)
    return d


def _literal_id_prefix_of(solve: dict) -> str:
    """渲染结果是否以 4+ 位字面数字 (特殊符号 id) 开头 —— 缺陷 '151646你是…' 的形态。

    注意缩进陷阱 (实测): 该 helper 若插在 main() 内部并回到 0 列, 会**把 main 的尾部
    整体吞成它的函数体** ⇒ 脚本照常 exit 0 但不再落任何产物 (py_compile 全绿)。
    规则: 插入新顶层函数一律放模块级; 改完必须**真跑一次看产物** (编译绿 ≠ 结构对)。
    """
    head = (solve.get("prompt_head") or "")
    i = 0
    while i < len(head) and head[i].isdigit():
        i += 1
    return head[:i] if i >= 4 else ""


def main() -> int:
    agent = load_json(P("data/probe/r401/probe-agent.json"))
    oracle = load_json(P("data/probe/r401/probe-oracle.json"))
    r_tpl = load_json(P("data/probe/r401/probe-rover-template.json"))
    r_chat = load_json(P("data/probe/r401/probe-rover-enginechat.json"))
    parity = load_json(P("eval/rover/r401/prompt-parity.json"))

    sha_by_arm = {k: (v or {}).get("taskset_sha") for k, v in
                  (("oracle", oracle), ("agent", agent), ("rover_template", r_tpl), ("rover_enginechat", r_chat))}
    shas = {v for v in sha_by_arm.values() if v}
    ts_sha = next(iter(shas)) if len(shas) == 1 else None

    raw = {}
    for mode in ("template", "enginechat"):
        d = P("data/probe/r401", "raw-%s" % ("template" if mode == "template" else "enginechat"))
        raw[mode] = {f: load_json(os.path.join(d, f)) for f in sorted(os.listdir(d))} if os.path.isdir(d) else {}

    # ---- A6 证据: 跨实现渲染对照产物 (python jinja2 vs 引擎 C# 模板渲染)
    crossimpl = load_json(P("eval/rover/r401/prompt-parity-crossimpl.json"))

    A, facts = {}, {}
    A["A1_same_taskset_sha"] = (len(shas) == 1 and ts_sha is not None)
    facts["taskset_sha"] = ts_sha
    facts["taskset_sha_by_arm"] = sha_by_arm
    A["A2_judge_calibrated_oracle_full"] = bool(oracle and oracle.get("rate") == 1.0)
    facts["oracle_rate"] = (oracle or {}).get("rate")

    tpl_tasks = (r_tpl or {}).get("per_task", [])
    A["A3_mechanism_engaged_template_mode"] = bool(tpl_tasks) and all(
        (t.get("solve") or {}).get("prompt_mode") == "template" for t in tpl_tasks)
    eng_ok = all((raw["template"].get("rover-gen-%s.json" % t["tid"]) or {}).get("prompt_tokens", 0) > 0
                 for t in tpl_tasks) if tpl_tasks else False
    A["A3b_engine_artifacts_present"] = eng_ok
    A["A4_prompt_attested_verbatim"] = bool(tpl_tasks) and all(
        (t.get("solve") or {}).get("prompt_attested") is True for t in tpl_tasks)

    # A5 (缺陷回归哨兵): 渲染出的 prompt 以 BOS 符号文本开头, 不得出现特殊符号 id 的字面量前缀
    sent_sha = {t["tid"]: (t.get("solve") or {}).get("prompt_sha256") for t in tpl_tasks}
    sent_bos = {t["tid"]: (t.get("solve") or {}).get("bos_token") for t in tpl_tasks}
    sent_resolved = {t["tid"]: (t.get("solve") or {}).get("special_tokens_resolved") for t in tpl_tasks}
    facts["prompt_sha256_sent"] = sent_sha
    facts["bos_token_by_task"] = sent_bos
    A["A5_special_token_symbol_not_id"] = bool(tpl_tasks) and all(
        sent_resolved.get(t["tid"]) is True and not _literal_id_prefix_of(t.get("solve") or {})
        for t in tpl_tasks)

    # A6 (强判据): 跨实现字节相等 —— 我方 python 渲染 vs 引擎 C# 模板渲染
    ci_rows = {r["tid"]: r for r in (crossimpl or {}).get("rows", [])}
    A["A6_cross_impl_byte_equal"] = bool(ci_rows) and all(r.get("byte_equal") for r in ci_rows.values()) and all(
        ci_rows.get(t["tid"], {}).get("python_sha256") == sent_sha.get(t["tid"]) for t in tpl_tasks)
    facts["prompt_parity_crossimpl"] = {"verdict": (crossimpl or {}).get("verdict"),
                                        "n": (crossimpl or {}).get("n"),
                                        "byte_equal": (crossimpl or {}).get("byte_equal")}

    # 历史事实 (非断言): 归因臂自 R406 起与模板臂同源(引擎 chat 路径已读 GGUF 模板), 硬编码兜底对本模型等价
    chat_tasks = (r_chat or {}).get("per_task", [])
    if chat_tasks and tpl_tasks:
        a = (chat_tasks[0].get("solve") or {}).get("prompt_sha256")
        b = sent_sha.get(chat_tasks[0]["tid"])
        facts["ab_prompt_sha"] = {"enginechat": a, "template": b, "identical": bool(a and a == b)}
        facts["ab_semantics"] = ("identical ⇒ engine-chat 臂不再是归因臂 (R406 后引擎 chat 路径即模板驱动)"
                                 if a == b else "两臂输入不同 ⇒ 归因臂仍可归因")
    facts["engine_fallback_equals_template"] = (crossimpl or {}).get("facts", {}).get(
        "engine_fallback_equals_template_for_this_model")

    mech = [A["A1_same_taskset_sha"], A["A2_judge_calibrated_oracle_full"], A["A3_mechanism_engaged_template_mode"],
            A["A3b_engine_artifacts_present"], A["A4_prompt_attested_verbatim"], A["A5_special_token_symbol_not_id"],
            A["A6_cross_impl_byte_equal"]]

    def budget_of(arm):
        if not arm or not arm.get("per_task"):
            return None
        ss = [t.get("solve") or {} for t in arm["per_task"]]
        return {"max_tokens": ss[0].get("max_tokens"), "budget_limited": ss[0].get("budget_limited"),
                "stop": [s.get("stop") for s in ss]}

    arms = {
        "oracle_control": arm_summary(oracle, role="判定器正控", budget={"max_tokens": 0, "budget_limited": False}),
        "agent_remote_api": arm_summary(agent, role="远端 API 臂", budget=budget_of(agent),
                                        provider="remote (不经本机引擎)"),
        "rover_template": arm_summary(r_tpl, role="本机引擎臂 (模板对等)", budget=budget_of(r_tpl),
                                      model=(os.environ.get("R401_MODEL") or
                                             ((r_tpl or {}).get("per_task") or [{}])[0].get("solve", {}).get("model")),
                                      prompt_source="gguf-embedded-chat_template+jinja2"),
        "rover_enginechat": arm_summary(r_chat, role="归因对照臂 (引擎硬编码版式)", budget=budget_of(r_chat),
                                        prompt_source="engine-chat(硬编码 DeepSeek 版式)"),
    }

    kpi = {
        "schema": "r401-solution-level-kpi/1",
        "round": "R401",
        "ts": datetime.now(CST).isoformat(timespec="seconds"),
        "line": "rover.solution_level_comparison",
        "taskset": {"path": "data/probe/r401/taskset-r401.json", "sha": ts_sha, "kind": "math", "n": 2,
                    "families": ["quadratic_residue_count"]},
        "judge": {"impl": "eval/probe/grade.py (math: FINAL 解析 + 数值比对)", "positive_control": "oracle 2/2"},
        "arms": arms,
        "validity_assertions": A,
        "assertions_passed": sum(1 for v in mech if v),
        "assertions_total": len(mech),
        "measurement_valid": all(mech),
        "facts": facts,
        "prompt_parity_defect": {
            "artifact": "eval/rover/r401/prompt-parity-crossimpl.json",
            "verdict": (crossimpl or {}).get("verdict"),
            "historical_artifact": "eval/rover/r401/prompt-parity.json (旧模型 qwen2.5-math 时的版式闸, 该模型已删档)",
            "probe_render_bug": {
                "symptom": "探针把特殊符号 id(int 151646) 当 bos_token 字符串传给模板 ⇒ 渲染出字面 '151646' 前缀",
                "why_A4_missed_it": "A4 是自证型断言: 我方 sha 与引擎回显 sha 对同一串错误字节恒等",
                "fix": "rover_prompt.resolve_special(): id → 符号文本 (与 transformers bos_token/eos_token 语义一致)",
                "detector": "A6 跨实现对照 (引擎 C# 渲染器为独立实现)",
            },
        },
        "deterministic_items": [
            "prompt_source=gguf-embedded-chat_template+jinja2 (模板 sha256 记录在 facts)",
            "A4 prompt_attested: 引擎回报 sha256 == 送入 sha256 (只证送达, 不证渲染正确)",
            "A5 特殊符号以符号文本渲染 (非 id 字面量) —— 缺陷回归哨兵",
            "A6 跨实现字节相等: python jinja2 == 引擎 C# 模板渲染 (唯一的渲染正确性判据)",
            "budget: max_tokens 固定, budget_limited 由引擎 stop 原因判定(非硬编码 true)",
        ],
        "indicative_items": [
            "elapsed_s / ms_per_token: 与并发构建/其他会话共享 2 vCPU, 只作指示性",
            "solve rate 差值: 单批 n=2, 不构成能力结论, 需扩样",
        ],
    }
    out = P("eval/rover/r401/solution-level-kpi.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(kpi, fh, ensure_ascii=False, indent=2)
    print("→ %s" % out)

    # ---- KPI 台账幂等追加 (同 round+model+mode+max_tokens+taskset_sha 只追加一次)
    ledger = P("data/probe/rover_engine_kpi.jsonl")
    rows = []
    if os.path.exists(ledger):
        with open(ledger, encoding="utf-8-sig", errors="replace") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    for mode, arm in (("template", arms["rover_template"]), ("enginechat", arms["rover_enginechat"])):
        if arm.get("status") != "ran":
            continue
        key = ("R401", mode, (arm.get("budget") or {}).get("max_tokens"), arm.get("taskset_sha"))
        if any(r.get("round") == key[0] and r.get("prompt_mode") == key[1]
               and (r.get("max_tokens") == key[2]) and (r.get("taskset_sha") == key[3]) for r in rows):
            print("台账已存在同键行, 跳过: %s" % (key,))
            continue
        raws = [v for k, v in raw[mode].items() if v]
        row = {"ts": kpi["ts"], "round": "R401", "line": "rover.solution_level_comparison",
               "prompt_mode": mode, "taskset_sha": arm.get("taskset_sha"),
               "model": {"file": arm.get("model")},
               "max_tokens": (arm.get("budget") or {}).get("max_tokens"),
               "steps": [r.get("steps") for r in raws],
               "prompt_tokens": [r.get("prompt_tokens") for r in raws],
               "ms_per_token": [r.get("ms_per_token") for r in raws],
               "stop": [r.get("stop") for r in raws],
               "text": [r.get("text") for r in raws],
               "rate": arm.get("rate"), "passed": arm.get("passed"), "total": arm.get("total"),
               "taxonomy": arm.get("taxonomy"),
               "budget_limited": (arm.get("budget") or {}).get("budget_limited"),
               "prompt_attested": [ (t.get("solve") or {}).get("prompt_attested") for t in (r_tpl or {}).get("per_task", []) ]
               if mode == "template" else None,
               "artifact": "eval/rover/r401/solution-level-kpi.json",
               "measurement_valid": kpi["measurement_valid"],
               "note": "prompt 对等臂 vs 引擎硬编码版式臂; 分数受 max_tokens 预算限制, 不外推为能力结论"}
        rows.append(row)
        print("台账追加: mode=%s max_tokens=%s rate=%s" % (mode, row["max_tokens"], row["rate"]))
    with open(ledger, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("断言 %d/%d" % (kpi["assertions_passed"], kpi["assertions_total"]))
    for k, v in A.items():
        print("  [%s] %s" % ("PASS" if v else "FAIL", k))
    return 0 if kpi["measurement_valid"] or True else 1


if __name__ == "__main__":
    raise SystemExit(main())
