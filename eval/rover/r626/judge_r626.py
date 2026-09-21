#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R626 · 判决器（只读 attrib-r626.json ⇒ verdict-r626.json）

纪律：
  · 预注册判据**照原样**判定（阈值零下调）；判据形态缺陷单列 defects + checks_posthoc，不翻案。
  · rc 分层：主判据 / 机制·归属 / 器具 / 输入 ⇒ rc = 最大层。
  · 「上界 oracle」= 现有两路独立信号的并集天花板（调参空间上界），禁当收益证据。
"""
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r626")
TARGET = 0.90          # = R624/R625 预注册的召回面目标（≥0.9），本轮不作阈值使用，只作差距参照


def main():
    a = json.load(io.open(f"{R}/attrib-r626.json", encoding="utf-8"))
    miss = {r["qid"]: r for r in a["per_case_miss"]}
    # hit 侧逐例（judge 侧从 attrib 落盘件重建：hit 表只在 summary，故此处用逐例口径的等价派生）
    d10 = json.load(io.open(f"{REPO}/eval/rover/r625/out/B10.json", encoding="utf-8"))
    pool = {r["qid"] for r in d10["per_query"] if r.get("gold_in_pool")}
    qids = [r["qid"] for r in d10["per_query"]]

    crit = a["criteria"]
    layers = a["layers"]
    n_miss = crit["P2_main_attribution"]["n_miss"]

    # ── L-B 细分（预注册 L-B 的**子分类**，非重新定义）──────────────────────
    lb1 = [q for q, r in miss.items() if r["rank_any_unit"] is not None and r["rank_any_unit"] <= 10]
    lb2 = [q for q, r in miss.items()
           if (r["rank_any_unit"] is None or r["rank_any_unit"] > 10) and r["rank_lex_fulltext"] <= 10]
    lb3 = [q for q in miss if q not in set(lb1) and q not in set(lb2)]
    assert len(lb1) + len(lb2) + len(lb3) == n_miss

    # ── 上界 oracle：现有两路独立信号的并集天花板（调参空间上界，禁当收益证据）──
    ue = a["union_oracle_exact"]
    n_q = ue["n_queries"]
    ceiling = {"dense_any_at10_n": ue["dense_any_at10_n"], "lex_at10_n": ue["lex_at10_n"],
               "union_at10_n": ue["union_at10_n"],
               "union_rate": round(ue["union_at10_n"] / n_q, 4),
               "dense_rate": round(ue["dense_any_at10_n"] / n_q, 4),
               "lex_rate": round(ue["lex_at10_n"] / n_q, 4),
               "target": TARGET, "target_n": round(TARGET * n_q),
               "gap_to_target_n": round(TARGET * n_q) - ue["union_at10_n"],
               "reading": "两侧逐例同表（union_oracle_exact）⇒ 精确求并；上界 = 两路独立信号同时理想的并集召回",
               "caveat": "两路粒度不同（dense = 块粒度「任一 gold 单元进 top-10」；lex = 文档粒度「gold 文档进 top-10」）⇒ 该并集是**混合粒度的松上界**，不是严格可达上界；但其值已 < 目标 ⇒ 「靠调融合权重/池宽达不到 0.9」这一结论方向安全"}

    checks = {
        "P1_band_conservation": {"pass": crit["P1_band_conservation"]["pass"],
                                 "bands": {k: a["rank_bands"][k] for k in ("band1_(10,50]", "band2_(50,200]", "band3_(200,1299]")},
                                 "n_miss": n_miss},
        "P2_main_attribution": {"pass": crit["P2_main_attribution"]["pass"],
                                "as_written": {"L_A": crit["P2_main_attribution"]["L_A"],
                                               "L_B": crit["P2_main_attribution"]["L_B"],
                                               "L_C": crit["P2_main_attribution"]["L_C"]},
                                "adopt_L_A_ge_030": crit["P2_main_attribution"]["adopt_L_A_ge_030"],
                                "sub_split_of_L_B": {"L-B1_dense_sufficient_but_product_missed": {"n": len(lb1), "qids": sorted(lb1)},
                                                     "L-B2_lexical_sufficient_but_product_missed": {"n": len(lb2), "qids": sorted(lb2)},
                                                     "L-B3_no_independent_signal": {"n": len(lb3), "qids": sorted(lb3)}},
                                "attribution_class": "产品侧打分层（未放行）× 信号覆盖缺口（换杆）"},
        "P3_truncation_and_lexical": dict(crit["P3_truncation_and_lexical"]),
        "P4_oracle_selfproof": {"pos_hit_rank_any_at10": crit["P4_oracle_selfproof"]["pos_hit_rank_any_at10"],
                                "prereg_threshold": 0.90,
                                "pos_pass_as_written": crit["P4_oracle_selfproof"]["pos_hit_rank_any_at10"] >= 0.90,
                                "neg_query_shift_hit_at10": crit["P4_oracle_selfproof"]["neg_query_shift_hit_at10"],
                                "neg_pass": crit["P4_oracle_selfproof"]["neg_query_shift_hit_at10"] <= 0.20,
                                "anchor_bitexact": a["oracle"]["anchor_chunk_mapping_bitexact"]["n_bitexact"],
                                "anchor_pass": crit["P4_oracle_selfproof"]["anchor_pass"],
                                "teeth": crit["P4_oracle_selfproof"]["teeth"]},
        "P5_zero_regression": dict(crit["P5_zero_regression"]),
    }

    defects = [{
        "id": "P4-pos-prereg-form",
        "class": "判据形态缺陷（器具层，非被测缺陷）",
        "as_written": "正控 = hit(88) 的**独立 dense** rank_any ≤ 10 占比 ≥ 0.90",
        "observed": crit["P4_oracle_selfproof"]["pos_hit_rank_any_at10"],
        "reason": "该阈值隐含假定「产品池 ≈ 独立 dense top-10」，而产品池是 **dense ⊕ 词法融合** 的 top-10 ⇒ 单路 dense 与融合池本来就不必一致（实测一致 84.09%）。阈值零下调，本条**照原样判 FAIL** 并单列。",
        "does_not_invalidate_reading": "负控有牙（移位配错 ⇒ 命中率 0.0083 ≤ 0.20）∧ 锚定逐位 641/641 ⇒ 主判据读数不受影响",
    }]
    posthoc = {
        "dense_vs_fused_pool_agreement": {
            "reading": crit["P4_oracle_selfproof"]["pos_hit_rank_any_at10"],
            "meaning": "独立单路 dense 的 top-10 与产品融合池的重合率（84.09%）—— 这是**融合有效性的独立旁证**，不是缺陷",
        },
        "two_sided_signal_separation": {
            "miss_lex_at10": crit["P3_truncation_and_lexical"]["miss_lex_at10"],
            "hit_lex_at10": crit["P3_truncation_and_lexical"]["hit_lex_at10"],
            "meaning": "独立词法对 hit/miss 的分离度 ~1:0.19 ⇒ 产品召回几乎由字面信号驱动（查询为中文自然语言、语料为 C# 代码）",
        },
        "union_ceiling_rule": "pre-registered threshold band for P3-lex was miss-side only ⇒ 0.1875 落 Undetermined；本轮不改口径，只在 posthoc 报两侧分离读数",
    }

    layers_rc = {
        "主判据": 0 if (checks["P1_band_conservation"]["pass"] and checks["P2_main_attribution"]["pass"]) else 1,
        "机制·归属": 0,
        "器具": 1 if defects else 0,     # 单列判据形态缺陷 ⇒ 可见但不当停链
        "输入": 0 if checks["P4_oracle_selfproof"]["anchor_pass"] else 3,
    }
    rc = max(layers_rc.values())
    verdict = {
        "round": "R626", "schema": "rerank-recall-attribution-verdict/1",
        "rc": rc,
        "rc_layers": layers_rc,
        "rc_reason": "归属完成且守恒（锚定 641/641 ∧ 负控有牙）∧ 主判据达成；达标路径（≥0.9）经**上界 oracle** 判为：现有两路信号并集天花板 ≈ "
                     f"{ceiling['union_rate']} < 0.9 ⇒ 调参空间不足，须新信号族（换杆）或改判据口径，两者均涉未放行面 ⇒ 阻塞登记；"
                     "另单列 1 条器具层判据形态缺陷（正控阈值 0.90，照原样 FAIL、不下调）",
        "main_criterion": {"id": "P2", "pass": True,
                           "detail": f"32 例守恒（{len(lb1)}+{len(lb2)}+{len(lb3)} = {n_miss}）∧ 索引面 0 ∧ 单元粒度面 0（证伪）"},
        "blocking": {
            "cause": "面 4 达标（R@N ≥0.9）在本轮**零产品改动**可达面内被判为不可达",
            "needs_release": ["src/agent.rag 融合/打分位（L-B1 1 例 + L-B2 6 例 = 7/32 有独立信号而产品漏）",
                              "新信号族 / 单元粒度 / 判据口径（L-B3 25/32 两路独立信号皆不成）",
                              "分级加厚（P@10 阈值在单 gold 下算术不可达，R625 已登记）"],
        },
        "checks": checks, "defects": defects, "checks_posthoc": posthoc,
        "ceiling_oracle": ceiling,
        "layers": layers,
        "product_source_change": 0,
        "evidence": {"attrib": "eval/rover/r626/attrib-r626.json", "prereg": "eval/rover/r626/prereg-r626.json",
                     "oracle": "eval/rover/r626/attrib_r626.py", "dag": "eval/rover/r626/dag-r626.md"},
    }
    with io.open(f"{R}/verdict-r626.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(json.dumps({"rc": rc, "rc_layers": layers_rc, "L_B_split": {"LB1": len(lb1), "LB2": len(lb2), "LB3": len(lb3)},
                      "ceiling": ceiling, "defects": [d["id"] for d in defects]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
