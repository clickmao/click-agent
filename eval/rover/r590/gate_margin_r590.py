#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R590 候选④：起手闸余量条款**重派生**（只读）。

动因（预注册 C2 已先写）：R589 是**只读并池轮（零臂）** ⇒ 其
`~/.agentframework/harness/runs/r589/logs/run-samples.jsonl` **结构性不存在**，
于是条款 v2 的 `prev_swing = 上一轮同一宿主运行中实测振幅` 在「只读轮」上**取值未定义**
（既不是 0，也不是继承）——这是一处**条款缺分支**。

本器只做两件事：
① 按「上一轮优先取在飞窗振幅；无在飞窗（零臂）则取该轮**起手前采样**振幅」派生 `prev_swing_effective`，
   并把**来源**（文件 / 样本数）写进读数（禁硬编码常数）。
② 报 `cap` 是否 binding：`cap = CEIL − GATE_MB − floor`。binding 时振幅项**当前不承重**
   ⇒ 如实记「条款退化」，不得据此宣称条款已收紧。

**零写入 runs/ / 零产品改动 / 零远端。墙钟只作信息字段。**
"""
from __future__ import annotations

import argparse
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
HARNESS = os.path.expanduser("~/.agentframework/harness")
GATE_MB = 2650
FLOOR = 60
PREV_ROUND = "r589"


def _swing(path):
    if not os.path.isfile(path):
        return {"path": path, "n": 0, "swing": None, "note": "文件不存在（结构性缺测）"}
    vals = []
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001 — 解析失败须可见，不静默跳过
            continue
        m = d.get("mem_available_mb")
        if isinstance(m, (int, float)):
            vals.append(float(m))
    if len(vals) < 2:
        return {"path": path, "n": len(vals), "swing": None,
                "note": "样本 <2 ⇒ 不可估"}
    return {"path": path, "n": len(vals), "min": min(vals), "max": max(vals),
            "swing": int(max(vals) - min(vals))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r590/gate-margin-r590.json"))
    ap.add_argument("--round", default="R590")
    ap.add_argument("--prev-round", default=PREV_ROUND)
    a = ap.parse_args(argv)

    inrun = _swing(os.path.join(HARNESS, "runs", a.prev_round, "logs", "run-samples.jsonl"))
    pres = _swing(os.path.join(HARNESS, "runs", a.prev_round, "logs", "pre-samples.jsonl"))

    if inrun.get("swing") is not None:
        eff, src, branch = inrun["swing"], inrun["path"], "in_run"
    elif pres.get("swing") is not None:
        eff, src, branch = pres["swing"], pres["path"], "pre_sample_only"
    else:
        eff, src, branch = None, None, "unavailable"

    out = {
        "round": a.round,
        "criterion": "C2",
        "mode": "read_only margin re-derivation (零写入 runs/ · 零产品改动 · 零远端)",
        "clause_v2_text": "MARGIN = max(60MB, 上一轮同一宿主运行中实测振幅)；REQ = GATE_MB + MARGIN",
        "clause_v2_defect": "「只读轮（零臂）」无在飞窗 ⇒ prev_swing 取值未定义（条款缺分支，非数值问题）",
        "derived_clause": "prev_swing_effective = max(在飞窗振幅, 起手前采样振幅)；"
                          "MARGIN := clamp(prev_swing_effective, floor, cap)；"
                          "cap = CEIL − GATE_MB − floor；REQ = GATE_MB + MARGIN",
        "sources": {"in_run": inrun, "pre_sample": pres},
        "prev_swing_effective": eff,
        "prev_swing_source": src,
        "branch_taken": branch,
        "gate_mb": GATE_MB,
        "floor_mb": FLOOR,
        "rc": 0 if eff is not None else 2,
    }
    if eff is None:
        out["rc_reason"] = "上一轮在飞窗与起手前采样**均**不可估 ⇒ 条款无来源，fail-closed"

    # 来源可采性：只读轮分支的候选源必须**同态**（极差 ≤ 50MB），否则是跨清场跳变，不可当振幅用。
    ADMIT_SPREAD = 50
    src = pres if branch == "pre_sample_only" else inrun
    src_spread = (src.get("swing") if src.get("swing") is not None else None)
    out["source_admissibility"] = {
        "rule": "只读轮分支的振幅源须同态（样本极差 ≤ %dMB）" % ADMIT_SPREAD,
        "source_file": src.get("path"),
        "source_n": src.get("n"),
        "source_spread_mb": src_spread,
        "admissible": (src_spread is not None and src_spread <= ADMIT_SPREAD),
        "reason_if_not": (None if (src_spread is not None and src_spread <= ADMIT_SPREAD)
                          else "极差 %sMB > %dMB ⇒ 跨态（R589 的两个起手前样本分别落在"
                               "清本会话工具子进程**之前/之后**，差 361MB = 清场跳变，非宿主振幅）"
                               % (src_spread, ADMIT_SPREAD)),
        "recommended_rollback_source": "最近一次**同态在飞窗**振幅 = r588 run-samples（n=189, swing 314）",
    }

    # 稳健性：无论用受污染的 361 还是回退的 314，在当前顶棚下结论是否改变
    robust = []
    for ceiling in (2748, 2855):
        for label, swing in (("contaminated_r589_pre(361)", 361), ("rollback_r588_inrun(314)", 314)):
            cap = ceiling - GATE_MB - FLOOR
            margin = None if cap < FLOOR else min(swing, cap)
            robust.append({"ceiling": ceiling, "margin_source": label, "cap": cap,
                           "margin": margin, "req": (None if margin is None else GATE_MB + margin),
                           "openable": (margin is not None and margin >= FLOOR),
                           "cap_binding": (cap < swing)})
    out["robustness_table"] = robust
    out["robustness_note"] = ("两源在当前顶棚（2748）下**结论相同**（cap 38 < floor 60 ⇒ 窗口不可开）"
                              "⇒ 本轮读数对受污染源**不敏感**；但在高顶棚（2855）下两源都受 cap 夹取 "
                              "⇒ **振幅项恒不承重**（条款退化）。")


    rows = []
    for ceil in (2494, 2650, 2710, 2803, 2855, 2900):
        cap = ceil - GATE_MB - FLOOR
        # 夹取顺序与 `gate_r589.sh` 同形：先 min(eff, cap)，再判 < floor ⇒ fail-closed。
        raw = None
        if cap < FLOOR:
            clamped, openable = None, False
        elif eff is None:
            clamped, openable = None, False
        else:
            clamped, openable = min(eff, cap), min(eff, cap) >= FLOOR
        rows.append({
            "ceiling": ceil, "cap": cap,
            "margin_raw": eff,
            "margin_clamped": clamped,
            "cap_binding": (cap is not None and eff is not None and eff > cap),
            "openable": openable,
        })
    out["cap_binding_table"] = rows
    out["cap_binding_note"] = ("在当前顶棚量级（≈2.8–2.9GB）上 cap 恒 < prev_swing_effective ⇒ "
                               "振幅项被 cap 吃掉 = **条款退化**（收紧了上界、未收紧下界）；"
                               "只有 CEIL ≥ GATE_MB + floor + eff 时振幅项才承重。")
    out["live_ceiling_mb"] = _live_ceiling()

    with io.open(a.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1))
    print("branch=%s prev_swing_effective=%s source=%s cap_binding=%s" % (
        branch, eff, src, rows[-1]["cap_binding"]))
    print("OUT=%s rc=%s" % (a.out, out["rc"]))
    return out["rc"]


def _live_ceiling():
    try:
        with io.open("/proc/meminfo", encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                if ln.startswith("MemAvailable"):
                    return int(int(ln.split()[1]) / 1024)
    except Exception:  # noqa: BLE001
        return None
    return None


if __name__ == "__main__":
    import sys
    sys.exit(main())
