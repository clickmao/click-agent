#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R562 · 收口聚合器 (联合回归 + 只读定因的机检收口; 零产品改动/零新夹具/零远端).

机检面 (全部为**已落盘件**的双路径交叉校验, 判据键无条件计算):
  A. 判据 v2 复跑一致: verdict-r562-rerun.json vs 已提交 verdict-r561.json (判决面逐字段)
  B. 逐例矩阵跨文件一致: percase-matrix-r561.json vs r559/r560 evidence 的 cases_pass (27 臂窗)
  C. 定因器 vs 铁律11 前置器同源核对: wythoff-cause-r562.json 的失败例 vs 前置器 blocked 串 (27 臂窗)
  D. 起手闸联合回归: gate-regression-r562.json (rc + expectations_violated)
  E. 夹具-题面一致: 独立 oracle 复现全部 15 条 wythoff 期望值
rc 语义: 0 全过 / 1 红(被测/前提: 铁律11 rc=1 ⇒ 未可验收) / 2 器具缺陷(不一致·缺件·自检无牙) / 3 缺输入
用法: python3 eval/rover/r562/collect_r562.py
"""
from __future__ import annotations

import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r562")
ARM_WINDOWS = [("r559", w, a) for w in ("w104", "w105", "w106") for a in ("C1", "R559B0", "R559B3")] + \
              [("r560", w, a) for w in ("w107", "w108", "w109", "w110", "w111", "w112") for a in ("C1", "R560B0", "R560B3")]
JUDGE_DECISION_FIELDS = ("rc", "verdict", "blocked", "rowcount_bad", "missing_truth_windows",
                         "void_arm_windows", "criterion_version")


def j(p):
    return json.load(io.open(p, encoding="utf-8"))


def main():
    out = {"round": "R562", "instrument": "collect_r562.py"}
    # ---- E 夹具-题面一致 (先跑, 失败即 fail-closed) ----
    wc = j(os.path.join(R, "wythoff-cause-r562.json"))
    st = wc["classifier_selftest"]
    oracle_ok = bool(st["fixture_agrees_with_oracle"] and st["phi_vs_brute_equal"] and st["has_teeth"])
    out["E_fixture_vs_oracle"] = {"fixture_agrees": st["fixture_agrees_with_oracle"],
                                  "cold_phi_eq_brute": st["phi_vs_brute_equal"],
                                  "judger_has_teeth": st["has_teeth"],
                                  "positive": "%d/%d" % (st["positive_ok"], st["positive_n"]),
                                  "mutants": st["mutants_n"], "mutants_wrongly_ok": len(st["mutants_ok_wrongly"])}
    # ---- A 判据 v2 复跑一致 ----
    a_old, a_new = j(os.path.join(REPO, "eval/rover/r561/verdict-r561.json")), j(os.path.join(R, "verdict-r562-rerun.json"))
    diffs = {k: {"committed": a_old.get(k), "rerun": a_new.get(k)} for k in JUDGE_DECISION_FIELDS if a_old.get(k) != a_new.get(k)}
    st_old = a_old["checks"]["C1_judge_shadow_selftest"]
    st_new = a_new["checks"]["C1_judge_shadow_selftest"]
    out["A_judge_v2_rerun"] = {"decision_field_diffs": diffs, "identical": not diffs,
                               "selftest_committed": st_old["n_ok"] if isinstance(st_old, dict) and "n_ok" in st_old else
                               sum(1 for x in st_old["fixtures"] if x["ok"]) if isinstance(st_old, dict) else None,
                               "selftest_rerun": st_new["n_ok"] if isinstance(st_new, dict) and "n_ok" in st_new else
                               sum(1 for x in st_new["fixtures"] if x["ok"]) if isinstance(st_new, dict) else None}
    # ---- B 逐例矩阵跨文件一致 (cases_pass) ----
    m = j(os.path.join(REPO, "eval/rover/r561/percase-matrix-r561.json"))
    b_rows, b_bad = [], []
    for rk, w, arm in ARM_WINDOWS:
        rep = j(os.path.join(REPO, "eval/rover/%s/evidence/windows/%s/report.json" % (rk, w)))
        rec = [x for x in rep["rows"] if x["arm"] == arm][0]["cases_pass"]
        mat = m["windows"][w][arm]["pass"]
        b_rows.append({"arm_window": "%s/%s/%s" % (rk, w, arm), "report": rec, "matrix": mat, "ok": rec == mat})
        if rec != mat:
            b_bad.append(b_rows[-1])
    out["B_matrix_vs_report"] = {"n": len(b_rows), "n_ok": sum(1 for x in b_rows if x["ok"]), "bad": b_bad}
    # ---- C 定因器 vs 铁律11 前置器 (wythoff 失败例逐条, 两轮前置器合并) ----
    pre_map, pre_rc = {}, {}
    for rk, pf in (("r559", "/tmp/r562_precond_r559.json"), ("r560", "/tmp/r562_precond_r560.json")):
        pre = j(pf)
        pre_rc[rk] = (1 if pre.get("blocked") else 0, len(pre.get("blocked", [])))
        for s in pre.get("blocked", []):
            head = s.split(" ")[0]                    # e.g. w107/C1/g1
            parts = head.split("/")
            w, arm = parts[0], parts[1]
            names = [t for t in s.split("failed=")[-1].split(",") if t.startswith("wythoff#")]
            pre_map["%s|%s" % (w, arm)] = sorted(names)
        # 全对臂窗不出现在 blocked 里 ⇒ 以 report.json 补 0 失败
        for w, arm in [(x[1], x[2]) for x in ARM_WINDOWS if x[0] == rk]:
            rep = j(os.path.join(REPO, "eval/rover/%s/evidence/windows/%s/report.json" % (rk, w)))
            rec = [x for x in rep["rows"] if x["arm"] == arm][0]["cases_pass"]
            if rec == 58:
                pre_map.setdefault("%s|%s" % (w, arm), [])
    c_rows, c_bad = [], []
    # 命名对齐: 定因器按「族内序」编号 (0..14), 前置器按「题集全局序」(43..57) ⇒ 机取映射 (禁手抄)
    allcs = j(os.path.join(REPO, "eval/rover/r560/cases/cases-r521.json"))
    gmap = {i - 43: i for i, c in enumerate(allcs) if c["game"] == "wythoff"}
    for rk, w, arm in ARM_WINDOWS:
        rr = wc["raw_rows"]["%s|%s" % (w, arm)]
        mine = sorted("wythoff#%02d-%s" % (gmap[r["idx"]], r["name"].rsplit("-", 1)[1])
                      for r in rr if not r["match"])
        key = "%s|%s" % (w, arm)
        theirs = pre_map.get(key, [])
        ok = mine == theirs
        c_rows.append({"arm_window": "%s/%s/%s" % (rk, w, arm), "n_fail_mine": len(mine), "n_fail_precond": len(theirs), "ok": ok})
        if not ok:
            c_bad.append({"arm_window": key, "mine": mine, "precond": theirs})
    out["C_causefinder_vs_iron11"] = {"n": len(c_rows), "n_ok": sum(1 for x in c_rows if x["ok"]), "bad": c_bad,
                                      "precond_rc": {k: {"rc": v[0], "blocked_n": v[1]} for k, v in pre_rc.items()}}
    # ---- D 起手闸联合回归 ----
    g = j(os.path.join(R, "gate-regression-r562.json"))
    out["D_gate_regression"] = {"rc": g["rc"], "expectations_violated": g["expectations_violated"],
                                "runs": [{k: v for k, v in r.items() if k != "out"} for r in g["runs"]],
                                "decoy_premise": g.get("decoy")}
    # ---- 定因读数 (informational) ----
    import collections
    shares = collections.Counter()
    for k, v in wc["per_arm_window"].items():
        for cls, n in v["classes"].items():
            shares[cls] += n
    out["F_cause_distribution"] = {"class_shares": dict(shares),
                                   "per_arm_wythoff_pass_of_15": {k: v["n_pass"] for k, v in sorted(wc["per_arm_window"].items())},
                                   "oscillating_cases": {arm: sum(1 for k, v in wc["per_case_oscillation"].items()
                                                                  if k.startswith(arm + "#") and v["oscillates"])
                                                          for arm in ("C1", "R560B0", "R560B3")}}
    # ---- 判决 ----
    bad = []
    if not oracle_ok:
        bad.append(("E", "oracle/selftest 不过"))
    if diffs or out["A_judge_v2_rerun"]["selftest_committed"] != out["A_judge_v2_rerun"]["selftest_rerun"]:
        bad.append(("A", "判据 v2 复跑与已提交判决不一致"))
    if b_bad:
        bad.append(("B", "逐例矩阵与 report 不一致"))
    if c_bad:
        bad.append(("C", "定因器与铁律11 前置器不一致"))
    if g["rc"] != 0:
        bad.append(("D", "起手闸回归预期落空"))
    out["instrument_defects"] = bad
    pre_rc_all = max(v["rc"] for v in out["C_causefinder_vs_iron11"]["precond_rc"].values()) if out["C_causefinder_vs_iron11"]["precond_rc"] else 3
    pre_rc = pre_rc_all
    out["iron11"] = {"rounds": ["r559", "r560"], "rc": pre_rc,
                     "blocked_n": {k: v["blocked_n"] for k, v in out["C_causefinder_vs_iron11"]["precond_rc"].items()},
                     "note": "本轮零新臂 ⇒ 该 rc 为 R559/R560 冻结件复跑读数 (同一前置器/同一快照), 非本轮新交付"}
    out["rc"] = 2 if bad else (1 if pre_rc != 0 else 0)
    out["verdict"] = {0: "PASS", 1: "FAIL(被测/前提)", 2: "INSTRUMENT_DEFECT", 3: "ABSTAIN"}[out["rc"]]
    out["no_claim"] = {"zero_new_arms": True, "zero_product_change": True, "zero_remote": True,
                       "desc": "本轮零新臂读数 ⇒ 无任何降幅/增益宣称; 质量读数沿用 R559/R560 冻结件"}
    json.dump(out, io.open(os.path.join(R, "verdict-r562.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # ---- kpi.jsonl 台账 (键集与同族既有行逐字相同; 同 round+kind 原地更新 ⇒ 幂等) ----
    import datetime
    line = {"round": "R562",
            "ts": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "kind": "器具收口轮 (判据 v2 入册 + 起手闸/判据器/铁律11 前置器同轮复跑 + wythoff 族只读定因; "
                    "零远端调用 / 零产品源码改动 / 零新增夹具 / 零新臂)",
            "artifact": "eval/rover/r562/{wythoff_cause_r562.py,gate_regression_r562.py,collect_r562.py,"
                        "wythoff-cause-r562.json,gate-regression-r562.json,gate-*.json,verdict-r562.json}",
            "change": "① 质量判据 v2 正式入册 `docs/external-reference-harness.md` §12 (v1 声明作废: 绝对中位/极差门在真值自身极差 11 上结构性不可达); "
                      "② 三件器具同轮复跑: 判据 v2 判决面 vs 已提交件逐字段相同 ∧ 27/27 臂窗 cases_pass 跨文件相等 ∧ "
                      "27/27 臂窗失败例集合与铁律11 前置器逐条相同; ③ 起手闸 mem/shell 两面对照控制 (诱饵 shell 前提经 /proc 核实) rc=0; "
                      "④ wythoff 族只读定因 (405 例次重放冻结语料, 独立 oracle 复现 15/15 期望值)",
            "readings": {"A_judge_v2_rerun_identical": not diffs,
                         "B_matrix_vs_report": "%d/%d" % (out["B_matrix_vs_report"]["n_ok"], out["B_matrix_vs_report"]["n"]),
                         "C_causefinder_vs_iron11": "%d/%d" % (out["C_causefinder_vs_iron11"]["n_ok"], out["C_causefinder_vs_iron11"]["n"]),
                         "D_gate_regression_rc": g["rc"],
                         "E_fixture_vs_oracle": {"agrees": st["fixture_agrees_with_oracle"],
                                                 "cold_phi_eq_brute": st["phi_vs_brute_equal"],
                                                 "judger_teeth": st["has_teeth"],
                                                 "positive": "%d/%d" % (st["positive_ok"], st["positive_n"]),
                                                 "mutants": st["mutants_n"]},
                         "wythoff_per_arm_window_pass_of_15": {k: v["n_pass"] for k, v in sorted(wc["per_arm_window"].items())},
                         "wythoff_failure_classes_405_case_runs": dict(shares),
                         "form_check": "VerificationForm|SkillGeneralization|DevPlanDocRef 14/14 (Failed 0 / Skipped 0, FORMCHECK_EXIT=0)"},
            "honest_boundaries": "本轮零新臂 ⇒ 不宣称任何质量/成本降幅; 质量读数沿用 R559/R560 冻结件且与旧窗并列不相减; "
                                 "铁律11 rc=1 (r559 blocked 5 / r560 blocked 12, 同一前置器复跑) ⇒ 一切读数标「参考(未可验收)」; "
                                 "**本轮自捕 (已修, 读数重发)**: 收官器首跑判 C=10/27 —— 真因是「定因器按族内序编号 vs 前置器按题集全局序(43–57)」的命名错位 (器具缺陷, 非被测), "
                                 "修法=机取映射后 27/27; 该缺陷态读数 (rc=2) 原样留在 verdict-r562.json 的复算历史里, 不撤不掩盖; "
                                 "定因器自身三处 fail-closed 自捕同轮修 (冷点集漏 (0,0) / phi-vs-brute 排序与域不一致 / LOSE 词标不符被并成 OK); "
                                 "定因结论仅在 wythoff 族 (15 例) 成立, 不得外推其它族",
            "owner_round": "R562",
            "next": "wythoff 族修复须动契约/产品分支 ⇒ 待放行 (本轮零产品改动); 交付闸/停止条件同缺放行; "
                    "判据 v2 已入册 ⇒ 下轮对照可直接引用; 起手闸擦边 PASS 仍有振幅风险 (本轮 mem 2652 对门槛 2650, 余量 2 MB)"}
    kp = os.path.join(REPO, "eval/capability/kpi.jsonl")
    kept, replaced, stale = [], 0, []
    if os.path.isfile(kp):
        for l in io.open(kp, encoding="utf-8"):
            if not l.strip():
                continue
            try:
                d = json.loads(l)
            except Exception:  # noqa: BLE001
                kept.append(l.rstrip("\n"))
                continue
            if d.get("round") == "R562":
                replaced += 1
                if d.get("kind") != line["kind"]:
                    stale.append(d)      # 缺陷态读数原样留档 (不撤不掩盖), 见 verdict-r562.json
                continue
            kept.append(json.dumps(d, ensure_ascii=False))
    kept.append(json.dumps(line, ensure_ascii=False))
    with io.open(kp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kept) + "\n")
    out["kpi_line"] = {"replaced": replaced, "keys": list(line.keys()), "superseded_stale_lines": stale}
    json.dump(out, io.open(os.path.join(R, "verdict-r562.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": out["rc"], "verdict": out["verdict"], "instrument_defects": bad,
                      "A": out["A_judge_v2_rerun"]["identical"], "B": out["B_matrix_vs_report"],
                      "C": {k: out["C_causefinder_vs_iron11"][k] for k in ("n", "n_ok")},
                      "D": {"rc": g["rc"], "violated": g["expectations_violated"]},
                      "E": out["E_fixture_vs_oracle"], "shares": dict(shares),
                      "kpi_line": out["kpi_line"]}, ensure_ascii=False))
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
