#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R610 汇总 + 判决器（派生自 r603/judge_r603.py：**import** kpi_r599.py helpers 与 r604 的 J3v2 公式模块，
禁重写第二份）。

R610 = **同件同题集、只换窗集**（第十一窗集 w193..w195）；被测件（sha 8c3ade04d542）与冻结题集（e0c667c2）
与 R600/R602/R603 逐字节同 ⇒ 唯一自由度 = 窗集。
单变量 = AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER（T=治疗档/缺省 on, C=对照档 =0, C1=codex 真值）。

本轮新增（预注册 prereg-r610.json，先写后跑）：
  · J3 **v2 形态首次在新窗集行使**（a1 池化 ∧ a2 逐窗池化 ∧ b1 单位调用新算 prompt；无自由参数）
    + v1 照原样并列（不翻案）+ v2'(a1∧a2) 报告列（b1 降级须用户裁定）；
  · 有效窗下限判据面（W_floor，承 R604 §12.6 A 条）：有效窗 ∈ {0,1} ⇒ 标签 NO_RESOLUTION；
  · 低区分度冻结名单（LD：wythoff#43-public / wythoff#57-hidden）只加报 `v3_ex_LD` 诊断列。

rc 语义（分层）：0 已算 / 2 器具缺陷（含负控无牙 / 历史零回归不符） / 3 输入缺失。
用法: python3 judge_r610.py --D <run根> [--pd <repo/eval/rover/r610>] [--win wXXX]
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
             "action_candidates_declared", "action_candidates_accepted", "action_candidates_rejected",
             "prefix_sha256", "task_sha256")


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
    json.dump({"round": "R610", "win": W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"win": W, "arms": arts,
               "note": "快照 = snapshots/<win>/<sub>/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[evidence] windows/%s 落盘 rows=%d" % (W, len(rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--pd", default=os.path.join(REPO, "eval/rover/r610"))
    ap.add_argument("--win", default=None)
    ap.add_argument("--json", default=None, help="判决件输出路径（默认 <pd>/verdict-r610.json）")
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

    # --- J1 机制面（机械）：动作候选三计数（R610 单变量 = 动作候选轴 AGENTFRAMEWORK_R1_ACTION_CANDIDATES）---
    j1 = {}
    for arm in arms:
        rs = of(arm)
        dec = [r["tr"].get("action_candidates_declared") for r in rs]
        acc = [r["tr"].get("action_candidates_accepted") for r in rs]
        rej = [r["tr"].get("action_candidates_rejected") for r in rs]
        j1[arm] = {"runs": len(rs), "runs_with_declaration": sum(1 for x in dec if (x or 0) > 0),
                   "declared": dec, "accepted": acc, "rejected": rej,
                   "fallback_note": "字段缺席(None) ⇔ 声明数 0（轴关或远端未声明）—— ledger 侧按「声明数 > 0 才落字段」渲染"}
    j1_pass = j1["T"]["runs_with_declaration"] > 0 and j1["C"]["runs_with_declaration"] == 0

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
    j2b_pass = (j2b["T"]["conservation_violations"] == 0)

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
        v2recs, v2meta = j3mod.collect("r610", mod)
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
    PREV_TABLE = os.environ.get("R610_J5_PREV", os.path.join(REPO, "eval/rover/r603/kpi-table-r603.json"))
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
    j5["side_by_side_by_window"] = {"r606_set12": (prev or {}).get("paired_by_window"), "r610_set13": paired}
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
        "round": "R610",
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
    json.dump(table, io.open(os.path.join(pd, "kpi-table-r610.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    rc = 2 if defects else 0
    verdict = {
        "round": "R610",
        "kind": "M3 第一刀（RF0004.2 R610–R612 首轮）：动作候选进 R1 契约（前缀**只加厚**）+ 本地机械裁选器 + 三计数打点；第十三窗集 w199..w201",
        "instrument_source": {"helper": SRC599,
                              "helper_sha12": hashlib.sha256(io.open(SRC599, "rb").read()).hexdigest()[:12],
                              "j3v2_module": SRC_J3V2,
                              "driver_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12]},
        "J1_mechanism": {"pass": bool(j1_pass), "by_arm": j1},
        "J2b_selection_conservation": {"pass": bool(j2b_pass),
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
        "instrument_defects": defects,
        "verdict": {"rc": rc,
                    "rc_semantics": "分层：0 器具可用 / 2 器具缺陷（禁作被测结论） / 3 输入缺失；"
                                    "机制面结论见 mechanism_rc 与 label（承 R604 分层 rc 先例，本轮为**事后补记字段** checks_posthoc）",
                    "mechanism_rc": 0 if (j1_pass and j2b_pass) else 1,
                    "label": ("机制达标（J1∧J2b：声明面落地 + 逐条裁定守恒）" if (j1_pass and j2b_pass) else "机制未达标")
                             if rc == 0 else "器具缺陷（rc=2，禁作被测结论）",
                    "capability_claim": "仅并列（J4 次级、欠功率）；跨轮禁相减（被测件按设计变更）；M3 出口闸（调用数 ≤ 旧臂 50%）**本轮不判**——执行接线属第二刀（R611）"},
        "checks_posthoc": [
            "本轮 rc 语义分层（0 器具可用 / 2 器具缺陷 / 3 输入缺失）＋新增 mechanism_rc 字段：**首跑后补记**、"
            "不改任何判据与读数（r603 判据器把机制面编进 rc=1 ⇒ 两轮 rc 列不可直接并列，须按 mechanism_rc 对比）",
        ],
        "honest_bounds": [
            "J4 为 n=9/档 的欠功率读数 ⇒ 只作并列，不作能力结论",
            "被测件按设计变更（产品源码改动 ⇒ 重发布 AOT）⇒ 与 R585–R606 冻结件轮**禁相减**",
            "成本三列取中继 dump 时间轴；铁律 11 前置器 rc 见 precond-r610.json（rc≠0 ⇒ 标参考·未可验收）",
            "M3 出口闸（调用数按 request_id 去重 ≤ 旧臂 50%）本轮**不判**：远端动作只有声明没有执行接线 ⇒ 调用面按构造无分离",
            "J2/J3 为本轮继承面（修复收敛 / 成本形态）⇒ 只作并列，不进 mechanism_rc（机制面定义已收窄为 J1∧J2b）",
            "有效窗 ∈{0,1} ⇒ NO_RESOLUTION（禁记 PASS/不达）；真值自败窗剔除配对但单列我方读数",
            "LD 两例只作诊断列，不作收益/缺陷证据（主判据不剔除以保跨轮可比）",
        ],
    }
    out_path = a.json or os.path.join(pd, "verdict-r610.json")
    json.dump(verdict, io.open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "J1": j1_pass, "J2b": j2b_pass,
                      "J2": {"T": j2["T"]["converged"], "C": j2["C"]["converged"]},
                      "J3v2": j3_v2_pass, "J3v1": j3_v1_pass, "J4": j4_pass, "J5": j5_pass,
                      "v3": {"label": label, "D_list": v3["D_list"], "median": v3["D_median"],
                             "valid": v3["valid_windows"]},
                      "v3_ex_LD": {"D_list": v3_ex_ld["D_list"], "median": v3_ex_ld["D_median"]},
                      "defects": defects,
                      "T_all_pass": j4["T"]["all_pass"], "C_all_pass": j4["C"]["all_pass"],
                      "C1_all_pass": j4["C1"]["all_pass"]}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
