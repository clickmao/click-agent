#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R598 器具派生器（**只做命名空间/窗集替换，禁改任何判据逻辑**）。

派生自 `eval/rover/r597/derive_r597.py`（结构同源）:
  · `run_r598.sh`        ← `eval/rover/r597/run_r597.sh`（全局命名空间替换 + 头部注释块重写 + 三处常量）
  · `kpi_r598.py`        ← `eval/rover/r597/kpi_r597.py`（轮号/臂集合替换；C5 前序集仍指 R585–R588 历史四集）
  · `pool_taskface_r598.py` ← `eval/rover/r597/pool_taskface_r597.py`（**新增 set6 = [r598]**；set1..set5 逐字不变）
  · `launch_r598.sh`     ← `eval/rover/r597/launch_r597.sh`
  · `restore_env_r598.py`← `eval/rover/r597/restore_env_r597.py`（前置自恢复回退路径）

逐条声明的差异（run_r598.sh）:
  ① 轮号命名空间 R597→R598 / r597→r598；工作根 D=$HOME/.agentframework/harness/runs/r598；端口 49671→49691。
  ② 窗号 WIN0 175→178, NWIN 3, REPS 3 —— 臂 = C1(真值) + R598D(产品默认档, 三枚剂量键 unset)。
     **同件复跑轮**: 被测件与 R585–R597 **同 sha**(4b70fd7cdb39…, BIN 仍取 artifacts/pub_r591/agenthost),
     题集同 sha(e0c667c2…, 冻结 g1 题面 sha 已钉) ⇒ 只换窗集 ⇒ 判据 v3 **第六窗集**。
  ③ 起手闸摆动余量（候选⑤ 行使面）: PREV_SWING 168 ⇒ **83 = r597 同态在飞窗实测振幅**
     （~/.agentframework/harness/runs/r597/logs/run-samples.jsonl, n=46, min=2723/max=2806）。
  ④ 判据集: 主判据 = 判据 v3（整题全对率 + 按族分列，器具 `pool_taskface_r598.py` 复用 R589 逻辑源，set6 新增）;
     `kpi_r598` 的 C1（用例级配对）只作**同向参照**（v2 判决面已在 R590 §12.3 作废）。
  ⑤ 逐用例判分超时 `AGENTFRAMEWORK_GRADE_TIMEOUT`（默认 10，承 R591 派生修正）。

用法: python3 eval/rover/r598/derive_r598.py
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
PREV = os.path.join(REPO, "eval/rover/r597")
PD = os.path.join(REPO, "eval/rover/r598")

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
    return s.replace("R597", "R598").replace("r597", "r598")


