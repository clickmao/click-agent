#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R619 判据器影子自检派生器（幂等 · 字节级 · 锚点必须命中）。

派生自 eval/rover/r618/selftest_judge_r618.py。**声明的差异**：
  ① 命名空间 618->619；窗集 WINS 208..210 -> 211..213。
  ② J0 键改名 A_T_exec_source_all_candidates -> A_T_exec_source_in_allowed_faces（判据面改为
     「T 档面集合 ⊆ {candidates, plan_fallback}」）；A 态新增 allowed_faces / J1d / J1e 三检查。
  ③ build() 新增三态注入（第三刀专面）：
       F_fallback_ok   : rep2,3 走 plan_fallback ∧ executed>0 ∧ exec_fallback=candidates_absent
       G_fallback_empty: rep2,3 走 plan_fallback ∧ executed==0           ⇒ J1e 判红
       H_d1_form       : rep3 走 candidates ∧ executed==0                ⇒ J1d 判红（隔离 J1d 的牙）
     三态都保留 rep1 = candidates ∧ executed>0 ⇒ J1a 仍真 ⇒ 被隔离的是 J1d/J1e 本身。
  ④ main() 新增 F/G/H 三态断言块 + NOT_EXERCISED 的「不判红但如实记未测」断言。
其余五态（A/B/C/D/E）**逐字继承**。
"""
import ast
import io

SRC = 'eval/rover/r618/selftest_judge_r618.py'
DST = 'eval/rover/r619/selftest_judge_r619.py'

s = io.open(SRC, encoding='utf-8').read()
n = 0


def rep(old, new, cnt=1):
    global s, n
    got = s.count(old)
    if got != cnt:
        raise SystemExit('ANCHOR_MISS count=%d expect=%d :: %r' % (got, cnt, old[:100]))
    s = s.replace(old, new)
    n += 1


# ---- ① 命名空间 ----
rep('eval/rover/r618/judge_r618.py', 'eval/rover/r619/judge_r619.py')
rep('WINS = ("w208", "w209", "w210")', 'WINS = ("w211", "w212", "w213")')
rep('verdict-r618.json', 'verdict-r619.json')
rep('prefix="r618-selftest-"', 'prefix="r619-selftest-"')
rep('"""R618 判据器**影子自检**', '"""R619 判据器**影子自检**')
rep('python3 eval/rover/r618/selftest_judge_r618.py', 'python3 eval/rover/r619/selftest_judge_r619.py', 1)

# ---- ② J0 键改名（检查项 + 判据描述） ----
rep('A_T_exec_source_all_candidates', 'A_T_exec_source_in_allowed_faces', 1)

# ---- ③ build() 三态注入 ----
rep('''                if state == "D_conservation" and dose == "exec1":
                    kw.update(action_candidates_executed=9)     # accepted=4, unmapped=1 ⇒ mapped=3 < 9 ⇒ 违例''',
    '''                if state == "D_conservation" and dose == "exec1":
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
                    kw.update(exec_source="candidates", action_candidates_executed=0)''')

# ---- ② A 态新增三检查 ----
rep('''        chk.append(("A_J1c", j1.get("J1c_arms_distinguishable") is True))''',
    '''        chk.append(("A_J1c", j1.get("J1c_arms_distinguishable") is True))
        chk.append(("A_J1d", j1.get("J1d_exec_face_forms_zeroed") is True))
        # NOT_EXERCISED：本轮合成 A 态无回退跑次 ⇒ 三态必须落到「未行使」且**不判红**（禁把未测读成通过）
        chk.append(("A_J1e_not_exercised", j1.get("J1e_fallback_three_state") == "NOT_EXERCISED"
                    and j1.get("J1e_red_only_on_empty") is True))
        chk.append(("A_J0_allowed_faces", j0.get("by_arm", {}).get("A_T_face_set") == ["candidates"]))''')

# ---- ④ main() 新增 F/G/H 三态块 ----
rep('''        print(json.dumps({"states": {"A_ok": {"rc": rcA}, "B_indistinguishable": {"rc": rcB},
                                     "C_vacuous": {"rc": rcC}, "D_conservation": {"rc": rcD},
                                     "E_cross_anchor": {"rc": rcE}},''',
    '''        # ---- F 回退行使且真干活（EXERCISED_OK） ----
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
                                     "H_d1_form": {"rc": rcH}},''')

io.open(DST, 'w', encoding='utf-8').write(s)
try:
    ast.parse(s)
except SyntaxError as e:
    raise SystemExit('SYNTAX_FAIL %s' % e)

chk = {'r618_left': s.count('r618'),
       'R617_pin_kept': s.count('25c97bef'),
       'w208_left': s.count('w208'),
       'new_states': s.count('F_fallback_ok') + s.count('G_fallback_empty') + s.count('H_d1_form'),
       'old_key_left': s.count('A_T_exec_source_all_candidates')}
print('REPS=%d' % n)
print('SELFTEST=' + str(chk))
if chk['r618_left'] or chk['w208_left'] or chk['old_key_left'] or not chk['R617_pin_kept']:
    raise SystemExit('SELFTEST_FAIL')
print('SELFTEST_DERIVE=OK -> ' + DST)
