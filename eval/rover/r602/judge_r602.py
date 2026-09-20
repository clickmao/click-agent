#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R602 汇总 + 判决器（派生自 kpi_r599.py：**import** 其 helpers，禁重写第二份）。

R602 = **同件同题集、只换窗集**（第九窗集 w187..w189）扩窗复跑；被测件与题集与 R600 **逐字节同**
(sha 8c3ade04d542 / e0c667c2) ⇒ 唯一自由度 = 窗集。
单变量 = AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER（T=治疗档/缺省 on, C=对照档 =0, C1=codex 真值）。
判据 = 预注册 eval/rover/r602/prereg-r602.json 的 J1–J4（阈值与 R600 **一字未改**）+ 新增 J5「跨窗集同向性」(并列, 禁相减)。

口径（承 R585–R599，一字未改）：
  · 跑次 = runs.jsonl 一行（外部真值；不采信进程内 turn 计数）
  · 调用 / 新算 prompt / completion 取**中继 dump 索引区段**（transcript.calls 会漏续写调用）
  · 命中率双口径 v_all / v_incr；每窗每臂质量 = 重复跑次中位
用法: python3 judge_r602.py --D <run根> [--pd <repo/eval/rover/r602>]
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


def load_helpers():
    spec = importlib.util.spec_from_file_location("kpi599", SRC599)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


