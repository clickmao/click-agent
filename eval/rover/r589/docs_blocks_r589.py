#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R589 文档面收口（幂等；只做增量插入，禁整段覆盖）。

① `docs/reports/dynamic-telemetry-eval-rollback-strategy.md` §7: 在 R588 行上方插 R589 行，
   并把 R588 行标为【历史快照，已被上方 R589 行取代】（与 R587→R588 既有做法一致）。
② `docs/reports/iteration-master-plan.md` 末尾: 追加 R589 轮节 + 下轮候选 (R590)。
纪律：写前断言锚点唯一；写后回读断言（新串 == 1 ∧ 旧串 == 0）；JSON.stringify 式拼接避免占位符错位。
"""
from __future__ import annotations

import io
import json
import os
import time

REPO = "/home/agentuser/AgentFramework"
D = os.path.join(REPO, "eval/rover/r589")
STRAT = os.path.join(REPO, "docs/reports/dynamic-telemetry-eval-rollback-strategy.md")
PLAN = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
ANCHOR = "> - **最近一轮（R588，2026-09-20 · cron 60min tick）**: "
ANCHOR_NEW = "> - **最近一轮（R588，2026-09-20 · cron 60min tick）【历史快照，已被上方 R589 行取代】**: "


def rd(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def build_strategy_line(m):
    L = []
    L.append("> - **最近一轮（R589，%s · cron 60min tick）**: **判据面切换轮（整题全对率 58/58 + 按族分列）× 只读并池**")
    L.append(" —— 零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关；数据面 = R585–R588 四窗集在盘机械判分件")
    L.append("（12 窗 × 48 跑次 × 58 例；题集 sha `%s`、二进制 sha `%s`，跨轮只并列不相减）。")
    L.append("**主判据 C1（换面后缺口是否仍成立）**：有效窗 **%d**（unreliable = 真值自身失分窗 %s）；")
    L.append("**整题全对率面**中位 **%s** / 极差 **%s** / 符号 %s（阈值 中位 ≤ −0.34 ∧ 负号窗 ≥ 半数）⇒ **PASS「整题面缺口成立」**；")
    L.append("**用例级面**中位 %s（两面同向；量纲不同 ⇒ 只判同向、禁比大小）⇒ **rc=0**。")
    L.append("**按族分列（本轮新面）**：%s ⇒ 缺口 **100%% 集中在 `wythoff` 单族**，其余三族产品整题全对率与真值同级。")
    L.append("**候选并轮收口**：② 字符级最小复现（C8）rc=%s、最小删除集 **%s**（基数 **%s**；下沉到 `plan` 数组第 %s 个元素 = 该步子树），")
    L.append("块结构栈 **%s 个未闭合** ∧ **补闭合不恢复** ⇒ 内层异常而非单纯截断；③ 真值臂成本定因（C9）调用 **%s→%s（×%s）**、")
    L.append("prompt **%s→%s（×%s）**，而 `write_stdin`（yield 轮询）占比仅 %s→%s ⇒ **成本异常来自单窗集中**")
    L.append("（`r588/w165` = 40 调用 / 925,503 prompt / 27,824 completion），**非**「长命令轮询」假设；④ 脱钩（C10）%d/%d = %.4f；")
    L.append("⑤ 子类 gap（C11）max|gap|=%.4f ⇒ 描述项定案。**起手闸**：A1/A2 PASS ∧ 判别力成对控制 rc=%s")
    L.append("（修后同仪器可比；首跑混用两仪器读数的 rc=3 留档不翻案）∧ leak-selfcheck rc=%s；C5 只读性 %s（%d 文件 sha 前后同值）。")
    L.append("**铁律 11**：本轮重跑 rc=%s（前序各轮读数 r585 不收敛 / r586 9/9 一致 / r587 分母口径 / r588 rc=1 已登记）；")
    L.append("**零新跑次 ⇒ 不宣称任何降幅/增益**。**自捕 3 件（均未放宽判据）**：① `cases.txt` 读法漏带 reason 的 FAIL 行 ⇒ 15 行读空 rc=3；")
    L.append("② 负控首版两侧同步位移 ⇒ 假阴性（改单侧）；③ 判别力成对控制混用两仪器读数（系统差 +95MB）⇒ 判据恒不可行。")
    L.append("**诚实边界**：① 本轴缺口在**换判据面后仍成立**（R588 的「定案关闭」针对**加窗求效应**，不针对**换面**）；")
    L.append("② (b) 直进产品侧修复需用户放行、(c) 换更长题面会改可比性 ⇒ 二者列**待用户裁定**；③ 新读法器具不登记 capability 行。")
    L.append("轮志 `eval/rover/r589/report-r589.md`、预注册 `prereg-r589.json`、DAG `dag-r589.md`、台账 `eval/capability/kpi.jsonl`（R589）。")
    tpl = "".join(L) + "\n"
    return tpl % (
        m["date"], m["taskset"], m["bin12"],
        m["valid_windows"], m["unreliable"],
        m["task_median"], m["task_range"], m["task_sign"],
        m["case_median"],
        m["famtxt"],
        m["c8_rc"], m["c8_min"], m["c8_card"], m["c8_within_idx"],
        m["unclosed"],
        m["calls"][0], m["calls"][1], m["calls_x"],
        m["prompt"][0], m["prompt"][1], m["prompt_x"],
        m["ws"][0], m["ws"][1],
        m["c10_n"], m["c10_d"], m["c10_share"],
        m["c11"],
        m["disc_rc"], m["leak"],
        m["c5_pass"], m["c5_files"],
        m["pre_rc"],
    )


def build_plan_block(m):
    L = []
    L.append("")
    L.append("- **R589（判据面切换轮 · 只读并池：`R585–R588` 四窗集在盘机械判分件；零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关）**: ")
    L.append("**修改点** ① 并池器 `eval/rover/r589/pool_taskface_r589.py`（两面重算 + 按族 + 配对 + C6/C7/C10/C11；")
    L.append("器具自捕 3 件：`cases.txt` 读法漏 `FAIL <reason>` 行 ⇒ 15 行读空 rc=3、负控首版两侧同步位移 ⇒ 假阴性、判别力成对控制混用两仪器读数 ⇒ 判据恒不可行）；")
    L.append("② 起手闸 `gate_r589.sh`（MARGIN 由 R588 实测振幅派生）+ `disc_pair_r589.sh`（同仪器可比修后 rc=%s）；" % m["disc_rc"])
    L.append("③ 候选② `charlevel_bisect_r589.py`；④ 候选③ `codex_cost_cause_r589.py`；⑤ `readonly_fingerprint_r589.py`（与并池器同指纹口径, 直接 import）；⑥ `finish_r589.py` + `docs_blocks_r589.py`。")
    L.append("**读数**（12 窗 × 48 跑次 × 58 例；题集 sha `%s`、二进制 sha `%s`）：**有效窗 %d**（真值自身失分窗 %s）；" % (m["taskset"], m["bin12"], m["valid_windows"], m["unreliable"]))
    L.append("**整题全对率面**中位 **%s** / 极差 **%s** / 符号 %s ⇒ **判据 C1 PASS「整题面缺口成立」、rc=0**；" % (m["task_median"], m["task_range"], m["task_sign"]))
    L.append("**用例级面**中位 %s（同向）；**按族分列**：%s ⇒ 缺口集中在 `wythoff` 单族。" % (m["case_median"], m["famtxt"]))
    L.append("**候选②** 字符级最小复现：最小删除集 %s（基数 %s），下沉到 `plan` 元素第 %s；栈 %s 个未闭合 ∧ 补闭合不恢复 ⇒ 内层异常。" % (m["c8_min"], m["c8_card"], m["c8_within_idx"], m["unclosed"]))
    L.append("**候选③** 真值臂成本定因：调用 %s→%s（×%s）、prompt %s→%s（×%s）、`write_stdin` 占比 %s→%s ⇒ 成本异常在 **单窗集中**（`r588/w165`）。" % (m["calls"][0], m["calls"][1], m["calls_x"], m["prompt"][0], m["prompt"][1], m["prompt_x"], m["ws"][0], m["ws"][1]))
    L.append("**候选④** 脱钩 %d/%d = %.4f；**候选⑤** 子类 gap max|gap|=%.4f ⇒ 描述项定案。" % (m["c10_n"], m["c10_d"], m["c10_share"], m["c11"]))
    L.append("**诚实边界**：零新跑次 ⇒ 不宣称任何降幅/增益；铁律 11 本轮重跑 rc=%s（前序读数已登记）；(b)/(c) 待用户裁定。" % m["pre_rc"])
    L.append("轮志 `eval/rover/r589/report-r589.md`、预注册/DAG `eval/rover/r589/{prereg-r589.json,dag-r589.md}`、台账 `eval/capability/kpi.jsonl`（R589）。")
    L.append("")
    L.append("- **下轮候选 (R590)**: ① **本轴缺口定案后的处置裁定（待用户放行）**：(b) 直进产品侧修复（须放行 ⇒ 本轮未动产品源码）"
             "(c) 换更长题面=新基线（会改可比性 ⇒ 非可自决）；② **按族定因继续下沉**：`wythoff` 单族整族塌陷 ⇒ 从 C8 已定位的"
             "「`plan` 元素内过度转义」出发，量「该形态在 12 窗 36 产品跑次的出现率」与「与整族塌陷的相关性」（纯只读；"
             "出现率 0 则本候选自证无价值，应改查落点非冷点主因）；③ **判据面入册**：把「整题全对率 + 按族分列」写进 "
             "`docs/external-reference-harness.md` 判据 v3（v2 保留、作废登记，跨版本禁相减）；④ 起手闸余量条款按 R589 实测振幅重派生；"
             "⑤ 前置器在 project 布局下的**耗时**（本轮 4 轮重跑未跑完 ⇒ 只读轮可用「各轮自身已登记读数 + 抽样复跑」替代，"
             "写成口径再动器具）。")
    L.append("")
    return "\n".join(L) + "\n"


def main():
    pool = rd(os.path.join(D, "taskface-pool-r589.json"))
    v = rd(os.path.join(D, "verdict-r589.json"))
    pre = rd(os.path.join(D, "prereg-r589.json"))
    c8 = rd(os.path.join(D, "charlevel-bisect-r589.json"))
    c9 = rd(os.path.join(D, "codex-cost-cause-r589.json"))
    s, fam = pool["summary"], pool["family_aggregate"]
    ref = c8["refine_within_member"]
    famtxt = "；".join("%s all-pass %.4f（真值 %d/%d、失败原因 %s）"
                     % (f, fam[f]["prod_all_pass_rate_mean"], fam[f]["truth_all_pass_runs"], fam[f]["truth_runs"],
                        ", ".join("%s×%d" % (k, n) for k, n in (fam[f]["prod_fail_reasons_total"] or {}).items()) or "—")
                     for f in ("life", "nim", "sub", "wythoff"))
    m = {
        "date": time.strftime("%Y-%m-%d"),
        "taskset": pre["data_scope"]["taskset_sha16"], "bin12": pre["data_scope"]["bin_sha256"][:12],
        "valid_windows": s["valid_windows"], "unreliable": ", ".join(s["unreliable_windows_truth_self_fail"]),
        "task_median": s["task_face_valid"]["median"], "task_range": s["task_face_valid"]["range"],
        "task_sign": s["task_face_valid"]["sign"], "case_median": s["case_face_valid"]["median"],
        "famtxt": famtxt,
        "c8_rc": c8["rc"], "c8_min": c8["minimal_delete_set"], "c8_card": c8["minimal_delete_set_cardinality"],
        "c8_within_idx": (ref.get("minimal_delete_set_within") or [None])[0],
        "unclosed": c8["structure"]["unclosed_openers"],
        "calls": [r["calls_total"] for r in c9["rounds"]],
        "prompt": [r["tokens"]["prompt_total"] for r in c9["rounds"]],
        "calls_x": c9["ratio_r588_over_r587"]["calls"], "prompt_x": c9["ratio_r588_over_r587"]["prompt_total"],
        "ws": [r["write_stdin_share_of_calls"] for r in c9["rounds"]],
        "c10_n": pool["C10_decoupling"]["rc_nonzero_and_allpass"], "c10_d": pool["C10_decoupling"]["product_runs"],
        "c10_share": pool["C10_decoupling"]["share"], "c11": pool["C11_subspec_gap"]["max_abs_gap"],
        "disc_rc": v["checks"]["C4_gate"]["disc_pair"]["rc"],
        "leak": v["checks"]["C4_gate"]["leak_selfcheck_rc"],
        "c5_pass": pool["C5_readonly"]["pass"], "c5_files": pool["C5_readonly"]["files"],
        "pre_rc": v["checks"]["C3_truth11_precondition"]["rerun_rc"] or "in_flight",
    }
    assert m["c5_pass"] is True, "C5 未过 ⇒ 不出文档面"
    assert v["verdict"]["rc"] == 0, "裁定非 0 ⇒ 停（人工确认后再落文档）"

    # ---- ① §7 ----
    src = read(STRAT)
    if "最近一轮（R589" in src:
        print("§7: R589 行已存在 ⇒ 跳过")
    else:
        assert src.count(ANCHOR) == 1, "R588 锚点计数 != 1 (%d)" % src.count(ANCHOR)
        line = build_strategy_line(m)
        assert "\n" not in line.rstrip("\n")
        src = src.replace(ANCHOR, line + ANCHOR_NEW, 1)
        write(STRAT, src)
        back = read(STRAT)
        assert back.count("最近一轮（R589") == 1 and back.count(ANCHOR) == 0, "§7 回读断言失败"
        print("§7: 已插入 R589 行并将 R588 行转历史快照")

    # ---- ② master plan ----
    p = read(PLAN)
    if "\n- **R589（判据面切换轮" in p:
        print("master plan: R589 节已存在 ⇒ 跳过")
    else:
        p = p.rstrip("\n") + "\n" + build_plan_block(m)
        write(PLAN, p)
        back = read(PLAN)
        assert back.count("- **R589（判据面切换轮") == 1 and back.count("- **下轮候选 (R590)") == 1
        print("master plan: 已追加 R589 节 + R590 候选行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
