#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R620 判据器**影子自检**（承 skill kpi-eval-harness-design「判据器上线前先跑影子自检」＋
R419「仪器自证四态夹具回放」）。

真机臂昂贵且一次只跑一遍 ⇒ 上线前用**合成台账**逐态断言判据行为。五态:
  A 正常档        : T 档 exec_source=candidates ∧ 四字段齐备守恒 ∧ C 档四字段缺席 ∧ 前缀两臂同源
                    ⇒ 期望 J0∧J1a∧J1b∧J1c = True，且 defects 里无 J0/J1 项
  B 两臂不可区分  : C 档也带四字段 ⇒ 期望 J0=False ∧ J1c=False ∧ J1=False，defects 含「J0 臂轴未生效」
  C 真空档        : T 档四字段**全缺席** ⇒ 期望 J1b=False ∧ J1=False，defects 含「J1 真空绿闸」
  D 守恒违例      : executed > accepted-unmapped ⇒ 期望 J1b=False ∧ conservation_violations>=1
  E 跨轮锚不成立  : T 前缀 != R617 pin ⇒ 期望 J0 仍 True（可归因性不依赖跨轮），claims_violated 非空

rc 语义: 0 全态符合 / 2 有态不符（判据无牙或行为漂移） / 3 环境缺失（judge 不在盘上）
用法: python3 eval/rover/r620/selftest_judge_r620.py
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
JUDGE = os.path.join(REPO, "eval/rover/r620/judge_r620.py")
PREFIX_PIN = "25c97befa2124549b52991c0338324ceee7f7702a6348641ed917d3b7b658052"
WINS = ("w211", "w212", "w213")


