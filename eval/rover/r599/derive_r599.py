#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R599 器具派生器（**只做命名空间/窗集替换 + 预注册新增判据段，禁改任何既有判据逻辑**）。

派生自 `eval/rover/r598/derive_r598.py`（结构同源）:
  · `run_r599.sh`            ← `eval/rover/r598/run_r598.sh`（全局命名空间替换 + 头部注释块重写 + 三处常量）
  · `kpi_r599.py`            ← `eval/rover/r598/kpi_r598.py`（轮号/臂集合替换；C5 前序集仍指 R585–R588 历史四集）
  · `pool_taskface_r599.py`  ← `eval/rover/r598/pool_taskface_r598.py`（**新增 set7 = [r599]**；set1..set6 逐字不变）
  · `launch_r599.sh`         ← `eval/rover/r598/launch_r598.sh`
  · `restore_env_r599.py`    ← `eval/rover/r598/restore_env_r598.py`（前置自恢复回退路径）
  · `prereg-r599.json`       ← 结构化补丁自 `eval/rover/r598/prereg-r598.json`（round/arms/scope/C3 数值/新增 C11·C13）

逐条声明的差异（run_r599.sh）:
  ① 轮号命名空间 R598→R599 / r598→r599；工作根 D=$HOME/.agentframework/harness/runs/r599；端口 49691→49711。
  ② 窗号 WIN0 178→181, NWIN 3, REPS 3 —— 臂 = C1(真值) + R599D(产品默认档, 三枚剂量键 unset)。
     **同件复跑轮**: 被测件与 R585–R598 **同 sha**(4b70fd7cdb39…, BIN 仍取 artifacts/pub_r591/agenthost),
     题集同 sha(e0c667c2…, 冻结 g1 题面 sha 已钉) ⇒ 只换窗集 ⇒ 判据 v3 **第七窗集**。
  ③ 起手闸摆动余量（候选⑤ 行使面）: PREV_SWING 83 ⇒ **264 = r598 同态在飞窗实测振幅**
     （~/.agentframework/harness/runs/r598/logs/run-samples.jsonl, n=57, min=2589/max=2853）。
     诚实边界: 该窗含 R598 环境事件（CEIL 2765→2889MB）⇒ 振幅偏保守（fail-safe 方向）。
  ④ 判据集: 主判据 = 判据 v3（整题全对率 + 按族分列，器具 `pool_taskface_r599.py` 复用 R589 逻辑源，set7 新增）;
     `kpi_r599` 的 C1（用例级配对）只作**同向参照**（v2 判决面已在 R590 §12.3 作废）。
     新增（预注册）: **C11 rc 语义收口**（验收面 `C1_task_face_v3.pass` 编入 rc, fail-closed）
     + **C13 landing 零回归面 scope 绑定机检**（消除单窗集读法伪影）。
  ⑤ 逐用例判分超时 `AGENTFRAMEWORK_GRADE_TIMEOUT`（默认 10，承 R591 派生修正）。

用法: python3 eval/rover/r599/derive_r599.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
PREV = os.path.join(REPO, "eval/rover/r598")
PD = os.path.join(REPO, "eval/rover/r599")

DIFFS = []


def rd(p: str) -> str:
    return io.open(p, encoding="utf-8").read()


def wr(p: str, s: str) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(s)


def must(cond: bool, why: str) -> None:
    """fail-closed 断言: 任一派生不成立 ⇒ 立即中止（不静默产出半成品）。"""
    if not cond:
        print("[派生 fail-closed] %s" % why)
        raise SystemExit(2)
    DIFFS.append(why)


def ns(s: str) -> str:
    return s.replace("R598", "R599").replace("r598", "r599")


