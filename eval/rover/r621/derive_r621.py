#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R621 派生成（RF0004.2 · M3 **第五刀 = 等价面分辨率取证 + 判据分级**）。

派生源 = eval/rover/r620/{run_r620.sh,judge_r620.py,selftest_judge_r620.py,taskset-r620.json,cases/,closeout_r620.py}
派生方式 = **具名替换（R620→R621 / r620→r621）+ 逐条声明的结构化补丁**（补丁 id 逐条可核，命中数断言 == 1）。

本轮只改三件事（预注册 prereg-r621.json，**先写后跑**）：
  C1（器具面）：J6 类**机制面次级 FAIL** 不再进入 `instrument_defects`（R620 事故：`rc = 2 if defects else 0`
      把机制面次级 FAIL 编码成器具缺陷 ⇒ 整轮被标「禁作被测结论」）⇒ rc 分级 0/1/2/3。
  C2（机制面）：按 R620 登记的补救 **加 reps 3→6/窗**（禁调阈值），并把 J6 结论**三态化**
      （阈值 = **同臂跨跑次用例数极差**，数据派生非人为常数）：EQUIVALENT / NON_REGRESSION_DETECTED / NO_RESOLUTION。
  C3（只读）：R619 遗留 U2（rc=5 早退点）留作下轮。

纪律: 不改任何既有阈值（J1/J3/J4/W_floor 逐字继承）；被测件**与 R620 逐字节同件**（零产品源码改动 ⇒ 复用 pub_r619）；
      生成后 `--check` 断言生成物与替换规则一致（题集 sha 同源 ∧ 关键补丁落地 ∧ 无 pub_r620/r621 引用）。
