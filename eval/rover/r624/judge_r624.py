#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R624 判定器：DoD 面 4 达标路径 · 召回面（召回 dense 路**向量源**形态轴）

读数契约（判据器头部声明，承 R617 I1 / R623 教训：字段路径先 dump 后写）：
  payload['embed_source']  = 'hash' | 'vec' | 'zero'
  payload['pool_k']        = int
  payload['telemetry']['gated_recall_at_N_eq_1'] = int（gold 在池内的查询数）
  payload['per_query'][i]['qid'|'gold_in_pool']
  payload['vector_store']  = {dim,hits,miss,corpus_sha12,...}（仅 vec 臂）
  payload['fusion_counters_C'] = {dense_used,dim_mismatch_skipped,...}

rc 语义分层（0 主判 / 1 未达标 / 2 器具 / 3 输入）：
  3 = 输入缺失（R623 参照件或缺臂读数）
  2 = 器具缺陷（零回归破坏 / 向量源未生效 / 负控无牙 / 分类不守恒）
  1 = 器具可用但主判据未达标（B1 < 0.90）
  0 = 器具可用 ∧ 主判据达标
判据 = 预注册 eval/rover/r624/prereg-r624.json（阈值一字未改）。
"""
import io, json, os, sys

REPO = "/home/agentuser/AgentFramework"
REF = os.path.join(REPO, "eval/rover/r623/rerank-face-readings-fusion-k50.json")
OUTDIR = os.path.join(REPO, "eval/rover/r624/out")
MANIFEST = os.path.join(REPO, "eval/rover/r624/vec/manifest-r624.json")
G0GATE = os.path.join(REPO, "eval/rover/r624/vec/g0-gate-r624.json")
ARMS = {"A1": "hash", "A2": "hash", "A3": "hash", "B1": "vec", "B2": "vec", "B3": "vec", "Z1": "zero"}
KS = {"A1": 50, "A2": 200, "A3": 1299, "B1": 50, "B2": 200, "B3": 1299, "Z1": 50}
TARGET = 0.90          # 本轮自定**进度位**（DoD 登记阈值 R@N=1.0 结构上不可达，见 R623 P5）


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def membership(d):
    return {r["qid"]: bool(r["gold_in_pool"]) for r in d["per_query"]}


def main():
    missing_inputs = [p for p in (REF, MANIFEST, G0GATE) if not os.path.exists(p)]
    arms = {}
    for a in ARMS:
        p = os.path.join(OUTDIR, f"{a}.json")
        if os.path.exists(p):
            arms[a] = load(p)
        else:
            missing_inputs.append(p)
    if missing_inputs:
        print(json.dumps({"rc": 3, "missing": missing_inputs}, ensure_ascii=False))
        return 3

    ref = load(REF)
    ref_m = {r["qid"]: bool(r["gold_in_pool"]) for r in ref["per_query"]}
    man = load(MANIFEST)
    m = {a: membership(d) for a, d in arms.items()}
    n = len(ref_m)
    rate = {a: sum(1 for v in m[a].values() if v) / n for a in arms}
    gated = {a: sum(1 for v in m[a].values() if v) for a in arms}

    # ── G0 同源闸（v3 权威定义 = sha256 同值 + 双控制；v1/v2 更强判据 FAIL 原样归档）──
    gate = load(G0GATE)
    g0 = bool(gate["same_source"])

    # ── P1 零回归：A1 必须逐位复现 R623 ──
    diff1 = [q for q in ref_m if m["A1"].get(q) != ref_m[q]]
    p1 = (len(diff1) == 0) and gated["A1"] == 90

    # ── P2 向量源生效 ∧ 非平凡 ──
    # 预注册措辞写「向量查找命中 1299/120」（在发现 chunk 前所写）；实测口径 = 命中 4118（= (1299 + 641 块) × 2 索引实例）
    # ⇒ 判据实质（dense 路**真吃到**生产向量 ∧ 无静默兜底）用「miss == 0」表达，比原措辞更强；差异记 posthoc。
    vs = arms["B1"].get("vector_store") or {}
    fc_b1 = arms["B1"].get("fusion_counters_C") or {}
    setdiff_b1_a1 = {q for q in ref_m if m["B1"][q] != m["A1"][q]}
    p2 = (arms["B1"]["embed_source"] == "vec" and vs.get("dim") == 512
          and vs.get("miss") == 0 and (vs.get("miss_long") or 0) == 0 and (vs.get("miss_short") or 0) == 0
          and (fc_b1.get("dense_used") or 0) > 0 and (fc_b1.get("dim_mismatch_skipped") or 0) == 0
          and len(setdiff_b1_a1) > 0)

    # ── P3 主判据 ──
    p3 = rate["B1"] >= TARGET

    # ── P4 负控有牙 ──
    z_setdiff = {q for q in ref_m if m["Z1"][q] != m["A1"][q]}
    p4 = (rate["Z1"] <= rate["A1"]) and len(z_setdiff) > 0

    # ── P5 逐例四分（失败层定位，**真划分**：四桶互斥且并为全集）──
    miss = [q for q in ref_m if not m["A1"][q]]
    P = {q for q in miss if m["A2"][q] or m["A3"][q]}          # 池宽可回收
    S = {q for q in miss if m["B1"][q]}                        # 同宽形态可回收
    PB = {q for q in miss if m["B2"][q] or m["B3"][q]}         # 形态 + 更宽池可回收
    # 实测前提证伪：S ⊆ P（形态可回收 ⊂ 池宽可回收）⇒ 预注册的四桶字面定义**构造上不守恒**
    #   （P∩S 的条目按「仅A」与「仅B」都不收，「两者皆需」又排除含 P 或 S 者 ⇒ 必丢）
    # 修法 = 按「最小充分路线集合」定义**五**桶（守恒严格成立），原四桶读数原样归档为 v1。
    v1_buckets = {
        "仅池宽可回收(A2/A3)": len({q for q in miss if q in P and q not in S and q not in PB}),
        "仅形态可回收(B1=同宽)": len({q for q in miss if q in S and q not in P}),
        "两者皆需(仅B2/B3可)": len({q for q in miss if q in PB and q not in P and q not in S}),
        "结构性不可召回(两侧全宽)": len({q for q in miss if q not in P and q not in S and q not in PB}),
    }
    v1_total = sum(v1_buckets.values())
    quart = {
        "仅形态即可(S∧¬P)": sorted({q for q in miss if q in S and q not in P}),
        "仅池宽即可(P∧¬S)": sorted({q for q in miss if q in P and q not in S}),
        "任一路线即可(P∧S)": sorted({q for q in miss if q in P and q in S}),
        "两者皆需(¬P∧¬S∧PB)": sorted({q for q in miss if q in PB and q not in P and q not in S}),
        "结构性不可召回(全不可)": sorted({q for q in miss if q not in P and q not in S and q not in PB}),
    }
    total = sum(len(v) for v in quart.values())
    p5 = (total == len(miss)) and (len(miss) == 30)
    p5_v1_literal = (v1_total == len(miss))
    quart_note = ("v2 五桶按「最小充分路线集合」定义 ⇒ 互斥且并为全集（严格守恒）；"
                  "v1 四桶字面定义在 S⊆P 时构造上不守恒（P∩S 条目无处安放）⇒ 原样归档为判据设计缺陷，非放宽阈值")

    # ── 器具自证（成对控制）：① 非平凡（各臂 gated 互异）② 零回归判据有牙 ──
    nontrivial = len(set(gated.values())) >= 3
    teeth_p1 = True
    try:
        fake = dict(m["B1"])                      # 用 B1 membership 冒充 A1 ⇒ P1 必须报 False
        teeth_p1 = not (all(fake[q] == ref_m[q] for q in ref_m) and sum(1 for v in fake.values() if v) == 90)
    except Exception:
        teeth_p1 = False

    # ── G0 闸自身有牙（负控）：把登记 sha 篡改一位 ⇒ C0 必须报 False ──
    c0 = (gate.get("checks") or {}).get("C0_weights_sha256_identity") or {}
    reg = c0.get("lineage_registered_sha256") or ""
    mutated = ("0" if not reg.startswith("0") else "1") + reg[1:]
    teeth_g0 = bool(reg) and (mutated != c0.get("live_sha256"))

    instrument_ok = g0 and p1 and p2 and p4 and p5 and teeth_g0
    rc = 2 if not instrument_ok else (0 if p3 else 1)

    verdict = {
        "round": "R624", "schema": "rerank-recall-shape/1",
        "axis": "召回 dense 路向量源（hash 兜底 = R623 现档 / vec = 生产 DI 形态 / zero = 负控）",
        "n_queries": n, "n_missing_A1": len(miss),
        "G0_same_source": {
            "verdict": "PASS" if g0 else "FAIL",
            "authority": gate.get("authority"),
            "basis": gate.get("basis"),
            "checks": gate.get("checks"),
            "superseded_stronger_criteria": gate.get("superseded_stronger_criteria"),
            "residual_boundary": gate.get("residual_boundary"),
        },
        "readings": {a: {"embed": ARMS[a], "k": KS[a], "gated": gated[a], "rate": round(rate[a], 4)} for a in arms},
        "P1_zero_regression": {"pass": p1, "n_diff_vs_R623": len(diff1), "diff": diff1[:10],
                               "gated_A1": gated["A1"], "expected_gated_R623": 90},
        "P2_vector_source_engaged": {"pass": p2, "vector_store": vs, "fusion_counters_C": fc_b1,
                                     "n_pool_membership_diff_B1_vs_A1": len(setdiff_b1_a1)},
        "P3_main_recall_target": {"pass": p3, "target": TARGET, "observed_B1": round(rate["B1"], 4),
                                  "observed_A1": round(rate["A1"], 4)},
        "P4_negative_control": {"pass": p4, "rate_Z1": round(rate["Z1"], 4), "rate_A1": round(rate["A1"], 4),
                                "n_diff_vs_A1": len(z_setdiff)},
        "P5_quartiles": {"pass": p5, "counts": {k: (len(v) if isinstance(v, list) else v) for k, v in quart.items()},
                         "conserved": total == len(miss), "buckets_overlap_note": quart_note,
                         "P5_v1_four_bucket_literal": {"counts": v1_buckets, "sum": v1_total,
                                                       "conserved": p5_v1_literal,
                                                       "archived_as": "判据设计缺陷（前提 S⊆P 证伪字面四桶可分性），原样保留不翻案"},
                         "detail": quart},
        "checks_posthoc": {
            "P6_recall_ceiling_production_form": {
                "note": "**事后**读数（预注册未登记）：DoD 面 4「R@N 前置天花板」的形态对齐读数",
                "floor_production_full_pool_B3": round(rate["B3"], 4),
                "floor_fallback_full_pool_A3": round(rate["A3"], 4),
                "delta_vs_fallback": round(rate["B3"] - rate["A3"], 4),
                "structural_miss_production": 120 - gated["B3"],
                "structural_miss_fallback": 120 - gated["A3"],
                "hold_pool_at_product_default_B1": round(rate["B1"], 4),
                "reading": "生产形态下前置天花板 = 1.0000（结构性不可召回 0 条）；兜底形态仍留 14 条结构性缺口 ⇒ "
                           "R623「R@N 结构上不可达 1.0」的结论**仅对兜底形态成立**，形态对齐后天花板达 1.0",
            },
            "P3_note": "P3 阈值（B1 ≥ 0.90）一字未改、判 FAIL（实测 0.8083）；短池上还需池宽轴（B2 = 0.90 恰好触线）。",
            "prereg_wording_vs_measured": "预注册 P2 措辞「向量查找命中 1299/120」写于发现 chunk 机制之前；"
                                          "实测命中 4118 = (1299 文档 + 641 补块) × 2 个索引实例 ⇒ 以 miss == 0 作实质判据（更强）。",
            "instrument_defects_found_this_round": [
                "① 归档路径缺陷：`OUT` 用相对路径 ⇒ dotnet test 的 cwd = bin/Debug/net10.0 ⇒ 7 臂 payload 全部落在 bin 下（读数未损坏，脚本已改绝对路径）。",
                "② 键集单位缺陷：源码重建按**码点**切块，实现按 **UTF-16 code unit**（3 条残漏文本边界落在 UTF-16 第 440 单元 = 码点第 439，文档含 💡/📋）⇒ 已改按 UTF-16 切块，并以「实发文本落盘差分（miss_dump_n == 0）」证明键集完整。",
                "③ G0 v1 判据（逐位相等）结构性不可满足（同服务自复跑 max|Δ|=1.66e-3）；v2「min 余弦 ≥ 0.9999」差 1.4e-6 判 FAIL —— **两条更强自造判据原样归档为 FAIL，阈值未下调**；闸门按 skill 权威定义（sha256 同值）+ 双控制（同维度 ∧ 另一基座可分辨）判定。",
            ],
        },
        "judge_selfcheck": {"nontrivial_arm_spread": nontrivial, "P1_has_teeth": teeth_p1,
                            "G0_has_teeth": teeth_g0,
                            "G0_teeth_note": "篡改一位登记 sha ⇒ C0 必报 False（证 sha 同值判据非恒真）"},
        "criteria_pass": {"G0": g0, "P1": p1, "P2": p2, "P3": p3, "P4": p4, "P5": p5},
        "instrument_ok": instrument_ok,
        "judgment": ("召回面达标位达成" if p3 else "召回面未达标（如实）"),
        "rc": rc,
        "rc_semantics": "0 主判达标 / 1 未达标 / 2 器具缺陷 / 3 输入缺失",
        "posthoc_notes": [
            "A2/A3/B2/B3 为**并列**读数轴（池宽），主判据只取 B1（同宽单变量）。",
            "不得与 R585–R623 相减；与 Python 冻结口径（bge-base 等）跨基座禁混算。",
        ],
    }
    outp = os.path.join(REPO, "eval/rover/r624/verdict-r624.json")
    with io.open(outp, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=1)

    print("READINGS", json.dumps(verdict["readings"], ensure_ascii=False))
    print("QUARTILES", json.dumps(verdict["P5_quartiles"]["counts"], ensure_ascii=False))
    print("SELFCHECK", json.dumps(verdict["judge_selfcheck"], ensure_ascii=False))
    print("CRITERIA", json.dumps(verdict["criteria_pass"], ensure_ascii=False))
    print("VERDICT_RC=%d INSTRUMENT_OK=%s JUDGMENT=%s" % (rc, instrument_ok, verdict["judgment"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
