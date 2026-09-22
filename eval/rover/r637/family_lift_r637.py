#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R637 · 「最低族栏」判据（`F_lift_min`）落地 + 两侧自检（承 R636 下轮候选 ② = L-adopted-8 实施侧）。

**机制假设（来源 = lit 台账 R637 段，两条纯预印本，只作机制来源）**：聚合读数（逐窗中位 / 池化均值）
**按构造**会掩盖子群体归零。R636 实证：主判据 Q1 逐窗配对差中位 **+4（PASS）**，而同批里
`w234/agentP-r3` 的 wythoff 族 **0/15 整族归零**（Δ = −15 例）⇒ 判据须**成对**：聚合（中位）+ **最低族栏**。

**口径（先声明后算，prereg-r637.json J7）**：单位 = **例数**（非比率，避开族规模 14 vs 15 的分母差）；
`Δ = 产品族通过例数 − 真值族通过例数`；逐窗取 min over 族；阈值 **−2 例**（与主判据 §阈同尺度）。

**预注册判据在冻结面上被证伪（本轮如实修正，不翻案、不放宽阈值）**：字面形式「取**重复跑次中位**的族读数」
在 R636 面上**无牙**（`w234`：P wythoff = [15,15,0] ⇒ 中位 15 ⇒ Δ = 0 ⇒ 判过，而同一窗有一跑次 0/15）
⇒ 该形式是**空心闸**。修正形态 = **取最差跑次**（`min over reps`，同一阈值 −2 例**不放宽**）；
两种读数**并列报告**，首版（中位式）读数原样入档。这是「判据被否证 ⇒ 修判据 + 单测覆盖被否证分支」的落地。
"""
from __future__ import annotations
import argparse
import io
import json
import os
import statistics
import sys

REPO = "/home/agentuser/AgentFramework"
FAMILIES = ["life", "sub", "nim", "wythoff"]
THRESH = -2          # 例数；声明先于算（prereg-r637.json J7，两形态共用、未放宽）


def family_lift_core(windows, thresh=THRESH):
    """windows = {win: {"P": [run...], "C1": [run...]}}；run = {"families": {fam: {"pass": n, "n": m}}}
    → verdict dict（单一口径实现；未来 judge 直接 import 本函数，不重写第二份）。

    返回同时给两种形态（并列，禁互相解释）：
      · `median_form`（预注册字面式）—— 族读数的**重复跑次中位**；本轮证明其在冻结面上无牙。
      · `worst_form`（本轮修正式）—— 族读数的**最差跑次**；判决以此式为准。
    """
    out = {"threshold_cases": thresh, "per_window": [], "valid_windows": 0, "min_lift": None,
           "min_lift_median_form": None, "pass": None, "pass_median_form": None}
    worst, med = [], []
    for win in sorted(windows):
        w = windows[win]
        if not w.get("C1"):
            out["per_window"].append({"win": win, "valid": False, "reason": "truth_arm_absent"})
            continue
        c1 = w["C1"][0]["families"]
        rows, worst_delta = {}, None
        for fam in FAMILIES:
            p_vals = [r["families"][fam]["pass"] for r in w["P"] if fam in r["families"]]
            if fam not in c1 or not p_vals:
                continue
            p_med, p_min = statistics.median(p_vals), min(p_vals)
            rows[fam] = {"P_median_cases": p_med, "P_min_cases": p_min, "P_reps": p_vals,
                         "C1_cases": c1[fam]["pass"], "n": c1[fam]["n"],
                         "delta_cases_median_form": p_med - c1[fam]["pass"],
                         "delta_cases_worst_form": p_min - c1[fam]["pass"]}
            wd = rows[fam]["delta_cases_worst_form"]
            worst_delta = wd if worst_delta is None else min(worst_delta, wd)
        if not rows:
            out["per_window"].append({"win": win, "valid": False, "reason": "no_family_rows"})
            continue
        fam_med = min(r["delta_cases_median_form"] for r in rows.values())
        out["valid_windows"] += 1
        worst.append(worst_delta)
        med.append(fam_med)
        out["per_window"].append({
            "win": win, "valid": True, "families": rows,
            "F_lift_min_worst": worst_delta, "F_lift_min_median": fam_med,
            "worst_family_worst_form": min(rows, key=lambda f: rows[f]["delta_cases_worst_form"]),
            "family_pass_worst": worst_delta >= thresh, "family_pass_median": fam_med >= thresh})
    if worst:
        out["min_lift"] = min(worst)
        out["pass"] = all(x >= thresh for x in worst) and out["valid_windows"] >= 1
        out["min_lift_median_form"] = min(med)
        out["pass_median_form"] = all(x >= thresh for x in med)
    return out


# ------------------------------------------------------------------ 两侧自检
def selftest():
    N = {"life": 14, "sub": 14, "nim": 15, "wythoff": 15}
    full = dict(N)

    def run(fam_pass):
        return {"families": {f: {"pass": fam_pass[f], "n": N[f]} for f in FAMILIES}}

    cases, res = {}, {}
    # S1 POS：全族/全跑次相等
    w1 = {"wA": {"P": [run(full), run(full), run(full)], "C1": [run(full)]}}
    # S2 NEG（R636 实证形态）：单跑次整族归零 ⇒ 中位式无牙 ∧ 最差式必红
    blocked = dict(full, wythoff=0)
    w2 = {"wA": {"P": [run(full), run(full), run(blocked)], "C1": [run(full)]}}
    # S3 旁路（退化检查）：同数据只用聚合口径 ⇒ 判过（证明判决来自本判据）
    med_P_cases = statistics.median([58, 58, 43])
    agg_pass = (med_P_cases - 58) >= -2
    # S4 NEG：全族/全跑次一致落后 6 例
    worse = {f: max(full[f] - 6, 0) for f in FAMILIES}
    w4 = {"wA": {"P": [run(worse)], "C1": [run(full)]}}
    # S5 POS：单族落后 1 例 ⇒ 未跨阈 ⇒ 过（证明阈值非恒红）
    slight = dict(full, wythoff=14)
    w5 = {"wA": {"P": [run(slight), run(full)], "C1": [run(full)]}}

    specs = [("S1_pos_all_equal", w1, True, "全族/全跑次相等 ⇒ 过"),
             ("S2_neg_single_rep_family_block", w2, False, "单跑次整族归零 ⇒ 最差式必红（中位式无牙，并列报告）"),
             ("S3_bypass_aggregate_only", "BYPASS", bool(agg_pass), "同数据旁路本判据 ⇒ 聚合口径判过（判决来自判据，非数据）"),
             ("S4_neg_uniform_shortfall", w4, False, "全族一致落后 6 例 ⇒ 必红"),
             ("S5_pos_within_threshold", w5, True, "单族落后 1 例（未跨阈 −2）⇒ 过（阈值非恒红）")]
    ok = True
    for name, data, expect, rule in specs:
        if data == "BYPASS":
            got = bool(agg_pass)
        else:
            got = bool(family_lift_core(data)["pass"])
        good = (got == expect)
        res[name] = {"expect_pass": expect, "got_pass": got, "ok": good, "rule": rule}
        ok = ok and good
    d2 = family_lift_core(w2)
    res["S2_detail"] = {"F_lift_min_worst": d2["min_lift"], "F_lift_min_median": d2["min_lift_median_form"],
                        "aggregate_median_D_cases": med_P_cases - 58}
    res["pass"] = ok
    res["rc_hint"] = 0 if ok else 2
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--from-attrib", default=os.path.join(REPO, "eval/rover/r637/out/percase-r637.json"))
    ap.add_argument("--frozen-r636", default=os.path.join(REPO, "eval/rover/r636/verdict-r636.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r637/family-lift-r637.json"))
    args = ap.parse_args()

    if args.selftest:
        st = selftest()
        io.open(args.out.replace(".json", "-selftest.json"), "w", encoding="utf-8").write(
            json.dumps({"round": "R637", "kind": "family_lift_selftest", **st}, ensure_ascii=False, indent=1))
        for k, v in st.items():
            if isinstance(v, dict) and "ok" in v:
                print("  %-34s expect=%-5s got=%-5s %s" % (k, v["expect_pass"], v["got_pass"],
                                                           "OK" if v["ok"] else "FAIL"))
        print("S2 detail:", json.dumps(st["S2_detail"], ensure_ascii=False))
        print("SELFTEST", "PASS" if st["pass"] else "FAIL")
        return st["rc_hint"]

    if not os.path.isfile(args.from_attrib):
        print("missing input:", args.from_attrib, file=sys.stderr)
        return 3
    per = json.load(io.open(args.from_attrib, encoding="utf-8"))
    windows = {}
    for r in per["runs"]:
        win = "%s:%s" % (r["round"], r["win"])
        side = "C1" if r["side"] == "codex" else "P"
        windows.setdefault(win, {"P": [], "C1": []})[side].append(r)
    core = family_lift_core(windows)

    xcheck = {"checked": 0, "mismatch": [], "note": "R636 冻结判决件的族读数 vs 本轮独立重放（r636 面）"}
    if os.path.isfile(args.frozen_r636):
        fz = json.load(io.open(args.frozen_r636, encoding="utf-8")).get("B_family_block", {}).get("by_run", [])
        mine = {(r["round"], r["win"], r["arm"]): r for r in per["runs"]}
        for b in fz:
            k = ("r636", b["win"], b["sub"])
            m = mine.get(k)
            if not m:
                continue
            xcheck["checked"] += 1
            for fam, s in (b.get("families") or {}).items():
                if "/" in s and m["families"][fam]["pass"] != int(s.split("/")[0]):
                    xcheck["mismatch"].append({"key": list(k), "fam": fam, "frozen": s,
                                               "mine": m["families"][fam]["pass"]})
    xcheck["pass"] = xcheck["checked"] > 0 and not xcheck["mismatch"]

    res = {"round": "R637", "kind": "family_lift_criterion",
           "criterion": "F_lift_min（最低族栏）：逐窗 min over 族 of Δ（例数）；判决式 = 最差跑次式",
           "threshold_cases": THRESH, "declared_before_compute": True,
           "median_form_falsified_on_frozen": {
               "why": "字面式（重复跑次中位）在冻结面无牙：单跑次整族归零被中位吃掉",
               "evidence_window": "r636:w234", "median_form_value": None, "worst_form_value": None},
           "core": core, "cross_check_r636_frozen": xcheck,
           "verdict": ("PASS" if core["pass"] else "FAIL") if core["pass"] is not None else "NO_RESOLUTION",
           "verdict_median_form": ("PASS" if core["pass_median_form"] else "FAIL") if core["pass_median_form"] is not None else "NO_RESOLUTION"}
    for w in core["per_window"]:
        if w.get("win") == "r636:w234" and w.get("valid"):
            res["median_form_falsified_on_frozen"]["median_form_value"] = w["F_lift_min_median"]
            res["median_form_falsified_on_frozen"]["worst_form_value"] = w["F_lift_min_worst"]
    io.open(args.out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print("F_lift_min（阈值 %d 例）判决式=最差跑次: %s · valid_windows=%d · min_lift=%s"
          % (THRESH, res["verdict"], core["valid_windows"], core["min_lift"]))
    print("  并列：中位式 %s（min_lift_median=%s）—— 本轮已证其在冻结面无牙"
          % (res["verdict_median_form"], core["min_lift_median_form"]))
    for w in core["per_window"]:
        if not w.get("valid"):
            print("  %-12s invalid(%s)" % (w["win"], w["reason"]))
            continue
        print("  %-12s worst=%4s med=%4s worst_fam=%-8s Δ=%s"
              % (w["win"], w["F_lift_min_worst"], w["F_lift_min_median"], w["worst_family_worst_form"],
                 json.dumps({f: v["delta_cases_worst_form"] for f, v in w["families"].items()}, ensure_ascii=False)))
    print("R636 冻结族读数交叉校验: checked=%d mismatch=%d pass=%s"
          % (xcheck["checked"], len(xcheck["mismatch"]), xcheck["pass"]))
    return 0 if (core["pass"] is not None and not xcheck["mismatch"]) else 2


if __name__ == "__main__":
    sys.exit(main())
