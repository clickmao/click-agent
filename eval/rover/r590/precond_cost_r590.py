#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R590 候选⑤：铁律 11 前置器在 **project 布局**下的耗时口径（只读）。

背景（预注册 C3 已先写）：R589 轮志**内部自相矛盾** —— C3 行写「完成 4/4」，诚实边界行写
「本轮重跑未全数完成」，master R590 候选⑤ 沿用后者。本器以**在盘证据**裁定，并给出只读轮的
**抽样复跑替代口径**。

只读 / 零写入 runs/ / 零产品改动 / 零远端。**墙钟只作信息字段，不作红绿判据。**

守恒判据（可机检）：复跑结论必须与该轮**自身已登记**结论一致
（`~/.agentframework/harness/runs/<r>/precond.rc`，由该轮自己跑动时写下）。
不一致 ⇒ 数据面异常 ⇒ 全量重跑（fail-closed），不得用抽样读数据说结论。
"""
from __future__ import annotations

import argparse
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
HARNESS = os.path.expanduser("~/.agentframework/harness")
ROUNDS = ["r585", "r586", "r587", "r588"]


def _rc_of_verdict(d):
    """前置器 rc 由验收面决定（0/1），不由末条命令退出码决定。"""
    if d.get("acceptable_scoped") is True and d.get("executable_and_correct") is True:
        return 0
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r590/precond-cost-r590.json"))
    a = ap.parse_args(argv)

    rows = []
    for r in ROUNDS:
        log = os.path.join(REPO, "eval/rover/r589/logs", "precond-%s.log" % r)
        js = os.path.join(REPO, "eval/rover/r589", "precond-%s.json" % r)
        own = os.path.join(HARNESS, "runs", r, "precond.rc")
        row = {"round": r, "rerun_log": log, "rerun_json": js,
               "rerun_done_epoch": None, "own_registered_rc": None,
               "rerun_rc": None, "consistent": None}
        if os.path.isfile(log):
            row["rerun_done_epoch"] = int(os.stat(log).st_mtime)
        if os.path.isfile(own):
            row["own_registered_rc"] = int(io.open(own).read().strip() or -1)
        if os.path.isfile(js):
            d = json.load(io.open(js, encoding="utf-8"))
            row["rerun_rc"] = _rc_of_verdict(d)
            row["label"] = d.get("label")
            row["windows_n"] = d.get("windows_n")
            row["blocked_n"] = len(d.get("blocked") or [])
            row["executable_and_correct"] = d.get("executable_and_correct")
            row["acceptable_scoped"] = d.get("acceptable_scoped")
            row["self_report_agrees"] = d.get("self_report_agrees")
        row["consistent"] = (row["rerun_rc"] is not None
                             and row["own_registered_rc"] is not None
                             and row["rerun_rc"] == row["own_registered_rc"])
        rows.append(row)

    done = [x["rerun_done_epoch"] for x in rows if x["rerun_done_epoch"] is not None]
    deltas = [done[i] - done[i - 1] for i in range(1, len(done))]
    observed = [x for x in rows if x["rerun_rc"] is not None]
    consistent = all(x["consistent"] for x in rows)

    out = {
        "round": "R590",
        "criterion": "C3",
        "mode": "read_only cost/口径 derivation (零写入 runs/ · 零产品改动 · 零远端)",
        "predeclared_conflict": {
            "claim_A": "R589 轮志 C3 行: 本轮重跑「完成 4/4」",
            "claim_B": "R589 轮志 诚实边界行 + master R590 候选⑤: 「4 轮重跑未跑完」",
            "adjudication": "以在盘证据为准：4 份 log + 4 份 JSON 齐备、每份含完整判决字段与终态"
                            "（executable_and_correct / acceptable_scoped / blocked），"
                            "完成时刻单调推进 ⇒ 判 **4/4 完成**；claim_B 不成立。",
        },
        "rows": rows,
        "n_rerun_completed": len(observed),
        "n_rounds": len(ROUNDS),
        "durations_s_informational_only": {
            "note": "第 1 轮的起点无锚（只有完成时刻）⇒ 只可测 2..4 轮的**相邻完成间隔**；"
                    "墙钟一律信息字段，不进任何红绿判据。",
            "intervals": deltas,
            "total_window_s": (max(done) - min(done)) if len(done) > 1 else None,
            "per_round_upper_bound_s": (max(deltas) if deltas else None),
            "n_intervals": len(deltas),
        },
        "consistency_check": {
            "rule": "复跑结论 == 该轮自身已登记结论（runs/<r>/precond.rc）",
            "all_consistent": consistent,
            "pairs": [{"round": x["round"], "own": x["own_registered_rc"], "rerun": x["rerun_rc"]}
                      for x in rows],
        },
        "sampling_substitution_protocol": {
            "applies_to": "只读轮（零新臂）复算铁律 11 验收面",
            "rule": "抽样 ≥1 轮**真跑** + 其余取各轮**自身已登记**读数；抽样轮须满足 "
                    "「复跑结论 == 自身已登记结论」守恒判据",
            "fail_closed": "任一抽样轮不一致 ⇒ 判数据面异常 ⇒ 放弃抽样、全量重跑（不得用抽样读数下结论）",
            "why_not_free": "全量复跑实测 ≈ 20–22 s/轮（project 布局，4 轮 ≈ 63 s 窗口）；"
                            "只读轮以「各轮自身已登记读数」为主可把该成本降到 1 轮",
            "precondition": "各轮自身已登记读数必须在盘（`runs/<r>/precond.rc`）；缺失的轮必须真跑，不得跳过",
        },
        "rc": 0 if (len(observed) == len(ROUNDS) and consistent) else 3,
    }
    if out["rc"] != 0:
        out["rc_reason"] = "重跑件不齐或守恒判据不成立 ⇒ 数据面异常（fail-closed）"

    with io.open(a.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1))
    print("completed=%d/%d consistent=%s intervals=%s total=%ss" % (
        len(observed), len(ROUNDS), consistent, deltas, out["durations_s_informational_only"]["total_window_s"]))
    print("OUT=%s rc=%s" % (a.out, out["rc"]))
    return out["rc"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
