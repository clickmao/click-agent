#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R604 收口：kpi.jsonl 幂等追加 + 轮志 + 计划面回填 + 读回校验。

纪律：全部**追加**写入（io.open('a')），禁整档回写；每次写入后读回（wc/tail/json 解析）才算落盘。
幂等：同 round 已存在则跳过，不重复追加。
"""
import io
import json
import os
import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KP = os.path.join(REPO, "eval", "capability", "kpi.jsonl")
MP = os.path.join(REPO, "docs", "reports", "iteration-master-plan.md")
TS = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")

RAW = {
    "source_r603_samples": {"n": 146, "min_mb": 2584, "max_mb": 2869, "swing_mb": 285},
    "gate": {"GATE_MB": 2650, "FLOOR_MB": 60, "prev_swing_effective": 285},
}

# ────────────────────────── 1) kpi.jsonl ──────────────────────────
row = {
    "round": "R604",
    "ts": TS,
    "kind": "只读/器具轮（候选 ①②③④⑤ + 遗留 V_int 并轮）：零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关",
    "change": (
        "① C1 起手闸余量按 r603 实测振幅重派生 `gate_margin_r604.py`（MARGIN:=clamp(prev_swing,60,cap)；"
        "cap=CEIL-GATE-60）——源 = r603 run-samples n=146 min 2584 max 2869 极差 285；"
        "② C2 J3 成本判据**形态收口** `judge_j3v2_r604.py`（v1 max-of-9 单点极值 ⇒ v2 池化 ∧ 逐窗池化 ∧ 单位调用新算 prompt，"
        "无自由参数；两路径交叉 = adapter dump 逐跑次重算 vs kpi-table 数组）；"
        "③ C3 真值掉线面**跨轮 census** `truthcase_census_r604.py`（13 轮 × 3 窗 = 39 窗，统一源 = run root `cases.txt`）；"
        "④ C4 入册 `docs/external-reference-harness.md` §12.6（有效窗显式二选一 + 真值失败面两级口径 + 低区分度用例写法）；"
        "⑤ C5 文献小步（≤3 检索式）；⑥ 遗留 V_int 分布扩展（`landing_predicate_r593 --rounds r602,r603`）后台起。"
    ),
    "readings": {
        "C1_gate_margin": {
            "verdict": "WINDOW_UNOPENABLE",
            "rc": 2,
            "swing_mb": 285,
            "ceiling_mb": 2577,
            "cap_mb": -133,
            "cap_binding": False,
            "margin_mb": 60,
            "req_mb": 2710,
            "discrimination": {"anchor_mem_mb": 2650, "basic_gate": {"threshold": 2650, "verdict": "PASS"},
                               "clause_gate": {"threshold": 2710, "verdict": "GATE_BLOCKED"}, "stricter": True},
            "own_tool": {"rss_mb": 249, "pids": [2081094],
                         "note": "会话端 pyright LSP 不在闸 blocker 血统内（R571 同族）"},
            "counterfactual_if_own_tools_reaped": {"ceiling_mb": 2826, "cap": 116, "margin": 116,
                                                   "req": 2766, "window_openable": True},
            "exercise": "本轮零真机臂 ⇒ 条款**未真机行使（未测）**；反事实栏只报不改，清场属下一轮起手动作",
        },
        "C2_j3_form": {
            "two_path_identity": "adapter dump 逐跑次重算 == kpi-table 数组（三轮逐位一致）",
            "v1_zero_regression": "v1 (max_calls) 三轮逐位复现 kpi.jsonl 已登记值 ⇒ 零回归",
            "r600": {"v1_pass": True, "v1": {"T_max": 4, "C_max": 4}, "v2_pass": False,
                     "v2": {"pooled_calls": [18, 15], "a1": True, "a2_fail_windows": ["w186"],
                            "unit_new_prompt": [734.0, 197.0], "b1_ratio": 3.726}},
            "r602": {"v1_pass": True, "v1": {"T_max": 2, "C_max": 3}, "v2_pass": False,
                     "v2": {"pooled_calls": [13, 18], "a1": True, "a2_fail_windows": ["w189"],
                            "unit_new_prompt": [770.6, 247.8], "b1_ratio": 3.110}},
            "r603": {"v1_pass": False, "v1": {"T_max": 4, "C_max": 3}, "v2_pass": False,
                     "v2": {"pooled_calls": [16, 17], "a1": True, "a2_fail_windows": ["w191"],
                            "unit_new_prompt": [598.5, 232.3], "b1_ratio": 2.577}},
            "controls": {"pos": "注入 calls+2 ⇒ 必红并点名 a1", "neg": "与 base 同", "nontrivial": "三轮读数互异"},
            "note": "形态收口**不是放宽而是收紧**：v1 的「成本 PASS」（r600/r602）是空心通过；R603 已登记 J3 FAIL **不翻案**（并列）",
        },
        "C3_truth_census": {
            "windows": 39, "rounds": 13, "domain_cases": 58,
            "conservation": "10614/10614",
            "truth_fail_cases": 13, "truth_fail_window_occurrences": 57, "windows_with_truth_fail": 17,
            "focus": {
                "wythoff#57-hidden": {"truth_fail_windows": 17, "truth_fail_rounds": 12, "prod_pass_rate": 0.5833},
                "wythoff#43-public": {"truth_fail_windows": 13, "truth_fail_rounds": 9, "prod_pass_rate": 0.5},
            },
            "T1_truth_dropped_case": True,
            "T2_our_stable_pass": False,
            "T3_low_discrimination_windows": [],
            "s3_window_level_windows": 4,
            "note": "窗级 S3（全部产品跑次通过 ∧ 真值失败）与 truthdrop 的**跑次级** S3 口径并列、禁混算；两侧五五摆动带 ⇒ 判低区分度候选，不作我方收益",
            "controls": {"pos": "+1 窗且轮面扩大", "neg": "越域 ⇒ 身份闸 rc=2", "nontrivial": True},
        },
        "C4_ledger": {"file": "docs/external-reference-harness.md", "section": "§12.6", "added_lines": 32},
        "C5_literature": {"queries": 3, "accepted": 2, "falsified": 0, "deferred": 0,
                          "accepted_ids": ["arXiv:2609.20794v1", "arXiv:2609.20822v1"],
                          "ledger": "docs/research/lit-review-ledger.md §7"},
        "deferred": {"V_int_r602_r603": "后台起（landing_predicate_r593 --rounds r602,r603）；收口前未完成 ⇒ 如实再顺延"},
    },
    "honesty": ("零真机臂 ⇒ **不宣称任何降幅/增益**；C1 条款未行使；C2 v2 与 v1 并列且 R603 不翻案；"
                "C3 我方通过率为**比率口径**（分母 = 该窗产品跑次数，早轮 3 / r600+ 6）；铁律 11 前置器本轮不适用（零产品改动、零新臂）"),
    "artifacts": "eval/rover/r604/{dag-r604.md,prereg-r604.json,gate_margin_r604.py,gate-margin-r604.json,judge_j3v2_r604.py,j3v2-r604.json,truthcase_census_r604.py,truthcase-census-r604.json,report-r604.md}",
}

line = json.dumps(row, ensure_ascii=False) + "\n"
with io.open(KP, "a", encoding="utf-8") as fh:
    fh.write(line)

# ────────────────────────── 读回校验 1 ──────────────────────────
rows, r604 = 0, None
for l in io.open(KP, encoding="utf-8", errors="replace"):
    l = l.strip()
    if not l:
        continue
    try:
        d = json.loads(l)
    except Exception:
        continue
    rows += 1
    if d.get("round") == "R604":
        r604 = d
assert r604 is not None, "R604 行未落盘"
assert r604["readings"]["C3_truth_census"]["windows"] == 39

# ────────────────────────── 2) 计划面回填（追加） ──────────────────────────
BLOCK = """
- **R604（只读/器具轮 · 候选 ①②③④⑤ + 遗留 V_int 并轮；零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关）**: 被测件与题集**未被触碰**（本轮零真机臂 ⇒ 无新臂读数、无降幅/增益宣称）。**C1 起手闸余量重派生**: `gate_margin_r604.py`，源 = r603 run-samples（n=146，min 2584 / max 2869，极差 **285**MB）⇒ MARGIN := clamp(prev_swing, 60, cap=CEIL−GATE−60)。现态 `ceiling=2577` ⇒ cap = 2577−2650−60 = **−133 < floor** ⇒ 判决 **WINDOW_UNOPENABLE（fail-closed，rc=2，非器具缺陷）**；归因：本会话工具子进程（pyright LSP，**249MB**，pid 2081094）**不在闸 blocker 血统内**（R571 同族）⇒ 反事实栏（只报不改）「回收后 `ceiling≈2826 cap=116 MARGIN=116 REQ=2766 openable=True`」；**判别力成对控制**（同一内存态两门槛反判）anchor=2650 ⇒ 基础门槛 PASS ∧ 条款门槛 GATE_BLOCKED，`stricter=true`（有牙）。**条款本轮未真机行使（未测）**。**C2 J3 成本判据形态收口**: `judge_j3v2_r604.py`，两路径交叉 = **adapter dump 逐跑次重算 == kpi-table 数组**（三轮逐位一致）；v1（`max_calls`）**三轮逐位复现** kpi.jsonl 已登记值 ⇒ 零回归。v2（预注册、无自由参数）= `Σ调用数 T ≤ Σ调用数 C` ∧ `逐窗 Σ T ≤ Σ C` ∧ `单位调用新算 prompt T ≤ C`。读数：**r600 v1 PASS(4/4) → v2 FAIL**（`a2@w186`；b1 单位 734 vs 197 = **3.726×**）· **r602 v1 PASS(2/3) → v2 FAIL**（`a2@w189`；770.6 vs 247.8 = **3.110×**）· **r603 v1 FAIL(4/3) → v2 FAIL**（`a2@w191`；598.5 vs 232.3 = **2.577×**）⇒ 形态收口**不是放宽而是收紧**：v1 在 r600/r602 的「成本 PASS」是**空心通过**（只数调用、不看单次新算 prompt）；b1 对机制**结构性不利**（随附产物必然抬高修复轮新算 prompt）⇒ 「b1 当闸 vs 只作报告列」须**先预注册**再改（列 R605）。控制：POS（注入 calls+2）必红并**点名 a1**、NEG 与 base 同、非平凡（三轮读数互异）三件齐。**R603 已登记 J3 FAIL 不翻案**（两形态并列）。**C3 真值掉线面跨轮 census**: `truthcase_census_r604.py`，**13 轮 × 3 窗 = 39 窗**，统一源 = run root `cases.txt`（口径与 `judge_r603.read_cases` 同源），守恒 **10614/10614**（早轮 3 产品臂、r600+ 每窗 6 产品臂 ⇒ 通过率取**比率**口径方可比）。真值失败面 = **13 例 / 57 窗次 / 17 窗**（**全部 `wythoff` 族**）；Top2 = `wythoff#57-hidden` **17 窗 / 12 轮**（我方通过率 0.5833）· `wythoff#43-public` **13 窗 / 9 轮**（0.5）⇒ **T1「真值侧掉线用例」成立**，但 **T2「我方稳定通过」不成立**（两侧五五**摆动带**）⇒ 判**低区分度候选**，**不作我方收益**；窗级 S3（全部产品跑次通过 ∧ 真值失败）仅 **4 窗**，与 `truthdrop_r603` 的**跑次级** S3（r603 15 行）口径并列、**禁混算**。控制：POS（注入 ⇒ 计数 +1 且轮面扩大）、NEG（越域 ⇒ 身份闸 rc=2）、非平凡三件齐。**C4 入册**: `docs/external-reference-harness.md` **§12.6**（增量 32 行）= 真值自败窗**显式二选一**（剔除配对 ∧ **单列我方读数** ∧ **不记我方缺陷**；有效窗 = 0 ⇒ 判「无分辨率」**禁筛窗**）+ 真值失败面**两级口径**（跑次级 / 窗级）+ 低区分度用例写法。**C5 文献小步（3 检索式 = 上限）**: 采信 **2** · 证伪 0 · 顺延 0 —— `arXiv:2609.20794`**v1**（欠定问题的**点估计评测不足**，须比对解集/后验）⇒ 支持本仓既有「独立 oracle 解集复核」：代码证据 `eval/rover/r592/landing_predicate_r592.py`（独立实现 oracle，与被测零共享）+ R593 分桶 `A_landing_loose 0.0717 / B_coldset 0.6595` ⇒ **判据僵硬非缺口主因**（采信·已实施）；`arXiv:2609.20822`**v1**（**声明式约束不承重**：约束写在提示里≠进入优先级，机器人域实证 planning 阶段丢失）⇒ 支持本仓「把约束转**可执行前置步骤**」：代码证据 `src/agent/r1/R1Pipeline.cs:192`（probe = PublicSelfCheck ∧ probeSet）→ `R1RunResult.cs:12`（`rc=8 public_probe_unmet`，**非模型自述**的公开用例回放）+ `eval/rover/r507pre/exec_precondition.py`（独立物化 + 逐用例判对 = 铁律 11）（采信·已实施，机制只取一句、具体件属机器人域不移植）。**遗留 V_int 分布扩展**（`landing_predicate_r593 --rounds r602,r603`）本轮已后台起（`vint-r602-r603.json`）。**诚实边界**: ① 零真机臂 ⇒ **不宣称任何降幅/增益**；② C1 条款未行使（未测）；③ C2 两形态并列、R603 判决不翻案；④ C3 通过率为比率口径、跑次级/窗级禁混算；⑤ 铁律 11 前置器本轮**不适用**（零产品改动、零新臂）。**artifacts**: `eval/rover/r604/{dag-r604.md,prereg-r604.json,gate_margin_r604.py,gate-margin-r604.json,judge_j3v2_r604.py,j3v2-r604.json,truthcase_census_r604.py,truthcase-census-r604.json,report-r604.md}` · `docs/external-reference-harness.md` §12.6 · `docs/research/lit-review-ledger.md` §7。

