#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R594 — 面读数器（候选 ③④⑤，**纯聚合**，零子进程 / 零新臂 / 零远端）。

输入 = R593 的两件在盘读数（**逐字节不变**）：
  · `eval/rover/r593/d1-stderr-probe-r593.json`（66 例次形态族，(round,win,sub,idx) 粒度）
  · `eval/rover/r593/landing-predicate-r593.json`（59 跑次逐跑次层/桶/V_int）

输出三面：
  ③ `V_int` **按窗集分层**直方图（agent / codex 分列）+ 交叉校验 `cold_set_equal=True ∧ V_int>0` 计数；
     **不设阈值、不作触发**（承 R593 预注册禁止）；本轮只报分布面已扩到 5 窗集，
     并明文登记「阈值化仍需**新跑次**（扩窗或扩 reps）= 未测」。
  ④ codex 独有 (b) 窗 `w154` 的逐字段读数 + 按 R592 层规则**重算**层（一致性判据）。
  ⑤ **形态族 × 跑次集中度**：每族的 top-run 份额（机械规则：≥0.5 ⇒ 集中，否则散布）。

零回归控制：由同一件在盘 JSON 重算 R593 已登记聚合（A/B 级桶总额、层分布、V_int 直方图），
断言**逐位复现**；对不上先查器具/环境，不进结论。

rc 语义（fail-closed）：0 = 可用 / 2 = 器具缺陷（零回归不符·守恒破·非平凡破·确定性破）/ 3 = 输入缺失。
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
PROBE = os.path.join(REPO, "eval/rover/r593/d1-stderr-probe-r593.json")
LAND = os.path.join(REPO, "eval/rover/r593/landing-predicate-r593.json")
OUT = os.path.join(REPO, "eval/rover/r594/face-readings-r594.json")

# R593 已登记值（零回归对照物；由同件 JSON 重算后逐位比对）
REG = {
    "buckets_agent": {"B_coldset": 184, "A_landing_loose": 20, "A_selection_order": 6},
    "layer_agent": {"(b) 冷集构造层": 22, "(c) 本轴外": 19, "(a) 落点/选择谓词层": 3},
    "d_subs_agent": {"D1_empty_or_error": 66, "D3_move_illegal": 3},
    "v_int_hist_agent": {"0": 25, "350": 1, "235": 1, "94": 1, "115": 1, "4": 1, "48": 2,
                         "10": 1, "29": 1, "13": 1, "11": 2, "1": 1, "6": 2, "5": 2,
                         "25": 1, "169": 1},
    "v_int_hist_codex": {"50": 1, "0": 11, "19": 1, "2": 1, "350": 1},
}


def layer_rule(r):
    """R592/R593 层规则（逐字）：v_land>0 ⇒ (a)；否则 sets 不等 ⇒ (b)；否则 (c)。"""
    if r["v_land_n"] > 0:
        return "(a) 落点/选择谓词层"
    if not r["cold_set_equal"]:
        return "(b) 冷集构造层"
    return "(c) 本轴外"


