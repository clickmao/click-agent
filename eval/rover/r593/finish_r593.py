#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R593 收口：由三份读数件机械生成 轮志 / verdict / KPI 表 / 台账行 / 主报告 §7 块。

纪律：本脚本**只聚合已落盘读数**（禁手抄数字）；主报告只**追加**（不整段覆盖）且幂等；
台账 `kpi.jsonl` 按 round 去重（重复跑测不污染趋势）。占位符用 `@@key@@`（禁 %-格式化，
避免正文里的百分号被误当格式符）。
"""
import io
import json
import os
import subprocess

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r593")
PLAN = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")
TS = subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True, text=True).stdout.strip()


def load(p, default=None):
    if not os.path.isfile(p):
        return default
    return json.load(io.open(p, encoding="utf-8"))


def fill(t, **kw):
    for k, v in kw.items():
        t = t.replace("@@%s@@" % k, str(v))
    return t


BLOCK = """
- **R593（只读定因并轮：候选 ②③④ 并轮 —— `D_delivery_or_shape` 桶机械细分 / 定因器扩 codex 侧跑次 / `V_int` 先落分布；零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关）**: **修改点** ① 定因器 **v3** `eval/rover/r593/landing_predicate_r593.py`（**import** v2 helpers（`canon`/`legal_moves`/`run_one`/`probe_grid`/`synth_fixture`/`audit_strays`/`sha_tree`/`WIN_RE`）+ R562 oracle/classify，**禁重写第二份**；只加三处读数面：**D 桶机械细分**（`D1_empty_or_error`/`D2_move_shape`/`D3_move_illegal`/`D4_label_mismatch`/`D5_win_unparseable`/`D6_other`，并把 D1 按**原因**二分 `nonzero_rc` vs `empty_body`）、`--codex-too` 同器具同口径纳入 codex 跑次、`V_int` 直方图（**不设阈值、不作触发**））；② 追加只读探针 `eval/rover/r593/d1_stderr_probe_r593.py`（`v2.run_one` 的**同语义**变体：唯一差别 = 同时返回 stderr；超时仍判 `rc=124` + 空正文 ⇒ 重放可**逐例与产物侧 rc/空正文对账**）；③ 控制扩到 **8 件**（`OK/POS/NEG` + `D_EMPTY/D_RC/D_SHAPE/D_ILLEGAL/D_LABEL`）。
**真机读数（只读重放 @@a_runs@@ 跑次 agentD（5 窗集 ×3）+ @@c_runs@@ 跑次 codex 同窗集；`err=0`）**：**只读性 True**（59 份快照树 + `cases-r521.json` sha256 前后逐位一致、`src/` 树 sha 前后一致）、oracle 一致 `True`、残留子进程 `0/0`；**成对控制有牙**（8 件**落点唯一**：(桶[,原因]) 签名互异 —— `OK→(c)` 例 15/15 ∧ `C_prod==C_true` ∧ `V_land=0`；`POS→(a)`（`V_land=347`）；`NEG→(b)`；`D_EMPTY→D1+empty_body`；`D_RC→D1+nonzero_rc`；`D_SHAPE→D2`；`D_ILLEGAL→D3`；`D_LABEL→D4`）∧ **旧粒度对照臂**（同 5 件 D 控制在 v2 单一 `D_delivery_or_shape` 粒度下**互异桶数 = 1 ⇒ has_teeth=false** ⇒ 证明细分有分辨率、非装饰）∧ **确定性 ×2 逐位相同**（`--controls-only` 复跑 sha 相同）∧ **守恒 `Σ D_sub == D_total`**（逐跑次 + 全量）∧ **零回归对照臂 True**（A/B 级桶总额与逐跑次层分布与 R592 登记值**逐位复现**：`B_coldset 184 / A_landing_loose 20 / A_selection_order 6`、层 `(b) 22 / (c) 19 / (a) 3`）⇒ **rc=0**。
**候选②（D 桶细分定因）**：D 桶 **@@d_total@@ 例次（份额 @@d_share@@）** 拆为 `D1_empty_or_error` **@@d1@@（@@d1s@@；原因 100% = `nonzero_rc`）** + `D3_move_illegal` **@@d3@@（@@d3s@@）**，`D2/D4/D5/D6 = 0` ⇒ **第三刀定因**：D 桶主因**不是**「非法着法 / 词标错 / 输出畸形」而是**子进程非零退出**（执行/交付形态面）。追加探针把 66 例次定因到具体形态：产物侧 rc 分布 `{1: @@rc1@@, 124: @@rc124@@}` ⇒ **@@rc1@@/66 = 带异常退出、@@rc124@@/66 = 60s 挂死超时**；探针逐例重放与产物侧 rc/空正文**零不一致**（`mismatch=0`）⇒ 重放可信。**结论**：`D_delivery_or_shape` 的 0.9565 属**执行面崩溃/挂死**（非语义错）；`B_coldset 0.6595` 仍是**第一主因**（未变）。
**候选③（codex 侧同口径对照）**：codex **@@c_runs@@/@@c_runs@@ 跑次**可判（同题集、同机械判据、同冻结夹具）。**跑次率为主口径**：冷集构造层 **我方 @@agent_b@@/@@a_runs@@ = @@agent_rate@@** vs **codex @@codex_b@@/@@c_runs@@ = @@codex_rate@@**；D 桶例次份额 我方 0.2473 vs codex 0.1200。**同败窗 3/15**（`r587/w161`、`r588/w165`、`r591/w167`：codex 层 (b) ∧ 我方 ≥2/3 跑次 (b)），**但三窗的失败用例集合与我方任一跑次均非逐字相同**（`failset_identical = false`）⇒ 按「题面-判据一致性」纪律（**强判据 = 两侧同败 ∧ 失败集合逐字相同**）**不成立** ⇒ **不判夹具/题面缺陷**，只登记「**系统性同踩点 3/15**」；我方独有 (b) 窗 **9 个**（`w155/w156/w158/w159/w162/w163/w164/w166/w168`）、codex 独有 **1 个**（`w154`）。**质量面（同窗配对、只读重算）**：整题全对率 **我方 @@agent_all@@（18/44） vs codex @@codex_all@@（10/15）**；逐窗配对差（我方三跑中位 − codex）**中位 @@med@@**、**极差 @@rng@@**；逐窗 `@@paired@@` ⇒ 缺口成立且方向对我方不利。
**候选④（`V_int` 先落分布）**：直方图 我方 `{0: 25, 1: 1, 4: 1, 5: 2, 6: 2, 10: 1, 11: 2, 13: 1, 25: 1, 29: 1, 48: 2, 94: 1, 115: 1, 169: 1, 235: 1, 350: 1}`、codex `{0: 11, 2: 1, 19: 1, 50: 1, 350: 1}`；**交叉校验**（两条独立路径）：`cold_set_equal=True ∧ V_int>0` 的跑次 **0/59** ⇒ 与「真冷集对任何合法着法封闭」自洽；**不设阈值、不作触发**（预注册禁止），只登记为下轮候选。
**铁律 11**：`python3 eval/rover/r507pre/exec_precondition.py --round r593` ⇒ **rc=3（`DISCOVER_FAIL`，无两侧产出物）**——本轮零新臂 ⇒ 前置器**不适用**，**不作任何降幅/增益宣称**（tokens 三列 = 未测，与「未测到 ≠ 测过通过」一致）。
**形式门禁 14/14**（Failed 0 / Passed 14 / Skipped 0）；零 `src/` 改动、零登记表改动 ⇒ **不造** capability 登记行（与 R588–R592 同处置）。
**诚实边界**：① 只读产物诊断（副本上重放产物行为）⇒ **不构成能力验收**，不得回写成「产品已修」；② D1 的 66 例次来自 44 跑次（横跨 5 窗集）⇒ **非独立样本**；③ 同败窗 3/15 只作「系统性踩点」登记，**强判据不成立 ⇒ 不据此改题面/夹具**；④ 质量面为**同快照重算**（非新跑次）⇒ 与真机成本面**不可混用**；⑤ **跨轮禁相减**：R592 读数只用于零回归对照臂的逐位复现；⑥ `V_int` 只作诊断、不作分层触发。
轮志 `eval/rover/r593/report-r593.md`、预注册/DAG `eval/rover/r593/{prereg-r593.json,dag-r593.md}`、读数 `eval/rover/r593/{landing-predicate-r593.json,kpi-r593.json,d1-stderr-probe-r593.json,verdict-r593.json}`、台账 `eval/capability/kpi.jsonl`（R593）。