HEADER = """#!/usr/bin/env bash
# R598 驱动器: **主线同件扩窗轮（判据 v3 第六窗集行使）** —— 产品默认档 × 外部真值 codex, 3 新窗 w178..w180;
#              零产品源码改动 / 零新增夹具语义 / 零新增开关。
# 派生 = run_r597.sh（结构逐字节复用；仅命名空间/窗号/起手闸余量源替换, 判据逻辑一字未改）+ 下列**逐条声明的差异**:
#   ① 轮号命名空间 R597→R598 / r597→r598；工作根 D=$HOME/.agentframework/harness/runs/r598；端口 49671→49691。
#   ② 窗号 WIN0 175→178, NWIN 3, REPS 3 —— 臂 = C1(真值) + R598D(产品默认档, 三枚剂量键 unset)。
#      **同件复跑轮**: 被测件与 R585–R597 **同 sha**(4b70fd7cdb39…, BIN 仍取 artifacts/pub_r591/agenthost),
#      题集同 sha(e0c667c2…, 冻结 g1 题面 sha 已钉) ⇒ 只换窗集 ⇒ 判据 v3 **第六窗集**。
#   ③ 起手闸摆动余量（**候选⑤ 行使面**）: PREV_SWING 168 ⇒ **83 = r597 同态在飞窗实测振幅**
#      （n=46, min=2723/max=2806MB）+ 起手前 3 样本（CEIL = min，极差 ≤ 50MB fail-closed）。
#      条款 = MARGIN := clamp(prev_swing, floor 60, cap = CEIL − GATE − floor)。
#      **起手前清场登记（R598 环境事件, 非判据改动）**: 本 tick 首次采样 CEIL≈2765MB ⇒ CAP=55 < floor 60
#      ⇒ 条款 fail-closed；处置 = sync + drop_caches（page cache 回收, 无数据/状态改动）⇒ CEIL≈3017MB。
#   ④ 判据集: 主判据 = 判据 v3（整题全对率 + 按族分列，器具 `pool_taskface_r598.py` 复用 R589 逻辑源，set6 新增）;
#      `kpi_r598` 的 C1（用例级配对）只作**同向参照**（v2 判决面已在 R590 §12.3 作废）。
#   ⑤ 判据器 `kpi_r598.py` 派生自 `kpi_r597.py`（轮号/臂集合替换 + C5 前序集仍指向 R585–R588 历史四集）。
#   ⑥ 逐用例判分超时 `AGENTFRAMEWORK_GRADE_TIMEOUT`（默认 10，承 R591 派生修正）。
# 用法: bash eval/rover/r598/run_r598.sh            (全部路径有默认值)
"""


def derive_run() -> None:
    s = rd(os.path.join(PREV, "run_r597.sh"))
    head, sep, tail = s.partition("\nset -uo pipefail\n")
    must(sep != "", "run 头部定位: 找到 'set -uo pipefail' 分隔")
    s = ns(head) + sep + ns(tail)
    s = s.replace("PORT:-49671", "PORT:-49691")
    must("PORT:-49691" in s, "run: 端口默认 49671→49691")
    s = s.replace("WIN0:-175", "WIN0:-178")
    must("WIN0:-178" in s, "run: WIN0 175→178")
    s = s.replace("窗号 WIN0 175", "窗号 WIN0 178")
    s = s.replace("PREV_SWING:-168", "PREV_SWING:-83")
    must("PREV_SWING:-83" in s, "run: PREV_SWING 168→83 (r597 实测)")
    must("artifacts/pub_r591/agenthost" in s, "run: 被测件仍钉 pub_r591（同件单变量）")
    # 余量源注释与派生件字段（命名空间已把 r596→r597; 此处只改数值）
    old_amp = "观测振幅实测 168MB**（同态在飞窗源, n=61, min=2454/max=2622"
    must(old_amp in s, "run: 定位余量注释体")
    s = s.replace(old_amp, "观测振幅实测 83MB**（同态在飞窗源, n=46, min=2723/max=2806")
    old_src = "(同态在飞窗, n=61, swing=168)"
    must(old_src in s, "run: 定位余量派生件字段")
    s = s.replace(old_src, "(同态在飞窗, n=46, swing=83)")
    # 余量源**标签**归位: 派生器命名空间只映射 r597→r598, 故源标签仍写作 r596 ⇒ 必须改标为前窗 r597
    # （数值已是 r597 实测; 标签与数值不同源 = 事实性错标, 会误导下游追溯）。
    must("前窗(r596) 观测振幅实测" in s, "run: 定位余量注释源标签")
    s = s.replace("前窗(r596) 观测振幅实测", "前窗(r597) 观测振幅实测")
    must("前窗r596/logs/run-samples.jsonl" in s, "run: 定位余量字段源标签")
    s = s.replace("前窗r596/logs/run-samples.jsonl", "前窗r597/logs/run-samples.jsonl")
    body = HEADER + s.split("\n", 1)[1]
    wr(os.path.join(PD, "run_r598.sh"), body)
    # 残留检查只看**正文**（头部声明块按纪律必须写明派生来源与历史 ⇒ 允许出现旧轮号）；
    # 正文里允许出现的旧轮号 = **仅** 起手闸余量源（候选⑤ 的派生依据，须可追溯）。
    tail_txt = body.split("\nset -uo pipefail\n", 1)[-1]
    allowed = ["前窗r597/logs/run-samples.jsonl",
               "# PREV_SWING = **前窗(r597) 观测振幅实测 83MB**（同态在飞窗源, n=46, min=2723/max=2806；候选⑤ 派生）。"]
    for a in allowed:
        tail_txt = tail_txt.replace(a, "<AMPLITUDE_SRC>")
    must("r597" not in tail_txt and "R597" not in tail_txt, "run: 正文无 r597/R597 残留（余量源除外）")