TR_FIELDS = ("calls", "rc", "stage", "repair_rounds", "exec_repairs", "probe_repairs",
             "steps_executed", "plan_steps_total", "self_test_unmet", "correctness_asserted",
             "public_probe_ran", "public_probe_failed", "public_probe_total", "public_probe_reason",
             "artifact_carryover_enabled", "artifact_carryover_rounds", "artifact_carryover_chars",
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
    """逐窗证据件（供铁律 11 前置器 project 布局发现；schema 与 R599 同形）。"""
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
    json.dump({"round": "R602", "win": W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"win": W, "arms": arts,
               "note": "快照 = snapshots/<win>/<sub>/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[evidence] windows/%s 落盘 rows=%d" % (W, len(rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--pd", default=os.path.join(REPO, "eval/rover/r602"))
    ap.add_argument("--win", default=None)
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
        recs.append({
            "arm": r["arm"], "win": r["win"], "rep": r["rep"], "sub": r["sub"], "side": side,
            "cases_pass": cs["pass"], "cases_total": cs["total"], "fail_families": cs["families"],
            "failed_cases": cs["fails"], "all_pass": bool(cs["total"] == 58 and cs["pass"] == 58),
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

    # --- J1 机制面（机械）：随附轮数打点 ---
    j1 = {}
    for arm in arms:
        rs = of(arm)
        rounds = [r["tr"].get("artifact_carryover_rounds") or 0 for r in rs]
        chars = [r["tr"].get("artifact_carryover_chars") or 0 for r in rs]
        j1[arm] = {"runs": len(rs), "runs_with_carryover": sum(1 for x in rounds if x > 0),
                   "carryover_rounds": rounds, "carryover_chars": chars,
                   "fallback_note": "打点为 None ⇒ 该跑次 transcript 无该字段（轴关/未触发）"}
    j1_pass = j1["T"]["runs_with_carryover"] > 0 and j1["C"]["runs_with_carryover"] == 0

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

    # --- J3 成本面：调用数不增 + 增量只出现在修复轮 ---
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
    j3_pass = (j3["T"]["max_calls"] is not None and j3["C"]["max_calls"] is not None
               and j3["T"]["max_calls"] <= j3["C"]["max_calls"])

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


    # --- J5 跨窗集同向性（**并列，禁相减**；被测件与题集逐字节同 ⇒ 唯一变的是窗集）---
    PREV_TABLE = os.environ.get("R602_J5_PREV", os.path.join(REPO, "eval/rover/r600/kpi-table-r600.json"))
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
    j5["side_by_side_by_window"] = {
        "r600_set8": (prev or {}).get("paired_by_window"),
        "r602_set9": paired}
    j5_pass = bool(j5["sign_consistent"]) if j5["sign_consistent"] is not None else None

    table = {
        "round": "R602",
        "columns": ["臂", "整题全对(逐窗/池化)", "用例通过中位", "调用", "新算prompt", "completion",
                    "命中率(v_all/v_incr)", "步数/步骤总数", "随附轮数", "rc/stage", "判据"],
        "rows": [],
        "paired_by_window": paired,
        "note": "T=治疗档（随附盘上产物）/ C=对照档（轴关 = 旧行为）/ C1=codex 外部真值；成本三列 = 中继 dump 时间轴聚合（非 transcript.calls）。",
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
    json.dump(table, io.open(os.path.join(pd, "kpi-table-r602.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    verdict = {
        "round": "R602",
        "kind": "同件扩窗轮（用户放行）：回灌修复环「带现状」= 修复指令随附盘上产物原文；"
                "单变量 = AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER；真机 A/B（3 窗 × T/C 各 3 跑次 + codex 同窗 ×1）",
        "bin_sha256": hashlib.sha256(io.open(os.path.join(REPO, ".git/ROUND_CLAIM"), "rb").read()).hexdigest()[:12]
                      if os.path.isfile(os.path.join(REPO, ".git/ROUND_CLAIM")) else None,
        "instrument_source": {"helper": SRC599,
                              "helper_sha12": hashlib.sha256(io.open(SRC599, "rb").read()).hexdigest()[:12],
                              "driver_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12]},
        "J1_mechanism": {"pass": bool(j1_pass), "by_arm": j1},
        "J2_repair_convergence": {"pass": bool(j2_pass), "need": "T_converged >= C_converged + 1", "by_arm": j2},
        "J3_cost": {"pass": bool(j3_pass), "need": "T_max_calls <= C_max_calls（增量只出现在修复轮）", "by_arm": j3},
        "J5_cross_windowset_same_direction": {"pass": j5_pass, "note": "并列项, 不改主 rc", **j5},
        "J4_capability_secondary": {"pass": bool(j4_pass), "need": "T_all_pass >= C_all_pass + 1 ∧ 无窗下降",
                                    "by_arm": j4, "power_note": "n=9/档 ⇒ 欠功率；单窗集不作能力结论（R587 教训）"},
        "paired_vs_codex": paired,
        "verdict": {"rc": 0 if (j1_pass and j2_pass and j3_pass) else 1,
                    "label": "机制达标（J1∧J2∧J3）" if (j1_pass and j2_pass and j3_pass) else "机制未达标",
                    "capability_claim": "仅并列（J4 次级、欠功率）；跨轮禁相减（被测件按设计变更）"},
        "honest_bounds": [
            "J4 为 n=9/档 的欠功率读数 ⇒ 只作并列，不作能力结论",
            "被测件按设计变更（产品源码改动 ⇒ 重发布 AOT）⇒ 与 R585–R599 冻结件轮**禁相减**",
            "成本三列取中继 dump 时间轴；铁律 11 前置器 rc 见 precond-r600.json（rc≠0 ⇒ 标参考·未可验收）",
            "J2 的「收敛」按终态机械判（探针 failed==0 ∧ rc==0）；中间步骤失败不算收敛",
            "J5 为并列项（禁相减）；被测件与题集逐字节同 ⇒ 窗集是唯一自由度，但 n 仍欠功率",
        ],
    }
    json.dump(verdict, io.open(os.path.join(pd, "verdict-r602.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"J1": j1_pass, "J2": {"T": j2["T"]["converged"], "C": j2["C"]["converged"]},
                      "J3": j3_pass, "J4": j4_pass, "J5": j5_pass,
                      "J5_sign": j5["sign_consistent"], "J5_cur": cur_pooled, "J5_prev": prev_pooled,
                      "T_all_pass": j4["T"]["all_pass"], "C_all_pass": j4["C"]["all_pass"],
                      "C1_all_pass": j4["C1"]["all_pass"],
                      "paired": {w: paired[w]["D_T_minus_C"] for w in wins}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
