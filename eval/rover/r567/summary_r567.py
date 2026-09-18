#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R567 收口: 读数汇总 (只读) → 打印 + 落 eval/rover/r567/summary-r567.json (供报告与 kpi 行引用)。"""
import io, json, os, statistics as st

REPO = "/home/agentuser/AgentFramework"
D = "/tmp/r567"
OUT = os.path.join(REPO, "eval/rover/r567/summary-r567.json")
ARMS = ["C1", "R567B0", "R567B3"]
WINS = ["w131", "w132", "w133", "w134", "w135", "w136"]


def main():
    k = json.load(io.open(os.path.join(REPO, "eval/rover/r567/kpi-table-r567.json"), encoding="utf-8"))
    m = json.load(io.open(os.path.join(REPO, "eval/rover/r567/percase-matrix-r567.json"), encoding="utf-8"))
    v = json.load(io.open(os.path.join(REPO, "eval/rover/r567/verdict-r567.json"), encoding="utf-8"))
    pc = json.load(io.open(os.path.join(REPO, "eval/rover/r567/precond-r567.json"), encoding="utf-8"))
    fp = json.load(io.open(os.path.join(REPO, "eval/rover/r567/fingerprint-r567.json"), encoding="utf-8"))
    out = {"round": "R567", "windows": WINS, "arms": {}, "verdict": v,
           "precond": {"acceptable_scoped": pc.get("acceptable_scoped"), "blocked_n": len(pc.get("blocked") or []),
                       "windows_n": pc.get("windows_n"), "tasks_n": pc.get("tasks_n"),
                       "scope_source": pc.get("scope_source")},
           "fingerprint": {"rc": fp.get("rc"), "checks": fp.get("checks"), "selftest": fp.get("selftest")}}
    for a in ARMS:
        ws = k["arms"][a]["windows"]
        cases = [w["cases_pass"] for w in ws]
        calls = [w["calls"] for w in ws]
        np_ = [w["new_prompt"] for w in ws]
        cp = [w["completion"] for w in ws]
        va = [w.get("v_all") for w in ws]
        vi = [w.get("v_incr") for w in ws]
        steps = []
        for w in WINS:
            p = os.path.join(REPO, "eval/rover/r567/snapshots", w, a, "g1", "work", "transcript.json")
            if not os.path.isfile(p):
                p = os.path.join(D, w, {"C1": "codex", "R567B0": "agentB0", "R567B3": "agentB3"}[a], "g1", "work", "transcript.json")
            if os.path.isfile(p):
                t = json.load(io.open(p, encoding="utf-8"))
                steps.append((t.get("steps_executed"), t.get("plan_steps_total"), t.get("rc"), t.get("stage"),
                              t.get("max_exec_repair"), t.get("calls")))
            else:
                steps.append(None)
        nz = [x for x in (va + vi) if x is not None]
        out["arms"][a] = {
            "cases_windows": cases, "median": st.median(cases), "range": max(cases) - min(cases),
            "calls": sum(calls), "calls_windows": calls,
            "new_prompt": sum(np_), "new_prompt_windows": np_,
            "completion": sum(cp), "completion_windows": cp,
            "v_all_med": st.median(va), "v_incr_med": (st.median([x for x in vi if x is not None]) if any(vi) else None),
            "v_all_windows": va, "v_incr_windows": vi,
            "steps": [{"executed": s[0], "total": s[1], "rc": s[2], "stage": s[3],
                       "max_exec_repair": s[4], "calls": s[5]} if s else None for s in steps],
            "rc_windows": [s[2] if s else None for s in steps],
            "stages": sorted({str(s[3]) for s in steps if s}),
        }
    # 逐例稳定性 (判分对副本)
    for a in ARMS:
        pass_a = {w: set() for w in WINS}
        for rec in (m.get("cells") or []):
            if rec.get("arm") == a and rec.get("win") in pass_a and rec.get("verdict") in ("PASS", "pass", True):
                pass_a[rec["win"]].add(rec.get("case"))
        if all(pass_a.values()):
            always = set.intersection(*pass_a.values()); never = set()
            allc = set.union(*pass_a.values())
            never = {c for c in allc if all(c not in pass_a[w] for w in WINS)}
            out["arms"][a]["per_case"] = {"always_pass": len(always), "never_pass": len(never),
                                          "wobble": len(allc) - len(always) - len(never), "cases_seen": len(allc)}
    # 优化前后并排 (禁止相减): R566 (同轴 0 vs 1) vs R567 (同轴 0 vs 3) —— 逐格机取自各自 summary JSON, 不手抄
    try:
        s566 = json.load(io.open(os.path.join(REPO, "eval/rover/r566/summary-r566.json"), encoding="utf-8"))
        out["prev_round_R566"] = {
            a: {"windows": s566["windows"], "cases_windows": s566["arms"][a]["cases_windows"],
                "median": s566["arms"][a]["median"], "range": s566["arms"][a]["range"],
                "calls": s566["arms"][a]["calls"], "new_prompt": s566["arms"][a]["new_prompt"],
                "completion": s566["arms"][a]["completion"], "v_all_med": s566["arms"][a]["v_all_med"],
                "v_incr_med": s566["arms"][a]["v_incr_med"]}
            for a in ("C1", "R566B0", "R566B1")}
    except Exception as e:
        out["prev_round_R566"] = {"error": str(e)}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for a in ARMS:
        r = out["arms"][a]
        print("%-7s cases=%s med=%s rng=%d calls=%d new_prompt=%d completion=%d v_all=%s v_incr=%s steps=%s rc=%s"
              % (a, r["cases_windows"], r["median"], r["range"], r["calls"], r["new_prompt"], r["completion"],
                 r["v_all_med"], r["v_incr_med"],
                 [(s or {}).get("executed") for s in r["steps"]], r["rc_windows"]))
        print("        per_case=%s stages=%s" % (r.get("per_case"), r["stages"]))
    print("verdict:", json.dumps(v, ensure_ascii=False))
    print("precond:", json.dumps(out["precond"], ensure_ascii=False))
    print("R566(prev):", json.dumps(out["prev_round_R566"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
