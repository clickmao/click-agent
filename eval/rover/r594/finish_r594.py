#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R594 收口器：台账行（幂等原地替换）+ 轮志 + §7 主报告块 + §7 运行状态快照刷新 + improvements 条目。

输入（全部为**在盘读数**，本器只做汇总与文档写入，不重算测量）：
  · eval/rover/r594/entry-contract-r594.json   （候选②）
  · eval/rover/r594/face-readings-r594.json    （候选③④⑤）
写入：
  · eval/capability/kpi.jsonl                  （键集与同族既有行逐字相同）
  · eval/rover/r594/report-r594.md
  · eval/rover/r594/finish-r594.json
  · docs/reports/iteration-master-plan.md      （追加 R594 块 + 下轮候选 (R595)）
  · docs/reports/dynamic-telemetry-eval-rollback-strategy.md（§7 快照「最近一轮」→ R594）
  · docs/improvements.md                       （顶部 +R594 节）
禁：git push / gh api 写 / 镜像上传；禁改任何判据阈值。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
EC = os.path.join(REPO, "eval/rover/r594/entry-contract-r594.json")
FR = os.path.join(REPO, "eval/rover/r594/face-readings-r594.json")
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")
MASTER = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
ROLLBACK = os.path.join(REPO, "docs/reports/dynamic-telemetry-eval-rollback-strategy.md")
IMPROV = os.path.join(REPO, "docs/improvements.md")
REPORT = os.path.join(REPO, "eval/rover/r594/report-r594.md")
FIN = os.path.join(REPO, "eval/rover/r594/finish-r594.json")
TS = "2026-09-20T13:05+08:00"


