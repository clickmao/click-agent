#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R544 读数器 —— g1 产物侧公开用例独立回放 (单变量 AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {off,on} × 3 reps)
+ 旧路径基线 A1on (同窗同题)。

读数来源(三路交叉, 与 R542 同口径):
  ① transcript.json (被测体自报 rc/stage/calls/exec_repairs/公开用例回放字段) —— **不作正确性证据**, 只作机制启用断言
  ② adapter side-agent-* 实发用量 (calls/prompt/cached/completion/total) —— 付费口径唯一来源(中继 usage)
  ③ 隐藏用例实跑 cases.txt (58 条) —— **唯一正确性证据**
另: full-agent-* 裸消息数组机检 role 段是否进实发 user 轮。

用法: python3 analyze_r544.py --run-dir <D> --window w1 [--taskset <TS>] [--out <json>]
"""
from __future__ import annotations
import argparse, importlib.util, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
A540 = "/home/agentuser/AgentFramework/eval/rover/r540/analyze_r540.py"

OFF = ["P0a", "P0b", "P0c"]
ON = ["P1a", "P1b", "P1c"]
ARMS = OFF + ON + ["A1on"]
TID = "g1"
HID = 58


def load(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


a540 = load(A540, "analyze_r540_mod")

KEYS = ("rc", "stage", "calls", "prompt_tokens", "completion_tokens", "cache_hit_tokens",
        "cache_miss_tokens", "repair_rounds", "exec_repairs", "plan_steps_total", "steps_executed",
        "self_test_unmet", "correctness_asserted", "role_note_chars", "prefix_sha256", "prefix_chars",
        "task_sha256", "public_probe_ran", "public_probe_total", "public_probe_failed")


def idx_ranges(D):
    out = {}
    p = os.path.join(D, "logs/idx.txt")
    if not os.path.isfile(p):
        return out
    for ln in io.open(p, encoding="utf-8"):
        f = ln.split()
        if len(f) >= 3:
            out[f[0]] = [int(f[1]), int(f[2])]
    return out


def transcript(D, arm):
    p = os.path.join(D, arm, TID, "transcript.json")
    if not os.path.isfile(p):
        return {}
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(d, list):
        d = d[-1] if d else {}
    return {k: d.get(k) for k in KEYS}


def cases(D, arm):
    p = os.path.join(D, arm, TID, "cases.txt")
    if not os.path.isfile(p):
        return {"pass": 0, "total": 0, "rc": None, "failed": [], "public_failed": []}
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


def ratio(new, base):
    if not new or not base:
        return None
    return round(float(new) / float(base), 3)


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
    out = {"round": "r544", "window": W,
           "run_dir": os.path.relpath(D, "/home/agentuser/AgentFramework"),
           "single_variable": "AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK", "arms": {}, "columns": {},
           "invariants": {}, "judgments": {}, "notes": []}

    for arm in ARMS:
        i0, i1 = (rng.get("%s-%s" % (arm, TID)) or [0, 0])
        t = transcript(D, arm)
        c = cases(D, arm)
        u = a540.cost(dumps, "agent", i0, i1) if os.path.isdir(dumps) else {}
        out["arms"][arm] = {
            "side": "off" if arm in OFF else ("on" if arm in ON else "legacy"),
            "range": [i0, i1],
            "rc": t.get("rc"), "stage": t.get("stage"), "reason_head": (t.get("reason") or "")[:200],
            "calls_dump": u.get("calls"), "calls_self": t.get("calls"),
            "prompt_tokens": u.get("prompt_tokens"), "cached_tokens": u.get("cached_tokens"),
            "completion_tokens": u.get("completion_tokens"), "total_tokens": u.get("total_tokens"),
            "unreported_usage": u.get("unreported_usage"),
            "plan_steps_total": t.get("plan_steps_total"), "steps_executed": t.get("steps_executed"),
            "exec_repairs": t.get("exec_repairs"), "repair_rounds": t.get("repair_rounds"),
            "correctness_asserted": t.get("correctness_asserted"),
            "public_probe_ran": t.get("public_probe_ran"), "public_probe_total": t.get("public_probe_total"),
            "public_probe_failed": t.get("public_probe_failed"),
            "role_note_chars": t.get("role_note_chars"), "prefix_sha256": t.get("prefix_sha256"),
            "cases_pass": c["pass"], "cases_total": c["total"], "cases_rc": c["rc"],
            "all_green": bool(c["rc"] == 0 and c["total"] == HID and c["pass"] == HID),
            "failed_cases": c["failed"], "public_failed": c["public_failed"],
            "reply_has_probe_marker": None,
        }
        rp = os.path.join(D, arm, TID, "reply.txt")
        if os.path.isfile(rp):
            txt = io.open(rp, encoding="utf-8", errors="replace").read()
            out["arms"][arm]["reply_has_probe_marker"] = "R1_PUBLIC_PROBE" in txt

    # ---- 列汇总 -------------------------------------------------------------
    for name, arms in (("off", OFF), ("on", ON)):
        recs = [out["arms"][k] for k in arms]
        out["columns"][name] = {
            "arms": arms,
            "rc": [r["rc"] for r in recs],
            "cases_pass": [r["cases_pass"] for r in recs],
            "all_green": [r["all_green"] for r in recs],
            "all_green_n": sum(1 for r in recs if r["all_green"]),
            "calls": [r["calls_dump"] for r in recs],
            "prompt_tokens": [r["prompt_tokens"] for r in recs],
            "completion_tokens": [r["completion_tokens"] for r in recs],
            "total_tokens": [r["total_tokens"] for r in recs],
            "calls_median": median([r["calls_dump"] for r in recs]),
            "prompt_median": median([r["prompt_tokens"] for r in recs]),
            "completion_median": median([r["completion_tokens"] for r in recs]),
            "total_median": median([r["total_tokens"] for r in recs]),
            "probe_failed": [r["public_probe_failed"] for r in recs],
            "false_success_n": sum(1 for r in recs if r["rc"] == 0 and not r["all_green"]),
        }
    lc = out["arms"]["A1on"]
    out["columns"]["legacy"] = {"arms": ["A1on"], "cases_pass": [lc["cases_pass"]],
                                "all_green_n": int(bool(lc["all_green"])),
                                "calls": lc["calls_dump"], "prompt_tokens": lc["prompt_tokens"],
                                "completion_tokens": lc["completion_tokens"],
                                "total_tokens": lc["total_tokens"]}

    # ---- 单变量自洽门 -------------------------------------------------------
    pfx = sorted({out["arms"][k].get("prefix_sha256") for k in ON + OFF})
    roles = sorted({out["arms"][k].get("role_note_chars") for k in ON + OFF})
    out["invariants"] = {
        "prefix_sha256_set": pfx, "prefix_identical": len(pfx) == 1,
        "role_note_chars_set": roles, "role_mounted_all": roles == [326],
        "cases_total_58_all": all(out["arms"][k]["cases_total"] == HID for k in ON + OFF),
        "mechanism_on_arms_ran": all(out["arms"][k]["public_probe_ran"] == 1 for k in ON),
        "mechanism_off_arms_absent": all(out["arms"][k]["public_probe_ran"] is None for k in OFF),
        "mechanism_off_no_marker": all(not out["arms"][k]["reply_has_probe_marker"] for k in OFF),
    }

    # ---- 判据 ---------------------------------------------------------------
    on_p, off_p = out["columns"]["on"], out["columns"]["off"]
    probe_vals = sorted({r["public_probe_failed"] for r in (out["arms"][k] for k in ON)
                         if r["public_probe_failed"] is not None})
    out["judgments"] = {
        "J1_机制启用断言": {
            "on_ran": [out["arms"][k]["public_probe_ran"] for k in ON],
            "on_total": [out["arms"][k]["public_probe_total"] for k in ON],
            "off_ran": [out["arms"][k]["public_probe_ran"] for k in OFF],
            "verdict": ("PASS" if out["invariants"]["mechanism_on_arms_ran"]
                        and out["invariants"]["mechanism_off_arms_absent"] else "FAIL(臂判 VOID)"),
        },
        "J2_假成功消解": {
            "off_false_success_n": off_p["false_success_n"], "on_false_success_n": on_p["false_success_n"],
            "verdict": ("支持" if on_p["false_success_n"] < off_p["false_success_n"]
                        else ("未消解: 两列同为 %s" % on_p["false_success_n"])),
        },
        "J3_质量": {"off_all_green": off_p["all_green"], "on_all_green": on_p["all_green"],
                    "off_cases": off_p["cases_pass"], "on_cases": on_p["cases_pass"],
                    "verdict": ("不降" if on_p["all_green_n"] >= off_p["all_green_n"] else "降(如实收窄)")},
        "J4_代价": {
            "calls": {"off_median": off_p["calls_median"], "on_median": on_p["calls_median"],
                      "ratio_on_off": ratio(on_p["calls_median"], off_p["calls_median"])},
            "prompt": {"off_median": off_p["prompt_median"], "on_median": on_p["prompt_median"],
                       "ratio_on_off": ratio(on_p["prompt_median"], off_p["prompt_median"])},
            "completion": {"off_median": off_p["completion_median"], "on_median": on_p["completion_median"],
                           "ratio_on_off": ratio(on_p["completion_median"], off_p["completion_median"])},
            "total": {"off_median": off_p["total_median"], "on_median": on_p["total_median"],
                      "ratio_on_off": ratio(on_p["total_median"], off_p["total_median"])},
        },
        "J5_同窗旧路径对照": {
            "A1on_calls": lc["calls_dump"], "A1on_total_tokens": lc["total_tokens"],
            "A1on_cases": "%s/%s" % (lc["cases_pass"], lc["cases_total"]),
            "on_calls_median": on_p["calls_median"], "on_total_median": on_p["total_median"],
            "call_ratio_on_vs_A1on": ratio(on_p["calls_median"], lc["calls_dump"]),
            "token_ratio_on_vs_A1on": ratio(on_p["total_median"], lc["total_tokens"]),
            "quality_premise_ok": bool(on_p["all_green_n"] == len(ON) and lc["cases_pass"] <= HID),
        },
        "J6_探针非平凡": {"probe_failed_values": probe_vals,
                          "constant": len(probe_vals) <= 1,
                          "note": "跨臂恒为同一值 ⇒ 臂级无可解释性; 判别力由 L2 成对单测(错产物⇒failed=1 / 对产物⇒failed=0)承担"},
        "J7_rc语义": "rc=8 public_probe_unmet = 公开用例回放未过 ∧ 回灌预算耗尽 ⇒ 成对报『回放未达成 ∧ 产物可疑』, correctness_asserted=0; 唯一正确性证据 = 隐藏用例实跑",
    }

    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    dst = os.path.join(HERE, "readings-%s.json" % W)
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))

    print("== R544 读数 (%s) ==" % W)
    print("%-6s %-7s %-14s %-9s %-3s %-4s %-6s %-8s %-9s %-9s %-9s %-8s %s" %
          ("arm", "col", "stage", "cases", "rc", "er", "pran", "pfail", "calls", "prompt", "compl", "total", "failed"))
    for arm in ARMS:
        r = out["arms"][arm]
        print("%-6s %-7s %-14s %-9s %-3s %-4s %-6s %-8s %-9s %-9s %-9s %-8s %s" %
              (arm, r["side"], (r["stage"] or "-")[:14], "%s/%s" % (r["cases_pass"], r["cases_total"]),
               r["rc"], r["exec_repairs"], r["public_probe_ran"], r["public_probe_failed"],
               r["calls_dump"], r["prompt_tokens"], r["completion_tokens"], r["total_tokens"],
               ",".join(r["failed_cases"])[:50] or "-"))
    print("\n单变量自洽: prefix_identical=%s role_mounted_all=%s cases58=%s | 机制: on_ran=%s off_absent=%s off_no_marker=%s" % (
        out["invariants"]["prefix_identical"], out["invariants"]["role_mounted_all"],
        out["invariants"]["cases_total_58_all"], out["invariants"]["mechanism_on_arms_ran"],
        out["invariants"]["mechanism_off_arms_absent"], out["invariants"]["mechanism_off_no_marker"]))
    print("J1 %s | J2 %s | J3 %s" % (out["judgments"]["J1_机制启用断言"]["verdict"],
                                     out["judgments"]["J2_假成功消解"]["verdict"],
                                     out["judgments"]["J3_质量"]["verdict"]))
    print("J4 代价(on/off 倍率): calls %s / prompt %s / completion %s / total %s" % (
        out["judgments"]["J4_代价"]["calls"]["ratio_on_off"], out["judgments"]["J4_代价"]["prompt"]["ratio_on_off"],
        out["judgments"]["J4_代价"]["completion"]["ratio_on_off"], out["judgments"]["J4_代价"]["total"]["ratio_on_off"]))
    print("J5 vs A1on: calls %s vs %s (%s), tokens %s vs %s (%s), cases %s" % (
        on_p["calls_median"], lc["calls_dump"], out["judgments"]["J5_同窗旧路径对照"]["call_ratio_on_vs_A1on"],
        on_p["total_median"], lc["total_tokens"], out["judgments"]["J5_同窗旧路径对照"]["token_ratio_on_vs_A1on"],
        out["judgments"]["J5_同窗旧路径对照"]["A1on_cases"]))
    print("readings -> %s" % os.path.relpath(dst, "/home/agentuser/AgentFramework"))
    return 0 if on_p["all_green_n"] == len(ON) else 1


if __name__ == "__main__":
    sys.exit(main())
