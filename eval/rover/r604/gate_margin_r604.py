#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R604 C1：起手闸余量条款**按 r603 实测振幅重派生**（纯读 + 纯函数判别力控制）。

口径（承 §12.1.2 入册条目，一字未改）：
  MARGIN := clamp(prev_swing_effective, floor=60, cap=CEIL-GATE_MB-floor)
  REQ     = GATE_MB + MARGIN
  CEIL    = 起手前 3 样本取 min；极差 > 50MB ⇒ fail-closed（窗口不可开）
  cap == MARGIN ⇒ cap_binding=true ⇒ 振幅项退化（收紧的是上界而非下界）

本轮零真机臂 ⇒ 条款**不真机行使**（记「未测」）；判别力由**纯函数**两门槛反判承担：
  同一内存态 m* = GATE_MB 下，基础门槛判 PASS ∧ 条款 REQ 判 GATE_BLOCKED。

rc: 0 已派生 / 2 器具缺陷（顶棚低于下限 ⇒ 窗口结构性不可开；判别力无牙）/ 3 输入缺失。
用法: python3 eval/rover/r604/gate_margin_r604.py [--sample-source r603] [--json <out>]
"""
from __future__ import annotations
import argparse
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
GATE_MB = 2650      # 基础门槛（R585–R603 全档不变；来源 = gate-margin-r60*.json 反解）
FLOOR_MB = 60       # 余量下限（§12.1.2）
SPREAD_MAX = 50     # 起手前 3 样本极差上界（fail-closed）


def read_samples(round_id):
    p = os.path.join(RUNS, round_id, "logs", "run-samples.jsonl")
    if not os.path.isfile(p):
        return None, p
    vals = []
    for line in io.open(p, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        m = r.get("mem_available_mb")
        if isinstance(m, (int, float)):
            vals.append(int(m))
    return vals, p


def mem_avail():
    try:
        for line in io.open("/proc/meminfo", encoding="utf-8", errors="replace"):
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except Exception:  # noqa: BLE001
        return None
    return None


def own_tool_rss():
    """会话端工具子进程（LSP/编辑器）——**不在闸 blocker 血统内**，但会压低 MemAvailable（R571 实测 +359MB）。"""
    tot, pids = 0, []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            cmd = io.open("/proc/%s/cmdline" % d, encoding="utf-8", errors="replace").read()
            if not cmd:
                continue
            low = cmd.lower()
            if ("langserver" in low or "language-server" in low or "pyright" in low):
                for line in io.open("/proc/%s/status" % d, encoding="utf-8", errors="replace"):
                    if line.startswith("VmRSS:"):
                        tot += int(line.split()[1]) // 1024
                        pids.append(int(d))
                        break
        except Exception:  # noqa: BLE001
            continue
    return tot, sorted(pids)


def gate_pass(mem_mb, req):
    return mem_mb >= req


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-source", default="r603")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    out = {"tool": "gate_margin_r604", "round": "R604", "verdict": "PENDING", "rc": 3,
           "clause": "MARGIN := clamp(prev_swing_effective, floor=60, cap=CEIL-GATE-floor); REQ=GATE+MARGIN",
           "gate_mb": GATE_MB, "floor_mb": FLOOR_MB, "spread_clause": "<=50MB else fail-closed"}

    vals, src = read_samples(a.sample_source)
    if vals is None:
        out.update({"verdict": "INPUT_MISSING", "rc": 3, "missing": [src]})
        print("[gate-r604] rc=3 INPUT_MISSING %s" % src)
        return 3
    swing = max(vals) - min(vals)
    samples = [mem_avail(), mem_avail(), mem_avail()]   # 起手前 3 样本
    if any(s is None for s in samples):
        out.update({"verdict": "INPUT_MISSING", "rc": 3, "missing": ["/proc/meminfo"]})
        print("[gate-r604] rc=3 无法读 /proc/meminfo")
        return 3
    sv = [int(s) for s in samples if s is not None]
    ceil_ = min(sv)
    spread = max(sv) - min(sv)
    cap = ceil_ - GATE_MB - FLOOR_MB
    margin = max(FLOOR_MB, min(swing, cap))
    req = GATE_MB + margin

    out.update({
        "prev_swing_source": "%s/logs/run-samples.jsonl (同态在飞窗, n=%d, min=%d, max=%d)"
                              % (a.sample_source, len(vals), min(vals), max(vals)),
        "prev_swing_effective": swing,
        "prev_swing_prev_round": 252,
        "pre_samples": samples, "ceiling_min_of_3": ceil_, "pre_sample_spread_mb": spread,
        "cap": cap, "margin": margin, "req": req,
        "cap_binding": bool(margin == cap),
        "note": "cap==margin ⇒ 振幅项退化（承 R590 登记）",
    })

    defects, blocking = [], []
    if spread > SPREAD_MAX:
        blocking.append("起手前 3 样本极差 %dMB > %dMB ⇒ 跨态，窗口不可开（fail-closed）"
                        % (spread, SPREAD_MAX))
    if cap < FLOOR_MB:
        blocking.append("cap %d < floor %d ⇒ 顶棚低于下限，窗口结构性不可开（fail-closed 正确行为，不记缺陷）"
                        % (cap, FLOOR_MB))

    # --- 判别力：纯函数两门槛反判（同一内存态 m* = GATE_MB）---
    m_star = GATE_MB
    disc = {
        "anchor_mem_mb": m_star,
        "basic_gate": {"threshold": GATE_MB, "verdict": "PASS" if gate_pass(m_star, GATE_MB) else "GATE_BLOCKED"},
        "clause_gate": {"threshold": req, "verdict": "PASS" if gate_pass(m_star, req) else "GATE_BLOCKED"},
    }
    disc["stricter"] = (disc["basic_gate"]["verdict"] == "PASS"
                        and disc["clause_gate"]["verdict"] == "GATE_BLOCKED")
    if not disc["stricter"]:
        defects.append("判别力无牙：同态两门槛未产生 PASS/BLOCKED 反判（req %d <= gate %d）" % (req, GATE_MB))
    out["discrimination_pure_function"] = disc
    out["live_exercise"] = {"done": False,
                            "why": "本轮零真机臂 ⇒ 条款未真机行使（如实记「未测」，不得读成已收紧生效）"}
    usable = sum(1 for v in vals if gate_pass(v, req))
    out["availability_on_recorded_window"] = {
        "samples": len(vals), "pass_new_req": usable,
        "share": round(usable / len(vals), 4),
        "info_only": "只作参照（历史窗采样 ≠ 起手窗口）",
    }

    if defects:
        out.update({"verdict": "INSTRUMENT_DEFECT", "rc": 2, "defects": defects})
    elif blocking:
        out.update({"verdict": "WINDOW_UNOPENABLE", "rc": 2, "blocking": blocking,
                    "note_failclosed": "窗口不可开 = fail-closed 的正确行为（承 R590 先例，不记器具缺陷）"})
    else:
        out.update({"verdict": "DERIVED", "rc": 0})

    own_mb, own_pids = own_tool_rss()
    ceil_reaped = ceil_ + own_mb
    cap_reaped = ceil_reaped - GATE_MB - FLOOR_MB
    margin_reaped = max(FLOOR_MB, min(swing, cap_reaped)) if cap_reaped >= FLOOR_MB else None
    out["own_tool_context"] = {
        "rss_mb": own_mb, "pids": own_pids,
        "note": "会话端工具子进程（LSP 等）不在闸 blocker 血统内，但会压低 MemAvailable（R571 实测 +359MB）⇒ 只作信息项，不改条款",
        "mem_available_if_reaped_mb": ceil_reaped,
    }
    out["scenario_if_own_tools_reaped"] = {
        "ceiling_mb": ceil_reaped, "cap": cap_reaped,
        "margin": margin_reaped,
        "req": (GATE_MB + margin_reaped) if margin_reaped is not None else None,
        "window_openable": bool(margin_reaped is not None),
        "note": "反事实栏（只报不改）：说明「窗口不可开」是否由本会话工具子进程造成——按 pid 清场属**下一轮起手前的动作**，本轮不动任何进程",
    }

    print("[gate-r604] rc=%d verdict=%s swing=%d ceiling=%d spread=%d margin=%d req=%d cap_binding=%s"
          % (out["rc"], out["verdict"], swing, ceil_, spread, margin, req, out["cap_binding"]))
    print("  own_tool: rss=%dMB pids=%s ⇒ 若回收后 ceiling≈%dMB cap=%d margin=%s REQ=%s openable=%s"
          % (own_mb, own_pids, ceil_reaped, cap_reaped, margin_reaped,
             out["scenario_if_own_tools_reaped"]["req"],
             out["scenario_if_own_tools_reaped"]["window_openable"]))
    print("  disc: %s" % json.dumps(disc, ensure_ascii=False))
    dst = a.json or os.path.join(REPO, "eval", "rover", "r604", "gate-margin-r604.json")
    with io.open(dst, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("  wrote %s" % dst)
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
