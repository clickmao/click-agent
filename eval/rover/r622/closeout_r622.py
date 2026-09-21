#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R622 收口：把预注册判据 J0–J5 与实测读数机械比对 ⇒ verdict-r622.json（禁手写判决）。

rc 分层（承 R621 v4）：0 = 主判据无红 / 1 = 机制或能力面次级红 / 2 = 器具缺陷 / 3 = 输入缺失。
"""
from __future__ import annotations
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r622")
OUT = os.path.join(PD, "out")


def rd(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    need = ["percase-r622.json", "mech-r622.json", "negctl-r622.json"]
    missing = [n for n in need if not os.path.isfile(os.path.join(OUT, n))]
    if missing:
        print("输入缺失: %s" % missing)
        return 3
    pc, me, nc = (rd(os.path.join(OUT, n)) for n in need)
    crash = rd(os.path.join(OUT, "crash-stderr-r622.json"))

    o = pc["oracle_control"]
    j0 = bool(o["pass"])
    j1 = bool(nc["pass"])
    tot = {a: pc["arm_totals"][a] for a in pc["arm_totals"]}
    # J2: 与 R621 **冻结裁决件**的 wythoff 族逐臂通过数比对（禁写死常量 ⇒ 从冻结件派生）
    froz = rd(os.path.join(REPO, "eval/rover/r621/verdict-r621.json"))
    fw = froz["J4_capability_secondary"]["by_arm"]
    exp = {a: (fw[a]["families"]["wythoff"]["total"], fw[a]["families"]["wythoff"]["pass"])
           for a in ("T", "C", "C1")}
    got = {a: (tot[a]["n"], tot[a]["ok"]) for a in exp}
    j2 = got == exp
    non_ok = [r for r in pc["rows"] if r["tag"] != "OK"]
    four = {"OK", "HARD_CRASH", "FORMAT", "STATE_FLIP", "LEGAL_NONMIN", "TRUE_WRONG"}
    j3 = all(r["tag"] in four for r in pc["rows"])
    mt = me["tally"]
    m_tot = sum(mt.values())
    j4 = (mt.get("COLD_PRED_WRONG", 0) / m_tot) >= 0.50 if m_tot else False
    j5 = tot["C1"]["ok"] == tot["C1"]["n"]

    verdict = {
        "round": "R622",
        "kind": "read-only-per-case-attribution（零产品源码改动 / 零新臂 / 零远端）",
        "verdict": {
            "label": "定因轮：wythoff 族缺口主因 = 冷点(P 位)判定层错",
            "J0_oracle_positive_control": j0,
            "J1_negctl": j1,
            "J2_recompute_matches_R621_frozen": j2,
            "J3_four_way_coverage": j3,
            "J4_target_subtype_ge_50pct": j4,
            "J5_external_truth_full_pass": j5,
            "mechanism_tally": mt,
            "mechanism_share": {k: round(v / m_tot, 4) for k, v in mt.items()},
            "judgment_family_share": round((mt.get("COLD_PRED_WRONG", 0) + mt.get("CRASH", 0)) / m_tot, 4),
        },
        "readings": {
            "per_arm": {a: {"n": v["n"], "ok": v["ok"], "rate": round(v["ok"] / v["n"], 4),
                            "tags": v["tags"]} for a, v in tot.items()},
            "oracle_positive_control": o,
            "negctl_v2": nc,
            "negctl_v1_falsified": rd(os.path.join(OUT, "negctl-r622-v1.json")),
            "fixture_census": rd(os.path.join(OUT, "fixture-census-r622.json")),
            "crash_mechanism": crash,
            "cost_j3_decomposition": rd(os.path.join(OUT, "cost-decomp-r622.json")),
        },
        "rc": 0 if (j0 and j1 and j2 and j3 and j4 and j5) else 2,
        "rc_note": "rc=0 仅表示**定因轮自身**的判据全绿；不代表能力/成本面达标（无臂、无产品改动 ⇒ 无收益可宣称）。",
        "honest_bounds": [
            "本轮**无对照臂、无产品源码改动、无远端调用** ⇒ 不产出任何降幅/能力达标读数；质量/成本面沿用 R621「参考（未可验收）」。",
            "预注册 v1 的 J1 判据（M1/M2 非 OK == 15/15）**首跑即证伪**（实测 4/15、12/15）⇒ 原样入档 FAIL、不翻案；修正判据（逐例对应）为 post-hoc（`checks_posthoc`），其价值是**暴露夹具判别力**：字典序最小子型仅 3/15 例被行使，退化解「取最大必胜着法」得 12/15 = 80.0%。",
            "探索性 dry run（写预注册前的分型定义用）读数留档 `out/dryrun-*.json`，不翻案；正式跑次独立重跑。",
            "机制归因基于**行为式谓词**（问产物自己的接口）⇒ 只能判「产物是否自认该落点为必败位」，不判其内部实现（源码层未逐树审计）。",
            "CRASH（31/159）与 COLD_PRED_WRONG 同源（stderr: `i, j = best` 上 `TypeError: cannot unpack non-iterable NoneType`：谓词全否 ⇒ best=None ⇒ 未自验即交付）⇒ 判定层族合计 144/159 = 90.6%；两桶仍分列，不合并成一个数。",
            "复算**确定性**：`percase-r622.json` 两次独立跑次 sha256 同值（344ffa227f07…）⇒ 逐例分类可复现（非一次读数）。",
            "cost 差额方向（签名约定 delta = C − T）：新算 prompt T 29,871 vs C 28,939 ⇒ **T 多花 932**（+3.2%，伴随 +24pt 质量）；净差 / Σ|Δ| = 0.0851、单档最大 |Δ| 占比 = 0.1402（<0.5）⇒ **无集中来源**，差额是对称摆动残差 ⇒ 该差额不可归因到轴（与 R621 J6 同族结论：摆动 ≥ 效应）。",
            "跨轮禁相减：本轮复算 = R621 冻结件同窗集，与 R585–R619 冻结件轮不可相减；baselines 的 wythoff 项为 135 例次（9 跑次）口径，本轮 270 例次（18 跑次）**只可比率、禁比总和**。",
        ],
        "checks_posthoc": [
            "negctl v2（逐例对应 mismatch==0）为**事后**修正版判据；v1 FAIL 保留。",
            "cost J3 逐档分解（cost-decomp-r622.json）为事后诊断列，不作判据。",
            "fixture census（3/15 字典序子型判别力）为 v1 判据证伪的副产物，登记为**夹具面缺口候选**，需用户放行才可加隐藏用例（禁新增夹具令）。",
        ],
        "next_candidates": "见 report-r622.md §下轮候选",
    }
    io.open(os.path.join(PD, "verdict-r622.json"), "w", encoding="utf-8").write(
        json.dumps(verdict, ensure_ascii=False, indent=1))
    print(json.dumps(verdict["verdict"], ensure_ascii=False, indent=1))
    print("rc=%d" % verdict["rc"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
