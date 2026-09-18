"""R547 读数器 —— g1 产物侧 **早停阈值剂量面** 单变量对照 (AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {0,1,2,3})。

单变量(4 水平): δ=0(轴关,5) / δ=1(5) / δ=2(5) / δ=3(阴控,3) + 旧路径 A1on × 3。窗 = w2。
因果假设(R413 判据抓手): 探针已判产物不合格(pfail≥δ)时, 那次「回灌修复」远端调用是**不必要请求**;
  阈值 δ 决定触发面 ⇒ **剂量-代价响应**(δ=1 最宽, δ=3 在实测分布上从不触发 = 判别性阴控)。
读数来源(三路交叉, 与 R542/R544/R546 同口径):
  ① transcript.json (机制断言 + rc/stage + early_stop_pfail/early_stop_skipped; **不作正确性证据**)
  ② adapter side-agent-* 实发用量 (付费口径唯一来源: 中继 usage)
  ③ 隐藏用例实跑 cases.txt (58 条, **唯一正确性证据**)
  ④ 产物树独立清点 (work 文件数) —— 「产物在盘」的非自报判据。
窗面: w1 读数属 R546(run-w1, 已发布) ⇒ **只并列引用 + 极差, 禁跨轮相减**。

用法: python3 analyze_r547.py --run-dir <D> --window w2 [--taskset <TS>] [--out <json>]
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
W1_READINGS = os.path.join(REPO, "eval/rover/r546/readings-w1.json")

COLS = {
    "d0": ["E0a", "E0b", "E0c", "E0d", "E0e"],
    "d1": ["D1a", "D1b", "D1c", "D1d", "D1e"],
    "d2": ["E1a", "E1b", "E1c", "E1d", "E1e"],
    "d3": ["D3a", "D3b", "D3c"],
}
THRESH = {"d0": 0, "d1": 1, "d2": 2, "d3": 3}
LEG = ["A1on", "A1onb", "A1onc"]
ARMS = [a for c in ("d0", "d2", "d1", "d3") for a in COLS[c]] + LEG
TID = "g1"
HID = 58

KEYS = ("rc", "stage", "calls", "prompt_tokens", "completion_tokens", "cache_hit_tokens",
        "cache_miss_tokens", "repair_rounds", "exec_repairs", "plan_steps_total", "steps_executed",
        "self_test_unmet", "correctness_asserted", "role_note_chars", "prefix_sha256", "prefix_chars",
        "task_sha256", "public_probe_ran", "public_probe_total", "public_probe_failed",
        "public_probe_trigger_rc", "public_probe_reason", "early_stop_pfail", "early_stop_skipped")


def load(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


a540 = load(A540, "analyze_r540_mod")


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
    return d


def cases(D, arm):
    p = os.path.join(D, arm, TID, "cases.txt")
    if not os.path.isfile(p):
        return {"pass": 0, "total": 0, "rc": None, "failed": [], "public_failed": []}
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    rc = None
    if lines and lines[-1].strip().isdigit():
        rc = int(lines[-1].strip()); lines = lines[:-1]
    tot = [l for l in lines if l.startswith("CASE ")]
    npass = [l for l in tot if l.strip().endswith("PASS")]
    failed = [l.split()[1] for l in tot if not l.strip().endswith("PASS")]
    return {"pass": len(npass), "total": len(tot), "rc": rc, "failed": failed,
            "public_failed": [x for x in failed if "public" in x]}


def artifact_count(D, arm):
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
    out = {"round": "r547", "window": W, "run_dir": os.path.relpath(D, REPO),
           "single_variable": "AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {0(轴关),1,2,3} —— 触发面随阈值收窄, 省下的是那次回灌修复远端调用",
           "arms": {}, "columns": {}, "invariants": {}, "judgments": {}, "notes": []}

    for arm in ARMS:
        i0, i1 = (rng.get("%s-%s" % (arm, TID)) or [0, 0])
        t = transcript(D, arm)
        c = cases(D, arm)
        u = a540.cost(dumps, "agent", i0, i1) if os.path.isdir(dumps) else {}
        col = next((k for k, v in COLS.items() if arm in v), "legacy")
        rec = {
            "column": col, "threshold": THRESH.get(col, None), "range": [i0, i1],
            "rc": t.get("rc"), "stage": t.get("stage"), "reason_head": (t.get("reason") or "")[:160],
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
            "early_stop_pfail": t.get("early_stop_pfail"), "early_stop_skipped": t.get("early_stop_skipped"),
            "artifact_files": artifact_count(D, arm),
            "role_note_chars": t.get("role_note_chars"), "prefix_sha256": t.get("prefix_sha256"),
            "cases_pass": c["pass"], "cases_total": c["total"], "cases_rc": c["rc"],
            "all_green": bool(c["rc"] == 0 and c["total"] == HID and c["pass"] == HID),
            "failed_cases": c["failed"], "public_failed": c["public_failed"],
            "reply_has_probe_marker": None, "reply_has_early_stop_marker": None, "reply_chars": None,
        }
        rp = os.path.join(D, arm, TID, "reply.txt")
        if os.path.isfile(rp):
            txt = io.open(rp, encoding="utf-8", errors="replace").read()
            rec["reply_has_probe_marker"] = "R1_PUBLIC_PROBE" in txt
            rec["reply_has_early_stop_marker"] = "R1_EARLY_STOP" in txt
            rec["reply_chars"] = len(txt)
        out["arms"][arm] = rec

    # ---- 列汇总 (逐 δ) ------------------------------------------------------
    for name, arms in COLS.items():
        recs = [out["arms"][k] for k in arms]
        out["columns"][name] = {
            "arms": arms, "threshold": THRESH[name],
            "rc": [r["rc"] for r in recs], "cases_pass": [r["cases_pass"] for r in recs],
            "all_green": [r["all_green"] for r in recs],
            "all_green_n": sum(1 for r in recs if r["all_green"]),
            "cases_median": median([r["cases_pass"] for r in recs]),
            "calls": [r["calls_dump"] for r in recs],
            "calls_median": median([r["calls_dump"] for r in recs]),
            "calls_spread": spread([r["calls_dump"] for r in recs]),
            "prompt_median": median([r["prompt_tokens"] for r in recs]),
            "completion_median": median([r["completion_tokens"] for r in recs]),
            "total_median": median([r["total_tokens"] for r in recs]),
            "total_spread": spread([r["total_tokens"] for r in recs]),
            "probe_failed": [r["public_probe_failed"] for r in recs],
            "skipped": [r["early_stop_skipped"] for r in recs],
            "false_success_n": sum(1 for r in recs if r["rc"] == 0 and not r["all_green"]),
        }
    leg = [out["arms"][k] for k in LEG]
    out["columns"]["legacy"] = {"arms": LEG, "threshold": None,
                                "cases_pass": [r["cases_pass"] for r in leg],
                                "all_green_n": sum(1 for r in leg if r["all_green"]),
                                "calls": [r["calls_dump"] for r in leg],
                                "calls_median": median([r["calls_dump"] for r in leg]),
                                "calls_spread": spread([r["calls_dump"] for r in leg]),
                                "total_median": median([r["total_tokens"] for r in leg]),
                                "total_spread": spread([r["total_tokens"] for r in leg])}

    # ---- 不变量 -------------------------------------------------------------
    tcols = [k for k in COLS if k != "d0"]
    pfx = sorted({out["arms"][k].get("prefix_sha256") for k in ARMS if k not in LEG})
    roles = sorted({out["arms"][k].get("role_note_chars") for k in ARMS if k not in LEG})
    d0 = out["columns"]["d0"]
    out["invariants"] = {
        "prefix_sha256_set": pfx, "prefix_identical": len(pfx) == 1,
        "role_note_chars_set": roles, "role_mounted_all": roles == [326],
        "cases_total_58_all": all(out["arms"][k]["cases_total"] == HID for k in ARMS if k not in LEG),
        "threshold_field_matches_column": all(
            (out["arms"][k]["early_stop_pfail"] in (None, THRESH[c])) for c in tcols for k in COLS[c]),
        "d0_zero_regression_fields_absent": all(
            out["arms"][k]["early_stop_pfail"] is None and not out["arms"][k]["reply_has_early_stop_marker"]
            for k in COLS["d0"]),
        "reachable_arms": [k for k in ARMS if out["arms"][k]["artifact_files"] > 0],
        "probe_ran_on_reachable": all(out["arms"][k]["public_probe_ran"] == 1
                                      for k in ARMS if k not in LEG and out["arms"][k]["artifact_files"] > 0
                                      and out["arms"][k]["public_probe_ran"] is not None),
        "nonzero_exit_covered": any(v not in (None, 0)
                                    for v in (out["arms"][k]["public_probe_trigger_rc"] for k in ARMS)),
    }

    # ---- K1 剂量机制 (机械, 逐 δ) -------------------------------------------
    k1 = {}
    for c in ("d1", "d2", "d3"):
        th = THRESH[c]
        fired, nonfired, void, viol = [], [], [], []
        for k in COLS[c]:
            r = out["arms"][k]
            pf = r["public_probe_failed"]
            if pf is None:
                void.append(k); continue
            if pf >= th:
                fired.append(k)
                bad = []
                if r["early_stop_skipped"] != 1: bad.append("skipped!=1")
                if r["exec_repairs"] != 0: bad.append("exec_repairs!=0")
                if not r["reply_has_early_stop_marker"]: bad.append("no_marker")
                if bad: viol.append({"arm": k, "pfail": pf, "why": bad})
            else:
                nonfired.append(k)
                bad = []
                if r["early_stop_skipped"] not in (None, 0): bad.append("skipped!=0")
                if r["reply_has_early_stop_marker"]: bad.append("marker_present")
                if bad: viol.append({"arm": k, "pfail": pf, "why": bad})
        k1[c] = {"threshold": th, "fired": fired, "fired_n": len(fired), "nonfired": nonfired,
                 "nonfired_n": len(nonfired), "void": void, "violations": viol,
                 "verdict": ("VOID(该剂量未行使)" if not fired and not nonfired else
                             ("PASS" if not viol else "FAIL(%d)" % len(viol)))}
    out["judgments"]["K1_剂量机制"] = k1

    # ---- K2 剂量-代价 -------------------------------------------------------
    k2 = {}
    for c in ("d0", "d1", "d2", "d3"):
        col = out["columns"][c]
        k2[c] = {"threshold": THRESH[c], "n": len(COLS[c]),
                 "calls": col["calls"], "calls_median": col["calls_median"], "calls_spread": col["calls_spread"],
                 "total_median": col["total_median"], "total_spread": col["total_spread"],
                 "prompt_median": col["prompt_median"], "completion_median": col["completion_median"],
                 "calls_ratio_vs_d0": ratio(col["calls_median"], d0["calls_median"]),
                 "total_ratio_vs_d0": ratio(col["total_median"], d0["total_median"]),
                 "skipped_n": sum(1 for x in col["skipped"] if x == 1)}
    k2["point_estimates"] = {
        "fired_n_monotone_d1_ge_d2_ge_d3": bool(k1["d1"]["fired_n"] >= k1["d2"]["fired_n"] >= k1["d3"]["fired_n"]),
        "d3_equals_d0_on_calls": bool(out["columns"]["d3"]["calls_median"] == d0["calls_median"]),
        "saved_calls_marginal = fired_n × 1": {"d1": k1["d1"]["fired_n"], "d2": k1["d2"]["fired_n"],
                                              "d3": k1["d3"]["fired_n"]},
    }
    out["judgments"]["K2_剂量代价"] = k2

    # ---- K3 配对反事实 (判据性) --------------------------------------------
    k3 = {}
    d0recs = [out["arms"][k] for k in COLS["d0"]]
    for c in ("d1", "d2"):
        th = THRESH[c]
        tr = [out["arms"][k] for k in COLS[c] if (out["arms"][k]["public_probe_failed"] or -1) >= th]
        ct = [out["arms"][k] for k in COLS["d0"] if (out["arms"][k]["public_probe_failed"] or -1) >= th]
        enough = len(tr) >= 5 and len(ct) >= 5
        k3[c] = {"threshold": th,
                 "treated_arms": [r["column"] for r in tr], "treated_n": len(tr),
                 "control_arms_pfail_ge_th": [k for k in COLS["d0"]
                                              if (out["arms"][k]["public_probe_failed"] or -1) >= th],
                 "control_n": len(ct),
                 "treated_calls_median": median([r["calls_dump"] for r in tr]),
                 "control_calls_median": median([r["calls_dump"] for r in ct]),
                 "treated_total_median": median([r["total_tokens"] for r in tr]),
                 "control_total_median": median([r["total_tokens"] for r in ct]),
                 "paired_by_pfail": {str(v): {
                     "treated": [r["calls_dump"] for k, r in ((k, out["arms"][k]) for k in COLS[c])
                                 if r["public_probe_failed"] == v],
                     "control": [r["calls_dump"] for k in COLS["d0"]
                                 if out["arms"][k]["public_probe_failed"] == v]}
                     for v in sorted({(r["public_probe_failed"]) for r in tr if r["public_probe_failed"] is not None})},
                 "sample_sufficient": enough,
                 "verdict": ("可判(两类 n≥5)" if enough else
                             "样本不足(n_treated=%d, n_control=%d) ⇒ 不作降幅宣称" % (len(tr), len(ct)))}
    out["judgments"]["K3_配对反事实"] = k3

    # ---- K4 质量非劣 -------------------------------------------------------
    fired_all = [k for c in ("d1", "d2", "d3") for k in k1[c]["fired"]]
    nonfired_all = [k for c in ("d1", "d2", "d3") for k in k1[c]["nonfired"]]
    out["judgments"]["K4_质量"] = {
        "per_column": {c: {"all_green_n": out["columns"][c]["all_green_n"], "n": len(COLS[c]),
                           "cases_median": out["columns"][c]["cases_median"],
                           "cases": out["columns"][c]["cases_pass"]} for c in ("d0", "d1", "d2", "d3")},
        "fired_subset": {"arms": fired_all,
                         "all_green_n": sum(1 for k in fired_all if out["arms"][k]["all_green"]),
                         "cases_median": median([out["arms"][k]["cases_pass"] for k in fired_all])},
        "nonfired_subset": {"arms": nonfired_all,
                            "all_green_n": sum(1 for k in nonfired_all if out["arms"][k]["all_green"]),
                            "cases_median": median([out["arms"][k]["cases_pass"] for k in nonfired_all])},
        "not_worse_vs_d0": {c: bool(out["columns"][c]["all_green_n"] >= d0["all_green_n"]
                                    and (out["columns"][c]["cases_median"] or 0) >= (d0["cases_median"] or 0))
                            for c in ("d1", "d2", "d3")},
    }

    # ---- K5 零回归 ---------------------------------------------------------
    out["judgments"]["K5_零回归"] = {
        "d0_fields_absent": out["invariants"]["d0_zero_regression_fields_absent"],
        "d0_reply_scan": {k: out["arms"][k]["reply_has_early_stop_marker"] for k in COLS["d0"]},
        "note": "另外机检: 既有测试全绿 + AOT IL 警告 0 (产品源码本轮零改动 ⇒ 复用 R546 同一二进制 sha256)",
    }

    # ---- K6 窗口面 (候选①; 只并列, 禁相减) ---------------------------------
    k6 = {"w2": {c: {"calls_median": out["columns"][c]["calls_median"],
                     "calls_spread": out["columns"][c]["calls_spread"],
                     "cases_median": out["columns"][c]["cases_median"],
                     "all_green_n": out["columns"][c]["all_green_n"]} for c in ("d0", "d2")}}
    if os.path.isfile(W1_READINGS):
        try:
            w1 = json.load(io.open(W1_READINGS, encoding="utf-8"))
            k6["w1_source"] = os.path.relpath(W1_READINGS, REPO) + " (R546 轮, 同臂清单/同输入)"
            k6["w1"] = {c: {"calls_median": (w1["columns"][c] or {}).get("calls_median"),
                            "calls_spread": (w1["columns"][c] or {}).get("calls_spread"),
                            "cases_median": (w1["columns"][c] or {}).get("cases_median"),
                            "all_green_n": (w1["columns"][c] or {}).get("all_green_n"),
                            "calls": (w1["columns"][c] or {}).get("calls")}
                        for c in ("off", "on")}
            for w2c, w1c in (("d0", "off"), ("d2", "on")):
                k6.setdefault("side_by_side", {})[w2c] = {
                    "w1_calls_median": k6["w1"][w1c]["calls_median"],
                    "w2_calls_median": k6["w2"][w2c]["calls_median"],
                    "w1_calls_list": k6["w1"][w1c]["calls"], "w2_calls_list": k6["w2"][w2c]["calls"],
                    "span_across_windows": spread([k6["w1"][w1c]["calls_median"], k6["w2"][w2c]["calls_median"]]),
                }
        except Exception as e:  # noqa: BLE001
            k6["w1_error"] = type(e).__name__
    k6["discipline"] = "窗间只并列读数与极差; **禁跨轮相减**(w1 属 R546 轮)"
    out["judgments"]["K6_窗口面"] = k6

    # ---- K7 旧路径列 -------------------------------------------------------
    k7 = {"w2_samples": [{"arm": k, "calls": out["arms"][k]["calls_dump"],
                          "total": out["arms"][k]["total_tokens"],
                          "cases": "%s/%s" % (out["arms"][k]["cases_pass"], out["arms"][k]["cases_total"])}
                         for k in LEG],
          "w2_calls_median": out["columns"]["legacy"]["calls_median"],
          "w2_calls_spread": out["columns"]["legacy"]["calls_spread"],
          "w2_total_median": out["columns"]["legacy"]["total_median"],
          "quality_premise": "旧路径满绿 ⇒ 比值只作参考, 不得当增益证据",
          "leg_all_green_n": sum(1 for k in LEG if out["arms"][k]["all_green"])}
    if os.path.isfile(W1_READINGS):
        try:
            w1 = json.load(io.open(W1_READINGS, encoding="utf-8"))
            k7["w1_calls"] = (w1["columns"]["legacy"] or {}).get("calls")
            k7["w1_calls_median"] = (w1["columns"]["legacy"] or {}).get("calls_median")
            k7["w1_calls_spread"] = (w1["columns"]["legacy"] or {}).get("calls_spread")
            k7["w1_all_green_n"] = (w1["columns"]["legacy"] or {}).get("all_green_n")
            k7["two_window_n"] = len(k7["w1_calls"] or []) + len(LEG)
        except Exception:  # noqa: BLE001
            pass
    out["judgments"]["K7_旧路径列"] = k7

    out["judgments"]["K8_收口"] = {"gate": "eval/rover/r507pre/exec_precondition.py --round r547",
                                   "precond_rc": None,
                                   "rule": "rc≠0 ⇒ 本轮一切降幅标「参考(未可验收)」, 禁作验收依据"}
    out["notes"].append("K3 样本不足的口径 = 未获得证据(≠获得证据); 与 R546 J10 同。")
    out["notes"].append("δ=3 是判别性阴控: 若实测 pfail 从未 ≥3 而 δ=3 列出现 skipped=1 ⇒ 阈值语义被证伪。")

    p = a.out or os.path.join(os.path.dirname(D.rstrip("/")), "readings-%s.json" % W)
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- 人读摘要 -----------------------------------------------------------
    L = []
    L.append("== R547 δ 剂量面 (%s) ==" % W)
    for c in ("d0", "d1", "d2", "d3"):
        col = out["columns"][c]
        L.append("  δ=%-2d n=%d calls=%s(中位 %s) total中位=%s 用例中位=%s 全绿=%d/%d 行使=%d" % (
            THRESH[c], len(COLS[c]), col["calls"], col["calls_median"], col["total_median"],
            col["cases_median"], col["all_green_n"], len(COLS[c]),
            sum(1 for x in col["skipped"] if x == 1)))
    for c in ("d1", "d2", "d3"):
        L.append("  K1 δ=%d: %s fired=%s nonfired=%s void=%s" % (
            THRESH[c], k1[c]["verdict"], k1[c]["fired"], k1[c]["nonfired"], k1[c]["void"]))
        for v in k1[c]["violations"]:
            L.append("     [违] %s" % v)
    for c in ("d1", "d2"):
        L.append("  K3 δ=%d: %s" % (THRESH[c], k3[c]["verdict"]))
    L.append("  K4 质量: " + " ".join(
        "δ%d 全绿%d/%d 用例中位%s" % (THRESH[c], out["columns"][c]["all_green_n"], len(COLS[c]),
                                      out["columns"][c]["cases_median"]) for c in ("d0", "d1", "d2", "d3")))
    L.append("  K6 窗面: " + json.dumps(k6.get("side_by_side", {}), ensure_ascii=False))
    L.append("  K7 旧路径: w2=%s (中位 %s, 极差 %s) | w1=%s (中位 %s)" % (
        out["columns"]["legacy"]["calls"], k7["w2_calls_median"], k7["w2_calls_spread"],
        k7.get("w1_calls"), k7.get("w1_calls_median")))
    L.append("  不变量: prefix同=%s role挂载=%s 阈值字段对齐=%s d0零回归=%s" % (
        out["invariants"]["prefix_identical"], out["invariants"]["role_mounted_all"],
        out["invariants"]["threshold_field_matches_column"],
        out["invariants"]["d0_zero_regression_fields_absent"]))
    L.append("读数落盘: %s" % os.path.relpath(p, REPO))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
