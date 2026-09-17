#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R545 读数器 —— g1 产物侧公开用例独立回放 **触发面修正** 轴 (R544 预注册 J1 被证伪后的修订轮)。

单变量: AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {unset(off), 1(on)} × **5 独立 session**
        + 旧路径基线 A1on × **3 独立 session**(候选③: 该列跨窗 8.5× 摆动, 须多样本定因)。
R545 v2 与 v1 的差别(只剩这一处):
  触发面 `exec.Rc==0`  →  **全部「产物已在盘」出口(rc 0/5/8)**; 「产物在盘」判据 =
  执行器 Steps 里出现过 write_file(唯一落盘工具), 与链自报 rc 无关。
读数来源(三路交叉, 与 R542/R544 同口径):
  ① transcript.json (机制启用断言 + rc/stage; **不作正确性证据**)
  ② adapter side-agent-* 实发用量 (付费口径唯一来源: 中继 usage)
  ③ 隐藏用例实跑 cases.txt (58 条, **唯一正确性证据**)
  ④ [R545 新增] 产物树独立清点 (work 目录文件数) —— 「产物在盘」的**非自报**判据, 用于把 J1 限定到可触达臂。

用法: python3 analyze_r545.py --run-dir <D> --window w1 [--taskset <TS>] [--out <json>]
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/agentuser/AgentFramework"
A540 = os.path.join(REPO, "eval/rover/r540/analyze_r540.py")

OFF = ["P0a", "P0b", "P0c", "P0d", "P0e"]
ON = ["P1a", "P1b", "P1c", "P1d", "P1e"]
LEG = ["A1on", "A1onb", "A1onc"]
ARMS = OFF + ON + LEG
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
        "task_sha256", "public_probe_ran", "public_probe_total", "public_probe_failed",
        "public_probe_trigger_rc", "public_probe_reason")


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


