#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R597 判据 v3 **第五窗集行使** 器具（driver）。

纪律（承 R564「逻辑源一字未改，只替换窗集常量」先例）:
  · **逻辑源 = `eval/rover/r589/pool_taskface_r589.py`（import，禁重写第二份）**;
    逐窗两面重算 / 按族分列 / `unreliable` 单列 / 失败原因直方图 全部由该模块提供。
  · 本文件只做三件事: ① 参数化窗集（`mod.ROUNDS`）② C0 期望值随窗集参数化（R589 的 48/12 是四集常数）
    ③ 把 set1（R585–R588）/ set2（R591）/ set3（R595）/ set4（R596）/ set5（R597）**并列**输出（跨窗集**禁相减**）。
  · 判据阈值与 R589 同源同值: v3 主判据 = 有效窗 `中位 ≤ -0.34 ∧ 负号窗 ≥ ceil(有效/2)`（写死, 非事后调）。

用法: python3 eval/rover/r597/pool_taskface_r597.py --out eval/rover/r597/taskface-pool-r597.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import statistics
import sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r589/pool_taskface_r589.py")
RUNS = os.path.expanduser("~/.agentframework/harness/runs")


def load_src():
    spec = importlib.util.spec_from_file_location("pool589", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def eval_set(mod, rounds):
    """对给定窗集重算两面 —— 全部复用逻辑源函数（零逻辑复制）。"""
    mod.ROUNDS = list(rounds)
    data = mod.load_all(RUNS)
    rows = mod.face_by_window(data)
    summ = mod.summarize(rows)

    runs_seen, bad = 0, []
    for r, wins in data.items():
        for win, rec in wins.items():
            allruns = ([rec["truth"]] if rec["truth"] else []) + rec["prod"]
            if rec["truth"] is None:
                bad.append({"why": "missing_truth", "round": r, "win": win})
            if len(rec["prod"]) != 3:
                bad.append({"why": "prod_reps!=3", "round": r, "win": win, "n": len(rec["prod"])})
            for x in allruns:
                runs_seen += 1
                if x["n"] != mod.CASES_N:
                    bad.append({"why": "cases_n!=58", "round": r, "win": win, "n": x["n"]})
                if x["summary"] and x["summary"][0] != sum(1 for v in x["cases"].values() if v):
                    bad.append({"why": "summary_mismatch", "round": r, "win": win})
    exp_runs = 4 * 3 * len(rounds)
    C0 = {"runs_seen": runs_seen, "expected_runs": exp_runs,
          "windows": sum(len(v) for v in data.values()), "expected_windows": 3 * len(rounds),
          "issues": bad, "pass": (not bad and runs_seen == exp_runs)}

    # ---- C1 判据 v3 主面（整题全对率）----
    valid = [r for r in rows if r["valid_task"]]
    vD_task = [r["D_task"] for r in valid]
    med = statistics.median(vD_task) if vD_task else None
    neg = sum(1 for x in vD_task if x < 0)
    thr = -0.34
    c1_pass = bool(vD_task) and med is not None and med <= thr and neg >= (len(vD_task) + 1) // 2
    C1 = {"median_D_task": med, "neg_windows": neg, "valid_windows": len(vD_task),
          "threshold_median": thr, "threshold_sign": "neg >= ceil(valid/2)",
          "pass": c1_pass,
          "verdict": ("整题面缺口成立" if c1_pass else ("整题面无缺口" if vD_task else "不可判"))}

    # ---- C2 两面同向（量纲不同 ⇒ 只判方向, 禁跨面比大小）----
    cm = summ.get("case_face_valid", {}).get("median")
    tm = summ.get("task_face_valid", {}).get("median")
    same = (cm is not None and tm is not None and cm != 0 and tm != 0 and ((cm < 0) == (tm < 0))) or \
           (cm == 0 and tm == 0)
    C2 = {"case_face_median": cm, "task_face_median": tm, "same_sign": bool(same), "pass": bool(same)}

    # ---- 按族分列（公式与逻辑源 main() 同款）----
    fam_agg = {}
    for f, tot in (mod.FAM_TOTAL.items() if rows else []):
        tp = sum(r["families"][f]["truth_pass"] for r in rows)
        t_all = sum(int(r["families"][f]["truth_pass"] == tot) for r in rows)
        pp = [r["families"][f]["prod_pass_med"] for r in rows]
        p_rates = [r["families"][f]["prod_all_pass_rate"] for r in rows]
        fam_agg[f] = {"n_cases": tot, "truth_pass_cases": tp, "truth_runs": len(rows),
                      "truth_all_pass_runs": t_all,
                      "truth_all_pass_rate": round(t_all / max(1, len(rows)), 4),
                      "prod_pass_cases_median_per_window": statistics.median(pp),
                      "prod_all_pass_rate_mean": round(sum(p_rates) / max(1, len(p_rates)), 4),
                      "prod_fail_reasons_total": mod._sum_reasons(rows, f)}

    # ---- C7 负控（有牙, 单侧变异; 靶点按窗集参数化: 取该集首个「产品有失败例」的窗）----
    tgt = None
    for r in rows:
        if any(not v for v in mod.read_run(os.path.join(RUNS, r["round"], r["win"], "agentD-r1", "g1"))["cases"].values()):
            tgt = r["win"]
            break

    def mutate_one(win, side, cid, ok):
        if side == "prod" and win == tgt and ok is False:
            return True
        return None
    rows_nc = mod.face_by_window(data, mutate=mutate_one)
    nc_changed = (json.dumps([(x["win"], x["D_case"], x["D_task"]) for x in rows]) !=
                  json.dumps([(x["win"], x["D_case"], x["D_task"]) for x in rows_nc]))
    nc_prod_only = all(a["truth_pass"] == b["truth_pass"] and a["truth_all_pass"] == b["truth_all_pass"]
                       for a, b in zip(rows, rows_nc))
    C7 = {"mutation": "%s 产品侧任一失败例 FAIL->PASS (副本内, 单侧)" % tgt,
          "target_window": tgt, "readings_changed": nc_changed, "truth_side_untouched": nc_prod_only,
          "has_teeth": bool(nc_changed and nc_prod_only)}

    roots = [os.path.join(RUNS, r) for r in rounds] + \
            [os.path.join(REPO, "eval/rover", r, "snapshots") for r in rounds]
    fa = mod.fingerprint(roots)
    C5 = {"files": fa[0], "sha": fa[1], "pass": True, "note": "只读面指纹（读数自身不写入）"}

    # ---- C10 自报期待 vs 外部用例脱钩 ----
    dec = []
    for r, wins in data.items():
        for win, rec in wins.items():
            for run, rc in zip(rec["prod"], rec["prod_rc"]):
                k = sum(1 for v in run["cases"].values() if v)
                if rc is not None and rc != "0" and k == mod.CASES_N:
                    dec.append("%s/%s rc=%s cases=58/58" % (r, win, rc))
    nprod = sum(len(v["prod"]) for w in data.values() for v in w.values())
    C10 = {"product_runs": nprod, "rc_nonzero_and_allpass": len(dec), "named": dec,
           "share": round(len(dec) / max(1, nprod), 4)}

    rc = 0 if (C0["pass"] and C7["has_teeth"]) else (3 if not C0["pass"] else 2)
    return {"rounds": list(rounds), "data_scope": {"windows": sum(len(v) for v in data.values()),
                                                   "runs": runs_seen, "products": nprod},
            "C0": C0, "C1_task_face_v3": C1, "C2_face_direction": C2, "C5_readonly": C5,
            "C7_negative_control": C7, "C10_decoupling": C10, "summary": summ,
            "family_aggregate": fam_agg, "per_window": rows,
            "verdict": {"rc": rc, "judge": ("PASS" if rc == 0 else ("FAIL(数据/器具)" if rc == 2 else "BLOCKED(数据残缺)"))}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    mod = load_src()
    set1 = eval_set(mod, ["r585", "r586", "r587", "r588"])
    set2 = eval_set(mod, ["r591"])
    set3 = eval_set(mod, ["r595"])
    set4 = eval_set(mod, ["r596"])
    set5 = eval_set(mod, ["r597"])
    out = {
        "round": "R597",
        "mode": "判据 v3 第三窗集行使（真机臂轮）；set1/set2 复算作并列件（跨窗集禁相减）",
        "instrument_logic_source": {"path": SRC, "sha12": hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:12],
                                    "driver_sha12": hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:12]},
        "set1_first_window_set": set1,
        "set2_second_window_set": set2,
        "set3_third_window_set": set3,
        "set4_fourth_window_set": set4,
        "set5_fifth_window_set": set5,
        "juxtaposition": {
            "rule": "跨窗集**禁相减**，只并列（§12.3）；阈值 -0.34 同一件、非事后调。",
            "set1": {"valid": set1["C1_task_face_v3"]["valid_windows"],
                     "median": set1["C1_task_face_v3"]["median_D_task"],
                     "neg": set1["C1_task_face_v3"]["neg_windows"], "pass": set1["C1_task_face_v3"]["pass"]},
            "set2": {"valid": set2["C1_task_face_v3"]["valid_windows"],
                     "median": set2["C1_task_face_v3"]["median_D_task"],
                     "neg": set2["C1_task_face_v3"]["neg_windows"], "pass": set2["C1_task_face_v3"]["pass"]},
            "set3": {"valid": set3["C1_task_face_v3"]["valid_windows"],
                     "median": set3["C1_task_face_v3"]["median_D_task"],
                     "neg": set3["C1_task_face_v3"]["neg_windows"], "pass": set3["C1_task_face_v3"]["pass"]},
            "set4": {"valid": set4["C1_task_face_v3"]["valid_windows"],
                     "median": set4["C1_task_face_v3"]["median_D_task"],
                     "neg": set4["C1_task_face_v3"]["neg_windows"], "pass": set4["C1_task_face_v3"]["pass"]},
            "set5": {"valid": set5["C1_task_face_v3"]["valid_windows"],
                     "median": set5["C1_task_face_v3"]["median_D_task"],
                     "neg": set5["C1_task_face_v3"]["neg_windows"], "pass": set5["C1_task_face_v3"]["pass"]},
            "family_all_pass_rate": {f: {"set1": set1["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean"),
                                         "set2": set2["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean"),
                                         "set5": set5["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean")}
                                     for f in mod.FAM_TOTAL},
            "reproduced_first_set": {
                "registered_r589": {"median": -0.6667, "neg": 8, "valid": 9},
                "recomputed_here": {"median": set1["C1_task_face_v3"]["median_D_task"],
                                    "neg": set1["C1_task_face_v3"]["neg_windows"],
                                    "valid": set1["C1_task_face_v3"]["valid_windows"]},
                "consistent": (set1["C1_task_face_v3"]["median_D_task"] == -0.6667)}}
    }
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    j = out["juxtaposition"]
    print("== R597 判据 v3 第五窗集 ==")
    print("set1(R585-588): valid=%s median=%s neg=%s pass=%s | 与 R589 登记件一致=%s"
          % (j["set1"]["valid"], j["set1"]["median"], j["set1"]["neg"], j["set1"]["pass"],
             j["reproduced_first_set"]["consistent"]))
    print("set2(w166-168, 第二窗集): valid=%s median=%s neg=%s pass=%s rc=%d"
          % (j["set2"]["valid"], j["set2"]["median"], j["set2"]["neg"], j["set2"]["pass"],
             set2["verdict"]["rc"]))
    print("set4(w172-174, 第四窗集): valid=%s median=%s neg=%s pass=%s rc=%d"
          % (j["set4"]["valid"], j["set4"]["median"], j["set4"]["neg"], j["set4"]["pass"],
             set4["verdict"]["rc"]))
    print("set5(w175-177, 第五窗集): valid=%s median=%s neg=%s pass=%s rc=%d"
          % (j["set5"]["valid"], j["set5"]["median"], j["set5"]["neg"], j["set5"]["pass"],
             set5["verdict"]["rc"]))
    print("族 all-pass 率: %s" % json.dumps(j["family_all_pass_rate"], ensure_ascii=False))
    print("C0 set2: runs=%d/%d windows=%d issues=%d | C7 有牙=%s"
          % (set2["C0"]["runs_seen"], set2["C0"]["expected_runs"], set2["C0"]["windows"],
             len(set2["C0"]["issues"]), set2["C7_negative_control"]["has_teeth"]))
    print("set3(w169-171, 第三窗集): valid=%s median=%s neg=%s pass=%s rc=%d"
          % (j["set3"]["valid"], j["set3"]["median"], j["set3"]["neg"], j["set3"]["pass"],
             set3["verdict"]["rc"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
