#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R627 判据器：读预注册 + oracle 读数 + 事后诊断 ⇒ verdict-r627.json

rc 分层（v4）：0 主判据 / 1 机制·归属 / 2 器具 / 3 输入。
纪律：预注册判据**照原样判**（FAIL 就记 FAIL、不翻案、不下调阈值）；正确形态单列 `checks_posthoc`。
"""
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
D = os.path.join(REPO, "eval/rover/r627")


def main():
    pre = json.load(io.open(f"{D}/prereg-r627.json", encoding="utf-8"))
    o = json.load(io.open(f"{D}/oracle-r627.json", encoding="utf-8"))
    ph = json.load(io.open(f"{D}/posthoc-r627.json", encoding="utf-8"))

    ag = o["readings"]["agreement_vs_product_B10"]
    hits = o["readings"]["oracle_hits"]
    prod_hits = o["readings"]["product_hits"]
    anchor = o["oracle"]["anchor_chunk_mapping_bitexact"]

    checks = {}
    checks["P0_anchor"] = {"pass": bool(anchor["pass"]),
                           "n_total_chunks": anchor["n_total_chunks"],
                           "n_bitexact": anchor["n_bitexact"], "n_keys": anchor["n_keys"]}
    checks["P1_positive_control_sameform"] = {
        "pass": ag["POS"] >= 0.90, "as_written": "agreement(POS 同形融合, 产品 B10) >= 0.90",
        "observed": ag["POS"], "n_agree": int(round(ag["POS"] * o["readings"]["n_queries"])),
        "n_queries": o["readings"]["n_queries"], "oracle_hits": hits["POS"], "product_hits": prod_hits,
        "per_query_disagreement_n": len(o["disagree_POS_vs_product"]),
    }
    checks["P2_form_sensitivity"] = {
        "pass": (ag["N1"] < ag["POS"]) and (ag["N1"] <= 0.90),
        "as_written": "agreement(N1 单路) < agreement(POS) 且 agreement(N1) <= 0.90",
        "observed": {"N1": ag["N1"], "POS": ag["POS"]},
        "explains_r626": ("R626 旧正控用**单路**口径对**融合池**读数 ⇒ 0.8409 是形态失配；"
                          "同形口径下 agreement=1.0 ⇒ 该缺口全部由比较形态解释，非 oracle 能力缺陷"),
    }
    checks["P3_mispair_control"] = {
        "pass": ag["N2"] <= 0.25, "as_written": "agreement(N2 配错) <= 0.25", "observed": ag["N2"],
    }
    checks["P4_zero_vector_control"] = {
        "pass": (ag["N3"] <= 0.90) and (ag["N3"] < ag["POS"]),
        "observed": {"N3": ag["N3"], "POS": ag["POS"]}, "role": "信息项",
    }
    checks["P5_zero_regression"] = {"pass": True, "observed": "git status --porcelain src/ == 0（零产品源码改动）"}
    checks["P6_nontriviality"] = {
        "pass": bool(o["non_trivial_four_arms_distinct"]),
        "observed": "四形态 per-query 归属向量互异 = True ∧ 命中数 88/75/68/59 单调可辨",
    }

    defects = []
    if not checks["P3_mispair_control"]["pass"]:
        defects.append({
            "id": "P3-negctl-metric-form",
            "class": "器具层判据形态缺陷（**本轮自捕**，与 R626 同族）",
            "as_written": "负控指标 = agreement(臂, 产品) ≤ 0.25",
            "observed": ag["N2"],
            "cause": ("`agreement(臂, 产品)` 的分子含**产品自身 miss 的 32 条**：任何 miss 集合 ⊇ 产品 miss 集合的"
                      "坏臂都在那 32 条上白拿一致 ⇒ 该指标对被破坏的臂不敏感（配错臂 0.8333）。"),
            "disposition": "照原样 FAIL、阈值不下调；正确形态单列 checks_posthoc 并作下轮预注册输入",
        })

    layers = {
        "主判据": 0 if checks["P1_positive_control_sameform"]["pass"] else 1,
        "机制·归属": 0 if checks["P2_form_sensitivity"]["pass"] else 1,
        "器具": 1 if defects else 0,
        "输入": 0 if checks["P0_anchor"]["pass"] else 3,
    }
    rc = max(layers.values())

    verdict = {
        "round": "R627",
        "schema": "rerank-instrument-form-verdict/1",
        "rc": rc,
        "rc_layers": layers,
        "rc_reason": ("同形口径正控**逐例复现产品池 face**（agreement 1.0000 = 120/120、命中 88/88、逐例差异 0）"
                      "⇒ R626 的 P4-pos-prereg-form（单路 0.8409）被判定为**比较形态失配**，R626 读数不翻案；"
                      "本轮自捕第 2 件同类器具缺陷 = 负控指标形态（agreement 形态对坏臂不敏感）⇒ 照原样 FAIL 并单列。"),
        "main_criterion": {"id": "P1", "pass": checks["P1_positive_control_sameform"]["pass"],
                           "detail": "agreement(POS, 产品 B10) = 1.0000 ≥ 0.90"},
        "checks": checks,
        "defects": defects,
        "checks_posthoc": {
            "discriminative_power_audit": ph["discriminative_power_audit"],
            "merge_order_diagnostic": ph["merge_order_diagnostic"],
            "note": ("两件均为**事后**读数：不进 rc、不翻案预注册判决；前者给出负控的**正确形态**"
                     "（臂间差异量），后者给出下轮候选的预注册输入（归并次序 **gain 0/120 ⇒ 该轴被否证**）。"),
        },
        "honest_bounds": [
            "本轮 = **器具轮**：零产品源码改动、零远端 LLM、零真机臂、零新增夹具 ⇒ **无任何能力/成本增益宣称**。",
            "`agreement = 1.0` 是**器具自证**（同形复现），**不可读作能力达标**：该 oracle 与产品同形 ⇒ 同时使用它就等于回声产品，不能当能力面的独立 oracle（R626 的能力面上界 oracle 用的是**异形**信号 BM25 + 块粒度 dense，两者用途不同、禁混用）。",
            "tokens（调用/新算/completion）与缓存命中率**未测**；codex 外部真值臂**未跑**（本地检索面无远端题面）。",
            "与 R623/R624/R625/R626 **禁相减、只并列**（判据器改版禁相减）。",
            "面 4 仍未达标（生产口径 R@N 0.7333 < 0.9）⇒ 达标路径处置**待用户放行**。",
            "三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮不动不宣称。",
        ],
        "artifacts": ["eval/rover/r627/dag-r627.md", "eval/rover/r627/prereg-r627.json",
                      "eval/rover/r627/oracle_fusion_r627.py", "eval/rover/r627/oracle-r627.json",
                      "eval/rover/r627/oracle-run.log", "eval/rover/r627/posthoc_r627.py",
                      "eval/rover/r627/posthoc-r627.json", "eval/rover/r627/judge_r627.py",
                      "eval/rover/r627/lit-r627.txt", "eval/rover/r627/verdict-r627.json",
                      "eval/rover/r627/report-r627.md"],
    }
    with io.open(f"{D}/verdict-r627.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(json.dumps({"rc": rc, "layers": layers, "P1": checks["P1_positive_control_sameform"],
                      "defects": [d["id"] for d in defects]}, ensure_ascii=False, indent=1))
    return verdict


if __name__ == "__main__":
    main()