HEADER = """#!/usr/bin/env bash
# R599 驱动器: **主线同件扩窗轮（判据 v3 第七窗集行使）** —— 产品默认档 × 外部真值 codex, 3 新窗 w181..w183;
#              零产品源码改动 / 零新增夹具语义 / 零新增开关。
# 派生 = run_r598.sh（结构逐字节复用；仅命名空间/窗号/起手闸余量源替换, 判据逻辑一字未改）+ 下列**逐条声明的差异**:
#   ① 轮号命名空间 R598→R599 / r598→r599；工作根 D=$HOME/.agentframework/harness/runs/r599；端口 49691→49711。
#   ② 窗号 WIN0 178→181, NWIN 3, REPS 3 —— 臂 = C1(真值) + R599D(产品默认档, 三枚剂量键 unset)。
#      **同件复跑轮**: 被测件与 R585–R598 **同 sha**(4b70fd7cdb39…, BIN 仍取 artifacts/pub_r591/agenthost),
#      题集同 sha(e0c667c2…, 冻结 g1 题面 sha 已钉) ⇒ 只换窗集 ⇒ 判据 v3 **第七窗集**。
#   ③ 起手闸摆动余量（**候选⑤ 行使面**）: PREV_SWING 83 ⇒ **264 = r598 同态在飞窗实测振幅**
#      （n=57, min=2589/max=2853MB）+ 起手前 3 样本（CEIL = min，极差 ≤ 50MB fail-closed）。
#      条款 = MARGIN := clamp(prev_swing, floor 60, cap = CEIL − GATE − floor)。
#      **口径诚实**: r598 那窗含环境事件（CEIL 2765→2889MB）⇒ 264 是保守（fail-safe）余量; 若本轮 CAP<floor 则
#      fail-closed（同 R598 处置: 清场 + sync/drop_caches 后重采样, 无数据/状态改动）。
#   ④ 判据集: 主判据 = 判据 v3（整题全对率 + 按族分列，器具 `pool_taskface_r599.py` 复用 R589 逻辑源，set7 新增）;
#      `kpi_r599` 的 C1（用例级配对）只作**同向参照**（v2 判决面已在 R590 §12.3 作废）。
#   ⑤ 判据器 `kpi_r599.py` 派生自 `kpi_r598.py`（轮号/臂集合替换 + C5 前序集仍指向 R585–R588 历史四集）。
#   ⑥ 逐用例判分超时 `AGENTFRAMEWORK_GRADE_TIMEOUT`（默认 10，承 R591 派生修正）。
# 用法: bash eval/rover/r599/run_r599.sh            (全部路径有默认值)
"""


def derive_run() -> None:
    s = ns(rd(os.path.join(PREV, "run_r598.sh")))
    head, sep, tail = s.partition("\nset -uo pipefail\n")
    must(sep != "", "run 头部定位: 找到 'set -uo pipefail' 分隔")
    s = head + sep + tail
    must("PORT:-49711" not in s, "run: 端口未被意外替换")
    s = s.replace("PORT:-49691", "PORT:-49711")
    must("PORT:-49711" in s, "run: 端口默认 49691→49711")
    s = s.replace("WIN0:-178", "WIN0:-181")
    must("WIN0:-181" in s, "run: WIN0 178→181")
    s = s.replace("窗号 WIN0 178", "窗号 WIN0 181")
    s = s.replace("PREV_SWING:-83", "PREV_SWING:-264")
    must("PREV_SWING:-264" in s, "run: PREV_SWING 83→264 (r598 实测)")
    must("artifacts/pub_r591/agenthost" in s, "run: 被测件仍钉 pub_r591（同件单变量）")
    # 余量源注释与派生件字段: 源轮 r597 ⇒ r598, 数值 83/n=46/2723/2806 ⇒ 264/n=57/2589/2853
    old_amp = "观测振幅实测 83MB**（同态在飞窗源, n=46, min=2723/max=2806"
    must(old_amp in s, "run: 定位余量注释体")
    s = s.replace(old_amp, "观测振幅实测 264MB**（同态在飞窗源, n=57, min=2589/max=2853")
    old_src = "(同态在飞窗, n=46, swing=83)"
    must(old_src in s, "run: 定位余量派生件字段")
    s = s.replace(old_src, "(同态在飞窗, n=57, swing=264)")
    must("前窗(r597) 观测振幅实测" in s, "run: 定位余量注释源标签")
    s = s.replace("前窗(r597) 观测振幅实测", "前窗(r598) 观测振幅实测")
    must("前窗r597/logs/run-samples.jsonl" in s, "run: 定位余量字段源标签")
    s = s.replace("前窗r597/logs/run-samples.jsonl", "前窗r598/logs/run-samples.jsonl")
    head2, sep2, tail2 = s.partition("\nset -uo pipefail\n")
    body = HEADER + sep2 + tail2
    wr(os.path.join(PD, "run_r599.sh"), body)
    # 残留检查只看**正文**（头部声明块按纪律必须写明派生来源与历史 ⇒ 允许出现旧轮号）；
    # 正文里允许出现的旧轮号 = **仅** 起手闸余量源（候选⑤ 的派生依据，须可追溯）。
    tail_txt = body.split("\nset -uo pipefail\n", 1)[-1]
    allowed = ["前窗r598/logs/run-samples.jsonl",
               "# PREV_SWING = **前窗(r598) 观测振幅实测 264MB**（同态在飞窗源, n=57, min=2589/max=2853；候选⑤ 派生）。"]
    for a in allowed:
        must(a in tail_txt, "run: 余量源痕迹存在 (%s)" % a[:28])
        tail_txt = tail_txt.replace(a, "<AMPLITUDE_SRC>")
    must("r598" not in tail_txt and "R598" not in tail_txt, "run: 正文无 r598/R598 残留（余量源除外）")


