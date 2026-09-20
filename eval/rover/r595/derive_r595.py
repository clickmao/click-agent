#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R595 器具派生器（**只做命名空间/窗集替换，禁改任何判据逻辑**）。

派生规则（承 R564/R588/R591 先例「逻辑源一字未改，只替换常量」）:
  · `run_r595.sh`        ← `eval/rover/r591/run_r591.sh`（全局命名空间替换 + 头部注释块重写）
  · `kpi_r595.py`        ← `eval/rover/r591/kpi_r591.py`（轮号/臂集合替换；C5 历史四集保留）
  · `pool_taskface_r595.py` ← `pool_taskface_r591.py`（**新增 set3 = [r595]**；set1/set2 逐字不变）
  · `restore_env_r595.py` ← `eval/rover/r588/restore_env_r588.py`（前置自恢复）

用法: python3 eval/rover/r595/derive_r595.py
"""
from __future__ import annotations

import io
import os

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r595")


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


HEADER = """#!/usr/bin/env bash
# R595 驱动器: **主线同件扩窗轮（判据 v3 第三窗集行使）** —— 产品默认档 × 外部真值 codex, 3 新窗 w169..w171;
#              零产品源码改动 / 零新增夹具语义 / 零新增开关。
# 派生 = run_r591.sh（结构逐字节复用；仅命名空间/窗号/起手闸余量源替换, 判据逻辑一字未改）+ 下列**逐条声明的差异**:
#   ① 轮号命名空间 R591→R595 / r591→r595；工作根 D=$HOME/.agentframework/harness/runs/r595；端口 49611→49631。
#   ② 窗号 WIN0 166→169, NWIN 3, REPS 3 —— 臂 = C1(真值) + R595D(产品默认档, 三枚剂量键 unset)。
#      **同件复跑轮**: 被测件与 R585–R591 **同 sha**(4b70fd7cdb39…, BIN 仍取 artifacts/pub_r591/agenthost),
#      题集同 sha(冻结 g1 题面 sha256 516f3208963c6e66) ⇒ 只换窗集。
#   ③ 起手闸摆动余量（**候选⑤ 行使面**）: PREV_SWING 314 ⇒ **102 = r591 观测振幅实测**
#      （同态在飞窗源；R594 为只读轮、无运行期采样器 ⇒ 不可作源，已登记）+ 起手前 3 样本
#      （CEIL = min，极差 ≤ 50MB fail-closed）。条款 = MARGIN := clamp(prev_swing, floor 60, cap = CEIL − GATE − floor)。
#   ④ 判据集: 主判据 = 判据 v3（整题全对率 + 按族分列，器具 `pool_taskface_r595.py` 复用 R589 逻辑源）；
#      `kpi_r595` 的 C1（用例级配对）只作**同向参照**（v2 判决面已在 R590 §12.3 作废）。
#   ⑤ 判据器 `kpi_r595.py` 派生自 `kpi_r591.py`（轮号/臂集合替换 + C5 前序集仍指向 R585–R588 历史四集）。
#   ⑥ 逐用例判分超时 `AGENTFRAMEWORK_GRADE_TIMEOUT`（默认 10，承 R591 派生修正 v2 的零回归控制）。
# 用法: bash eval/rover/r595/run_r595.sh            (全部路径有默认值)
"""


def main():
    # --- 1 run_r595.sh ------------------------------------------------------
    s = rd(os.path.join(REPO, "eval/rover/r591/run_r591.sh"))
    s = s.replace("r591", "r595").replace("R591", "R595")
    s = s.replace("PORT:-49611", "PORT:-49631")
    s = s.replace("PORT 49591→49611", "PORT 49611→49631")
    s = s.replace("WIN0:-166", "WIN0:-169")
    s = s.replace("窗号 WIN0 163→166", "窗号 WIN0 169")
    s = s.replace("PREV_SWING:-314", "PREV_SWING:-102")
    # 同件: 被测二进制仍取 artifacts/pub_r591/agenthost（sha 4b70fd7cdb39…）; 全局替换会把它改成 pub_r595 ⇒ 回钉
    s = s.replace("artifacts/pub_r595/agenthost", "artifacts/pub_r591/agenthost")
    s = s.replace("# PREV_SWING = R588 观测振幅实测 314MB（同态在飞窗源；R590-C2 的 source_admissibility 回退建议）。",
                  "# PREV_SWING = **r591 观测振幅实测 102MB**（同态在飞窗源, n=97, min=2713/max=2815；候选⑤ 派生）。\n"
                  "# 源回退规则（R590-C2）: 只取**同态在飞窗**的运行期采样；R594 为只读轮、无采样器 ⇒ 不可作源。")
    s = s.replace('"prev_swing_source": "r588/logs/run-samples.jsonl (同态在飞窗, n=189, swing=314)"',
                  '"prev_swing_source": "r591/logs/run-samples.jsonl (同态在飞窗, n=97, swing=102)"')
    s = s.replace('"criterion": "C3 起手闸余量条款（R590 派生版 + 只读轮分支以外之在飞窗分支）"',
                  '"criterion": "C3 起手闸余量条款（R590 派生版；候选⑤ 余量源按 R591 在同一飞窗实测重派生）"')
    # 头部注释块整体重写（第 1 行到 "# 用法:" 行）
    idx = s.index("# 用法:")
    end = s.index("\n", idx) + 1
    s = HEADER + s[end:]
    wr(os.path.join(PD, "run_r595.sh"), s)

    # --- 2 kpi_r595.py ------------------------------------------------------
    k = rd(os.path.join(REPO, "eval/rover/r591/kpi_r591.py"))
    k = k.replace("R591", "R595").replace("r591", "r595")
    wr(os.path.join(PD, "kpi_r595.py"), k)

    # --- 3 pool_taskface_r595.py（新增 set3） --------------------------------
    p = rd(os.path.join(REPO, "eval/rover/r591/pool_taskface_r591.py"))
    p = p.replace("R591", "R595").replace("r591", "r595").replace("pool589", "pool589")
    p = p.replace('    set2 = eval_set(mod, ["r595"])\n',
                  '    set2 = eval_set(mod, ["r591"])\n    set3 = eval_set(mod, ["r595"])\n')
    p = p.replace('        "set2_second_window_set": set2,\n',
                  '        "set2_second_window_set": set2,\n        "set3_third_window_set": set3,\n')
    p = p.replace('''            "set2": {"valid": set2["C1_task_face_v3"]["valid_windows"],
                     "median": set2["C1_task_face_v3"]["median_D_task"],
                     "neg": set2["C1_task_face_v3"]["neg_windows"], "pass": set2["C1_task_face_v3"]["pass"]},''',
                  '''            "set2": {"valid": set2["C1_task_face_v3"]["valid_windows"],
                     "median": set2["C1_task_face_v3"]["median_D_task"],
                     "neg": set2["C1_task_face_v3"]["neg_windows"], "pass": set2["C1_task_face_v3"]["pass"]},
            "set3": {"valid": set3["C1_task_face_v3"]["valid_windows"],
                     "median": set3["C1_task_face_v3"]["median_D_task"],
                     "neg": set3["C1_task_face_v3"]["neg_windows"], "pass": set3["C1_task_face_v3"]["pass"]},''')
    p = p.replace('''            "family_all_pass_rate": {f: {"set1": set1["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean"),
                                         "set2": set2["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean")}
                                     for f in mod.FAM_TOTAL},''',
                  '''            "family_all_pass_rate": {f: {"set1": set1["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean"),
                                         "set2": set2["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean"),
                                         "set3": set3["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean")}
                                     for f in mod.FAM_TOTAL},''')
    p = p.replace('    print("set2(w166-168)', '    print("set2(w166-168, 第二窗集)')
    p = p.replace('''    print("C0 set2: runs=%d/%d windows=%d issues=%d | C7 有牙=%s"
          % (set2["C0"]["runs_seen"], set2["C0"]["expected_runs"], set2["C0"]["windows"],
             len(set2["C0"]["issues"]), set2["C7_negative_control"]["has_teeth"]))''',
                  '''    print("C0 set2: runs=%d/%d windows=%d issues=%d | C7 有牙=%s"
          % (set2["C0"]["runs_seen"], set2["C0"]["expected_runs"], set2["C0"]["windows"],
             len(set2["C0"]["issues"]), set2["C7_negative_control"]["has_teeth"]))
    print("set3(w169-171, 第三窗集): valid=%s median=%s neg=%s pass=%s rc=%d"
          % (j["set3"]["valid"], j["set3"]["median"], j["set3"]["neg"], j["set3"]["pass"],
             set3["verdict"]["rc"]))''')
    p = p.replace('"mode": "判据 v3 第二窗集行使（真机臂轮）+ 第一窗集复算（并列件）"',
                  '"mode": "判据 v3 第三窗集行使（真机臂轮）；set1/set2 复算作并列件（跨窗集禁相减）"')
    wr(os.path.join(PD, "pool_taskface_r595.py"), p)

    # --- 4 restore_env_r595.py ---------------------------------------------
    r = rd(os.path.join(REPO, "eval/rover/r588/restore_env_r588.py"))
    r = r.replace("R588", "R595").replace("r588", "r595")
    wr(os.path.join(PD, "restore_env_r595.py"), r)

    for f in ("run_r595.sh", "kpi_r595.py", "pool_taskface_r595.py", "restore_env_r595.py"):
        p2 = os.path.join(PD, f)
        print("%-26s %6d B" % (f, os.path.getsize(p2)))


if __name__ == "__main__":
    main()
