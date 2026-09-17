#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R528 前缀稳定性机检 (用户 2026-09-17 定向: 「你往中间塞东西了？」+「上下文几乎不涨才是对的」)。

读**实发** adapter dump (full-*.json = 该次调用的 messages; side-*.json = usage), 不看代码行。
臂由调用序号区间界定 (--range A1-on=i0,i1, 与 run 脚本 logs/idx.txt 同源):
  M1 常量前缀: 处理臂 (缺省 A1-on) 在**全部窗口**的 system 段逐字节相同 (跨运行常量 ⇒ 服务端缓存前沿 = 全 system);
  M2 遥测外泄: 任何 system/user 段都不得出现 data/activity / prompt_audit / 工作区文件 标记 (R522 实测该块砍断前沿);
  M3 首调用: 每次运行首调用 cached_tokens >= 0.45 × system 字符数 且 新算 <= 2000 tok 且 cached > 2304 (R522 基线);
  M4 每步涨: 逐调用 prompt_tokens 步间增量中位 <= 700 tok (codex 同题基准 440; R522 我方 1,222 新算中位);
  M5 回灌: 工具回执字符中位 <= 400 且 p90 <= 1500, assistant 正文中位 == 0 (零过渡叙述)。
codex 只作参照列 (不参与 M1/M3/M4/M5 判定)。rc=0 仅当 M1..M5 全过; 全部读数照报。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import statistics as st
import sys

TELEMETRY_MARKERS = ("data/activity", "prompt_audit", "工作区文件", "Workspace Files")


def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def calls_of(adapter_dir: str):
    out = []
    for side_p in sorted(glob.glob(os.path.join(adapter_dir, "side-*.json"))):
        m = re.search(r"side-([a-z]+)-(\d+)\.json$", os.path.basename(side_p))
        if not m:
            continue
        side_name, idx = m.group(1), int(m.group(2))
        side = json.load(io.open(side_p, encoding="utf-8"))
        full_p = os.path.join(adapter_dir, "full-%s-%03d.json" % (side_name, idx))
        if not os.path.isfile(full_p):
            cands = glob.glob(os.path.join(adapter_dir, "full-*-%03d.json" % idx))
            if not cands:
                continue
            full_p = cands[0]
        msgs = json.load(io.open(full_p, encoding="utf-8"))
        if isinstance(msgs, dict):
            msgs = (msgs.get("request") or {}).get("messages") or []
        system = "\n".join(str(x.get("content") or "") for x in msgs if x.get("role") == "system")
        users = [str(x.get("content") or "") for x in msgs if x.get("role") == "user"]
        receipts = [len(str(x.get("content") or "")) for x in msgs if x.get("role") == "tool"]
        bodies = [len(str(x.get("content") or "")) for x in msgs
                  if x.get("role") == "assistant" and str(x.get("content") or "").strip()]
        u = ((side.get("response") or {}).get("usage") or {})
        cached = int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or u.get("prompt_cache_hit_tokens") or 0)
        prompt = int(u.get("prompt_tokens") or 0)
        comp = int(u.get("completion_tokens") or 0)
        out.append({"dir": os.path.basename(adapter_dir), "side": side_name, "idx": idx,
                    "system": system, "system_sha8": sha8(system), "users": users,
                    "receipt_chars": receipts, "body_chars": bodies,
                    "prompt": prompt, "cached": cached, "fresh": prompt - cached, "completion": comp})
    return sorted(out, key=lambda r: (r["dir"], r["side"], r["idx"]))


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else None


