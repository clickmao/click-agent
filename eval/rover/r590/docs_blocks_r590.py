#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R590 文档面收口：master §7 块（EOF 追加）+ improvements.md 顶部新节。
文本插入（**不做整份重排**）；写后回读核对字节与锚点。
"""
from __future__ import annotations

import io
import os

REPO = "/home/agentuser/AgentFramework"
MASTER = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
IMP = os.path.join(REPO, "docs/improvements.md")

BLOCK = """
- **R590（只读定因/入册轮：候选 ②③④⑤ 并轮；零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关）**:
**修改点** ① 候选② 普查器 `eval/rover/r590/escape_form_census_r590.py`（契约块 `contract_span` **import** R589 器具，禁重写第二份；器具自捕 #1: v1 把「契约块未闭合」支读成空串 ⇒ 同一条跑次在 POS 控制与 `scan_run` 上给出**互相矛盾**的形态读数 ⇒ 修后未闭合支也纳入形态判定并另记 `span_balanced`；v1 读数留档 `escape-census-r590-v1spanpath.json`，**不翻案**）；② 候选④ `gate_margin_r590.py` + `gate_r590.sh`（派生自 r589 版，**只改余量条款这一处自由度**）；③ 候选⑤ `precond_cost_r590.py`（守恒判据 = 复跑结论 == 该轮自身已登记 `precond.rc`）；④ N5 `readonly_fingerprint_r590.py`（与 r589 并池器同口径 import；对照物升级为**跨轮不变式**）；⑤ 候选③ 判据面入册 `docs/external-reference-harness.md` §12.3。
**读数**（R585–R588 在盘件；题集 sha `e0c667c2a313c04b`、二进制 sha `4b70fd7cdb39`）：**候选② 否证** —— 目标形态（契约块内双反斜杠 + n）出现率 **0.9722（35/36，近乎普遍）**、Δ_allpass **0.4000** < 阈值 **0.5833**（= R589 实测族间落差 0.9722 − 0.3889）⇒ **与整族塌陷非承重**；唯一缺档跑次（`r586/w159/agentD-r2`）**同时**是「契约块未闭合」跑次 ⇒ 该轴与「解析失败」**共线**、无独立可分面 ⇒ 依预注册决策树**转记落点非冷点主因**（post-hoc：`wythoff` 失败由 `stdout_mismatch×174` 主导，与 §12.2 的 `MOVE_NOT_COLD` 主因同向）；成对控制 POS（`r587/w162/agentD-r3`，form_n=59）/ NEG1（合成正确转义⇒否）/ NEG2（合成注入⇒是）全翻面（`has_teeth=true`）。**候选④ 三处缺陷一次收口** —— ① 只读轮（零臂）无在飞窗 ⇒ 条款 `prev_swing` **取值未定义**（缺分支，非数值问题）；② 条款写明「起手前样本极差 ≤ 50MB」而 r589 实现**未落**（r589 实测极差 361MB 仍被放行）⇒ 本轮落成 fail-closed 并行使（n=3 / 顶棚 2748 / 极差 **3MB** ⇒ 过）；③ R589 的 361MB 系**清场跳变**（两个样本分别落在清本会话工具子进程**之前/之后**：2480→2726MB，**+246MB 复现**）⇒ 非同态、不可当宿主振幅用，回退源 = 最近一次同态在飞窗振幅 R588 = 314MB，稳健性表证明换源**不改结论**；`cap` 在 2494–2900 全档**恒 binding** ⇒ **振幅项退化**（收紧的是上界、不是下界）；**真机行使 rc=2 fail-closed「窗口不可开」**（`cap = 2748 − 2650 − 60 = 38 < floor 60`）⇒ A1/A2 与判别力成对控制**未行使**（fail-closed 是**正确行为**、不记缺陷，但本轮因此**无闸 PASS 读数**）。**候选⑤** —— 前置器 **4/4 完成**、守恒判据 `all_consistent=true`（复跑结论与各轮自身 `runs/<r>/precond.rc` **逐轮一致**）、耗时（**墙钟信息字段**）相邻完成间隔 `[22,20,21] s` / 4 轮窗口 63 s（第 1 轮起点无锚 ⇒ 只测 2..4 轮）；**冲突定因（本轮只读定位）**：`eval/rover/r589/finish_r589.py` 的两处打印（:252 / :361）读的是它**自己从未回填的收集字典** `pre_rc` ⇒ 写「in_flight / 0/4」，而同报告另一处写「4/4」⇒ 同轮两处读数**都不是「回读磁盘归档」**（与「计数类读数取外部真值、不采信内存账本」同族）；R589 的「0/4 / 未全数完成」读数**不翻案**（原样留档），只作口径修正登记。**候选③** 判据 v3 入册（整题全对率 + 按族分列；v2 **判决面作废登记**、保留为用例级参照 + 派生器口径来源；**跨版本禁相减**；**事后入册**披露）。**只读性** 2210 文件、**跨轮不变式**成立（含 mtime ⇒ 任何写都会改 mtime）。**形式门禁** **14/14**（Failed 0 / Passed 14 / Skipped 0）· 本轮零 `src/` 改动、零登记表改动 ⇒ **不造** `owner_round=R590` 的 capability 登记行（与 R588/R589 同处置）。
**诚实边界**：零新跑次 ⇒ **不宣称任何质量/成本降幅/增益**；候选②为**否证**结论且属只读相关（唯一缺档组 n=1 ⇒ 不报显著性）；候选④ 本轮**无闸 PASS 读数**（「窗口不可开」不记缺陷、也不得读成「条款已收紧生效」）；候选⑤ 耗时只作信息字段；候选③为**事后入册**；候选①（(b) 直进产品侧修复 / (c) 换更长题面）**待用户放行**，本轮未推进。
轮志 `eval/rover/r590/report-r590.md`、预注册/DAG `eval/rover/r590/{prereg-r590.json,dag-r590.md}`、台账 `eval/capability/kpi.jsonl`（R590）。

