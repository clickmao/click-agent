#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R561 判定器 v2 (离线判定/收口轮).

修订面 (R560 候选②): 质量判据由「臂中位 >= 真值中位-2 ∧ 极差<=5」改为
  **逐窗并列 + 真值崩窗标 unreliable** 的两栏读法 —— 旧判据在真值自身崩窗 (w108=47/58, w112=52/58,
  真值极差 11 > 阈值 5) 上**结构性不可达**, 属判据缺陷。

判据字段一律**无条件计算** (缺项写 None / informational), 判决只读本文件产出的 verdict JSON。
rc 语义: 0 全过 / 1 判据未过(真红) / 2 器具缺陷(自检不过·复算不一致·缺字段) / 3 缺侧或不可判。
影子自检: 上线前用 6 例合成矩阵逐例断言预期 rc (含必须判红 / 必须弃权 / 必须器具缺陷三态)。
"""
from __future__ import annotations
import argparse
import io
import json
import sys
from statistics import median

EXP_N = 58
TRUTH_ARM = "C1"
MARGIN = 3          # 真值崩窗判定: truth <= median(truth) - MARGIN
PAIR_MIN = -2       # 逐窗配对中位下限
PAIR_FLOOR = -3     # 单窗配对下限 (<= 此值即点名)
MIN_RELIABLE = 3
REPO = "/home/agentuser/AgentFramework"
# 臂窗 VOID 口径 (与 R559/R560 两轮既有惯例一致: 契约死/零用例的臂窗不入质量读数, 单列)
REPORTS = {"R559": {"wins": ["w104", "w105", "w106"], "dir": "eval/rover/r559/evidence/windows",
                    "arms": ["C1", "R559B0", "R559B3"]},
           "R560": {"wins": ["w107", "w108", "w109", "w110", "w111", "w112"], "dir": "eval/rover/r560/evidence/windows",
                    "arms": ["C1", "R560B0", "R560B3"]}}


def void_arm_windows():
    """从已落盘 report.json 取「该臂窗无有效产物」标记 (rc/stage/cases 三字段), 只读。"""
    import os
    out = {}
    for rk, cfg in REPORTS.items():
        for w in cfg["wins"]:
            p = os.path.join(REPO, cfg["dir"], w, "report.json")
            if not os.path.isfile(p):
                continue
            for row in json.load(io.open(p, encoding="utf-8")).get("rows", []):
                if row.get("stage") == "contract" or row.get("cases_pass") == 0:
                    out["%s|%s|%s" % (rk, w, row["arm"])] = "arm_void(rc=%s stage=%s cases=%s)" % (
                        row.get("rc"), row.get("stage"), row.get("cases_pass"))
    return out


def med(xs):
    xs = [x for x in xs if x is not None]
    return median(xs) if xs else None


def _rows(famcnt):
    """合成用例行: 供分布/稳定性读数使用 (自检夹具用)。"""
    out, i = [], 0
    for fam, n in famcnt.items():
        for k in range(n):
            out.append({"idx": i, "name": "%s#%02d-fake" % (fam, i), "family": fam,
                        "vis": "public" if k == 0 else "hidden", "ok": True, "why": ""})
            i += 1
    return out


def synth(truth, arms, fams=None, drop=(None, None), bad_rows_for=None):
    """truth/arms: {win: cases_pass}; drop=(win, arm) 制造缺字段。"""
    fams = fams or {"nim": 15, "wythoff": 15, "life": 14, "sub": 14}
    w = {}
    for win, t in truth.items():
        w[win] = {"round": "SYN"}
        for arm, vals in list(arms.items()) + [(TRUTH_ARM, truth)]:
            n = vals[win] if isinstance(vals, dict) else vals
            if drop == (win, arm):
                w[win][arm] = {"error": "missing"}
                continue
            rows = _rows(fams)
            if bad_rows_for == (win, arm):
                rows = rows[:5]
            w[win][arm] = {"pass": n, "total": EXP_N, "rc": 0 if n == EXP_N else 1, "rows": rows}
    return {"windows": w, "errors": [], "xref_disagreements": [], "grader": {"sha256": "synth"}}


def judge(mat, windows=None, arms=None, primary_windows=None):
    """主判定; 只读矩阵。返回**无条件**键的 dict。

    器具自捕 (R561 二捕): 首版把 `side_arms` 从**全部窗**收集, 而主判窗只取最新一轮 ⇒
    上一轮的臂在主判窗内不存在 ⇒ n=0 ⇒ 被记成「质量判据未过」(伪红, 会把不存在于该窗集的臂
    算进 fail_arms)。修法 = 臂集按**主判窗集**收集 (作用域一致), 非主判窗的臂单列在各自视图里。
    """
    wins = windows or sorted(mat["windows"].keys())
    wmap = mat["windows"]
    prim = primary_windows or wins
    win_round = {w: rk for rk, cfg in REPORTS.items() for w in cfg["wins"]}
    VOID = void_arm_windows()
    truth = {w: (wmap[w].get(TRUTH_ARM) or {}).get("pass") for w in wins}
    truth_tot = {w: (wmap[w].get(TRUTH_ARM) or {}).get("total") for w in wins}
    side_arms = arms or sorted({a for w in prim for a in wmap[w]
                                if a != TRUTH_ARM and a != "round" and not str(a).startswith("_")})

    tvals = [v for v in truth.values() if isinstance(v, int)]
    tmed = med(tvals)
    tstat = {}
    for w in wins:
        v = truth.get(w)
        if not isinstance(v, int):
            tstat[w] = "missing"
        elif tmed is not None and v <= tmed - MARGIN:
            tstat[w] = "unreliable"
        else:
            tstat[w] = "reliable"
    reliable = [w for w in wins if tstat[w] == "reliable"]

    def paired(ws):
        d = {a: {} for a in side_arms}
        for w in ws:
            for a in side_arms:
                if VOID.get("%s|%s|%s" % (win_round.get(w), w, a)):
                    d[a][w] = None  # VOID 臂窗 (契约死/零用例): 不入配对, 单列
                    continue
                av = (wmap[w].get(a) or {}).get("pass")
                d[a][w] = (av - truth[w]) if isinstance(av, int) and isinstance(truth[w], int) else None
        return d

    prim = primary_windows or wins
    prim_rel = [w for w in prim if tstat.get(w) == "reliable"]
    dprim = paired(prim_rel)
    dall = paired(reliable)
    arms_res, fail_arms = {}, []
    for a in side_arms:
        ds = [v for v in dprim[a].values() if v is not None]
        rng = [v for v in ((wmap[w].get(a) or {}).get("pass") for w in prim) if isinstance(v, int)]
        ok_n = len(ds) >= MIN_RELIABLE
        bad_floor = sorted([w for w, v in dprim[a].items() if v is not None and v <= PAIR_FLOOR])
        med_ok = (med(ds) is not None and med(ds) >= PAIR_MIN)
        passed = bool(ok_n and not bad_floor and med_ok)
        if not passed:
            fail_arms.append(a)
        arms_res[a] = {"reliable_windows": len(ds), "deltas": dprim[a], "delta_median": med(ds),
                       "delta_min": min(ds) if ds else None, "named_windows": bad_floor,
                       "arm_median_cases": med(rng), "arm_range_cases": (max(rng) - min(rng)) if rng else None,
                       "pass": passed,
                       "fail_reason": None if passed else {
                           "insufficient_windows": not ok_n, "named_windows": bad_floor, "median_below": not med_ok}}
    # 族 × 窗 × 臂 分布 + 逐例稳定性 (信息项)
    fam_dist, stab = {}, {}
    for a in side_arms:
        pc = {}
        for w in wins:
            rec = wmap[w].get(a) or {}
            for r in rec.get("rows") or []:
                pc.setdefault(r["idx"], {"family": r["family"], "vis": r["vis"], "pass": []})
                pc[r["idx"]]["pass"].append(1 if r["ok"] else 0)
        stab[a] = {"always_pass": sorted([i for i, v in pc.items() if v["pass"] and sum(v["pass"]) == len(v["pass"])]),
                   "always_fail": sorted([i for i, v in pc.items() if v["pass"] and sum(v["pass"]) == 0]),
                   "wobble": sorted([i for i, v in pc.items() if v["pass"] and 0 < sum(v["pass"]) < len(v["pass"])]),
                   "n_windows": len(wins)}
        fam_dist[a] = {}
        for w in wins:
            for r in (wmap[w].get(a) or {}).get("rows") or []:
                fam_dist[a].setdefault(r["family"], {}).setdefault(w, [0, 0])
                fam_dist[a][r["family"]][w][1] += 1
                if r["ok"]:
                    fam_dist[a][r["family"]][w][0] += 1
    return {"windows": wins, "primary_windows": prim, "truth_cases": truth, "truth_total": truth_tot,
            "truth_median": tmed, "truth_range": (max(tvals) - min(tvals)) if tvals else None,
            "truth_status": tstat, "reliable_windows": reliable, "unreliable_windows": [w for w in wins if tstat[w] == "unreliable"],
            "arms": arms_res, "fail_arms": fail_arms, "family_distribution": fam_dist, "per_case_stability": stab,
            "void_arm_windows": VOID,
            "informational": {"deltas_all_reliable_9w": dall, "note": "极差/中位为信息项, 质判红绿只由 arms[*].pass 决定"}}


def selftest():
    """6 例合成矩阵: 每条 rc 分支至少一例; 含必须判红与必须弃权的成对夹具。"""
    T = [56, 58, 58, 58, 58]
    wins = ["s1", "s2", "s3", "s4", "s5"]
    tr_ok = {w: 58 for w in wins}
    cases = []
    # S1 全绿 => rc0
    m = synth(tr_ok, {"A0": {w: 58 for w in wins}, "A3": {w: 58 for w in wins}})
    cases.append(("S1_all_green", m, 0, None))
    # S2 被测崩一窗 => rc1 (配对 -8)
    m = synth(tr_ok, {"A0": {**{w: 58 for w in wins}, "s3": 50}})
    cases.append(("S2_arm_shortfall", m, 1, "A0"))
    # S3 真值崩窗 (median 58 - 3 = 55; 47 与 52 必标 unreliable) 且被测在崩窗缺分 => 该窗被排除, 其余全对 => rc0
    tr = {**tr_ok, "s3": 47, "s4": 52}
    m = synth(tr, {"A0": {**{w: 58 for w in wins}, "s3": 50, "s4": 40}})
    cases.append(("S3_truth_collapse_excluded", m, 0, None))
    # S4 缺真值臂 => 缺侧 rc3
    m = synth(tr_ok, {"A0": {w: 58 for w in wins}})
    for w in wins:
        m["windows"][w].pop(TRUTH_ARM, None)
    cases.append(("S4_truth_arm_absent", m, 3, None))
    # S5 缺字段/行数不足 => 器具缺陷 rc2 (行数 != 58)
    m = synth(tr_ok, {"A0": {w: 58 for w in wins}}, bad_rows_for=("s2", "A0"))
    cases.append(("S5_truncated_rows", m, 2, None))
    # S6 有效真值窗不足 3 => 弃权 rc3
    tr2 = {"s1": 58, "s2": 58, "s3": None, "s4": None, "s5": None}
    m = synth({k: v for k, v in tr2.items() if isinstance(v, int)}, {"A0": {"s1": 58, "s2": 58}},
              fams={"nim": 15, "wythoff": 15, "life": 14, "sub": 14})
    for w in ("s3", "s4", "s5"):
        m["windows"].setdefault(w, {})
        m["windows"][w]["A0"] = {"error": "missing"}
    cases.append(("S6_insufficient_reliable", m, 3, None))
    out = []
    for name, m, exp, failarm in cases:
        r = judge(m)
        got = decide(m, r, True)["rc"]
        out.append({"fixture": name, "expected_rc": exp, "got_rc": got, "ok": got == exp,
                    "expected_fail_arm": failarm, "fail_arms": r["fail_arms"],
                    "unreliable_windows": r["unreliable_windows"]})
    return {"fixtures": out, "n": len(out), "n_ok": sum(1 for x in out if x["ok"]),
            "has_teeth": all(x["ok"] for x in out)}


def _rowcount_bad(mat):
    bad = []
    for w, am in mat["windows"].items():
        for a, rec in am.items():
            if a == "round":
                continue
            if isinstance(rec, dict) and rec.get("error"):
                continue
            n = len(rec.get("rows") or [])
            if n != EXP_N:
                bad.append({"win": w, "arm": a, "rows": n})
    return bad


def decide(mat, r, selftest_ok: bool):
    """判决: 只由判据面决定; rc 分类 fail-closed。

    器具自捕 (R561 首跑): 首版把「影子自检结果」写成从 `r` 内部键读 (`r["selftest"]`),
    而夹具回放时 `r` 里没有该键 ⇒ 6/6 夹具全部 rc=2。这正是自检要抓的形态 (器具自检必须
    由**外部传入**结论, 不能要求被检对象自带结论)。修法 = 显式入参, 断言不放宽。
    """
    blocked = []
    if not selftest_ok:
        blocked.append("judge_selftest_failed")
    bad = _rowcount_bad(mat)
    if bad or mat.get("errors") or mat.get("xref_disagreements"):
        blocked.append("instrument_or_input_defect")
    missing_truth = [w for w, s in r["truth_status"].items() if s == "missing"]
    rc = 2 if any(b in ("judge_selftest_failed", "instrument_or_input_defect") for b in blocked) else None
    if rc is None and (missing_truth or len([w for w in r["primary_windows"] if r["truth_status"][w] == "reliable"]) < MIN_RELIABLE):
        rc = 3
        blocked.append("insufficient_reliable_windows_or_side")
    if rc is None and r["fail_arms"]:
        rc = 1
        blocked.append("quality_paired_shortfall:" + ",".join(r["fail_arms"]))
    if rc is None:
        rc = 0
    return {"rc": rc, "blocked": blocked, "rowcount_bad": bad, "missing_truth_windows": missing_truth}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    mat = json.load(io.open(a.matrix, encoding="utf-8"))

    st = selftest()
    r560 = ["w107", "w108", "w109", "w110", "w111", "w112"]
    r559 = ["w104", "w105", "w106"]
    j = judge(mat, primary_windows=r560)
    j["selftest"] = st
    def view(ws):
        try:
            return judge(mat, windows=ws, primary_windows=ws)
        except Exception as e:  # noqa: BLE001
            return {"error": "%s: %s" % (type(e).__name__, str(e)[:120])}
    j["r559_view"] = view(r559)
    dec = decide(mat, j, st["has_teeth"])

    out = {"round": "R561", "instrument": "verdict_r561.py",
           "criterion_version": "v2 (逐窗并列 + 真值崩窗 unreliable; 旧 v1 = 绝对中位/极差 <=5 结构性不可达)",
           "rc": dec["rc"], "verdict": {0: "PASS", 1: "FAIL(被测/前提)", 2: "INSTRUMENT_DEFECT", 3: "ABSTAIN(缺侧/不可判)"}[dec["rc"]],
           "blocked": dec["blocked"], "rowcount_bad": dec["rowcount_bad"], "missing_truth_windows": dec["missing_truth_windows"],
           "void_arm_windows": j["void_arm_windows"],
           "checks": {
               "C1_judge_shadow_selftest": st,
               "C2_truth_reliability": {"rule": "unreliable <=> truth_cases <= median(truth) - %d" % MARGIN,
                                        "truth_median": j["truth_median"], "truth_range": j["truth_range"],
                                        "status": j["truth_status"], "unreliable": j["unreliable_windows"],
                                        "negative_control": [x for x in st["fixtures"] if x["fixture"].startswith("S3")],
                                        "informational": True},
               "C3_quality_paired_two_column": {"primary_windows": j["primary_windows"],
                                                "reliable_windows": [w for w in j["primary_windows"] if j["truth_status"][w] == "reliable"],
                                                "arms": j["arms"], "fail_arms": j["fail_arms"],
                                                "views": {"R560": {"fail_arms": j["fail_arms"],
                                                                     "arm_detail": {a: {k: v for k, v in d.items() if k in ("reliable_windows", "delta_median", "delta_min", "named_windows", "pass")} for a, d in j["arms"].items()}},
                                                           "R559": ("error" if "error" in j["r559_view"] else
                                                                    {"fail_arms": j["r559_view"]["fail_arms"],
                                                                     "arm_detail": {a: {k: v for k, v in d.items() if k in ("reliable_windows", "delta_median", "delta_min", "named_windows", "pass")} for a, d in j["r559_view"]["arms"].items()}})},
                                                "informational_deltas_9w": j["informational"]["deltas_all_reliable_9w"]},
               "C4_axis_freeze_premise": "见 freeze_premise (由 readings 侧机检)",
               "C5_iron11": {"decision": "require 含对照臂 (宪法铁律 11 原文: 两侧产出物必须可实际执行且正确)",
                             "rc_record_of_reference_round": "见 report (exec_precondition --round r560)"},
               "C6_family_and_case_distribution": {"family_distribution": j["family_distribution"],
                                                   "per_case_stability": j["per_case_stability"], "informational": True},
               "C7_no_claim": {"pass": True, "desc": "本轮零新臂读数 ⇒ 无任何降幅宣称"}
           }}
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"selftest": st["n_ok"], "rc": out["rc"], "verdict": out["verdict"], "blocked": out["blocked"],
                      "truth_status": j["truth_status"], "fail_arms": j["fail_arms"],
                      "reliable": [w for w in j["primary_windows"] if j["truth_status"][w] == "reliable"]},
                     ensure_ascii=False))
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
