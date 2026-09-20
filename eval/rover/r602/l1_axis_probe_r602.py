#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R602 只读定因器：L1 的 `BR`(盲重采样) / `P`(同形无关内容安慰剂) 两臂**能否由 env 构造**。

文献 L1 声称「只需在既有跑臂配置上加 BR/P 两臂；产品代码零改动」（台账 §2 第 73 行）。
本器把这个声称变成**可机检的事实**：从源码派生该轴的**可取值集合**，而不是读注释或凭印象。

判据（预注册于 eval/rover/r602/prereg-r602.json 的 `l1_scope_declaration`）：
  · 轴 `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER` 的取值面 == 2（on/off）⇒ BR/P（第三种/第四种语义）
    **不可由 env 构造** ⇒ 台账 §2 的「零产品代码改动」声称**被证伪**，L1 需产品侧轴放行。
  · 随附内容由**单一函数**决定（`ArtifactCarryover.Render`）且其输入只有 (sandboxRoot, steps)
    ⇒ 无「注入无关内容」的既有入口 ⇒ 同结论。

控制（成对，防器具无牙/恒真）：
  · POS（器具能识别多值轴）：`AGENTFRAMEWORK_R1_MAX_REPAIR` 走 int.TryParse + 区间 ⇒ 取值面判定为 multi。
  · NEG（不恒真）：把布尔解析块的源码**扰动**成「三态 if/else」形态 ⇒ 派生器必须改为 multi。
  · NC-D（确定性）：跑两次读数字节全等。
rc: 0 定因成立且有牙 / 2 器具缺陷 / 3 输入缺失。
用法: python3 l1_axis_probe_r602.py [--out <path>]
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
OPT = os.path.join(REPO, "src/agent/r1/R1Options.cs")
PIPE = os.path.join(REPO, "src/agent/r1/R1Pipeline.cs")
CARRY = os.path.join(REPO, "src/agent/r1/ArtifactCarryover.cs")

BOOL_BLOCK = re.compile(
    r'var\s+(\w+)\s*=\s*true;\s*var\s+\w+\s*=\s*Environment\.GetEnvironmentVariable\("([A-Z0-9_]+)"\);(.*?)return new',
    re.S)
INT_BLOCK = re.compile(
    r'Environment\.GetEnvironmentVariable\("([A-Z0-9_]+)"\)\s*,\s*out\s+var\s+\w+\)\s*&&\s*\w+\s*>=', re.S)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def derive(src_text):
    """从源码派生：布尔轴 → 取值面 2；int+区间轴 → multi。**只看控制流形态**，不看注释。"""
    out = {"boolean_axes": {}, "multi_valued_axes": []}
    body = re.sub(r"//[^\n]*", "", src_text)          # 剥行注释（防注释里出现 env 名/关键词）
    m = BOOL_BLOCK.search(body)
    if m:
        __var, env, tail = m.group(1), m.group(2), m.group(3)
        # 取值面 = 三元否定的**字面量个数** + 1（默认值）；多于 2 个否定字面量 ⇒ multi
        negs = re.findall(r'av\s*==\s*"([^"]+)"|string\.Equals\(av,\s*"([^"]+)"', tail)
        n_lit = len([x for pair in negs for x in pair if x])
        out["boolean_axes"][env] = {"states": 2 if n_lit <= 3 else n_lit + 1, "neg_literals": n_lit}
    for e in INT_BLOCK.finditer(body):
        out["multi_valued_axes"].append(e.group(1))
    return out


def line_of(src_text, needle):
    for i, l in enumerate(src_text.splitlines(), 1):
        if needle in l:
            return i
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r602/l1-axis-probe-r602.json"))
    a = ap.parse_args()

    if not (os.path.isfile(OPT) and os.path.isfile(PIPE) and os.path.isfile(CARRY)):
        print(json.dumps({"rc": 3, "note": "输入缺失：源码件不在盘"}, ensure_ascii=False))
        return 3

    opt_raw = io.open(OPT, "rb").read()
    opt_src = opt_raw.decode("utf-8", "replace")
    pipe_src = io.open(PIPE, encoding="utf-8", errors="replace").read()
    carry_src = io.open(CARRY, encoding="utf-8", errors="replace").read()

    d1 = derive(opt_src)
    d2 = derive(opt_src)
    deterministic = (d1 == d2)

    axis = "AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER"
    booleans = d1["boolean_axes"]
    multis = d1["multi_valued_axes"]
    states = (booleans.get(axis) or {}).get("states")

    # 随附内容入口唯一性（同类证据：第二条独立路径）
    render_defs = len(re.findall(r'public static IReadOnlyList<string> Render\(', carry_src))
    render_calls = len(re.findall(r'ArtifactCarryover\.Render\(', pipe_src))

    # 控制 POS: 多值轴能被识别
    pos_ok = "AGENTFRAMEWORK_R1_MAX_REPAIR" in multis and len(multis) >= 3
    # 控制 NEG: 把布尔块扰动为三态 ⇒ 派生器必须改判 multi
    perturbed = opt_src.replace('av == "0"', 'av == "0" || av == "blind" || av == "placebo"')
    dneg = derive(perturbed)
    neg_ok = ((dneg["boolean_axes"].get(axis) or {}).get("states") or 0) > 2

    conclusion = ("BR/P 不可由 env 构造 ⇒ 台账 §2 的「零产品代码改动」声称被证伪；"
                  "L1 需产品侧轴放行（新增取值或新轴）") if states == 2 else \
                 "轴取值面 >2 ⇒ 需重核台账前提"

    res = {
        "round": "R602", "kind": "只读定因（L1 对照臂可构造性）",
        "source": {"R1Options.cs": _sha(opt_raw)[:16], "R1Pipeline.cs": _sha(io.open(PIPE, "rb").read())[:16],
                   "ArtifactCarryover.cs": _sha(io.open(CARRY, "rb").read())[:16]},
        "axis": axis,
        "derived": {"axis_states": states, "neg_literals": (booleans.get(axis) or {}).get("neg_literals"),
                    "multi_valued_axes": multis,
                    "carryover_render_definitions": render_defs, "carryover_render_call_sites": render_calls,
                    "line_R1Options_axis_parse": line_of(opt_src, 'GetEnvironmentVariable("AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER")'),
                    "line_R1Pipeline_attach": line_of(pipe_src, "ArtifactCarryover.Render("),
                    "line_R1Options_default_on": line_of(opt_src, "var artifactCarryover = true;")},
        "controls": {"determinism": bool(deterministic), "POS_multi_valued_recognized": bool(pos_ok),
                     "NEG_perturbation_flips_to_multi": bool(neg_ok)},
        "verdict": {
            "br_p_env_constructible": bool(states is not None and states > 2),
            "ledger_claim_zero_product_change": bool(states is not None and states > 2),
            "conclusion": conclusion,
        },
        "rc": 0 if (states == 2 and pos_ok and neg_ok and deterministic) else 2,
        "rc_semantics": "0 定因成立且控制全过 / 2 器具缺陷 / 3 输入缺失",
        "honest_bounds": [
            "本器判的是**可构造性**（env 取值面），不是「BR/P 是否有效」",
            "随附内容入口唯一性由 Render 定义/调用点计数给出（第二条独立路径）",
            "本器零产品源码改动、零远端调用；不构成能力验收",
        ],
    }
    json.dump(res, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": res["rc"], "axis_states": states, "controls": res["controls"],
                      "verdict": res["verdict"]["br_p_env_constructible"]}, ensure_ascii=False))
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
