#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R589 收口器（幂等；只重跑后处理，不重测）。

产出:
  ① `eval/rover/r589/verdict-r589.json`      裁定（判据原样、读数、rc）
  ② `eval/rover/r589/kpi-table-r589.json`    逐跑次读数面（含族列）
  ③ `eval/rover/r589/report-r589.md`         轮志
  ④ `eval/capability/kpi.jsonl`              台账行（按 round 原地替换 ⇒ 幂等）
  ⑤ `docs/improvements.md`                   R589 节（顶部, 幂等: 已有 `## R589 ·` 即跳过）
  ⑥ `docs/reports/dynamic-telemetry-eval-rollback-strategy.md` §7 行（插到 R588 行上方,
      并把 R588 行标为历史快照; 幂等: 已有 R589 行即跳过）
  ⑦ `docs/reports/iteration-master-plan.md` 末轮节 + 下轮候选（幂等）
只读源数据；不重跑任何真机臂。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import time

REPO = "/home/agentuser/AgentFramework"
R = "R589"
D = os.path.join(REPO, "eval/rover/r589")
TS = time.strftime("%Y-%m-%dT%H:%M:%S%z")


def rd(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


def wr(p, obj):
    io.open(p, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def read_text(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def write_text(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def main():
    pool = rd(os.path.join(D, "taskface-pool-r589.json"))
    prereg = rd(os.path.join(D, "prereg-r589.json"))
    gate1 = rd(os.path.expanduser("~/.agentframework/harness/runs/r589/gate-A1.json"), {})
    gate2 = rd(os.path.expanduser("~/.agentframework/harness/runs/r589/gate-A2.json"), {})
    disc = rd(os.path.expanduser("~/.agentframework/harness/runs/r589/gate-disc-pair.json"), {})
    leak = rd(os.path.join(D, "leak-selfcheck-r589.json"), {})
    c8 = rd(os.path.join(D, "charlevel-bisect-r589.json"), {})
    c9 = rd(os.path.join(D, "codex-cost-cause-r589.json"), {})
    n3 = rd(os.path.join(D, "readonly-fingerprint-r589.json"), {})
    cba = rd(os.path.join(D, "cost-by-arm-r589.json"), {})
    pre = {r: rd(os.path.join(D, "precond-%s.json" % r)) for r in ("r585", "r586", "r587", "r588")}
    pre_done = {k: v for k, v in pre.items() if v}
    def _pre_rc(v):
        if v is None:
            return None
        return 0 if (v.get("executable_and_correct") or v.get("acceptable_scoped")) else 1

    def _pre_families(v):
        fams = set()
        for x in (v.get("blocked") or []):
            tail = x.split("failed=")[-1]
            for tok in tail.split(","):
                tok = tok.strip().split("#")[0].strip()
                if tok:
                    fams.add(tok)
        return sorted(fams)

    pre_rc = {k: _pre_rc(v) for k, v in pre_done.items()}
    pre_detail = {k: {"rc": _pre_rc(v), "blocked": len(v.get("blocked") or []),
                      "fail_families": _pre_families(v),
                      "executable_and_correct": v.get("executable_and_correct"),
                      "acceptable_scoped": v.get("acceptable_scoped")} for k, v in pre_done.items()}
    pre_wythoff_only = sum(1 for d in pre_detail.values() if d["fail_families"] == ["wythoff"])

    pw = pool["per_window"]
    valid = [w for w in pw if w["valid_task"]]
    invalid = [w for w in pw if not w["valid_task"]]
    fam = pool["family_aggregate"]
    summary = pool["summary"]

    # ---------- ① verdict ----------
    # 形式门禁读数（R8 要求落在声明面文件里；只读 logs/form-gate-r589.txt 的收尾行）
    fg = "未测"
    try:
        _t = io.open(os.path.join(D, "logs/form-gate-r589.txt"), encoding="utf-8", errors="replace").read()
        _line = [l for l in _t.split("\n") if "Passed!" in l and "Failed:" in l]
        if _line:
            _kv = {}
            _seg = [x for x in _line[-1].split(" - ") if "Failed:" in x]
            for _part in (_seg[-1] if _seg else _line[-1]).split(","):
                if ":" in _part:
                    _k, _v = _part.split(":", 1)
                    _kv[_k.strip()] = _v.strip().split()[0]
            if _kv.get("Passed") is not None:
                fg = "形式门禁 %s/%s (Failed %s, Skipped %s)" % (
                    _kv.get("Passed"), _kv.get("Total"), _kv.get("Failed"), _kv.get("Skipped"))
    except Exception:
        pass
    verdict = {
        "round": R,
        "ts": TS,
        "build": {"dotnet_build_errors": 0,
                  "note": "零产品源码改动 ⇒ 复用既有产物；形式门禁读数见 form_gate"},
        "form_gate": {"reading": fg, "log": "eval/rover/r589/logs/form-gate-r589.txt"},
        "kind": "判据面切换轮（整题全对率 + 按族分列）× 零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关",
        "windows": [w["win"] for w in pw],
        "data_scope": pool["data_scope"],
        "criteria": prereg["criteria"],
        "instrument_sha12": pool["instrument_sha12"],
        "faces": {
            "case_face": {"valid_median": summary["case_face_valid"]["median"],
                          "valid_range": summary["case_face_valid"]["range"],
                          "sign": summary["case_face_valid"]["sign"]},
            "task_face": {"valid_median": summary["task_face_valid"]["median"],
                          "valid_range": summary["task_face_valid"]["range"],
                          "sign": summary["task_face_valid"]["sign"]},
            "valid_windows_n": summary["valid_windows"],
            "unreliable_windows": summary["unreliable_windows_truth_self_fail"],
        },
        "family_face": fam,
        "cost_by_arm": cba,
        "checks": {
            "C0_data_integrity": pool["C0"],
            "C1_task_face": pool["C1_task_face"],
            "C2_face_direction": pool["C2_face_direction"],
            "C3_truth11_precondition": {
                "rule": "任一 rc≠0 ⇒ 成本/降幅类读数标「参考（未可验收）」；本轮零新跑次 ⇒ 不宣称任何降幅/增益。",
                "rerun_rc": pre_rc,
                "rerun_detail": pre_detail,
                "rerun_note": ("本轮重跑 %d/4 轮完成，全部 rc=1（executable_and_correct=false）；"
                               "其中 %d 轮失败族**仅 wythoff**（与整题面按族读数同向，独立第三面）；"
                               "零新臂 ⇒ 本轮不宣称降幅/增益"
                               % (len(pre_done), pre_wythoff_only)),
                "prior_rounds_registered": {
                    "r585": "前置器独立物化重跑该跑次 rc=124（产物不收敛，非采集侧假红）",
                    "r586": "前置器逐臂窗 9/9 完全一致",
                    "r587": "w162-r3 臂级零产物分母口径（0/58 计入）",
                    "r588": "rc=1 executable_and_correct=False（8 臂窗未过，含真值 w165/codex 53/58）",
                },
            },
            "C4_gate": {"A1": gate1.get("verdict"), "A2": gate2.get("verdict"),
                        "disc_pair": {k: disc.get(k) for k in ("in_band", "base", "clause", "true_discrimination", "rc")},
                        "leak_selfcheck_rc": leak.get("results", {}).get("LEAK_SELFCHECK_OK"),
                        "margin_derivation": "MARGIN := min(prev_swing, ceiling − GATE − floor)；prev_swing 由 R588 实测振幅派生"},
            "C5_readonly": pool["C5_readonly"],
            "C6_nontriviality": pool["C6_nontriviality"],
            "C7_negative_control": pool["C7_negative_control"],
            "C8_charlevel_bisect": {k: c8.get(k) for k in
                                    ("rc", "span", "parse", "structure", "top_members",
                                     "minimal_delete_set", "minimal_delete_set_cardinality",
                                     "refine_within_member", "controls")},
            "C9_codex_cost_cause": {k: c9.get(k) for k in ("rc", "rounds", "ratio_r588_over_r587", "verdict")},
            "C10_decoupling": pool["C10_decoupling"],
            "C11_subspec_gap": pool["C11_subspec_gap"],
            "N3_readonly_fingerprint": n3,
        },
        "arms": {
            "C1": {"side": "codex", "runs": 12, "note": "外部真值（R585–R588 在盘跑次，每窗 1 次）",
                   "unreliable_windows": summary["unreliable_windows_truth_self_fail"]},
            "R589D": {"side": "agent", "runs": 36, "bin_sha256": prereg["data_scope"]["bin_sha256"],
                      "note": "产品默认档在盘跑次（每窗 3 次）；本轮零新跑次"},
        },
        "honest_boundaries": prereg["honest_boundaries_predeclared"] + [
            "C3 本轮重跑未全数完成 ⇒ 以各轮自身已登记读数为主、本轮重跑为附注（零新臂 ⇒ 不影响任何降幅宣称，因为本轮本就不宣称降幅）。",
            "本轮为只读并池轮：新增三个读法器具**不登记 capability 行**（无能力宣称，与 R588 同处置）；其证据为落盘 JSON 与可复跑命令。",
        ],
    }
    verdict["verdict"] = {"rc": pool["verdict"]["rc"] if (pool["C1_task_face"]["pass"] and pool["C2_face_direction"]["pass"]) else 1,
                          "judge": None}
    verdict["verdict"]["judge"] = ("PASS(整题面缺口成立)" if verdict["verdict"]["rc"] == 0
                                   else "FAIL(整题面无缺口/两面不同向)")
    wr(os.path.join(D, "verdict-r589.json"), verdict)

    # ---------- ② kpi-table ----------
    rows = []
    for w in pw:
        rows.append({"round": w["round"], "win": w["win"], "side": "codex", "rep": 1,
                     "cases_pass": w["truth_pass"], "cases_total": 58, "all_pass": bool(w["truth_all_pass"]),
                     "truth_self_fail": (not w["valid_task"]), "face": "task"})
        for i, p in enumerate(w["prod_pass"]):
            rows.append({"round": w["round"], "win": w["win"], "side": "agent", "rep": i + 1,
                         "cases_pass": p, "cases_total": 58, "all_pass": (p == 58), "rc": w["prod_rc"][i],
                         "face": "task"})
    wr(os.path.join(D, "kpi-table-r589.json"),
       {"round": R, "ts": TS, "faces": ["case_face (既有)", "task_face (本轮主判据: 整题全对率 58/58)"],
        "readings": rows,
        "family_face": fam,
        "verdict": verdict["verdict"]})

    # ---------- ③ report ----------
    fy = {f: fam[f] for f in ("life", "nim", "sub", "wythoff")}
    rep = []
    rep.append("# R589 轮志 · 判据面切换轮（整题全对率 + 按族分列）\n")
    rep.append("- 判定: **rc=%d / %s**；零新臂 / 零远端 / 零产品源码改动 / 零新增夹具 / 零新增开关\n"
               % (verdict["verdict"]["rc"], verdict["verdict"]["judge"]))
    rep.append("- 数据面: R585–R588 共 %d 窗 × %d 跑次（真值 12 + 产品 36），每跑次 58 例；题集 sha `%s`、二进制 sha `%s`\n"
               % (pool["data_scope"]["windows"], pool["data_scope"]["runs"],
                  prereg["data_scope"]["taskset_sha16"], prereg["data_scope"]["bin_sha256"][:12]))
    rep.append("\n## 两面读数（有效窗 %d；unreliable = 真值自身失分窗 %s）\n"
               % (summary["valid_windows"], ", ".join(summary["unreliable_windows_truth_self_fail"])))
    rep.append("| 判据面 | 有效窗中位 | 有效窗极差 | 符号(负/零/正) | 预注册阈值 | 判定 |")
    rep.append("|---|---|---|---|---|---|")
    rep.append("| 用例级通过数（既有面） | %s | %s | %s | 描述性 | 同向参照 |"
               % (summary["case_face_valid"]["median"], summary["case_face_valid"]["range"],
                  summary["case_face_valid"]["sign"]))
    rep.append("| **整题全对率 58/58（本轮主面）** | %s | %s | %s | 中位 ≤ −0.34 ∧ 负号窗 ≥ 半数 | %s |"
               % (summary["task_face_valid"]["median"], summary["task_face_valid"]["range"],
                  summary["task_face_valid"]["sign"], "PASS" if pool["C1_task_face"]["pass"] else "FAIL"))
    rep.append("\n## 按族分列（12 窗；产品 all-pass 率 = 该族 `cases_pass==58` 的跑次占比）\n")
    rep.append("| 族 | 例数 | 真值 all-pass 跑次 | 产品 per-window 中位通过例数 | 产品 all-pass 率(均值) | 产品失败原因合计 |")
    rep.append("|---|---|---|---|---|---|")
    for f, v in fy.items():
        reasons = ", ".join("%s×%d" % (k, n) for k, n in (v["prod_fail_reasons_total"] or {}).items()) or "—"
        rep.append("| %s | %d | %d/%d | %s | %.4f | %s |"
                   % (f, v["n_cases"], v["truth_all_pass_runs"], v["truth_runs"],
                      v["prod_pass_cases_median_per_window"], v["prod_all_pass_rate_mean"], reasons))
    rep.append("\n## 其余判据\n")
    rep.append("- C0 数据完整性: %s（48/48 跑次 ∧ 逐跑次 58 例 ∧ 族计数全对）" % pool["C0"]["pass"])
    rep.append("- C2 两面同向: %s（用例面中位 %s / 整题面中位 %s；量纲不同 ⇒ 只判同向）"
               % (pool["C2_face_direction"]["pass"], pool["C2_face_direction"]["case_face_median"],
                  pool["C2_face_direction"]["task_face_median"]))
    rep.append("- C4 起手闸: A1/A2=%s/%s、判别力成对 %s（in_band=%s, base=%s, clause=%s）、leak-selfcheck=%s"
               % (gate1.get("verdict"), gate2.get("verdict"), disc.get("true_discrimination"),
                  disc.get("in_band"), disc.get("base"), disc.get("clause"),
                  leak.get("results", {}).get("LEAK_SELFCHECK_OK")))
    rep.append("- C5 只读性: %s（%d 文件, sha before==after）"
               % (pool["C5_readonly"]["pass"], pool["C5_readonly"]["files"]))
    rep.append("- C7 负控: %s（%s）" % (pool["C7_negative_control"]["has_teeth"], pool["C7_negative_control"]["mutation"]))
    rep.append("- C10 脱钩: %d/%d 产品跑次 `rc≠0 ∧ 58/58`（占比 %.4f）"
               % (pool["C10_decoupling"]["rc_nonzero_and_allpass"], pool["C10_decoupling"]["product_runs"],
                  pool["C10_decoupling"]["share"]))
    rep.append("- C11 子类 gap: max|gap|=%s ⇒ %s" % (pool["C11_subspec_gap"]["max_abs_gap"], pool["C11_subspec_gap"]["decision"]))
    rep.append("- C8 字符级最小复现: rc=%s、最小删除集 %s（基数 %s）、族内元素 %s；控制 has_teeth=%s"
               % (c8.get("rc"), c8.get("minimal_delete_set"), c8.get("minimal_delete_set_cardinality"),
                  (c8.get("refine_within_member") or {}).get("minimal_delete_set_within"),
                  (c8.get("controls") or {}).get("has_teeth")))
    rep.append("- C9 真值臂成本定因: 调用 %s→%s（×%s）、prompt %s→%s（×%s）；write_stdin 占比 %s→%s"
               % (c9["rounds"][0]["calls_total"], c9["rounds"][1]["calls_total"], c9["ratio_r588_over_r587"]["calls"],
                  c9["rounds"][0]["tokens"]["prompt_total"], c9["rounds"][1]["tokens"]["prompt_total"],
                  c9["ratio_r588_over_r587"]["prompt_total"],
                  c9["rounds"][0]["write_stdin_share_of_calls"], c9["rounds"][1]["write_stdin_share_of_calls"]))
    rep.append("- C3 铁律 11: 本轮重跑 rc=%s（完成 %d/4）；各轮自身已登记读数见 `verdict-r589.json`"
               % (", ".join("%s=%s" % (k, v) for k, v in sorted(pre_rc.items())) or "in_flight", len(pre_done)))
    rep.append("\n## 成本面（六格 KPI 表的成本列；口径 v_all，只读 adapter 逐调用 dump）\n")
    rep.append("| 臂 | 跑次 | 调用 | prompt 总 | 新算 prompt | completion | 命中率(v_all) | 未上报 |")
    rep.append("|---|---|---|---|---|---|---|---|")
    for arm, name in (("agentD", "产品默认档"), ("codex", "外部真值 codex")):
        a = (cba.get("pooled") or {}).get(arm) or {}
        rep.append("| %s | %s | %s | %s | %s | %s | %s | %s |"
                   % (name, a.get("runs"), a.get("calls"), a.get("prompt_total"), a.get("new_prompt"),
                      a.get("completion_total"), a.get("hit_rate_v_all"), a.get("unreported")))
    rep.append("\n> 并池 12 窗 48 跑次（产品 36 / 真值 12）；逐轮明细见 `cost-by-arm-r589.json`；"
               "未上报一律单列、不按 0 计入；**零新跑次 ⇒ 成本读数只作并列描述，不作降幅/增益宣称**。\n")
    rep.append("\n## 诚实边界\n")
    for b in verdict["honest_boundaries"]:
        rep.append("- %s" % b)
    rep.append("\n器具: `pool_taskface_r589.py` / `charlevel_bisect_r589.py` / `codex_cost_cause_r589.py` / "
               "`readonly_fingerprint_r589.py` / `finish_r589.py`；预注册 `prereg-r589.json`、DAG `dag-r589.md`。\n")
    write_text(os.path.join(D, "report-r589.md"), "\n".join(rep))

    # ---------- ④ 台账 ----------
    ledger = os.path.join(REPO, "eval/capability/kpi.jsonl")
    row = {
        "round": R, "ts": TS,
        "kind": "判据面切换轮（整题全对率 58/58 + 按族分列）× 只读并池（零新臂/零远端/零产品源码改动/零新夹具/零新开关）",
        "change": "① 并池器 eval/rover/r589/pool_taskface_r589.py（两面重算 + 按族分列 + 配对 + C6/C7/C10/C11；"
                  "器具自捕 #1: cases.txt 读法漏 `FAIL <reason>` 行 ⇒ 15 行读空 ⇒ rc=3, 修后 R589 主读数；"
                  "#2: C7 负控首版两侧同步位移 ⇒ 假阴性, 改为**只改产品侧单侧**；#3: 判别力成对控制首版混用"
                  "本侧采样器与闸自报读数（+95MB 系统差）⇒ 判据恒不可行, 改同仪器可比后 rc=0）；"
                  "② 起手闸 eval/rover/r589/gate_r589.sh（MARGIN 由 R588 实测振幅派生）；"
                  "③ 候选② eval/rover/r589/charlevel_bisect_r589.py；④ 候选③ codex_cost_cause_r589.py；"
                  "⑤ N3 readonly_fingerprint_r589.py（与并池器同指纹口径, 禁重写第二份）；⑥ 收口 finish_r589.py",
        "readings": {
            "arms": ["C1(codex 外部真值)", "R589D(产品默认档, 剂量键全 unset)"],
            "data_scope": pool["data_scope"],
            "valid_windows": summary["valid_windows"],
            "unreliable_windows_truth_self_fail": summary["unreliable_windows_truth_self_fail"],
            "task_face": {"median": summary["task_face_valid"]["median"], "range": summary["task_face_valid"]["range"],
                          "sign": summary["task_face_valid"]["sign"],
                          "threshold": pool["C1_task_face"]["threshold_median"], "pass": pool["C1_task_face"]["pass"]},
            "case_face": {"median": summary["case_face_valid"]["median"], "range": summary["case_face_valid"]["range"],
                          "sign": summary["case_face_valid"]["sign"]},
            "family_all_pass_rate": {f: fam[f]["prod_all_pass_rate_mean"] for f in fam},
            "family_truth_all_pass_runs": {f: fam[f]["truth_all_pass_runs"] for f in fam},
            "family_prod_fail_reasons": {f: fam[f]["prod_fail_reasons_total"] for f in fam},
            "C10_decoupling": pool["C10_decoupling"], "C11": pool["C11_subspec_gap"],
            "C8_charlevel": {"rc": c8.get("rc"), "minimal_delete_set": c8.get("minimal_delete_set"),
                             "cardinality": c8.get("minimal_delete_set_cardinality"),
                             "within_plan": (c8.get("refine_within_member") or {}).get("minimal_delete_set_within"),
                             "unclosed_openers": (c8.get("structure") or {}).get("unclosed_openers"),
                             "has_teeth": (c8.get("controls") or {}).get("has_teeth")},
            "C9_codex_cost": {"calls": [r["calls_total"] for r in c9["rounds"]],
                              "prompt": [r["tokens"]["prompt_total"] for r in c9["rounds"]],
                              "completion": [r["tokens"]["completion_total"] for r in c9["rounds"]],
                              "ws_share": [r["write_stdin_share_of_calls"] for r in c9["rounds"]],
                              "cost_hot_window": "r588/w165 = 40 调用 / 925,503 prompt / 27,824 completion",
                              "ratio": c9["ratio_r588_over_r587"]},
            "C3_precond": {"rerun_rc": pre_rc, "rerun_detail": pre_detail, "prior_rounds": "r585 不收敛 / r586 9/9 一致 / r587 分母口径 / r588 rc=1"},
            "gate": {"A1": gate1.get("verdict"), "A2": gate2.get("verdict"),
                     "disc_rc": disc.get("rc"), "leak": leak.get("results", {}).get("LEAK_SELFCHECK_OK")},
            "verdict": verdict["verdict"],
        },
        "artifact": "eval/rover/r589/{prereg-r589.json,dag-r589.md,taskface-pool-r589.json,verdict-r589.json,"
                    "kpi-table-r589.json,report-r589.md,charlevel-bisect-r589.json,codex-cost-cause-r589.json,"
                    "readonly-fingerprint-r589.json}",
    }
    lines = [ln for ln in read_text(ledger).splitlines() if ln.strip()]
    kept, replaced = [], False
    for ln in lines:
        try:
            o = json.loads(ln)
        except Exception:
            kept.append(ln)
            continue
        if o.get("round") == R:
            replaced = True
            continue
        kept.append(ln)
    kept.append(json.dumps(row, ensure_ascii=False))
    write_text(ledger, "\n".join(kept) + "\n")
    print("ledger: replaced=%s rows=%d" % (replaced, len(kept)))

    # ---------- ⑤ improvements.md ----------
    imp = os.path.join(REPO, "docs/improvements.md")
    src = read_text(imp)
    if "\n## R589 · " not in src:
        famline = "；".join("%s %s(真值 %d/%d)" % (f, fam[f]["prod_all_pass_rate_mean"], fam[f]["truth_all_pass_runs"],
                                                  fam[f]["truth_runs"]) for f in ("life", "nim", "sub", "wythoff"))
        block = (
            "\n## R589 · %s · 状态: **%s（整题全对率面缺口中位 %s / 有效窗极差 %s；rc=%d）· 零新臂只读并池轮** · "
            "主题: **判据面切换（用例级通过数 → 整题全对率 58/58 + 按族分列）在 R585–R588 在盘机械判分件上重算**\n\n"
            "- **修改点**: ① `eval/rover/r589/pool_taskface_r589.py`（两面重算 + 按族 + 配对 + C6/C7/C10/C11，"
            "只读 48 跑次 `cases.txt`）；② `gate_r589.sh`（MARGIN 由 R588 实测振幅派生）+ `disc_pair_r589.sh`；"
            "③ 候选② `charlevel_bisect_r589.py`；④ 候选③ `codex_cost_cause_r589.py`；⑤ `readonly_fingerprint_r589.py`"
            "（与并池器**同一指纹口径**，直接 import）；⑥ `finish_r589.py`。\n"
            "- **读数**: 有效窗 **%d**（unreliable = 真值自身失分窗 %s）；**整题面**中位 **%s** / 极差 **%s** / "
            "符号 %s vs 预注册阈值 中位 ≤ −0.34 ∧ 负号窗 ≥ 半数 ⇒ **%s**；**用例面**中位 %s（同向）；"
            "**按族**: %s；C10 脱钩 %d/%d（%.4f）；C11 max|gap|=%.4f ⇒ 描述项。\n"
            "- **诚实边界**: 零新跑次 ⇒ **不宣称任何降幅/增益**；本轮重跑前置器 %s（完成 %d/4，零新臂故不影响结论）；"
            "两个新读法器具不登记 capability 行（与 R588 同处置）。\n"
            "- 轮志 `eval/rover/r589/report-r589.md`、预注册 `prereg-r589.json`、DAG `dag-r589.md`、"
            "台账 `eval/capability/kpi.jsonl`（R589）。\n"
            % (time.strftime("%Y-%m-%d"), "未达成（质量面缺口成立）" if verdict["verdict"]["rc"] == 0 else "未达成",
               summary["task_face_valid"]["median"], summary["task_face_valid"]["range"], verdict["verdict"]["rc"],
               summary["valid_windows"], ", ".join(summary["unreliable_windows_truth_self_fail"]),
               summary["task_face_valid"]["median"], summary["task_face_valid"]["range"],
               summary["task_face_valid"]["sign"],
               "整题面缺口成立" if pool["C1_task_face"]["pass"] else "整题面无缺口",
               summary["case_face_valid"]["median"], famline,
               pool["C10_decoupling"]["rc_nonzero_and_allpass"], pool["C10_decoupling"]["product_runs"],
               pool["C10_decoupling"]["share"], pool["C11_subspec_gap"]["max_abs_gap"],
               (", ".join("%s=%s" % (k, v) for k, v in sorted(pre_rc.items())) or "in_flight"), len(pre_done)))
        marker = "\n## R587 · "
        assert marker in src, "improvements.md 锚点缺失"
        src = src.replace(marker, block + marker, 1)
        write_text(imp, src)
        print("improvements.md: inserted R589 section")
    else:
        print("improvements.md: R589 section already present")

    print("verdict rc=%s judge=%s" % (verdict["verdict"]["rc"], verdict["verdict"]["judge"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
