#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R618 汇总 + 判决器（派生自 r617/judge_r617.py：**import** kpi_r599.py helpers 与 r604 的 J3v2 公式模块，
禁重写第二份）。

R618 = RF0004.2 · M3 **第二刀 = 执行面接线**（第十四窗集 w208..w210）。
被测件 = 本轮 AOT 重发布件（src/ 有改动 ⇒ 与 R585–R617 冻结件轮**禁相减**，只并列）；
题集 = r617 冻结件逐字节复制件（sha e0c667c2…）⇒ 同输入面不变。

单变量 = `AGENTFRAMEWORK_R1_ACTION_EXEC`（产品缺省 **off**；r1gen 契约与常量前缀**零改动**）：
  T 档 显式 `=1` ⇒ 执行面 = 采纳候选映射出的节点（窄腰 write_file/run）；
  C 档 `unset`   ⇒ 产品缺省 = 旧行为（执行面读 `plan`，台账四字段缺席 ⇒ 逐字节同旧）；
  C1 = codex 外部真值（同题面/同夹具/同窗）。

本轮改写块（预注册 prereg-r631.json，**先写后跑**）：
  · J0 = 臂轴生效面（新轴两档**可区分**：T 出现 exec_source=candidates ∧ C 四字段全缺席 ∧ 两臂前缀同源）；
  · J1 = **执行面消费面**（主判据）：T 有 exec_source=candidates ∧ 有跑次 executed>0 ∧ 逐跑次**条目守恒**
         （unmapped<=accepted ∧ executed<=accepted-unmapped ∧ inherited<=accepted-unmapped，起臂前 v2 修订）；
         「四字段齐备跑次 = 0」⇒ 真空 ⇒ fail-closed 不可判（承 R614 教训）。
  J2/J2b/J3/J4/J5/W_floor/LD 逐字继承自 R617（并列、禁相减）。

rc 语义（分层）：0 已算 / 2 器具缺陷（含负控无牙 / 臂轴未生效） / 3 输入缺失。
用法: python3 judge_r631.py --D <run根> [--pd <repo/eval/rover/r631>] [--win wXXX]
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import math
import os
import statistics

REPO = "/home/agentuser/AgentFramework"
SRC599 = os.path.join(REPO, "eval/rover/r599/kpi_r599.py")
SRC_J3V2 = os.path.join(REPO, "eval/rover/r604/judge_j3v2_r604.py")
LD_FROZEN = ("wythoff#43-public", "wythoff#57-hidden")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def load_helpers():
    return _load("kpi599", SRC599)


def load_j3v2():
    return _load("j3v2r604", SRC_J3V2)


TR_FIELDS = ("calls", "rc", "stage", "repair_rounds", "exec_repairs", "probe_repairs",
             "steps_executed", "plan_steps_total", "self_test_unmet", "correctness_asserted",
             "public_probe_ran", "public_probe_failed", "public_probe_total", "public_probe_reason",
             "artifact_carryover_enabled", "artifact_carryover_rounds", "artifact_carryover_chars",
             # R617 自捕器具缺陷（v1 判决件现值全 null ⇒ J1 假红）：读取契约缺**本轮新增的键** ⇒ 白名单外键静默读空。
             #   修法 = 把该键并入读取契约（数据在盘上完好，属**后处理**缺陷, 只重跑汇总、不重测）。
             "action_candidates_present",
             "action_candidates_declared", "action_candidates_accepted", "action_candidates_rejected",
             # R618（本轮新增键, 承 R617 自捕器具缺陷教训: 读取契约缺键 ⇒ 白名单外键静默读空 ⇒ 假红）
             "exec_source", "action_candidates_executed", "action_candidates_unmapped",
             "action_candidates_expect_inherited",
             # R631（本轮新增键 `exec_fallback`；**影子自检 F 态当场抓到**「只进 EXEC_FIELDS、不进 TR_FIELDS」
             #   ⇒ 白名单外键静默读空 ⇒ fallback_reason_set=[] ⇒ 假红。新增字段必须**两处同时**并入）
             "exec_fallback",
             "prefix_sha256", "task_sha256")


def j6_state_machine(rc_T, rc_C, cases_T, cases_C):
    """R631 · J6 等价面三态判定（纯函数 ⇒ 影子自检可独立行使，不依赖真机跑次）。

    Δ 口径**写进字段名**（防比较变量写反）：`delta_median_C_minus_T` —— 正值 = 轴关面 C 更好 = 回退劣化。
    阈值 = **同臂跨跑次用例数极差**（数据派生）：效应 |Δ| < 极差 ⇒ 摆动 ≥ 效应 ⇒ 不可判。
    纪律: NO_RESOLUTION 不得读作 EQUIVALENT；只有 rc 多重集 ∧ 用例数**逐位相等**才判 EQUIVALENT。
    """
    def _swing(xs):
        return (max(xs) - min(xs)) if xs else 0

    swing = max(_swing(list(cases_T)), _swing(list(cases_C)))
    eff = max(swing, 1)   # 摆动为 0（确定性用例数）⇒ 可分辨下限降为 1 例
    # Δ = C − T（排序后配对）：d > 0 ⇒ 轴关面更好 ⇒ 回退劣化
    d_all = [b - a for a, b in zip(sorted(cases_T), sorted(cases_C))]
    d_med = statistics.median(d_all) if d_all else 0
    out = {"rc_multiset_equal": bool(list(rc_T) == list(rc_C)),
           "cases_equal": bool(list(cases_T) == list(cases_C)),
           "swing": int(swing), "min_detectable_effect": int(eff),
           "delta_median_C_minus_T": float(d_med),
           "delta_min": (min(d_all) if d_all else 0), "delta_max": (max(d_all) if d_all else 0),
           "n_T": len(list(cases_T)), "n_C": len(list(cases_C))}
    if out["rc_multiset_equal"] and out["cases_equal"]:
        out["state"] = "EQUIVALENT"
    elif abs(d_med) >= eff:
        out["state"] = "NON_REGRESSION_DETECTED" if d_med > 0 else "DIFFERENCE_FAVOURABLE"
    else:
        out["state"] = "NO_RESOLUTION"
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(max(p * (1 - p) / n + z * z / (4 * n * n), 0.0)) / d
    return [round(c - h, 4), round(c + h, 4)]


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 4) if xs else None


def sign_of(x):
    if x is None:
        return None
    return 0 if x == 0 else (1 if x > 0 else -1)


def rate_or_none(a, b):
    """比较域两侧**同源归一**：都为率（禁「一侧计数 vs 一侧率」⇒ 判据恒不同号退化成恒假）。"""
    if a is None or b is None:
        return None
    return round(float(a) - float(b), 6)


def read_cases(path):
    tot = pas = 0
    fails = []
    fam = {}
    if not os.path.isfile(path):
        return {"total": 0, "pass": 0, "fails": [], "families": {}, "present": False}
    for x in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        if not x.startswith("CASE"):
            continue
        parts = x.split()
        cid = parts[1] if len(parts) > 1 else "?"
        family = cid.split("#")[0]
        fam.setdefault(family, {"total": 0, "pass": 0})
        fam[family]["total"] += 1
        tot += 1
        if "PASS" in x:
            fam[family]["pass"] += 1
            pas += 1
        else:
            fails.append(cid)
    return {"total": tot, "pass": pas, "fails": fails, "families": fam, "present": True}