def derive_kpi() -> None:
    k = ns(rd(os.path.join(PREV, "kpi_r598.py")))
    wr(os.path.join(PD, "kpi_r599.py"), k)
    txt = rd(os.path.join(PD, "kpi_r599.py"))
    must("r598" not in txt and "R598" not in txt, "kpi: 无 r598 残留")
    must('"R599D"' in txt, "kpi: 臂名 R599D 已替换")


def derive_pool() -> None:
    src = rd(os.path.join(PREV, "pool_taskface_r598.py"))
    # 历史引用保护: `# R598 修法（预注册 C9…` 是**史实**（C9 在 R598 落地），命名空间替换不得改标它。
    HIST = "# R598 修法（**预注册 C9"
    must(HIST in src, "pool: 定位 C9 史实注释")
    s = src.replace(HIST, "# __PREVC9__ 修法（**预注册 C9")
    # 面序: 先 set6→set7（变量/键/标签/sixth/window-label）, 再命名空间（set7 的源轮 r598 ⇒ r599）
    s = (s.replace("set6", "set7").replace("sixth", "seventh")
          .replace("第六窗集", "第七窗集").replace("w178-180", "w181-183"))
    p = ns(s)
    must("__PREVC9__" in p, "pool: 史实占位存活")
    p = p.replace("__PREVC9__", "R598")
    must(HIST in p, "pool: C9 史实注释未改标（仍写 R598）")
    must("set7 = eval_set(mod, [\"r599\"])" in p, "pool: set7 源轮 = r599")
    must('"set7_seventh_window_set": set7,' in p, "pool: 顶层输出键 set7")
    jux7 = ('            "set7": {"valid": set7["C1_task_face_v3"]["valid_windows"],\n'
            '                     "median": set7["C1_task_face_v3"]["median_D_task"],\n'
            '                     "neg": set7["C1_task_face_v3"]["neg_windows"], "pass": set7["C1_task_face_v3"]["pass"]},\n')
    must(jux7 in p, "pool: juxtaposition set7 块")
    fam7 = ('                                         "set7": set7["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean")}\n')
    must(fam7 in p, "pool: family set7 键")
    pr7 = ('    print("set7(w181-183, 第七窗集): valid=%s median=%s neg=%s pass=%s rc=%d"\n'
           '          % (j["set7"]["valid"], j["set7"]["median"], j["set7"]["neg"], j["set7"]["pass"],\n'
           '             set7["verdict"]["rc"]))\n')
    must(pr7 in p, "pool: set7 打印面")
    # ---- 回填 set6（历史窗集 w178-180, 源轮 r598）----
    a1 = '    set7 = eval_set(mod, ["r599"])\n'
    p = p.replace(a1, '    set6 = eval_set(mod, ["r598"])\n' + a1)
    a2 = '        "set7_seventh_window_set": set7,\n'
    p = p.replace(a2, '        "set6_sixth_window_set": set6,\n' + a2)
    p = p.replace(jux7, jux7.replace("set7", "set6") + jux7)   # 回填 twin（禁覆盖原块）
    must('"set6": {"valid"' in p and '"set7": {"valid"' in p, "pool: juxtaposition 双键共存（set6 回填未覆盖 set7）")
    p = p.replace(fam7, fam7.replace("set7", "set6")[:-2] + ",\n" + fam7)
    p = p.replace(pr7, pr7.replace("set7", "set6").replace("第七窗集", "第六窗集").replace("w181-183", "w178-180") + pr7)
    ds9 = "/ set7（R599）**并列**输出"
    must(ds9 in p, "pool: 定位 docstring 窗集清单")
    p = p.replace(ds9, "/ set6（R598）/ set7（R599）**并列**输出")
    must('set2 = eval_set(mod, ["r591"])' in p and 'set3 = eval_set(mod, ["r595"])' in p
         and 'set4 = eval_set(mod, ["r596"])' in p and 'set5 = eval_set(mod, ["r597"])' in p
         and 'set6 = eval_set(mod, ["r598"])' in p and 'set7 = eval_set(mod, ["r599"])' in p,
         "pool: set2..set7 窗集选择子逐项归位")
    must('"round": "R599"' in p, "pool: 顶层轮号已替换")
    old_mode = '        "mode": "判据 v3 第三窗集行使（真机臂轮）；set1/set2 复算作并列件（跨窗集禁相减）",\n'
    must(old_mode in p, "pool: 定位 mode 串")
    p = p.replace(old_mode, '        "mode": "判据 v3 第七窗集行使（真机臂轮）；set1..set6 复算作并列件（跨窗集禁相减）",\n')
    old_round = '        "round": "R599",\n'
    must(old_round in p, "pool: 定位 round 行（C11 披露插入点）")
    p = p.replace(old_round, old_round + (
        '        "rc_semantics_C11": {"rule": "rc=0 iff (C0.pass ∧ C7.has_teeth ∧ C1_task_face_v3.pass)；'
        '否则 3(数据/真值) > 2(器具缺陷) > 1(验收面未达) 取首因",\n'
        '                             "source": "R598 checks_posthoc: rc 未编码验收面（v2 set5/set6 rc=0 而验收面 pass=False）",\n'
        '                             "audit": "eval/rover/r599/rc_semantics_audit_r599.py（历史逐件 + 单调性 + 三例影子负控）"},\n'
        '        "set_verdicts_C11": {\n'
        '            "rule": "逐窗集落盘 C11 三元素 + rc（审计器据此独立复算，禁靠器件自证）",\n'
        '            "sets": {\n'
        '                "set1": {"set_name": "set1_first_window_set", "c0_pass": set1["C0"]["pass"],\n'
        '                         "c7_has_teeth": set1["C7_negative_control"]["has_teeth"],\n'
        '                         "c1_face_pass": set1["C1_task_face_v3"]["pass"], **set1["verdict"]},\n'
        '                "set2": {"set_name": "set2_second_window_set", "c0_pass": set2["C0"]["pass"],\n'
        '                         "c7_has_teeth": set2["C7_negative_control"]["has_teeth"],\n'
        '                         "c1_face_pass": set2["C1_task_face_v3"]["pass"], **set2["verdict"]},\n'
        '                "set3": {"set_name": "set3_third_window_set", "c0_pass": set3["C0"]["pass"],\n'
        '                         "c7_has_teeth": set3["C7_negative_control"]["has_teeth"],\n'
        '                         "c1_face_pass": set3["C1_task_face_v3"]["pass"], **set3["verdict"]},\n'
        '                "set4": {"set_name": "set4_fourth_window_set", "c0_pass": set4["C0"]["pass"],\n'
        '                         "c7_has_teeth": set4["C7_negative_control"]["has_teeth"],\n'
        '                         "c1_face_pass": set4["C1_task_face_v3"]["pass"], **set4["verdict"]},\n'
        '                "set5": {"set_name": "set5_fifth_window_set", "c0_pass": set5["C0"]["pass"],\n'
        '                         "c7_has_teeth": set5["C7_negative_control"]["has_teeth"],\n'
        '                         "c1_face_pass": set5["C1_task_face_v3"]["pass"], **set5["verdict"]},\n'
        '                "set6": {"set_name": "set6_sixth_window_set", "c0_pass": set6["C0"]["pass"],\n'
        '                         "c7_has_teeth": set6["C7_negative_control"]["has_teeth"],\n'
        '                         "c1_face_pass": set6["C1_task_face_v3"]["pass"], **set6["verdict"]},\n'
        '                "set7": {"set_name": "set7_seventh_window_set", "c0_pass": set7["C0"]["pass"],\n'
        '                         "c7_has_teeth": set7["C7_negative_control"]["has_teeth"],\n'
        '                         "c1_face_pass": set7["C1_task_face_v3"]["pass"], **set7["verdict"]}}},\n'))
    # ---- 新增（预注册 C11）: rc 语义收口（验收面编入 rc, fail-closed） ----
    old_rc = '    rc = 0 if (C0["pass"] and C7["has_teeth"]) else (3 if not C0["pass"] else 2)\n'
    must(old_rc in p, "pool: 定位 rc 计算行（C11 收口靶点）")
    new_rc = ('    # C11（R599 预注册）: rc 语义收口 —— 验收面 `C1_task_face_v3.pass` **编入 rc**（fail-closed）。\n'
              '    # 旧式 rc = (C0.pass ∧ C7.has_teeth) ⇒ set5/set6 出现 rc=0 而验收面 pass=False（脱钩, R598 checks_posthoc）。\n'
              '    # 新式分层: 0 = 全过 / 1 = 被测不满足验收面 / 2 = 器具缺陷（负控无靶）/ 3 = 数据残缺或真值不可靠。\n'
              '    acc = bool(C0["pass"] and C7["has_teeth"] and C1["pass"])\n'
              '    rc = 0 if acc else (3 if not C0["pass"] else (2 if not C7["has_teeth"] else 1))\n')
    p = p.replace(old_rc, new_rc)
    must("C11" in p and 'C1["pass"]' in p, "pool: C11 rc 语义收口已注入")
    old_v = '            "verdict": {"rc": rc, "judge": ("PASS" if rc == 0 else ("FAIL(数据/器具)" if rc == 2 else "BLOCKED(数据残缺)"))}}'
    must(old_v in p, "pool: 定位 verdict 行")
    new_v = ('            "verdict": {"rc": rc, "acceptance_face_encoded": True,\n'
             '                        "blocked": ([k for k, ok in (("C0_truth_reliability", C0["pass"]),\n'
             '                                                   ("C7_negative_control_teeth", C7["has_teeth"]),\n'
             '                                                   ("C1_task_face_v3_acceptance", C1["pass"])) if not ok]),\n'
             '                        "judge": ("PASS" if rc == 0 else ("BLOCKED(数据残缺/真值不可靠)" if rc == 3 else\n'
             '                                                        ("FAIL(器具缺陷: 负控无靶)" if rc == 2 else "FAIL(验收面未达: 质量缺口未成立)")))}}')
    p = p.replace(old_v, new_v)
    must('"C1_task_face_v3_acceptance"' in p, "pool: C11 blocked 列表含验收面")
    # 打印面: rc 语义标注
    must('"verdict"' in p, "pool: verdict 面存在")
    wr(os.path.join(PD, "pool_taskface_r599.py"), p)