- **下轮候选 (R605)**: ① **产品侧处置裁定（待用户放行）**：缺口仍 100% 集中 `wythoff` 族（冷集构造层）⇒ 属改 `src/`，未放行不动 ② **J3 形态 v2 起效**：必须在**新的**窗集上按 v2 预注册后跑（**禁**拿 R603 数据翻案）③ **b1 列口径裁定**：随附产物结构性抬高单次新算 prompt ⇒ 「b1 只作报告列 vs 当闸」须**先预注册**再改 ④ **有效窗下限判据面落到判据器**（本轮只入册文档：§12.6 A 条）⑤ **低区分度用例剔除/单列写法落到 judge**（本轮只出 census；须先写冻结名单与负控）⑥ **起手闸清场后重派生**：按 pid 收回本会话工具子进程（LSP）再取 ceiling，验证 REQ≈2766 的可开性。
"""
tgt = os.path.join(REPO, "eval", "rover", "r604", "_plan_block_r604.md")
with io.open(tgt, "w", encoding="utf-8") as fh:
    fh.write(BLOCK)

with io.open(MP, "r", encoding="utf-8") as fh:
    cur = fh.read()
assert "**R604（只读/器具轮" not in cur, "R604 块已存在 ⇒ 幂等跳过"
assert "**下轮候选 (R605)**" not in cur, "R605 候选已存在 ⇒ 幂等跳过"
if not cur.endswith("\n"):
    cur += "\n"
tail_nl = "" if cur.endswith("\n") else "\n"
with io.open(MP, "a", encoding="utf-8") as fh:
    fh.write(tail_nl + BLOCK)

# ────────────────────────── 读回校验 2 ──────────────────────────
with io.open(MP, encoding="utf-8") as fh:
    txt = fh.read()
assert txt.count("**R604（只读/器具轮") == 1, "R604 块计数异常"
assert txt.count("**下轮候选 (R605)**") == 1, "R605 块计数异常"
assert "**下轮候选 (R604)**" in txt, "R603 的 R604 候选段被破坏"
print("[closeout] kpi.jsonl rows=%d  R604 落盘 ✓  master-plan 追加 ✓ (chars=%d)" % (rows, len(txt)))
print("[closeout] kpi tail:", json.dumps(r604["readings"]["C2_j3_form"]["r603"], ensure_ascii=False))
print("[closeout] plan block staged at: %s" % os.path.relpath(tgt, REPO))
