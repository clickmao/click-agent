#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R640 · 判决件（只读定因轮 + 缺口族可执行前置步骤）。

输入（全部为已落盘读数件，本件不执行被测面）：
  · `out/attrib-r640.json`    ← `attrib_r640.py`（J0–J5b / J9）
  · `out/precheck-r640.json`  ← `wythoff_precheck_r640.py --selfcheck`（J6 两侧齿证）
  · `out/posthoc-r639.json`   ← `posthoc_r640.py --face r639`（J8 常设件）
  · `prereg-r640.json`        ← 预注册（声明先于跑；本件校验其 sha 与关键段在位）

rc 分层（承 R621/R631 v4）：0 = 全部判据绿 / 1 = 能力层或次级判据红 / 2 = 器具缺陷（锚面·负控·守恒） /
3 = 输入缺失或不可判。**判据器自身的假绿防护**：每个键无条件计算，缺项写 None + `informational`。

用法:
  python3 judge_r640.py                       # 出判决件
  python3 judge_r640.py --selftest            # 影子自检（零被测执行，合成输入 + 真实读数投影）
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r640")
OUT = os.path.join(PD, "out")


def jload(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def sha12(p):
    try:
        return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]
    except Exception:  # noqa: BLE001
        return None


def core(attrib, precheck, posthoc, prereg, precheck_v2=None):
    v = {}
    # ---- 输入在位（缺项 ⇒ rc=3，不判绿）
    v["inputs"] = {"attrib": attrib is not None, "precheck": precheck is not None,
                   "posthoc": posthoc is not None, "prereg": prereg is not None}
    if not all(v["inputs"].values()):
        missing = [k for k, ok in v["inputs"].items() if not ok]
        v["rc"] = 3
        v["verdict"] = {"rc": 3, "label": "输入缺失", "missing": missing}
        return v

    # ---- J0 oracle 正控 + 变异负控
    nc = attrib.get("J5b_negctl", {})
    v["J0_oracle_control"] = {
        "positive": nc.get("oracle_positive_control"),
        "positive_pass": nc.get("oracle_positive_pass"),
        "mutant_pass": nc.get("oracle_mutant_pass"),
        "mutant_teeth": nc.get("oracle_mutant_teeth"),
        "pass": bool(nc.get("oracle_positive_pass") and nc.get("oracle_mutant_teeth")),
    }

    # ---- J1 交叉校验 / J2 守恒
    j1 = attrib.get("J1_replay_cross_validation", {})
    v["J1_replay_cross_validation"] = {"mismatch": j1.get("mismatch"), "pass": j1.get("pass"),
                                       "detail": j1.get("detail", [])}
    v["J2_conservation"] = attrib.get("J2_conservation", {})

    # ---- J3 机制探针
    j3 = attrib.get("J3_mechanism_probe", {})
    v["J3_mechanism_probe"] = {"mechanism_histogram": j3.get("mechanism_histogram"),
                               "r637_discriminant_true_positive": j3.get("r637_discriminant_true_positive"),
                               "r637_discriminant_false_positive": j3.get("r637_discriminant_false_positive"),
                               "r637_discriminant_transfers": j3.get("r637_discriminant_transfers"),
                               "by_run": j3.get("by_run", [])}

    # ---- J4/J5 行级定因 + 三态
    mf = attrib.get("J4_minfix", [])
    confirmed = {m["run"]: m["confirmed"] for m in mf}
    states = {m["run"]: m["state"] for m in mf}
    v["J4_line_level_attribution"] = {"confirmed": confirmed, "states": states,
                                      "n_failing_runs_analyzed": len(mf),
                                      "all_confirmed": bool(mf) and all(confirmed.values())}
    v["J5_three_state_verdict"] = {
        "state_product_defect": sorted(r for r, s in states.items() if s.startswith("能力缺陷")),
        "state_not_attributed": sorted(r for r, s in states.items() if not s.startswith("能力缺陷")),
        "fixture_defect": [] if v["J0_oracle_control"]["pass"] else ["oracle 与题面期望不一致"],
        "note": "夹具缺陷由 J0 正控排他；本态为空 = 未发现夹具侧成因",
    }

    # ---- J5b 行级变异负控
    v["J5b_negctl"] = {k: nc.get(k) for k in
                       ("N1_null_rewrite", "N2_correct_impl", "N3_always_lose", "on_run")}

    # ---- J6 可执行前置步骤（两侧齿证）
    t = precheck.get("teeth", {})
    v["J6_executable_precondition"] = {
        "round": "v1(pre-registered)",
        "pos_all_pass_runs_rc0": t.get("POS_all_pass_runs_rc0"),
        "neg_all_fail_runs_rc1": t.get("NEG_all_fail_runs_rc1"),
        "pass": t.get("pass"),
        "per_run_rc": {r["run"]: r["rc"] for r in precheck.get("readings", [])},
        "failed_predicates": {r["run"]: sorted(k for k, x in r.get("predicates", {}).items()
                                               if not x["pass"])
                              for r in precheck.get("readings", []) if r.get("rc") == 1},
    }

    t2 = (precheck_v2 or {}).get("teeth", {})
    v["J6v2_corrected_instrument"] = {
        "round": "v2(checks_posthoc; 下轮重注册)",
        "instrument_sha16": (precheck_v2 or {}).get("instrument"),
        "expectations_machine_derived": bool((precheck_v2 or {}).get("expectations")),
        "source_of_expectations": ((precheck_v2 or {}).get("expectations") or {}).get("source"),
        "pos_all_pass_runs_rc0": t2.get("POS_all_pass_runs_rc0"),
        "neg_all_fail_runs_nongreen": t2.get("NEG_all_fail_runs_nongreen"),
        "synthetic_arms_rc": t2.get("synthetic_arms_rc"),
        "pass": t2.get("pass") is True,
        "rc_by_run": {r["run"]: r["rc"] for r in (precheck_v2 or {}).get("readings", [])},
        "predicate_violation_counts": {r["run"]: {k: x["n_viol"] for k, x in r.get("predicates", {}).items()
                                                  if not x["pass"]}
                                       for r in (precheck_v2 or {}).get("readings", []) if r.get("rc") == 1},
        "note": ("v1 两侧双红 = 器具误规格（手写期望表 + 把「交付物过慢」归 rc=2）⇒ v2 机取期望表 + "
                 "P0_budget 独立谓词 + 预算 300s；预注册判据照原样判（J6 FAIL），本条为**事后修正**、不改判 v1"),
    }

    # ---- J7 F_lift_min 分辨力未行使条款（承 R639 候选②）
    fl = (jload(os.path.join(REPO, "eval/rover/r639/verdict-r639.json"), {}) or {}).get("F_lift_min", {})
    worst, med = fl.get("min_lift"), fl.get("min_lift_median_form")
    thr = fl.get("threshold_cases", -2)
    if worst is None or med is None:
        exercised = None
    else:
        exercised = (worst < thr) != (med < thr)     # 两式判决方向是否不同 ⇒ 分辨力是否被行使
    v["J7_f_lift_resolution_clause"] = {
        "source_round": "R639", "worst_form": worst, "median_form": med, "threshold": thr,
        "lift_resolution_exercised": exercised,
        "claimed_exercised_ok": exercised is False,   # R639 实读数两式同向 ⇒ 应算出 False
        "pass": exercised is False,
        "rule": "两式同向 ⇒ `lift_resolution_exercised=False` ⇒ **禁**把 R636 冻结面证据说成真机行使；键缺失/为 True ⇒ 判红（声明滞后类）",
    }

    # ---- J8 posthoc 常设件
    s = posthoc.get("summary", {})
    v["J8_posthoc_standing_piece"] = {"n_runs": s.get("n_runs"),
                                      "rc_nonzero_but_stdout_match_total": s.get("rc_nonzero_but_stdout_match_total"),
                                      "may_be_underestimated": s.get("may_be_underestimated"),
                                      "by_run": s.get("by_run", {}),
                                      "pass": posthoc.get("rc") == 0,
                                      "note": "该列由「未生成 ⇒ 不可判」转为可判（常设件，`--face` 参数化）"}

    # ---- J9 确定性
    v["J9_determinism"] = attrib.get("J9_determinism", {"pass": None, "state": "informational"})

    # ---- rc 分层
    hard = []       # rc=2 器具层
    cap = []        # rc=1 能力/次级层
    if not v["J0_oracle_control"]["pass"]:
        hard.append("J0 oracle 正控/变异负控未过")
    if v["J1_replay_cross_validation"]["pass"] is False:
        hard.append("J1 重放与冻结读数不一致（器具读法错）")
    if v["J2_conservation"] and v["J2_conservation"].get("pass") is False:
        hard.append("J2 守恒式不成立")
    for k in ("N1_null_rewrite", "N2_correct_impl", "N3_always_lose"):
        if isinstance(v["J5b_negctl"].get(k), dict) and v["J5b_negctl"][k].get("verdict") == "FAIL":
            hard.append("J5b %s 方向错（器具无牙）" % k)
    if v["J6_executable_precondition"]["pass"] is False:
        hard.append("J6 可执行前置步骤（**v1 预注册器具**）两侧齿证未过 ⇒ 器具缺陷（v2 单列，下轮重注册）")
    if v.get("J6v2_corrected_instrument", {}).get("pass") is False:
        hard.append("J6v2 修正器具两侧齿证未过")
    if v["J9_determinism"].get("pass") is False:
        hard.append("J9 确定性失败")
    if v["J7_f_lift_resolution_clause"]["pass"] is False:
        hard.append("J7 F 分辨力条款未过（声明滞后类）")
    if not v["J4_line_level_attribution"]["all_confirmed"]:
        cap.append("J4 有失败跑次未行级定因（记「未测到」，非「无缺陷」）")
    if v["J3_mechanism_probe"]["r637_discriminant_transfers"] is False:
        cap.append("J3 R637 判别式不跨窗迁移（轮内证伪）")

    rc = 2 if hard else (1 if cap else 0)
    v["rc"] = rc
    v["rc_semantics"] = "0 全绿 / 1 能力或次级红 / 2 器具缺陷 / 3 输入缺失"
    v["verdict"] = {"rc": rc, "hard": hard, "capability_secondary": cap,
                    "label": ("器具缺陷" if rc == 2 else ("能力/次级未过" if rc == 1 else "全绿"))}
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=os.path.join(PD, "verdict-r640.json"))
    a = ap.parse_args()
    attrib = jload(os.path.join(OUT, "attrib-r640.json"))
    pre = jload(os.path.join(OUT, "precheck-r640-v1.json"))
    pre2 = jload(os.path.join(OUT, "precheck-r640-v2.json"))
    post = jload(os.path.join(OUT, "posthoc-r639.json"))
    prereg = jload(os.path.join(PD, "prereg-r640.json"))

    if a.selftest:
        cases = []
        # S1 真读数 ⇒ rc 按公式复现（不硬编码期望 rc，只断言键齐全 + 无异常）
        v = core(attrib, pre, post, prereg, pre2)
        cases.append(("S1_real_readings", v["rc"] in (0, 1, 2, 3)
                      and set(v) >= {"J0_oracle_control", "J1_replay_cross_validation",
                                     "J4_line_level_attribution", "J6_executable_precondition",
                                     "J7_f_lift_resolution_clause", "J8_posthoc_standing_piece"}))
        # S2 缺输入 ⇒ rc=3（fail-closed）
        v2 = core(None, pre, post, prereg, pre2)
        cases.append(("S2_missing_input_rc3", v2["rc"] == 3))
        # S3 J6 两侧齿证翻面 ⇒ rc 抬 2
        pre_bad = json.loads(json.dumps(pre))
        pre_bad["teeth"]["POS_all_pass_runs_rc0"] = False
        pre_bad["teeth"]["pass"] = False
        v3 = core(attrib, pre_bad, post, prereg, pre2)
        cases.append(("S3_precheck_teeth_flip_rc2", v3["rc"] == 2))
        # S4 J7 条款翻面（宣称已行使）⇒ rc 抬 2
        tmp_v639 = os.path.join(REPO, "eval/rover/r639/verdict-r639.json")
        saved = io.open(tmp_v639, encoding="utf-8").read()
        try:
            d = json.loads(saved)
            orig = d["F_lift_min"].get("min_lift_median_form")
            d["F_lift_min"]["min_lift_median_form"] = 0     # 造「两式方向不同」⇒ exercised=True（中位式不跨阈）
            io.open(tmp_v639, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
            v4 = core(attrib, pre, post, prereg, pre2)
            flipped = v4["J7_f_lift_resolution_clause"]["lift_resolution_exercised"]
        finally:
            io.open(tmp_v639, "w", encoding="utf-8").write(saved)   # 逐字节复原
            assert io.open(tmp_v639, encoding="utf-8").read() == saved
        cases.append(("S4_f_lift_clause_teeth", flipped is True and v4["rc"] == 2 and orig == -9))
        # S5 J1 不一致 ⇒ rc=2（器具读法错优先于被测结论）
        at_bad = json.loads(json.dumps(attrib))
        at_bad["J1_replay_cross_validation"]["pass"] = False
        v5 = core(at_bad, pre, post, prereg, pre2)
        cases.append(("S5_j1_mismatch_rc2", v5["rc"] == 2))
        # S6 J4 未定因 ⇒ rc≥1 但非 2（能力层，不得混入器具层）
        at_c = json.loads(json.dumps(attrib))
        pre_ok = json.loads(json.dumps(pre))
        pre_ok["teeth"]["pass"] = True          # 隔离：陈 J6(v1) 器具红，只测能力层是否落 rc=1
        for m in at_c["J4_minfix"]:
            m["confirmed"] = []
            m["state"] = "未测到（锚点缺失或候选全不生效）"
        v6 = core(at_c, pre_ok, post, prereg, pre2)
        cases.append(("S6_not_attributed_is_capability_layer", v6["rc"] == 1))
        ok = all(c[1] for c in cases)
        io.open(os.path.join(PD, "selftest-r640.json"), "w", encoding="utf-8").write(
            json.dumps({"cases": [{"id": i, "pass": p} for i, p in cases], "pass": ok},
                       ensure_ascii=False, indent=1))
        for i, p in cases:
            print(("PASS " if p else "FAIL ") + i)
        print("SELFTEST", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    v = core(attrib, pre, post, prereg, pre2)
    v["round"] = "R640"
    v["kind"] = ("只读承重缺口定因（wythoff 族；R639 冻结面 12 跑次）+ 缺口族可执行前置步骤落地 "
                 "+ 判据/器具面收口（F 未行使条款 · posthoc 常设件）")
    v["instrument_source"] = {"attrib": sha12(os.path.join(PD, "attrib_r640.py")),
                              "precheck": sha12(os.path.join(PD, "wythoff_precheck_r640.py")),
                              "posthoc": sha12(os.path.join(PD, "posthoc_r640.py")),
                              "judge": sha12(os.path.abspath(__file__)),
                              "prereg_sha256": hashlib.sha256(
                                  io.open(os.path.join(PD, "prereg-r640.json"), "rb").read()).hexdigest()}
    v["prereg_declared_before_run"] = bool(prereg.get("written_before_run"))
    v["honest_bounds"] = [
        "只读复算面 ≠ 真机新跑 ⇒ 读数只对**R639 冻结面**成立；本轮**不宣称生产已修**",
        "行级定因来自**副本上的最小修复实验** ⇒ 只证「缺陷在被改那一行」，不证生产链路只有这一处",
        "无单变量轴 / 无新窗集 / 无新跑次 ⇒ **跨轮禁相减**（RF0005 §6 红线 4）；n=9（P）/3（真值）欠功率",
        "铁律 11 可执行前置器**不适用**（无真机臂、无降幅宣称）—— 显式声明，非跳步掩盖",
        "J8 posthoc 为 30s 超时口径（冻结跑 10s）⇒ 只作**上界**读数",
        "三档终局目标读数（32 ms 级 / 快 50× / −95% / 成本 −85~91%）本轮**不动不宣称**",
    ]
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(v, ensure_ascii=False, indent=1))
    print(json.dumps({"rc": v["rc"], "label": v["verdict"]["label"],
                      "hard": v["verdict"]["hard"], "cap": v["verdict"]["capability_secondary"],
                      "J4": v["J4_line_level_attribution"]["confirmed"],
                      "J6_pass_v1": v["J6_executable_precondition"]["pass"],
                      "J6v2_pass": v["J6v2_corrected_instrument"]["pass"],
                      "J7": v["J7_f_lift_resolution_clause"]["lift_resolution_exercised"],
                      "J8_total": v["J8_posthoc_standing_piece"]["rc_nonzero_but_stdout_match_total"]},
                     ensure_ascii=False, indent=1))
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