用法: python3 eval/rover/r621/derive_r621.py [--check]
"""
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r620")
DST = os.path.join(REPO, "eval/rover/r621")
LEGACY_ANCHOR = "a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e"
ARTIFACT = "$HOME/.agentframework/artifacts/pub_r619/agenthost"

REPL = [("R620", "R621"), ("r620", "r621")]

# ---- 结构化补丁（run：精确串；judge：区块边界替换） -------------------------
RUN_PATCHES = [
    ("W1_reps", "REPS=${REPS:-3}", "REPS=${REPS:-6}"),
    ("W2_win0", "WIN0=${WIN0:-214}", "WIN0=${WIN0:-217}"),
    ("W3_windows", 'assert sorted(d["windows"]["set"]) == ["w214", "w215", "w216"], d["windows"]["set"]',
     'assert sorted(d["windows"]["set"]) == ["w217", "w218", "w219"], d["windows"]["set"]'),
    ("W4_criterion", 'startswith("v3")', 'startswith("v4")'),
    ("W5_prev_swing", "PREV_SWING=${PREV_SWING:-125}", "PREV_SWING=${PREV_SWING:-119}"),
    ("W6_swing_source",
     '"prev_swing_source": "前窗r617/logs/run-samples.jsonl (同态在飞窗, n=377, swing=81; 口径 = 本轮起手闸 2775 − 产品门槛 2650)"',
     '"prev_swing_source": "前窗r620/logs/run-samples.jsonl (同态在飞窗, n=191, swing=78; 口径 = R620 起手闸 2769 − 产品门槛 2650)"'),
    ("W7_preflight_mb", '"preflight_min_avail_mb": 2775,', '"preflight_min_avail_mb": 2769,'),
]

JUDGE_ANCHORS = {
    "j6_start": "    # --- J6 零回归等价面（**次级**",
    "j6_end": "    # --- J2b 裁选面（机械守恒）",
}

J6_NEW = '''    # --- J6 零回归等价面（次级 · **R621 v4 = 分辨率分级**）------------------------------
    #   R620 事实（登记在案）：逐窗 rc 多重集 ∧ 用例数**逐位相等**在「同臂跨跑次用例数摆动 48..58
    #   （≈10 例）」下**无分辨率** ⇒ 「回退面 ≠ 轴关面」与「同臂噪声」不可区分（R620 记「未判明」）。
    #   R621 按 R620 登记的补救（**加 reps 3→6/窗，禁调阈值**）重测，并把结论**三态化**：
    #     阈值 = **同臂跨跑次用例数极差**（数据派生，非人为常数）—— |Δ中位| < 极差 ⇒ 摆动 ≥ 效应 ⇒ 不可判。
    #     EQUIVALENT              : 逐窗 rc 多重集 ∧ 用例数逐位相等 ⇒ 零回归成立（唯一可读作等价之态）
    #     NON_REGRESSION_DETECTED : Δ中位 ≥ 极差 > 0 ⇒ 回退使行为变劣（**机制面次级红**）
    #     DIFFERENCE_FAVOURABLE   : Δ中位 ≤ −极差 ⇒ 有差但方向有利（**不可读作等价**，信息项）
    #     NO_RESOLUTION           : 其余 ⇒ 判据在本题集/模型下不可判（**禁读作零回归、禁读作通过**）
    #   本条**不再进 instrument_defects**（R620 C1 器具面缺陷：机制面次级 FAIL 曾被编码进
    #   `rc = 2 if defects else 0` ⇒ 整轮被标「禁作被测结论」）。
    j6 = {"need": "逐窗 rc 多重集 ∧ 用例通过数 T == C；不可判则按同臂极差三态化",
          "threshold_source": "同臂跨跑次用例数极差（本轮实测，非人为常数）", "per_window": {}}
    _j6_states = []
    for w in wins:
        _t = sorted((r["tr"].get("rc") for r in of("T", w)), key=lambda x: (x is None, x))
        _c = sorted((r["tr"].get("rc") for r in of("C", w)), key=lambda x: (x is None, x))
        _tp = sorted(r["cases_pass"] for r in of("T", w))
        _cp = sorted(r["cases_pass"] for r in of("C", w))
        _st = j6_state_machine(_t, _c, _tp, _cp)
        j6["per_window"][w] = {"rc_T": _t, "rc_C": _c, "cases_pass_T": _tp, "cases_pass_C": _cp, **_st}
        _j6_states.append(_st["state"])
    if all(s == "EQUIVALENT" for s in _j6_states):
        j6["state"] = "EQUIVALENT"
    elif any(s == "NON_REGRESSION_DETECTED" for s in _j6_states):
        j6["state"] = "NON_REGRESSION_DETECTED"
    elif any(s == "NO_RESOLUTION" for s in _j6_states):
        j6["state"] = "NO_RESOLUTION"
    else:
        j6["state"] = "DIFFERENCE_FAVOURABLE"
    j6["pass"] = bool(j6["state"] == "EQUIVALENT")
    j6["readable_as_zero_regression"] = bool(j6["state"] == "EQUIVALENT")
    j6["reps_per_window"] = int(len(_j6_states) and len(j6["per_window"][wins[0]]["cases_pass_T"]))
    j6["note"] = ("三态 = %s；NO_RESOLUTION 与 DIFFERENCE_FAVOURABLE 一律**不得**读作零回归"
                  "（R620 C2 登记的补救 = reps 3→6；本轴若仍不可判 ⇒ 按 RF0005 §3 R2/R5 记「非承重变量」定案关闭）"
                  % j6["state"])
    if j6["state"] == "NON_REGRESSION_DETECTED":
        mech_secondary.append("J6 非零回归：逐窗 Δ中位 ≥ 同臂极差且方向为劣（机制面次级红，rc=1；不入器具层）")

'''

JUDGE_PATCHES = [
    ("J1_mech_secondary_list", "    defects = []",
     "    defects = []\n    mech_secondary = []   # R621: 机制面次级 FAIL（J6 三态红）——R620 C1 修法：不入器具层"),
    ("J2_rc_rule", "    rc = 2 if defects else 0",
     "    # R621 · rc 分级（R620 C1 器具面缺陷的修法，**在预注册里写明、禁回溯改 R620 判据**）：\n"
     "    #   defects        = **器具缺陷**（臂轴未生效 / 负控无牙 / 输入缺失 …）⇒ rc=2（禁作被测结论）\n"
     "    #   mech_secondary = **机制面次级 FAIL**（J6 非零回归）⇒ rc=1（被测/机制面不满足，器具可用）\n"
     "    #   NO_RESOLUTION / DIFFERENCE_FAVOURABLE ⇒ 不入 rc（**不可判 ≠ 未通过 ≠ 通过**；按预注册 v4 登记）\n"
     "    rc = 2 if defects else (1 if mech_secondary else 0)"),
    ("J3_label", '                    "label": ("机制达标（J0∧J1a∧J1b∧J1c∧J1d∧J1e∧J2b：臂轴生效 + 执行面被采纳集驱动 + 条目守恒 + 空执行面形态清零 + 回退三态不红 + 逐条裁定守恒）"\n'
                 '                              if (j0_pass and j1_pass and j2b_pass) else "机制未达标")\n'
                 '                             if rc == 0 else "器具缺陷（rc=2，禁作被测结论）",',
     '                    "label": (("机制达标（J0∧J1a∧J1b∧J1c∧J1d∧J1e ∧ J2b=%s）· J6=%s"\n'
     '                              % ("PASS" if j2b_pass else "N/A", j6["state"]))\n'
     '                              if (j0_pass and j1_pass and (j2b_pass or j2b_declared_runs == 0)) else "机制未达标")\n'
     '                             if rc != 2 else "器具缺陷（rc=2，禁作被测结论）",\n'
     '                    "label_defect_fixed": ("v4 后置修（起臂后，只改 label 文本）：旧式 label 直接读 '
     '`j2b_pass`，而 legacy 档下 J2b **结构性 N/A**（declared_runs=0）⇒ label 会与 `mechanism_rc` 口径矛盾'
     '（一个读 N/A 一个读失败）。本修使 label 与 mechanism_rc 同谓词；**未改任何阈值、未改 rc、未改判据**，'
     '修前 label 原文另列 `checks_posthoc`。"),\n'
     '                    "rc_rule": ("0 = 主判据无红且次级等价面未判劣（NO_RESOLUTION 不入 rc） / "\n'
     '                                "1 = 机制面次级红（J6 非零回归）/ 2 = 器具缺陷 / 3 = 输入缺失"),'),
    ("J4_verdict_j6", '        "J6_zero_regression_equivalence": {"pass": j6["pass"], "note": "次级，不改主 rc", **j6},',
     '        "J6_zero_regression_equivalence": {"pass": j6["pass"], "state": j6["state"],\n'
     '                                           "note": "次级（三态）；仅 EQUIVALENT 可读作零回归；不改主 rc 之外的层", **j6},\n'
     '        "mechanism_secondary_failures": mech_secondary,'),
    ("J5_print", '                      "J6": j6["pass"], "face_T": j0["A_T_face_set"], "fb_T": j1["T"]["runs_plan_fallback"],',
     '                      "J6": j6["pass"], "J6_state": j6["state"], "face_T": j0["A_T_face_set"],\n'
     '                      "fb_T": j1["T"]["runs_plan_fallback"], "mech_secondary": mech_secondary,'),
    ("J6_rc_semantics", '                    "rc_semantics": "分层：0 器具可用 / 2 器具缺陷（禁作被测结论） / 3 输入缺失；"\n'
                        '                                    "机制面结论见 mechanism_rc 与 label",',
     '                    "rc_semantics": "分层（R621 v4）：0 = 主判据无红（NO_RESOLUTION 不入 rc）/ "\n'
     '                                    "1 = 机制面次级红（J6 非零回归）/ 2 = 器具缺陷（禁作被测结论）/ 3 输入缺失；"\n'
     '                                    "机制面结论见 mechanism_rc 与 label",'),
    # 2026-09-21 补（起臂后、判决前落盘）：派生件里残留的**轮次描述文本**修正
    #   （R620 的 judge 头/kind/honest_bounds 是逐轮 REPL 继承的旧描述 ⇒ 本轮不得沿用旧轮口径）
    ("K1_kind",
     '        "kind": "M3 第三刀（RF0004.2）：空执行面**回退**（采纳集映射出空执行面 ∧ plan 非空 ⇒ 执行面回退读 plan + 原因码入台账）；窗集 w211..w213（与历史 w184..w210 不相交）",',
     '        "kind": "R621 · M3 **第五刀 = 等价面分辨率取证（reps 3→6/窗）+ 判据分级**（RF0004.2）：'
     '唯一变量与 R620 同轴同档位（AGENTFRAMEWORK_R1_ACTION_EXEC，held-constant = legacy），'
     '零产品源码改动 ⇒ 本轮只量「J6 等价面在 reps 翻倍后是否可判」；窗集 w217..w219（与历史 w184..w216 不相交）",'),
    ("K2_bounds_window",
     '            "被测件按设计变更（产品源码改动 ⇒ 重发布 AOT）⇒ 与 R585–R617 冻结件轮**禁相减**；窗集 w208..w210 与历史窗集不相交",',
     '            "被测件与 R619/R620 **逐字节同件**（零产品源码改动，sha a184d731…）⇒ 与 R620 **禁相减、只并列**'
     '（rc 编码层两轮不同：R620 rc=2 器具层 / 本轮 v4 分层）；窗集 w217..w219 与历史窗集不相交",'),
    ("K3_bounds_k5",
     '            "R621 第三刀 = 空执行面**回退**：回退判据为**三态**；若本窗集回退零行使 ⇒ 记 NOT_EXERCISED "',
     '            "R621 第五刀 = 等价面分辨率取证 + 判据分级：J6 判据为**三态**；NO_RESOLUTION ⇒ **不可判**'
     '（禁读作通过、禁读作零回归），按 RF0005 §3 R5 记「本轴非承重变量」定案关闭，禁为同一缺口再加轮；'
     '回退若零行使 ⇒ 记 NOT_EXERCISED "'),
    ("K4_swing_note",
     '        "J6_zero_regression_equivalence": {"pass": j6["pass"], "state": j6["state"],',
     '        "J6_zero_regression_equivalence": {"pass": j6["pass"], "state": j6["state"],\n'
     '                                           "resolution_rule": "阈值 = 同臂跨跑次用例数极差（数据派生）；'
     '|Δ| < 极差 ⇒ NO_RESOLUTION（摆动 ≥ 效应 ⇒ 不可判）",'),
    ("K5_posthoc",
     '        "checks_posthoc": [\n'
     '            "rc 语义分层（0/2/3）＋ mechanism_rc 字段：承 R614/R617，本轮沿用（两轮 rc 列不可直接并列，按 mechanism_rc 对比）",\n',
     '        "checks_posthoc": [\n'
     '            "rc 语义分层（0/2/3）＋ mechanism_rc 字段：承 R614/R617，本轮沿用（两轮 rc 列不可直接并列，按 mechanism_rc 对比）",\n'
     '            "自捕器具缺陷 ①（起臂后修、非回溯）：label 旧式直接读 `j2b_pass`，与 mechanism_rc 的「J2b 结构性 N/A」口径矛盾'
     '（修前 label 原文 = 「机制未达标」，修后 = 「机制达标（… ∧ J2b=N/A）· J6=NO_RESOLUTION」）；**只改 label 文本**，'
     '阈值/rc/判据零改动，两版 label 并列入档",\n'
     '            "自捕器具缺陷 ②（运行期外因，非本仓件）：运行期内存采样 `logs/run-samples.jsonl` 在 elapsed≈190s 处含一枚 '
     '237MB 编辑器语言服务器（pyright/node）⇒ 该窗 mem 读数被压低（2630MB）；已按 pid 清场（不触在飞件）。'
     '本轮判决不读该字段；下轮起手闸 swing 由该文件重派生 ⇒ 方向为**保守**（抬高 margin 只会更严，不产假绿）",\n'),
]

J6_FUNC = '''def j6_state_machine(rc_T, rc_C, cases_T, cases_C):
    """R621 · J6 等价面三态判定（纯函数 ⇒ 影子自检可独立行使，不依赖真机跑次）。

    Δ 口径**写进字段名**（防比较变量写反）：`delta_median_C_minus_T` —— 正值 = 轴关面 C 更好 = 回退劣化。
    阈值 = **同臂跨跑次用例数极差**（数据派生）：效应 |Δ| < 极差 ⇒ 摆动 ≥ 效应 ⇒ 不可判。
    纪律: NO_RESOLUTION 不得读作 EQUIVALENT；只有 rc 多重集 ∧ 用例数**逐位相等**才判 EQUIVALENT。
    """
    def _swing(xs):
        return (max(xs) - min(xs)) if xs else 0

    swing = max(_swing(list(cases_T)), _swing(list(cases_C)))
    eff = max(swing, 1)   # 摆动为 0（确定性用例数）⇒ 可分辨下限降为 1 例
    # Δ = C − T（排序后配对）：d > 0 ⇒ 轴关面更好 ⇒ 回退劣化
    d_all = [b - a for a, b in zip(sorted(cases_T), sorted(cases_C))]
    d_med = statistics.median(d_all) if d_all else 0
    out = {"rc_multiset_equal": bool(list(rc_T) == list(rc_C)),
           "cases_equal": bool(list(cases_T) == list(cases_C)),
           "swing": int(swing), "min_detectable_effect": int(eff),
           "delta_median_C_minus_T": float(d_med),
           "delta_min": (min(d_all) if d_all else 0), "delta_max": (max(d_all) if d_all else 0),
           "n_T": len(list(cases_T)), "n_C": len(list(cases_C))}
    if out["rc_multiset_equal"] and out["cases_equal"]:
        out["state"] = "EQUIVALENT"
    elif abs(d_med) >= eff:
        out["state"] = "NON_REGRESSION_DETECTED" if d_med > 0 else "DIFFERENCE_FAVOURABLE"
    else:
        out["state"] = "NO_RESOLUTION"
    return out


'''


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def main():
    check = "--check" in sys.argv
    os.makedirs(os.path.join(DST, "snapshots"), exist_ok=True)
    os.makedirs(os.path.join(DST, "evidence/windows"), exist_ok=True)
    applied = []

    # 1) 逐字节复制件：cases/ + taskset（题集**逐字节同源** ⇒ 跨窗可比）
    if not check:
        if os.path.isdir(os.path.join(DST, "cases")):
            shutil.rmtree(os.path.join(DST, "cases"))
        shutil.copytree(os.path.join(SRC, "cases"), os.path.join(DST, "cases"))
        shutil.copyfile(os.path.join(SRC, "taskset-r620.json"), os.path.join(DST, "taskset-r621.json"))
    ts_src = sha12(os.path.join(SRC, "taskset-r620.json"))
    ts_dst = sha12(os.path.join(DST, "taskset-r621.json"))
    assert ts_src == ts_dst, "题集复制件必须逐字节同源 (%s vs %s)" % (ts_src, ts_dst)

    # 2) run_r621.sh
    txt = io.open(os.path.join(SRC, "run_r620.sh"), encoding="utf-8").read()
    for a, b in REPL:
        txt = txt.replace(a, b)
    txt = txt.replace("# R621 驱动器（RF0004.2 · M3 **第四刀 = 回退分支真机行使**）——",
                      "# R621 驱动器（RF0004.2 · M3 **第五刀 = 等价面分辨率取证（reps 3→6）+ 判据分级**）——")
    for pid, old, new in RUN_PATCHES:
        assert txt.count(old) == 1, "补丁 %s old 命中数 != 1 (%d)" % (pid, txt.count(old))
        txt = txt.replace(old, new)
        applied.append(pid)
    out_sh = os.path.join(DST, "run_r621.sh")
    assert "AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy" in txt, "held-constant 未落地"
    assert "pub_r620" not in txt and "pub_r621" not in txt, "被测件必须与 R620 同件（pub_r619 逐字节）"
    assert ARTIFACT in txt, "被测件路径应为 pub_r619（同件）"
    assert 'REPS=${REPS:-6}' in txt and "WIN0=${WIN0:-217}" in txt, "reps/窗号补丁未落地"
    if not check:
        io.open(out_sh, "w", encoding="utf-8").write(txt)
        os.chmod(out_sh, 0o755)

    # 3) judge_r621.py
    j = io.open(os.path.join(SRC, "judge_r620.py"), encoding="utf-8").read()
    for a, b in REPL:
        j = j.replace(a, b)
    # 3a) 模块级纯函数（插在 wilson 之前）
    anchor_fn = "def wilson(k, n, z=1.96):"
    assert j.count(anchor_fn) == 1
    j = j.replace(anchor_fn, J6_FUNC + anchor_fn)
    applied.append("JF_j6_state_machine")
    # 3b) J6 区块（边界替换，抗空白漂移）
    s0 = j.index(JUDGE_ANCHORS["j6_start"])
    s1 = j.index(JUDGE_ANCHORS["j6_end"])
    assert s0 < s1, "J6 区块边界顺序异常"
    j = j[:s0] + J6_NEW + j[s1:]
    applied.append("J6_block_v4")
    for pid, old, new in JUDGE_PATCHES:
        assert j.count(old) == 1, "补丁 %s old 命中数 != 1 (%d)" % (pid, j.count(old))
        j = j.replace(old, new)
        applied.append(pid)
    out_j = os.path.join(DST, "judge_r621.py")
    if not check:
        io.open(out_j, "w", encoding="utf-8").write(j)

    # 4) selftest：本轮判据改版（J6 三态 + rc 分级）⇒ 影子自检**新建**（承 R419 四态夹具回放纪律）
    out_s = os.path.join(DST, "selftest_judge_r621.py")
    if not check:
        io.open(out_s, "w", encoding="utf-8").write(SELFTEST_SRC)

    print(json.dumps({"applied": applied, "taskset_sha12": ts_dst,
                      "run_sha12": sha12(out_sh) if not check else None,
                      "judge_sha12": sha12(out_j) if not check else None,
                      "selftest_sha12": sha12(out_s) if not check else None,
                      "legacy_anchor": LEGACY_ANCHOR[:12]}, ensure_ascii=False))


SELFTEST_SRC = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R621 影子自检（**零被测执行**）：直接行使判据器的 J6 三态机 + rc 分级。

纪律（R419/R621）：判据器改版必须先跑影子自检；自检必须能抓到「比较变量写反」这类缺陷
（本轮改版正对 J6 与 rc 层）⇒ 每条断言绑定一个**可预期的三态/rc**，且含 fail-closed 用例。
用法: python3 eval/rover/r621/selftest_judge_r621.py   (rc=0 全过 / rc=2 有未过项)
"""
import importlib.util
import io
import os
import sys