def build_prereg() -> None:
    import datetime
    dst = os.path.join(PD, "prereg-r599.json")
    if os.environ.get("SKIP_PREREG") == "1":
        must(os.path.exists(dst), "prereg: SKIP_PREREG 但先写后跑件存在")
        print("[派生] SKIP_PREREG=1 ⇒ 保留原预注册（先写后跑件禁事后重写）")
        return
    d = json.load(io.open(os.path.join(PREV, "prereg-r598.json"), encoding="utf-8"))
    d = json.loads(json.dumps(d))  # deep copy（禁共享引用）
    # set6 读数机取（禁手抄）: 优先 C9 修法后的 ncv2 件, 回退登记件（二者都记）
    def _g(fn):
        p = os.path.join(PREV, fn)
        if not os.path.exists(p):
            return None
        j = json.load(io.open(p, encoding="utf-8"))
        s6 = j.get("set6_sixth_window_set", {})
        f = s6.get("C1_task_face_v3", {})
        return {"artifact": "eval/rover/r598/" + fn, "valid": f.get("valid_windows"),
                "median": f.get("median_D_task"), "neg": f.get("neg_windows"), "pass": f.get("pass"),
                "rc": j.get("verdict", {}).get("rc"), "has_teeth": j.get("C7_negative_control", {}).get("has_teeth")}
    v1, v2 = _g("taskface-pool-r598.json"), _g("taskface-pool-r598-ncv2.json")
    must(v1 is not None, "prereg: set6 登记件存在")
    d["round"] = "R599"
    d["written_at"] = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
    d["claim"] = ("主线真机对照轮 = **判据 v3 第七窗集行使**（同被测件 + 同冻结题集、只换窗集 w181..w183）× 外部真值 codex；"
                  "并轮推进 R598 §9 候选 ②（rc 语义收口: 验收面编入 rc, 配历史判决审计）/ ③（真值侧弱点文本级定因）/"
                  "④（V_int 第六窗集 + landing 零回归面 scope 绑定机检）/ ⑤（起手闸余量按 r598 实测振幅重派生）；"
                  "候选①（产品侧处置）**未做**（须用户放行）。")
    d["single_variable"] = ("本轮自变量 = 窗集（真机臂轮，新窗 w181..w183）。被测件（bin sha 4b70fd7cdb39）、题集（逐字节复用，"
                            "g1 题面 sha 已钉）、判据（v3）、夹具（cases-r521 冻结件）与 R585–R598 同 sha ⇒ 构成判据 v3 的"
                            "**第七窗集**，继续累积有效窗。")
    otc = d["one_time_context"]
    otc["in_scope_rounds_prev"] = otc["in_scope_rounds_prev"] + ["r598"]
    otc["windows"] = ["w181", "w182", "w183"]
    otc["reps_per_window"] = {"C1": 1, "R599D": 3}
    otc["prior_window_sets"]["set6"] = {
        "rounds": ["r598"], "rounds_label": "w178-w180", "valid_windows": v1["valid"], "median_D_task": v1["median"],
        "neg_windows": v1["neg"], "pass": v1["pass"], "note":
        ("登记件 eval/rover/r598/taskface-pool-r598.json (v1: C7 选择面=agentD-r1 单臂 ⇒ 负控无靶 ⇒ rc=%s) ; "
         "C9 修法后 ncv2 件 = %s (has_teeth=%s, rc=%s) ⇒ R598 checks_posthoc 登记「rc 未编码验收面」⇒ 本轮候选② 收口"
         % (v1["rc"], v2, (v2 or {}).get("has_teeth"), (v2 or {}).get("rc")))}
    must("R598D" in d["arms"], "prereg: 定位前轮臂名 R598D")
    d["arms"] = {"C1": d["arms"]["C1"], "R599D": d["arms"]["R598D"]}
    d["arms"]["R599D"]["reps"] = 3
    d["evidence_scope"]["require"] = [
        "eval/rover/r599/dag-r599.md", "eval/rover/r599/prereg-r599.json", "eval/rover/r599/taskset-r599.json",
        "eval/rover/r599/percase-attrib-r599.json", "eval/rover/r599/behav-census-r599.json",
        "eval/rover/r599/gate-margin-r599.json", "eval/rover/r599/kpi-table-r599.json",
        "eval/rover/r599/verdict-r599.json", "eval/rover/r599/taskface-pool-r599.json",
        "eval/rover/r599/landing-predicate-r599.json", "eval/rover/r599/report-r599.md", "eval/rover/r599/snapshots"]
    d["evidence_scope"]["out_of_scope"] = [("R585–R598 在盘读数（只作零回归对照臂 / 并列件，禁相减）")]
    ac = d.pop("axis_criteria_R598")
    ac["note"] = ("主判据 = 判据 v3（整题全对率 + 按族分列，器具 pool_taskface_r599.py 复用 R589 逻辑源）。"
                  "kpi_r599.py 的 C1（用例级配对）只作**同向参照**：v2 判决面已在 docs/external-reference-harness.md §12.3 作废。")
    c3 = ac["C3 起手闸余量条款（候选⑤ 行使面）"]
    c3["prev_swing_effective"] = 264
    c3["prev_swing_evidence"] = ("~/.agentframework/harness/runs/r598/logs/run-samples.jsonl （n=57, min=2589MB, max=2853MB, "
                                "swing=264MB；同态在飞窗。口径诚实: 该窗含 R598 环境事件 ⇒ 保守方向）")
    ac["C8 候选② 真值侧 wythoff 缺口归因（只读, 零子进程）"]["claim"] = (
        "w175/w176/w178 真值（codex）自败 56/58 且失败例同为 wythoff 公开例 + wythoff 隐藏例。"
        "R599 候选③ = 对该二例（wythoff#43-public + wythoff#57-hidden）做**文本级定因**：真值臂产出 vs 期望逐字比对，"
        "判「真值侧弱点」能否由真值臂参数面（同件同档）解释；预注册判据 C8b 三态（格式差异 / 语义差异 / 未能定因）。")
    ac["C10 候选④ V_int 第五窗集分布（真机臂轮）"]["量"] = (
        "对 r599 新窗快照，用与 r593 **同一件定因器**（`landing_predicate_r593.py`，`--rounds r599 --codex-too`）出 `V_int` "
        "直方图 + `cold_set_equal` 交叉校验 + 2×2 列联（两侧分列）")
    ac["C12 铁律 11 前置器"] = ("`exec_precondition.py --round r599` 逐跑次产出物独立物化 + 真跑 + 逐用例判对；"
                              "rc≠0 ⇒ 全部成本/质量降幅读数标「参考（未可验收）」，禁作验收依据。")
    ac["C11 rc 语义收口（R599 预注册, 器具缺陷修法）"] = {
        "claim": ("R598 checks_posthoc 登记: pool 器具 rc 未编码验收面（v2 下 set5/set6 rc=0 而 C1_task_face_v3.pass=False）。"
                  "本项把验收面 pass 编入 rc, fail-closed 分层 0/1/2/3。"),
        "rule": "rc = 0 iff (C0.pass ∧ C7.has_teeth ∧ C1_task_face_v3.pass)；否则 3(数据/真值) > 2(器具缺陷) > 1(验收面未达) 取首因。",
        "audit": ("历史判决审计（`rc_semantics_audit_r599.py`）: 对全部在盘 pool 件（r585..r598，含 v1 与 ncv2 变体）逐件算 旧rc/新rc，"
                  "断言 **单调性（禁放松: 旧非零 ⇒ 新不得 0；旧 0 ⇒ 新 ∈ {0,1}）**，并逐件列出翻转。"),
        "negative_control": ("三例合成 fixture 影子自检: ①旧0∧验收面True ⇒ 新0（不误伤）②旧2∧验收面True ⇒ 新2（不放松）"
                             "③旧0∧验收面False ⇒ 新1（收紧生效）。"),
        "neutrality_claim": "**纯收紧、判决中性**（中性面 = 全部历史登记判决；翻转项须逐条点名，禁静默）。"}
    ac["C13 landing 零回归面 scope 绑定机检（R599 预注册, 器具读法缺陷修法）"] = {
        "claim": ("R598 checks_posthoc: `--rounds r598` 只覆盖 9 跑次 ⇒ 器具零回归面（钉在 R592 登记件全 scope）读数 False 属**单窗集读法伪影**。"
                  "本项把 `--rounds` 与登记件 scope **绑成机检**（`scope_bind_r599.py`）。"),
        "rule": ("请求轮集 ⊊ 登记全 scope ⇒ 零回归面记 `applicable=false, reason=partial_scope`（不进 rc）; 请求 == 全 scope ⇒ 正常判定; "
                 "请求 ⊄ scope ⇒ rc=3 fail-closed。"),
        "neutrality": "全 scope 复跑读数须与 R598 历史全 scope 件（`landing-hist-r598.json`）逐位一致（新增字段除外）。"}
    d["axis_criteria_R599"] = ac
    d["candidate_ledger_R599"] = {
        "① 产品侧处置裁定（wythoff 冷集构造层 / 交付面入口契约）": "**未做（待用户放行）**：动 `src/` 须放行令；本 tick 零产品源码改动。",
        "② rc 语义收口（C11, 器具缺陷修法）": "本轮做（预注册 rc 规则 + 历史判决审计 + 三例影子负控）",
        "③ 真值侧弱点面收口（C8b, 只读文本级定因）": "本轮做（wythoff#43-public + #57-hidden: 真值臂产出 vs 期望逐字）",
        "④ V_int 第六窗集（C10）+ landing scope 绑定机检（C13）": "本轮做（随真机臂轮 + 器具读法机检）",
        "⑤ 起手闸余量按 r598 实测振幅重派生（C3）": "本轮做（swing 83→264）",
    }
    wr(os.path.join(PD, "prereg-r599.json"), json.dumps(d, ensure_ascii=False, indent=1) + "\n")


