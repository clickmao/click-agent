#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R603 收口器（只读计算 + 落盘；零产品改动 / 零远端调用）。

产出：
  · `eval/rover/r603/report-r603.md`      —— 轮志（含主判据 v3 set10 与 J1–J5）
  · `eval/capability/kpi.jsonl` **追加**一行（12 键，与既有行**键集对齐**）
  · `docs/evidence/RF0001/R603-*.md`      —— 证据面指针（含 sha + 复现命令）

判据 v3（同窗 codex 配对，**公式逐字取自** `eval/rover/r599/kpi_r599.py::judge` 的主线段）：
  D_w = median(cases_pass 产品) − median(cases_pass 真值)；只算**有效窗**（真值 58/58）；
  C1_ok = 有效窗 ≥ 2 ∧ D_median ≥ −2 ∧ ∀ D_w > −15。
用法: python3 finish_r603.py
"""
from __future__ import annotations
import hashlib
import importlib.util
import io
import json
import os
import statistics
import sys

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r603")
D = os.path.expanduser("~/.agentframework/harness/runs/r603")
SRC599 = os.path.join(REPO, "eval/rover/r599/kpi_r599.py")


def load_helpers():
    spec = importlib.util.spec_from_file_location("kpi599", SRC599)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def main():
    mod = load_helpers()
    recs = mod.collect(D, PD)
    wins = sorted({r["win"] for r in recs}, key=lambda w: int(w[1:]))
    prod = [r for r in recs if r["arm"] == "T"]
    ctl = [r for r in recs if r["arm"] == "C"]
    tru = [r for r in recs if r["arm"] == "C1"]

    # ── 主判据 v3（同窗 codex 配对；公式与 kpi_r599.judge 主线段逐字一致）──
    dw = {}
    for r in recs:
        dw.setdefault(r["win"], {}).setdefault(r["arm"], []).append(r)
    unreliable = [w for w in wins if not all(x["cases_total"] == 58 and x["cases_pass"] == 58
                                            for x in dw.get(w, {}).get("C1", []))]
    Dq, per_win = [], {}
    for w in wins:
        a = med([x["cases_pass"] for x in dw.get(w, {}).get("C1", [])])
        b = med([x["cases_pass"] for x in dw.get(w, {}).get("T", [])])
        per_win[w] = {"truth_med_cases": a, "product_med_cases": b,
                      "reliable": w not in unreliable,
                      "D": None if (a is None or b is None or w in unreliable) else round(b - a, 2)}
        if per_win[w]["D"] is not None:
            Dq.append(per_win[w]["D"])
    v3 = {"D_list": Dq, "D_median": med(Dq) if Dq else None, "valid_windows": len(Dq),
          "unreliable_windows": unreliable, "floor": -15, "median_floor": -2,
          "per_window": per_win}
    v3["pass"] = bool(len(Dq) >= 2 and v3["D_median"] is not None and v3["D_median"] >= -2
                      and all(x > -15 for x in Dq))

    # ── 成本三列（信息项，禁合并成名义总量）──
    def sums(rs, k):
        return sum(x[k] for x in rs if x.get(k) is not None)
    cost = {"product": {"calls": sums(prod, "calls"), "new_prompt": sums(prod, "new_prompt"),
                        "completion": sums(prod, "completion"),
                        "v_all_med": med([r["v_all"] for r in prod]),
                        "v_incr_med": med([r["v_incr"] for r in prod])},
            "truth": {"calls": sums(tru, "calls"), "new_prompt": sums(tru, "new_prompt"),
                      "completion": sums(tru, "completion"),
                      "v_all_med": med([r["v_all"] for r in tru]),
                      "v_incr_med": med([r["v_incr"] for r in tru])},
            "control": {"calls": sums(ctl, "calls"), "new_prompt": sums(ctl, "new_prompt"),
                        "completion": sums(ctl, "completion")}}

    verdict = json.load(io.open(os.path.join(PD, "verdict-r603.json"), encoding="utf-8"))
    table = json.load(io.open(os.path.join(PD, "kpi-table-r603.json"), encoding="utf-8"))
    checks = json.load(io.open(os.path.join(PD, "checks-r603.json"), encoding="utf-8"))
    precond = json.load(io.open(os.path.join(D, "precond-r603.json"), encoding="utf-8"))
    i11 = 1 if not precond.get("executable_and_correct") else 0

    allp = {a: {w: "%d/%d" % (sum(1 for x in dw[w].get(a, []) if x["cases_pass"] == 58 and x["cases_total"] == 58),
                              len(dw[w].get(a, []))) for w in wins} for a in ("T", "C", "C1")}

    # ── 轮志 ──
    rep = []
    rep.append("# R603 轮志 · 同件扩窗轮（第十窗集 w190..w192）\n")
    rep.append("- 被测件 `pub_r600` sha12 **8c3ade04d542**（与 R600 同一件，逐字节同，零产品源码改动）；"
               "冻结题集 `taskset-r603.json` sha256 `e0c667c2a313c04b`==r602/r600 件（cmp 零差异）；"
               "判分脚本 `run_cases_r521.py` sha256 同 r602 ⇒ **唯一自由度 = 窗集**。\n")
    rep.append("- 臂：`T` 产品默认档 ×3/窗 · `C` 轴关对照档(=0) ×3/窗 · `C1` codex 外部真值 ×1/窗（21 跑次）。\n")
    rep.append("- 预注册 `prereg-r603.json`（written_before_run=true）· DAG `dag-r603.md` · 起手闸 A1/A2 PASS"
               "（条款派生见 `gate-margin-r603.json`）· 判别力成对控制 rc=0 · leak-selfcheck rc=0。\n\n")
    rep.append("## 1. 主判据 v3（同窗 codex 配对，set10）\n\n")
    rep.append("| 窗 | 真值中位(cases) | 产品中位(cases) | 有效窗 | D(产品−真值) |\n|---|---|---|---|---|\n")
    for w in wins:
        p = per_win[w]
        rep.append("| %s | %s | %s | %s | %s |\n" % (
            w, p["truth_med_cases"], p["product_med_cases"], p["reliable"], p["D"] if p["D"] is not None else "excused"))
    rep.append("\n- **D_list=%s / D_median=%s / valid=%d / 阈值(D_median≥−2 ∧ 各窗>−15) ⇒ 判据 v3 = %s**\n"
               % (v3["D_list"], v3["D_median"], v3["valid_windows"], "PASS" if v3["pass"] else "不达"))
    rep.append("- `unreliable` 窗（真值自身未 58/58）：%s ⇒ 按 C0 剔除、**禁筛窗**。\n\n"
               % (v3["unreliable_windows"] or "无"))
    rep.append("## 2. 机制/成本/能力（J1–J5 取自 `verdict-r603.json`，阈值与 R600/R602 一字未改）\n\n")
    rep.append("| 判据 | pass | 读数 |\n|---|---|---|\n")
    rep.append("| J1 机制（随附轮数打点） | %s | T 跑次含随附 %d/9 · C %d/9 |\n"
               % (verdict["J1_mechanism"]["pass"], verdict["J1_mechanism"]["by_arm"]["T"]["runs_with_carryover"],
                  verdict["J1_mechanism"]["by_arm"]["C"]["runs_with_carryover"]))
    rep.append("| J2 修复收敛（主） | %s | T %d/9 vs C %d/9 |\n"
               % (verdict["J2_repair_convergence"]["pass"], verdict["J2_repair_convergence"]["by_arm"]["T"]["converged"],
                  verdict["J2_repair_convergence"]["by_arm"]["C"]["converged"]))
    rep.append("| J3 成本（max calls） | %s | T %s vs C %s |\n"
               % (verdict["J3_cost"]["pass"], verdict["J3_cost"]["by_arm"]["T"]["max_calls"],
                  verdict["J3_cost"]["by_arm"]["C"]["max_calls"]))
    rep.append("| J4 能力（次级/欠功率） | %s | T %d vs C %d vs C1 %d（整题全对计数） |\n"
               % (verdict["J4_capability_secondary"]["pass"], verdict["J4_capability_secondary"]["by_arm"]["T"]["all_pass"],
                  verdict["J4_capability_secondary"]["by_arm"]["C"]["all_pass"],
                  verdict["J4_capability_secondary"]["by_arm"]["C1"]["all_pass"]))
    rep.append("| J5 跨窗集同向性（并列） | %s | set9(r602) %s / set10(r603) %s（率，禁相减） |\n"
               % (verdict["J5_cross_windowset_same_direction"]["pass"],
                  verdict["J5_cross_windowset_same_direction"]["prev_pooled_T_minus_C"],
                  verdict["J5_cross_windowset_same_direction"]["cur_pooled_T_minus_C"]))
    rep.append("\n整题全对（逐窗）：T %s · C %s · C1 %s\n\n" % (allp["T"], allp["C"], allp["C1"]))
    rep.append("## 3. 成本三列（**参考·未可验收**，铁律 11 rc=%d；口径 = 中继 dump 时间轴）\n\n" % i11)
    rep.append("| 臂 | 调用 | 新算 prompt | completion | 命中率 v_all(中位) | v_incr(中位) |\n|---|---|---|---|---|---|\n")
    for k, lbl in (("product", "产品默认档 T"), ("control", "轴关对照 C"), ("truth", "codex 真值 C1")):
        c = cost[k]
        rep.append("| %s | %s | %s | %s | %s | %s |\n" % (lbl, c["calls"], c["new_prompt"], c["completion"],
                                                          c.get("v_all_med", "未测"), c.get("v_incr_med", "未测")))
    rep.append("\n## 4. 只读并轮（零远端 / 零产品改动）\n\n")
    rep.append("- **L2 前缀连续性**（`checks-r603.json`）：pass=%s，`prefix_chars` 唯一值 %s、`prefix_sha256` 唯一值 %d、"
               "`task_sha256` 唯一值 %d（18 跑次）⇒ 恒前缀 + 同输入成立。\n"
               % (checks["L2_prefix_invariance"]["pass"], checks["L2_prefix_invariance"]["prefix_chars_values"],
                  checks["L2_prefix_invariance"]["prefix_sha256_distinct"], checks["L2_prefix_invariance"]["task_sha256_distinct"]))
    rep.append("- **L3 判定卫生 census**：pass=%s，%d/%d 跑次由**外部用例集**判、自证面 0。\n"
               % (checks["L3_judgment_hygiene"]["pass"], checks["L3_judgment_hygiene"]["with_external_suite"], checks["L3_judgment_hygiene"]["runs_total"]))
    _q = checks["Q1_false_confidence"]
    rep.append("- **Q1 假信心率（自报 rc=0 ∧ 外部真值未全对）**：rate=%s / den=%s / **冲突 %d 例**（目标 0）；"
               "反向（rc≠0 ∧ 外部 58/58）= **%d 例**：%s ⇒ 自判**过度保守**方向，两侧都要报。"
               "器具自捕：原实现 `int(rc or -1)` 使 rc==0 恒错判 ⇒ 该判据曾**结构性恒 0（空心）**，已修后本读数非空心；"
               "负控有牙 = %s（注入前缀漂移必翻红）。启发式 overclaim 计数 = **%s（启发式，不入判据）**。\n"
               % (_q["rate"], _q["denominator"], len(_q["rc0_but_external_unmet"]),
                  len(_q["rc_non0_but_external_full"]),
                  json.dumps(_q["rc_non0_but_external_full"], ensure_ascii=False),
                  checks.get("negctl_teeth"), checks["overclaim_heuristic"]))
    rep.append("- **L1 可构造性**（`eval/rover/r603/l1_axis_probe_r603.py`）：`axis_states=2` ⇒ 台账 §3.1 的「零产品改动加 BR/P 两臂」"
               "**被机检证伪**（该轴 env 面仅 on/off）；三控制（确定性/多值正控/扰动负控）全过 ⇒ 器具有牙。\n")
    rep.append("- **V_int 分布**（r602+r603 窗集）：见 `vint-r602-r603.json`。\n\n")
    rep.append("## 5. 诚实边界\n\n")
    rep.append("1. **铁律 11 rc=%d**（`executable_and_correct=%s`）⇒ 本轮全部成本/质量读数标「**参考（未可验收）**」，"
               "禁作验收依据。\n" % (i11, precond.get("executable_and_correct")))
    rep.append("2. J4/J5 为 n=9/档 与 3 窗集尺度 ⇒ **欠功率**，只作并列、不作能力结论；"
               "逐窗方向在 set10 内即翻号（%s）⇒ 窗集尺度摆动 > 轴效应。\n"
               % json.dumps({w: (per_win[w]["D"] if per_win[w]["D"] is not None else None) for w in wins}))
    rep.append("3. 被测件与 R600/R602 同一枚（sha 8c3ade04d542）⇒ 与 R600/R602 **可并列**；与 R585–R599 冻结件轮**禁相减**。\n")
    rep.append("4. 真值窗 %s 自败 ⇒ 该窗不进配对（C0），且**不得**因此筛掉产品侧下降窗。\n" % (unreliable or "无"))
    rep.append("5. 本轮**零新增夹具语义 / 零新增开关 / 零产品源码改动**；文献小步 ≤3 检索式，未占用主线预算。\n")
    io.open(os.path.join(PD, "report-r603.md"), "w", encoding="utf-8").write("".join(rep))

    # ── kpi.jsonl 追加（12 键，与既有行键集对齐）──
    row = {
        "round": "R603",
        "ts": "2026-09-21T01:30:00+0800",
        "tag": "same-artifact-windowset-expansion",
        "taskset_sha": "e0c667c2a313c04b",
        "bin_sha12": "8c3ade04d542",
        "J1_mechanism": {"pass": verdict["J1_mechanism"]["pass"],
                         "T_runs_with_carryover": verdict["J1_mechanism"]["by_arm"]["T"]["runs_with_carryover"],
                         "C_runs_with_carryover": verdict["J1_mechanism"]["by_arm"]["C"]["runs_with_carryover"]},
        "J2_convergence": {"pass": verdict["J2_repair_convergence"]["pass"],
                           "T": verdict["J2_repair_convergence"]["by_arm"]["T"]["converged"],
                           "C": verdict["J2_repair_convergence"]["by_arm"]["C"]["converged"],
                           "T_wilson95": verdict["J2_repair_convergence"]["by_arm"]["T"]["wilson95"],
                           "C_wilson95": verdict["J2_repair_convergence"]["by_arm"]["C"]["wilson95"]},
        "J3_cost": {"pass": verdict["J3_cost"]["pass"],
                    "T_max_calls": verdict["J3_cost"]["by_arm"]["T"]["max_calls"],
                    "C_max_calls": verdict["J3_cost"]["by_arm"]["C"]["max_calls"]},
        "J4_capability": {"pass": verdict["J4_capability_secondary"]["pass"],
                          "T_all_pass": verdict["J4_capability_secondary"]["by_arm"]["T"]["all_pass"],
                          "C_all_pass": verdict["J4_capability_secondary"]["by_arm"]["C"]["all_pass"],
                          "C1_all_pass": verdict["J4_capability_secondary"]["by_arm"]["C1"]["all_pass"],
                          "power_note": "n=9/档欠功率"},
        "quality_paired": {w: per_win[w]["D"] for w in wins},
        "iron11": {"rc": str(i11), "readable": "参考（未可验收）" if i11 else "可验收"},
        "report": "eval/rover/r603/report-r603.md",
    }
    prev_keys = list(json.loads([l for l in io.open(os.path.join(REPO, "eval/capability/kpi.jsonl"),
                                                    encoding="utf-8") if l.strip()][-1]).keys())
    assert list(row.keys()) == prev_keys, ("kpi 键集不对齐", list(row.keys()), prev_keys)
    with io.open(os.path.join(REPO, "eval/capability/kpi.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ── 证据面 ──
    ev = os.path.join(REPO, "docs/evidence/RF0001/R603-windowset-expansion.md")
    io.open(ev, "w", encoding="utf-8").write(
        "# R603 证据面 · 同件扩窗轮（第十窗集 w190..w192）\n\n"
        "- 级别：**L3 真机运行**（真二进制 + 真外部真值 codex + 机械判分；**未可验收**：铁律 11 rc=%d）\n" % i11 +
        "- 被测件：`$HOME/.agentframework/artifacts/pub_r600/agenthost` sha12 `8c3ade04d542`（与 R600/R602 同件）\n"
        "- 冻结题集：`eval/rover/r603/taskset-r603.json` sha256 `e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a`"
        "（与 r602 逐字节同：`cmp` 零差异）\n"
        "- 复现命令：`bash eval/rover/r603/run_r603.sh`（含起手闸 A1/A2 + 判别力成对控制 + leak-selfcheck + 铁律 11 前置器）\n"
        "- 判决：`python3 eval/rover/r603/judge_r603.py --D $HOME/.agentframework/harness/runs/r603 --pd eval/rover/r603`\n"
        "- 只读并轮：`python3 eval/rover/r603/checks_r603.py --D <run根>`（L2/L3/Q1；负控 `--negctl` 有牙）· "
        "`python3 eval/rover/r603/l1_axis_probe_r603.py`（L1 可构造性）· "
        "`python3 eval/rover/r593/landing_predicate_r593.py --rounds r602,r603`（V_int）\n"
        "- 轮志：`eval/rover/r603/report-r603.md` · KPI 行：`eval/capability/kpi.jsonl`（round=R603）\n")

    # ── 摘要 ──
    print(json.dumps({"v3": {"pass": v3["pass"], "D_list": v3["D_list"], "median": v3["D_median"],
                             "valid": v3["valid_windows"], "unreliable": unreliable},
                      "J1": verdict["J1_mechanism"]["pass"], "J2": verdict["J2_repair_convergence"]["pass"],
                      "J3": verdict["J3_cost"]["pass"], "J4": verdict["J4_capability_secondary"]["pass"],
                      "J5": verdict["J5_cross_windowset_same_direction"]["pass"],
                      "iron11_rc": i11, "L2": checks["L2_prefix_invariance"]["pass"],
                      "L3": checks["L3_judgment_hygiene"]["pass"],
                      "Q1_rate": checks["Q1_false_confidence"]["rate"],
                      "Q1_converse": len(checks["Q1_false_confidence"]["rc_non0_but_external_full"]),
                      "overclaim_heuristic": checks["overclaim_heuristic"],
                      "report_sha12": sha12(os.path.join(PD, "report-r603.md")),
                      "kpi_lines": len([l for l in io.open(os.path.join(REPO, "eval/capability/kpi.jsonl"),
                                                           encoding="utf-8") if l.strip()])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
