#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R591 汇总 + 判决器 (派生自 kpi_r585.py: 轮号/臂集合/判据段替换 + **步数列进汇总打印面** + C5/C6 两段新增)
   (判据文本取自 prereg-r591.json; 其余逻辑逐字节同 R585)。

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
import hashlib
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
    json.dump({"round": "R591", "win": W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    arts = {}
    for r in recs:
        if r["win"] != W:
            continue
        arts[r["sub"]] = {"side": r["side"], "dir": "%s/g1" % r["sub"], "cases": r["cases_total"],
                          "repair_rounds": r["repair_rounds"], "rc": r["rc"], "stage": r["stage"]}
    json.dump({"win": W, "arms": arts, "note": "快照 = snapshots/<win>/<sub>/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[R591 %s] rows=%d" % (W, len(rows)))


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def judge(recs, prereg):
    wins = sorted({r["win"] for r in recs})
    out = {"round": "R591", "windows": wins, "criteria": prereg["axis_criteria_R591"], "arms": {}, "paired": {}}
    for arm in ("C1", "R591D"):
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
    # (无剂量轴: 原 R571 的 m1/m3 段已由下方 主线判据 段替代)
    # ── 主线判据 (无剂量轴: 产品默认档 × 外部真值) ─────────────────────────
    dw = {}
    for r in recs:
        dw.setdefault(r["win"], {}).setdefault(r["arm"], []).append(r)
    prod, c1a = out["arms"]["R591D"], out["arms"]["C1"]
    # C0 真值可靠性: 某窗真值自身失败 ⇒ 该窗 unreliable (剔除配对)
    unreliable = [w for w in wins if not all(x["all_pass"] for x in dw.get(w, {}).get("C1", []) if x[
        "cases_total"] == 58)]
    missing = [w for w in wins if not dw.get(w, {}).get("C1") or not dw.get(w, {}).get("R591D")]
    Dq = []
    for w in wins:
        if w in unreliable or w in missing:
            continue
        a = med([x["cases_pass"] for x in dw[w]["C1"]])
        b = med([x["cases_pass"] for x in dw[w]["R591D"]])
        if a is not None and b is not None:
            Dq.append(round(b - a, 2))
    out["paired"]["D_product_minus_truth_per_window"] = Dq
    out["paired"]["D_median"] = med(Dq) if Dq else None
    out["paired"]["valid_windows"] = len(Dq)
    out["paired"]["unreliable_windows_truth_self_fail"] = unreliable
    out["paired"]["missing_windows"] = missing
    out["paired"]["truth_per_window"] = {w: med([x["cases_pass"] for x in dw.get(w, {}).get("C1", [])]) for w in wins}
    out["paired"]["product_per_window"] = {w: med([x["cases_pass"] for x in dw.get(w, {}).get("R591D", [])]) for w in wins}
    c1_ok = (len(Dq) >= 2) and (out["paired"]["D_median"] is not None) and \
            (out["paired"]["D_median"] >= -2) and all(x > -15 for x in Dq)
    c2 = {"calls": {"product": prod["calls"], "truth": c1a["calls"]},
          "new_prompt": {"product": prod["new_prompt"], "truth": c1a["new_prompt"]},
          "completion": {"product": prod["completion"], "truth": c1a["completion"]},
          "hit_rate_v_all": {"product": prod["v_all_med"], "truth": c1a["v_all_med"]},
          "hit_rate_v_incr": {"product": prod["v_incr_med"], "truth": c1a["v_incr_med"]},
          "note": "信息项, 不判红绿 (禁合并成名义总量; 命中率口径 = 中继 dump 时间轴)"}
    out["C0_truth_reliability"] = {"pass": not unreliable, "unreliable": unreliable,
                                   "truth_all_pass": {w: [x["all_pass"] for x in dw.get(w, {}).get("C1", [])] for w in wins}}
    out["C1_quality_paired"] = {"pass": bool(c1_ok), "D_list": Dq, "D_median": out["paired"]["D_median"],
                                "valid_windows": len(Dq), "floor": -15, "median_floor": -2}
    out["C2_cost_three_columns"] = c2
    # ── C5 缺口复现判据 (与 R585 **同件**的两个窗集并列, 禁相减) ------------------
    prev_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "..", "r588", "verdict-r588.json"))
    c5 = {"prev_path": prev_path, "prev_D": None, "prev_median": None, "state": None}
    try:
        pv = json.load(io.open(prev_path, encoding="utf-8"))
        c5["prev_D"] = pv["C1_quality_paired"]["D_list"]
        c5["prev_median"] = pv["C1_quality_paired"]["D_median"]
        c5["prev_sha16"] = hashlib.sha256(io.open(prev_path, "rb").read()).hexdigest()[:16]
    except Exception as e:  # noqa: BLE001
        c5["err"] = str(e)[:80]
    c5["this_D"] = Dq
    c5["this_median"] = med(Dq) if Dq else None
    if Dq and c5.get("prev_D"):
        a_med, b_med = med(Dq), c5["prev_median"]
        same_sign = a_med is not None and b_med is not None and (a_med < 0) == (b_med < 0)
        overlap = not (max(Dq) < min(c5["prev_D"]) or max(c5["prev_D"]) < min(Dq))
        c5["same_sign"] = same_sign
        c5["interval_overlap"] = overlap
        c5["state"] = ("缺口跨窗复现" if (same_sign and overlap)
                       else "方向一致、量级漂移" if same_sign else "未复现(单窗集摆动)")
    out["C5_gap_reproduction"] = c5
    # ── C5b 四窗集并列 (禁相减; 只列已登记读数, 不重算) ------------------------
    # R591 注: 表中**故意只放历史四集**(R585–R588) ⇒ 池化摆动/效应估计与 R588 同基准、可并列;
    #         本轮新窗集的判决由 **判据 v3 器具**(pool_taskface_r591.py, C7) 出, 不在此处混池。
    sets = {}
    base = os.path.dirname(os.path.abspath(__file__))
    for rnd, fname in (("R585", "verdict-r585.json"), ("R586", "verdict-r586.json"),
                       ("R587", "verdict-r587.json"), ("R588", "verdict-r588.json")):
        p = os.path.normpath(os.path.join(base, "..", rnd.lower(), fname))
        try:
            pv = json.load(io.open(p, encoding="utf-8"))
            sets[rnd] = {"path": p, "sha16": hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:16],
                         "D": pv["C1_quality_paired"]["D_list"], "median": pv["C1_quality_paired"]["D_median"]}
        except Exception as e:  # noqa: BLE001
            sets[rnd] = {"path": p, "err": str(e)[:60]}
    pooled = []
    for rnd in ("R585", "R586", "R587", "R588"):
        pooled += list(sets.get(rnd, {}).get("D") or [])
    nneg = len([x for x in pooled if x < 0]); npos = len([x for x in pooled if x > 0]); nz = len(pooled) - nneg - npos
    def _bin2(n, k):  # 双侧精确二项 p (p0=0.5), 纯 stdlib
        if n == 0: return None
        from math import comb
        tail = sum(comb(n, i) for i in range(0, min(k, n - k) + 1)) / (2 ** n)
        return round(min(1.0, 2 * tail), 4)
    c5b = {"per_set": {k: {"D": v.get("D"), "median": v.get("median"), "sha16": v.get("sha16")}
                       for k, v in sets.items()},
           "pooled_n_valid_windows": len(pooled), "pooled_D": pooled,
           "pooled_median_effect": med(pooled) if pooled else None,
           "pooled_range_swing": (max(pooled) - min(pooled)) if pooled else None,
           "max_dev_from_median": (max(abs(x - statistics.median(pooled)) for x in pooled)) if pooled else None,
           "sign_count": {"neg": nneg, "pos": npos, "zero": nz},
           "sign_test_p_two_sided": _bin2(nneg + npos, nneg),
           "note": "跨轮禁相减: 各集只并列; 池化仅用于摆动/效应分离估计"}
    eff, sw = c5b["pooled_median_effect"], c5b["pooled_range_swing"]
    if eff is None or sw is None:
        c5b["state"] = "不可判(无有效窗)"
    elif sw > abs(eff):
        c5b["state"] = "摆动 > 效应 ⇒ 该轴非承重变量、定案关闭"
    elif (c5b["sign_test_p_two_sided"] or 1) < 0.05:
        c5b["state"] = "摆动 <= 效应 ∧ 符号检验 p<0.05 ⇒ 缺口方向稳定（限本件本题集）"
    else:
        c5b["state"] = "不可分离，需更多窗"
    out["C5b_swing_vs_effect"] = c5b
    # ── C6 步数列面 (读数面收口; prereg C6) -------------------------------------
    nn = len([x for x in prod["steps"] if x is not None])
    c6 = {"nonnull": nn, "runs": prod["runs"], "pass": bool(nn > 0 and nn == prod["runs"]),
          "steps": prod["steps"], "plan_steps_total": [r["plan_steps_total"] for r in recs if r["arm"] == "R591D"],
          "note": "R585 纠偏: 同列本就在档 (verdict-r585.json::arms.R585D.steps=[8,15,7,14,7,7,7,7,7]), "
                  "而 R585 报告与 §7 块写「未测(adapter 未取该字段)」= 报告面与自己的读数不一致; 首跑读数不撤。"}
    out["C6_steps_face"] = c6
    bad = [r for r in recs if r["bad_dumps"]]
    if missing:
        out["verdict"] = {"rc": 3, "judge": "缺侧/不可判", "blocked": ["missing:" + ",".join(missing)]}
    elif bad:
        out["verdict"] = {"rc": 2, "judge": "器具缺陷(bad_dumps)", "blocked": [r["sub"] for r in bad]}
    elif not c6["pass"]:
        out["verdict"] = {"rc": 2, "judge": "器具缺陷(步数列缺档)",
                          "blocked": ["steps_face:%d/%d" % (nn, prod["runs"])]}
    elif c1_ok:
        out["verdict"] = {"rc": 0, "judge": "PASS(质量未低于判据)", "blocked": []}
    else:
        out["verdict"] = {"rc": 1, "judge": "FAIL(质量配对未过)", "blocked": ["C1_quality_paired:R591D"]}
    out["verdict"]["iron11"] = "见 eval/rover/r507pre/precondition-r591.json"
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
    prereg = json.load(io.open(os.path.join(a.pd, "prereg-r591.json"), encoding="utf-8"))
    v = judge(recs_all, prereg)
    json.dump({"round": "R591", "readings": recs_all, "verdict": v},
              io.open(os.path.join(a.pd, "kpi-table-r591.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(v, io.open(os.path.join(a.pd, "verdict-r591.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"arms": {k: {kk: vv for kk, vv in val.items()
                                   if kk in ("runs", "median", "per_window_median", "calls",
                                             "new_prompt", "completion", "v_all_med", "v_incr_med", "rc",
                                             "steps")}
                              for k, val in v["arms"].items()},
                      "C0": v["C0_truth_reliability"], "C1": v["C1_quality_paired"],
                      "C2": v["C2_cost_three_columns"], "C5": v["C5_gap_reproduction"],
                      "C6": v["C6_steps_face"], "C5b": v["C5b_swing_vs_effect"]["state"], "verdict": v["verdict"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