def artifact_count(D, arm):
    """产物树独立清点(非自报): work 下真实文件数, 去掉字节码缓存。"""
    root = os.path.join(D, arm, TID, "work")
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            if f.endswith(".pyc"):
                continue
            n += 1
    return n


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else round((xs[n // 2 - 1] + xs[n // 2]) / 2.0, 1)


def spread(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"min": min(xs), "max": max(xs), "span": max(xs) - min(xs)}


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
    out = {"round": "r545", "window": W,
           "run_dir": os.path.relpath(D, REPO),
           "single_variable": "AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK (触发面=v2: 产物在盘的全部出口)",
           "arms": {}, "columns": {}, "invariants": {}, "judgments": {}, "notes": []}

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
            "public_probe_trigger_rc": t.get("public_probe_trigger_rc"),
            "public_probe_reason": t.get("public_probe_reason"),
            "artifact_files": artifact_count(D, arm),
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
            "cases_median": median([r["cases_pass"] for r in recs]),
            "calls": [r["calls_dump"] for r in recs],
            "prompt_tokens": [r["prompt_tokens"] for r in recs],
            "completion_tokens": [r["completion_tokens"] for r in recs],
            "total_tokens": [r["total_tokens"] for r in recs],
            "calls_median": median([r["calls_dump"] for r in recs]),
            "prompt_median": median([r["prompt_tokens"] for r in recs]),
            "completion_median": median([r["completion_tokens"] for r in recs]),
            "total_median": median([r["total_tokens"] for r in recs]),
            "calls_spread": spread([r["calls_dump"] for r in recs]),
            "total_spread": spread([r["total_tokens"] for r in recs]),
            "probe_failed": [r["public_probe_failed"] for r in recs],
            "trigger_rc": [r["public_probe_trigger_rc"] for r in recs],
            "false_success_n": sum(1 for r in recs if r["rc"] == 0 and not r["all_green"]),
        }
    leg = [out["arms"][k] for k in LEG]
    out["columns"]["legacy"] = {"arms": LEG, "cases_pass": [r["cases_pass"] for r in leg],
                                "all_green_n": sum(1 for r in leg if r["all_green"]),
                                "calls": [r["calls_dump"] for r in leg],
                                "total_tokens": [r["total_tokens"] for r in leg],
                                "calls_median": median([r["calls_dump"] for r in leg]),
                                "total_median": median([r["total_tokens"] for r in leg]),
                                "calls_spread": spread([r["calls_dump"] for r in leg]),
                                "total_spread": spread([r["total_tokens"] for r in leg])}

    # ---- 单变量自洽门 + 触发面可触达集 --------------------------------------
    pfx = sorted({out["arms"][k].get("prefix_sha256") for k in ON + OFF})
    roles = sorted({out["arms"][k].get("role_note_chars") for k in ON + OFF})
    reachable = [k for k in ON + OFF if out["arms"][k]["artifact_files"] > 0]
    on_reach = [k for k in ON if out["arms"][k]["artifact_files"] > 0]
    on_trig = {k: out["arms"][k]["public_probe_trigger_rc"] for k in ON}
    out["invariants"] = {
        "prefix_sha256_set": pfx, "prefix_identical": len(pfx) == 1,
        "role_note_chars_set": roles, "role_mounted_all": roles == [326],
        "cases_total_58_all": all(out["arms"][k]["cases_total"] == HID for k in ON + OFF),
        "reachable_arms": reachable, "reachable_on_arms": on_reach,
        "mechanism_on_arms_ran": all(out["arms"][k]["public_probe_ran"] == 1 for k in on_reach),
        "mechanism_on_arms_ran_all": all(out["arms"][k]["public_probe_ran"] == 1 for k in ON),
        "mechanism_off_arms_absent": all(out["arms"][k]["public_probe_ran"] is None for k in OFF),
        "mechanism_off_no_marker": all(not out["arms"][k]["reply_has_probe_marker"] for k in OFF),
        "on_trigger_rc": on_trig,
        "nonzero_exit_covered": any(v not in (None, 0) for v in on_trig.values()),
    }

    # ---- 判据 ---------------------------------------------------------------
    on_p, off_p = out["columns"]["on"], out["columns"]["off"]
    probe_vals = sorted({r["public_probe_failed"] for r in (out["arms"][k] for k in ON)
                         if r["public_probe_failed"] is not None})
    out["judgments"] = {
        "J1v2_机制启用(触发面修正)": {
            "scope": "on 臂中**产物在盘**(work 文件数>0, 非自报)的臂 ⇒ 必须 public_probe_ran=1",
            "reachable_on_arms": on_reach,
            "on_ran": [out["arms"][k]["public_probe_ran"] for k in ON],
            "on_artifact_files": [out["arms"][k]["artifact_files"] for k in ON],
            "off_ran": [out["arms"][k]["public_probe_ran"] for k in OFF],
            "verdict": ("PASS" if out["invariants"]["mechanism_on_arms_ran"]
                        and out["invariants"]["mechanism_off_arms_absent"] else "FAIL(臂判 VOID)"),
        },
        "J8_出口覆盖": {
            "trigger_rc_set_on": sorted({v for v in on_trig.values() if v is not None}),
            "nonzero_exit_covered": out["invariants"]["nonzero_exit_covered"],
            "note": "v1 的触发面只有 rc=0 ⇒ 该集合必为 {0}; v2 若出现 ≠0 值 ⇒ 旧触发面外的出口真被覆盖",
        },
        "J2_假成功消解": {
            "off_false_success_n": off_p["false_success_n"], "on_false_success_n": on_p["false_success_n"],
            "verdict": ("支持" if on_p["false_success_n"] < off_p["false_success_n"]
                        else ("未消解: 两列同为 %s" % on_p["false_success_n"])),
        },
        "J3_质量": {"off_all_green": off_p["all_green"], "on_all_green": on_p["all_green"],
                    "off_cases": off_p["cases_pass"], "on_cases": on_p["cases_pass"],
                    "off_all_green_n": off_p["all_green_n"], "on_all_green_n": on_p["all_green_n"],
                    "off_cases_median": off_p["cases_median"], "on_cases_median": on_p["cases_median"],
                    # R545 判据器实现修正(同窗同产物重算, 不动读数): 预注册 J3 是**两维**非劣
                    # ① 全绿臂数 ② 用例通过数中位; 初版实现只算了 ①(与预注册不符) ⇒ 补齐并如实分列。
                    "all_green_not_worse": bool(on_p["all_green_n"] >= off_p["all_green_n"]),
                    "cases_median_not_worse": bool(on_p["cases_median"] >= off_p["cases_median"]),
                    "verdict": ("不降" if (on_p["all_green_n"] >= off_p["all_green_n"]
                                          and on_p["cases_median"] >= off_p["cases_median"])
                                else ("收窄(如实): 全绿臂 %d vs %d %s / 用例中位 %s vs %s %s"
                                      % (on_p["all_green_n"], off_p["all_green_n"],
                                         "≥" if on_p["all_green_n"] >= off_p["all_green_n"] else "<",
                                         on_p["cases_median"], off_p["cases_median"],
                                         "≥" if on_p["cases_median"] >= off_p["cases_median"] else "<")))},
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
            "A1on_samples": [{"arm": k, "calls": out["arms"][k]["calls_dump"],
                              "total": out["arms"][k]["total_tokens"],
                              "cases": "%s/%s" % (out["arms"][k]["cases_pass"], out["arms"][k]["cases_total"])}
                             for k in LEG],
            "A1on_calls_median": out["columns"]["legacy"]["calls_median"],
            "A1on_calls_spread": out["columns"]["legacy"]["calls_spread"],
            "A1on_total_spread": out["columns"]["legacy"]["total_spread"],
            "on_calls_median": on_p["calls_median"], "on_total_median": on_p["total_median"],
            "call_ratio_on_vs_A1on": ratio(on_p["calls_median"], out["columns"]["legacy"]["calls_median"]),
            "token_ratio_on_vs_A1on": ratio(on_p["total_median"], out["columns"]["legacy"]["total_median"]),
            "quality_premise_ok": bool(on_p["all_green_n"] == len(ON)
                                       and max(r["cases_pass"] for r in leg) <= HID),
            "quality_premise_note": "前提不成立 ⇒ 本列的 calls/token 比值**只作参考**, 不得当增益证据"
                                    " (质量前提 = 我方全绿臂数达满 ∧ 旧路径无满绿; 本窗旧路径 2/3 满绿 ⇒ 假)",
            "leg_quality_all_green_n": sum(1 for r in leg if r["cases_pass"] == r["cases_total"]),
            "leg_cases_median": sorted(r["cases_pass"] for r in leg)[len(leg) // 2],
        },
        "J6_探针非平凡": {"probe_failed_values": probe_vals, "constant": len(probe_vals) <= 1,
                          "note": "跨臂恒为同一值 ⇒ 臂级无可解释性(判别力另由 L2 成对单测承担); "
                                  "另: v2 的 no_artifacts_on_disk 明确**不是**失败, 不得当 0 分"},
        "J7_rc语义": "rc=8 有两种 stage: self_test_unmet(模型自撰期望不符) / public_probe_unmet(管道自产证据不符); "
                     "两者都 correctness_asserted=0, 不作正确性证据; 唯一正确性证据 = 隐藏用例实跑。",
        "J9_采样方差": {
            "off_calls_spread": off_p["calls_spread"], "on_calls_spread": on_p["calls_spread"],
            "off_total_spread": off_p["total_spread"], "on_total_spread": on_p["total_spread"],
            "legacy_calls_spread": out["columns"]["legacy"]["calls_spread"],
            "note": "离散结局(rc/用例数)主导方差; 报极差与逐窗读数, 禁以单臂定轴。",
        },
        "posthoc_公开用例回放对隐藏用例的预测力": {
            "label": "**事后(post-hoc) 单列**, 非预注册闸; 只报读数与单调性, 不作验收依据",
            "pairs": [{"arm": k, "public_probe_failed": out["arms"][k]["public_probe_failed"],
                       "cases_pass": out["arms"][k]["cases_pass"]} for k in ON],
            "mean_hidden_by_public_failed": {
                str(v): round(sum(r["cases_pass"] for r in (out["arms"][k] for k in ON)
                                  if r["public_probe_failed"] == v)
                              / max(1, sum(1 for r in (out["arms"][k] for k in ON)
                                           if r["public_probe_failed"] == v)), 1)
                for v in probe_vals},
            "monotone_less_hidden_as_public_fail_rises": bool(
                [sum(r["cases_pass"] for r in (out["arms"][k] for k in ON)
                     if r["public_probe_failed"] == v)
                 / max(1, sum(1 for r in (out["arms"][k] for k in ON)
                              if r["public_probe_failed"] == v)) for v in probe_vals]
                == sorted([sum(r["cases_pass"] for r in (out["arms"][k] for k in ON)
                               if r["public_probe_failed"] == v)
                           / max(1, sum(1 for r in (out["arms"][k] for k in ON)
                                        if r["public_probe_failed"] == v)) for v in probe_vals],
                          reverse=True)),
            "note": "公开面回放**零远端调用**(纯本地进程内执行) ⇒ 若其与隐藏分单调相关, 则可作「少发远端请求」的替代信号(主线判据抓手)。",
        },
    }

    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    dst = os.path.join(HERE, "readings-%s.json" % W)
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))

    print("== R545 读数 (%s) ==" % W)
    print("%-6s %-7s %-16s %-9s %-3s %-4s %-5s %-9s %-6s %-8s %-9s %-9s %-9s %-8s %s" %
          ("arm", "col", "stage", "cases", "rc", "er", "files", "trig_rc", "pran", "pfail",
           "calls", "prompt", "compl", "total", "failed"))
    for arm in ARMS:
        r = out["arms"][arm]
        print("%-6s %-7s %-16s %-9s %-3s %-4s %-5s %-9s %-6s %-8s %-9s %-9s %-9s %-8s %s" %
              (arm, r["side"], (r["stage"] or "-")[:16], "%s/%s" % (r["cases_pass"], r["cases_total"]),
               r["rc"], r["exec_repairs"], r["artifact_files"], r["public_probe_trigger_rc"],
               r["public_probe_ran"], r["public_probe_failed"],
               r["calls_dump"], r["prompt_tokens"], r["completion_tokens"], r["total_tokens"],
               ",".join(r["failed_cases"])[:44] or "-"))
    print("\n单变量自洽: prefix_identical=%s role_mounted_all=%s cases58=%s | 机制: on_ran(可触达)=%s off_absent=%s off_no_marker=%s" % (
        out["invariants"]["prefix_identical"], out["invariants"]["role_mounted_all"],
        out["invariants"]["cases_total_58_all"], out["invariants"]["mechanism_on_arms_ran"],
        out["invariants"]["mechanism_off_arms_absent"], out["invariants"]["mechanism_off_no_marker"]))
    print("J1v2 %s (可触达 on 臂 %s) | J8 出口覆盖 %s (trigger_rc 集 %s)" % (
        out["judgments"]["J1v2_机制启用(触发面修正)"]["verdict"], on_reach,
        out["invariants"]["nonzero_exit_covered"], out["judgments"]["J8_出口覆盖"]["trigger_rc_set_on"]))
    print("J2 %s | J3 %s" % (out["judgments"]["J2_假成功消解"]["verdict"], out["judgments"]["J3_质量"]["verdict"]))
    print("J4 代价(on/off 中位倍率): calls %s / prompt %s / completion %s / total %s" % (
        out["judgments"]["J4_代价"]["calls"]["ratio_on_off"], out["judgments"]["J4_代价"]["prompt"]["ratio_on_off"],
        out["judgments"]["J4_代价"]["completion"]["ratio_on_off"], out["judgments"]["J4_代价"]["total"]["ratio_on_off"]))
    print("J5 vs A1on(3 样本): calls 中位 %s vs %s (极差 %s), tokens 中位 %s vs %s (极差 %s), 我方全绿 %s/%s" % (
        on_p["calls_median"], out["columns"]["legacy"]["calls_median"], out["columns"]["legacy"]["calls_spread"],
        on_p["total_median"], out["columns"]["legacy"]["total_median"], out["columns"]["legacy"]["total_spread"],
        on_p["all_green_n"], len(ON)))
    print("readings -> %s" % os.path.relpath(dst, REPO))
    return 0 if on_p["all_green_n"] == len(ON) else 1


if __name__ == "__main__":
    sys.exit(main())