def derive_kpi() -> None:
    k = ns(rd(os.path.join(PREV, "kpi_r597.py")))
    wr(os.path.join(PD, "kpi_r598.py"), k)
    txt = rd(os.path.join(PD, "kpi_r598.py"))
    must("r597" not in txt and "R597" not in txt, "kpi: 无 r597 残留")
    must('"R598D"' in txt, "kpi: 臂名 R598D 已替换")


DS_NEW = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R598 判据 v3 **第六窗集行使** 器具（driver）。

纪律（承 R564「逻辑源一字未改，只替换窗集常量」先例）:
  · **逻辑源 = `eval/rover/r589/pool_taskface_r589.py`（import，禁重写第二份）**;
    逐窗两面重算 / 按族分列 / `unreliable` 单列 / 失败原因直方图 全部由该模块提供。
  · 本文件只做三件事: ① 参数化窗集（`mod.ROUNDS`）② C0 期望值随窗集参数化（R589 的 48/12 是四集常数）
    ③ 把 set1（R585–R588）/ set2（R591）/ set3（R595）/ set4（R596）/ set5（R597）/ set6（R598）**并列**输出（跨窗集**禁相减**）。
  · 判据阈值与 R589 同源同值: v3 主判据 = 有效窗 `中位 ≤ -0.34 ∧ 负号窗 ≥ ceil(有效/2)`（写死, 非事后调）。

用法: python3 eval/rover/r598/pool_taskface_r598.py --out eval/rover/r598/taskface-pool-r598.json
"""'''


def derive_pool() -> None:
    p = rd(os.path.join(PREV, "pool_taskface_r597.py"))
    i = p.index('"""', 3) + 3          # 文档串**开**引号之后
    j = p.index('"""', i) + 3          # 文档串**闭**引号之后
    p = DS_NEW + p[j:]
    # ① 新增 set6
    a1 = '    set5 = eval_set(mod, ["r597"])\n'
    must(a1 in p, "pool: 定位 set5 行")
    p = p.replace(a1, a1 + '    set6 = eval_set(mod, ["r598"])\n')
    # ② 顶层输出键
    a2 = '        "set5_fifth_window_set": set5,\n'
    must(a2 in p, "pool: 定位 set5 输出键")
    p = p.replace(a2, a2 + '        "set6_sixth_window_set": set6,\n')
    # ③ juxtaposition 内 set5 → set5 + set6
    a3 = ('            "set5": {"valid": set5["C1_task_face_v3"]["valid_windows"],\n'
          '                     "median": set5["C1_task_face_v3"]["median_D_task"],\n'
          '                     "neg": set5["C1_task_face_v3"]["neg_windows"], "pass": set5["C1_task_face_v3"]["pass"]},\n')
    must(a3 in p, "pool: 定位 juxtaposition set5 块")
    p = p.replace(a3, a3 + a3.replace('"set5"', '"set6"').replace("set5[", "set6["))
    # ④ family_all_pass_rate 增 set6（**只补前一行逗号 + 追加一行**，末行仍以 } 收口）
    a4 = '                                         "set5": set5["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean")}\n'
    must(a4 in p, "pool: 定位 family set5 键")
    a4n = ('                                         "set6": set6["family_aggregate"].get(f, {}).get("prod_all_pass_rate_mean")}\n')
    p = p.replace(a4, a4[:-2] + ",\n" + a4n)
    # ⑤ 打印面
    a5 = '    print("族 all-pass 率: %s" % json.dumps(j["family_all_pass_rate"], ensure_ascii=False))\n'
    must(a5 in p, "pool: 定位打印面")
    p = p.replace(a5, ('    print("set6(w178-180, 第六窗集): valid=%s median=%s neg=%s pass=%s rc=%d"\n'
                       '          % (j["set6"]["valid"], j["set6"]["median"], j["set6"]["neg"], j["set6"]["pass"],\n'
                       '             set6["verdict"]["rc"]))\n') + a5)
    # ⑥ 顶层轮号（**不动** set2..set5 的窗集选择子）
    p = p.replace('        "round": "R597",', '        "round": "R598",')
    p = p.replace('print("== R597 判据 v3 第五窗集 ==")', 'print("== R598 判据 v3 第六窗集 ==")')
    wr(os.path.join(PD, "pool_taskface_r598.py"), p)
    txt = rd(os.path.join(PD, "pool_taskface_r598.py"))
    must('set6 = eval_set(mod, ["r598"])' in txt, "pool: set6 已生成")
    must('set2 = eval_set(mod, ["r591"])' in txt and 'set3 = eval_set(mod, ["r595"])' in txt
         and 'set4 = eval_set(mod, ["r596"])' in txt and 'set5 = eval_set(mod, ["r597"])' in txt,
         "pool: set2/set3/set4/set5 窗集选择子未被误改")
    must('"round": "R598"' in txt, "pool: 顶层轮号已替换")