def p90(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return round(st.quantiles(xs, n=10)[8], 1) if len(xs) >= 10 else xs[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter-dir", action="append", required=True)
    ap.add_argument("--range", action="append", default=[], help="<臂名>=<i0>,<i1> (side=agent)")
    ap.add_argument("--treatment", default="A1-on")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ranges = {}
    for r in a.range:
        name, sp = r.split("=", 1)
        i0, i1 = (int(x) for x in sp.split(","))
        ranges[name] = (i0, i1)
    all_calls = []
    for d in a.adapter_dir:
        all_calls.extend(calls_of(d))
    if not all_calls:
        print("FAIL: 无可用 dump")
        return 3

    def pick(name):
        i0, i1 = ranges.get(name, (1, 10 ** 9))
        return [c for c in all_calls if c["side"] == "agent" and i0 <= c["idx"] <= i1]

    treat = pick(a.treatment)
    codex = [c for c in all_calls if c["side"] == "codex"]

    # 宿主修复回路 (aux) 调用: system 不含 `## §N ` 分区段头 ⇒ 属**宿主侧**提示 (修复/闸门),
    #   不是 agent 主环前缀; 单列 aux_calls 并从 M1/S* 与步间聚合中剔除 (R522 口径: 末次修复调用增量不可归因)。
    def _is_aux(c):
        return not re.search(r"(?m)^## §\d+ ", c["system"])
    treat_main = [c for c in treat if not _is_aux(c)]
    treat_aux = [c for c in treat if _is_aux(c)]

    m1 = len({c["system"] for c in treat_main}) == 1 and len(treat_main) > 0
    m2 = all(not any(mk in c["system"] for mk in TELEMETRY_MARKERS) for c in all_calls) and \
         all(not any(mk in u for mk in TELEMETRY_MARKERS) for c in all_calls for u in c["users"])

    firsts = {}
    for c in treat_main:
        firsts.setdefault(c["dir"], []).append(c)
    first_rows = [{"run": k, "system_chars": len(v[0]["system"]), "cached": v[0]["cached"],
                   "fresh": v[0]["fresh"], "prompt": v[0]["prompt"]} for k, v in sorted(firsts.items())]
    m3 = all(r["cached"] >= 0.45 * r["system_chars"] and r["fresh"] <= 2000 and r["cached"] > 2304 for r in first_rows) and bool(first_rows)

    growth, fresh_all, receipt_all, body_all = [], [], [], []
    for k, v in sorted(firsts.items()):
        for i in range(1, len(v)):
            growth.append(v[i]["prompt"] - v[i - 1]["prompt"])
        fresh_all.extend(c["fresh"] for c in v)
        receipt_all.extend(x for c in v for x in c["receipt_chars"])
        body_all.extend(x for c in v for x in c["body_chars"])
    g_med, g_p90, fresh_med = med(growth), p90(growth), med(fresh_all)
    m4 = (g_med is not None and g_med <= 700) and (fresh_med is not None and fresh_med <= 600)
    r_med, r_p, b_med, b_p = med(receipt_all), p90(receipt_all), med(body_all), p90(body_all)
    m5 = (r_med is not None and r_med <= 400 and (r_p is None or r_p <= 1500)) and (b_med in (None, 0, 0.0))

    # M6 (用户定向: user 轮只留题面 + 小追加): 处理臂 user 段 <= 3200 字符, 且常量材料 [技能知识参考] 不在 user 段 (须在常量前缀)。
    user_sizes = [len("\n".join(c["users"])) for c in treat_main]
    user_mat = any("技能知识参考" in u for c in treat_main for u in c["users"])
    m6 = bool(user_sizes) and max(user_sizes) <= 3200 and not user_mat

    # ---- R528 分区常量前缀结构锁 (用户令: 按外部真值 Fable 5.1 泄露 system 重构 + 记入铁律 12) ----
    #   外部真值形状: 274,608 字符 = **一个逐字节恒定前缀** (270 个顶级段; 46 个工具 schema 亦在常量区), 每轮只做尾部追加。
    #   S1 段头序列 == 固定 §1..§11 升序各一次; S2 段头集合跨臂/跨窗口恒一 (结构漂移 = 前缀漂移);
    #   S3 每段体量: 下界 40 字符 (防空段), 上界 12000 字符 —— 上界取自**外部真值**(Fable 5.1 最大段
    #      `preferences_guardrails` 10,784 字符) 上取整+余量, 不按本侧读数调 (本侧实测最大段 6,485 = §11 关键模块地图)。
    SECTION_ORDER = ["§1 身份与目标", "§2 安全与诚实底线 (违反即返工)", "§3 记忆与召回规则 (常量规则; 材料一律只追加尾部)",
                     "§4 行为与输出纪律", "§5 工程与执行纪律 (违反即返工)", "§6 工具协议",
                     "§7 技能菜单与按需加载", "§8 环境与工作区 (会话首轮快照)",
                     "§9 常见失败模式与自检 (历史实证, 逐条自查)", "§10 汇报格式 (约定)",
                     "§11 关键模块地图 (本仓库实况, 便于定位改动点)"]

    def sections(sys_text):
        return ["§%s %s" % (m.group(1), m.group(2).strip())
                for m in re.finditer(r"(?m)^## §(\d+) (.+)$", sys_text)]

    treat_headers = [sections(c["system"]) for c in treat_main]
    s1 = bool(treat_main) and all(h == SECTION_ORDER for h in treat_headers)
    agent_headers = {tuple(sections(c["system"])) for c in all_calls if c["side"] == "agent" and not _is_aux(c)}
    s2 = len(agent_headers) == 1 and next(iter(agent_headers)) == tuple(SECTION_ORDER)
    sizes = []
    if treat_main:
        sys0 = treat_main[0]["system"]
        idx = [m.start() for m in re.finditer(r"(?m)^## §\d+ ", sys0)]
        for i, p in enumerate(idx):
            end = idx[i + 1] if i + 1 < len(idx) else sys0.find("\n[正式提示合同", p) if "\n[正式提示合同" in sys0 else len(sys0)
            sizes.append(end - p if end > p else len(sys0) - p)
    s3 = bool(sizes) and min(sizes) >= 40 and max(sizes) <= 12000
    s4 = bool(treat_main) and "常量前缀" in treat_main[0]["system"] and "追加在尾部" in treat_main[0]["system"]
    user_marks = any(("## §" in u) or ("技能知识参考" in u)
                     for c in all_calls if c["side"] == "agent" and not _is_aux(c) for u in c["users"])
    s5 = not user_marks

    ref = {"codex_calls": len(codex),
           "codex_first": ({"system_chars": len(codex[0]["system"]), "cached": codex[0]["cached"],
                            "fresh": codex[0]["fresh"], "prompt": codex[0]["prompt"]} if codex else None),
           "codex_step_growth_median": med([codex[i]["prompt"] - codex[i - 1]["prompt"] for i in range(1, len(codex))]),
           "codex_receipt_chars_median": med([x for c in codex for x in c["receipt_chars"]]),
           "codex_body_median": med([x for c in codex for x in c["body_chars"]])}

    verdict = {"M1_system_constant": m1, "M2_no_telemetry_in_prompt": m2, "M3_first_call_cache": m3,
               "M4_step_growth": m4, "M5_receipts_and_narration": m5, "M6_user_turn_task_only": m6,
               "S1_section_order": s1, "S2_sections_constant": s2, "S3_section_size_bound": s3,
               "S4_prefix_declaration": s4, "S5_tail_only_in_user": s5}
    blob = {"round": "R531", "treatment": a.treatment, "ranges": ranges,
            "calls_total": len(all_calls), "calls_treatment": len(treat),
            "calls_treatment_main": len(treat_main), "aux_calls": len(treat_aux),
            "system_chars": len(treat_main[0]["system"]) if treat_main else None,
            "system_sha8_distinct": sorted({c["system_sha8"] for c in treat_main}),
            "first_rows": first_rows, "user_chars_max": max(user_sizes) if user_sizes else None,
            "user_has_constant_material": user_mat,
            "step_growth_median": g_med, "step_growth_p90": g_p90, "fresh_median": fresh_med,
            "receipt_chars_median": r_med, "receipt_chars_p90": r_p,
            "assistant_body_median": b_med, "assistant_body_p90": b_p,
            "structure": {"section_order": SECTION_ORDER,
                          "sections_found": treat_headers[0] if treat_headers else None,
                          "section_sizes": sizes},
            "reference_codex": ref, "verdict": verdict, "pass": all(verdict.values())}
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
    print("处理臂=%s 调用=%d system 字符=%s 不同 system 段=%d (%s)" %
          (a.treatment, len(treat), blob["system_chars"], len(blob["system_sha8_distinct"]),
           ",".join(blob["system_sha8_distinct"])))
    print("首调用:", json.dumps(first_rows, ensure_ascii=False))
    print("步间涨幅中位=%s p90=%s 新算中位=%s 回执中位=%s p90=%s 正文中位=%s" %
          (g_med, g_p90, fresh_med, r_med, r_p, b_med))
    print("codex 参照:", json.dumps(ref, ensure_ascii=False))
    print("verdict:", json.dumps(verdict, ensure_ascii=False))
    return 0 if blob["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
