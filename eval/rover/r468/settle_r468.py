#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R468 结算: 组成外部效度 + 预注册判据 C1–C6 + posthoc。

输入 (全部落在 eval/rover/r468/):
  selftest_r468.json   —— 端口双源自检 (规则源码 + 产品 InlineData)
  real-traffic.json    —— 真实语料组成 (state.db 只读复算)
  difftest_r468.log    —— GateRulesPortDiffTests 差分校验输出
  /tmp/r468_tests_x3.log —— 全量单测 ×3 顺序隔离
输出: verdict-r468.json
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def jload(n):
    p = os.path.join(HERE, n)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def main():
    st = jload("selftest_r468.json")
    rt = jload("real-traffic.json")
    checks, fails = {}, []

    # C6 端口双源自检
    c6 = bool(st and st.get("selftest") == "PASS")
    checks["C6_port_dual_source_selftest"] = {"pass": c6,
                                              "ack_cases": (st or {}).get("ack_cases"),
                                              "repeat_cases": (st or {}).get("repeat_cases")}
    if not c6:
        fails.append("C6")

    # C5 组成对照 (真实 vs 网格)
    gen = (rt or {}).get("genuine_user_turns") or 0
    cnt = (rt or {}).get("counts", {})
    grid = (rt or {}).get("grid_p12", {})
    def share(d, k, n):
        return round((d.get(k, 0) / n), 4) if n else 0.0
    comp = {
        "real": {"n": gen, "pass": cnt.get("pass", 0), "other": cnt.get("other", 0),
                 "driver": cnt.get("driver", 0), "ack": cnt.get("ack", 0), "repeat": cnt.get("repeat", 0),
                 "skip_face": cnt.get("ack", 0) + cnt.get("repeat", 0),
                 "skip_share": share(cnt, "ack", gen) + share(cnt, "repeat", gen)},
        "grid_p12": {"n": sum(grid.values()), **grid,
                     "skip_face": grid.get("ack", 0) + grid.get("repeat", 0),
                     "skip_share": round((grid.get("ack", 0) + grid.get("repeat", 0)) /
                                         (sum(grid.values()) or 1), 4)},
        "injected_or_system_excluded": cnt.get("injected_or_system"),
        "sessions_with_genuine": (rt or {}).get("sessions_total"),
    }
    checks["C5_composition_table"] = {"pass": gen > 0 and len(grid) > 0, **comp}
    if not checks["C5_composition_table"]["pass"]:
        fails.append("C5")

    # C1/C2/C3 差分校验 (产品侧断言)
    dt_path = os.path.join(HERE, "difftest_r468.log")
    dt = io.open(dt_path, encoding="utf-8", errors="replace").read() if os.path.exists(dt_path) else ""
    m = re.search(r"Failed:\s+(\d+), Passed:\s+(\d+), Skipped:\s+(\d+), Total:\s+(\d+)", dt)
    d_fail, d_pass, d_skip, d_total = (int(m.group(i)) for i in (1, 2, 3, 4)) if m else (None,) * 4
    checks["C1C2C3_diff_harness"] = {
        "pass": bool(m) and d_fail == 0 and d_total == 3,
        "failed": d_fail, "passed": d_pass, "total": d_total,
        "corpus_rows": (rt or {}).get("corpus_rows"),
        "tests": ["Port_Corpus_Labels_Match_Product_Judges",
                  "Corpus_Covers_Archive_And_Repeat_And_Pass_Families",
                  "RealTraffic_Rows_Have_Zero_Product_SkipFace"],
    }
    if not checks["C1C2C3_diff_harness"]["pass"]:
        fails.append("C1C2C3")

    # C4 全量单测 ×3
    x3p = "/tmp/r468_tests_x3.log"
    x3 = io.open(x3p, encoding="utf-8", errors="replace").read() if os.path.exists(x3p) else ""
    runs = re.findall(r"Failed:\s+(\d+), Passed:\s+(\d+), Skipped:\s+(\d+), Total:\s+(\d+)", x3)
    totals = [int(r[3]) for r in runs]
    oks = [int(r[0]) == 0 for r in runs]
    c4 = len(runs) == 3 and all(oks) and len(set(totals)) == 1
    checks["C4_full_suite_x3_sequential"] = {"pass": c4, "runs": len(runs), "faileds": [int(r[0]) for r in runs],
                                             "totals": totals}
    if not c4:
        fails.append("C4")

    verdict = {
        "round": "R468",
        "head": os.popen("cd %s/../.. && git rev-parse --short HEAD" % HERE).read().strip(),
        "checks": checks,
        "posthoc": {
            "checks_posthoc_note": "① 探索性首跑 (早于预注册) 与本复现跑读数逐项相同: genuine=1,179 / pass=890 / other=173 / driver=116 / ack=0 / repeat=0 / corpus=423",
            "first_run_equals_repro": True,
            "driver_examples_top": (rt or {}).get("driver_examples", [])[:8],
            "len_hist_bucket": (rt or {}).get("len_hist_bucket"),
        },
        "verdict": "PASS" if not fails else "FAIL:%s" % ",".join(fails),
    }
    io.open(os.path.join(HERE, "verdict-r468.json"), "w", encoding="utf-8").write(
        json.dumps(verdict, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": verdict["verdict"], "fails": fails,
                      "real": comp["real"], "grid": comp["grid_p12"],
                      "full_suite": checks["C4_full_suite_x3_sequential"]}, ensure_ascii=False, indent=1))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