def derive_aux() -> None:
    for src, dst in (("launch_r597.sh", "launch_r598.sh"), ("restore_env_r597.py", "restore_env_r598.py")):
        wr(os.path.join(PD, dst), ns(rd(os.path.join(PREV, src))))
    must("r597" not in rd(os.path.join(PD, "launch_r598.sh")), "launch: 无 r597 残留")
    # 冻结夹具/题集**逐字节复制**（禁重造）
    shutil.rmtree(os.path.join(PD, "cases"), ignore_errors=True)
    shutil.copytree(os.path.join(PREV, "cases"), os.path.join(PD, "cases"))
    shutil.copy2(os.path.join(PREV, "taskset-r597.json"), os.path.join(PD, "taskset-r598.json"))
    must(rd(os.path.join(PD, "cases/cases-r521.json")) == rd(os.path.join(PREV, "cases/cases-r521.json")),
         "aux: cases-r521 逐字节同源")
    must(rd(os.path.join(PD, "taskset-r598.json")) == rd(os.path.join(PREV, "taskset-r597.json")),
         "aux: taskset 逐字节同源")


def syntax_check() -> None:
    for f in ("run_r598.sh", "launch_r598.sh"):
        r = subprocess.run(["bash", "-n", os.path.join(PD, f)], capture_output=True, text=True)
        must(r.returncode == 0, "语法: %s bash -n rc=%d %s" % (f, r.returncode, r.stderr.strip()[:120]))
    r = subprocess.run([sys.executable, "-m", "py_compile",
                        os.path.join(PD, "kpi_r598.py"), os.path.join(PD, "pool_taskface_r598.py"),
                        os.path.join(PD, "restore_env_r598.py")], capture_output=True, text=True)
    must(r.returncode == 0, "语法: py_compile rc=%d %s" % (r.returncode, r.stderr.strip()[:200]))


def main() -> int:
    os.makedirs(PD, exist_ok=True)
    derive_run()
    derive_kpi()
    derive_pool()
    derive_aux()
    syntax_check()
    print("[派生] %d 项断言全过:" % len(DIFFS))
    for d in DIFFS:
        print("  · %s" % d)
    print("[派生] 件: %s" % ", ".join(sorted(os.listdir(PD))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