DAG = """# R599 DAG（意图 → 子任务；先出 DAG 后执行）

**意图**: 主线真机对照轮 —— 判据 v3 **第七窗集**（w181..w183）行使 + R598 §9 候选②③④⑤ 并轮。

| 节点 | 内容 | 依赖 | 可并行面 |
|---|---|---|---|
| N0 | 起手闸（内存余量条款 + 端口/资产 fail-closed + 清场） | — | 串行（独占窗口） |
| N1 | 派生 r599 器具 + **先写后跑** 预注册（含 C11/C13） | N0 | 串行（写同仓） |
| N2 | 真机臂轮：codex 真值 ×1 + 产品默认档 ×3 × 3 窗 = 12 跑次 | N1 | 串行（端口/工作根独占） |
| N3 | 汇总: kpi_r599 + pool set7（含 C11）+ precond(铁律 11) | N2 | 只读 |
| N4 | 候选② rc 语义收口审计 + 候选③ 真值侧文本级定因 + 候选④ V_int set6 / scope 绑定 | N2（读产物） | 只读，可与 N3 并行（不同文件面） |
| N5 | 轮志 + kpi.jsonl + 形式校验 + 本地 commit | N3,N4 | 串行（写同仓） |

**收尾重启判据**: 若 N2 中某窗 12 跑次出现 `unreliable`（真值自败）⇒ 只重启该窗的**产品跑次**（不重跑全轮）；
若 N4 发现 rc 收口引入 `旧非零 ⇒ 新 0` 的放松项 ⇒ 停改、回退该收口（判定器具缺陷，不改判据凑绿）。
"""