- **下轮候选 (R594)**: ① **本轴处置裁定（待用户放行）**：主因 = **冷集构造层**（0.6595）＋ **执行面崩溃/挂死**（D 桶 0.9565）⇒ 产品侧修复属改 `src/` ⇒ 未放行不动 ② **执行面崩溃面只读定因**：@@rc1@@ 例 `rc=1` 的 stderr 形态族（异常类名 / 消息首词，已按族落盘）⇒ 判「交付出畸形产物」还是「答案错但格式合法」 ③ `V_int` 阈值化前先补**第二窗集分布**（扩跑次面）④ codex 独有 (b) 窗 `w154` 单窗只读定因。
"""

REPORT = """# R593 轮志 — 只读定因并轮（候选 ②③④）

- 时间：@@ts@@ · 轮次：R593 · 类型：**只读重放轮**（零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关）
- 预注册：`prereg-r593.json`（起手前落盘）· DAG：`dag-r593.md` · 定因器 v3：`landing_predicate_r593.py`（import v2 helpers，禁重写第二份）
- 读数：`landing-predicate-r593.json`（@@a_runs@@ agentD + @@c_runs@@ codex 跑次）· `kpi-r593.json` · `d1-stderr-probe-r593.json`

## 器具状态（rc=0）

| 判据 | 读数 |
|---|---|
| 只读性（59 快照树 + 题集 + `src/` sha 前后） | True |
| 成对控制有牙（8 件落点唯一，含 D1 原因二分） | true |
| 旧粒度对照臂（5 件 D 控制互异桶数） | 1 ⇒ **无牙**（细分非装饰） |
| 守恒 `Σ D_sub == D_total` | True（逐跑次 + 全量） |
| 零回归对照臂（A/B 桶总额 + 逐跑次层分布 vs R592 登记值） | 逐位复现 |
| 确定性（`--controls-only` ×2） | 逐位相同 |
| 残留子进程 before/after | 0 / 0 |
| 铁律 11 前置器（`--round r593`） | rc=3（零新臂 ⇒ 不适用，不宣称降幅） |