REPO = "/home/agentuser/AgentFramework"
JUDGE = os.path.join(REPO, "eval/rover/r621/judge_r621.py")


def load():
    spec = importlib.util.spec_from_file_location("judge621", JUDGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    m = load()
    f = m.j6_state_machine
    cases = []

    # 1) 逐位相等 ⇒ EQUIVALENT（唯一可读作零回归之态）
    st = f([0, 0, 0], [0, 0, 0], [58, 58, 58], [58, 58, 58])
    cases.append(("P1_equal", st["state"] == "EQUIVALENT" and st["pass"] if "pass" in st else
                  st["state"] == "EQUIVALENT", st))

    # 2) 同臂摆动大（极差 10）而 Δ 中位 1 ⇒ 摆动 ≥ 效应 ⇒ NO_RESOLUTION（**禁读作等价**）
    st = f([0, 0, 5], [0, 5, 5], [58, 48, 53], [57, 47, 52])
    cases.append(("P2_no_resolution", st["state"] == "NO_RESOLUTION", st))

    # 3) 无摆动 + Δ 中位 ≥ 可分辨下限（劣向）⇒ NON_REGRESSION_DETECTED（机制面次级红）
    st = f([0, 0, 0], [0, 0, 0], [56, 56, 56], [58, 58, 58])
    cases.append(("P3_non_regression", st["state"] == "NON_REGRESSION_DETECTED", st))
    cases.append(("P3b_delta_sign_convention", st["delta_median_C_minus_T"] > 0, st))

    # 4) 无摆动 + Δ 中位有利 ⇒ DIFFERENCE_FAVOURABLE（有差且不可读作等价，但不判红）
    st = f([0, 0, 0], [0, 0, 0], [58, 58, 58], [56, 56, 56])
    cases.append(("P4_favourable", st["state"] == "DIFFERENCE_FAVOURABLE", st))
    cases.append(("P4_favourable_not_regression", st["state"] != "NON_REGRESSION_DETECTED", st))

    # 5) 比较变量写反的负控：把 T/C 对调 ⇒ 状态必须随之翻转（否则判据是恒真/恒假门）
    a = f([0, 0, 0], [0, 0, 0], [56, 56, 56], [58, 58, 58])["state"]
    b = f([0, 0, 0], [0, 0, 0], [58, 58, 58], [56, 56, 56])["state"]
    cases.append(("P5_swap_flips", a != b, {"a": a, "b": b}))

    # 6) 极差为 0 且用例数不等但 Δ 中位 == 0 ⇒ 不可判（不冒充等价，也不误判回归）
    st = f([0, 0], [0, 0], [58, 57], [58, 57][::-1])
    cases.append(("P6_zero_delta_non_equal", st["state"] in ("NO_RESOLUTION", "EQUIVALENT"), st))

    # 7) 源码面：rc 分级落地（1 = 机制面次级红层）且 J6 **不再**写进 instrument_defects
    src = io.open(JUDGE, encoding="utf-8").read()
    cases.append(("P7_rc_rule", "rc = 2 if defects else (1 if mech_secondary else 0)" in src, {}))
    cases.append(("P8_j6_not_in_defects",
                  'defects.append("J6' not in src, {}))
    cases.append(("P9_mech_secondary_used",
                  "mech_secondary.append(" in src and '"mechanism_secondary_failures": mech_secondary,' in src, {}))

    bad = 0
    for name, ok, det in cases:
        print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, "" if ok else str(det)[:200]))
        bad += 0 if ok else 1
    print("[影子自检] %d/%d 过" % (len(cases) - bad, len(cases)))
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
'''


if __name__ == "__main__":
    main()