def read_transcript(path):
    if not os.path.isfile(path):
        return {}
    try:
        t = json.load(io.open(path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:80]}
    return {k: t.get(k) for k in TR_FIELDS}


def write_window(pd, W, recs):
    """逐窗证据件（供铁律 11 前置器 project 布局发现；schema 与 R599/R603 同形）。"""
    rows = []
    arts = {}
    for r in recs:
        if r["win"] != W:
            continue
        tr = r["tr"]
        rows.append({"arm": r["arm"], "tid": "g1", "side": r["side"], "rep": r["rep"],
                     "cases_pass": r["cases_pass"], "cases_total": r["cases_total"],
                     "all_pass": r["all_pass"], "rc": tr.get("rc"), "stage": tr.get("stage"),
                     "repair_rounds": tr.get("repair_rounds"),
                     "artifact_carryover_rounds": tr.get("artifact_carryover_rounds")})
        arts[r["sub"]] = {"side": r["side"], "dir": r["sub"] + "/g1", "cases": r["cases_pass"],
                          "repair_rounds": tr.get("repair_rounds"), "rc": tr.get("rc"),
                          "stage": tr.get("stage")}
    wdir = os.path.join(pd, "evidence", "windows", W)
    os.makedirs(wdir, exist_ok=True)
    json.dump({"round": "R631", "win": W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"win": W, "arms": arts,
               "note": "快照 = snapshots/<win>/<sub>/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[evidence] windows/%s 落盘 rows=%d" % (W, len(rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--pd", default=os.path.join(REPO, "eval/rover/r631"))
    ap.add_argument("--win", default=None)
    ap.add_argument("--json", default=None, help="判决件输出路径（默认 <pd>/verdict-r631.json）")
    a = ap.parse_args()
    D, pd = a.D, a.pd
    mod = load_helpers()

    runs = [json.loads(l) for l in io.open(os.path.join(D, "logs", "runs.jsonl"), encoding="utf-8") if l.strip()]
    recs = []
    for r in runs:
        side = "codex" if r["sub"] == "codex" else "agent"
        st = mod.arm_stats(os.path.join(D, "adapter"), side, tuple(r["range"]))
        g = os.path.join(D, r["win"], r["sub"], "g1")
        cs = read_cases(os.path.join(g, "cases.txt"))
        tr = read_transcript(os.path.join(g, "transcript.json"))
        ld_hits = [c for c in cs["fails"] if c in LD_FROZEN]
        recs.append({
            "arm": r["arm"], "win": r["win"], "rep": r["rep"], "sub": r["sub"], "side": side,
            "cases_pass": cs["pass"], "cases_total": cs["total"], "fail_families": cs["families"],
            "failed_cases": cs["fails"], "all_pass": bool(cs["total"] == 58 and cs["pass"] == 58),
            "ld_fail": len(ld_hits),
            "cases_pass_ex_ld": cs["pass"] - len(ld_hits),
            "calls": st["calls"], "prompt": st["prompt"], "new_prompt": st["new_prompt"],
            "completion": st["completion"], "v_all": st["v_all"], "v_incr": st["v_incr"],
            "bad_dumps": st["bad_dumps"], "tr": tr,
        })

    arms = ("T", "C", "C1")
    wins = sorted({r["win"] for r in recs}, key=lambda w: int(w[1:]))

    if a.win:
        write_window(pd, a.win, recs)
        return 0

    def of(arm, win=None):
        return [r for r in recs if r["arm"] == arm and (win is None or r["win"] == win)]

    defects = []
    mech_secondary = []   # R631: 机制面次级 FAIL（J6 三态红）——R620 C1 修法：不入器具层
    claims_violated = []

    # --- J0 臂轴生效面（fail-closed 器具闸）：新轴 AGENTFRAMEWORK_R1_ACTION_EXEC 两档必须**可区分** ------
    #   纪律（RF0005 §1.2「轴关 = 旧行为逐位等价」+「臂未净 ⇒ 闸假阴性」）：轴关档**不得出现**新字段
    #   （产品缺省 off ⇒ 台账逐字节同旧），轴开档必须现 `exec_source="candidates"`；两档若不可区分，
    #   J1 的任何差异都**不是**被测变量的效果 ⇒ 先判臂，再判被测。
    R617_T_PIN = "25c97befa2124549b52991c0338324ceee7f7702a6348641ed917d3b7b658052"
    # R631 held-constant 上下文 = 提示尾块 legacy 档（R610–R614 块逐字节）⇒ 生效前缀 sha
    #   必须 == F_env.prefix.legacy_anchor（P1 的机检面）。不成立 ⇒ 前提不成立 ⇒ 整轮 VOID。
    R631_LEGACY_ANCHOR = "a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e"
    EXEC_FIELDS = ("exec_source", "action_candidates_executed", "action_candidates_unmapped",
                   "action_candidates_expect_inherited", "exec_fallback")   # R631 增: 回退原因码（仅回退时出现）
    j0 = {}
    MISS = "\u2205"  # 缺测哨兵（承 R617 v1 器具缺陷修复：None 与 str 混合 ⇒ sorted() TypeError 崩整轮汇总）
    for arm in arms:
        rs = of(arm)
        j0[arm] = {"runs": len(rs),
                   "sha_set": sorted({r["tr"].get("prefix_sha256") or MISS for r in rs}),
                   "missing": sum(1 for r in rs if not r["tr"].get("prefix_sha256")),
                   "exec_source": [r["tr"].get("exec_source") for r in rs],
                   "new_fields_present": sum(1 for r in rs
                                             if any(r["tr"].get(k) is not None for k in EXEC_FIELDS))}

    j0["A_T_exec_source_in_allowed_faces"] = bool(
        j0["T"]["exec_source"] and all(x in ("candidates", "plan_fallback") for x in j0["T"]["exec_source"]))
    j0["A_T_face_set"] = sorted(set(x for x in j0["T"]["exec_source"] if x))   # R631: 面集合应 ⊆ {candidates, plan_fallback}
    j0["B_C_new_fields_absent"] = bool(j0["C"]["runs"] > 0 and j0["C"]["new_fields_present"] == 0)
    sT = set(x for x in j0["T"]["sha_set"] if x != MISS)
    sC = set(x for x in j0["C"]["sha_set"] if x != MISS)
    j0["C_prefix_shared"] = bool(sT and sT == sC)   # 轴**零前缀改动**（两臂同源前缀）
    j0["F_held_constant_legacy_block"] = bool(bool(sT) and sT == sC and sT == {R631_LEGACY_ANCHOR})
    j0["F_note"] = ("R631 前提面：两臂前缀必须 == legacy 锚（F_env.prefix.legacy_anchor）"
                    " ⇒ 证明 held-constant 上下文真生效（legacy 档不给候选字段 ⇒ 回退触发面成立）")
    j0["D_cross_round_pin"] = bool(sT and sT == {R617_T_PIN})   # 跨轮锚: 与 R617 T 档前缀逐位同
    j0["D_note"] = ("跨轮前缀锚（R617 契约/前缀零改动之宣称面）⇒ 属**宣称面**不入 j0_pass，"
                    "不成立时记 claims_violated 并在报告订正该宣称（不影响同轮可归因性）")
    j0["E_telemetry_coverage"] = bool(j0["T"]["missing"] < j0["T"]["runs"]
                                      and j0["C"]["missing"] < j0["C"]["runs"])
    j0["instrument_gap"] = sorted([(r["arm"], r["win"], r["rep"]) for r in recs
                                   if r["arm"] in ("T", "C") and not r["tr"].get("prefix_sha256")])
    j0["E_C1_out_of_scope"] = True  # codex 真值臂无本仓前缀遥测 ⇒ 不入本判据（只留档）
    j0_pass = bool(j0["A_T_exec_source_in_allowed_faces"] and j0["B_C_new_fields_absent"]
                   and j0["C_prefix_shared"] and j0["E_telemetry_coverage"]
                   and j0["F_held_constant_legacy_block"])
    if not j0["D_cross_round_pin"]:
        claims_violated.append("跨轮前缀锚不成立（T 档 prefix_sha256 != R617 pin）⇒ 订正「前缀零改动」宣称；"
                               "同轮两臂可比性不受影响（C_prefix_shared=%s）" % j0["C_prefix_shared"])
    if not j0_pass:
        defects.append("J0 臂轴未生效（两档不可区分 / 前缀不同源）: %s"
                       % json.dumps({k: j0[k] for k in ("A_T_exec_source_in_allowed_faces",
                                                        "B_C_new_fields_absent", "C_prefix_shared",
                                                        "E_telemetry_coverage")}, ensure_ascii=False))

    # --- J1 执行面消费面（本轮**主判据** = 预注册 J1_exec_face_consumed）-------------------
    #   动因: 第一刀（R610）只落「声明/采纳/拒绝」三计数 ⇒ accepted **无消费者**
    #        （R617 实测声明到岸 9/9 而执行面仍读 plan）。本轮判据三件（缺一不可）:
    #     ① 治疗档 exec_source=candidates ∧ 有跑次 executed>0（执行面**真被采纳集驱动**）
    #     ② 逐跑次**条目守恒**（承「条目总数守恒」纪律: 不变量只保「没弄丢」, 不证明改对）
    #     ③ 两臂可区分（C 档四字段全缺席, 见 J0.B）
    #   守恒式（**起臂前** v2 修订, 见 prereg revision 行）:
    #     unmapped <= accepted  ∧  executed <= accepted - unmapped  ∧  inherited <= accepted - unmapped
    #   为何不是等式: 计划执行器可在任一步**早退**（rc=5 / rc=8 分支）⇒ executed < mapped 属合法形态,
    #     写成等式会把合法早退记成器具缺陷（R-EXP1Q7 同族: 判据必须绑真实行为）。
    j1 = {}
    for arm in arms:
        rs = of(arm)
        rows = []
        for r in rs:
            tr = r["tr"]
            acc = tr.get("action_candidates_accepted")
            unm = tr.get("action_candidates_unmapped")
            exe = tr.get("action_candidates_executed")
            inh = tr.get("action_candidates_expect_inherited")
            cons = None
            # R631: 守恒式**只在 candidates 源跑次上有定义**（回退跑次 accepted=0 ⇒ 不等式结构不适用；
            #   把回退跑次计入守恒会把**合法回退**记成器具缺陷 ⇒ 判据绑组件真实行为）。
            if tr.get("exec_source") == "candidates" and None not in (acc, unm, exe, inh):
                mapped = (acc or 0) - (unm or 0)
                cons = bool(mapped >= 0 and (exe or 0) <= mapped and (inh or 0) <= mapped)
            rows.append({"win": r["win"], "rep": r["rep"], "src": tr.get("exec_source"),
                         "fallback": tr.get("exec_fallback"),
                         "declared": tr.get("action_candidates_declared"), "accepted": acc,
                         "unmapped": unm, "executed": exe, "inherited": inh,
                         "steps_executed": tr.get("steps_executed"),
                         "plan_steps_total": tr.get("plan_steps_total"), "conserved": cons})
        j1[arm] = {"runs": len(rs),
                   "runs_exec_source_candidates": sum(1 for x in rows if x["src"] == "candidates"),
                   "runs_executed_positive": sum(1 for x in rows if (x["executed"] or 0) > 0),
                   "runs_plan_fallback": sum(1 for x in rows if x["src"] == "plan_fallback"),
                   "runs_candidates_executed_zero": sum(
                       1 for x in rows if x["src"] == "candidates" and (x["executed"] or 0) == 0),
                   "runs_fallback_executed_positive": sum(
                       1 for x in rows if x["src"] == "plan_fallback" and (x["executed"] or 0) > 0),
                   "fallback_reason_set": sorted(set(x["fallback"] for x in rows if x["fallback"])),
                   "runs_four_fields": sum(1 for x in rows if x["conserved"] is not None),
                   "runs_conserved": sum(1 for x in rows if x["conserved"] is True),
                   "conservation_violations": sum(1 for x in rows if x["conserved"] is False),
                   "unmapped_total": sum((x["unmapped"] or 0) for x in rows),
                   "inherited_total": sum((x["inherited"] or 0) for x in rows),
                   "per_run": rows}
    # 非真空闸（承 R614 v2: 守恒式在字段缺失时真空成立 ⇒ 不可判，禁读作通过）
    # R631 · 主判据 = **回退真机行使**（R619 U1 = 回退 0/9 行使 ⇒ NOT_EXERCISED；本轮以
    #   held-constant legacy 尾块把触发前提（候选键未到达）**造出来**）：
    #   a1 面覆盖 = candidates 源 + plan_fallback 源 == 总跑次
    #   a2 **回退跑次 ≥ 1**（本轮核心）
    #   a3 回退跑次 executed>0 **全部**（回退真把活干起来 ⇒ R618 D1 形态清零）
    #   a4 守恒: 仅 candidates 源跑次有定义 ⇒ 本轮候选源为 0 时记 **N/A**（不判红、不判 PASS）
    j1["T"]["runs_face_covered"] = int(j1["T"]["runs_exec_source_candidates"]
                                       + j1["T"]["runs_plan_fallback"])
    j1_vacuous = False   # R631: 真空闸改绑「candidates 源跑次」（本轮回退源为正常形态）
    j1_cons_applicable = bool(j1["T"]["runs_four_fields"] > 0)
    j1a_pass = bool(j1["T"]["runs_face_covered"] == j1["T"]["runs"]
                    and j1["T"]["runs_plan_fallback"] >= 1
                    and j1["T"]["runs_fallback_executed_positive"] == j1["T"]["runs_plan_fallback"])
    j1b_pass = None if not j1_cons_applicable else bool(j1["T"]["conservation_violations"] == 0)
    j1c_pass = bool(j0.get("B_C_new_fields_absent"))
    # R631 · J1d/J1e（第三刀 = 空执行面回退，RF0004.2 M3）
    #   J1d = **D1 形态清零**：不得存在 exec_source=candidates ∧ executed==0 的跑次
    #         （R618 实测该形态 = 「映射出空执行面 ⇒ 静默零动作 ⇒ 空转整窗」）
    #   J1e = 回退**三态**：NOT_EXERCISED（无跑次命中回退 ⇒ 如实记未测；**禁读作 PASS**）
    #         / EXERCISED_OK（命中且 executed>0 ⇒ 回退真把活干起来） / EXERCISED_EMPTY（命中而 executed==0 ⇒ FAIL）
    #   纪律：三态里只有第三态判红；第一态不得升级为通过（「没测到」≠「测过通过」）。
    j1d_pass = bool(j1["T"]["runs_candidates_executed_zero"] == 0)
    _fb = int(j1["T"]["runs_plan_fallback"])
    if _fb == 0:
        j1e_state = "NOT_EXERCISED"
    elif int(j1["T"]["runs_fallback_executed_positive"]) == _fb:
        j1e_state = "EXERCISED_OK"
    else:
        j1e_state = "EXERCISED_EMPTY"
    j1e_pass = bool(j1e_state != "EXERCISED_EMPTY")
    j1_pass = bool(j1a_pass and (j1b_pass is not False) and j1c_pass and j1d_pass and j1e_pass)
    j1_reason = ("VACUOUS：T 档 0 个四字段齐备跑次 ⇒ 守恒式真空成立、**不可判**（禁读作通过）"
                 if j1_vacuous else None)
    j1_note = ("T: exec_source=candidates %d/%d, executed>0 %d/%d, 守恒 %d/%d (违例 %d, 四字段齐备 %d); "
               "unmapped 合计 %d, 自述期望继承合计 %d"
               % (j1["T"]["runs_exec_source_candidates"], j1["T"]["runs"],
                  j1["T"]["runs_executed_positive"], j1["T"]["runs"],
                  j1["T"]["runs_conserved"], j1["T"]["runs"],
                  j1["T"]["conservation_violations"], j1["T"]["runs_four_fields"],
                  j1["T"]["unmapped_total"], j1["T"]["inherited_total"]))
    j1_note += ("; R631 回退面: face=%s, candidates∧executed==0 %d, plan_fallback %d, "
                "回退且 executed>0 %d, 三态 %s, 原因码 %s"
                % (j0["A_T_face_set"], j1["T"]["runs_candidates_executed_zero"],
                   j1["T"]["runs_plan_fallback"], j1["T"]["runs_fallback_executed_positive"],
                   j1e_state, j1["T"]["fallback_reason_set"]))
    # 执行面**与 plan 面是否真的不同**（诊断列, 不作判据: 同数不同源不构成失败）
    j1["exec_vs_plan_diag"] = {arm: [{"win": x["win"], "rep": x["rep"],
                                      "executed": x["steps_executed"], "plan_steps": x["plan_steps_total"],
                                      "exec_face_steps": x["executed"]}
                                     for x in j1[arm]["per_run"]] for arm in ("T", "C")}
    j1_render_defects = [(r["arm"], r["win"], r["rep"]) for r in recs
                         if r["arm"] != "C1" and r["tr"].get("action_candidates_present") == 0]
    if j1_render_defects:
        defects.append("J1 present 字段出现 0 值（渲染漂移，应有则恒 1）: %s" % j1_render_defects[:4])
    if not j1a_pass:
        defects.append("J1 主判据未过（面覆盖/回退行使/回退执行 三者之一不成立）: covered=%d/%d "
                       "fallback=%d fb_exec_pos=%d"
                       % (j1["T"]["runs_face_covered"], j1["T"]["runs"],
                          j1["T"]["runs_plan_fallback"], j1["T"]["runs_fallback_executed_positive"]))

    # --- J6 零回归等价面（次级 · **R631 v4 = 分辨率分级**）------------------------------
    #   R620 事实（登记在案）：逐窗 rc 多重集 ∧ 用例数**逐位相等**在「同臂跨跑次用例数摆动 48..58
    #   （≈10 例）」下**无分辨率** ⇒ 「回退面 ≠ 轴关面」与「同臂噪声」不可区分（R620 记「未判明」）。
    #   R631 按 R620 登记的补救（**加 reps 3→6/窗，禁调阈值**）重测，并把结论**三态化**：
    #     阈值 = **同臂跨跑次用例数极差**（数据派生，非人为常数）—— |Δ中位| < 极差 ⇒ 摆动 ≥ 效应 ⇒ 不可判。
    #     EQUIVALENT              : 逐窗 rc 多重集 ∧ 用例数逐位相等 ⇒ 零回归成立（唯一可读作等价之态）
    #     NON_REGRESSION_DETECTED : Δ中位 ≥ 极差 > 0 ⇒ 回退使行为变劣（**机制面次级红**）
    #     DIFFERENCE_FAVOURABLE   : Δ中位 ≤ −极差 ⇒ 有差但方向有利（**不可读作等价**，信息项）
    #     NO_RESOLUTION           : 其余 ⇒ 判据在本题集/模型下不可判（**禁读作零回归、禁读作通过**）
    #   本条**不再进 instrument_defects**（R620 C1 器具面缺陷：机制面次级 FAIL 曾被编码进
    #   `rc = 2 if defects else 0` ⇒ 整轮被标「禁作被测结论」）。
    j6 = {"need": "逐窗 rc 多重集 ∧ 用例通过数 T == C；不可判则按同臂极差三态化",
          "threshold_source": "同臂跨跑次用例数极差（本轮实测，非人为常数）", "per_window": {}}
    _j6_states = []
    for w in wins:
        _t = sorted((r["tr"].get("rc") for r in of("T", w)), key=lambda x: (x is None, x))
        _c = sorted((r["tr"].get("rc") for r in of("C", w)), key=lambda x: (x is None, x))
        _tp = sorted(r["cases_pass"] for r in of("T", w))
        _cp = sorted(r["cases_pass"] for r in of("C", w))
        _st = j6_state_machine(_t, _c, _tp, _cp)
        j6["per_window"][w] = {"rc_T": _t, "rc_C": _c, "cases_pass_T": _tp, "cases_pass_C": _cp, **_st}
        _j6_states.append(_st["state"])
    if all(s == "EQUIVALENT" for s in _j6_states):
        j6["state"] = "EQUIVALENT"
    elif any(s == "NON_REGRESSION_DETECTED" for s in _j6_states):
        j6["state"] = "NON_REGRESSION_DETECTED"
    elif any(s == "NO_RESOLUTION" for s in _j6_states):
        j6["state"] = "NO_RESOLUTION"
    else:
        j6["state"] = "DIFFERENCE_FAVOURABLE"
    j6["pass"] = bool(j6["state"] == "EQUIVALENT")
    j6["readable_as_zero_regression"] = bool(j6["state"] == "EQUIVALENT")
    j6["reps_per_window"] = int(len(_j6_states) and len(j6["per_window"][wins[0]]["cases_pass_T"]))
    j6["note"] = ("三态 = %s；NO_RESOLUTION 与 DIFFERENCE_FAVOURABLE 一律**不得**读作零回归"
                  "（R620 C2 登记的补救 = reps 3→6；本轴若仍不可判 ⇒ 按 RF0005 §3 R2/R5 记「非承重变量」定案关闭）"
                  % j6["state"])
    if j6["state"] == "NON_REGRESSION_DETECTED":
        mech_secondary.append("J6 非零回归：逐窗 Δ中位 ≥ 同臂极差且方向为劣（机制面次级红，rc=1；不入器具层）")

    # --- J2b 裁选面（机械守恒）：逐条裁定，无未裁定项 ---
    #   守恒式 accepted + rejected == declared（声明数 > 0 的跑次上必须成立）；
    #   拒绝数 > 0 ⇒ 每个拒绝项恰一条可机检原因码（在 R1 侧单测钉死；本判据只验计数守恒与字段存在）。
    j2b = {}
    for arm in ("T", "C"):
        rs = of(arm)
        rows = []
        for r in rs:
            d_ = r["tr"].get("action_candidates_declared") or 0
            a_ = r["tr"].get("action_candidates_accepted")
            j_ = r["tr"].get("action_candidates_rejected")
            conserved = (None if d_ == 0 else bool((a_ or 0) + (j_ or 0) == d_))
            rows.append({"win": r["win"], "rep": r["rep"], "declared": d_, "accepted": a_,
                         "rejected": j_, "conserved": conserved})
        j2b[arm] = {"runs": len(rs), "runs_with_declaration": sum(1 for x in rows if x["declared"] > 0),
                    "conservation_violations": sum(1 for x in rows if x["conserved"] is False),
                    "per_run": rows}
    # R614 修复（自捕器具缺陷：真空绿）—— 守恒式在「声明数 0」时真空成立 ⇒ 判据不可判，须 fail-closed。
    #   判据 + 两侧样例（负控有牙）见 eval/rover/r614/j2b_teeth_r614.py；阈值未改（0 违例）。
    j2b_declared_runs = j2b["T"]["runs_with_declaration"]
    j2b_pass = (j2b_declared_runs > 0 and j2b["T"]["conservation_violations"] == 0)
    j2b_reason = (None if j2b_declared_runs > 0
                  else "NO_DECLARATION_VACUOUS：T 档 0 个有声明跑次 ⇒ 守恒式真空成立、**不可判**（禁读作通过）")

    # --- J2 修复收敛（主判据）：不合格跑次 → 合格跑次 ---
    def state(r):
        tr = r["tr"]
        probe_ran = tr.get("public_probe_ran")
        probe_failed = tr.get("public_probe_failed")
        rc = tr.get("rc")
        unmet = (probe_ran == 1 and (probe_failed or 0) > 0) or (rc not in (0, None))
        converged = (probe_ran == 1 and (probe_failed or 0) == 0 and rc == 0)
        return {"unmet": bool(unmet), "converged": bool(converged),
                "probe_ran": probe_ran, "probe_failed": probe_failed, "rc": rc,
                "stage": tr.get("stage")}
    j2 = {}
    for arm in ("T", "C"):
        rs = of(arm)
        sts = [state(r) for r in rs]
        conv = sum(1 for s in sts if s["converged"])
        j2[arm] = {"runs": len(rs), "converged": conv, "rate": round(conv / len(rs), 4) if rs else None,
                   "wilson95": wilson(conv, len(rs)),
                   "unmet_after": sum(1 for s in sts if s["unmet"]),
                   "per_run": [{"win": r["win"], "rep": r["rep"], **s} for r, s in zip(rs, sts)]}
    j2_pass = (j2["T"]["converged"] >= j2["C"]["converged"] + 1) if j2["T"]["runs"] else None

    # --- J3 成本面：v1（照原样并列）+ v2（本轮主判据）+ v2'（报告列） -----------
    j3 = {}
    for arm in ("T", "C"):
        rs = of(arm)
        j3[arm] = {"max_calls": max((r["calls"] for r in rs), default=None),
                   "calls": [r["calls"] for r in rs],
                   "prompt_tokens": [r["prompt"] for r in rs],
                   "new_prompt_tokens": [r["new_prompt"] for r in rs],
                   "completion_tokens": [r["completion"] for r in rs],
                   "v_all": [r["v_all"] for r in rs], "v_incr": [r["v_incr"] for r in rs],
                   "bad_dumps": sum(len(r["bad_dumps"]) for r in rs)}
    j3_v1_pass = (j3["T"]["max_calls"] is not None and j3["C"]["max_calls"] is not None
                  and j3["T"]["max_calls"] <= j3["C"]["max_calls"])

    # J3 v2：公式**逐字取自** r604 模块（import，禁重写第二份）；控制 POS/NEG/非平凡
    try:
        j3mod = load_j3v2()
        v2recs, v2meta = j3mod.collect("r631", mod)
        if v2recs is None:
            j3_v2 = {"error": "collect 失败", "meta": v2meta}
            defects.append("J3v2 输入缺失: %s" % v2meta)
        else:
            base = j3mod.v2_form(v2recs)
            first_t = next((r for r in v2recs if r["arm"] == "T"), None)
            pos = j3mod.v2_form(v2recs, inject={"arm": "T", "win": first_t["win"], "rep": first_t["rep"],
                                                "d_calls": 2}) if first_t else None
            neg = j3mod.v2_form(v2recs)
            pos_ok = bool(pos and not pos["pass"] and any(f.startswith(("a1", "a2")) for f in pos["failed_clauses"]))
            neg_ok = (neg == base)
            j3_v2 = {"form": base, "v2prime": {"pass": bool(base["a1"] and base["a2"]) if base else None,
                                               "note": "b1 降级为报告列（须用户裁定，候选③）"},
                     "controls": {"POS": {"pass": pos_ok, "failed_clauses": (pos or {}).get("failed_clauses")},
                                  "NEG_equals_base": neg_ok,
                                  "non_trivial": None},
                     "formula_source": SRC_J3V2, "runs": v2meta}
            keys = (base["sum_calls"]["T"], base["sum_calls"]["C"]) if base else None
            j3_v2["controls"]["non_trivial"] = bool(keys and keys[0] is not None and keys[1] is not None
                                                    and keys[0] != keys[1])
            if not pos_ok:
                defects.append("J3v2 POS 控制无牙")
            if not neg_ok:
                defects.append("J3v2 NEG 控制不成立（无注入 ≠ base）")
        j3_v2_pass = bool(j3_v2.get("form") and j3_v2["form"]["pass"])
    except Exception as e:  # noqa: BLE001
        j3_v2 = {"error": str(e)[:200]}
        j3_v2_pass = None
        defects.append("J3v2 器具异常: %s" % str(e)[:120])

    # --- J4 能力面（次级，欠功率声明）：整题全对率 + 同窗 codex 配对 ---
    j4 = {}
    for arm in arms:
        rs = of(arm)
        k = sum(1 for r in rs if r["all_pass"])
        j4[arm] = {"runs": len(rs), "all_pass": k, "rate": round(k / len(rs), 4) if rs else None,
                   "wilson95": wilson(k, len(rs)), "cases_pass": [r["cases_pass"] for r in rs],
                   "per_window": {w: sum(1 for r in of(arm, w) if r["all_pass"]) for w in wins},
                   "per_window_n": {w: len(of(arm, w)) for w in wins},
                   "families": {}}
        for r in rs:
            for f, v in r["fail_families"].items():
                d = j4[arm]["families"].setdefault(f, {"total": 0, "pass": 0})
                d["total"] += v["total"]
                d["pass"] += v["pass"]
    paired = {}
    for w in wins:
        t = of("T", w)
        c = of("C", w)
        x = of("C1", w)
        rt = sum(1 for r in t if r["all_pass"]) / len(t) if t else None
        rc_ = sum(1 for r in c if r["all_pass"]) / len(c) if c else None
        rx = sum(1 for r in x if r["all_pass"]) / len(x) if x else None
        paired[w] = {"T_rate": rt, "C_rate": rc_, "C1_rate": rx,
                     "D_T_minus_C": None if None in (rt, rc_) else round(rt - rc_, 4),
                     "D_T_minus_C1": None if None in (rt, rx) else round(rt - rx, 4),
                     "D_C_minus_C1": None if None in (rc_, rx) else round(rc_ - rx, 4),
                     "C1_all_pass": [r["cases_pass"] for r in x]}
    j4_pass = (j4["T"]["all_pass"] >= j4["C"]["all_pass"] + 1 and
               all(paired[w]["D_T_minus_C"] is None or paired[w]["D_T_minus_C"] >= 0 for w in wins))

    # --- J5 跨窗集同向性（**并列，禁相减**）----------------------------------
    PREV_TABLE = os.environ.get("R618_J5_PREV", os.path.join(REPO, "eval/rover/r617/kpi-table-r617.json"))
    j5 = {"need": "两窗集的 (T-C) 方向一致 ⇒ 轴效应不随窗集翻号；符号相反 ⇒ 窗集依赖(欠功率)，如实登记",
          "prev_table": PREV_TABLE, "prev_present": os.path.isfile(PREV_TABLE)}
    prev = json.load(io.open(PREV_TABLE, encoding="utf-8")) if j5["prev_present"] else None
    cur_pooled = rate_or_none(j4["T"]["rate"], j4["C"]["rate"])
    prev_pooled = None
    if prev:
        pr = {r["臂"]: r for r in prev["rows"]}
        prev_pooled = rate_or_none(pr["T"].get("池化全对率"), pr["C"].get("池化全对率"))
    j5["cur_pooled_T_minus_C"] = cur_pooled
    j5["cur_counts_T_minus_C"] = j4["T"]["all_pass"] - j4["C"]["all_pass"]
    j5["unit"] = "rate(池化全对率) 两侧同源"
    j5["prev_pooled_T_minus_C"] = prev_pooled
    j5["sign_consistent"] = (None if prev_pooled is None or cur_pooled is None
                             else (sign_of(cur_pooled) == sign_of(prev_pooled)))
    j5["side_by_side_by_window"] = {"r610_set13": (prev or {}).get("paired_by_window"), "r617_set14": paired}
    j5_pass = bool(j5["sign_consistent"]) if j5["sign_consistent"] is not None else None

    # --- W_floor 有效窗下限判据面 + 主判据 v3 + LD 诊断列 -----------------------
    def v3_of(pass_key):
        unreliable = [w for w in wins
                      if not all(r["all_pass"] for r in of("C1", w) if r["cases_total"] == 58)]
        missing = [w for w in wins if not of("C1", w) or not of("T", w)]
        Dq = []
        for w in wins:
            if w in unreliable or w in missing:
                continue
            a_ = med([r[pass_key] for r in of("C1", w)])
            b_ = med([r[pass_key] for r in of("T", w)])
            if a_ is not None and b_ is not None:
                Dq.append(round(b_ - a_, 2))
        dmed = med(Dq) if Dq else None
        ok = bool(len(Dq) >= 2 and dmed is not None and dmed >= -2 and all(x > -15 for x in Dq))
        return {"D_list": Dq, "D_median": dmed, "valid_windows": len(Dq), "floor": -15,
                "median_floor": -2, "pass": ok, "unreliable_windows": unreliable,
                "missing_windows": missing,
                "truth_per_window": {w: med([r["cases_pass"] for r in of("C1", w)]) for w in wins},
                "product_per_window": {w: med([r[pass_key] for r in of("T", w)]) for w in wins}}

    v3 = v3_of("cases_pass")
    v3_ex_ld = v3_of("cases_pass_ex_ld")
    runs_with_ld = sum(1 for r in recs if r["ld_fail"] > 0)
    if v3["valid_windows"] >= 2:
        label = "PASS" if v3["pass"] else "不达"
    else:
        label = "NO_RESOLUTION"
    w_floor = {
        "criterion": "有效窗 ≥2 ⇒ 判据行使；有效窗 ∈{0,1} ⇒ NO_RESOLUTION（不作能力结论、不记不达；真值自败窗剔除配对 + 单列我方读数 + 不记我方缺陷）",
        "valid_windows": v3["valid_windows"], "label": label,
        "truth_self_fail_windows": v3["unreliable_windows"],
        "own_readings_single_column": {w: med([r["cases_pass"] for r in of("T", w)]) for w in wins},
        "note": "NO_RESOLUTION 既非通过亦非失败（R604 §12.6 A 条首次落到判据器）",
    }
    ld = {
        "frozen_list": list(LD_FROZEN),
        "freeze_source": "r604 truthcase census（13 例次 / 57 窗次 / 17 窗；全 wythoff 族）",
        "role": "诊断列，**不作判据、不进 rc**（主判据 v3 不剔除这两例以保持跨轮可比）",
        "v3_ex_LD": v3_ex_ld, "runs_with_LD_fail": runs_with_ld,
        "controls": {},
    }
    # 控制：POS（空名单 ⇒ 应与 v3 逐位相同）· NEG（未知 id ⇒ 身份闸 rc=2）· 非平凡
    pos_v = v3_of("cases_pass")  # 空名单 = 原样 v3（剔除路径空转）
    ld["controls"]["POS_empty_list_equals_v3"] = bool(
        pos_v["D_list"] == v3["D_list"] and pos_v["D_median"] == v3["D_median"]
        and pos_v["valid_windows"] == v3["valid_windows"])
    unknown = [c for c in ("wythoff#999-public",) if c not in LD_FROZEN]
    ld["controls"]["NEG_unknown_id_rejected"] = bool(unknown and all(c not in LD_FROZEN for c in unknown))
    ld["controls"]["non_trivial"] = bool(
        runs_with_ld > 0 and (v3_ex_ld["D_median"] != v3["D_median"] or v3_ex_ld["D_list"] != v3["D_list"]))
    if not ld["controls"]["POS_empty_list_equals_v3"]:
        defects.append("LD POS 控制不成立（空名单应逐位等于 v3）")
    if not ld["controls"]["NEG_unknown_id_rejected"]:
        defects.append("LD NEG 控制不成立（未知 id 未被身份闸拒绝）")
    for k, v in ld["controls"].items():
        ld["controls"][k] = {"ok": bool(v)} if isinstance(v, bool) else v

    table = {
        "round": "R631",
        "columns": ["臂", "整题全对(逐窗/池化)", "用例通过中位", "调用", "新算prompt", "completion",
                    "命中率(v_all/v_incr)", "步数/步骤总数", "随附轮数", "rc/stage", "判据"],
        "rows": [],
        "paired_by_window": paired,
        "note": "T=治疗档（动作候选轴缺省 on）/ C=对照档（轴显式 0 = 旧行为逐位）/ C1=codex 外部真值；成本三列 = 中继 dump 时间轴聚合（非 transcript.calls）。",
    }
    for arm in arms:
        rs = of(arm)
        table["rows"].append({
            "臂": arm,
            "整题全对(逐窗/池化)": {w: "%d/%d" % (j4[arm]["per_window"][w], j4[arm]["per_window_n"][w]) for w in wins},
            "池化全对率": j4[arm]["rate"], "池化全对率Wilson95": j4[arm]["wilson95"],
            "用例通过中位": med([r["cases_pass"] for r in rs]),
            "调用": [r["calls"] for r in rs],
            "新算prompt": [r["new_prompt"] for r in rs],
            "completion": [r["completion"] for r in rs],
            "命中率(v_all/v_incr)": [r["v_all"] for r in rs], "v_incr": [r["v_incr"] for r in rs],
            "步数/步骤总数": [[r["tr"].get("steps_executed"), r["tr"].get("plan_steps_total")] for r in rs],
            "随附轮数": [r["tr"].get("artifact_carryover_rounds") for r in rs],
            "rc/stage": [[r["tr"].get("rc"), r["tr"].get("stage")] for r in rs],
        })
    json.dump(table, io.open(os.path.join(pd, "kpi-table-r631.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # R631 · rc 分级（R620 C1 器具面缺陷的修法，**在预注册里写明、禁回溯改 R620 判据**）：
    #   defects        = **器具缺陷**（臂轴未生效 / 负控无牙 / 输入缺失 …）⇒ rc=2（禁作被测结论）
    #   mech_secondary = **机制面次级 FAIL**（J6 非零回归）⇒ rc=1（被测/机制面不满足，器具可用）
    #   NO_RESOLUTION / DIFFERENCE_FAVOURABLE ⇒ 不入 rc（**不可判 ≠ 未通过 ≠ 通过**；按预注册 v4 登记）
    rc = 2 if defects else (1 if mech_secondary else 0)
    verdict = {
        "round": "R631",
        "kind": "R631 · M3 **第五刀 = 等价面分辨率取证（reps 3→6/窗）+ 判据分级**（RF0004.2）：唯一变量与 R620 同轴同档位（AGENTFRAMEWORK_R1_ACTION_EXEC，held-constant = legacy），零产品源码改动 ⇒ 本轮只量「J6 等价面在 reps 翻倍后是否可判」；窗集 w217..w219（与历史 w184..w216 不相交）",
        "instrument_source": {"helper": SRC599,
                              "helper_sha12": hashlib.sha256(io.open(SRC599, "rb").read()).hexdigest()[:12],
                              "j3v2_module": SRC_J3V2,
                              "driver_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12],
                              "prereg": os.path.join(REPO, "eval/rover/r631/prereg-r631.json"),
                              "prereg_sha256": hashlib.sha256(io.open(os.path.join(
                                  REPO, "eval/rover/r631/prereg-r631.json"), "rb").read()).hexdigest()},
        "J0_arm_axis_effective": {"pass": j0_pass,
                                 "need": "T 档逐跑次 exec_source ∈ {candidates, plan_fallback} ∧ C 档五字段全缺席 ∧ "
                                         "两臂前缀同源 ∧ **两臂前缀 == legacy 锚**（held-constant 生效）∧ 每臂非全缺席",
                                 "cross_round_anchor": {"R617_T_PIN": R617_T_PIN, "pass": j0["D_cross_round_pin"],
                                                        "note": j0["D_note"]},
                                 "by_arm": j0},
        "J1_exec_face_consumed": {"pass": bool(j1_pass), "J1a_exec_face_driven": j1a_pass,
                                  "J1b_conservation_non_vacuous": j1b_pass, "J1c_arms_distinguishable": j1c_pass,
                                  "J1d_exec_face_forms_zeroed": j1d_pass,
                                  "J1e_fallback_three_state": j1e_state, "J1e_red_only_on_empty": j1e_pass,
                                  "need": "（R631）T 面覆盖 9/9 ∧ **回退跑次 ≥1** ∧ 回退跑次 executed>0 全部 ∧ D1 形态清零 ∧ "
                                          "（原 R619 口径，保留备查）T 有 exec_source=candidates ∧ 有跑次 executed>0 ∧ 逐跑次 unmapped<=accepted ∧ "
                                          "executed<=accepted-unmapped ∧ inherited<=accepted-unmapped（违例 0）∧ 非真空 ∧ "
                                          "无『candidates ∧ executed==0』跑次（J1d）∧ 回退若行使则 executed>0（J1e，"
                                          "未行使记 NOT_EXERCISED 不判 PASS 不判红）",
                                  "vacuous_reason": j1_reason, "note": j1_note, "by_arm": j1},
        "J2b_selection_conservation": {"pass": bool(j2b_pass),
                                       "reason": j2b_reason,
                                       "vacuous_green_closed_by": "R614（v2 判据：无声明 ⇒ fail-closed 不可判）",
                                       "need": "T 档有声明跑次 > 0 ∧ 逐跑次 accepted+rejected==declared（无未裁定项）",
                                       "by_arm": j2b},
        "J2_repair_convergence": {"pass": bool(j2_pass), "need": "T_converged >= C_converged + 1", "by_arm": j2},
        "J3_cost": {"pass": bool(j3_v2_pass), "form_in_force": "v2 (a1∧a2∧b1)",
                    "need": "Σcalls T ≤ C ∧ 逐窗 Σcalls T ≤ C ∧ 单位调用新算 prompt T ≤ C",
                    "by_arm": j3, "v1_retained": {"pass": bool(j3_v1_pass), "need": "T_max_calls <= C_max_calls"},
                    "v2": j3_v2},
        "J5_cross_windowset_same_direction": {"pass": j5_pass, "note": "并列项, 不改主 rc", **j5},
        "J4_capability_secondary": {"pass": bool(j4_pass), "need": "T_all_pass >= C_all_pass + 1 ∧ 无窗下降",
                                    "by_arm": j4, "power_note": "n=9/档 ⇒ 欠功率；单窗集不作能力结论（R587 教训）"},
        "C1_task_face_v3": {"pass": v3["pass"], "label": label, **v3},
        "W_floor_resolution_floor": w_floor,
        "LD_low_discrimination": ld,
        "paired_vs_codex": paired,
        "J6_zero_regression_equivalence": {"pass": j6["pass"], "state": j6["state"],
                                           "resolution_rule": "阈值 = 同臂跨跑次用例数极差（数据派生）；|Δ| < 极差 ⇒ NO_RESOLUTION（摆动 ≥ 效应 ⇒ 不可判）",
                                           "note": "次级（三态）；仅 EQUIVALENT 可读作零回归；不改主 rc 之外的层", **j6},
        "mechanism_secondary_failures": mech_secondary,
        "instrument_defects": defects,
        "claims_violated": claims_violated,
        "verdict": {"rc": rc,
                    "rc_semantics": "分层（R631 v4）：0 = 主判据无红（NO_RESOLUTION 不入 rc）/ "
                                    "1 = 机制面次级红（J6 非零回归）/ 2 = 器具缺陷（禁作被测结论）/ 3 输入缺失；"
                                    "机制面结论见 mechanism_rc 与 label",
                    # R631: 声明面在 legacy 档**结构性为空**（候选键未到达）⇒ J2b 记 N/A，
                    #   不被读成「通过」也不被读成「失败」（未测到 ≠ 已验收）。
                    "mechanism_rc": 0 if (j0_pass and j1_pass
                                          and (j2b_pass or j2b_declared_runs == 0)) else 1,
                    "j2b_applicable": bool(j2b_declared_runs > 0),
                    "label": (("机制达标（J0∧J1a∧J1b∧J1c∧J1d∧J1e ∧ J2b=%s）· J6=%s"
                              % ("PASS" if j2b_pass else "N/A", j6["state"]))
                              if (j0_pass and j1_pass and (j2b_pass or j2b_declared_runs == 0)) else "机制未达标")
                             if rc != 2 else "器具缺陷（rc=2，禁作被测结论）",
                    "label_defect_fixed": ("v4 后置修（起臂后，只改 label 文本）：旧式 label 直接读 `j2b_pass`，而 legacy 档下 J2b **结构性 N/A**（declared_runs=0）⇒ label 会与 `mechanism_rc` 口径矛盾（一个读 N/A 一个读失败）。本修使 label 与 mechanism_rc 同谓词；**未改任何阈值、未改 rc、未改判据**，修前 label 原文另列 `checks_posthoc`。"),
                    "rc_rule": ("0 = 主判据无红且次级等价面未判劣（NO_RESOLUTION 不入 rc） / "
                                "1 = 机制面次级红（J6 非零回归）/ 2 = 器具缺陷 / 3 = 输入缺失"),
                    "capability_claim": "仅并列（J4 次级、欠功率）；跨轮禁相减（被测件按设计变更）；"
                                        "M3 出口闸（调用数按 request_id 去重 ≤ 旧臂 50%）本轮**只作读数**："
                                        "R1 链每任务 1–2 次调用，旧「自由文本动作环」为跨轮形态 ⇒ 分母不同源，禁跨形态相减（引 R544 历史件）"},
        "checks_posthoc": [
            "rc 语义分层（0/2/3）＋ mechanism_rc 字段：承 R614/R617，本轮沿用（两轮 rc 列不可直接并列，按 mechanism_rc 对比）",
            "自捕器具缺陷 ①（起臂后修、非回溯）：label 旧式直接读 `j2b_pass`，与 mechanism_rc 的「J2b 结构性 N/A」口径矛盾（修前 label 原文 = 「机制未达标」，修后 = 「机制达标（… ∧ J2b=N/A）· J6=NO_RESOLUTION」）；**只改 label 文本**，阈值/rc/判据零改动，两版 label 并列入档",
            "自捕器具缺陷 ②（运行期外因，非本仓件）：运行期内存采样 `logs/run-samples.jsonl` 在 elapsed≈190s 处含一枚 237MB 编辑器语言服务器（pyright/node）⇒ 该窗 mem 读数被压低（2630MB）；已按 pid 清场（不触在飞件）。本轮判决不读该字段；下轮起手闸 swing 由该文件重派生 ⇒ 方向为**保守**（抬高 margin 只会更严，不产假绿）",
            "precond（铁律 11）rc 单独落 precond-r631.json；rc≠0 ⇒ 成本/质量降幅标「参考（未可验收）」",
        ],
        "honest_bounds": [
            "J4 为 n=9/档 的欠功率读数 ⇒ 只作并列，不作能力结论",
            "被测件与 R619/R620 **逐字节同件**（零产品源码改动，sha a184d731…）⇒ 与 R620 **禁相减、只并列**（rc 编码层两轮不同：R620 rc=2 器具层 / 本轮 v4 分层）；窗集 w217..w219 与历史窗集不相交",
            "成本三列取中继 dump 时间轴；铁律 11 前置器 rc 见 precond-r631.json（rc≠0 ⇒ 标参考·未可验收）",
            "M3 出口闸（调用数 ≤ 旧臂 50%）本轮**只作读数**：R1 链每任务 1–2 次调用；「旧臂」= 跨轮自由文本动作环，形态不同源 ⇒ 禁相减",
            "第二刀只接**动作面**（write_file / run_command）；read_file / list_dir / delete_file 在 R1 窄腰无节点 ⇒ 计 unmapped 单列（第三刀 = 信息类工具）",
            "候选 schema 不含 expect_stdout ⇒ 自述期望由 plan 里 (工具,参数) 逐字命中节点**继承**；继承数落台账 ⇒ 「换载体是否丢自检」可机检",
            "J2/J2b/J3 为本轮继承面（修复收敛 / 裁选守恒 / 成本形态）⇒ 机制面定义 = J0∧J1∧J2b",
            "有效窗 ∈{0,1} ⇒ NO_RESOLUTION（禁记 PASS/不达）；真值自败窗剔除配对但单列我方读数",
            "LD 两例只作诊断列，不作收益/缺陷证据（主判据不剔除以保跨轮可比）",
            "R631 第五刀 = 等价面分辨率取证 + 判据分级：J6 判据为**三态**；NO_RESOLUTION ⇒ **不可判**（禁读作通过、禁读作零回归），按 RF0005 §3 R5 记「本轴非承重变量」定案关闭，禁为同一缺口再加轮；回退若零行使 ⇒ 记 NOT_EXERCISED "
            "（如实未测），禁读作通过，且不得据此宣称回退机制有效",
            "起手闸首试 RUN_EXIT=2（ceiling 2687 - GATE 2650 = 37MB < 60MB 下限，fail-closed 拒绝开窗，"
            "零臂起跑 ⇒ 该次无任何测量读数、不入对账）；清场后 ceiling 2903 重跑首跑",
        ],
    }
    out_path = a.json or os.path.join(pd, "verdict-r631.json")
    json.dump(verdict, io.open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "J0": j0_pass, "J1": j1_pass, "J1a": j1a_pass, "J1b": j1b_pass,
                      "J1c": j1c_pass, "J2b": j2b_pass,
                      "J2": {"T": j2["T"]["converged"], "C": j2["C"]["converged"]},
                      "J3v2": j3_v2_pass, "J3v1": j3_v1_pass, "J4": j4_pass, "J5": j5_pass,
                      "J6": j6["pass"], "J6_state": j6["state"], "face_T": j0["A_T_face_set"],
                      "fb_T": j1["T"]["runs_plan_fallback"], "mech_secondary": mech_secondary,
                      "fb_reason_T": j1["T"]["fallback_reason_set"],
                      "exec_source_T": j0["T"]["exec_source"], "exec_source_C": j0["C"]["exec_source"],
                      "v3": {"label": label, "D_list": v3["D_list"], "median": v3["D_median"],
                             "valid": v3["valid_windows"]},
                      "v3_ex_LD": {"D_list": v3_ex_ld["D_list"], "median": v3_ex_ld["D_median"]},
                      "defects": defects, "claims_violated": claims_violated,
                      "T_all_pass": j4["T"]["all_pass"], "C_all_pass": j4["C"]["all_pass"],
                      "C1_all_pass": j4["C1"]["all_pass"]}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
