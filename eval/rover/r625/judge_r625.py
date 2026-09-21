#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R625 判定器：DoD 面 4 生产口径对齐（K=10）+ 精排段成本列首测。

读取契约（R615 I1 教训：判据器读取契约必须显式并随轮更新）：
  逐臂读数件 = eval/rover/r625/out/<ARM>.json，schema "rerank-face-readings/1"
  顶层键：shape / pool_k / embed_source / telemetry{gated_recall_at_N_eq_1,pool_len_median}
          / aggregates{ARM4{median_ndcg@10,mean_mrr,...}} / per_query[{qid,gold_in_pool,...}]
          / cost_informational{...} / criteria{P1_telemetry,P4_cost_column_present,...}
  基线件（零回归对照）= eval/rover/r624/out/{A1,B1}.json（只读，禁改写）
  阈值出处 = eval/capability/baselines.json 的 id `rerank-four`（四值 DoD 阈值）
            与 id `rerank-recall-shape`（R@N 天花板口径）。

rc 分层（v4）：0 = 判据全绿；1 = 判据成立但主判据未达标；2 = 器具缺陷；3 = 输入缺失/不可判。
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(REPO, "eval", "rover", "r625", "out")
BASE624 = os.path.join(REPO, "eval", "rover", "r624", "out")
ARMS = ["A50", "A10", "B50", "B10", "Z10"]
DOD = {"ndcg@10": 0.8, "mrr": 0.6, "p@10": 0.8, "recall@N": 1.0}


def load(path):
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        return {"__parse_error__": str(e)}


def missing(arm_name, d):
    return [r["qid"] for r in d["per_query"] if not r["gold_in_pool"]]


def goldset(d):
    return {r["qid"] for r in d["per_query"] if r["gold_in_pool"]}


