#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R618 判据器补丁器（一次性）: 把 r617 判据的 J0/J1 两块替换为本轮单变量的判据面。
每步断言 ⇒ 失败即停（禁静默半改）。"""
import io

P = "/home/agentuser/AgentFramework/eval/rover/r618/judge_r618.py"
s = io.open(P, encoding="utf-8").read()


def cut(text, a, b, new):
    i = text.index(a)
    j = text.index(b)
    assert i < j, (a, b)
    return text[:i] + new + text[j:]


# ---------- A. 头部说明 ----------
OLD_DOC = s[s.index('"""R617 汇总'):s.index('"""\nfrom __future__') + 4]
NEW_DOC = '''"""R618 汇总 + 判决器（派生自 r617/judge_r617.py：**import** kpi_r599.py helpers 与 r604 的 J3v2 公式模块，
禁重写第二份）。

R618 = RF0004.2 · M3 **第二刀 = 执行面接线**（第十四窗集 w208..w210）。
被测件 = 本轮 AOT 重发布件（src/ 有改动 ⇒ 与 R585–R617 冻结件轮**禁相减**，只并列）；
题集 = r617 冻结件逐字节复制件（sha e0c667c2…）⇒ 同输入面不变。

单变量 = `AGENTFRAMEWORK_R1_ACTION_EXEC`（产品缺省 **off**；r1gen 契约与常量前缀**零改动**）：
  T 档 显式 `=1` ⇒ 执行面 = 采纳候选映射出的节点（窄腰 write_file/run）；
  C 档 `unset`   ⇒ 产品缺省 = 旧行为（执行面读 `plan`，台账四字段缺席 ⇒ 逐字节同旧）；
  C1 = codex 外部真值（同题面/同夹具/同窗）。

本轮改写块（预注册 prereg-r618.json，**先写后跑**）：
  · J0 = 臂轴生效面（新轴两档**可区分**：T 出现 exec_source=candidates ∧ C 四字段全缺席 ∧ 两臂前缀同源）；
  · J1 = **执行面消费面**（主判据）：T 有 exec_source=candidates ∧ 有跑次 executed>0 ∧ 逐跑次**条目守恒**
         （unmapped<=accepted ∧ executed<=accepted-unmapped ∧ inherited<=accepted-unmapped，起臂前 v2 修订）；
         「四字段齐备跑次 = 0」⇒ 真空 ⇒ fail-closed 不可判（承 R614 教训）。
  J2/J2b/J3/J4/J5/W_floor/LD 逐字继承自 R617（并列、禁相减）。

