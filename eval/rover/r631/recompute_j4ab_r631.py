#!/usr/bin/env python3
"""R631 · 预注册判据 J4a/J4b 的**冻产后处理复算**（缺派生件时重跑后处理，不重测）。

背景（本轮自捕器件缺陷，如实披露）:
  `judge_r631.py` 的判据族 = **旧草稿残留**（输出 `kind` 写「第五刀 = 等价面分辨率取证 reps 3→6 / 窗集 w217..w219」，
  判据键为 J6/`v3`），与本轮 `prereg-r631.json` 声明的判据族（J0/J1/J4a/J4b）**不同源** ⇒
  该件判决**不予采用**（保留在盘、不翻案、不当本轮判决）。
  本件按 RF0005 §1「后处理必须能从原始落盘数据幂等重算」+ §3「缺派生件只重跑后处理」从**冻结快照产物**
  `evidence/windows/<win>/report.json` 复算预注册判据；零重测、零产品改动、零阈值改动。

判据逐字取自 prereg-r631.json（sha256 见输出）:
  J4a（capability_secondary）: 逐窗配对 Δ := T − C（此处取**整题全对率**与**用例通过中位**两口径并列）；
       复现判据 = Δ 中位 > 0 ∧ 逐窗符号非负占比 ≥ 1/2（n=2 ⇒ 欠功率，只作趋势不作能力结论）
  J4b（capability）        : 逐窗 D := 产品(治疗臂) − codex 真值（用例通过数）；
       判据 = D 中位 ≥ −2 ∧ 无窗 ≤ −15；真值自败窗按 R4 单列 unreliable（不进配对）
用法: python3 eval/rover/r631/recompute_j4ab_r631.py [--json <out>]
"""
import hashlib
import io
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PD = os.path.join(REPO, "eval/rover/r631")
PREREG = os.path.join(PD, "prereg-r631.json")
WROOT = os.path.join(PD, "evidence/windows")


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def load_rows(win):
    p = os.path.join(WROOT, win, "report.json")
    d = json.load(io.open(p, encoding="utf-8-sig"))
    return d["rows"], sha(p)


def main():
    pre = json.load(io.open(PREREG, encoding="utf-8"))
    wins = sorted(pre["windows"]["set"])
    per, unreli, evidence = {}, [], {}
    for w in wins:
        rows, sh = load_rows(w)
        evidence["%s/report.json" % w] = sh
        arms = {}
        for r in rows:
            a = r["arm"]
            arms.setdefault(a, []).append(r)
        def med(a, key):
            return statistics.median([x[key] for x in arms[a]])
        truth_all = all(x["all_pass"] for x in arms["C1"]) if "C1" in arms else False
        truth_cases = med("C1", "cases_pass") if "C1" in arms else None
        rec = {
            "T_allpass_rate": sum(1 for x in arms["T"] if x["all_pass"]) / len(arms["T"]),
            "C_allpass_rate": sum(1 for x in arms["C"] if x["all_pass"]) / len(arms["C"]),
            "T_cases_median": med("T", "cases_pass"),
            "C_cases_median": med("C", "cases_pass"),
            "C1_cases_median": truth_cases,
            "C1_all_pass": truth_all,
            "reps": {"T": len(arms["T"]), "C": len(arms["C"]), "C1": len(arms.get("C1", []))},
        }
        rec["D_T_minus_C_allpass_rate"] = round(rec["T_allpass_rate"] - rec["C_allpass_rate"], 4)
        rec["D_T_minus_C_cases_median"] = rec["T_cases_median"] - rec["C_cases_median"]
        rec["D_product_minus_truth_cases_median"] = (
            rec["T_cases_median"] - truth_cases if truth_cases is not None else None)
        if not truth_all:
            unreli.append({"window": w, "truth_cases": truth_cases,
                           "note": "外部真值未全对 ⇒ 该窗对照列标 unreliable（RF0005 §3 R4），J4b 该窗单列不并入"})
        per[w] = rec

    pa = [per[w]["D_T_minus_C_allpass_rate"] for w in wins]
    pc = [per[w]["D_T_minus_C_cases_median"] for w in wins]
    # J4b 只用真值可靠的窗（truth_all）——J4a 不受真值影响（两侧同窗 T vs C）
    pdt = [per[w]["D_product_minus_truth_cases_median"] for w in wins if per[w]["C1_all_pass"]]
    j4a = {"D_allpass_rate_by_window": dict(zip(wins, pa)), "D_cases_median_by_window": dict(zip(wins, pc)),
           "median": statistics.median(pa), "nonneg_frac": sum(1 for x in pa if x >= 0) / len(pa),
           "pass": (statistics.median(pa) > 0 and sum(1 for x in pa if x >= 0) / len(pa) >= 0.5),
           "power_note": "n=%d 窗 ⇒ 欠功率, 只作趋势不作能力结论" % len(wins)}
    j4b = {"D_product_minus_truth_cases_median_by_window": {w: per[w]["D_product_minus_truth_cases_median"] for w in wins},
           "windows_used": [w for w in wins if per[w]["C1_all_pass"]], "reliable_windows_from": sorted(evidence),
           "median": (statistics.median(pdt) if pdt else None),
           "pass": bool(pdt) and statistics.median(pdt) >= -2 and min(pdt) > -15}
    out = {"round": "R631", "kind": "J4a/J4b 冻产后处理复算（judge_r631.py 判据族与预注册不同源 ⇒ 不采用该件判决）",
           "criterion_source": {"prereg": "eval/rover/r631/prereg-r631.json", "prereg_sha256": sha(PREREG),
                                "criteria_keys": ["J4a_capability_replication", "J4b_capability_vs_truth"]},
           "evidence_sha256": evidence, "per_window": per, "unreliable_windows": unreli,
           "J4a": j4a, "J4b": j4b}
    out["verdict"] = {"J4a_replicated": j4a["pass"], "J4b_pass": j4b["pass"],
                      "headline": ("效应未跨窗复现（Δ 中位 %s）" % j4a["median"]) if not j4a["pass"] else "效应复现"}
    dst = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else os.path.join(PD, "verdict-j4ab-r631.json")
    io.open(dst, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"dst": dst, "J4a": j4a, "J4b": j4b, "verdict": out["verdict"],
                      "unreliable": [u["window"] for u in unreli]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