def derive_aux() -> None:
    for src, dst in (("launch_r598.sh", "launch_r599.sh"), ("restore_env_r598.py", "restore_env_r599.py")):
        wr(os.path.join(PD, dst), ns(rd(os.path.join(PREV, src))))
    must("r598" not in rd(os.path.join(PD, "launch_r599.sh")), "launch: 无 r598 残留")
    # 冻结夹具/题集**逐字节复制**（禁重造）
    shutil.rmtree(os.path.join(PD, "cases"), ignore_errors=True)
    shutil.copytree(os.path.join(PREV, "cases"), os.path.join(PD, "cases"))
    shutil.copy2(os.path.join(PREV, "taskset-r598.json"), os.path.join(PD, "taskset-r599.json"))
    must(rd(os.path.join(PD, "cases/cases-r521.json")) == rd(os.path.join(PREV, "cases/cases-r521.json")),
         "aux: cases-r521 逐字节同源")
    must(rd(os.path.join(PD, "taskset-r599.json")) == rd(os.path.join(PREV, "taskset-r598.json")),
         "aux: taskset 逐字节同源")
    wr(os.path.join(PD, "dag-r599.md"), DAG)
    must("第七窗集" in rd(os.path.join(PD, "dag-r599.md")), "aux: dag-r599.md 落盘")