rc 语义（分层）：0 已算 / 2 器具缺陷（含负控无牙 / 臂轴未生效） / 3 输入缺失。
用法: python3 judge_r618.py --D <run根> [--pd <repo/eval/rover/r618>] [--win wXXX]
"""'''
s = s.replace(OLD_DOC, NEW_DOC, 1)

# ---------- B. J0 块 ----------
J0_NEW = '''    # --- J0 臂轴生效面（fail-closed 器具闸）：新轴 AGENTFRAMEWORK_R1_ACTION_EXEC 两档必须**可区分** ------
    #   纪律（RF0005 §1.2「轴关 = 旧行为逐位等价」+「臂未净 ⇒ 闸假阴性」）：轴关档**不得出现**新字段
    #   （产品缺省 off ⇒ 台账逐字节同旧），轴开档必须现 `exec_source="candidates"`；两档若不可区分，
    #   J1 的任何差异都**不是**被测变量的效果 ⇒ 先判臂，再判被测。
    R617_T_PIN = "25c97befa2124549b52991c0338324ceee7f7702a6348641ed917d3b7b658052"
    EXEC_FIELDS = ("exec_source", "action_candidates_executed", "action_candidates_unmapped",
                   "action_candidates_expect_inherited")
    j0 = {}
    MISS = "\\u2205"  # 缺测哨兵（承 R617 v1 器具缺陷修复：None 与 str 混合 ⇒ sorted() TypeError 崩整轮汇总）
    for arm in arms:
        rs = of(arm)
        j0[arm] = {"runs": len(rs),
                   "sha_set": sorted({r["tr"].get("prefix_sha256") or MISS for r in rs}),
                   "missing": sum(1 for r in rs if not r["tr"].get("prefix_sha256")),
                   "exec_source": [r["tr"].get("exec_source") for r in rs],
                   "new_fields_present": sum(1 for r in rs
                                             if any(r["tr"].get(k) is not None for k in EXEC_FIELDS))}

    j0["A_T_exec_source_all_candidates"] = bool(
        j0["T"]["exec_source"] and all(x == "candidates" for x in j0["T"]["exec_source"]))
    j0["B_C_new_fields_absent"] = bool(j0["C"]["runs"] > 0 and j0["C"]["new_fields_present"] == 0)
    sT = set(x for x in j0["T"]["sha_set"] if x != MISS)
    sC = set(x for x in j0["C"]["sha_set"] if x != MISS)
    j0["C_prefix_shared"] = bool(sT and sT == sC)   # 轴**零前缀改动**（两臂同源前缀）
    j0["D_cross_round_pin"] = bool(sT and sT == {R617_T_PIN})   # 跨轮锚: 与 R617 T 档前缀逐位同
    j0["D_note"] = ("跨轮前缀锚（R617 契约/前缀零改动之宣称面）⇒ 属**宣称面**不入 j0_pass，"
                    "不成立时记 claims_violated 并在报告订正该宣称（不影响同轮可归因性）")
    j0["E_telemetry_coverage"] = bool(j0["T"]["missing"] < j0["T"]["runs"]
                                      and j0["C"]["missing"] < j0["C"]["runs"])
    j0["instrument_gap"] = sorted([(r["arm"], r["win"], r["rep"]) for r in recs
                                   if r["arm"] in ("T", "C") and not r["tr"].get("prefix_sha256")])
    j0["E_C1_out_of_scope"] = True  # codex 真值臂无本仓前缀遥测 ⇒ 不入本判据（只留档）
    j0_pass = bool(j0["A_T_exec_source_all_candidates"] and j0["B_C_new_fields_absent"]
                   and j0["C_prefix_shared"] and j0["E_telemetry_coverage"])
    if not j0["D_cross_round_pin"]:
        claims_violated.append("跨轮前缀锚不成立（T 档 prefix_sha256 != R617 pin）⇒ 订正「前缀零改动」宣称；"
                               "同轮两臂可比性不受影响（C_prefix_shared=%s）" % j0["C_prefix_shared"])
    if not j0_pass:
        defects.append("J0 臂轴未生效（两档不可区分 / 前缀不同源）: %s"
                       % json.dumps({k: j0[k] for k in ("A_T_exec_source_all_candidates",
                                                        "B_C_new_fields_absent", "C_prefix_shared",
                                                        "E_telemetry_coverage")}, ensure_ascii=False))

'''
s = cut(s, "    # --- J0 臂轴生效面", "    # --- J1 机制面", J0_NEW)

# ---------- C. J1 块 ----------
J1_NEW = '''    # --- J1 执行面消费面（本轮**主判据** = 预注册 J1_exec_face_consumed）-------------------
    #   动因: 第一刀（R610）只落「声明/采纳/拒绝」三计数 ⇒ accepted **无消费者**
    #        （R617 实测声明到岸 9/9 而执行面仍读 plan）。本轮判据三件（缺一不可）:
    #     ① 治疗档 exec_source=candidates ∧ 有跑次 executed>0（执行面**真被采纳集驱动**）
    #     ② 逐跑次**条目守恒**（承「条目总数守恒」纪律: 不变量只保「没弄丢」, 不证明改对）
    #     ③ 两臂可区分（C 档四字段全缺席, 见 J0.B）
    #   守恒式（**起臂前** v2 修订, 见 prereg revision 行）:
    #     unmapped <= accepted  ∧  executed <= accepted - unmapped  ∧  inherited <= accepted - unmapped
    #   为何不是等式: 计划执行器可在任一步**早退**（rc=5 / rc=8 分支）⇒ executed < mapped 属合法形态,
    #     写成等式会把合法早退记成器具缺陷（R-EXP1Q7 同族: 判据必须绑真实行为）。
    j1 = {}
    for arm in arms:
        rs = of(arm)
        rows = []
        for r in rs:
            tr = r["tr"]
            acc = tr.get("action_candidates_accepted")
            unm = tr.get("action_candidates_unmapped")
            exe = tr.get("action_candidates_executed")
            inh = tr.get("action_candidates_expect_inherited")
            cons = None
            if None not in (acc, unm, exe, inh):
                mapped = (acc or 0) - (unm or 0)
                cons = bool(mapped >= 0 and (exe or 0) <= mapped and (inh or 0) <= mapped)
            rows.append({"win": r["win"], "rep": r["rep"], "src": tr.get("exec_source"),
                         "declared": tr.get("action_candidates_declared"), "accepted": acc,
                         "unmapped": unm, "executed": exe, "inherited": inh,
                         "steps_executed": tr.get("steps_executed"),
                         "plan_steps_total": tr.get("plan_steps_total"), "conserved": cons})
        j1[arm] = {"runs": len(rs),
                   "runs_exec_source_candidates": sum(1 for x in rows if x["src"] == "candidates"),
                   "runs_executed_positive": sum(1 for x in rows if (x["executed"] or 0) > 0),
                   "runs_four_fields": sum(1 for x in rows if x["conserved"] is not None),
                   "runs_conserved": sum(1 for x in rows if x["conserved"] is True),
                   "conservation_violations": sum(1 for x in rows if x["conserved"] is False),
                   "unmapped_total": sum((x["unmapped"] or 0) for x in rows),
                   "inherited_total": sum((x["inherited"] or 0) for x in rows),
                   "per_run": rows}
    # 非真空闸（承 R614 v2: 守恒式在字段缺失时真空成立 ⇒ 不可判，禁读作通过）
    j1_vacuous = bool(j1["T"]["runs_four_fields"] == 0)
    j1a_pass = bool(j1["T"]["runs_exec_source_candidates"] >= 1 and j1["T"]["runs_executed_positive"] >= 1)
    j1b_pass = bool(not j1_vacuous and j1["T"]["conservation_violations"] == 0)
    j1c_pass = bool(j0.get("B_C_new_fields_absent"))
    j1_pass = bool(j1a_pass and j1b_pass and j1c_pass)
    j1_reason = ("VACUOUS：T 档 0 个四字段齐备跑次 ⇒ 守恒式真空成立、**不可判**（禁读作通过）"
                 if j1_vacuous else None)
    j1_note = ("T: exec_source=candidates %d/%d, executed>0 %d/%d, 守恒 %d/%d (违例 %d, 四字段齐备 %d); "
               "unmapped 合计 %d, 自述期望继承合计 %d"
               % (j1["T"]["runs_exec_source_candidates"], j1["T"]["runs"],
                  j1["T"]["runs_executed_positive"], j1["T"]["runs"],
                  j1["T"]["runs_conserved"], j1["T"]["runs"],
                  j1["T"]["conservation_violations"], j1["T"]["runs_four_fields"],
                  j1["T"]["unmapped_total"], j1["T"]["inherited_total"]))
    # 执行面**与 plan 面是否真的不同**（诊断列, 不作判据: 同数不同源不构成失败）
    j1["exec_vs_plan_diag"] = {arm: [{"win": x["win"], "rep": x["rep"],
                                      "executed": x["steps_executed"], "plan_steps": x["plan_steps_total"],
                                      "exec_face_steps": x["executed"]}
                                     for x in j1[arm]["per_run"]] for arm in ("T", "C")}
    j1_render_defects = [(r["arm"], r["win"], r["rep"]) for r in recs
                         if r["arm"] != "C1" and r["tr"].get("action_candidates_present") == 0]
    if j1_render_defects:
        defects.append("J1 present 字段出现 0 值（渲染漂移，应有则恒 1）: %s" % j1_render_defects[:4])
    if j1_vacuous:
        defects.append("J1 真空绿闸: T 档四字段齐备跑次 = 0 ⇒ 守恒式不可判（fail-closed）")

'''
s = cut(s, "    # --- J1 机制面", "    # --- J2b 裁选面", J1_NEW)

# ---------- D. 轮号 / 落盘件 / 前表指针 ----------
reps = [
    ('ap.add_argument("--pd", default=os.path.join(REPO, "eval/rover/r617"))',
     'ap.add_argument("--pd", default=os.path.join(REPO, "eval/rover/r618"))'),
    ('ap.add_argument("--json", default=None, help="判决件输出路径（默认 <pd>/verdict-r617.json）")',
     'ap.add_argument("--json", default=None, help="判决件输出路径（默认 <pd>/verdict-r618.json）")'),
    ('json.dump({"round": "R617", "win": W, "rows": rows},',
     'json.dump({"round": "R618", "win": W, "rows": rows},'),
    ('json.dump(table, io.open(os.path.join(pd, "kpi-table-r617.json"), "w", encoding="utf-8"),',
     'json.dump(table, io.open(os.path.join(pd, "kpi-table-r618.json"), "w", encoding="utf-8"),'),
    ('v2recs, v2meta = j3mod.collect("r617", mod)', 'v2recs, v2meta = j3mod.collect("r618", mod)'),
    ('PREV_TABLE = os.environ.get("R617_J5_PREV", os.path.join(REPO, "eval/rover/r615/kpi-table-r615.json"))',
     'PREV_TABLE = os.environ.get("R618_J5_PREV", os.path.join(REPO, "eval/rover/r617/kpi-table-r617.json"))'),
    ('    table = {\n        "round": "R617",', '    table = {\n        "round": "R618",'),
    ('        "round": "R617",\n        "kind": "M3 第一刀', '        "round": "R618",\n        "kind": "M3 第二刀'),
    ('out_path = a.json or os.path.join(pd, "verdict-r617.json")',
     'out_path = a.json or os.path.join(pd, "verdict-r618.json")'),
    ('"driver_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12]},',
     '"driver_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12],\n'
     '                              "prereg": os.path.join(REPO, "eval/rover/r618/prereg-r618.json"),\n'
     '                              "prereg_sha256": hashlib.sha256(io.open(os.path.join(\n'
     '                                  REPO, "eval/rover/r618/prereg-r618.json"), "rb").read()).hexdigest()},'),
]
for a, b in reps:
    assert a in s, a[:70]
    s = s.replace(a, b, 1)

# ---------- E. claims_violated 容器 ----------
s = s.replace("    defects = []\n", "    defects = []\n    claims_violated = []\n", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("patched OK  bytes=%d" % len(s))
