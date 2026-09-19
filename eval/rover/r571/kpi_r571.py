#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R571 汇总 + 判决器 (零逻辑复制; 判据文本取自 prereg-r571.json)。

模式:
  --win W   写 evidence/windows/W/{report.json,artifacts.json} (供铁律 11 前置器 project 布局发现)
  无 --win  读 $D/logs/runs.jsonl ⇒ 逐跑次读数 ⇒ KPI 表 + A1/A2/A3 判决

口径:
  · 跑次 = runs.jsonl 的一行 (外部真值; 不采信进程内 turn 计数)
  · 调用/新算 prompt/completion 取**中继 dump 索引区段** (transcript.calls 会漏续写调用)
  · 命中率双口径 v_all (含冷启动) / v_incr (去冷启动第一次调用)
  · 每窗每臂质量 = 重复跑次的**中位** (每跑次独立会话; 单跑次禁作结论)
"""
from __future__ import annotations
import argparse
import io
import json
import os
import statistics


def _usage(u):
    if not u:
        return {}
    p = int(u.get("prompt_tokens") or 0)
    hit = u.get("prompt_cache_hit_tokens")
    if hit is None:
        hit = ((u.get("prompt_tokens_details") or {}).get("cached_tokens"))
    if hit is None:
        hit = 0
    hit = int(hit)
    miss = u.get("prompt_cache_miss_tokens")
    if miss is None:
        miss = max(p - hit, 0)
    return {"prompt": p, "hit": hit, "miss": int(miss),
            "completion": int(u.get("completion_tokens") or 0)}


def arm_stats(adapter_dir, side, rng):
    a, b = rng
    files = [os.path.join(adapter_dir, "side-%s-%03d.json" % (side, i)) for i in range(a + 1, b + 1)]
    files = [f for f in files if os.path.isfile(f)]
    agg = {"calls": len(files), "prompt": 0, "new_prompt": 0, "hit": 0, "completion": 0,
           "turns": [], "bad_dumps": []}
    for f in files:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            agg["bad_dumps"].append({"file": os.path.basename(f), "err": str(e)[:60]})
            continue
        u = _usage(((d.get("response") or {}).get("usage")) or {})
        for k, kk in (("prompt", "prompt"), ("hit", "hit"), ("miss", "new_prompt"), ("completion", "completion")):
            agg[kk] += u.get(k, 0)
        agg["turns"].append({"file": os.path.basename(f), **u})
    t = agg["turns"]
    agg["v_all"] = round(agg["hit"] / agg["prompt"], 4) if agg["prompt"] else None
    inc = t[1:]
    ip = sum(x["prompt"] for x in inc)
    agg["v_incr"] = round(sum(x["hit"] for x in inc) / ip, 4) if ip else None
    return agg


def parse_cases(path):
    tot = pas = 0
    fails = []
    if not os.path.isfile(path):
        return {"total": 0, "pass": 0, "fails": [], "present": False}
    for x in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        if x.startswith("CASE"):
            tot += 1
            if "PASS" in x:
                pas += 1
            else:
                fails.append(x.split()[1] if len(x.split()) > 1 else "?")
    return {"total": tot, "pass": pas, "fails": fails, "present": True}


TR_FIELDS = ("calls", "rc", "stage", "repair_rounds", "exec_repairs", "probe_repairs",
             "steps_executed", "plan_steps_total", "self_test_unmet", "correctness_asserted",
             "public_probe_ran", "public_probe_failed", "prefix_sha256", "task_sha256")


def transcript(path):
    if not os.path.isfile(path):
        return {}
    try:
        t = json.load(io.open(path, encoding="utf-8"))
        return {k: t.get(k) for k in TR_FIELDS}
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:80]}


def load_runs(D):
    runs = []
    p = os.path.join(D, "logs", "runs.jsonl")
    for ln in io.open(p, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if ln:
            runs.append(json.loads(ln))
    return runs


def collect(D, pd):
    adir = os.path.join(D, "adapter")
    recs = []
    for r in load_runs(D):
        side = "codex" if r["sub"] == "codex" else "agent"
        st = arm_stats(adir, side, tuple(r["range"]))
        g = os.path.join(D, r["win"], r["sub"], "g1")
        cases = parse_cases(os.path.join(g, "cases.txt"))
        tr = transcript(os.path.join(g, "transcript.json"))
        recs.append({"arm": r["arm"], "win": r["win"], "rep": r["rep"], "sub": r["sub"],
                     "side": side, "cases_pass": cases["pass"], "cases_total": cases["total"],
                     "failed_cases": cases["fails"], "all_pass": bool(cases["total"] == 58 and cases["pass"] == 58),
                     "calls": st["calls"], "new_prompt": st["new_prompt"], "prompt": st["prompt"],
                     "completion": st["completion"], "v_all": st["v_all"], "v_incr": st["v_incr"],
                     "bad_dumps": st["bad_dumps"],
                     "rc": tr.get("rc"), "stage": tr.get("stage"), "repair_rounds": tr.get("repair_rounds"),
                     "exec_repairs": tr.get("exec_repairs"), "public_probe_failed": tr.get("public_probe_failed"),
                     "steps_executed": tr.get("steps_executed"), "plan_steps_total": tr.get("plan_steps_total")})
    return recs


def write_window(D, pd, W, recs):
    rows = []
    for r in recs:
        if r["win"] != W:
            continue
        rows.append({"arm": r["arm"], "tid": "g1", "side": r["side"], "rep": r["rep"],
                     "cases_pass": r["cases_pass"], "cases_total": r["cases_total"],
                     "all_pass": r["all_pass"], "rc": r["rc"], "stage": r["stage"],
                     "repair_rounds": r["repair_rounds"]})
    wdir = os.path.join(pd, "evidence", "windows", W)
    os.makedirs(wdir, exist_ok=True)
    json.dump({"round": "R571", "win": W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    arts = {}
    for r in recs:
        if r["win"] != W:
            continue
        arts[r["sub"]] = {"side": r["side"], "dir": "%s/g1" % r["sub"], "cases": r["cases_total"],
                          "repair_rounds": r["repair_rounds"], "rc": r["rc"], "stage": r["stage"]}
    json.dump({"win": W, "arms": arts, "note": "快照 = snapshots/<win>/<sub>/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[R571 %s] rows=%d" % (W, len(rows)))


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def judge(recs, prereg):
    wins = sorted({r["win"] for r in recs})
    out = {"round": "R571", "windows": wins, "criteria": prereg["axis_criteria_R571"], "arms": {}, "paired": {}}
    for arm in ("C1", "R571M1", "R571M3"):
        rs = [r for r in recs if r["arm"] == arm]
        out["arms"][arm] = {
            "runs": len(rs),
            "cases_per_run": [r["cases_pass"] for r in rs],
            "per_window_median": {w: med([r["cases_pass"] for r in rs if r["win"] == w]) for w in wins},
            "median": med([r["cases_pass"] for r in rs]),
            "min": min([r["cases_pass"] for r in rs]) if rs else None,
            "max": max([r["cases_pass"] for r in rs]) if rs else None,
            "calls": sum(r["calls"] for r in rs), "new_prompt": sum(r["new_prompt"] for r in rs),
            "completion": sum(r["completion"] for r in rs),
            "v_all_med": med([r["v_all"] for r in rs]), "v_incr_med": med([r["v_incr"] for r in rs]),
            "repair_rounds": [r["repair_rounds"] for r in rs],
            "rc": [r["rc"] for r in rs], "stages": [r["stage"] for r in rs],
            "steps": [r["steps_executed"] for r in rs],
        }
    m1 = out["arms"]["R571M1"]
    m3 = out["arms"]["R571M3"]
    # A1 行使面
    a1_extra = [x for x in m3["repair_rounds"] if isinstance(x, int) and x >= 2]
    d_m1 = {r["win"]: [] for r in []}
    m1_by_win, m3_by_win = {}, {}
    for r in recs:
        (m1_by_win if r["arm"] == "R571M1" else (m3_by_win if r["arm"] == "R571M3" else {})).setdefault(r["win"], []).append(r)
    cross = []
    for w in wins:
        for a in m1_by_win.get(w, []):
            if a.get("rc") == 4 and a.get("stage") == "contract":
                if any(b.get("rc") != 4 for b in m3_by_win.get(w, [])):
                    cross.append(w)
    a1 = bool(a1_extra) or bool(cross)
    # A2 质量 (逐窗重复中位差)
    Dq = []
    for w in wins:
        a = med([r["cases_pass"] for r in m1_by_win.get(w, [])])
        b = med([r["cases_pass"] for r in m3_by_win.get(w, [])])
        if a is not None and b is not None:
            Dq.append(b - a)
    out["paired"]["D_m3_minus_m1_per_window"] = Dq
    out["paired"]["D_median"] = med(Dq) if Dq else None
    out["paired"]["valid_windows"] = len(Dq)
    a2 = (len(Dq) >= 3) and (med(Dq) is not None) and (med(Dq) >= 0) and all(x > -3 for x in Dq)
    # A3 成本上界
    r_calls = (m3["calls"] / m1["calls"]) if m1["calls"] else None
    r_new = (m3["new_prompt"] / m1["new_prompt"]) if m1["new_prompt"] else None
    a3 = (r_calls is not None and r_calls <= 1.25) and (r_new is not None and r_new <= 1.25)
    out["ratio_m3_over_m1"] = {"calls": round(r_calls, 4) if r_calls else None,
                               "new_prompt": round(r_new, 4) if r_new else None}
    out["A1_exercised"] = {"pass": a1, "repair_rounds_ge2_on_M3": a1_extra,
                           "cross_windows_contract_death_M1": cross}
    out["A2_quality_not_worse"] = {"pass": a2, "D_list": Dq, "D_median": out["paired"]["D_median"],
                                   "valid_windows": len(Dq)}
    out["A3_cost_bounded"] = {"pass": a3, **out["ratio_m3_over_m1"], "bound": 1.25}
    if not a1:
        out["verdict"] = {"rc": 1, "judge": "mechanism-not-engaged",
                          "blocked": ["A1_exercise_face"], "note": "按预注册: 质量/成本对比作废; 不得据此宣称无效应 (见 resolution_bound)"}
    elif a2 and a3:
        out["verdict"] = {"rc": 0, "judge": "PASS", "blocked": []}
    else:
        b = []
        if not a2:
            b.append("A2_quality_shortfall")
        if not a3:
            b.append("A3_cost_over_bound")
        out["verdict"] = {"rc": 1, "judge": "FAIL(被测/前提)", "blocked": b}
    out["verdict"]["iron11"] = "见 eval/rover/r507pre/precondition-r571.json"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--pd", required=True)
    ap.add_argument("--win", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    recs = collect(a.D, a.pd)
    if a.win:
        write_window(a.D, a.pd, a.win, recs)
        return 0
    recs_all = [r for r in recs]
    with io.open(os.path.join(a.D, "readings.jsonl"), "w", encoding="utf-8") as fh:
        for r in recs_all:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    prereg = json.load(io.open(os.path.join(a.pd, "prereg-r571.json"), encoding="utf-8"))
    v = judge(recs_all, prereg)
    json.dump({"round": "R571", "readings": recs_all, "verdict": v},
              io.open(os.path.join(a.pd, "kpi-table-r571.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(v, io.open(os.path.join(a.pd, "verdict-r571.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"arms": {k: {kk: vv for kk, vv in val.items()
                                   if kk in ("runs", "median", "per_window_median", "calls",
                                             "new_prompt", "completion", "v_all_med", "repair_rounds", "rc")}
                              for k, val in v["arms"].items()},
                      "A1": v["A1_exercised"], "A2": v["A2_quality_not_worse"],
                      "A3": v["A3_cost_bounded"], "verdict": v["verdict"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
