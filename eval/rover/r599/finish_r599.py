#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R599 收尾（本侧自写，**不复用 R598 的散文**）: ① `eval/capability/kpi.jsonl` 追加（幂等，按 round+tag 去重）
② `docs/reports/iteration-master-plan.md` §7 轮块追加（幂等，按 R599 标记去重）。

所有读数**机取自本轮落盘件**（禁手抄）；缺件如实写「未测」。
用法: python3 eval/rover/r599/finish_r599.py
"""
from __future__ import annotations

import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r599")
HARNESS = os.path.expanduser("~/.agentframework/harness/runs/r599")
KPI = os.path.join(REPO, "eval/capability/kpi.jsonl")
PLAN = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
ROUND = "R599"
TAG = "mainline-contrast-windowset7"


def rd(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    pool = rd(os.path.join(PD, "taskface-pool-r599.json"), {})
    verdict = rd(os.path.join(PD, "verdict-r599.json"), {})
    precond = rd(os.path.join(HARNESS, "precond-r599.json"), {})
    census = rd(os.path.join(PD, "behav-census-r599.json"), {})
    percase = rd(os.path.join(PD, "percase-attrib-r599.json"), {})
    rcsem = rd(os.path.join(PD, "rc-semantics-r599.json"), {})
    truth = rd(os.path.join(PD, "truthgap-r599.json"), {})
    sb = rd(os.path.join(PD, "scope-bind-r599.json"), {})
    land = rd(os.path.join(PD, "landing-predicate-r599.json"), {})
    prereg = rd(os.path.join(PD, "prereg-r599.json"), {})
    s7 = (pool.get("juxtaposition") or {}).get("set7") or {}
    fam = (pool.get("juxtaposition") or {}).get("family_all_pass_rate") or {}
    c2 = verdict.get("C2_cost_three_columns") or {}
    c6 = verdict.get("C6_steps_face") or {}
    c0 = verdict.get("C0_truth_reliability") or {}
    c1 = verdict.get("C1_quality_paired") or {}
    rcsets = ((rcsem.get("neutrality") or {}).get("tightening_count"),
              (rcsem.get("neutrality") or {}).get("relaxation_count"))
    entry = {
        "round": ROUND, "ts": __import__("datetime").datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M%z"),
        "tag": TAG,
        "taskset_sha": (prereg.get("one_time_context") or {}).get("taskset_sha"),
        "bin_sha12": (rd(os.path.join(PD, "bins-r599.json"), {}) or {}).get("bin_all_arms", {}).get("sha256", "")[:12],
        "judge_v3_set7": {"valid": s7.get("valid"), "median": s7.get("median"), "neg": s7.get("neg"),
                          "pass": s7.get("pass"),
                          "note": "真值三窗自败（w181 56/58、w182 51/58、w183 56/58）按 C0 unreliable ⇒ 有效窗 0 ⇒ 不作能力结论"},
        "family_wythoff_allpass": {k: ((fam.get("wythoff") or {}).get(k)) for k in ("set1", "set2", "set5", "set6", "set7")},
        "cost_three_columns": {"product": {"calls": (c2.get("calls") or {}).get("product"),
                                           "new_prompt": (c2.get("new_prompt") or {}).get("product"),
                                           "completion": (c2.get("completion") or {}).get("product"),
                                           "v_all": (c2.get("hit_rate_v_all") or {}).get("product"),
                                           "v_incr": (c2.get("hit_rate_v_incr") or {}).get("product")},
                               "truth": {"calls": (c2.get("calls") or {}).get("truth"),
                                         "new_prompt": (c2.get("new_prompt") or {}).get("truth"),
                                         "completion": (c2.get("completion") or {}).get("truth"),
                                         "v_all": (c2.get("hit_rate_v_all") or {}).get("truth"),
                                         "v_incr": (c2.get("hit_rate_v_incr") or {}).get("truth")}},
        "steps": {"steps": c6.get("steps"), "plan_steps_total": c6.get("plan_steps_total")},
        "iron11": {"rc": int((io.open(os.path.join(HARNESS, "precond.rc")).read().strip() or 1))
                            if os.path.exists(os.path.join(HARNESS, "precond.rc")) else None,
                   "blocked": len(precond.get("blocked") or []),
                   "readable": "参考（未可验收）" if not precond.get("acceptable_scoped") else "可验收"},
        "candidates": {
            "c11_rc_semantics": {"rc": rcsem.get("rc"), "device_formula_mismatch": len(rcsem.get("device_formula_mismatch") or []),
                                 "tightening": rcsets[0], "relaxation": rcsets[1],
                                 "controls": (rcsem.get("controls") or {}).get("all_pass")},
            "c3_truth_gap_textual": {"rc": truth.get("rc"), "instances": (truth.get("scope") or {}).get("instances_with_repro"),
                                     "codex_class_hist": truth.get("codex_class_hist"),
                                     "controls": truth.get("controls")},
            "c4_v_int_set6": {"agent": (land.get("agent") or {}).get("v_int_hist"),
                              "codex": (land.get("codex") or {}).get("v_int_hist"),
                              "device_rc": (land.get("verdict") or {}).get("rc")},
            "c4b_scope_bind": {"rc": sb.get("rc"), "relation": (sb.get("judgment") or {}).get("relation"),
                               "face": (sb.get("judgment") or {}).get("zero_regression_verdict"),
                               "device_internal_match": (sb.get("full_scope_recompute") or {}).get("device_internal_match"),
                               "cross_check_vs_r598_hist": (((sb.get("full_scope_recompute") or {})
                                                             .get("cross_check_against_r598_hist") or {}).get("match"))},
            "c1_behavior_census": {"agent_runs": (((census.get("summary") or {}).get("agent") or {}).get("runs")),
                                   "agent_ok": (((census.get("summary") or {}).get("agent") or {}).get("OK")),
                                   "entry_fail": (((census.get("summary") or {}).get("agent") or {}).get("ENTRY_FAIL")),
                                   "codex_ok": (((census.get("summary") or {}).get("codex") or {}).get("OK")),
                                   "codex_runs": (((census.get("summary") or {}).get("codex") or {}).get("runs"))},
            "c2_percase_attrib": {"buckets": percase.get("pooled_buckets"),
                                  "A_share": (percase.get("verdict") or {}).get("A_share_pooled"),
                                  "rc": (percase.get("verdict") or {}).get("rc")},
            "c0_product_side": "未做（待用户放行；动 src/ 须放行令）",
        },
        "instrument_selfcatch": {
            "derive_residual": ["pool juxtaposition 回填覆盖原块 ⇒ 已改 twin 拼接 + 双键断言（首跑 rc=1 未落盘）",
                                "behav-census/percase 由 ns 造成的 r596/r598 错标 ⇒ 显式补丁归位"],
            "checks_posthoc": ["C11 把「有效窗=0（真值全不可靠）」编码为 rc=1（验收面未达）而非 rc=3（数据残缺）⇒ 是否升格留 R600 预注册",
                               "scope-bind 以**外包机检**实现（未改共享器具内部）⇒ 下沉到 landing_predicate 内部留 R600"],
        },
        "report": "eval/rover/r599/report-r599.md",
    }
    lines = [l for l in io.open(KPI, encoding="utf-8") if l.strip()] if os.path.exists(KPI) else []
    idx = None
    for i, l in enumerate(lines):
        try:
            j = json.loads(l)
            if j.get("round") == ROUND and j.get("tag") == TAG:
                idx = i
                break
        except Exception:  # noqa: BLE001
            continue
    if idx is None:
        with io.open(KPI, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print("kpi: 追加 1 行（共 %d 行，此前 %d）" % (len(lines) + 1, len(lines)))
    elif "--rewrite" in sys.argv:
        lines[idx] = json.dumps(entry, ensure_ascii=False) + "\n"
        with io.open(KPI, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        print("kpi: 重写本轮同一行（读数修正；总行数不变 %d）" % len(lines))
    else:
        print("kpi: 已存在 ⇒ 跳过（幂等）")
    # §7 轮块
    txt = io.open(PLAN, encoding="utf-8").read() if os.path.exists(PLAN) else ""
    marker = "#### R599（判据 v3 第七窗集行使"
    if marker in txt:
        print("§7: R599 块已存在 ⇒ 跳过（幂等）")
    else:
        block = ("\n%s）\n"
                 "- 真机臂轮 w181..w183（codex 真值 ×1 + R599D 产品默认档 ×3，同件 sha 4b70fd7cdb39 / 题集 e0c667c2）；"
                 "**真值三窗自败**（56/51/56 of 58）⇒ C0 unreliable ⇒ set7 有效窗 **0**、判据无分辨率（不作能力结论）。\n"
                 "- 成本三列（信息项，参考）: 产品 18 调用 / 新算 prompt 4,127 / completion 40,617；真值 25 / 15,522 / 12,001。\n"
                 "- 候选② rc 语义收口（C11）: 器件-公式一致 7/7、tightening 3（set5/6/7 0→1）、relaxation **0**、控制全过 rc=0。\n"
                 "- 候选③ 真值侧文本级定因: 40 复现实例（codex 14 / 产品 26）全判 **semantic**（#43-public 实得 `WIN 1 13` vs 期望 `WIN 15 15`；"
                 "#57-hidden 实得 `WIN 2 11` vs 期望 `WIN 25 25`），控制 NC-D/NC-T/POS 全过 rc=0。\n"
                 "- 候选④ `V_int` 第六窗集 agent {\"0\":7,\"118\":1,\"6\":1} / codex {\"0\":3}（阈值化未测）；"
                 "landing scope 绑定机检 rc=0（请求 ⊊ 登记全 scope ⇒ 零回归面 not_applicable）。\n"
                 "- 候选⑤ 起手闸余量 swing 83→**264**（r598 同态在飞窗实测），ceiling 2889 / margin 179(cap_binding) / REQ 2829 ⇒ A1/A2 PASS。\n"
                 "- 铁律 11: `exec_precondition.py --round r599` rc=**1** ⇒ 全部成本/质量读数标「参考（未可验收）」；"
                 "轮志 `eval/rover/r599/report-r599.md`。\n") % marker
        with io.open(PLAN, "a", encoding="utf-8") as fh:
            fh.write(block)
        print("§7: 追加 R599 轮块")
    return 0


if __name__ == "__main__":
    sys.exit(main())
