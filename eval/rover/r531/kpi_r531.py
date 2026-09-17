#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R531 分列 KPI: 四臂 (A0-off / A1-on / A2-merge / C-codex) 同窗读数 + 合批轴对照。

口径 (禁跨轮相减):
  · calls        = 该臂该窗**全部** LLM 调用数 (按 adapter dump 逐条计, request_id 去重见 ufd);
  · new_prompt   = prompt_tokens - cached_tokens (新算 token, 即"不必要的远端请求"的代理量);
  · hit_pct      = cached_tokens / prompt_tokens;
  · completion   = completion_tokens;
  · cases        = Σpassed / Σtotal (机械判分清点, 不取模型裁判)。
判据 (预注册 prediction 逐条对照):
  P1 merge 调用降 >= 15% / P2 merge completion 降 >= 15% / P3 质量不降 (A2 每题目 all_pass 且不少于 A1)。
外部真值不完整 (codex 臂某题未全对) ⇒ 该窗对照列标 unreliable, 并单列, 不进验收面。
只读本仓读数 ⇒ **闭合前必跑** exec_precondition (铁律 11); rc!=0 时本表一律标「参考(未可验收)」。
"""
import argparse, io, json, os, sys

REPO = "/home/agentuser/AgentFramework"
ARMS = ["A0-off", "A1-on", "A2-merge", "codex"]
TRUTH = "codex"


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def agg(rows):
    a = {"calls": 0, "prompt": 0, "cached": 0, "completion": 0, "total": 0, "unrep": 0,
         "cases_pass": 0, "cases_total": 0, "tasks": {}, "empty": []}
    for r in rows:
        a["calls"] += r.get("calls") or 0
        a["prompt"] += r.get("prompt_tokens") or 0
        a["cached"] += r.get("cached_tokens") or 0
        a["completion"] += r.get("completion_tokens") or 0
        a["total"] += r.get("total_tokens") or 0
        a["unrep"] += r.get("unreported_usage") or 0
        a["cases_pass"] += r.get("cases_pass") or 0
        a["cases_total"] += r.get("cases_total") or 0
        a["tasks"][r["tid"]] = {"all_pass": bool(r.get("all_pass")), "cases": "%s/%s" % (
            r.get("cases_pass"), r.get("cases_total")), "calls": r.get("calls") or 0,
            "completion": r.get("completion_tokens") or 0, "family": r.get("family")}
        if r.get("snapshot_empty") or (r.get("cases_total") or 0) == 0:
            a["empty"].append(r["tid"])
    a["new_prompt"] = a["prompt"] - a["cached"]
    a["hit_pct"] = (100.0 * a["cached"] / a["prompt"]) if a["prompt"] else None
    return a


def pct_drop(base, treat):
    if not base:
        return None
    return 100.0 * (base - treat) / base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rep, pre = load(a.report), load(a.prereg)
    win = rep.get("window")
    rows = rep["rows"]
    by = {arm: agg([r for r in rows if r.get("arm") == arm]) for arm in ARMS}
    out = {"round": "R531", "window": win, "arms": {}, "contrasts": {}, "criteria": {},
           "notes": [], "prereg_sha_note": pre.get("predictions")}
    lines = ["== R531 KPI window=%s (臂=calls / new_prompt / hit%% / completion / cases) ==" % win]
    for arm in ARMS:
        x = by[arm]
        if not x["tasks"]:
            lines.append("%-9s : (无行)" % arm)
            continue
        out["arms"][arm] = {k: x[k] for k in ("calls", "prompt", "cached", "new_prompt", "hit_pct",
                                              "completion", "total", "unrep", "cases_pass",
                                              "cases_total", "tasks", "empty")}
        lines.append("%-9s : %5d / %8d / %6s / %8d / %d/%d %s" % (
            arm, x["calls"], x["new_prompt"],
            ("%.1f" % x["hit_pct"]) if x["hit_pct"] is not None else "-", x["completion"],
            x["cases_pass"], x["cases_total"],
            ("EMPTY=" + ",".join(x["empty"])) if x["empty"] else ""))
        if x["unrep"]:
            out["notes"].append("%s: unreported_usage=%d (计价禁当 0)" % (arm, x["unrep"]))

    c = out["contrasts"]
    for name, (b, t) in {"merge_vs_on": ("A1-on", "A2-merge"), "on_vs_off": ("A0-off", "A1-on"),
                         "merge_vs_off": ("A0-off", "A2-merge")}.items():
        if not by[b]["calls"] or not by[t]["calls"]:
            continue
        c[name] = {"calls_drop_pct": pct_drop(by[b]["calls"], by[t]["calls"]),
                   "new_prompt_drop_pct": pct_drop(by[b]["new_prompt"], by[t]["new_prompt"]),
                   "completion_drop_pct": pct_drop(by[b]["completion"], by[t]["completion"]),
                   "base_calls": by[b]["calls"], "treat_calls": by[t]["calls"],
                   "base_completion": by[b]["completion"], "treat_completion": by[t]["completion"]}
    if by[TRUTH]["tasks"] and by["A2-merge"]["tasks"]:
        c["merge_vs_truth"] = {
            "calls_ratio": (float(by["A2-merge"]["calls"]) / by[TRUTH]["calls"]) if by[TRUTH]["calls"] else None,
            "agent_calls": by["A2-merge"]["calls"], "truth_calls": by[TRUTH]["calls"],
            "agent_completion": by["A2-merge"]["completion"], "truth_completion": by[TRUTH]["completion"]}

    pred = pre.get("predictions", {})
    q_ok, q_note = True, []
    for tid in sorted(set(by["A1-on"]["tasks"]) | set(by["A2-merge"]["tasks"])):
        a1 = by["A1-on"]["tasks"].get(tid, {}).get("all_pass")
        a2 = by["A2-merge"]["tasks"].get(tid, {}).get("all_pass")
        if a1 and not a2:
            q_ok = False
            q_note.append("%s: A1 过而 A2 未过 (质量降)" % tid)
    truth_incomplete = [t for t, v in by[TRUTH]["tasks"].items() if not v["all_pass"]]
    if truth_incomplete:
        out["notes"].append("truth_arm_incomplete=%s ⇒ 本窗对照列 unreliable(truth_arm)" % truth_incomplete)
    crit = out["criteria"]
    crit["P1_merge_calls_drop_ge15"] = bool((c.get("merge_vs_on", {}).get("calls_drop_pct") or 0) >= 15)
    crit["P2_merge_completion_drop_ge15"] = bool((c.get("merge_vs_on", {}).get("completion_drop_pct") or 0) >= 15)
    crit["P3_quality_not_lower"] = q_ok
    crit["P3_notes"] = q_note
    crit["truth_arm_unreliable"] = bool(truth_incomplete)
    crit["declared_thresholds"] = {k: pred.get(k) for k in
                                   ("calls_drop_pct_min", "new_prompt_drop_pct_min", "completion_drop_pct_min")}
    rc = 0 if (crit["P1_merge_calls_drop_ge15"] and crit["P2_merge_completion_drop_ge15"]
               and q_ok) else 1
    out["rc"] = rc
    lines.append("对照 merge_vs_on : calls %+.1f%% / new_prompt %+.1f%% / completion %+.1f%%" % tuple(
        -(c.get("merge_vs_on", {}).get(k) or 0.0) for k in ("calls_drop_pct", "new_prompt_drop_pct",
                                                            "completion_drop_pct")))
    if "merge_vs_truth" in c:
        lines.append("对照 merge_vs_truth: agent_calls=%s truth_calls=%s (比值 %.2f) q:agent=%s truth=%s" % (
            c["merge_vs_truth"]["agent_calls"], c["merge_vs_truth"]["truth_calls"],
            c["merge_vs_truth"]["calls_ratio"] or 0.0,
            "".join("1" if v["all_pass"] else "0" for _, v in sorted(by["A2-merge"]["tasks"].items())),
            "".join("1" if v["all_pass"] else "0" for _, v in sorted(by[TRUTH]["tasks"].items()))))
    lines.append("判据: " + " ".join("%s=%s" % (k, v) for k, v in crit.items() if isinstance(v, bool)))
    lines.append("KPI_RC=%d  (1 ⇒ 该窗合批轴判据未过; 验收另需 exec_precondition rc=0)" % rc)
    for n in out["notes"]:
        lines.append("note: " + n)
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