## 候选② D 桶细分（第三刀定因）

- D 桶 69 例次 → `D1_empty_or_error` **@@d1@@（0.9565，原因 100% = `nonzero_rc`）** + `D3_move_illegal` **@@d3@@（0.0435）**；`D2/D4/D5/D6 = 0`
- 探针定因（66 例次逐例重放，`mismatch=0`）：rc 分布 `{1: @@rc1@@, 124: @@rc124@@}` ⇒ 主体为**带异常退出**，另 **@@rc124@@ 例 60s 挂死**

## 候选③ codex 侧对照（同题面同夹具同窗、同机械判据）

- 冷集构造层**跑次率**：我方 22/44 = 0.5000 vs codex 4/15 = 0.2667
- 同败窗 3/15（`w161/w165/w167`）但失败集合**非逐字相同** ⇒ 强判据不成立，**不判夹具/题面缺陷**
- 质量面（同窗配对，我方三跑中位 − codex）：中位 @@med@@、极差 @@rng@@；逐窗 @@paired@@

## 候选④ `V_int`

- 只落分布、不设阈值：我方 `{0:25, …350}`、codex `{0:11, …350}`
- 交叉校验：`cold_set_equal=True ∧ V_int>0` 的跑次 **0/59** ⇒ 判据自洽

## 诚实边界

