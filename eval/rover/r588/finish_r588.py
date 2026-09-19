#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R588 收口器: 汇总台账行 + 轮志 + 六格 KPI 打印面（幂等; 缺件 fail-closed）。

用法: python3 eval/rover/r588/finish_r588.py [--dry]
只读各读数件, 不改任何被测/器具读数; 仅追加台账行(r588 已存在则跳过) + 写 report-r588.md。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import time

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r588")
D = os.path.expanduser("~/.agentframework/harness/runs/r588")
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")


def rd(p, req=True):
    if not os.path.isfile(p):
        if req:
            raise SystemExit("MISSING: " + p)
        return None
    return json.load(io.open(p, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    v = rd(os.path.join(PD, "verdict-r588.json"))
    t = rd(os.path.join(PD, "kpi-table-r588.json"))
    pre = rd(os.path.join(D, "precond-r588.json"))
    cand3 = rd(os.path.join(PD, "noartifact-cause-r588.json"))
    cand2 = rd(os.path.join(PD, "timeout-cause-r588.json"), req=False)
    cand4 = rd(os.path.join(PD, "subspec-v2-r588.json"))
    arms = t["readings"]
    c1 = {r["win"]: r for r in arms if r["arm"] == "C1"}
    pd_ = {r["win"]: r for r in arms if r["arm"] == "R588D"}
    defs = v["C1_quality_paired"]
    defs_map = defs.get("D_per_window") or {}
    pooled = v["C5b_swing_vs_effect"]
    c2 = v.get("C2_cost_three_columns")
    c6 = v["C6_steps_face"]
    hits = {"C1_v_all": c1[list(c1)[0]].get("v_all"), "C1_v_incr": c1[list(c1)[0]].get("v_incr"),
            "R588D_v_all": pd_[list(pd_)[0]].get("v_all"), "R588D_v_incr": pd_[list(pd_)[0]].get("v_incr")}
    prev = json.load(io.open(os.path.join(REPO, "eval/rover/r587/verdict-r587.json"), encoding="utf-8"))
    row = {
        "round": "R588",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "kind": ("主线同件扩窗轮 (外部真值 codex 同窗对照; w163..w165 第四窗集) + R587 五项候选并轮收口 "
                 "(零产品源码改动/零新夹具语义/零新开关; src/ 外唯一改动 = 新器具目录 eval/rover/r588)"),
        "change": (
            "① 驱动器 eval/rover/r588/run_r588.sh 派生自 run_r587.sh (轮号/窗口段 160→163/端口 49571→49591/"
            "起手闸摆动余量 130→65[=R587 实测振幅, min(65,cap=151) 不夹]); "
            "② 候选①(第四窗集): 同件同题集只换窗集, 有效窗 7→10, 摆动/效应分离估计与符号检验进 C5b; "
            "③ 候选② eval/rover/r588/timeout_cause_r588.py (TIMEOUT 族 8 例在冻结快照物化副本上三阶复跑 T=10s×3 + T=60s, 判「不收敛 vs 慢」+ 4 例对照); "
            "④ 候选③+⑤ eval/rover/r588/noartifact_cause_r588.py (27 产品跑次分类; NO_ARTIFACT 单例定因=契约块结构不闭合 ⇒ 解析位置与产品报的 BytePositionInLine 逐字节对齐 delta=0; 谓词落点 src/agent/r1/R1Pipeline.cs:147) + "
            "判据面 eval/rover/r588/noartifact-denominator-spec-r588.md; "
            "⑤ 候选④ eval/rover/r588/subspec_v2_r588.py (轴 A v1 恒等复刻通过; 轴 B 加厚: 未分类 18→2, 但对照组判别力 gap 0.007 ⇒ 只作描述性登记)"),
        "readings": {
            "arms": ["C1(codex 外部真值)", "R588D(产品默认档, 剂量键全 unset)"],
            "windows": sorted(c1),
            "reps_per_window": 3,
            "quality_cases_pass_58": {
                "C1_truth_per_window": {w: c1[w]["cases_pass"] for w in sorted(c1)},
                "R588D_cases_per_run": [r["cases_pass"] for r in arms if r["arm"] == "R588D"],
                "R588D_median_per_window": {w: pd_[w]["cases_pass"] for w in sorted(pd_)},
            },
            "paired": {"D_per_window": defs_map, "D_median": defs["D_median"],
                       "valid_windows": len(defs["D_list"]), "floor": defs.get("floor"),
                       "median_floor": defs.get("median_floor"), "pass": defs.get("pass")},
            "pooled_all_sets": {"n_valid_windows": pooled["pooled_n_valid_windows"],
                                "D": pooled["pooled_D"], "median_effect": pooled["pooled_median_effect"],
                                "range_swing": pooled["pooled_range_swing"],
                                "sign": pooled["sign_count"], "p_two_sided": pooled["sign_test_p_two_sided"],
                                "state": pooled["state"]},
            "cost_per_run": c2, "steps": c6["steps"], "hits": hits,
            "iron11_precondition": {"executable_and_correct": pre.get("executable_and_correct"),
                                    "acceptable_scoped": pre.get("acceptable_scoped"),
                                    "blocked": pre.get("blocked"), "blocked_scoped": pre.get("blocked_scoped"),
                                    "self_report_agrees": pre.get("self_report_agrees")},
            "cands": {
                "c1_fourth_window_set": "做 (w163..w165)",
                "c2_timeout_cause": ("做: " + str(cand2.get("class_histogram"))) if cand2 else "做: 见 timeout-cause-r588.json",
                "c3_noartifact_cause": ("做: class=" + json.dumps(cand3["class_distribution"], ensure_ascii=False)
                                       + " delta=" + str(cand3["noartifact_replay"][list(cand3["noartifact_replay"])[0]]["byte_alignment_delta"])),
                "c4_subspec_thickening": ("做: 未分类 %d→%d, 判别力 gap %s" % (
                    cand4["unclassified_before"], cand4["unclassified_after_residual"],
                    cand4["discrimination"]["gap"])),
                "c5_denominator_policy": "做: NO_ARTIFACT 计入配对 + 单列 (1/27=3.7%), unreliable 仅留给真值自身失分窗",
            },
            "arm_identity": rd(os.path.join(D, "bin-sha-check.json"), req=False),
        },
        "artifact": ("eval/rover/r588/{report-r588.md, verdict-r588.json, kpi-table-r588.json, prereg-r588.json, "
                     "run_r588.sh, noartifact-cause-r588.json, timeout-cause-r588.json, subspec-v2-r588.json, "
                     "noartifact-denominator-spec-r588.md}"),
    }
    if a.dry:
        print(json.dumps(row, ensure_ascii=False, indent=1))
        return 0
    # 幂等追加
    lines = [l for l in io.open(LEDGER, encoding="utf-8").read().strip().split("\n") if l.strip()]
    others = [l for l in lines if json.loads(l).get("round") != "R588"]
    n_before = len(lines) - len(others)
    out = others + [json.dumps(row, ensure_ascii=False)]
    io.open(LEDGER, "w", encoding="utf-8").write("\n".join(out) + "\n")
    chk = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8").read().strip().split("\n") if l.strip()]
    assert all(isinstance(x, dict) for x in chk) and len(chk) == len(out)
    print("LEDGER: R588 行 %s (旧行数 %d, 写后总行 %d, 逐行可解析 OK)" % (
        "原地替换" if n_before else "追加", n_before, len(chk)))
    # 轮志
    tbl = ["| 臂 | 回复质量(逐窗/中位/极差) | 调用 | 新算prompt | completion | 命中率(v_all/v_incr) | 步数/轮数 | rc |",
           "|---|---|---|---|---|---|---|---|"]
    for arm, key in (("C1(codex 真值)", "C1"), ("R588D(产品)", "R588D")):
        rr = [r for r in arms if r["arm"] == key]
        q = [r["cases_pass"] for r in rr]
        med = sorted(q)[len(q) // 2] if q else None
        tbl.append("| %s | %s / %s / %s | %s | %s | %s | %s / %s | %s | %s |" % (
            arm, q, med, (max(q) - min(q)) if q else None,
            sum(r.get("calls") or 0 for r in rr), sum(r.get("new_prompt") or 0 for r in rr),
            sum(r.get("completion") or 0 for r in rr),
            rr[0].get("v_all") if rr else None, rr[0].get("v_incr") if rr else None,
            c6["steps"] if key == "R588D" else [r.get("steps_executed") for r in rr],
            v["verdict"]["rc"]))
    rp = json.load(io.open(os.path.join(REPO, "eval/rover/r587/verdict-r587.json"), encoding="utf-8"))
    md = ["# R588 轮志 · 主线同件扩窗轮（第四窗集 w163..w165）+ R587 五项候选并轮收口", "",
          "- 判定: **rc=%s / %s**；铁律 11 前置器 `executable_and_correct=%s` `acceptable_scoped=%s` blocked=%s" % (
              v["verdict"]["rc"], v["verdict"]["judge"], pre.get("executable_and_correct"),
              pre.get("acceptable_scoped"), pre.get("blocked")),
          "- 配对差(有效窗): %s 中位 **%s**（下限 %s）；真值自身失分窗剔除并单列: %s" % (
              defs_map, defs["D_median"], defs.get("median_floor"), v["C0_truth_reliability"]),
          "- 全窗集池化: %d 有效窗, 摆动 %s vs 效应 %s ⇒ **%s**（符号 %s, 双侧 p=%s）" % (
              pooled["pooled_n_valid_windows"], pooled["pooled_range_swing"], pooled["pooled_median_effect"],
              pooled["state"], pooled["sign_count"], pooled["sign_test_p_two_sided"]),
          "- 优化前后同列并排 (R587 → R588): 有效窗 %s → %s；配对中位 %s → %s；摆动 %s → %s" % (
              len(rp["C1_quality_paired"]["D_list"]), len(defs["D_list"]),
              rp["C1_quality_paired"]["D_median"], defs["D_median"],
              (rp.get("C5b_swing_vs_effect") or
               json.load(io.open(os.path.join(REPO, "eval/rover/r587/sixwindow-pool-r587.json"),
                                 encoding="utf-8"))["swing_vs_effect"]).get("swing_over_pooled_6w"),
              pooled["pooled_range_swing"]), "",
          "## KPI 表（同题面/同夹具/同窗内对照）", ""] + tbl + ["",
          "## 候选台账（R587 遗留五项，全部并入本轮）", ""]
    for k, s in row["readings"]["cands"].items():
        md.append("- `%s` — %s" % (k, s))
    md += ["", "## 诚实边界", "",
           "- 单窗读数不得作能力结论；摆动 ≥ 效应时该轴非承重变量（本件/本题集范围内）。",
           "- 候选④的子类**判别力 gap ≈ 0**（对照组命中率 0.882 vs 未分类组 0.889）⇒ 只作描述性登记，不改判据、不宣称能力。",
           "- 候选③ 的**字符级**病因未定因（残余已入档）。",
           "- 真值臂本轮出现长命令 120s yield 轮询（codex 侧行为）⇒ 耗时读数只作指示性。", "",
           "## 证据路径", "",
           "- `eval/rover/r588/{prereg-r588.json, run_r588.sh, kpi_r588.py, verdict-r588.json, kpi-table-r588.json}`",
           "- `eval/rover/r588/{noartifact-cause-r588.json, timeout-cause-r588.json, subspec-v2-r588.json}`",
           "- `eval/rover/r588/noartifact-denominator-spec-r588.md`",
           "- 台账行: `eval/capability/kpi.jsonl` (round=R588)"]
    io.open(os.path.join(PD, "report-r588.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("REPORT: eval/rover/r588/report-r588.md")
    print(json.dumps({"verdict": v["verdict"], "D_map": defs_map, "D_median": defs["D_median"],
                      "pooled": {k: pooled[k] for k in ("pooled_n_valid_windows", "pooled_median_effect",
                                                        "pooled_range_swing", "sign_count",
                                                        "sign_test_p_two_sided", "state")},
                      "truth_per_window": {w: c1[w]["cases_pass"] for w in sorted(c1)},
                      "product_per_run": [r["cases_pass"] for r in arms if r["arm"] == "R588D"],
                      "calls": {"C1": sum(r.get("calls") or 0 for r in arms if r["arm"] == "C1"),
                                "R588D": sum(r.get("calls") or 0 for r in arms if r["arm"] == "R588D")},
                      "hits": hits, "steps": c6["steps"],
                      "precond": {"correct": pre.get("executable_and_correct"), "rc_blocked": pre.get("blocked")}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