- **下轮候选 (R591)**: ① **本轴处置裁定（待用户放行）**：(b) 直进产品侧修复（须放行 ⇒ 本轮未动产品源码）(c) 换更长题面=新基线（改可比性 ⇒ 非可自决） ② **落点非冷点主因定因**（候选②已把「过度转义」形态轴**否证** ⇒ 靶点转入 `MOVE_NOT_COLD`：从 §12.2 的 67/131 份额出发，只读量「落点谓词的真值 vs 产物」逐例差，判「算法错」还是「冷集构造错」；纯只读、零产品改动） ③ **起手闸「只读轮分支」入册**（把 R590 派生的 `prev_swing_effective = max(在飞窗振幅, 起手前采样振幅)` + 「极差 ≤ 50MB」fail-closed 条写进 `docs/external-reference-harness.md` §12.1.1；v2 保留、标注禁相减） ④ **前置器抽样复跑口径入册**（守恒判据「复跑结论 == 该轮自身已登记读数」+ fail-closed 条件；器具面零开发） ⑤ **判据 v3 的第二窗集行使**（`−0.34` 阈值只在一个窗集上行使过 ⇒ 分辨率未经复核；同件同题集、零产品改动 ⇒ 须跑新窗 = 真机臂）。
"""

IMP_BLOCK = """## R590 · 2026-09-20 · 状态: **完成（rc=0 / 六判据组件全 0；候选②为否证结论；形式门禁 14/14）· 只读定因/入册轮** · 主题: **候选 ②③④⑤ 并轮 —— 形态普查（⇒ 否证）× 起手闸余量条款重派生（⇒ 三处缺陷收口 + fail-closed）× 前置器耗时口径（⇒ 冲突定因）× 判据 v3 入册**

