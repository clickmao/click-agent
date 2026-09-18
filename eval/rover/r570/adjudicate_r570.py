#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R570 判决驱动器: 复用 R561 判据 v2 装置 (verdict_r561.py 的 judge/decide/selftest),
**零逻辑复制** —— 只把 R570 的窗集/臂集喂进去, 并把「臂窗 VOID 归属」按运行时
内存扩展 REPORTS 的方式补上 (不修改任何已提交器具文件, 前后 sha 相同即证保形)。

判据口径来源 = docs/external-reference-harness.md §12 (R562 入册), 本件不重定义口径
(防「同一判据两份实现」漂移)。

rc 语义 (沿用装置): 0 全过 / 1 判据未过 (被测或前提) / 2 器具缺陷 / 3 缺侧或不可判。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
WINS = ["w143", "w144", "w145", "w146", "w147", "w148"]
ARMS = ["C1", "R570E0", "R570E2"]
DEVICE = os.path.join(REPO, "eval/rover/r561/verdict_r561.py")


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def load_device():
    spec = importlib.util.spec_from_file_location("verdict_r561_dev", DEVICE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    before = sha(DEVICE)
    V = load_device()
    # 运行时扩展 REPORTS (只为 VOID 臂窗归属: 读 r570 落盘 report.json 的 stage/cases_pass)
    V.REPORTS["R570"] = {"wins": WINS, "dir": "eval/rover/r570/evidence/windows", "arms": ARMS}
    mat = json.load(io.open(a.matrix, encoding="utf-8"))
    st = V.selftest()
    j = V.judge(mat, windows=WINS, arms=ARMS, primary_windows=WINS)
    dec = V.decide(mat, j, st["has_teeth"])
    after = sha(DEVICE)

    keep = ("reliable_windows", "deltas", "delta_median", "delta_min", "named_windows",
            "arm_median_cases", "arm_range_cases", "pass", "fail_reason")
    out = {
        "round": "R570",
        "instrument": "adjudicate_r570.py (复用 verdict_r561.py judge/decide/selftest; 零逻辑复制)",
        "criterion_version": "v2 (逐窗并列 + 真值崩窗 unreliable[MARGIN=3] + 配对判据[n>=3, 无窗<=-3, 中位>=-2] + VOID 单列)",
        "criterion_source": "docs/external-reference-harness.md §12",
        "manipulation": {
            "windows": WINS, "arms": ARMS,
            "device_runtime_extension": "V.REPORTS['R570'] (内存内; VOID 臂窗归属)",
            "device_file_sha_before": before[:16], "device_file_sha_after": after[:16],
            "device_unchanged": before == after,
        },
        "rc": dec["rc"],
        "verdict": {0: "PASS", 1: "FAIL(被测/前提)", 2: "INSTRUMENT_DEFECT",
                    3: "ABSTAIN(缺侧/不可判)"}[dec["rc"]],
        "blocked": dec["blocked"],
        "rowcount_bad": dec["rowcount_bad"],
        "missing_truth_windows": dec["missing_truth_windows"],
        "truth_cases": j["truth_cases"], "truth_median": j["truth_median"],
        "truth_range": j["truth_range"], "truth_status": j["truth_status"],
        "unreliable_windows": j["unreliable_windows"], "reliable_windows": j["reliable_windows"],
        "arms": {x: {k: v[k] for k in keep if k in v} for x, v in j["arms"].items()},
        "fail_arms": j["fail_arms"],
        "void_arm_windows": j["void_arm_windows"],
        "selftest": st,
        "family_distribution": j["family_distribution"],
        "per_case_stability": j["per_case_stability"],
        "informational": {"criterion_keys_unconditional": True,
                          "note": "红绿只由 arms[*].pass 决定; 中位/极差为信息项"},
    }
    if not out["manipulation"]["device_unchanged"]:
        out["rc"] = 2
        out["verdict"] = "INSTRUMENT_DEFECT"
        out["blocked"] = out["blocked"] + ["device_file_written_during_adjudication"]
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": out["rc"], "verdict": out["verdict"], "blocked": out["blocked"],
                      "truth_median": out["truth_median"], "truth_range": out["truth_range"],
                      "truth_status": out["truth_status"], "fail_arms": out["fail_arms"],
                      "arms": {k: {"delta_median": v.get("delta_median"),
                                   "delta_min": v.get("delta_min"),
                                   "arm_median": v.get("arm_median_cases"),
                                   "pass": v.get("pass")} for k, v in out["arms"].items()},
                      "selftest": "%d/%d" % (st["n_ok"], st["n"])},
                     ensure_ascii=False))
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