def main():
    verdict = {
        "round": "R625",
        "schema": "rerank-production-caliber/1",
        "axis": "召回池宽 K（口径轴）：K=10 = 生产口径 / K=50 = R623–R624 测量口径",
        "product_source_change": 0,
        "readings": {},
        "arms": {},
    }
    defects = []
    secondary = []

    data = {}
    for a in ARMS:
        d = load(os.path.join(OUT, a + ".json"))
        if d is None or "__parse_error__" in d:
            verdict["rc"] = 3
            verdict["rc_reason"] = "读数件缺失或不可解析: %s %s" % (a, (d or {}).get("__parse_error__", "missing"))
            verdict["checks"] = {}
            _write(verdict)
            print("rc=3 DISCOVER_FAIL", a)
            return 3
        data[a] = d
        verdict["arms"][a] = {
            "embed": d.get("embed_source"), "k": d.get("pool_k"),
            "gated": d["telemetry"]["gated_recall_at_N_eq_1"],
            "rate": round(d["telemetry"]["gated_ratio"], 4),
            "pool_len_median": d["telemetry"]["pool_len_median"],
            "criteria": d.get("criteria"),
        }
        verdict["readings"][a] = {
            "embed": d.get("embed_source"), "k": d.get("pool_k"),
            "gated": d["telemetry"]["gated_recall_at_N_eq_1"],
            "rate": round(d["telemetry"]["gated_ratio"], 4),
            "pool_len_median": d["telemetry"]["pool_len_median"],
        }

    base = {a: load(os.path.join(BASE624, a + ".json")) for a in ("A1", "B1")}

    checks = {}

    # ── P1 零回归（R623/R624 现档复算）────────────────────────────────
    zr = {}
    for arm, ref in (("A50", "A1"), ("B50", "B1")):
        b = base[ref]
        cur = sorted(goldset(data[arm]))
        old = sorted(goldset(b))
        zr[arm] = {
            "ref": "R624/" + ref,
            "n_membership_diff": len(set(cur) ^ set(old)),
            "gated_now": data[arm]["telemetry"]["gated_recall_at_N_eq_1"],
            "gated_ref": b["telemetry"]["gated_recall_at_N_eq_1"],
            "pool_len_median_now": data[arm]["telemetry"]["pool_len_median"],
            "pool_len_median_ref": b["telemetry"]["pool_len_median"],
            "pass": (set(cur) == set(old)
                     and data[arm]["telemetry"]["gated_recall_at_N_eq_1"] == b["telemetry"]["gated_recall_at_N_eq_1"]),
        }
    checks["P1_zero_regression"] = {"pass": all(v["pass"] for v in zr.values()), "detail": zr}

    # ── P2 口径生效 ────────────────────────────────────────────────────
    n_eff = {
        "pool_len_median_K10": data["A10"]["telemetry"]["pool_len_median"],
        "pool_len_median_K50": data["A50"]["telemetry"]["pool_len_median"],
        "readings_differ": data["A10"]["telemetry"]["gated_recall_at_N_eq_1"]
                           != data["A50"]["telemetry"]["gated_recall_at_N_eq_1"],
    }
    n_eff["pass"] = (n_eff["pool_len_median_K10"] <= 10.0
                     and n_eff["pool_len_median_K10"] < n_eff["pool_len_median_K50"])
    checks["P2_caliber_engaged"] = n_eff
    if not n_eff["pass"]:
        defects.append("P2 口径轴未生效（K=10 池宽未收窄）")

    # ── P3 主判据：生产口径四值 + DoD 阈值对照 ─────────────────────────
    d10, d50 = data["B10"], data["B50"]
    gT10 = d10["aggregates"]["T"]
    four_prod = {
        "ndcg@10": round(gT10.get("median_ndcg@10", float("nan")), 4),
        "mrr": round(gT10.get("median_mrr", float("nan")), 4),
        "mrr_mean": round(gT10.get("mean_mrr", float("nan")), 4),
        "p@10": round(gT10.get("median_p@10", float("nan")), 4),
        "recall@N": round(d10["telemetry"]["gated_ratio"], 4),
    }
    thr_eval = {k: {"threshold": v, "observed": four_prod[k], "pass": four_prod[k] >= v} for k, v in DOD.items()}
    r_gain = four_prod["recall@N"] - round(d50["telemetry"]["gated_ratio"], 4)
    checks["P3_production_caliber_four_metrics"] = {
        "baseline_id": "rerank-four",
        "threshold_source": "eval/capability/baselines.json#rerank-four + RF0005 §0 面 4",
        "domain_K10": "R@N==1 的查询（gold 在 K=10 池内）",
        "gated_n_K10": d10["telemetry"]["gated_recall_at_N_eq_1"],
        "four": four_prod,
        "thresholds": thr_eval,
        "all_pass": all(v["pass"] for v in thr_eval.values()),
        "n_thresholds_met": sum(1 for v in thr_eval.values() if v["pass"]),
        "falsifier_pool_width_hypothesis": {
            "rule": "R@N(K=10) >= R@N(K=50) ⇒ 「池宽=可回收来源」证伪",
            "r_at_N_K10": four_prod["recall@N"],
            "r_at_N_K50": round(d50["telemetry"]["gated_ratio"], 4),
            "falsified": r_gain >= 0,
        },
    }

    # ── P4 成本列采集完整（信息项，不入红绿）────────────────────────────
    cost = {}
    for a in ARMS:
        c = data[a].get("cost_informational") or {}
        cost[a] = {
            "latency_us_C_median": c.get("latency_us_C_median"),
            "latency_us_T_median": c.get("latency_us_T_median"),
            "latency_us_pair_diff_median": c.get("latency_us_pair_diff_median"),
            "latency_us_pair_diff_p90": c.get("latency_us_pair_diff_p90"),
            "candidates_scored_C": c.get("candidates_scored_C"),
            "assembled_chars_T_sum": c.get("assembled_chars_T_sum"),
            "token_estimator": c.get("token_estimator"),
            "token_est_T": c.get("token_est_T"),
            "remote_calls": c.get("remote_calls"),
            "flag_present": bool(data[a]["criteria"].get("P4_cost_column_present")),
        }
    complete = all(all(cost[a][k] not in (None, "") for k in
                       ("latency_us_C_median", "latency_us_T_median", "latency_us_pair_diff_median",
                        "candidates_scored_C", "assembled_chars_T_sum", "token_estimator"))
                   and cost[a]["flag_present"] for a in ARMS)
    checks["P4_cost_column"] = {
        "informational_only": True,
        "ground_rule": "R410：墙钟只作信息字段，不作红绿判据",
        "complete": complete,
        "rows": cost,
    }
    if not complete:
        defects.append("P4 成本列不全（字段缺失）")

    # ── P5 负控有牙 ───────────────────────────────────────────────────
    z_ok = (data["Z10"]["telemetry"]["gated_ratio"] <= data["A10"]["telemetry"]["gated_ratio"]
            and len(set(missing("Z10", data["Z10"])) ^ set(missing("A10", data["A10"]))) > 0)
    checks["P5_negative_control"] = {
        "pass": z_ok,
        "rate_Z10": round(data["Z10"]["telemetry"]["gated_ratio"], 4),
        "rate_A10": round(data["A10"]["telemetry"]["gated_ratio"], 4),
        "n_membership_diff": len(set(missing("Z10", data["Z10"])) ^ set(missing("A10", data["A10"]))),
    }
    if not z_ok:
        defects.append("P5 负控无牙")

    # ── P6 五桶守恒（基线 = 生产口径 A10 的未召回集）───────────────────
    miss10 = set(missing("A10", data["A10"]))
    gA50, gB10, gB50 = goldset(data["A50"]), goldset(data["B10"]), goldset(data["B50"])
    b = {"only_pool": 0, "only_shape": 0, "either": 0, "both_needed": 0, "structural": 0}
    for q in miss10:
        P, S, PB = q in gA50, q in gB10, q in gB50
        if P and S:
            b["either"] += 1
        elif P:
            b["only_pool"] += 1
        elif S:
            b["only_shape"] += 1
        elif PB:
            b["both_needed"] += 1
        else:
            b["structural"] += 1
    checks["P6_conservation"] = {
        "base": "A10 未召回集（生产口径 × 兜底形态）",
        "n_missing_base": len(miss10),
        "buckets": b,
        "sum": sum(b.values()),
        "pass": sum(b.values()) == len(miss10),
    }
    if sum(b.values()) != len(miss10):
        defects.append("P6 守恒不成立")

    # ── rc 合成（v4 分层：器具层优先于主判据层）────────────────────────
    verdict["checks"] = checks
    verdict["cost_informational"] = cost
    main_pass = checks["P3_production_caliber_four_metrics"]["all_pass"]
    verdict["main_criterion"] = {
        "id": "P3",
        "pass": main_pass,
        "baseline_id": "rerank-four",
        "detail": "生产口径 K=10 四值达标 %d/4" % checks["P3_production_caliber_four_metrics"]["n_thresholds_met"],
    }
    if defects:
        rc = 2
        verdict["rc_reason"] = "器具层缺陷: " + "; ".join(defects)
    elif not main_pass:
        rc = 1
        verdict["rc_reason"] = "判据成立但主判据未达标（生产口径四值 %d/4）" % \
                               checks["P3_production_caliber_four_metrics"]["n_thresholds_met"]
    else:
        rc = 0
        verdict["rc_reason"] = "全部判据绿"
    verdict["defects"] = defects
    verdict["mech_secondary"] = secondary
    verdict["rc"] = rc
    _write(verdict)
    print("rc=%d %s" % (rc, verdict["rc_reason"]))
    print(json.dumps({k: (v if not isinstance(v, dict) or "rows" not in v else {kk: vv for kk, vv in v.items() if kk != "rows"})
                      for k, v in checks.items()}, ensure_ascii=False, indent=1)[:2500])
    return rc


def _write(verdict):
    p = os.path.join(REPO, "eval", "rover", "r625", "verdict-r625.json")
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