def load(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-docs", action="store_true")
    a = ap.parse_args()

    ec, fr = load(EC), load(FR)
    out = {"round": "R594", "ts": TS, "inputs": {"entry_contract": ec["rc"], "face_readings": fr["rc"]}}

    ag, cx = ec["sides"]["agent"], ec["sides"]["codex"]
    fam = fr["family_concentration"]
    concentrated = {k: v for k, v in fam.items() if v["concentration"] == "集中在单一跑次"}
    out["summary"] = {
        "candidate2_branch": "product_contract" if ec["verdict"]["branch_product_contract"] else "UNRESOLVED",
        "agent_runs_missing_solve": "%d/%d" % (ag["runs_missing"], ag["runs"]),
        "codex_runs_missing_solve": "%d/%d" % (cx["runs_missing"], cx["runs"]),
        "two_sided_strong_criterion": ec["verdict"]["two_sided_strong_criterion_holds"],
        "statement_entry_required": ec["face_statement_vs_judge"]["statement_entry_name_required"],
        "judge_same_source": ec["face_statement_vs_judge"]["same_source"],
        "candidate3_v_int": "5 窗集分层直方图落盘；阈值化未测（需新跑次）",
        "candidate4_w154_codex_only_b": fr["w154"]["codex_only_b_holds"],
        "candidate5_families_concentrated": "%d/%d" % (len(concentrated), len(fam)),
    }

    # ---------- 轮志 ----------
    report = """# R594 轮志 — 入口契约面只读定因（候选②）+ 面读数并轮（候选③④⑤）

**轮次性质**：只读定因并轮。零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关。
**被测对象**：在盘快照树（59 跑次 × 4 模块）+ 冻结用例集 `cases-r521.json`（逐字节不变）。
**预注册/DAG**：`eval/rover/r594/{prereg-r594.json,dag-r594.md}`（起手前落盘）。

## 候选② 入口契约面（决定性读数）

| 面 | 读数 | 器具 |
|---|---|---|
| 题面 | 要求 `solve(text: str) -> str` = **True**；评分路径 `python3 -m games` ×2 | `entry-contract-r594.json::face_statement_vs_judge` |
| 判分器 | 实发 argv `-B -m games`（同源）∧ **无**直接导入 | 同上（源码抽取，非人工） |
| 两侧 census | agent **2/44** 跑次缺 `solve`（均仅 `wythoff`）vs codex **0/15** | `sides` / `missing_runs` |
| 实测复现 | 2 跑次 rc=1 ∧ stderr 尾行 `AttributeError: module 'games.wythoff' has no attribute 'solve'`；对照跑次 rc=0 | `replay` |

**裁定**：`branch_product_contract = True` / `branch_fixture_defect = False` ——
两个缺入口跑次**自己的** `__main__.py` 都调用 `.solve`（`main_calls_solve=true`）而其**自己的** `wythoff.py`
只定义 `_win`/`_lose`（无 `solve`）⇒ **产物自身契约自相矛盾**；题面已写明入口名、判分路径与题面同源 ⇒
题面/夹具分支被**否证**；两侧同败强判据（codex 侧 0/15）**不成立** ⇒ 不判夹具/题面缺陷。

## 候选③④⑤ 面读数（纯聚合，零子进程）

- **③ `V_int` 按窗集分层**：15 个窗集 × 两侧直方图落盘；交叉校验 `cold_set_equal ∧ V_int>0` = **0/59**；
  2×2 列联：agent `(T,0)=19 / (F,pos)=19 / (F,0)=6`、codex `(T,0)=11 / (F,pos)=4` ⇒
  **V_int>0 恒伴随冷集不等**（两侧皆然）。**阈值化 = 未测**（需新跑次）。
- **④ codex 独有 (b) 窗 `w154`**：codex 声明冷集 **51** vs 真值 **10**（多 41，形如整行 `(0,1..6)` 被判冷）⇒
  层 `(b) 冷集构造层`、13/15 通过、2 例 `B_coldset`；同窗 3 个 agent 跑次全 **15/15** 且层 `(c)` ⇒
  **该窗缺口属 codex 侧，非我方缺陷**（`codex_only_b_holds = True`，逐字段复算与登记层一致）。
- **⑤ 形态族集中度**（预注册机械规则：top-run 份额 ≥ 0.5 ⇒ 集中）：5 族中 **4 族集中**、
  1 族（`TypeError: 'NoneType'...`，n=11 / 4 跑次，份额 0.455）**散布** ⇒
  「执行面崩溃/挂死」形态**按跑次成簇**（`AttributeError` 30 = 2 跑次、`TIMEOUT` 8 = 1 跑次、
  `%d format` 2 = 1 跑次），不是跨跑次普遍形态。

## 零回归 / 只读性 / 器具自捕

- **零回归对照臂**：由同一件 R593 在盘 JSON 重算 A/B 级桶（`B_coldset 184 / A_landing_loose 20 /
  A_selection_order 6`）、层分布（`(b)22/(c)19/(a)3`）、`d_subs`（`D1 66 / D3 3`）、两侧 `V_int` 直方图
  ⇒ 与该轮登记值**逐位复现**；另断言 `D_delivery_or_shape == d_total = 69`。
- **只读性**：59 跑次快照树（`g1` 子树 `.py`）+ 冻结用例集 sha256 前后一致（`411434e5f8939c3b`）；
  控制只写 `/tmp` 副本。**确定性 ×2** 逐位相同。
- **器具自捕 2 件（零判据放宽、首跑留档不翻案）**：
  ① `entry_contract_r594` v1 **路径层级错**（census 传 `g1` 而非 `g1/games`）⇒ 全跑次「全 missing」，
  与同轮 POS 控制**直接矛盾**；修法 = **单点路径构造** + 新增「非平凡性」机检（全跑次面须有 present 模块），
  留档 `entry-contract-r594-v1pathbug.json`；
  ② `face_readings_r594` 首跑**打印面 KeyError**（读数面键名与打印面键名分叉）⇒ 修打印面不改读数面，
  留档 `face-readings-r594-v1printbug.json`；扩展 2×2 列联前的中间版留档 `face-readings-r594-v2.json`。

## 门禁 / 铁律 11

- **形式门禁**：`dotnet test … --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒
  **Failed 0 / Passed 14 / Skipped 0**。
- **铁律 11**：`python3 eval/rover/r507pre/exec_precondition.py --round r594` ⇒ **rc=3 DISCOVER_FAIL**
  （零新臂 ⇒ 前置器不适用）⇒ **不作任何降幅/增益宣称；tokens 三列 = 未测**。
- 零 `src/` 改动、零登记表改动 ⇒ 依 R588–R593 同处置**不造** capability 登记行。

## 诚实边界

1. 只读产物诊断 ⇒ **不构成能力验收**，不得回写成「产品已修」；
2. 候选②的 2 个缺入口跑次属**产物侧**契约自相矛盾，但**产品侧修复仍待用户放行**（候选①）；
3. `V_int` **阈值化未测**（需新跑次），本轮只出分布与列联；
4. 形态族集中度为**跑次级**统计（44 agent 跑次横跨 5 窗集）⇒ 非独立样本；
5. 跨轮**禁相减**：R593 读数只用于零回归对照臂的逐位复现；
6. `w154` 的 (b) 属 codex 侧 ⇒ 不得计入我方缺陷份额。
"""
    with io.open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(report)

    # ---------- 台账行（幂等原地替换） ----------
    readings = {
        "round": "R594", "ts": TS,
        "candidate2_entry_contract": {
            "statement_entry_required": ec["face_statement_vs_judge"]["statement_entry_name_required"],
            "judge_same_source": ec["face_statement_vs_judge"]["same_source"],
            "agent_missing": "%d/%d" % (ag["runs_missing"], ag["runs"]),
            "codex_missing": "%d/%d" % (cx["runs_missing"], cx["runs"]),
            "missing_runs": [m["run"] for m in ec["missing_runs"]],
            "branch_product_contract": ec["verdict"]["branch_product_contract"],
            "branch_fixture_defect": ec["verdict"]["branch_fixture_defect"],
            "two_sided_strong": ec["verdict"]["two_sided_strong_criterion_holds"],
            "replay": ec["replay"], "teeth": ec["teeth"]["has_teeth"],
            "non_trivial": ec["non_trivial"]["ok"], "readonly": ec["readonly"]["ok"],
        },
        "candidate3_v_int": {"window_sets": len(fr["v_int_by_window_set"]),
                             "cross_check_cold_eq_and_pos": fr["v_int_cross_check"]["cold_equal_and_vint_pos_runs"],
                             "contingency": fr["v_int_vs_cold_equal"],
                             "threshold_status": "未测（需新跑次）"},
        "candidate4_w154": {"codex_layer": fr["w154"]["codex_layer"],
                            "agent_layers": fr["w154"]["agent_layers"],
                            "codex_only_b_holds": fr["w154"]["codex_only_b_holds"]},
        "candidate5_family_concentration": {k: {"n": v["n"], "runs": v["runs"],
                                                "top_share": v["top_share"], "verdict": v["concentration"]}
                                            for k, v in fam.items()},
        "zero_regression": fr["zero_regression"]["match"],
        "determinism_x2": fr["determinism_x2"],
        "form_gate": "14/14 (Failed 0 / Passed 14 / Skipped 0)",
        "iron_law_11": "exec_precondition --round r594 ⇒ rc=3 DISCOVER_FAIL（零新臂 ⇒ 不适用；不宣称降幅）",
        "tokens": "未测（零远端调用）",
    }
    row = {
        "round": "R594", "ts": TS,
        "kind": "入口契约面只读定因（候选②）+ 面读数并轮（候选③④⑤）：题面/夹具分支否证（产物侧契约自相矛盾）；V_int 分布面扩到 5 窗集；codex 独有 (b) 窗定因；形态族按跑次集中度。零新臂 / 零远端 / 零产品源码改动 / 零新增夹具语义 / 零新增开关",
        "change": ("① `eval/rover/r594/entry_contract_r594.py`（题面抽取 + 判分器 argv 同源检查 + 全跑次面 `def solve` census（两侧分列）+ 实测复现 + POS/NEG 副本控制；单点路径构造 + 非平凡性机检）；"
                   "② `eval/rover/r594/face_readings_r594.py`（纯聚合：V_int 按窗集分层 + 2×2 列联 / codex w154 逐字段复算并按 R592 层规则重算 / 形态族 × 跑次集中度；零回归对照臂逐位复现 R593 登记值）；"
                   "③ 轮志 + 台账 + §7 主报告块 + §7 运行状态快照 + improvements 条目。器具自捕 2 件（路径层级错 ⇒ 全 missing 假读数；打印面 KeyError）均留档不翻案、未放宽判据。"),
        "readings": readings,
        "artifact": "eval/rover/r594/{report-r594.md,prereg-r594.json,dag-r594.md,entry-contract-r594.json,face-readings-r594.json,entry-contract-r594-v1pathbug.json,face-readings-r594-v1printbug.json,face-readings-r594-v2.json} · docs/reports/iteration-master-plan.md §7 R594 块 · docs/reports/dynamic-telemetry-eval-rollback-strategy.md §7 快照",
    }
    lines = io.open(LEDGER, encoding="utf-8").read().splitlines()
    kept, replaced = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            kept.append(ln)
            continue
        if d.get("round") == "R594":
            replaced += 1
            continue
        kept.append(ln)
    kept.append(json.dumps(row, ensure_ascii=False))
    with io.open(LEDGER, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kept) + "\n")
    out["ledger"] = {"rows_before": len(lines), "rows_after": len(kept), "replaced_same_round": replaced}

    if not a.no_docs:
        # ---------- §7 主报告块 ----------
        block = (
            "\n- **R594（只读定因并轮：入口契约面（候选②）+ 面读数并轮（候选③④⑤）；零新臂 / 零远端调用 / "
            "零产品源码改动 / 零新增夹具语义 / 零新增开关）**: **修改点** ① `eval/rover/r594/entry_contract_r594.py`"
            "（题面原文抽取入口名/评分路径 + 判分器源码 argv 同源检查 + **全跑次面** `def solve` census（agent/codex 分列）"
            "+ 实测复现 + POS/NEG 副本控制 + 单点路径构造 + 非平凡性机检）；② `eval/rover/r594/face_readings_r594.py`"
            "（纯聚合：`V_int` 按窗集分层 + 2×2 列联 / codex `w154` 逐字段复算 + 层规则重算 / 形态族 × 跑次集中度；"
            "零回归对照臂与 R593 登记值**逐位复现**）；③ 轮志/台账/§7 块/§7 快照/improvements。"
            "**真机读数**：**候选② 入口契约面**（决定性）—— 题面明文要求 `solve(text: str) -> str`（True）∧ 评分路径 "
            "`python3 -m games`（×2）∧ 判分器实发 argv `-B -m games`（**同源**）∧ 判分器**无**直接导入；"
            "两侧 census **agent 2/44** 跑次缺 `solve`（均仅 `wythoff`，`r588/w163/agentD-r2`、`r591/w166/agentD-r2`）"
            "vs **codex 0/15**；实测复现两跑次 rc=1 ∧ stderr 尾行 `AttributeError: module 'games.wythoff' has no attribute 'solve'`，"
            "对照跑次 `r585/w154/agentD-r1` rc=0 ⇒ **裁定 `branch_product_contract=True` / `branch_fixture_defect=False`**："
            "两跑次**自己的** `__main__.py` 都调用 `.solve` 而其**自己的** `wythoff.py` 只定义 `_win`/`_lose` ⇒ "
            "**产物自身契约自相矛盾**；题面/夹具分支被否证，两侧同败强判据（codex 0/15）**不成立** ⇒ 不判夹具/题面缺陷。"
            "**候选③**：`V_int` 按 15 窗集 × 两侧分层直方图落盘；交叉校验 `cold_set_equal ∧ V_int>0` = **0/59**；2×2 列联 "
            "agent `(T,0)=19/(F,pos)=19/(F,0)=6`、codex `(T,0)=11/(F,pos)=4` ⇒ **V_int>0 恒伴随冷集不等**；**阈值化未测**（需新跑次）。"
            "**候选④**：codex 独有 (b) 窗 `w154` 确为 (b) —— codex 声明冷集 **51** vs 真值 **10**（多 41，形如整行 `(0,1..6)` 被判冷）、"
            "13/15 通过、2 例 `B_coldset`；同窗 3 个 agent 跑次全 **15/15** 且层 `(c)` ⇒ 该窗缺口**属 codex 侧**（不得计入我方份额）。"
            "**候选⑤**：5 形态族中 **4 族 top-run 份额 ≥0.5（集中在单一跑次）**、1 族（`TypeError:'NoneType'` n=11/4 跑次，份额 0.455）散布 ⇒"
            "「执行面崩溃/挂死」形态**按跑次成簇**（`AttributeError` 30 = 2 跑次 / `TIMEOUT` 8 = 1 跑次 / `%d` 2 = 1 跑次）。"
            "**零回归/只读性**：A/B 级桶 `B_coldset 184 / A_landing_loose 20 / A_selection_order 6`、层 `(b)22/(c)19/(a)3`、"
            "`d_subs D1 66 / D3 3`、两侧 `V_int` 直方图与 R593 登记值**逐位复现**，`D_delivery_or_shape == d_total = 69`；"
            "59 跑次快照树 + 冻结用例 sha 前后一致（`411434e5f8939c3b`）；确定性 ×2 逐位相同。"
            "**器具自捕 2 件（零判据放宽、首跑留档不翻案）**：① `entry_contract_r594` v1 **路径层级错**（census 传 `g1` 而非 `g1/games`）"
            "⇒ 全跑次「全 missing」，与同轮 POS 控制直接矛盾 ⇒ 修法 = 单点路径构造 + 非平凡性机检（留档 `entry-contract-r594-v1pathbug.json`）；"
            "② `face_readings_r594` 首跑**打印面 KeyError**（读数面/打印面键名分叉）⇒ 修打印面不改读数面（留档 `face-readings-r594-v1printbug.json`；"
            "扩展列联前中间版 `face-readings-r594-v2.json`）。**形式门禁** **14/14**（Failed 0 / Passed 14 / Skipped 0）。"
            "**铁律 11**：`exec_precondition --round r594` ⇒ **rc=3 DISCOVER_FAIL**（零新臂 ⇒ 前置器不适用）⇒ "
            "**不作任何降幅/增益宣称；tokens 三列 = 未测**。零 `src/` 改动、零登记表改动 ⇒ 依 R588–R593 同处置**不造** capability 登记行。"
            "**诚实边界**：① 只读产物诊断 ⇒ 不构成能力验收、不得回写成「产品已修」；② 候选②定因到位但**产品侧修复仍待用户放行**（候选①）；"
            "③ `V_int` 阈值化**未测**；④ 形态族集中度为**跑次级**统计（44 agent 跑次横跨 5 窗集）⇒ 非独立样本；"
            "⑤ 跨轮**禁相减**（R593 读数只用于零回归对照臂）；⑥ `w154` 的 (b) 属 codex 侧 ⇒ 不计我方缺陷份额。"
            "轮志 `eval/rover/r594/report-r594.md`、预注册/DAG `eval/rover/r594/{prereg-r594.json,dag-r594.md}`、"
            "读数 `eval/rover/r594/{entry-contract-r594.json,face-readings-r594.json}`、台账 `eval/capability/kpi.jsonl`（R594）。\n"
            "\n- **下轮候选 (R595)**: ① **本轴处置裁定（待用户放行）**：候选②已把「缺入口」定因到**产物侧契约自相矛盾**、候选④已排除 codex 窗 ⇒ "
            "产品侧修复（`src/` 或题面外契约面）**须用户放行** ② **`wythoff` 冷集构造层定因继续下沉**：从 R592 的 `B_coldset 184（0.6595）` 出发，"
            "只读量「声明冷集 vs 真值冷集的集合差结构」（超出/缺失的方向与形态），判「Beatty 判定错」还是「边界处理错」 ③ **候选② 的姊妹面**："
            "对**交付物自洽性**做只读普查（`__main__` 引用 vs 模块导出、4 模块 × 59 跑次的**契约一致性**，含非 `solve` 面）——"
            "本轮只查了 `solve` 单键 ④ `V_int` 阈值化前的**第二窗集分布**（须新跑次 ⇒ 真机臂轮，与主线对照合并跑） ⑤ 起手闸只读轮分支余量按 R594 实测派生。\n"
        )
        with io.open(MASTER, "a", encoding="utf-8") as fh:
            fh.write(block)
        out["master_appended"] = True

        # ---------- §7 运行状态快照（最近一轮 → R594；R593 转历史快照） ----------
        rb = io.open(ROLLBACK, encoding="utf-8").read()
        anchor = "> - **最近一轮（R593，2026-09-20 · cron 60min tick）**:"
        if anchor in rb:
            newline = ("> - **最近一轮（R594，2026-09-20 · cron 60min tick）**: **入口契约面只读定因（候选②）+ 面读数并轮（候选③④⑤）**"
                       " —— 零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关。**候选②（决定性）**：题面明文要求 "
                       "`solve(text: str) -> str` ∧ 评分走 `python3 -m games` ∧ 判分器实发 argv `-B -m games`（同源）∧ **无**直接导入；"
                       "两侧 census **agent 2/44** 跑次缺 `solve`（均仅 `wythoff`）vs **codex 0/15**；实测复现 rc=1 ∧ "
                       "`AttributeError: module 'games.wythoff' has no attribute 'solve'`，对照跑次 rc=0 ⇒ **产物侧契约自相矛盾**，"
                       "题面/夹具分支**否证**、两侧同败强判据**不成立**。**候选③**：`V_int` 15 窗集 × 两侧分层直方图 + 2×2 列联落盘；"
                       "交叉校验 `cold_set_equal ∧ V_int>0` = **0/59**；**阈值化未测（需新跑次）**。**候选④**：codex 独有 (b) 窗 `w154` 定因 = "
                       "声明冷集 **51** vs 真值 **10**（13/15 通过、2 例 `B_coldset`），同窗 3 个 agent 跑次全 **15/15** ⇒ **属 codex 侧**。"
                       "**候选⑤**：5 形态族中 **4 族集中在单一跑次**（`AttributeError` 30 = 2 跑次 / `TIMEOUT` 8 = 1 跑次 / `%d` 2 = 1 跑次），"
                       "`TypeError:'NoneType'`（n=11/4 跑次，份额 0.455）散布。**零回归**：A/B 桶 184/20/6、层 22/19/3、`d_subs 66/3`、"
                       "两侧 `V_int` 直方图与 R593 登记值**逐位复现**；只读性 sha 前后一致；确定性 ×2。**器具自捕 2 件**（路径层级错 ⇒ 全 missing 假读数；"
                       "打印面 KeyError）留档不翻案。**形式门禁 14/14**；**铁律 11 rc=3**（零新臂 ⇒ 不适用；**tokens 三列未测**、不宣称降幅）。"
                       "轮志 `eval/rover/r594/report-r594.md`。\n")
            rb = rb.replace(anchor, newline + "> - **最近一轮（R593，2026-09-20 · cron 60min tick）**【历史快照，已被上方 R594 行取代】:", 1)
            with io.open(ROLLBACK, "w", encoding="utf-8") as fh:
                fh.write(rb)
            out["rollback_updated"] = True
        else:
            out["rollback_updated"] = False

        # ---------- improvements 顶部节 ----------
        imp = io.open(IMPROV, encoding="utf-8").read()
        m = re.search(r"\n## R59\d", imp)
        sec = (
            "\n## R594 · 2026-09-20 · 状态: **完成（两器具 rc=0；候选②定因到位、③④⑤面读数落盘；形式门禁 14/14）· 只读定因并轮**"
            " · 主题: **入口契约面（缺 `solve`）定因 = 产物侧契约自相矛盾（题面/夹具分支否证）× `V_int` 分布面扩到 5 窗集 × codex 独有 (b) 窗定因 × 形态族按跑次集中度**\n\n"
            "- **候选②（决定性）**: 题面明文要求 `solve(text: str) -> str` ∧ 评分跑 `python3 -m games` ∧ 判分器实发 argv 同源 ∧ 无直接导入；"
            "census **agent 2/44**（均仅 `wythoff`：`r588/w163/agentD-r2`、`r591/w166/agentD-r2`，其**自己的** `__main__.py` 调 `.solve` 而**自己的** "
            "`wythoff.py` 无 `solve`）vs **codex 0/15**；实测复现 rc=1 ∧ `AttributeError: module 'games.wythoff' has no attribute 'solve'` ⇒ "
            "**产物自身契约自相矛盾**；两侧同败强判据不成立 ⇒ **不判夹具/题面缺陷**。\n"
            "- **候选③**: `V_int` 15 窗集 × 两侧直方图 + 2×2 列联；`cold_set_equal ∧ V_int>0` = **0/59**；**阈值化未测（需新跑次）**。\n"
            "- **候选④**: `w154` codex 声明冷集 51 vs 真值 10（13/15）、同窗 agent 3 跑次全 15/15 ⇒ 缺口**属 codex 侧**。\n"
            "- **候选⑤**: 5 族中 4 族集中在单一跑次（份额 ≥0.5）⇒ 执行面崩溃/挂死形态**按跑次成簇**。\n"
            "- **器具自捕 2 件**: 路径层级错 ⇒ 全 missing 假读数（与 POS 控制矛盾，修法=单点路径构造+非平凡性机检）/ 打印面 KeyError；"
            "均留档不翻案、未放宽判据。\n"
            "- **边界**: 只读诊断 ⇒ 不构成能力验收；产品侧修复**待用户放行**；`V_int` 阈值化未测；跨轮禁相减。\n"
            "- 轮志 `eval/rover/r594/report-r594.md`、预注册 `prereg-r594.json`、DAG `dag-r594.md`、台账 `eval/capability/kpi.jsonl`（R594）。\n"
        )
        if m:
            imp = imp[:m.start()] + sec + imp[m.start():]
        else:
            imp = imp + sec
        with io.open(IMPROV, "w", encoding="utf-8") as fh:
            fh.write(imp)
        out["improvements_updated"] = True

    with io.open(FIN, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=1))
    print("ledger", out["ledger"], "docs", out.get("master_appended"), out.get("rollback_updated"), out.get("improvements_updated"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