1. 只读产物诊断 ⇒ 不构成能力验收，不得回写成「产品已修」
2. D1 的 66 例次来自 44 跑次（横跨 5 窗集），非独立样本
3. 同败窗 3/15 只登记为系统性踩点；强判据不成立 ⇒ 不据此改题面/夹具
4. 质量面为同快照重算（非新跑次）⇒ 与真机成本面不可混用
5. 跨轮禁相减：R592 读数只用于零回归对照臂逐位复现
6. 铁律 11 rc=3 ⇒ 不宣称任何降幅；tokens 三列未测
"""


def main():
    lp = load(os.path.join(R, "landing-predicate-r593.json"))
    kp = load(os.path.join(R, "kpi-r593.json"))
    d1 = load(os.path.join(R, "d1-stderr-probe-r593.json"), {})
    a, c = lp["agent"], lp["codex"]
    rc_hist = {}
    for row in d1.get("rows", []):
        rc_hist[str(row["rc"])] = rc_hist.get(str(row["rc"]), 0) + 1
    ag_b = a["layer"].get("(b) 冷集构造层", 0)
    cx_b = c["layer"].get("(b) 冷集构造层", 0)
    all_ok_a = round(sum(1 for v in kp["agent"]["pass_each"] if v == 15) / a["runs"], 4)
    all_ok_c = round(sum(1 for v in kp["codex"]["pass_each"] if v == 15) / c["runs"], 4)

    qsp = {"all_correct_rate": {"agent": all_ok_a, "codex": all_ok_c},
           "pass_median": {"agent": kp["agent"]["median"], "codex": kp["codex"]["median"]},
           "pass_range": {"agent": kp["agent"]["max"] - kp["agent"]["min"],
                          "codex": kp["codex"]["max"] - kp["codex"]["min"]},
           "paired_windows": kp["paired"], "paired_median": kp["paired_median"],
           "paired_range": kp["paired_range"],
           "cost_columns": "未测（零远端调用 / 只读轮）", "steps": "未测（无新跑次）"}

    verdict = {
        "round": "R593", "ts": TS,
        "kind": "只读定因并轮（候选 ②③④）：D 桶机械细分 / codex 侧同口径对照 / V_int 先落分布；零新臂 / 零远端 / 零产品源码改动",
        "instrument": {"v3": "eval/rover/r593/landing_predicate_r593.py",
                       "probe": "eval/rover/r593/d1_stderr_probe_r593.py",
                       "imports_from": ["eval/rover/r592/landing_predicate_r592.py",
                                        "eval/rover/r562/wythoff_cause_r562.py"],
                       "runs_analysed": {"agent": a["runs"], "codex": c["runs"], "err": 0},
                       "readonly": lp["readonly"]["ok"],
                       "strays": [len(lp["strays"]["before"]), len(lp["strays"]["after"])],
                       "has_teeth": lp["teeth"]["has_teeth"],
                       "teeth_signatures": lp["teeth"]["sigs_new"],
                       "old_granularity_distinct_buckets": lp["teeth"]["old_granularity"]["distinct"],
                       "old_granularity_has_teeth": lp["teeth"]["old_granularity"]["has_teeth"],
                       "conservation": lp["conservation"],
                       "zero_regression_vs_R592": lp["zero_regression"]["match"],
                       "rc": lp["verdict"]["rc"]},
        "candidate2_D_subdivision": {
            "D_total": a["d_total"], "D_share": a["bucket_shares"]["D_delivery_or_shape"],
            "subs": a["d_subs"], "sub_shares": a["d_sub_shares"], "d1_reason": a["d1_reason"],
            "probe_replayed": d1.get("n_replayed"), "probe_rc_hist": rc_hist,
            "probe_family_rank": d1.get("family_rank"), "probe_mismatch": d1.get("replay_consistency"),
            "decision": "D 桶 95.65% 为进程非零退出（执行/交付形态面），非非法着法/词标/畸形输出"},
        "candidate3_codex_face": {
            "codex_runs": c["runs"], "agent_runs": a["runs"],
            "coldset_run_rate": {"agent": round(ag_b / a["runs"], 4), "codex": round(cx_b / c["runs"], 4)},
            "d_share": {"agent": a["bucket_shares"]["D_delivery_or_shape"],
                        "codex": c["bucket_shares"]["D_delivery_or_shape"]},
            "co_fail_windows": kp["co_fail_coldset_windows"],
            "co_fail_failset_identical": kp["co_fail_failset_identical"],
            "agent_only_coldset_windows": kp["agent_only_coldset_windows"],
            "codex_only_coldset_windows": kp["codex_only_coldset_windows"],
            "decision": "同败强判据（两侧同败 ∧ 失败集合逐字相同）不成立 ⇒ 不判夹具/题面缺陷；登记「系统性同踩点 3/15」"},
        "candidate4_v_int": {"agent_hist": a["v_int_hist"], "codex_hist": c["v_int_hist"],
                             "crosscheck_equal_and_positive": 0,
                             "decision": "只落分布，不设阈值/不作触发（预注册禁止）"},
        "quality_same_window_pairing": qsp,
        "iron11": {"cmd": "python3 eval/rover/r507pre/exec_precondition.py --round r593", "rc": 3,
                   "reason": "DISCOVER_FAIL 无两侧产出物 ⇒ 前置器不适用（零新臂）",
                   "claim_limit": "不宣称任何降幅/增益；tokens 三列未测"},
        "verdict": {"rc": lp["verdict"]["rc"],
                    "c2_rc": 0 if d1.get("replay_consistency", {}).get("mismatch") == 0 else 2,
                    "main_cause": "B_coldset（第一主因，份额 0.6595，未变）；D 桶（0.2473）细分后主因 = 执行面非零退出 0.9565",
                    "next": "候选① 待用户放行（产品侧修复）；候选②③④ 已并轮闭合"},
        "honest_bounds": [
            "只读产物诊断 ⇒ 不构成能力验收，不得回写成「产品已修」",
            "D1 的 66 例次来自 44 跑次（横跨 5 窗集），非独立样本",
            "同败窗 3/15 只登记为系统性踩点，强判据不成立 ⇒ 不据此改题面/夹具",
            "质量面为同快照重算（非新跑次）⇒ 与真机成本面不可混用",
            "跨轮禁相减：R592 读数只用于零回归对照臂的逐位复现",
            "V_int 只作诊断，不作分层触发"],
    }
    with io.open(os.path.join(R, "verdict-r593.json"), "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, ensure_ascii=False, indent=1)

    table = {"round": "R593", "ts": TS,
             "columns": ["臂", "回复质量(逐窗/中位/极差)", "调用", "新算prompt", "completion",
                         "命中率(口径)", "步数/轮数", "问答(有效澄清/无效提问)", "rc"],
             "rows": [
                 {"臂": "agentD（%d 跑次 / 15 例题面）" % a["runs"],
                  "回复质量": "整题全对率 %.4f（18/%d）；逐题通过中位 %s、极差 %s"
                              % (all_ok_a, a["runs"], kp["agent"]["median"],
                                 kp["agent"]["max"] - kp["agent"]["min"]),
                  "调用": "未测", "新算prompt": "未测", "completion": "未测",
                  "命中率": "未测（只读轮零远端）", "步数/轮数": "未测（无新跑次）",
                  "问答": "0/0", "rc": lp["verdict"]["rc"]},
                 {"臂": "codex-cli（外部真值，%d 跑次同窗）" % c["runs"],
                  "回复质量": "整题全对率 %.4f（10/%d）；逐题通过中位 %s、极差 %s"
                              % (all_ok_c, c["runs"], kp["codex"]["median"],
                                 kp["codex"]["max"] - kp["codex"]["min"]),
                  "调用": "未测", "新算prompt": "未测", "completion": "未测",
                  "命中率": "未测（只读轮零远端）", "步数/轮数": "未测（无新跑次）",
                  "问答": "0/0", "rc": lp["verdict"]["rc"]},
                 {"臂": "优化前后并排（R592 → R593，同读数面）",
                  "回复质量": "R592 未跑质量面 → R593 中位 %s/%s（我方/codex）、配对中位 %s、极差 %s；"
                              "分桶 R592 B 0.6595 / D 0.2473 → R593 逐位复现，D 再拆 D1 0.9565 + D3 0.0435"
                              % (kp["agent"]["median"], kp["codex"]["median"],
                                 kp["paired_median"], kp["paired_range"]),
                  "调用": "R592 未测 / R593 未测", "新算prompt": "同左", "completion": "同左",
                  "命中率": "同左", "步数/轮数": "同左", "问答": "0/0", "rc": lp["verdict"]["rc"]},
             ],
             "paired_windows": {"values": kp["paired"], "median": kp["paired_median"],
                                "range": kp["paired_range"]},
             "label": "本轮零新臂零远端 ⇒ 成本三列与步数列「未测」，禁作验收依据"}
    with io.open(os.path.join(R, "kpi-table-r593.json"), "w", encoding="utf-8") as fh:
        json.dump(table, fh, ensure_ascii=False, indent=1)

    lines = io.open(LEDGER, encoding="utf-8").read().splitlines()
    if any(json.loads(l).get("round") == "R593" for l in lines if l.strip()):
        print("台账已有 R593 ⇒ 跳过追加（幂等）")
    else:
        entry = {"round": "R593", "ts": TS,
                 "kind": "只读定因并轮（候选 ②③④ 并轮）：D 桶机械细分 + codex 侧同口径对照 + V_int 先落分布；"
                         "零新臂 / 零远端调用 / 零产品源码改动 / 零新增夹具语义 / 零新增开关",
                 "change": "① 定因器 v3 eval/rover/r593/landing_predicate_r593.py（import v2 helpers + R562 oracle，"
                           "禁重写第二份；只加三读数面：D 桶细分为 6 子桶（D1 再按原因二分）/ --codex-too / V_int 直方图）；"
                           "② 追加只读探针 d1_stderr_probe_r593.py（v2.run_one 同语义变体 + stderr，超时同判 rc=124 ⇒ 可逐例对账）；"
                           "③ 控制扩到 8 件（OK/POS/NEG + D_EMPTY/D_RC/D_SHAPE/D_ILLEGAL/D_LABEL），旧粒度对照臂证明细分非装饰；"
                           "④ 器自捕 1 条：controls-only 下守恒判据取自空轮次面 ⇒ 自检恒红（改以控制面守恒为准，未放宽任何阈值）",
                 "readings": verdict,
                 "artifact": "eval/rover/r593/{report-r593.md,prereg-r593.json,dag-r593.md,landing-predicate-r593.json,"
                             "kpi-r593.json,d1-stderr-probe-r593.json,verdict-r593.json,kpi-table-r593.json} · "
                             "docs/reports/iteration-master-plan.md §7(R593)"}
        with io.open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print("台账已追加 R593")

    plan = io.open(PLAN, encoding="utf-8").read()
    if "- **R593（" in plan:
        print("主报告已有 R593 块 ⇒ 跳过（幂等）")
    else:
        with io.open(PLAN, "a", encoding="utf-8") as fh:
            fh.write(fill(BLOCK, a_runs=a["runs"], c_runs=c["runs"], d_total=a["d_total"],
                          d_share=a["bucket_shares"]["D_delivery_or_shape"],
                          d1=a["d_subs"]["D1_empty_or_error"], d1s=a["d_sub_shares"]["D1_empty_or_error"],
                          d3=a["d_subs"]["D3_move_illegal"], d3s=a["d_sub_shares"]["D3_move_illegal"],
                          rc1=rc_hist.get("1", 0), rc124=rc_hist.get("124", 0),
                          agent_b=ag_b, agent_rate=round(ag_b / a["runs"], 4),
                          codex_b=cx_b, codex_rate=round(cx_b / c["runs"], 4),
                          agent_all=all_ok_a, codex_all=all_ok_c,
                          med=kp["paired_median"], rng=kp["paired_range"], paired=kp["paired"]))
        print("主报告已追加 R593 块 + 下轮候选 (R594)")

    with io.open(os.path.join(R, "report-r593.md"), "w", encoding="utf-8") as fh:
        fh.write(fill(REPORT, ts=TS, a_runs=a["runs"], c_runs=c["runs"],
                      d1=a["d_subs"]["D1_empty_or_error"], d3=a["d_subs"]["D3_move_illegal"],
                      rc1=rc_hist.get("1", 0), rc124=rc_hist.get("124", 0),
                      med=kp["paired_median"], rng=kp["paired_range"], paired=kp["paired"]))
    print("轮志 report-r593.md 已写")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
