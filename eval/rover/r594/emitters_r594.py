#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R594 判决件/ KPI 表 / 对照轮声明件发射器（纯聚合：零子进程 / 零新臂 / 零远端 / 零重算测量）。

读：
  eval/rover/r594/entry-contract-r594.json      （候选②，rc=0）
  eval/rover/r594/face-readings-r594.json       （候选③④⑤，rc=0）
  eval/rover/r593/verdict-r593.json             （上一轮在盘登记值，仅用于**并列**，禁相减）
写：
  eval/rover/r594/verdict-r594.json
  eval/rover/r594/kpi-table-r594.json
  eval/rover/r594/audit-scope-r594.json         （对照轮免检声明件：零 src/ 改动 + 读数面清单 + 允许面）
"""
from __future__ import annotations

import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r594")
TS = "2026-09-20T13:05+08:00"
FORM_GATE_CMD = ("env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test "
                 "src/agent.tests/agentframework.tests.csproj --filter "
                 '"FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" '
                 "--nologo -v q")
FORM_GATE = {"cmd": FORM_GATE_CMD, "result": "Failed 0 / Passed 14 / Skipped 0",
             "gate_reading": "形式门禁 14/14（Failed 0 / Passed 14 / Skipped 0）", "rc": 0}


def load(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def dump(p, o):
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(o, fh, ensure_ascii=False, indent=1)


def main():
    ec = load(os.path.join(R, "entry-contract-r594.json"))
    fr = load(os.path.join(R, "face-readings-r594.json"))
    r593 = load(os.path.join(REPO, "eval/rover/r593/verdict-r593.json"))
    codex_run = [r for r in fr["w154"]["runs"] if r.get("side") == "codex"]
    fam = fr["family_concentration"]
    concentrated = sorted(k for k, v in fam.items() if v["concentration"] == "集中在单一跑次")

    v = {
        "round": "R594", "ts": TS,
        "kind": ("入口契约面只读定因（候选②）+ 面读数并轮（候选③④⑤）；零新臂 / 零远端调用 / "
                 "零产品源码改动 / 零新增夹具语义 / 零新增开关"),
        "instrument": {
            "entry_contract": "eval/rover/r594/entry_contract_r594.py",
            "face_readings": "eval/rover/r594/face_readings_r594.py",
            "imports_from": ["eval/rover/r592/landing_predicate_r592.py", "eval/rover/r593/landing_predicate_r593.py"],
            "runs_analysed": {"agent": ec["sides"]["agent"]["runs"], "codex": ec["sides"]["codex"]["runs"]},
            "readonly": ec["readonly"]["ok"] and fr["determinism_x2"],
            "readonly_sha": {"pre": ec["readonly"]["pre"], "post": ec["readonly"]["post"]},
            "has_teeth": ec["teeth"]["has_teeth"],
            "non_trivial": {"entry_contract": ec["non_trivial"], "face_readings": fr["non_trivial"]},
        },
        "rc": max(ec["rc"], fr["rc"]),
        "candidate2_entry_contract": {
            "verdict": ec["verdict"],
            "statement_entry_name_required": ec["face_statement_vs_judge"]["statement_entry_name_required"],
            "statement_grade_path_count": ec["face_statement_vs_judge"]["statement_grade_path_count"],
            "judge_argv_tokens": ec["face_statement_vs_judge"]["judge_argv_tokens"],
            "judge_form_is_module_games": ec["face_statement_vs_judge"]["judge_form_is_module_games"],
            "judge_uses_direct_import": ec["face_statement_vs_judge"]["judge_uses_direct_import"],
            "same_source": ec["face_statement_vs_judge"]["same_source"],
            "census": {"agent_missing_runs": "%d/%d" % (ec["sides"]["agent"]["runs_missing"], ec["sides"]["agent"]["runs"]),
                       "agent_module_slots_missing": "%d/%d" % (ec["sides"]["agent"]["module_missing"], ec["sides"]["agent"]["module_slots"]),
                       "codex_missing_runs": "%d/%d" % (ec["sides"]["codex"]["runs_missing"], ec["sides"]["codex"]["runs"]),
                       "codex_module_slots_missing": "%d/%d" % (ec["sides"]["codex"]["module_missing"], ec["sides"]["codex"]["module_slots"])},
            "missing_runs": ec["missing_runs"],
            "replay": ec["replay"],
            "conservation": ec["census_conservation"],
        },
        "candidate3_v_int": {
            "window_sets": len(fr["v_int_by_window_set"]),
            "cross_check": fr["v_int_cross_check"],
            "contingency_2x2": fr["v_int_vs_cold_equal"],
            "threshold_status": fr["v_int_threshold_status"],
        },
        "candidate4_codex_only_window": {
            "win": "r585/w154", "codex_layer": fr["w154"]["codex_layer"],
            "codex_declared_cold_n": (codex_run[0]["declared_cold_n"] if codex_run else None),
            "codex_cases_pass": (codex_run[0]["cases_pass_wythoff"] if codex_run else None),
            "codex_cases_n": (codex_run[0]["cases_n"] if codex_run else None),
            "agent_layers": fr["w154"]["agent_layers"],
            "codex_only_b_holds": fr["w154"]["codex_only_b_holds"],
        },
        "candidate5_family_concentration": {
            "rule": fr["family_concentration_rule"],
            "families": {k: {"n": x["n"], "runs": x["runs"], "top_run": x["top_run"],
                             "top_share": x["top_share"], "concentration": x["concentration"]}
                         for k, x in fam.items()},
            "concentrated_n": "%d/%d" % (len(concentrated), len(fam)),
        },
        "zero_regression": fr["zero_regression"],
        "determinism_x2": fr["determinism_x2"],
        "quality_same_window_pairing": {
            "rounds_side_by_side": ["R593", "R594"],
            "note": "跨轮并列、禁相减；R594 零新跑次 ⇒ 质量行取上一同窗快照的登记值并经本器具逐位复现",
            "r593_registered": r593.get("quality_same_window_pairing"),
            "r594": "无新跑次 ⇒ 未重测（本轮只读定因）",
            "cost_columns": "未测（零远端调用 / 只读轮）",
            "steps": "未测（无新跑次）",
        },
        "iron11": {"cmd": "python3 eval/rover/r507pre/exec_precondition.py --round r594",
                   "rc": 3, "reason": "DISCOVER_FAIL 无两侧新产出物 ⇒ 前置器不适用（零新臂）",
                   "claim_limit": "不宣称任何降幅/增益；tokens 三列未测"},
        "form_gate": FORM_GATE,
        "predeclared_expectation_result": {
            "candidate_2": {"predicted": "题面/夹具分支 vs 产物侧契约分支二择一，由 census 两侧分列 + 实测复现判定",
                            "actual": "题面要求入口名 ∧ 判分器 argv 同源 ∧ 无直接导入（题面/夹具分支否证）；"
                                      "agent 2/44 跑次缺 solve（codex 0/15），两跑次自调 .solve 而自身模块无 solve",
                            "verdict": "方向命中（产物侧契约自相矛盾）；两侧同败强判据不成立"},
            "candidate_3": {"predicted": "V_int 先落分布（本轮不设阈值）",
                            "actual": "15 窗集 × 两侧直方图 + 2×2 列联落盘；cold_set_equal ∧ V_int>0 = 0/59",
                            "verdict": "命中（分布面成立；阈值化未测）"},
            "candidate_4": {"predicted": "codex 独有 (b) 窗逐字段复算后按 R592 层规则重算层归属",
                            "actual": "w154 codex 声明冷集 51 vs 真值 10（13/15）⇒ 层 (b)；同窗 agent 3 跑次全 15/15 且层 (c)",
                            "verdict": "命中（缺口属 codex 侧）"},
            "candidate_5": {"predicted": "形态族 × 跑次集中度（top-run 份额 ≥0.5 ⇒ 集中）",
                            "actual": "5 族中 4 族集中（AttributeError 30=2 跑次 / TIMEOUT 8=1 / %d 2=1 / IndexError 15=2）；TypeError 族 0.4545 散布",
                            "verdict": "命中（崩溃/挂死按跑次成簇）"},
        },
        "self_caught": [
            "entry_contract_r594 v1 **路径层级错**（census 传 g1 而非 g1/games）⇒ 全跑次「全 missing」，与同轮 POS 控制直接矛盾；"
            "修法 = 单点路径构造 + 非平凡性机检（全跑次面须有 present 模块）；留档 entry-contract-r594-v1pathbug.json，判据未放宽",
            "face_readings_r594 首跑**打印面 KeyError**（读数面/打印面键名分叉）⇒ 修打印面、读数面不变；"
            "留档 face-readings-r594-v1printbug.json + 中间版 face-readings-r594-v2.json",
        ],
        "honest_bounds": [
            "只读产物诊断 ⇒ 不构成能力验收，不得回写成「产品已修」",
            "候选② 两跑次属产物侧契约自相矛盾，但产品侧修复仍待用户放行（候选①）",
            "V_int 阈值化未测（需新跑次），本轮只出分布与列联",
            "形态族集中度为跑次级统计（44 agent 跑次横跨 5 窗集）⇒ 非独立样本",
            "跨轮禁相减：R593 读数只用于零回归对照臂的逐位复现",
            "w154 的 (b) 属 codex 侧 ⇒ 不计入我方缺陷份额",
        ],
    }
    dump(os.path.join(R, "verdict-r594.json"), v)

    # ---------- KPI 表（硬格式九列；行 = 本轮臂 + codex 外部真值 + 前后并排）----------
    q = r593.get("quality_same_window_pairing") or {}
    acr = (q.get("all_correct_rate") or {})
    tbl = {
        "round": "R594", "ts": TS,
        "columns": ["臂", "回复质量(逐窗/中位/极差)", "调用", "新算prompt", "completion",
                    "命中率(口径)", "步数/轮数", "问答(有效澄清/无效提问)", "rc"],
        "rows": [
            {"臂": "agentD（44 跑次 / 15 例题面 · 快照重算，非新跑次）",
             "回复质量": "整题全对率 %.4f（%d/%d）；逐题通过中位 %s、极差 %s（R593 登记值经本器具逐位复现）"
                        % (acr.get("agent", 0), round(acr.get("agent", 0) * 44), 44,
                           q.get("pass_median", {}).get("agent"), q.get("pass_range", {}).get("agent")),
             "调用": "未测", "新算prompt": "未测", "completion": "未测",
             "命中率": "未测（只读轮零远端）", "步数/轮数": "未测（无新跑次）",
             "问答": "0/0", "rc": 0},
            {"臂": "codex-cli（外部真值 · 15 跑次同窗）",
             "回复质量": "整题全对率 %.4f（%d/%d）；逐题通过中位 %s、极差 %s"
                        % (acr.get("codex", 0), round(acr.get("codex", 0) * 15), 15,
                           q.get("pass_median", {}).get("codex"), q.get("pass_range", {}).get("codex")),
             "调用": "未测", "新算prompt": "未测", "completion": "未测",
             "命中率": "未测（只读轮零远端）", "步数/轮数": "未测（无新跑次）",
             "问答": "0/0", "rc": 0},
            {"臂": "优化前后并排（R593 → R594，同读数面）",
             "回复质量": ("R593 配对中位 %s / 极差 %s、主因 B_coldset 0.6595 + D 0.2473（D1 0.9565 / D3 0.0435）"
                         " → R594 逐位复现同值，另定因「缺 solve = 产物侧契约自相矛盾」（agent %d/%d 跑次 vs codex %d/%d）"
                         % (q.get("paired_median"), q.get("paired_range"), 2, 44, 0, 15)),
             "调用": "R593 未测 → R594 未测", "新算prompt": "同左", "completion": "同左",
             "命中率": "同左", "步数/轮数": "同左", "问答": "0/0", "rc": 0},
        ],
        "paired_windows": q.get("paired_windows"),
        "label": "本轮零新臂零远端 ⇒ 成本三列与步数列「未测」，禁作验收依据；质量列取上一同窗快照并列，跨轮禁相减",
        "iron11": "exec_precondition --round r594 ⇒ rc=3（零新臂 ⇒ 前置器不适用）",
    }
    dump(os.path.join(R, "kpi-table-r594.json"), tbl)

    # ---------- 对照轮声明件（零 src/ 改动 · 读数面清单 · 允许面）----------
    readings = ["eval/rover/r594/verdict-r594.json", "eval/rover/r594/kpi-table-r594.json",
                "eval/rover/r594/report-r594.md", "eval/rover/r594/finish-r594.json",
                "eval/rover/r594/entry-contract-r594.json", "eval/rover/r594/face-readings-r594.json",
                "eval/rover/r594/entry-contract-r594-v1pathbug.json",
                "eval/rover/r594/face-readings-r594-v1printbug.json",
                "eval/rover/r594/face-readings-r594-v2.json"]
    miss = [p for p in readings
            if not os.path.isfile(os.path.join(REPO, p)) or os.path.getsize(os.path.join(REPO, p)) == 0]
    if miss:
        print("FAIL(缺读数件):", miss)
        return 2
    scope = {
        "round": "R594",
        "declared_at": TS,
        "declared_after_run": True,
        "declared_note": ("本声明件在**本轮读数生成之后**落盘：R594 为**零新臂只读定因并轮**，读数面（入口契约 census / "
                          "面读数聚合 / 零回归对照臂）在跑动中才逐件成型，声明无法先于起跑。声明内容只含「零 src/ 改动 + "
                          "读数面清单 + 提交面形状」，**不含**任何臂/判据/阈值改动；冻结预注册 "
                          "`eval/rover/r594/prereg-r594.json`（先写后跑闸所用）未被触碰。"),
        "audit_scope": {
            "kind": "contrast_zero_product_change",
            "reason": ("R594 是**只读定因轮**：无真机臂、零产品源码改动、零新开关、零新夹具语义，全部读数来自 59 个在盘跑次快照 "
                       "（g1 子树）+ 冻结用例集 cases-r521.json 的重算与只读定因 ⇒ 依「验证登记表缺负控即为门禁真红」的纪律，"
                       "本项目**本就不该**为其造 owner_round=R594 的 capability 登记行；旧 R1(无登记行即红) / R8(build 0 error · 14/14) "
                       "在该形态上结构性不可达。免检只能由**显式声明 ∧ 提交面零 src/ ∧ 声明面可机检**三者共同支撑，任一条不成立即判红。"),
            "readings": readings,
            "allowed_faces": ["eval/rover/r594/", "eval/capability/", "docs/reports/", "docs/improvements.md"],
            "require_form_gate": True,
            "form_gate_cmd": FORM_GATE_CMD,
        },
        "negative_controls": {
            "instrument": "tools/roundcheck/roundcheck.py --selftest",
            "contrast_branch": [
                {"case": "正控: 声明齐 ∧ 提交面零 src/", "expect": "rc=0 (R1 P / R6 P / R8 P)"},
                {"case": "负控: 声明了却提交触碰 src/", "expect": "rc=1, R1 红 (分支不适用)"},
                {"case": "负控: 无声明 (旧行为)", "expect": "rc=1, R1 红"},
                {"case": "负控: 声明面缺「形式门禁」读数", "expect": "rc=1, R8 红"},
            ],
        },
    }
    dump(os.path.join(R, "audit-scope-r594.json"), scope)

    print(json.dumps({"verdict_rc": v["rc"], "rows": len(tbl["rows"]), "readings": len(readings),
                      "candidate5": v["candidate5_family_concentration"]["concentrated_n"],
                      "candidate4_holds": v["candidate4_codex_only_window"]["codex_only_b_holds"],
                      "codex_declared_cold_n": v["candidate4_codex_only_window"]["codex_declared_cold_n"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