def derive_tools() -> None:
    """证据面工具（与臂轮无关，纯只读消费在盘读数）: percase-attrib / behav-census。

    残差修正（**必须是显式补丁**，禁靠命名空间替换蒙混）:
      · behav-census: SCOPE 里 r598 的窗集被 ns 改标成 r599 ⇒ 回填 r598(w178-180) + 新增 r599(w181-183)；
        用例源与 --out 默认改指 r599（否则写入 r596 目录 = 跨轮错标）。
      · percase-attrib: SETS 里原 set6=r598 被 ns 改标成 r599 ⇒ 回填 set6=r598(precond-r598) + 新增 set7=r599。
    """
    c = ns(rd(os.path.join(PREV, "behav_census_r598.py")))
    must('"r599": ["w178", "w179", "w180"]' in c, "tools: 定位 census SCOPE 错标项")
    c = c.replace('"r599": ["w178", "w179", "w180"]}',
                  '"r598": ["w178", "w179", "w180"], "r599": ["w181", "w182", "w183"]}')
    must('"r598": ["w178", "w179", "w180"], "r599": ["w181", "w182", "w183"]' in c, "tools: census SCOPE 已归位")
    c = c.replace('eval/rover/r596/cases/cases-r521.json', 'eval/rover/r599/cases/cases-r521.json')
    # 用法/文档串同样归位（承 R598 遗留的 r596 错标: 名字与 --out 默认两处）
    c = c.replace('eval/rover/r596/behav_census_r596.py', 'eval/rover/r599/behav_census_r599.py')
    c = c.replace('[--out eval/rover/r596/behav-census-r596.json]', '[--out eval/rover/r599/behav-census-r599.json]')
    c = c.replace('"eval/rover/r596/behav-census-r596.json"', '"eval/rover/r599/behav-census-r599.json"')
    must('default=os.path.join(REPO, "eval/rover/r599/behav-census-r599.json")' in c,
         "tools: census --out 默认归位")
    must("r596/behav" not in c, "tools: census 无 r596 错标残留")
    wr(os.path.join(PD, "behav_census_r599.py"), c)
    p = ns(rd(os.path.join(PREV, "percase_attrib_r598.py")))
    old6 = '    "set6": {"rounds": ["r599"], "precond": "precond-r599.json"},\n'
    must(old6 in p, "tools: 定位 percase SETS 错标项")
    p = p.replace(old6, ('    "set6": {"rounds": ["r598"], "precond": "precond-r598.json"},\n'
                         '    "set7": {"rounds": ["r599"], "precond": "precond-r599.json"},\n'))
    must('"set7": {"rounds": ["r599"]' in p, "tools: percase SETS set7 已落")
    wr(os.path.join(PD, "percase_attrib_r599.py"), p)
    for f in ("behav_census_r599.py", "percase_attrib_r599.py"):
        txt = rd(os.path.join(PD, f))
        must("r598" not in txt.replace('["r598"]', "").replace("precond-r598.json", "")
             .replace("r598\": [\"w178\"", ""), "tools: %s 无错标 r598 残留（白名单外）" % f)


