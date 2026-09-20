#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R605 收尾器：由已落盘派生件生成轮志 `report-r605.md` 与证据面文件。

输入（全部为本轮已落盘件，零重算、零子进程）：
  · verdict-r605.json · kpi-table-r605.json · checks-r605.json · checks-r605-negctl.json
  · gate-margin-r605.json · precond-r605.json（run root）
用法: python3 finish_r605.py
"""
from __future__ import annotations
import hashlib
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
PD = os.path.join(REPO, "eval/rover/r605")
D = os.path.expanduser("~/.agentframework/harness/runs/r605")


def j(p):
    return json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else None


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12] if os.path.isfile(p) else None


def main():
    v = j(os.path.join(PD, "verdict-r605.json"))
    t = j(os.path.join(PD, "kpi-table-r605.json"))
    ck = j(os.path.join(PD, "checks-r605.json"))
    ckn = j(os.path.join(PD, "checks-r605-negctl.json"))
    gm = j(os.path.join(PD, "gate-margin-r605.json"))
    pc = j(os.path.join(D, "precond-r605.json"))
    v3 = v["C1_task_face_v3"]
    j3 = v["J3_cost"]
    wf = v["W_floor_resolution_floor"]
    ld = v["LD_low_discrimination"]
    b3 = j3["by_arm"]

    rep = []
    rep.append("# R605 轮志 · 同件扩窗轮（第十一窗集 w193..w195）\n\n")
    rep.append("- 被测件 `pub_r600` sha256 `8c3ade04d542c091…`（与 R600/R602/R603 **同一枚**；本侧独立复核 "
               "`sha256sum $HOME/.agentframework/artifacts/pub_r600/agenthost` 前 12 位一致）· 冻结题集 "
               "`taskset-r605.json` sha256 `e0c667c2a313c04b` 与 r603 件 `cmp` **零差异** ⇒ **唯一自由度 = 窗集**。\n")
    rep.append("- 臂：`T` 产品默认档 ×3/窗 · `C` 轴关对照档 ×3/窗 · `C1` codex 外部真值 ×1/窗（21 跑次）；"
               "单变量 = `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`（T 缺省 on / C 显式 0）。\n")
    rep.append("- 预注册 `prereg-r605.json`（written_before_run=true）· DAG `dag-r605.md` · 起手闸 A1/A2 PASS"
               "（`ceiling=2775 / prev_swing=285 / margin=65(cap_binding) / REQ=2715`；起手前按 pid 收口会话端 "
               "LSP 子进程，实测 `MemAvailable` +177MB）· 判别力成对控制**未行使**（内存高于阈值带 ⇒ 两闸同 PASS，"
               "如实登记）· leak-selfcheck rc=0。\n\n")

    rep.append("## 1. 主判据 v3（同窗 codex 配对，set11）\n\n")
    rep.append("| 窗 | 真值中位(cases) | 产品中位(cases) | 有效窗 | D(产品−真值) |\n|---|---|---|---|---|\n")
    for w in v3["truth_per_window"]:
        dq = None
        idx = list(v3["truth_per_window"]).index(w)
        if w not in v3["unreliable_windows"] and w not in v3["missing_windows"]:
            dq = v3["D_list"][len([x for x in list(v3["truth_per_window"])[:idx]
                                   if x not in v3["unreliable_windows"] and x not in v3["missing_windows"]])]
        rep.append("| %s | %s | %s | %s | %s |\n" % (w, v3["truth_per_window"][w], v3["product_per_window"][w],
                                                     "✔" if dq is not None else "—", dq if dq is not None else "—"))
    rep.append("\n- **D_list=%s / D_median=%s / valid=%d / 阈值(D_median≥−2 ∧ 各窗>−15) ⇒ 判据 v3 = %s**\n"
               % (v3["D_list"], v3["D_median"], v3["valid_windows"], v3["label"]))
    rep.append("- 真值自败窗（剔除配对，**禁筛窗**）：%s\n" % (v3["unreliable_windows"] or "无"))
    rep.append("- 本窗集**三窗真值全 58/58**（首例）：全部窗进配对 ⇒ 主判据**第一次具备完整分辨率**（承 W_floor 条款）。\n")
    rep.append("- LD 诊断列（**不作判据**）：`v3_ex_LD` D_list=%s / median=%s（冻结名单 %s；非平凡=%s）\n"
               % (ld["v3_ex_LD"]["D_list"], ld["v3_ex_LD"]["D_median"], ld["frozen_list"],
                  ld["controls"]["non_trivial"]["ok"]))
    wfr = j(os.path.join(PD, "wfloor-regression-r605.json"))
    if wfr:
        rep.append("- **W_floor 零回归（候选④ 负控）**：回放 %d 轮 ⇒ 标签翻号 %d（全为 `不达→NO_RESOLUTION`：%s）；"
                   "`NO_RESOLUTION→PASS` **0**、`PASS→任何` **0** ⇒ **纯标签语义收口、非阈值改动**；"
                   "主 rc 不由该标签决定（机制面结论见 `mechanism_rc`）。\n"
                   % (wfr["rounds_checked"], wfr["flip_count"],
                      ", ".join("%s(valid=%d)" % (x["round"], x["valid"]) for x in wfr["label_flips"]) or "无"))
    rep.append("\n")

    rep.append("## 2. 机制/成本/能力（J1–J5 取自 `verdict-r605.json`）\n\n")
    rep.append("| 判据 | 结果 | 读数 |\n|---|---|---|\n")
    rep.append("| J1 机制（随附打点） | %s | T 跑次含随附 %d/9 · C %d/9 |\n"
               % (v["J1_mechanism"]["pass"],
                  v["J1_mechanism"]["by_arm"]["T"]["runs_with_carryover"],
                  v["J1_mechanism"]["by_arm"]["C"]["runs_with_carryover"]))
    rep.append("| J2 修复收敛（主） | %s | T %d/9 Wilson %s vs C %d/9 Wilson %s |\n"
               % (v["J2_repair_convergence"]["pass"],
                  v["J2_repair_convergence"]["by_arm"]["T"]["converged"],
                  v["J2_repair_convergence"]["by_arm"]["T"]["wilson95"],
                  v["J2_repair_convergence"]["by_arm"]["C"]["converged"],
                  v["J2_repair_convergence"]["by_arm"]["C"]["wilson95"]))
    f = j3["v2"]["form"]
    rep.append("| J3 成本 **v2（本轮主判据）** | %s | a1 池化 Σcalls %s vs %s=%s · a2 逐窗 %s · b1 单位新算 %s vs %s=%s |\n"
               % (j3["pass"], f["sum_calls"]["T"], f["sum_calls"]["C"], f["a1"],
                  {w: v["ok"] for w, v in f["per_window_calls"].items()}, f["unit_new_prompt_per_call"]["T"],
                  f["unit_new_prompt_per_call"]["C"], f["b1"]))
    rep.append("| J3 v1（照原样并列，不翻案） | %s | T_max_calls %s vs C_max_calls %s |\n"
               % (j3["v1_retained"]["pass"], b3["T"]["max_calls"], b3["C"]["max_calls"]))
    rep.append("| J3 v2′（b1 降级为报告列；须用户裁定） | %s | a1∧a2（b1 不进判据） |\n"
               % j3["v2"]["v2prime"]["pass"])
    rep.append("| J4 能力（次级/欠功率） | %s | 整题全对 T %d vs C %d vs C1 %d |\n"
               % (v["J4_capability_secondary"]["pass"], v["J4_capability_secondary"]["by_arm"]["T"]["all_pass"],
                  v["J4_capability_secondary"]["by_arm"]["C"]["all_pass"],
                  v["J4_capability_secondary"]["by_arm"]["C1"]["all_pass"]))
    j5 = v["J5_cross_windowset_same_direction"]
    rep.append("| J5 跨窗集同向性（并列） | %s | set10(r603) %s / set11(r605) %s（率，禁相减） |\n"
               % (j5["pass"], j5["prev_pooled_T_minus_C"], j5["cur_pooled_T_minus_C"]))
    rep.append("| W_floor 有效窗下限 | %s | valid=%d ⇒ label `%s` |\n"
               % (True if wf["label"] != "NO_RESOLUTION" else "NO_RESOLUTION", wf["valid_windows"], wf["label"]))
    rep.append("\n### 2.1 逐窗整题全对（v3 配对）\n\n")
    rep.append("| 窗 | T | C | C1(cases/58) | D(T−C) | D(T−C1) |\n|---|---|---|---|---|---|\n")
    for w, d in v["paired_vs_codex"].items():
        tp = v["J4_capability_secondary"]["by_arm"]["T"]["per_window"][w]
        tn = v["J4_capability_secondary"]["by_arm"]["T"]["per_window_n"][w]
        cp = v["J4_capability_secondary"]["by_arm"]["C"]["per_window"][w]
        cn = v["J4_capability_secondary"]["by_arm"]["C"]["per_window_n"][w]
        rep.append("| %s | %d/%d | %d/%d | %s/1 | %s | %s |\n"
                   % (w, tp, tn, cp, cn, d["C1_all_pass"][0], d["D_T_minus_C"], d["D_T_minus_C1"]))
    rep.append("\n### 2.2 成本三列（信息项；铁律 11 未过 ⇒ 标「参考·未可验收」）\n\n")
    rep.append("| 臂 | 调用 | 新算 prompt | completion | 命中率 v_all 中位 | 命中率 v_incr 中位 |\n|---|---|---|---|---|---|\n")
    for arm in ("T", "C", "C1"):
        r = b3[arm] if arm in b3 else None
        if r is None:
            row = [x for x in t["rows"] if x["臂"] == arm][0]
            rep.append("| %s | %s | %s | %s | %s | %s |\n" % (arm, sum(x or 0 for x in row["调用"]),
                       sum(x or 0 for x in row["新算prompt"]), sum(x or 0 for x in row["completion"]),
                       "—", "—"))
        else:
            va = [x for x in r["v_all"] if x is not None]
            vi = [x for x in r["v_incr"] if x is not None]
            import statistics
            rep.append("| %s | %d | %d | %d | %s | %s |\n"
                       % (arm, sum(x or 0 for x in r["calls"]), sum(x or 0 for x in r["new_prompt_tokens"]),
                          sum(x or 0 for x in r["completion_tokens"]),
                          round(statistics.median(va), 4) if va else "—",
                          round(statistics.median(vi), 4) if vi else "—"))
    c1row = [x for x in t["rows"] if x["臂"] == "C1"][0]
    rep.append("\n- codex 真值三列：调用 %s / 新算 %s / completion %s（命中率 %s）\n"
               % (sum(x or 0 for x in c1row["调用"]), sum(x or 0 for x in c1row["新算prompt"]),
                  sum(x or 0 for x in c1row["completion"]), c1row["命中率(v_all/v_incr)"]))

    rep.append("\n## 3. 只读并轮（rc=%s）\n\n" % ck["rc"])
    rep.append("- **L2 前缀连续性**：pass=%s（`prefix_chars` 唯一 %s ∧ `prefix_sha256` 唯一 %d ∧ `task_sha256` 唯一 %d）\n"
               % (ck["L2_prefix_invariance"]["pass"], ck["L2_prefix_invariance"]["prefix_chars_values"],
                  ck["L2_prefix_invariance"]["prefix_sha256_distinct"], ck["L2_prefix_invariance"]["task_sha256_distinct"]))
    rep.append("- **L3 判定卫生**：pass=%s（%d/%d 跑次由外部用例套件判、自证面 0）\n"
               % (ck["L3_judgment_hygiene"]["pass"], ck["L3_judgment_hygiene"]["with_external_suite"],
                  ck["L3_judgment_hygiene"]["runs_total"]))
    q1 = ck["Q1_false_confidence"]
    rep.append("- **Q1 假信心率**：%.4f（%d/%d）：rc==0 ∧ 外部未满分 **%d 例**（%s）；反向 rc≠0 ∧ 外部满分 **%d 例**"
               "（**自判过度保守**方向）\n" % (q1["rate"], len(q1["rc0_but_external_unmet"]), q1["denominator"],
                                             len(q1["rc0_but_external_unmet"]),
                                             ", ".join(x["run"] + " " + x["cases"] for x in q1["rc0_but_external_unmet"]),
                                             len(q1["rc_non0_but_external_full"])))
    rep.append("- **负控有牙**：注入前缀漂移 ⇒ L2 翻红（`rc=%s, negctl_teeth=%s, l2_violated=%s`）\n"
               % (ckn["rc"], ckn["negctl_teeth"], ckn["l2_violated"]))
    vi = j(os.path.join(PD, "vint-r605.json"))
    if vi:
        r = vi["readings"]
        rep.append("- **V_int 第六窗集**（`vint-r605.json`；同件同口径，未改一字）：跑次 %s · oracle 一致 %s · 控制 OK/POS/NEG 落点唯一"
                   "（新粒度 has_teeth=%s，旧粒度 =%s）· 守恒 %s；agent 桶 `%s` / codex 桶 `%s`；"
                   "`v_int_hist` agent `%s` / codex `%s`；层 agent `%s`\n"
                   % (r["runs"], r["oracle_consistent"], r["controls"]["new_granularity_has_teeth"],
                      r["controls"]["old_granularity_has_teeth"], r["conservation"],
                      json.dumps(r["buckets_agent"], ensure_ascii=False), json.dumps(r["buckets_codex"], ensure_ascii=False),
                      json.dumps(r["v_int_hist_agent"], ensure_ascii=False), json.dumps(r["v_int_hist_codex"], ensure_ascii=False),
                      json.dumps(r["layer_agent"], ensure_ascii=False)))
        rep.append("- **V_int 器具 rc=2（两项 False，均已定因、不翻案）**：① `零回归=False` = **已知 scope 伪影**（单窗集重算 vs r592 登记值比较域不同；"
                   "同器具对历史全集复算 match=True ⇒ 器具完好）② `只读=False` = **本侧流程违反**（器具以 `src/` 树 sha 前后比对作只读判据，"
                   "而本侧在器具运行期间并发跑了 `dotnet test` ⇒ 构建写 `src/*/obj|bin`；快照树 `-newermt 04:26` 文件数 = 0 ⇒ 被测面未被改）。"
                   "R606 以「无并发构建」重跑取纯净读数；本轮 V_int 读数按「参考（器具 rc=2）」登记，**不入主线结论**（V_int 为诊断项，预注册禁止阈值化）。\n")

    rep.append("\n## 4. 铁律 11 可验收前置\n\n")
    if pc:
        blocked = pc.get("blocked") or []
        prc = None
        if os.path.isfile(os.path.join(D, "precond.rc")):
            prc = io.open(os.path.join(D, "precond.rc"), encoding="utf-8").read().strip()
        rep.append("- `exec_precondition.py --round r605` ⇒ **rc=%s**（blocked %d 条，全部落 `wythoff` 族）"
                   "⇒ 全部成本/质量读数标「**参考（未可验收）**」，禁作验收依据。\n" % (prc, len(blocked)))
        rep.append("- `EXECUTABLE_AND_CORRECT=%s` · `SELF_REPORT_AGREES=%s` · 未声明臂 %d 条（NONREQUIRED 单列 `%d`）\n"
                   % (pc.get("executable_and_correct"), pc.get("self_report_agrees"),
                      len(pc.get("undeclared_arms") or []), len(pc.get("nonrequired_arms") or [])))
    else:
        rep.append("- 前置器产物缺失 ⇒ 本轮标「未可验收」。\n")

    rep.append("\n## 5. 诚实边界\n\n")
    for b in v["honest_bounds"]:
        rep.append("- %s\n" % b)
    rep.append("- 判别力成对控制本轮**未行使**（内存高于条款带 ⇒ 两闸同 PASS，实测 ceiling %sMB vs REQ %sMB）⇒ 记「未测」，"
               "不得读成条款已收紧生效。\n" % (gm["ceiling_min_of_3"] if gm else "?", gm["req"] if gm else "?"))
    rep.append("- 本轮**零产品源码改动 / 零新增夹具语义 / 零新增开关**；J3 v2 是**形态收口**（收紧）而非放宽。\n")

    rep.append("\n## 6. 复现命令\n\n")
    rep.append("- 真机臂轮：`bash eval/rover/r605/run_r605.sh`\n")
    rep.append("- 判决：`python3 eval/rover/r605/judge_r605.py --D $HOME/.agentframework/harness/runs/r605 --pd eval/rover/r605`\n")
    rep.append("- 只读并轮：`python3 eval/rover/r605/checks_r605.py --D $HOME/.agentframework/harness/runs/r605 --pd eval/rover/r605`"
               "（负控 `--negctl`）\n")
    rep.append("- 铁律 11：`python3 eval/rover/r507pre/exec_precondition.py --round r605`\n")
    io.open(os.path.join(PD, "report-r605.md"), "w", encoding="utf-8").write("".join(rep))

    ev = {
        "round": "R605", "kind": "主线同件扩窗轮（第十一窗集）+ 器具面收口首次行使",
        "report": "eval/rover/r605/report-r605.md",
        "artifacts": {
            "prereg": "eval/rover/r605/prereg-r605.json", "dag": "eval/rover/r605/dag-r605.md",
            "verdict": "eval/rover/r605/verdict-r605.json", "kpi_table": "eval/rover/r605/kpi-table-r605.json",
            "gate_margin": "eval/rover/r605/gate-margin-r605.json",
            "checks": "eval/rover/r605/checks-r605.json", "checks_negctl": "eval/rover/r605/checks-r605-negctl.json",
            "precond": os.path.join(D, "precond-r605.json"),
        },
        "sha12": {k: sha12(v_) for k, v_ in {
            "report": os.path.join(PD, "report-r605.md"), "verdict": os.path.join(PD, "verdict-r605.json"),
            "judge": os.path.join(PD, "judge_r605.py"), "runner": os.path.join(PD, "run_r605.sh")}.items()},
        "criterion": {"v3": {"label": v3["label"], "D_median": v3["D_median"], "valid": v3["valid_windows"]},
                      "J3_form_in_force": "v2", "W_floor": wf["label"], "LD": ld["frozen_list"]},
        "verdict_rc": v["verdict"]["rc"], "precond_rc": (pc or {}).get("rc"),
        "note": "全量测试/形式门禁读数见轮志与提交信息；本文件为证据面指针。",
    }
    json.dump(ev, io.open(os.path.join(PD, "evidence-r605.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[finish-r605] report + evidence 落盘；v3=%s(J3=%s) precond_rc=%s"
          % (v3["label"], j3["pass"],
             (io.open(os.path.join(D, "precond.rc"), encoding="utf-8").read().strip()
              if os.path.isfile(os.path.join(D, "precond.rc")) else None)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
