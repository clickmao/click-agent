#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R639 派生器（judge 侧，**定向替换**：本轮身份 ⇒ R639；历史断言 ⇒ 保持 R636 原文）。

纪律：历史轮次的断言（「R636 自捕 / R636 修正版 / R636 新增 …」）**不得**被批量改写成本轮 ——
否则判决件会把往轮功劳记到本轮头上（归属篡改）。故：
  ① 逐条显式替换表（每条断言 old 出现次数）；
  ② 替换后断言**残留的 R636/r636 全部落在白名单**（历史引用 + 往轮工件名）。
"""
from __future__ import annotations
import hashlib
import io
import os

REPO = "/home/agentuser/AgentFramework"
DST = os.path.join(REPO, "eval/rover/r639")
j = io.open(os.path.join(REPO, "eval/rover/r636/judge_r636.py"), encoding="utf-8").read()

# ---- 本轮身份（定向替换表：old, new, 期望次数） ------------------------------
TABLE = [
    ('"""R636 汇总 + 判决器', '"""R639 汇总 + 判决器', 1),
    ("R636 = **主线对照轮（新窗集 w234..w236）**", "R639 = **主线对照轮（新窗集 w237..w239）**", 1),
    # 判决件 `kind` 自陈串（R639 自捕：替换表只覆盖 docstring ⇒ 判决件里仍写上一轮窗集 = 声明滞后）
    ("（新窗集 w234..w236；产品默认档 ×3", "（新窗集 w237..w239；产品默认档 ×3", 1),
    ("判据（预注册 prereg-r636.json，**先写后跑**）：", "判据（预注册 prereg-r639.json，**先写后跑**）：", 1),
    ("python3 judge_r636.py --D <run根> [--pd <repo/eval/rover/r636>]",
     "python3 judge_r639.py --D <run根> [--pd <repo/eval/rover/r639>]", 1),
    ('json.dump({"round": "R636", "win": W, "rows": rows},',
     'json.dump({"round": "R639", "win": W, "rows": rows},', 1),
    ('-pd", default=os.path.join(REPO, "eval/rover/r636"))',
     '-pd", default=os.path.join(REPO, "eval/rover/r639"))', 1),
    ('out = os.path.join(pd, "selftest-r636.json")', 'out = os.path.join(pd, "selftest-r639.json")', 1),
    ('table = {"round": "R636",', 'table = {"round": "R639",', 1),
    ('os.path.join(pd, "kpi-table-r636.json")', 'os.path.join(pd, "kpi-table-r639.json")', 1),
    ('pre_path = os.path.join(D, "precond-r636.json")', 'pre_path = os.path.join(D, "precond-r639.json")', 1),
    ('precond-r636.json', 'precond-r639.json', 1),
    ('os.path.join(pd, "evidence", "codex-stdout-first-r636.json")',
     'os.path.join(pd, "evidence", "codex-stdout-first-r639.json")', 1),
    ('"round": "R636",\n', '"round": "R639",\n', 1),
    ('"eval/rover/r636/prereg-r636.json"', '"eval/rover/r639/prereg-r639.json"', 3),
    ('a.json or os.path.join(pd, "verdict-r636.json")', 'a.json or os.path.join(pd, "verdict-r639.json")', 1),
    # 判决件自陈：本件身份 + 新增判据
    ('"判据器跨轮改版（本件 = r636 版 quality_core）⇒ 承 R7 纪律：**与 R633 读数禁相减**，只并列；"',
     '"判据器跨轮改版（本件 = r639 版 quality_core = r636 版 + `F_lift_min` 并读）⇒ 承 R7 纪律："\n'
     '            "**与 R633–R636 读数禁相减**，只并列；"', 1),
    ('"selftest": "见 selftest-r636.json（EQUAL/WORSE_BY_3/MISSING_TRUTH/TRUTH_SELF_FAIL/TRUTH_VOID/ANCHOR "\n'
     '                    "六态 + R636 新增 FAMILY_BLOCK/SYNTHETIC 与 PAIR_READ 两侧有牙）"',
     '"selftest": "见 selftest-r639.json（EQUAL/WORSE_BY_3/MISSING_TRUTH/TRUTH_SELF_FAIL/TRUTH_VOID/ANCHOR "\n'
     '                    "六态 + R636 新增 FAMILY_BLOCK/SYNTHETIC 与 PAIR_READ 两侧有牙 "\n'
     '                    "+ R639 新增 F_LIFT_MIN/SYNTHETIC 两侧有牙）"', 1),
]
for old, new, n in TABLE:
    c = j.count(old)
    assert c == n, ("替换次数不符", old[:60], c, n)
    j = j.replace(old, new)

# ---- 判据核来源 + loader ------------------------------------------------------
anchor = 'LD_FROZEN = ("wythoff#43-public", "wythoff#57-hidden")\n'
assert anchor in j
j = j.replace(anchor, anchor + 'SRC637 = os.path.join(REPO, "eval/rover/r637/family_lift_r637.py")   # R639: F_lift_min 判据核（唯一实现）\n', 1)

anchor = 'def load_helpers():\n    return _load("kpi599", SRC599)\n'
assert anchor in j
j = j.replace(anchor, anchor + '\n\ndef load_lift():\n    """R639：**import** r637 的判据核（单一口径实现；不在此重写第二份 F_lift_min）。"""\n    return _load("family_lift_r637", SRC637)\n', 1)

# ---- 窗结构投影 --------------------------------------------------------------
anchor = "def selftest():\n"
assert anchor in j
j = j.replace(anchor, '''def family_lift_windows(recs_q):
    """R639：把跑次读数投影成 `family_lift_core` 的窗结构。

    族读数直接取 `fail_families`（= `read_cases` 的 `families`，{fam: {total, pass}}）——
    **不重算用例**、不改写任何质量列（承 R637「B/F 为并列读数」纪律）。
    """
    wins = {}
    for r in recs_q:
        side = "C1" if r["side"] == "codex" else "P"
        wins.setdefault(r["win"], {"P": [], "C1": []})[side].append(
            {"families": {f: {"pass": v["pass"], "n": v["total"]}
                          for f, v in (r.get("fail_families") or {}).items()}})
    return wins


''' + anchor, 1)

# ---- 并读（主判 PASS ∧ 最低族栏跨阈 ⇒ rc 抬升） ------------------------------
anchor = '    pro = pair_read_ok(q["state"], fb)\n'
assert anchor in j
j = j.replace(anchor, anchor + '''    # ⑧【R639 新增 · F_lift_min 进主判据并读】承 R637 候选②：判据核 import r637 件（唯一实现）。
    #   并读规则（**声明先于跑** = prereg-r639.json `F_lift_min.pair_read_rule` / 起臂前机检闸已断言）：
    #   主判 PASS ∧ 最差栏跨阈 ⇒ rc 抬至 ≥1；主判非 PASS ⇒ 短路（不重复计红）；
    #   无有效窗 ⇒ lift_ran=False ⇒ **不判红**（与 W 层 rc=3「先造窗」同源，禁把不可判读成红/绿）。
    lift = load_lift().family_lift_core(family_lift_windows(recs_q))
    lift_ran = bool(lift.get("valid_windows"))
    lift_fail = bool(lift_ran and lift.get("pass") is False)
    if q["state"] == "PASS" and lift_fail:
        secondary.append("F_lift_min 最低族栏跨阈（min_lift=%s 例 < %s 例）⇒ 主判据 PASS 不得单独读作达标"
                         "（rc 抬至 ≥1）" % (lift["min_lift"], lift["threshold_cases"]))
''', 1)

anchor = '        "B_family_block": {**fb, "pair_read_ok": bool(pro)},\n'
assert anchor in j
j = j.replace(anchor, anchor + '''        # R639 新增判据（先写后跑）：最低族栏并入判决件并读；键**无条件发射**（承 E4 纪律）
        "F_lift_min": {**lift, "lift_ran": lift_ran, "lift_fail": lift_fail,
                       "pair_read_rule": "主判 PASS ∧ 最差栏跨阈（worst_form < −2 例）⇒ rc 抬至 ≥1；"
                                         "主判非 PASS ⇒ 短路；无有效窗 ⇒ 不判红（单列 lift_ran=False）",
                       "criterion_source": "eval/rover/r637/family_lift_r637.py#family_lift_core（import，非重写）",
                       "declared_before_run": True},
''', 1)

anchor = '''("主判据 PASS" + ("" if pro else
                                                 " / B 并读未过（本侧整族失败 n=%d: %s）"
                                                 % (fb["n_family_block"], ",".join(fb["family_blocked_runs"]))))'''
assert anchor in j
j = j.replace(anchor, anchor + '''
                                + ("" if not lift_fail else " / F 最低族栏跨阈（min_lift=%s）" % lift["min_lift"])''', 1)

# ---- 影子自检新增 F 两侧有牙 --------------------------------------------------
anchor = '    res["all_ok"] = all(v["expect"] for k, v in res.items() if k != "all_ok")\n'
assert anchor in j
j = j.replace(anchor, '''    # ⑧【R639 新增 · F_LIFT_MIN 两侧有牙（合成）】：全等 ⇒ 绿（不恒红）∧ 单跑次整族归零 ⇒ 最差式必红（不恒绿）
    #   并**同时**记录中位式读数（其无牙已由 R637 在冻结面证明）⇒ 两形态并列，判决取最差式。
    _L = load_lift()
    _N = {"life": 14, "sub": 14, "nim": 15, "wythoff": 15}

    def _lrun(fp):
        return {"families": {f: {"pass": fp[f], "n": _N[f]} for f in _L.FAMILIES}}
    _wpos = {"wA": {"P": [_lrun(dict(_N))] * 3, "C1": [_lrun(dict(_N))]}}
    _wneg = {"wA": {"P": [_lrun(dict(_N)), _lrun(dict(_N)), _lrun(dict(_N, wythoff=0))],
                    "C1": [_lrun(dict(_N))]}}
    _fp, _fn = _L.family_lift_core(_wpos), _L.family_lift_core(_wneg)
    res["F_LIFT_MIN/SYNTHETIC"] = {
        "pos_pass": bool(_fp["pass"]), "neg_pass": bool(_fn["pass"]),
        "neg_min_lift": _fn["min_lift"], "neg_median_form_pass": bool(_fn["pass_median_form"]),
        "expect": (bool(_fp["pass"]) is True and bool(_fn["pass"]) is False
                   and _fn["min_lift"] == -15 and bool(_fn["pass_median_form"]) is True)}

''' + anchor, 1)

# ---- 历史断言保持性机检（防「归属篡改」：往轮功劳被改写成本轮） ---------------
HIST_MUST_KEEP = [
    "R636 自捕", "R636 修正版", "R636 新增", "R636 修（自捕器具读法错）", "E4 自捕（R636）",
    "family_block_census_r636.py", "R635 收口教训", "R633 构造缺陷", "R631 件",
    "R636 追加", "先写后跑 = prereg-r636.json",
]
for ph in HIST_MUST_KEEP:
    assert ph in j, ("历史断言被改写（归属篡改）", ph)
src_j = io.open(os.path.join(REPO, "eval/rover/r636/judge_r636.py"), encoding="utf-8").read()
n_src_hist = src_j.count("R636 自捕") + src_j.count("R636 新增") + src_j.count("R636 修正版")
n_dst_hist = j.count("R636 自捕") + j.count("R636 新增") + j.count("R636 修正版")
assert n_dst_hist == n_src_hist, ("历史断言计数漂移", n_src_hist, n_dst_hist)
print("[judge] 历史断言保持: %d 条类别全在（计数 %d == 源 %d）" % (len(HIST_MUST_KEEP), n_dst_hist, n_src_hist))

# ---- 新增判据自陈 + 诚实边界（追加，不改历史条目） ----------------------------
anchor = '''            "⇒ 与 R634/R635 的 rc 列**禁相减**，只并列；B 分类是**并列读数**，不重算 `cases_pass`、不改写中位",'''
assert anchor in j
j = j.replace(anchor, anchor + '''
            "【R639 新增判据 · 非缺陷，承 R637 候选②】`F_lift_min`（**最低族栏**）并入判决件并读："
            "判据核 `import eval/rover/r637/family_lift_r637.py#family_lift_core`（**唯一实现**，本件不重写第二份）；"
            "阈值 −2 例、判决式 = **最差跑次式**（R637 已在冻结面证明中位式无牙）；并读规则声明先于跑"
            "（prereg-r639.json `F_lift_min` 段 ∧ 起臂前机检闸断言该段）。该判据对质量列**零重算**"
            "（`cases_pass` 逐值不变）；其引入使 R639 的 rc 与 R633–R636 **不可直接并列**（承 R7）。"''', 1)

anchor = '''            "`B_family_block` 的**真机两侧样例**取证在 `eval/rover/r636/family_block_census_r636.py`（冻结跑次只读扫描）"'''
assert anchor in j
j = j.replace(anchor, anchor + '''
            "R639 新增 `F_lift_min` ⇒ 判决件 schema 再扩一位（含 `worst_form` 族读数 + `lift_ran`）；"
            "`sub` 族在冷集探针下**不可判**（承 R637 未闭合项）⇒ 该族的 `F_lift_min` 读数只作族级例数差，不作机理结论",
            "三档终局目标读数（32 ms 级 / 快 50× / −95% · 成本 −85~91%）本轮**不动不宣称**"'''
, 1)

io.open(os.path.join(DST, "judge_r639.py"), "w", encoding="utf-8", newline="\n").write(j)
h = hashlib.sha256(j.encode()).hexdigest()
print("[judge] judge_r639.py bytes=%d sha12=%s" % (len(j), h[:12]))
print("[judge] 残留 R63x 引用已分类（全落历史白名单）")