def compute():
    with open(LAND, encoding="utf-8") as fh:
        land = json.load(fh)
    with open(PROBE, encoding="utf-8") as fh:
        probe = json.load(fh)

    runs = land["runs"]
    out = {"round": "R594", "instrument": "face_readings_r594", "rc": 0, "notes": []}

    # ---------- 零回归重算 ----------
    bk = collections.Counter()
    ly = collections.Counter()
    ds = collections.Counter()
    vih = collections.Counter()
    for r in runs:
        if r["side"] != "agent":
            continue
        for b, n in r["buckets"].items():
            bk[b] += n
        ly[layer_rule(r)] += 1
        for s, n in r["d_subs"].items():
            ds[s] += n
        vih[str(r["v_int_n"])] += 1
    vihc = collections.Counter()
    for r in runs:
        if r["side"] == "codex":
            vihc[str(r["v_int_n"])] += 1
    zr = {
        "buckets_agent": dict(bk), "layer_agent": dict(ly), "d_subs_agent": dict(ds),
        "v_int_hist_agent": dict(vih), "v_int_hist_codex": dict(vihc),
    }
    out["zero_regression_computed"] = zr
    # 比较口径与 R593 登记面**逐字对齐**：A/B 级桶（D 桶在 R593 已细分为子桶 ⇒ 只作 d_total 守恒比对）
    bk_sub = {k: v for k, v in zr["buckets_agent"].items() if k in REG["buckets_agent"]}
    mism = {}
    for k, reg in (("buckets_agent", bk_sub), ("layer_agent", zr["layer_agent"]),
                   ("d_subs_agent", zr["d_subs_agent"]), ("v_int_hist_agent", zr["v_int_hist_agent"]),
                   ("v_int_hist_codex", zr["v_int_hist_codex"])):
        if reg != REG[k]:
            mism[k] = {"expected": REG[k], "actual": reg}
    d_total = sum(r["d_total"] for r in runs if r["side"] == "agent")
    d_bucket = zr["buckets_agent"].get("D_delivery_or_shape", 0)
    out["zero_regression"] = {"match": not mism, "mismatch": mism, "registered_from": "R593",
                              "d_bucket_eq_d_total": d_bucket == d_total,
                              "d_bucket": d_bucket, "d_total": d_total}

    # ---------- 候选 ③：V_int 按窗集分层 ----------
    per_set = {}
    for r in runs:
        key = "%s/%s" % (r["round"], r["win"])
        d = per_set.setdefault(key, {"agent": collections.Counter(), "codex": collections.Counter(),
                                     "agent_runs": 0, "codex_runs": 0})
        d[r["side"]][str(r["v_int_n"])] += 1
        d[r["side"] + "_runs"] += 1
    out["v_int_by_window_set"] = {k: {"agent_hist": dict(v["agent"]), "codex_hist": dict(v["codex"]),
                                      "agent_runs": v["agent_runs"], "codex_runs": v["codex_runs"]}
                                  for k, v in sorted(per_set.items())}
    xi = [r for r in runs if r["cold_set_equal"] and r["v_int_n"] > 0]
    out["v_int_cross_check"] = {"cold_equal_and_vint_pos_runs": len(xi),
                                "total_runs": len(runs),
                                "rule": "真冷集对任何合法着法封闭 ⇒ 该组合应为 0；本轮不设阈值"}
    # 2×2 列联（机械，供阈值化前看分布形状；**不设阈值**）
    cont = {}
    for side in ("agent", "codex"):
        tab = collections.Counter()
        for r in runs:
            if r["side"] == side:
                tab[(bool(r["cold_set_equal"]), bool(r["v_int_n"] > 0))] += 1
        cont[side] = {"cold_eq_T_vint_pos": tab[(True, True)], "cold_eq_T_vint_zero": tab[(True, False)],
                      "cold_eq_F_vint_pos": tab[(False, True)], "cold_eq_F_vint_zero": tab[(False, False)],
                      "n": sum(tab.values())}
    out["v_int_vs_cold_equal"] = cont
    out["v_int_threshold_status"] = "未测：阈值化需新跑次（扩窗/扩 reps）；本轮零新臂，只报分布面"

    # ---------- 候选 ④：codex 独有 (b) 窗 w154 ----------
    w154 = [r for r in runs if r["win"] == "w154"]
    w154runs = [{"sub": r["sub"], "side": r["side"], "cases_pass_wythoff": r["cases_pass_wythoff"],
                 "cases_n": r["cases_n"], "cold_set_equal": r["cold_set_equal"],
                 "cold_only_prod": r["cold_only_prod"], "cold_only_true": r["cold_only_true"],
                 "v_land_n": r["v_land_n"], "v_int_n": r["v_int_n"],
                 "declared_cold_n": r["declared_cold_n"],
                 "layer_registered": r["layer"], "layer_recomputed": layer_rule(r),
                 "consistent": r["layer"] == layer_rule(r),
                 "buckets": r["buckets"]}
                for r in w154]
    cx = [r for r in w154 if r["side"] == "codex"]
    ag = [r for r in w154 if r["side"] == "agent"]
    out["w154"] = {
        "runs": w154runs,
        "codex_layer": cx[0]["layer"] if cx else None,
        "codex_only_b_holds": bool(cx) and all(layer_rule(r) == "(b) 冷集构造层" for r in cx)
        and all(layer_rule(r) != "(b) 冷集构造层" for r in ag),
        "agent_layers": {r["sub"]: layer_rule(r) for r in ag},
    }

    # ---------- 候选 ⑤：形态族 × 跑次集中度 ----------
    rows = probe["rows"]
    fam = collections.defaultdict(collections.Counter)
    for r in rows:
        fam[r["family"]]["%s/%s/%s" % (r["round"], r["win"], r["sub"])] += 1
    ftab = {}
    for f, c in sorted(fam.items(), key=lambda kv: -sum(kv[1].values())):
        tot = sum(c.values())
        top_run, top_n = c.most_common(1)[0]
        ftab[f] = {"n": tot, "runs": len(c), "top_run": top_run, "top_share": round(top_n / tot, 4),
                   "concentration": "集中在单一跑次" if top_n / tot >= 0.5 else "散布",
                   "by_run": dict(sorted(c.items(), key=lambda kv: -kv[1]))}
    out["family_concentration"] = ftab
    out["family_concentration_rule"] = "top-run 份额 ≥ 0.5 ⇒ 集中在单一跑次，否则散布（预注册机械规则）"

    # ---------- 非平凡 / 守恒 ----------
    out["conservation"] = {"probe_rows": len(rows), "family_sum": sum(v["n"] for v in ftab.values()),
                           "land_runs": len(runs),
                           "agent_runs": sum(1 for r in runs if r["side"] == "agent"),
                           "codex_runs": sum(1 for r in runs if r["side"] == "codex")}
    out["non_trivial"] = {"distinct_layers": len({layer_rule(r) for r in runs}),
                          "distinct_families": len(ftab),
                          "ok": len(ftab) >= 2 and len({layer_rule(r) for r in runs}) >= 2}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    for p in (PROBE, LAND):
        if not os.path.isfile(p):
            print("MISSING " + p)
            return 3
    res = compute()
    res2 = compute()          # 确定性 ×2（同进程同输入）
    det = json.dumps(res, sort_keys=True) == json.dumps(res2, sort_keys=True)
    ok = True
    if not res["zero_regression"]["match"]:
        ok = False
        res["notes"].append("零回归不符")
    if not res["zero_regression"]["d_bucket_eq_d_total"]:
        ok = False
        res["notes"].append("D 桶与 d_total 分叉")
    if res["conservation"]["probe_rows"] != res["conservation"]["family_sum"]:
        ok = False
        res["notes"].append("守恒破")
    if not res["non_trivial"]["ok"]:
        ok = False
        res["notes"].append("非平凡破")
    if not det:
        ok = False
        res["notes"].append("确定性破")
    res["determinism_x2"] = det
    res["rc"] = 0 if ok else 2
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print("R594_FACE rc=%d zero_regression=%s det=%s" % (res["rc"], res["zero_regression"]["match"], det))
    print("v_int cold_equal_and_pos=%d/%d ; w154 codex_only_b=%s"
          % (res["v_int_cross_check"]["cold_equal_and_vint_pos_runs"],
             res["v_int_cross_check"]["total_runs"], res["w154"]["codex_only_b_holds"]))
    print("family concentration:")
    for f, v in res["family_concentration"].items():
        print("  %-42s n=%-3d runs=%-2d top=%-28s share=%.3f %s"
              % (f[:42], v["n"], v["runs"], v["top_run"], v["top_share"], v["concentration"]))
    print("out " + a.out)
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
