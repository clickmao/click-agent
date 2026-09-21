#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R619 判据器派生器（**幂等 · 字节级 · 锚点必须命中**）。

派生自 eval/rover/r618/judge_r618.py。**声明的差异**（逐条）：
  ① 全局命名空间 R618->R619 / r618->r619（跨轮锚 R617_T_PIN 与 r617 路径**不动**）。
  ② EXEC_FIELDS 增第 5 个受闸字段 `exec_fallback`（对照档必须 5 字段全缺席）。
  ③ J0 判据 A：由「T 档 exec_source 全 == candidates」改为「全 ∈ {candidates, plan_fallback}」
     （本轮治疗档**允许**回退档出现）+ 新增面集合读数 `A_T_face_set`。
  ④ J1 新增两项：J1d = D1 形态清零（candidates ∧ executed==0 跑次必须为 0）；
     J1e = 回退**三态**（NOT_EXERCISED / EXERCISED_OK / EXERCISED_EMPTY，仅第三态判红）。
  ⑤ J1 逐跑次行增 `fallback` 列；by_arm 增三个计数器。
  ⑥ verdict 的 J1 段增 J1d/J1e 与更新后的 need；label 文本同步。
  ⑦ honest_bounds 增「回退三态未行使」与「起手闸首试 fail-closed」两行如实标注。