def syntax_check() -> None:
    for f in ("run_r599.sh", "launch_r599.sh"):
        r = subprocess.run(["bash", "-n", os.path.join(PD, f)], capture_output=True, text=True)
        must(r.returncode == 0, "语法: %s bash -n rc=%d %s" % (f, r.returncode, r.stderr.strip()[:120]))
    r = subprocess.run([sys.executable, "-m", "py_compile",
                        os.path.join(PD, "kpi_r599.py"), os.path.join(PD, "pool_taskface_r599.py"),
                        os.path.join(PD, "restore_env_r599.py"), os.path.join(PD, "percase_attrib_r599.py"),
                        os.path.join(PD, "behav_census_r599.py"), os.path.join(PD, "finish_r599.py")],
                       capture_output=True, text=True)
    must(r.returncode == 0, "语法: py_compile rc=%d %s" % (r.returncode, r.stderr.strip()[:200]))


def main() -> int:
    os.makedirs(PD, exist_ok=True)
    derive_run()
    derive_kpi()
    derive_pool()
    derive_aux()
    derive_tools()
    build_prereg()
    # 预注册自检（与 run_r599.sh 第 0 步同源口径）
    pr = json.load(io.open(os.path.join(PD, "prereg-r599.json"), encoding="utf-8"))
    must(pr["round"] == "R599" and pr["written_before_run"] is True, "prereg: round/written_before_run")
    must(set(pr["arms"]) == {"C1", "R599D"}, "prereg: 臂集合")
    must(len(pr["evidence_scope"]["require"]) == 12, "prereg: evidence_scope.require == 12")
    must(str(pr.get("criterion_version", "")).startswith("v3"), "prereg: criterion_version v3")
    must("axis_criteria_R599" in pr and "C11 rc 语义收口（R599 预注册, 器具缺陷修法）" in pr["axis_criteria_R599"],
         "prereg: C11 段落地")
    must("C13 landing 零回归面 scope 绑定机检（R599 预注册, 器具读法缺陷修法）" in pr["axis_criteria_R599"],
         "prereg: C13 段落地")
    syntax_check()
    print("[派生] %d 项断言全过:" % len(DIFFS))
    for d in DIFFS:
        print("  · %s" % d)
    print("[派生] 件: %s" % ", ".join(sorted(os.listdir(PD))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