def dump_usage(adapter, side, idx, prompt=1000, hit=900, comp=50):
    p = os.path.join(adapter, "side-%s-%03d.json" % (side, idx))
    json.dump({"request": {"model": "deepseek-flash"},
               "response": {"usage": {"prompt_tokens": prompt, "prompt_cache_hit_tokens": hit,
                                      "prompt_cache_miss_tokens": prompt - hit,
                                      "completion_tokens": comp}}},
              io.open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return idx


def transcript(path, **kw):
    tr = {"calls": 1, "rc": 0, "stage": "done", "repair_rounds": 0, "exec_repairs": 0, "probe_repairs": 0,
          "steps_executed": 1, "plan_steps_total": 1, "self_test_unmet": 0, "correctness_asserted": 1,
          "public_probe_ran": 1, "public_probe_failed": 0, "public_probe_total": 2,
          "public_probe_reason": "", "artifact_carryover_enabled": False,
          "artifact_carryover_rounds": 0, "artifact_carryover_chars": 0,
          "action_candidates_present": 1, "action_candidates_declared": 4,
          "action_candidates_accepted": 4, "action_candidates_rejected": 0,
          "prefix_sha256": PREFIX_PIN, "task_sha256": "t" * 64}
    tr.update(kw)
    for k in list(tr):
        if tr[k] is None:
            del tr[k]
    json.dump(tr, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cases(path, n_pass=58, n_total=58, fam="wythoff"):
    lines = []
    for i in range(1, n_total + 1):
        lines.append("CASE %s#%d-public %s" % (fam, i, "PASS" if i <= n_pass else "FAIL"))
    io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def build(root, state):
    """构造合成 run 根; state 决定注入哪种偏差。"""
    D = os.path.join(root, "runs")
    ad = os.path.join(D, "adapter")
    os.makedirs(ad, exist_ok=True)
    idx = 0
    runs = []
    for W in WINS:
        # C1 codex ×1
        idx += 1
        a = dump_usage(ad, "codex", idx)
        sub = "codex"
        g = os.path.join(D, W, sub, "g1")
        os.makedirs(g, exist_ok=True)
        cases(os.path.join(g, "cases.txt"))
        transcript(os.path.join(g, "transcript.json"))
        runs.append({"arm": "C1", "win": W, "rep": 1, "sub": sub, "range": [a - 1, a]})
        for arm, base, dose in (("T", "agentT", "exec1"), ("C", "agentC", "unset")):
            for rep in (1, 2, 3):
                idx += 1
                a = dump_usage(ad, "agent", idx)
                sub = "%s-r%d" % (base, rep)
                g = os.path.join(D, W, sub, "g1")
                os.makedirs(g, exist_ok=True)
                cases(os.path.join(g, "cases.txt"))
                kw = {}
                if dose == "exec1":
                    kw.update(exec_source="candidates", action_candidates_executed=3,
                              action_candidates_unmapped=1, action_candidates_expect_inherited=2)
                else:
                    # 对照档: 四字段**缺席**（产品缺省 off ⇒ 逐字节同旧）
                    pass
                if state == "C_vacuous" and dose == "exec1":
                    kw = {}                                     # T 档四字段全缺席 ⇒ 真空
                if state == "B_indistinguishable" and dose == "unset":
                    kw.update(exec_source="plan", action_candidates_executed=2,
                              action_candidates_unmapped=0, action_candidates_expect_inherited=0)
                if state == "D_conservation" and dose == "exec1":
                    kw.update(action_candidates_executed=9)     # accepted=4, unmapped=1 ⇒ mapped=3 < 9 ⇒ 违例
                if dose == "exec1" and state == "F_fallback_ok" and rep in (2, 3):
                    # 第三刀: 空执行面 ⇒ 回退读 plan（面=plan_fallback）且**真把活干起来**
                    kw.update(exec_source="plan_fallback", exec_fallback="candidates_absent",
                              action_candidates_executed=3)
                if dose == "exec1" and state == "G_fallback_empty" and rep in (2, 3):
                    # 回退命中但执行面仍空 ⇒ 必须判红（EXERCISED_EMPTY）
                    kw.update(exec_source="plan_fallback", exec_fallback="accepted_empty",
                              action_candidates_executed=0)
                if dose == "exec1" and state == "H_d1_form" and rep == 3:
                    # D1 形态: 面=candidates 而 executed==0（R618 实测的空转形态）⇒ 必须判红
                    kw.update(exec_source="candidates", action_candidates_executed=0)
                if state == "E_cross_anchor":
                    # 两臂**同源**前缀（可归因性成立）但与 R617 pin 不同 ⇒ 只触「宣称面」
                    kw.update(prefix_sha256="f" * 64)
                transcript(os.path.join(g, "transcript.json"), **kw)
                runs.append({"arm": arm, "win": W, "rep": rep, "sub": sub, "range": [a - 1, a]})
    os.makedirs(os.path.join(D, "logs"), exist_ok=True)
    with io.open(os.path.join(D, "logs", "runs.jsonl"), "w", encoding="utf-8") as f:
        for r in runs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return D


def run_judge(D, pd):
    p = subprocess.run([sys.executable, JUDGE, "--D", D, "--pd", pd],
                       capture_output=True, text=True, timeout=300)
    vp = os.path.join(pd, "verdict-r620.json")
    v = json.load(io.open(vp, encoding="utf-8")) if os.path.isfile(vp) else None
    return p.returncode, v, p.stdout + p.stderr


def main():
    if not os.path.isfile(JUDGE):
        print("ENV_MISSING judge=%s" % JUDGE)
        return 3
    root = tempfile.mkdtemp(prefix="r620-selftest-")
    fails = []
    try:
        # ---- A 正常档 ----
        D = build(os.path.join(root, "A"), "A_ok")
        pdA = os.path.join(root, "pdA")
        os.makedirs(pdA, exist_ok=True)
        rcA, vA, outA = run_judge(D, pdA)
        chk = []
        j0 = (vA or {}).get("J0_arm_axis_effective", {})
        j1 = (vA or {}).get("J1_exec_face_consumed", {})
        chk.append(("A_J0_pass", j0.get("pass") is True))
        chk.append(("A_J0_T_all_candidates", j0.get("by_arm", {}).get("A_T_exec_source_in_allowed_faces") is True))
        chk.append(("A_J0_C_absent", j0.get("by_arm", {}).get("B_C_new_fields_absent") is True))
        chk.append(("A_J0_prefix_shared", j0.get("by_arm", {}).get("C_prefix_shared") is True))
        chk.append(("A_J0_cross_anchor", j0.get("by_arm", {}).get("D_cross_round_pin") is True))
        chk.append(("A_J1_pass", j1.get("pass") is True))
        chk.append(("A_J1a", j1.get("J1a_exec_face_driven") is True))
        chk.append(("A_J1b", j1.get("J1b_conservation_non_vacuous") is True))
        chk.append(("A_J1c", j1.get("J1c_arms_distinguishable") is True))
        chk.append(("A_J1d", j1.get("J1d_exec_face_forms_zeroed") is True))
        # NOT_EXERCISED：本轮合成 A 态无回退跑次 ⇒ 三态必须落到「未行使」且**不判红**（禁把未测读成通过）
        chk.append(("A_J1e_not_exercised", j1.get("J1e_fallback_three_state") == "NOT_EXERCISED"
                    and j1.get("J1e_red_only_on_empty") is True))
        chk.append(("A_J0_allowed_faces", j0.get("by_arm", {}).get("A_T_face_set") == ["candidates"]))
        chk.append(("A_no_J0_defect", not any("J0 臂轴未生效" in d for d in (vA or {}).get("instrument_defects", []))))
        chk.append(("A_no_vacuous_defect", not any("真空绿闸" in d for d in (vA or {}).get("instrument_defects", []))))
        chk.append(("A_no_claims", (vA or {}).get("claims_violated") == []))
        # 合成根下 J3v2 的真实 runs 根不存在 ⇒ 只允许这一类**合成面**缺陷（如实登记其边界）
        chk.append(("A_defects_only_synthetic_j3v2",
                    all("J3v2" in d for d in (vA or {}).get("instrument_defects", []))))
        tr = j1.get("by_arm", {}).get("T", {}).get("per_run", [])
        chk.append(("A_T_runs_executed_positive", j1.get("by_arm", {}).get("T", {}).get("runs_executed_positive") == 9))
        chk.append(("A_conservation_zero", j1.get("by_arm", {}).get("T", {}).get("conservation_violations") == 0))
        fails += ["A:%s" % n for n, ok in chk if not ok]

        # ---- B 两臂不可区分 ----
        DB = build(os.path.join(root, "B"), "B_indistinguishable")
        pdB = os.path.join(root, "pdB")
        os.makedirs(pdB, exist_ok=True)
        rcB, vB, _ = run_judge(DB, pdB)
        j0b = (vB or {}).get("J0_arm_axis_effective", {})
        j1b = (vB or {}).get("J1_exec_face_consumed", {})
        chk = [("B_J0_false", j0b.get("pass") is False),
               ("B_C_not_absent", j0b.get("by_arm", {}).get("B_C_new_fields_absent") is False),
               ("B_J1c_false", j1b.get("J1c_arms_distinguishable") is False),
               ("B_J1_false", j1b.get("pass") is False),
               ("B_defect_named", any("J0 臂轴未生效" in d for d in (vB or {}).get("instrument_defects", [])))]
        fails += ["B:%s" % n for n, ok in chk if not ok]

        # ---- C 真空档（T 四字段全缺席） ----
        DC = build(os.path.join(root, "C"), "C_vacuous")
        pdC = os.path.join(root, "pdC")
        os.makedirs(pdC, exist_ok=True)
        rcC, vC, _ = run_judge(DC, pdC)
        j0c = (vC or {}).get("J0_arm_axis_effective", {})
        j1c = (vC or {}).get("J1_exec_face_consumed", {})
        chk = [("C_J0_false", j0c.get("pass") is False),          # T 档无 exec_source ⇒ 轴未生效
               ("C_J1b_false", j1c.get("J1b_conservation_non_vacuous") is False),
               ("C_J1_false", j1c.get("pass") is False),
               ("C_vacuous_named", any("真空绿闸" in d for d in (vC or {}).get("instrument_defects", []))),
               ("C_vacuous_reason", (j1c.get("vacuous_reason") or "").startswith("VACUOUS"))]
        fails += ["C:%s" % n for n, ok in chk if not ok]

        # ---- D 守恒违例 ----
        DD = build(os.path.join(root, "D"), "D_conservation")
        pdD = os.path.join(root, "pdD")
        os.makedirs(pdD, exist_ok=True)
        rcD, vD, _ = run_judge(DD, pdD)
        j1d = (vD or {}).get("J1_exec_face_consumed", {})
        chk = [("D_J1a_true", j1d.get("J1a_exec_face_driven") is True),
               ("D_J1b_false", j1d.get("J1b_conservation_non_vacuous") is False),
               ("D_J1_false", j1d.get("pass") is False),
               ("D_violations_ge1", j1d.get("by_arm", {}).get("T", {}).get("conservation_violations", 0) >= 1),
               ("D_not_vacuous", not any("真空绿闸" in d for d in (vD or {}).get("instrument_defects", [])))]
        fails += ["D:%s" % n for n, ok in chk if not ok]

        # ---- E 跨轮前缀锚不成立（宣称面 ≠ 判据面） ----
        DE = build(os.path.join(root, "E"), "E_cross_anchor")
        pdE = os.path.join(root, "pdE")
        os.makedirs(pdE, exist_ok=True)
        rcE, vE, _ = run_judge(DE, pdE)
        j0e = (vE or {}).get("J0_arm_axis_effective", {})
        chk = [("E_J0_true", j0e.get("pass") is True),            # 可归因性不依赖跨轮锚
               ("E_anchor_false", j0e.get("by_arm", {}).get("D_cross_round_pin") is False),
               ("E_claim_recorded", any("跨轮前缀锚" in c for c in (vE or {}).get("claims_violated", []))),
               ("E_no_hard_defect", not any("J0 臂轴未生效" in d for d in (vE or {}).get("instrument_defects", [])))]
        fails += ["E:%s" % n for n, ok in chk if not ok]

        # ---- F 回退行使且真干活（EXERCISED_OK） ----
        DF = build(os.path.join(root, "F"), "F_fallback_ok")
        pdF = os.path.join(root, "pdF")
        os.makedirs(pdF, exist_ok=True)
        rcF, vF, _ = run_judge(DF, pdF)
        j0f = (vF or {}).get("J0_arm_axis_effective", {})
        j1f = (vF or {}).get("J1_exec_face_consumed", {})
        chk = [("F_J0_pass", j0f.get("pass") is True),
               ("F_J0_face_set", sorted(j0f.get("by_arm", {}).get("A_T_face_set") or []) == ["candidates", "plan_fallback"]),
               ("F_J1d_true", j1f.get("J1d_exec_face_forms_zeroed") is True),
               ("F_J1e_exercised_ok", j1f.get("J1e_fallback_three_state") == "EXERCISED_OK"),
               ("F_J1_pass", j1f.get("pass") is True),
               ("F_fallback_runs_6", j1f.get("by_arm", {}).get("T", {}).get("runs_plan_fallback") == 6),
               ("F_reason_set", j1f.get("by_arm", {}).get("T", {}).get("fallback_reason_set") == ["candidates_absent"]),
               ("F_no_hard_defect", not any("J0 臂轴未生效" in d for d in (vF or {}).get("instrument_defects", [])))]
        fails += ["F:%s" % nm for nm, ok in chk if not ok]

        # ---- G 回退命中但执行面仍空（EXERCISED_EMPTY ⇒ 必须红；J1d 不掺和） ----
        DG = build(os.path.join(root, "G"), "G_fallback_empty")
        pdG = os.path.join(root, "pdG")
        os.makedirs(pdG, exist_ok=True)
        rcG, vG, _ = run_judge(DG, pdG)
        j1g = (vG or {}).get("J1_exec_face_consumed", {})
        chk = [("G_J1e_state", j1g.get("J1e_fallback_three_state") == "EXERCISED_EMPTY"),
               ("G_J1e_false", j1g.get("J1e_red_only_on_empty") is False),
               ("G_J1d_still_true", j1g.get("J1d_exec_face_forms_zeroed") is True),
               ("G_J1a_still_true", j1g.get("J1a_exec_face_driven") is True),
               ("G_J1_false", j1g.get("pass") is False)]
        fails += ["G:%s" % nm for nm, ok in chk if not ok]

        # ---- H D1 形态（candidates ∧ executed==0 ⇒ J1d 必须红） ----
        DH = build(os.path.join(root, "H"), "H_d1_form")
        pdH = os.path.join(root, "pdH")
        os.makedirs(pdH, exist_ok=True)
        rcH, vH, _ = run_judge(DH, pdH)
        j1h = (vH or {}).get("J1_exec_face_consumed", {})
        chk = [("H_J1d_false", j1h.get("J1d_exec_face_forms_zeroed") is False),
               ("H_zero_form_count_3", j1h.get("by_arm", {}).get("T", {}).get("runs_candidates_executed_zero") == 3),
               ("H_J1_false", j1h.get("pass") is False),
               ("H_J1e_not_exercised", j1h.get("J1e_fallback_three_state") == "NOT_EXERCISED")]
        fails += ["H:%s" % nm for nm, ok in chk if not ok]

        print(json.dumps({"states": {"A_ok": {"rc": rcA}, "B_indistinguishable": {"rc": rcB},
                                     "C_vacuous": {"rc": rcC}, "D_conservation": {"rc": rcD},
                                     "E_cross_anchor": {"rc": rcE},
                                     "F_fallback_ok": {"rc": rcF}, "G_fallback_empty": {"rc": rcG},
                                     "H_d1_form": {"rc": rcH}},
                          "checks_failed": fails, "n_failed": len(fails)},
                         ensure_ascii=False))
        print("A_J1_note: %s" % ((vA or {}).get("J1_exec_face_consumed", {}).get("note")))
        return 0 if not fails else 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
