#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R542 读数器 —— g1 执行回灌修复预算剂量消融 (单变量 AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR ∈ {1,2,3} × 3 reps)
+ 旧路径基线 A1on (EXP1-Q51 点名缺失面)。

读数来源(三路交叉):
  ① transcript.json (被测体自报 rc/stage/calls/plan_steps/exec_repairs/自测面) —— **不作正确性证据**
  ② adapter side-agent-* 实发用量 (calls/prompt/cached/completion/total) —— 付费口径唯一来源
  ③ 隐藏用例实跑 cases.txt (58 条) —— **唯一正确性证据**
另: full-agent-* 裸消息数组机检 role 段是否进实发 user 轮 (R540 已修读数器, 本轮复核)。

用法: python3 analyze_r542.py --run-dir <D> --window w1 [--taskset <TS>] [--self-test]
"""
from __future__ import annotations
import argparse, importlib.util, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
A540 = "/home/agentuser/AgentFramework/eval/rover/r540/analyze_r540.py"


def load(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


a540 = load(A540, "analyze_r540_mod")

ARMS = ["R1x1a", "R1x1b", "R1x1c", "R1x2a", "R1x2b", "R1x2c", "R1x3a", "R1x3b", "R1x3c", "A1on"]
DOSE = {"R1x1a": 1, "R1x1b": 1, "R1x1c": 1, "R1x2a": 2, "R1x2b": 2, "R1x2c": 2,
        "R1x3a": 3, "R1x3b": 3, "R1x3c": 3}


def idx_ranges(D):
    """本轮 idx.txt 形如: `<arm>-g1 <i0> <i1> <xr>`。"""
    out = {}
    p = os.path.join(D, "logs/idx.txt")
    if not os.path.isfile(p):
        return out
    for ln in io.open(p, encoding="utf-8"):
        f = ln.split()
        if len(f) >= 3:
            out[f[0]] = [int(f[1]), int(f[2])]
    return out


def transcript(D, arm, tid="g1"):
    p = os.path.join(D, arm, tid, "transcript.json")
    if not os.path.isfile(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(d, list):
        d = d[-1] if d else {}
    keys = ("rc", "stage", "reason", "calls", "prompt_tokens", "completion_tokens",
            "cache_hit_tokens", "cache_miss_tokens", "repair_rounds", "exec_repairs",
            "plan_steps_total", "steps_executed", "self_test_unmet", "correctness_asserted",
            "role_note_chars", "prefix_sha256", "prefix_chars", "task_sha256")
    return {k: d.get(k) for k in keys}


def cases(D, arm, tid="g1"):
    p = os.path.join(D, arm, tid, "cases.txt")
    if not os.path.isfile(p):
        return {"pass": 0, "total": 0, "rc": None, "public_failed": [], "failed": []}
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    rc = None
    if lines and lines[-1].strip().isdigit():
        rc = int(lines[-1].strip())
        lines = lines[:-1]
    tot = [l for l in lines if l.startswith("CASE ")]
    npass = [l for l in tot if l.strip().endswith("PASS")]
    failed = [l.split()[1] for l in tot if not l.strip().endswith("PASS")]
    return {"pass": len(npass), "total": len(tot), "rc": rc, "failed": failed,
            "public_failed": [x for x in failed if "public" in x]}


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else round((xs[n // 2 - 1] + xs[n // 2]) / 2.0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--window", required=True)
    ap.add_argument("--taskset")
    ap.add_argument("--out")
    a = ap.parse_args()
    D, W = a.run_dir, a.window
    dumps = os.path.join(D, "adapter")
    rng = idx_ranges(D)
    out = {"round": "r542", "window": W, "run_dir": os.path.relpath(D, "/home/agentuser/AgentFramework"),
           "single_variable": "AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR", "arms": {}, "dose": {},
           "role_axis": {}, "judgments": {}, "notes": []}

    for arm in ARMS:
        i0, i1 = (rng.get("%s-g1" % arm) or [0, 0])
        t = transcript(D, arm)
        c = cases(D, arm)
        u = a540.cost(dumps, "agent", i0, i1) if os.path.isdir(dumps) else {}
        rec = {"dose": DOSE.get(arm), "range": [i0, i1], "rc": t.get("rc"), "stage": t.get("stage"),
               "reason_head": (t.get("reason") or "")[:160], "calls_dump": u.get("calls"),
               "calls_self": t.get("calls"), "prompt_tokens": u.get("prompt_tokens"),
               "cached_tokens": u.get("cached_tokens"), "completion_tokens": u.get("completion_tokens"),
               "total_tokens": u.get("total_tokens"), "unreported_usage": u.get("unreported_usage"),
               "plan_steps_total": t.get("plan_steps_total"), "steps_executed": t.get("steps_executed"),
               "exec_repairs": t.get("exec_repairs"), "repair_rounds": t.get("repair_rounds"),
               "self_test_unmet": t.get("self_test_unmet"),
               "correctness_asserted": t.get("correctness_asserted"),
               "role_note_chars": t.get("role_note_chars"), "prefix_sha256": t.get("prefix_sha256"),
               "cases_pass": c["pass"], "cases_total": c["total"], "cases_rc": c["rc"],
               "failed_cases": c["failed"], "public_failed": c["public_failed"]}
        out["arms"][arm] = rec
        if arm in DOSE:
            out["role_axis"][arm] = a540.role_mount_check(dumps, "agent", i0, i1) if os.path.isdir(dumps) else {}

    # ---- 剂量表 -------------------------------------------------------------
    for xr in (1, 2, 3):
        reps = [out["arms"][k] for k in ARMS if DOSE.get(k) == xr]
        out["dose"][str(xr)] = {
            "reps": len(reps),
            "rc": [r["rc"] for r in reps],
            "cases_pass": [r["cases_pass"] for r in reps],
            "all_green": [bool(r["cases_pass"] == r["cases_total"] == 58 and r["cases_rc"] == 0) for r in reps],
            "calls": [r["calls_dump"] for r in reps],
            "total_tokens": [r["total_tokens"] for r in reps],
            "calls_median": median([r["calls_dump"] for r in reps]),
            "tokens_median": median([r["total_tokens"] for r in reps]),
            "exec_repairs_max": max([r["exec_repairs"] or 0 for r in reps] or [0]),
        }

    # ---- 单变量自洽门 -------------------------------------------------------
    pfx = sorted({out["arms"][k].get("prefix_sha256") for k in ARMS if k in DOSE})
    roles = sorted({out["arms"][k].get("role_note_chars") for k in ARMS if k in DOSE})
    out["invariants"] = {
        "prefix_sha256_set": pfx, "prefix_identical": len(pfx) == 1,
        "role_note_chars_set": roles, "role_mounted_all": roles == [326],
        "role_marker_in_user_all": all((out["role_axis"].get(k) or {}).get("marker_in_user") for k in DOSE),
        "role_marker_in_prefix_any": any((out["role_axis"].get(k) or {}).get("marker_in_prefix") for k in DOSE),
        "cases_total_58_all": all(out["arms"][k]["cases_total"] == 58 for k in DOSE),
    }

    # ---- 判据 ---------------------------------------------------------------
    d3 = out["dose"]["3"]; d1 = out["dose"]["1"]; d2 = out["dose"]["2"]
    a1 = out["arms"]["A1on"]
    med3 = out["dose"]["3"]["tokens_median"]
    out["judgments"] = {
        "J1_剂量主问": {
            "dose3_all_green": all(d3["all_green"]),
            "dose1_all_green": all(d1["all_green"]),
            "dose2_all_green": all(d2["all_green"]),
            "verdict": ("修复预算不足为主因(剂量3 三臂全绿 ∧ 剂量1 有失败)" if all(d3["all_green"]) and not all(d1["all_green"])
                        else ("假设被证伪: 剂量1 已全绿 ⇒ 预算非瓶颈" if all(d1["all_green"])
                              else "机制候选未成立: 剂量3 亦未全绿 ⇒ 修复预算非充分条件")),
        },
        "J2_代价曲线": {str(k): {"calls_median": out["dose"][str(k)]["calls_median"],
                                 "tokens_median": out["dose"][str(k)]["tokens_median"]} for k in (1, 2, 3)},
        "J3_同窗旧路径对照": {
            "A1on_calls": a1.get("calls_dump"), "A1on_total_tokens": a1.get("total_tokens"),
            "A1on_cases": "%s/%s" % (a1.get("cases_pass"), a1.get("cases_total")),
            "R1x3_tokens_median": med3,
            "token_delta_pct": (None if not (med3 and a1.get("total_tokens"))
                                else round(100.0 * (med3 - a1["total_tokens"]) / a1["total_tokens"], 1)),
            "call_delta_pct": (None if not (out["dose"]["3"]["calls_median"] and a1.get("calls_dump"))
                               else round(100.0 * (out["dose"]["3"]["calls_median"] - a1["calls_dump"]) / a1["calls_dump"], 1)),
            "quality_premise_ok": bool(all(d3["all_green"]) and a1.get("cases_pass") is not None
                                       and a1.get("cases_pass") <= 58),
        },
        "J4_自测面同向性": {
            arm: {"stage": out["arms"][arm]["stage"], "cases_pass": out["arms"][arm]["cases_pass"],
                  "public_failed": out["arms"][arm]["public_failed"]}
            for arm in ARMS if out["arms"][arm]["rc"] is not None
        },
    }
    # 自测闸 vs 产物面 同向/反向 机检: rc!=0 且 stage=expect_stdout_* ⇒ 自测面与产物面必须同向(都失败)
    mism = []
    for arm in ARMS:
        r = out["arms"][arm]
        if r["rc"] in (5, 8) and r["cases_pass"] == r["cases_total"] == 58:
            mism.append(arm)
    out["judgments"]["J4_自测面同向性"]["self_gate_vs_product_mismatch"] = mism
    out["judgments"]["J5_rc语义"] = ("rc=8=计划跑完但自测未达成(成对报产物可疑); rc=5=自测未达成且修复耗尽; "
                                     "8/5 均非正确性证据; 唯一正确性证据 = 隐藏用例实跑")

    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    dst = os.path.join(HERE, "readings-%s.json" % W)
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))

    # ---- 打印 ---------------------------------------------------------------
    print("== R542 读数 (%s) ==" % W)
    print("%-7s %-3s %-4s %-6s %-9s %-3s %-4s %-7s %-8s %-8s %-10s %s" %
          ("arm", "xr", "rc", "stage", "cases", "c", "sr", "calls", "prompt", "compl", "total", "failed"))
    for arm in ARMS:
        r = out["arms"][arm]
        print("%-7s %-3s %-4s %-6s %-9s %-3s %-4s %-7s %-8s %-8s %-10s %s" %
              (arm, r["dose"], r["rc"], (r["stage"] or "-")[:14], "%s/%s" % (r["cases_pass"], r["cases_total"]),
               r["calls_self"], r["exec_repairs"], r["calls_dump"], r["prompt_tokens"],
               r["completion_tokens"], r["total_tokens"], ",".join(r["failed_cases"])[:60] or "-"))
    print("\n单变量自洽: prefix_identical=%s role_mounted_all=%s marker_in_user_all=%s marker_in_prefix_any=%s cases58=%s" % (
        out["invariants"]["prefix_identical"], out["invariants"]["role_mounted_all"],
        out["invariants"]["role_marker_in_user_all"], out["invariants"]["role_marker_in_prefix_any"],
        out["invariants"]["cases_total_58_all"]))
    for k in ("1", "2", "3"):
        dd = out["dose"][k]
        print("剂量 %s: rc=%s cases=%s all_green=%s calls=%s tokens=%s(中位 %s)" % (
            k, dd["rc"], dd["cases_pass"], dd["all_green"], dd["calls"], dd["total_tokens"], dd["tokens_median"]))
    print("J1 %s" % out["judgments"]["J1_剂量主问"]["verdict"])
    print("J3 vs A1on: calls %s vs %s (%s%%), tokens %s vs %s (%s%%) cases %s" % (
        out["dose"]["3"]["calls_median"], a1.get("calls_dump"), out["judgments"]["J3_同窗旧路径对照"]["call_delta_pct"],
        med3, a1.get("total_tokens"), out["judgments"]["J3_同窗旧路径对照"]["token_delta_pct"],
        out["judgments"]["J3_同窗旧路径对照"]["A1on_cases"]))
    print("readings -> %s" % os.path.relpath(dst, "/home/agentuser/AgentFramework"))
    # 退出码: 0 = 交付面(剂量3)三臂全绿; 1 = 未闭合
    return 0 if all(d3["all_green"]) else 1


if __name__ == "__main__":
    sys.exit(main())