其余判据（J2b/J2/J3v1/v2/J4/J5/W_floor/LD/C1-v3/铁律11 前置器）**逐字继承**，不改阈值。
"""
import ast
import io
import sys

SRC = 'eval/rover/r618/judge_r618.py'
DST = 'eval/rover/r619/judge_r619.py'

s = io.open(SRC, encoding='utf-8').read()
n = 0


def rep(old, new, cnt=1):
    """锚点必须恰好命中 cnt 次，否则 fail-closed（禁静默跳过）。"""
    global s, n
    got = s.count(old)
    if got != cnt:
        raise SystemExit('ANCHOR_MISS count=%d expect=%d :: %r' % (got, cnt, old[:90]))
    s = s.replace(old, new)
    n += 1


# ---- ③ J0 判据 A：允许回退档 + 面集合读数（先于全局改名，锚点含旧名）----
rep('''    j0["A_T_exec_source_all_candidates"] = bool(
        j0["T"]["exec_source"] and all(x == "candidates" for x in j0["T"]["exec_source"]))''',
    '''    j0["A_T_exec_source_in_allowed_faces"] = bool(
        j0["T"]["exec_source"] and all(x in ("candidates", "plan_fallback") for x in j0["T"]["exec_source"]))
    j0["A_T_face_set"] = sorted(set(x for x in j0["T"]["exec_source"] if x))   # R619: 面集合应 ⊆ {candidates, plan_fallback}''')

# ---- ① 全局改名（跨轮锚 R617_T_PIN / r617 路径不动）----
# 步骤③ 已换掉赋值行那一处 ⇒ 余下恰 2 处（j0_pass 行 / instrument_defects 的 json.dumps 键表）
rep('A_T_exec_source_all_candidates', 'A_T_exec_source_in_allowed_faces', 2)
rep('"round": "R618"', '"round": "R619"', 3)
rep('eval/rover/r618/prereg-r618.json', 'eval/rover/r619/prereg-r619.json', 2)
rep('verdict-r618.json', 'verdict-r619.json', 2)
rep('precond-r618.json', 'precond-r619.json', 2)
# 剩余 6 处轮次专属残留（逐条定名，禁泛化替换 —— 泛化会误改跨轮锚/历史路径）
rep('prereg-r618.json', 'prereg-r619.json', 1)                     # 头部 docstring
rep('judge_r618.py', 'judge_r619.py', 1)                           # 用法行
rep('<repo/eval/rover/r618>', '<repo/eval/rover/r619>', 1)         # 用法行
rep('os.path.join(REPO, "eval/rover/r618")', 'os.path.join(REPO, "eval/rover/r619")', 1)   # --pd 缺省
rep('j3mod.collect("r618"', 'j3mod.collect("r619"', 1)             # J3v2 取数的轮次命名空间
rep('kpi-table-r618.json', 'kpi-table-r619.json', 1)               # KPI 表落盘名

# ---- ② EXEC_FIELDS 增第 5 字段 ----
rep('''    EXEC_FIELDS = ("exec_source", "action_candidates_executed", "action_candidates_unmapped",
                   "action_candidates_expect_inherited")''',
    '''    EXEC_FIELDS = ("exec_source", "action_candidates_executed", "action_candidates_unmapped",
                   "action_candidates_expect_inherited", "exec_fallback")   # R619 增: 回退原因码（仅回退时出现）''')

# ---- ②b 读取契约 TR_FIELDS 必须同步并入新键（影子自检 F 态当场抓到：只进 EXEC_FIELDS 不进 TR_FIELDS
#          ⇒ 白名单外键静默读空 ⇒ reason_set=[] ⇒ 假红；承 R617/R618「读取契约缺键」同族缺陷）----
rep('''             # R618（本轮新增键, 承 R617 自捕器具缺陷教训: 读取契约缺键 ⇒ 白名单外键静默读空 ⇒ 假红）
             "exec_source", "action_candidates_executed", "action_candidates_unmapped",
             "action_candidates_expect_inherited",''',
    '''             # R618（本轮新增键, 承 R617 自捕器具缺陷教训: 读取契约缺键 ⇒ 白名单外键静默读空 ⇒ 假红）
             "exec_source", "action_candidates_executed", "action_candidates_unmapped",
             "action_candidates_expect_inherited",
             # R619（本轮新增键 `exec_fallback`；**影子自检 F 态当场抓到**「只进 EXEC_FIELDS、不进 TR_FIELDS」
             #   ⇒ 白名单外键静默读空 ⇒ fallback_reason_set=[] ⇒ 假红。新增字段必须**两处同时**并入）
             "exec_fallback",''')

# ---- ⑤ 逐跑次行增 fallback 列 ----
rep('''            rows.append({"win": r["win"], "rep": r["rep"], "src": tr.get("exec_source"),''',
    '''            rows.append({"win": r["win"], "rep": r["rep"], "src": tr.get("exec_source"),
                         "fallback": tr.get("exec_fallback"),''')

# ---- ⑤ by_arm 增三计数器 ----
rep('''                   "runs_executed_positive": sum(1 for x in rows if (x["executed"] or 0) > 0),''',
    '''                   "runs_executed_positive": sum(1 for x in rows if (x["executed"] or 0) > 0),
                   "runs_plan_fallback": sum(1 for x in rows if x["src"] == "plan_fallback"),
                   "runs_candidates_executed_zero": sum(
                       1 for x in rows if x["src"] == "candidates" and (x["executed"] or 0) == 0),
                   "runs_fallback_executed_positive": sum(
                       1 for x in rows if x["src"] == "plan_fallback" and (x["executed"] or 0) > 0),
                   "fallback_reason_set": sorted(set(x["fallback"] for x in rows if x["fallback"])),''')

# ---- ④ J1d/J1e 判据 ----
rep('''    j1a_pass = bool(j1["T"]["runs_exec_source_candidates"] >= 1 and j1["T"]["runs_executed_positive"] >= 1)
    j1b_pass = bool(not j1_vacuous and j1["T"]["conservation_violations"] == 0)
    j1c_pass = bool(j0.get("B_C_new_fields_absent"))
    j1_pass = bool(j1a_pass and j1b_pass and j1c_pass)''',
    '''    j1a_pass = bool(j1["T"]["runs_exec_source_candidates"] >= 1 and j1["T"]["runs_executed_positive"] >= 1)
    j1b_pass = bool(not j1_vacuous and j1["T"]["conservation_violations"] == 0)
    j1c_pass = bool(j0.get("B_C_new_fields_absent"))
    # R619 · J1d/J1e（第三刀 = 空执行面回退，RF0004.2 M3）
    #   J1d = **D1 形态清零**：不得存在 exec_source=candidates ∧ executed==0 的跑次
    #         （R618 实测该形态 = 「映射出空执行面 ⇒ 静默零动作 ⇒ 空转整窗」）
    #   J1e = 回退**三态**：NOT_EXERCISED（无跑次命中回退 ⇒ 如实记未测；**禁读作 PASS**）
    #         / EXERCISED_OK（命中且 executed>0 ⇒ 回退真把活干起来） / EXERCISED_EMPTY（命中而 executed==0 ⇒ FAIL）
    #   纪律：三态里只有第三态判红；第一态不得升级为通过（「没测到」≠「测过通过」）。
    j1d_pass = bool(j1["T"]["runs_candidates_executed_zero"] == 0)
    _fb = int(j1["T"]["runs_plan_fallback"])
    if _fb == 0:
        j1e_state = "NOT_EXERCISED"
    elif int(j1["T"]["runs_fallback_executed_positive"]) == _fb:
        j1e_state = "EXERCISED_OK"
    else:
        j1e_state = "EXERCISED_EMPTY"
    j1e_pass = bool(j1e_state != "EXERCISED_EMPTY")
    j1_pass = bool(j1a_pass and j1b_pass and j1c_pass and j1d_pass and j1e_pass)''')

# ---- ⑦ j1_note 补回退读数 ----
rep('''                  j1["T"]["unmapped_total"], j1["T"]["inherited_total"]))''',
    '''                  j1["T"]["unmapped_total"], j1["T"]["inherited_total"]))
    j1_note += ("; R619 回退面: face=%s, candidates∧executed==0 %d, plan_fallback %d, "
                "回退且 executed>0 %d, 三态 %s, 原因码 %s"
                % (j0["A_T_face_set"], j1["T"]["runs_candidates_executed_zero"],
                   j1["T"]["runs_plan_fallback"], j1["T"]["runs_fallback_executed_positive"],
                   j1e_state, j1["T"]["fallback_reason_set"]))''')

# ---- ⑥ verdict J1 段 ----
rep('''        "J1_exec_face_consumed": {"pass": bool(j1_pass), "J1a_exec_face_driven": j1a_pass,
                                  "J1b_conservation_non_vacuous": j1b_pass, "J1c_arms_distinguishable": j1c_pass,
                                  "need": "T 有 exec_source=candidates ∧ 有跑次 executed>0 ∧ 逐跑次 unmapped<=accepted ∧ "
                                          "executed<=accepted-unmapped ∧ inherited<=accepted-unmapped（违例 0）∧ 非真空",''',
    '''        "J1_exec_face_consumed": {"pass": bool(j1_pass), "J1a_exec_face_driven": j1a_pass,
                                  "J1b_conservation_non_vacuous": j1b_pass, "J1c_arms_distinguishable": j1c_pass,
                                  "J1d_exec_face_forms_zeroed": j1d_pass,
                                  "J1e_fallback_three_state": j1e_state, "J1e_red_only_on_empty": j1e_pass,
                                  "need": "T 有 exec_source=candidates ∧ 有跑次 executed>0 ∧ 逐跑次 unmapped<=accepted ∧ "
                                          "executed<=accepted-unmapped ∧ inherited<=accepted-unmapped（违例 0）∧ 非真空 ∧ "
                                          "无『candidates ∧ executed==0』跑次（J1d）∧ 回退若行使则 executed>0（J1e，"
                                          "未行使记 NOT_EXERCISED 不判 PASS 不判红）",''')

# ---- ⑥ label 文本 ----
rep('"机制达标（J0∧J1a∧J1b∧J1c∧J2b：臂轴生效 + 执行面被采纳集驱动 + 条目守恒 + 逐条裁定守恒）"',
    '"机制达标（J0∧J1a∧J1b∧J1c∧J1d∧J1e∧J2b：臂轴生效 + 执行面被采纳集驱动 + 条目守恒 + '
    '空执行面形态清零 + 回退三态不红 + 逐条裁定守恒）"')

# ---- ⑦ honest_bounds 追加 ----
rep('''            "LD 两例只作诊断列，不作收益/缺陷证据（主判据不剔除以保跨轮可比）",''',
    '''            "LD 两例只作诊断列，不作收益/缺陷证据（主判据不剔除以保跨轮可比）",
            "R619 第三刀 = 空执行面**回退**：回退判据为**三态**；若本窗集回退零行使 ⇒ 记 NOT_EXERCISED "
            "（如实未测），禁读作通过，且不得据此宣称回退机制有效",
            "起手闸首试 RUN_EXIT=2（ceiling 2687 - GATE 2650 = 37MB < 60MB 下限，fail-closed 拒绝开窗，"
            "零臂起跑 ⇒ 该次无任何测量读数、不入对账）；清场后 ceiling 2903 重跑首跑",''')

# ---- 标题/kind ----
rep('"kind": "M3 第二刀（RF0004.2 R617–R612 首轮）：动作候选进 R1 契约（前缀**只加厚**）+ 本地机械裁选器 + 三计数打点；第十三窗集 w199..w201"',
    '"kind": "M3 第三刀（RF0004.2）：空执行面**回退**（采纳集映射出空执行面 ∧ plan 非空 ⇒ 执行面回退读 plan + 原因码入台账）；窗集 w211..w213（与历史 w184..w210 不相交）"')

io.open(DST, 'w', encoding='utf-8').write(s)

# ---- 自检：语法 + 关键 token 落盘复核（不采信写入回执）----
try:
    ast.parse(s)
except SyntaxError as e:
    raise SystemExit('SYNTAX_FAIL %s' % e)

chk = {
    'R619_round': s.count('"round": "R619"'),
    'EXEC_FIELDS_5': s.count('"exec_fallback")   # R619'),
    'allowed_faces': s.count('A_T_exec_source_in_allowed_faces'),
    'j1d': s.count('j1d_pass'),
    'j1e_state': s.count('j1e_state'),
    'fallback_col': s.count('"fallback": tr.get("exec_fallback")'),
    'old_name_left': s.count('A_T_exec_source_all_candidates'),
    'r618_left': s.count('r618'),
    'R617_pin_kept': s.count('R617_T_PIN'),
}
print('REPS=%d' % n)
print('SELFTEST=' + str(chk))
if chk['old_name_left'] or chk['r618_left'] or not chk['R617_pin_kept']:
    raise SystemExit('SELFTEST_FAIL')
print('JUDGE_DERIVE=OK -> ' + DST)
