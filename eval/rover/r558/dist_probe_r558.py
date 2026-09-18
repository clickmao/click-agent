#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R558 候选① 离线量测 (零远端调用): 「公开用例自验被行使」的分布。

只读扫 /tmp/r555, /tmp/r556, /tmp/r557[, /tmp/r558] 的 agent 臂 transcript.json + cases.txt,
产出一张联合分布: (public_probe_ran, public_probe_failed, exec_repairs, rc, stage, cases_pass)。

用途 (按用户/主线纪律「先量分布, 禁预言式修」):
  · 证明 public probe **看见** 失败 (probe_failed>0 的窗比例);
  · 证明执行面修复预算**被行使 / 被用尽** (exec_repairs == max_exec_repair 的窗比例);
  · 给出「被行使后仍不达标」的窗比例 ⇒ 判定剂量 1→2 是否值得测 / 是否是可判轴。
"""
from __future__ import annotations
import glob, io, json, os, sys

_argv = list(sys.argv[1:])
OUT = None
if "--out" in _argv:
    i = _argv.index("--out")
    OUT = _argv[i + 1]
    del _argv[i:i + 2]
ROOTS = _argv or ["/tmp/r555", "/tmp/r556", "/tmp/r557", "/tmp/r558"]

# 器具修复 (R558 收口, 自捕缺陷): 首版把输出路径**写死**为 <本目录>/dist-probe-r558.json
# ⇒ 「起臂前先量分布」的 pre-arm 读数被 post 重跑**静默覆盖**。修法 = 输出路径参数化 (`--out`),
# 默认仍写 pre-arm 名以保持既有调用可用; 每次跑都在 out["roots"] 里留输入清单 (可反查是哪一版)。


def parse_cases(path):
    if not os.path.isfile(path):
        return None
    tot = pas = 0
    for x in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        if x.startswith("CASE"):
            tot += 1
            if "PASS" in x:
                pas += 1
    return {"total": tot, "pass": pas}


def main():
    rows = []
    for root in ROOTS:
        for tp in sorted(glob.glob(os.path.join(root, "w*", "agent*", "g1", "transcript.json"))):
            try:
                t = json.load(io.open(tp, encoding="utf-8"))
            except Exception as e:
                rows.append({"file": tp, "err": str(e)[:60]})
                continue
            cp = parse_cases(os.path.join(os.path.dirname(tp), "cases.txt"))
            rows.append({
                "round": os.path.basename(root), "tag": t.get("tag"),
                "arm_dir": os.path.basename(os.path.dirname(os.path.dirname(tp))),
                "prefix_chars": t.get("prefix_chars"),
                "max_exec_repair": t.get("max_exec_repair"), "max_repair": t.get("max_repair"),
                "probe_ran": t.get("public_probe_ran"), "probe_total": t.get("public_probe_total"),
                "probe_failed": t.get("public_probe_failed"), "probe_reason": t.get("public_probe_reason"),
                "exec_repairs": t.get("exec_repairs"), "repair_rounds": t.get("repair_rounds"),
                "self_test_unmet": t.get("self_test_unmet"), "correctness_asserted": t.get("correctness_asserted"),
                "calls": t.get("calls"), "rc": t.get("rc"), "stage": t.get("stage"),
                "cases_pass": (cp or {}).get("pass"), "cases_total": (cp or {}).get("total"),
            })

    ok = [r for r in rows if "err" not in r and r.get("cases_total") == 58]
    def pct(n, d):
        return "%.0f%% (%d/%d)" % (100.0 * n / d, n, d) if d else "n/a"
    probed = [r for r in ok if r.get("probe_ran") == 1]
    pfail = [r for r in probed if (r.get("probe_failed") or 0) > 0]
    exercised = [r for r in ok if (r.get("exec_repairs") or 0) > 0]
    exhausted = [r for r in ok if r.get("max_exec_repair") and (r.get("exec_repairs") or 0) >= r["max_exec_repair"]]
    per = {}
    for r in ok:
        k = "%s/%s" % (r["round"], r["arm_dir"])
        e = per.setdefault(k, {"n": 0, "sum": 0, "all58": 0, "probe_failed_win": 0, "exec_used": 0,
                               "exec_exhausted": 0, "stages": {}})
        e["n"] += 1
        e["sum"] += r["cases_pass"] or 0
        e["all58"] += 1 if (r["cases_pass"] == 58) else 0
        e["probe_failed_win"] += 1 if (r.get("probe_failed") or 0) > 0 else 0
        e["exec_used"] += 1 if (r.get("exec_repairs") or 0) > 0 else 0
        e["exec_exhausted"] += 1 if (r.get("max_exec_repair") and (r.get("exec_repairs") or 0) >= r["max_exec_repair"]) else 0
        e["stages"][str(r.get("stage"))] = e["stages"].get(str(r.get("stage")), 0) + 1
    out = {
        "note": "零远端调用; 只读 transcript.json + cases.txt; 有效行 = cases_total==58 的 agent 臂运行",
        "roots": ROOTS,
        "n_runs_total": len(rows), "n_runs_valid": len(ok),
        "prefix_chars_set": sorted({r.get("prefix_chars") for r in ok}),
        "probe_ran": pct(len(probed), len(ok)),
        "probe_saw_failure": pct(len(pfail), len(probed)),
        "exec_repair_exercised": pct(len(exercised), len(ok)),
        "exec_repair_budget_exhausted": pct(len(exhausted), len(ok)),
        "exercised_but_not_all58": pct(len([r for r in exercised if r["cases_pass"] != 58]), len(exercised)),
        "probe_failed_but_all58": pct(len([r for r in pfail if r["cases_pass"] == 58]), len(pfail)),
        "per_arm": per,
        "rows": ok,
    }
    dest = OUT or os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist-probe-r558.json")
    json.dump(out, io.open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("runs_total=%d valid=%d" % (len(rows), len(ok)))
    print("prefix_chars_set=%s" % out["prefix_chars_set"])
    print("probe_ran=%s | probe_saw_failure=%s | probe_failed_but_all58=%s" % (
        out["probe_ran"], out["probe_saw_failure"], out["probe_failed_but_all58"]))
    print("exec_repair_exercised=%s | budget_exhausted=%s | exercised_but_not_all58=%s" % (
        out["exec_repair_exercised"], out["exec_repair_budget_exhausted"], out["exercised_but_not_all58"]))
    print("--- per arm-dir ---")
    for k in sorted(per):
        v = per[k]
        print("  %-28s n=%d mean=%5.1f all58=%d probe_failed=%d exec_used=%d exhausted=%d stages=%s" % (
            k, v["n"], v["sum"] / v["n"], v["all58"], v["probe_failed_win"], v["exec_used"],
            v["exec_exhausted"], v["stages"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
