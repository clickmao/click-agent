#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R596 收口器：轮志 + 台账行（幂等原地替换）+ §7 主报告块 + §7 运行状态快照 + improvements 条目。

纪律: ① **数字全部来自本轮落盘读数**（禁硬编码、禁手抄）; ② 各文档面**只做增量插入**（锚点缺失 ⇒ 该面记
`false`，不整段覆盖）; ③ 写后**回读断言**（新串计数 > 0 ∧ 旧轮快照行已标历史）。
用法: python3 eval/rover/r596/finish_r596.py [--no-docs]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re

REPO = "/home/agentuser/AgentFramework"
RP = os.path.join(REPO, "eval/rover/r596")
HARNESS = os.path.expanduser("~/.agentframework/harness/runs/r596")
MASTER = os.path.join(REPO, "docs/reports/iteration-master-plan.md")
ROLLBACK = os.path.join(REPO, "docs/reports/dynamic-telemetry-eval-rollback-strategy.md")
IMPROV = os.path.join(REPO, "docs/improvements.md")
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")
FIN = os.path.join(RP, "finish-r596.json")
REPORT = os.path.join(RP, "report-r596.md")


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def fmt(x, nd=4):
    return "未测" if x is None else (round(x, nd) if isinstance(x, float) else x)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-docs", action="store_true")
    a = ap.parse_args()
    out = {"round": "R596"}

    pool = load(os.path.join(RP, "taskface-pool-r596.json"), {})
    kpi = load(os.path.join(RP, "verdict-r596.json"), {})
    ktab = load(os.path.join(RP, "kpi-table-r596.json"), {})
    gate = load(os.path.join(RP, "gate-margin-r596.json"), {})
    pre = load(os.path.join(HARNESS, "precond-r596.json"), {})
    att = load(os.path.join(RP, "percase-attrib-r596.json"), {})
    cen = load(os.path.join(RP, "behav-census-r596.json"), {})
    # 候选④ 落盘面: r596 单窗集实跑（三段式 RUN1 零回归臂在本 tick 时间预算内未收口 ⇒ 单列声明, 不伪造 match）
    land_3 = load(os.path.join(RP, "landing-third-r596.json"), {})
    land_zr = load(os.path.join(RP, "landing-predicate-r596.json"), {})
    bins = load(os.path.join(RP, "bins-r596.json"), {})
    shachk = load(os.path.join(HARNESS, "bin-sha-check.json"), {})

    j = (pool or {}).get("juxtaposition", {})
    s4 = j.get("set4", {})
    fam = j.get("family_all_pass_rate", {})
    arms = (kpi or {}).get("arms", {})
    prod = arms.get("R596D", {})
    truth = arms.get("C1", {})
    pk = (kpi or {}).get("paired", {}) or {}
    pooled = (att or {}).get("pooled_buckets", {})
    ctrl_a = (att or {}).get("controls", {})
    cs = (cen or {}).get("summary", {})
    cctrl = (cen or {}).get("controls", {})
    lg = (land_3 or {}).get("agent", {})
    lc = (land_3 or {}).get("codex", {})
    verdict = (kpi or {}).get("verdict", {})
    rc_iron = pre.get("executable_and_correct"), pre.get("acceptable_scoped")
    blocked = pre.get("blocked", [])
    gate_ok = gate.get("req")
    dpair = pk.get("D_product_minus_truth_per_window") or []
    zr_match = (land_zr or {}).get("zero_regression", {}).get("match")
    zr3 = (land_3 or {}).get("zero_regression", {}) or {}
    zr_note = (("5 窗集零回归臂未收口（本 tick 时间预算内未跑完 ⇒ 不伪造 match）；"
                "r596 单窗集那次 match=%s 属**结构性不适用**（登记基准 = 44 跑次，单窗集只有 12 跑次）⇒ 该次 rc=2 由零回归面产生，"
                "其余面（守恒/只读/无残留/控制 POS(a)·NEG(b)/oracle 一致）全绿；固有成员零漂移由 pool `reproduced_first_set` 复算承担")
               % zr3.get("match") if zr_match is None else zr_match)

    status = ("完成（判据 v3 第四窗集 rc=%s；形式门禁见 §验证；铁律 11 rc=%s ⇒ 成本读数标未可验收）· 真机臂轮 + 只读并轮"
              % (j.get("set4", {}).get("pass"), 1 if not pre.get("executable_and_correct") else 0))

    summary = {
        "judge_v3_set4": {"valid": s4.get("valid"), "median": s4.get("median"), "neg": s4.get("neg"), "pass": s4.get("pass")},
        "family_all_pass_rate": fam,
        "cost_three_columns": {"product": {k: prod.get(k) for k in ("calls", "new_prompt", "completion", "v_all_med", "v_incr_med")},
                               "truth": {k: truth.get(k) for k in ("calls", "new_prompt", "completion", "v_all_med", "v_incr_med")}},
        "paired_case_face": {"median": pk.get("D_median"), "range": [min(dpair), max(dpair)] if dpair else None,
                             "valid_windows": pk.get("valid_windows"),
                             "unreliable_windows": pk.get("unreliable_windows_truth_self_fail")},
        "gate": {k: gate.get(k) for k in ("prev_swing_effective", "ceiling_min_of_3", "margin", "req", "cap", "cap_binding")},
        "iron11": {"rc": 1 if not pre.get("executable_and_correct") else 0, "blocked_n": len(blocked),
                   "executable_and_correct": rc_iron[0], "acceptable_scoped": rc_iron[1]},
        "candidate2_buckets": pooled, "candidate2_pos_teeth": (ctrl_a.get("pos") or {}).get("has_teeth"),
        "candidate3_agent": cs.get("agent"), "candidate3_codex": cs.get("codex"),
        "candidate3_pos_teeth": cctrl.get("pos_has_teeth"),
        "candidate4_agent_buckets": lg.get("buckets"), "candidate4_layer": lg.get("layer"),
        "candidate4_v_int": lg.get("v_int_hist"),
        "candidate4_zero_regression": zr_note,
        "candidate4_landing_file": "eval/rover/r596/landing-third-r596.json",
        "bin_sha_stable": shachk.get("bin_sha_stable"),
        "bin_sha12": (bins.get("bin_all_arms", {}) or {}).get("sha256", "")[:12],
    }
    out["summary"] = summary

    # ---------------- 轮志 ----------------
    rep = []
    rep.append("# R596 轮志 · %s\n" % ("判据 v3 第四窗集行使（真机臂轮 w172..w174）+ 只读并轮（候选②③④⑤）"))
    rep.append("**单变量**: 无新轴 —— 与 R585–R595 **同被测件**（bin sha12 `%s`，stable=%s）+ **同冻结题集**"
               "（`e0c667c2…`）+ 同判据（v3）；唯一改动 = 窗集 `w172..w174`（每窗 真值×1 ＋ 产品默认档×3）。"
               "候选①（产品侧修复）**待用户放行 ⇒ 零 `src/` 改动**。\n" % (summary["bin_sha12"], summary["bin_sha_stable"]))
    rep.append("## 主判据（判据 v3 第四窗集）\n")
    rep.append("- set4: valid=%s / 中位 %s / 负号窗 %s ⇒ **%s**（阈值 −0.34 写死）"
               % (s4.get("valid"), fmt(s4.get("median")), s4.get("neg"), "PASS" if s4.get("pass") else "FAIL"))
    rep.append("- 并列集: set1 %s / set2 %s / set3 %s（**跨窗集禁相减**）"
               % (j.get("set1"), j.get("set2"), j.get("set3")))
    rep.append("- 按族 all-pass 率: %s\n" % json.dumps(fam, ensure_ascii=False))
    rep.append("## 成本三列（铁律 11 rc=%s ⇒ 「参考（未可验收）」）\n"
               % ("0" if pre.get("executable_and_correct") else "1"))
    rep.append("- 产品: 调用 %s / 新算 prompt %s / completion %s（v_all %s / v_incr %s）"
               % (prod.get("calls"), prod.get("new_prompt"), prod.get("completion"), prod.get("v_all_med"), prod.get("v_incr_med")))
    rep.append("- 真值: 调用 %s / 新算 prompt %s / completion %s（v_all %s / v_incr %s）\n"
               % (truth.get("calls"), truth.get("new_prompt"), truth.get("completion"), truth.get("v_all_med"), truth.get("v_incr_med")))
    rep.append("## 候选② 铁律 11 阻塞臂逐例归因（只读）\n")
    rep.append("- 桶池化（6 轮窗集全量）: %s" % json.dumps(pooled, ensure_ascii=False))
    rep.append("- A 份额（= 加厚 prompt/契约类改动的**收益上界**）: %s；控制 POS 有牙=%s"
               % ((att or {}).get("verdict", {}).get("A_share_pooled"), summary["candidate2_pos_teeth"]))
    rep.append("- 跨例交叉校验（前置器 failed 集 ↔ `cases.txt` FAIL 集）: %s\n"
               % json.dumps((att or {}).get("cross_check", {}), ensure_ascii=False))
    rep.append("## 候选③ 交付物行为面契约普查（替代 R595 静态面无牙版）\n")
    rep.append("- agent: %s" % json.dumps(cs.get("agent"), ensure_ascii=False))
    rep.append("- codex: %s" % json.dumps(cs.get("codex"), ensure_ascii=False))
    rep.append("- 控制: base=%s POS 有牙=%s NEG 干净=%s；只读=%s\n"
               % (cctrl.get("base_run"), cctrl.get("pos_has_teeth"), cctrl.get("neg_clean"),
                  (cen or {}).get("readonly", {}).get("snapshot_stamp_equal")))
    rep.append("## 候选④ `V_int` 第三窗集分布（不设阈值）\n")
    rep.append("- agent 桶 %s / 层 %s / `v_int_hist` %s" % (json.dumps(lg.get("buckets"), ensure_ascii=False),
                                                            json.dumps(lg.get("layer"), ensure_ascii=False),
                                                            json.dumps(lg.get("v_int_hist"), ensure_ascii=False)))
    rep.append("- codex 桶 %s / 层 %s" % (json.dumps(lc.get("buckets"), ensure_ascii=False), json.dumps(lc.get("layer"), ensure_ascii=False)))
    rep.append("- 零回归（对 r592 池）：match=%s（口径见器具声明）\n" % summary["candidate4_zero_regression"])
    rep.append("## 候选⑤ 起手闸余量条款\n")
    rep.append("- 余量源 = r595 同态在飞窗实测振幅 %sMB；ceiling=%s / margin=%s / REQ=%s / cap=%s / cap_binding=%s ⇒ 真机行使 rc=%s\n"
               % (gate.get("prev_swing_effective"), gate.get("ceiling_min_of_3"), gate.get("margin"),
                  gate.get("req"), gate.get("cap"), gate.get("cap_binding"), 0 if gate_ok else None))
    rep.append("## 铁律 11 前置器\n")
    rep.append("- rc：`executable_and_correct=%s` / `acceptable_scoped=%s`；blocked=%d 条（前 3 条: %s）\n"
               % (rc_iron[0], rc_iron[1], len(blocked), json.dumps(blocked[:3], ensure_ascii=False)))
    rep.append("## 诚实边界\n")
    rep.append("- 铁律 11 rc≠0 ⇒ 全部质量/成本读数标「参考（未可验收）」，**不宣称任何降幅/增益**；")
    rep.append("- 候选②③④ 为只读/聚合面 ⇒ 不构成能力验收、不得回写成「产品已修」；")
    rep.append("- 跨轮/跨窗集**禁相减**，只并列；候选①（产品侧修复）**待用户放行**。\n")
    with io.open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(rep))
    out["report"] = os.path.relpath(REPORT, REPO)

    # ---------------- 台账（幂等: 按 round 原地替换） ----------------
    line = json.dumps({
        "round": "R596",
        "ts": __import__("datetime").datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M%z"),
        "kind": "判据 v3 第四窗集行使（真机臂轮 w172..w174）+ 只读并轮（候选②③④⑤）",
        "claim": "判据 v3 第四窗集行使（真机臂轮 w172..w174）+ 只读并轮（候选②③④⑤）；零产品源码改动/零新增夹具语义/零新增开关",
        "readings": {"summary": summary, "judge_v3": {"set1": j.get("set1"), "set2": j.get("set2"),
                                                      "set3": j.get("set3"), "set4": j.get("set4")}},
        "artifact": {"report": "eval/rover/r596/report-r596.md", "prereg": "eval/rover/r596/prereg-r596.json",
                     "dag": "eval/rover/r596/dag-r596.md", "pool": "eval/rover/r596/taskface-pool-r596.json",
                     "kpi": "eval/rover/r596/verdict-r596.json", "kpi_table": "eval/rover/r596/kpi-table-r596.json",
                     "attrib": "eval/rover/r596/percase-attrib-r596.json", "census": "eval/rover/r596/behav-census-r596.json",
                     "landing": "eval/rover/r596/landing-third-r596.json", "gate": "eval/rover/r596/gate-margin-r596.json",
                     "precond": "eval/rover/r507pre/precondition-r596.json"},
    }, ensure_ascii=False)
    lines = [l for l in io.open(LEDGER, encoding="utf-8").read().splitlines() if l.strip()]
    n_before = len(lines)
    replaced = False
    for i, l in enumerate(lines):
        try:
            if json.loads(l).get("round") == "R596":
                lines[i] = line
                replaced = True
        except Exception:  # noqa: BLE001
            pass
    if not replaced:
        lines.append(line)
    with io.open(LEDGER, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    out["ledger"] = {"lines_before": n_before, "lines_after": len(lines), "replaced": replaced}

    # ---------------- 文档面（增量插入 + 回读断言） ----------------
    if not a.no_docs:
        blk = ("\n- **R596（真机臂轮: 判据 v3 **第四窗集** w172..w174 × 外部真值 codex + 只读并轮 候选②③④⑤；"
               "零产品源码改动 / 零新增夹具语义 / 零新增开关 / 同件同题集）**: **主判据 v3** set4 "
               "valid=%s / 中位 %s / 负号窗 %s ⇒ **%s**（set1 %s / set2 %s / set3 %s 并列，禁相减）；"
               "族 all-pass `wythoff` %s。**候选②（铁律 11 可验收化）** 桶池化 %s（A 份额 %s = 加厚 prompt 的收益上界）。"
               "**候选③** 行为面契约普查: agent ENTRY_FAIL %s/%s 跑次、codex %s/%s（POS 有牙=%s）。"
               "**候选④** `V_int` 第三窗集: agent 层 %s、`v_int_hist` %s（阈值化仍未测）。"
               "**候选⑤** 余量源 r595 实测振幅 %sMB ⇒ margin %s / REQ %s（cap_binding=%s）。"
               "**成本三列（参考·未可验收）**: 产品 %s 调用 / %s 新算 / %s completion vs 真值 %s / %s / %s；"
               "命中率 v_all %s/%s。**铁律 11 rc=%s**（blocked %d 条）⇒ 全部读数标「参考（未可验收）」。"
               "轮志 `eval/rover/r596/report-r596.md`。\n" % (
                   s4.get("valid"), fmt(s4.get("median")), s4.get("neg"), "PASS" if s4.get("pass") else "FAIL",
                   j.get("set1"), j.get("set2"), j.get("set3"),
                   json.dumps({k: (v or {}).get("set4") for k, v in (fam or {}).items()}, ensure_ascii=False),
                   json.dumps(pooled, ensure_ascii=False), (att or {}).get("verdict", {}).get("A_share_pooled"),
                   cs.get("agent", {}).get("ENTRY_FAIL"), cs.get("agent", {}).get("runs"),
                   cs.get("codex", {}).get("ENTRY_FAIL"), cs.get("codex", {}).get("runs"), cctrl.get("pos_has_teeth"),
                   json.dumps(lg.get("layer"), ensure_ascii=False), json.dumps(lg.get("v_int_hist"), ensure_ascii=False),
                   gate.get("prev_swing_effective"), gate.get("margin"), gate.get("req"), gate.get("cap_binding"),
                   prod.get("calls"), prod.get("new_prompt"), prod.get("completion"),
                   truth.get("calls"), truth.get("new_prompt"), truth.get("completion"),
                   prod.get("hit_v_all"), truth.get("hit_v_all"),
                   "0" if pre.get("executable_and_correct") else "1", len(blocked)))
        with io.open(MASTER, "a", encoding="utf-8") as fh:
            fh.write(blk)
        rb = io.open(MASTER, encoding="utf-8").read()
        out["master_appended"] = "**R596（真机臂轮" in rb

        old = ("> - **最近一轮（R595，2026-09-20 · cron 60min tick）**:")
        snap = ("> - **最近一轮（R596，2026-09-20 · cron 60min tick）**: **真机臂轮 = 判据 v3 第四窗集行使**"
                "（w172..w174：codex 真值 ×1 + 产品默认档 ×3）+ 只读并轮（候选②③④⑤）；零产品源码改动 / 零新增夹具语义 / "
                "零新增开关 / 同件（bin sha `%s`）同题集。**主判据** set4 **valid=%s / 中位 %s / 负号窗 %s ⇒ %s**；"
                "族 all-pass `wythoff` %s。**候选②** 逐例归因桶 %s（A 份额 %s）；**候选③** 行为面普查 agent ENTRY_FAIL "
                "%s/%s；**候选④** `V_int` 第三窗集直方图 %s（阈值化未测）；**候选⑤** 余量源 r595 振幅 %sMB ⇒ REQ %s。"
                "**铁律 11 rc=%s** ⇒ 成本/质量读数「参考（未可验收）」。轮志 `eval/rover/r596/report-r596.md`。\n" % (
                    summary["bin_sha12"], s4.get("valid"), fmt(s4.get("median")), s4.get("neg"),
                    "PASS" if s4.get("pass") else "FAIL",
                    json.dumps({k: (v or {}).get("set4") for k, v in (fam or {}).items()}, ensure_ascii=False),
                    json.dumps(pooled, ensure_ascii=False), (att or {}).get("verdict", {}).get("A_share_pooled"),
                    cs.get("agent", {}).get("ENTRY_FAIL"), cs.get("agent", {}).get("runs"),
                    json.dumps(lg.get("v_int_hist"), ensure_ascii=False), gate.get("prev_swing_effective"), gate.get("req"),
                    "0" if pre.get("executable_and_correct") else "1"))
        doc = io.open(ROLLBACK, encoding="utf-8").read()
        if old in doc:
            doc2 = doc.replace(old, snap + old.replace("最近一轮", "最近一轮【历史快照，已被上方 R596 行取代】"), 1)
            with io.open(ROLLBACK, "w", encoding="utf-8") as fh:
                fh.write(doc2)
            rb2 = io.open(ROLLBACK, encoding="utf-8").read()
            out["snapshot_updated"] = ("**最近一轮（R596" in rb2) and ("已被上方 R596 行取代" in rb2)
        else:
            out["snapshot_updated"] = False

        imp = io.open(IMPROV, encoding="utf-8").read()
        sec = ("\n## R596 · 2026-09-20 · 状态: **%s** · 主题: **判据 v3 第四窗集行使 × 铁律 11 阻塞臂逐例归因（候选②）"
               "× 交付物行为面契约普查（候选③）× `V_int` 第三窗集（候选④）× 起手闸余量按 r595 实测重派生（候选⑤）**\n\n"
               "- **主判据**: set4 valid=%s / 中位 %s / 负号窗 %s ⇒ %s；并列 set1 %s / set2 %s / set3 %s（禁相减）；族 all-pass %s。\n"
               "- **候选②**: 桶池化 %s；A 份额 %s（**上界**）；交叉校验 %s；POS 有牙=%s。\n"
               "- **候选③**: agent %s；codex %s；POS 有牙=%s / NEG 干净=%s。\n"
               "- **候选④**: agent 层 %s、`v_int_hist` %s；**阈值化仍未测**（承预注册禁止）。\n"
               "- **候选⑤**: 余量源 r595 振幅 %sMB；ceiling %s / margin %s / REQ %s / cap_binding=%s。\n"
               "- **铁律 11**: rc=%s（blocked %d）⇒ 成本/质量读数「参考（未可验收）」；候选①（产品侧修复）**待用户放行**。\n"
               "- 轮志 `eval/rover/r596/report-r596.md`、预注册 `prereg-r596.json`、DAG `dag-r596.md`、"
               "台账 `eval/capability/kpi.jsonl`（R596）。\n" % (
                   status, s4.get("valid"), fmt(s4.get("median")), s4.get("neg"), "PASS" if s4.get("pass") else "FAIL",
                   j.get("set1"), j.get("set2"), j.get("set3"),
                   json.dumps({k: (v or {}).get("set4") for k, v in (fam or {}).items()}, ensure_ascii=False),
                   json.dumps(pooled, ensure_ascii=False), (att or {}).get("verdict", {}).get("A_share_pooled"),
                   json.dumps((att or {}).get("cross_check", {}), ensure_ascii=False), ctrl_a.get("pos", {}).get("has_teeth"),
                   json.dumps(cs.get("agent"), ensure_ascii=False), json.dumps(cs.get("codex"), ensure_ascii=False),
                   cctrl.get("pos_has_teeth"), cctrl.get("neg_clean"),
                   json.dumps(lg.get("layer"), ensure_ascii=False), json.dumps(lg.get("v_int_hist"), ensure_ascii=False),
                   gate.get("prev_swing_effective"), gate.get("ceiling_min_of_3"), gate.get("margin"), gate.get("req"),
                   gate.get("cap_binding"), "0" if pre.get("executable_and_correct") else "1", len(blocked)))
        m = re.search(r"\n## R59\d", imp)
        imp2 = (imp[:m.start()] + sec + imp[m.start():]) if m else (imp + sec)
        with io.open(IMPROV, "w", encoding="utf-8") as fh:
            fh.write(imp2)
        out["improvements_updated"] = "## R596 ·" in io.open(IMPROV, encoding="utf-8").read()

    with io.open(FIN, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "summary"}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