- **修改点**: ① `eval/rover/r590/escape_form_census_r590.py`（契约块切分 **import** R589 器具 ⇒ 同口径、禁重写第二份）；② `gate_margin_r590.py` + `gate_r590.sh`（派生自 r589 版，**只改余量条款一处自由度**）；③ `precond_cost_r590.py`；④ `readonly_fingerprint_r590.py`；⑤ `finish_r590.py`；⑥ `docs/external-reference-harness.md` §12.3。
- **候选②（形态普查）**: 目标形态 = 契约块内「双反斜杠 + 字母 n」（派生自 R589 C8 字符级最小化的定位元素）⇒ 出现率 **0.9722（35/36）**、Δ_allpass **0.4000** < 阈值 **0.5833** ⇒ **NOT_LOAD_BEARING（与整族塌陷非承重）**；唯一缺档跑次同时是「契约块未闭合」跑次 ⇒ 轴与「解析失败」**共线** ⇒ 依预注册决策树**转记落点非冷点主因**（`stdout_mismatch×174` 主导）。**器具自捕 #1**: v1 未闭合支读成空串 ⇒ 同一跑次在 POS 控制与 `scan_run` 上给出互相矛盾读数；修后更正，v1 留档不翻案。
- **候选④（余量条款）**: ① 补「只读轮（零臂）无在飞窗」分支（`prev_swing` 原为**未定义**）；② 把条款写明却**未实现**的「起手前样本极差 ≤ 50MB」落成 fail-closed（r589 实测 361MB 仍被放行）；③ 认定 R589 的 361MB = **清场跳变**（2480→2726MB，+246MB 复现）⇒ 不可采，回退 R588 同态 314MB、换源不改结论；`cap` 恒 binding ⇒ **振幅项退化**。**真机行使 rc=2 fail-closed**（cap 38 < floor 60）⇒ A1/A2 与成对控制未行使。
- **候选⑤（前置器口径）**: **4/4 完成**、守恒判据 `all_consistent=true`；耗时（信息字段）`[22,20,21] s` / 窗口 63 s；**冲突定因** = `finish_r589.py` 读**自己未回填的收集字典** ⇒ 写「in_flight / 0/4」（同报告另一处写「4/4」）⇒ 同轮两处读数**都非回读磁盘归档**；R589 读数不翻案、只作口径修正。
- **候选③（入册）**: `docs/external-reference-harness.md` 新增 §12.3 判据 v3（整题全对率 + 按族分列）；v2 **判决面作废登记**（保留为用例级参照 + 派生器口径来源）；**跨版本禁相减**；**事后入册**披露。
- **只读性 / 形式门禁**: 2210 文件、**跨轮不变式**成立（含 mtime）；形式门禁 **14/14**（Failed 0 / Passed 14）；零 `src/` 改动 ⇒ 不造 `owner_round=R590` 登记行。
- **诚实边界**: 零新跑次 ⇒ **不宣称任何降幅/增益**；候选②为否证结论（唯一缺档组 n=1 ⇒ 不报显著性）；候选④ 无闸 PASS 读数；候选⑤ 耗时为信息字段；候选① **待用户放行**。
- 轮志 `eval/rover/r590/report-r590.md`、预注册 `prereg-r590.json`、DAG `dag-r590.md`、台账 `eval/capability/kpi.jsonl`（R590）。

"""


def main():
    # 1) master plan：EOF 追加（R590 为最新块）
    with io.open(MASTER, "r", encoding="utf-8") as fh:
        mt = fh.read()
    assert "下轮候选 (R590)" in mt, "锚点缺失: master 无 R590 候选行"
    assert "R590（只读定因/入册轮" not in mt, "R590 块已存在 ⇒ 幂等跳过"
    before = len(mt.encode("utf-8"))
    if not mt.endswith("\n"):
        mt += "\n"
    mt += BLOCK
    with io.open(MASTER, "w", encoding="utf-8") as fh:
        fh.write(mt)

    # 2) improvements：在最新节（R589 节）之前插入
    with io.open(IMP, "r", encoding="utf-8") as fh:
        it = fh.read()
    anchor = "## R589 · 2026-09-20 ·"
    assert anchor in it, "锚点缺失: improvements 无 R589 节"
    assert "## R590 · 2026-09-20 ·" not in it, "R590 节已存在 ⇒ 幂等跳过"
    it = it.replace(anchor, IMP_BLOCK + anchor, 1)
    with io.open(IMP, "w", encoding="utf-8") as fh:
        fh.write(it)

    # 3) 回读核对
    mt2 = io.open(MASTER, encoding="utf-8").read()
    it2 = io.open(IMP, encoding="utf-8").read()
    print("master bytes %d -> %d" % (before, len(mt2.encode("utf-8"))))
    for probe in ("R590（只读定因/入册轮", "下轮候选 (R591)", "候选② 否证"):
        print("master has %-28s %s" % (probe, probe in mt2))
    print("imp bytes -> %d" % len(it2.encode("utf-8")))
    for probe in ("## R590 · 2026-09-20 ·", "## R589 · 2026-09-20 ·", "NOT_LOAD_BEARING", "14/14"):
        print("imp has %-28s %s" % (probe, probe in it2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
