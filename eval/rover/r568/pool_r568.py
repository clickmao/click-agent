#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R568 剂量轴并池**只读**判据器 (候选③) —— 零新臂 / 零新窗口 / 零远端 / 零产品改动。

读入 (全部只读, 只读不改):
  ① eval/rover/r568/prereg-r568.json  (机取登记表: 矩阵 sha 清单 / 臂→剂量 / 池构成)
  ② 各轮 percase-matrix-*.json        (逐例判分结果, 由 judge 对**副本**判分后落盘)

判定面 (与登记表逐条对齐; 判据文本以 prereg 的 criteria 为准, 本文件只实现):
  P1 池化合法性 —— 矩阵 sha 与登记表逐条相符 ∧ grader/cases sha 唯一 ∧ agent 臂二进制 sha 唯一;
                   不符 ⇒ rc=3 (fail-closed, 不出判决)
  P2 逐例稳定   —— 各剂量池的「混合例」(池内既有 PASS 又有 FAIL) 计数 <= 6
  P3 剂量无显著差 —— 逐例 Fisher 精确双侧 p<0.05 的例数 (0v3 / 0v1) 均 <= 2; 并落 Δ_min (分辨率下限)
  P4 失分归属   —— codex 池 × dose0 池的「同败例集」/「仅我方失败例集」分列计数 + 列名
  P0 非平凡     —— 族级通过率集合大小 >= 2 ∧ codex 与 agent 的逐例全败集合不相同

成对控制 (--selftest 一次跑全, 逐例断言预期 rc):
  NC1 sha 失配 ⇒ 3 / NC2 注入 1 例窗间翻转 ⇒ 混合例 +1 / NC3 注入 1 例剂量敏感 ⇒ 敏感例 +1 且 rc=2
  PL  真池读数  ⇒ 非平凡 (族级集合大小 >=2) 且 rc in {0,2}

rc 语义: 0 判据全绿 / 2 判据未达 / 3 输入或器具缺陷。
"""
from __future__ import annotations

import argparse
import collections
import copy
import glob
import hashlib
import io
import json
import math
import os
import sys

REPO = "/home/agentuser/AgentFramework"
PREREG = os.path.join(REPO, "eval/rover/r568/prereg-r568.json")
ALPHA = 0.05
MIXED_MAX = 6
SENS_MAX = 2


def sha256(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def J(p):
    return json.load(io.open(p, encoding="utf-8"))


def fisher2(a, b, c, d):
    """Fisher 精确双侧 p (表 [[a,b],[c,d]]; 小样本用 math.comb 精确算)。"""
    n = a + b + c + d
    r1, r2, c1 = a + b, c + d, a + c
    if r1 == 0 or r2 == 0 or c1 == 0 or c1 == n:
        return 1.0

    def pr(x):
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)

    p0 = pr(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    tot = 0.0
    for x in range(lo, hi + 1):
        px = pr(x)
        if px <= p0 * (1 + 1e-9):
            tot += px
    return min(1.0, tot)


def load(pre, inject_flip=None, inject_dose=None, nc_sha=None):
    """读全部矩阵 ⇒ 结构; 所有 sha 与登记表逐条对账。

    inject_flip: 负控 —— 把某例在**全部 dose-0 臂窗**上强制为 PASS
                 (v1 曾用「翻一个窗」的注入, 在混合例已饱和 (58/58) 时**结构性不可适用**:
                  混合例数无法再增; v2 改为「推成全过」, 断言混合例数 **-1** ∧ 全过例数 +1,
                  两个方向都可判 ⇒ 判据器对该统计量确有牙。v1 读数与原因保留在 checks_posthoc。)
    """
    reg = {m["path"]: m["sha256"] for m in pre["derived_from"]["matrices"]}
    windows = {}          # win -> {arm: rows}
    mwin = {}             # win -> round
    grader_shas, cases_shas = set(), set()
    errs = []
    for rel, want in sorted(reg.items()):
        p = os.path.join(REPO, rel)
        if not os.path.isfile(p):
            errs.append({"err": "matrix_missing", "path": rel})
            continue
        got = sha256(p)
        if nc_sha == rel:
            got = "0" * 64          # 负控: 注入 sha 失配
        if got != want:
            errs.append({"err": "matrix_sha_mismatch", "path": rel, "declared": want, "ondisk": got})
            continue
        d = J(p)
        grader_shas.add(d["grader"]["sha256"])
        cases_shas.add(d["cases"]["sha256"])
        for s in d["sets"]:
            for w in s["wins"]:
                mwin[w] = s["round"]
                windows.setdefault(w, {})
                for arm in s["arms"]:
                    rec = d["windows"].get(w, {}).get(arm)
                    if not isinstance(rec, dict) or "rows" not in rec:
                        errs.append({"err": "arm_window_missing", "win": w, "arm": arm, "path": rel})
                        continue
                    rows = rec["rows"]
                    if len(rows) != 58:
                        errs.append({"err": "case_lines", "win": w, "arm": arm, "n": len(rows)})
                    windows[w][arm] = {r["idx"]: bool(r["ok"]) for r in rows}
                    windows[w]["__family"] = {r["idx"]: r["family"] for r in rows}
    if inject_flip is not None:
        # NC2: 把某例在**全部 dose-0 臂窗**推成全过 ⇒ 混合例 -1 / 全过例 +1 (方向可判, 不饱和)
        arms0 = {a for a, dd in pre["derived_from"]["arm_dose"].items() if dd == 0}
        for w in pre["derived_from"]["dose_windows"]["0"]:
            for a in sorted(set(windows[w]) & arms0):
                windows[w][a][inject_flip] = True
    if inject_dose is not None:
        # NC3: 注入「dose0 全过 / dose3 全败」的病例
        for dose, val in (("0", True), ("3", False)):
            arms = {a for a, dd in pre["derived_from"]["arm_dose"].items() if str(dd) == dose}
            for w in pre["derived_from"]["dose_windows"][dose]:
                for a in sorted(set(windows[w]) & arms):
                    windows[w][a][inject_dose] = val
    return windows, mwin, grader_shas, cases_shas, errs


def pool_stats(windows, pre, dose):
    """某剂量池的逐例通过计数。

    只统计**该剂量自己的臂** (由登记表 arm_dose 机取); 同窗内的异剂量臂不得并入
    (自捕: 首版按「非 C1」过滤 ⇒ 把 0/1/3 三档混进同一池, 例窗数 2784 != 27窗×58例)。
    """
    arms_of_dose = {a for a, d in pre["derived_from"]["arm_dose"].items() if d == int(dose)}
    wins = pre["derived_from"]["dose_windows"][str(dose)]
    cnt = collections.Counter()
    tot = collections.Counter()
    used = []
    for w in wins:
        for a in sorted(set(windows[w]) & arms_of_dose):
            used.append((w, a))
            for idx, ok in windows[w][a].items():
                tot[idx] += 1
                cnt[idx] += 1 if ok else 0
    return wins, cnt, tot, used


def codex_stats(windows, pre):
    wins = pre["derived_from"]["all_windows"]
    cnt, tot = collections.Counter(), collections.Counter()
    for w in wins:
        if "C1" not in windows.get(w, {}):
            continue
        for idx, ok in windows[w]["C1"].items():
            tot[idx] += 1
            cnt[idx] += 1 if ok else 0
    return wins, cnt, tot


def delta_min(n0, n3, rate):
    """分辨率下限: 在给定池规模与参照率下, Fisher p<alpha 所需的最小差异 (百分点 / 例数)。"""
    k0 = int(round(rate * n0))
    best = None
    for k3 in range(0, n3 + 1):
        p = fisher2(k0, n0 - k0, k3, n3 - k3)
        if p < ALPHA:
            d = abs(k3 / n3 - k0 / n0)
            if best is None or d < best:
                best = d
    return {"n0": n0, "n3": n3, "ref_rate": round(rate, 4), "delta_min_pp": round(100 * best, 2) if best else None,
            "delta_min_cases_of_58": round(58 * best, 1) if best else None,
            "note": "差异小于该值 ⇒ 判据在数学上无法显著 (放行噪声)"}


def analyze(windows, pre):
    out = {}
    fams = {}
    for idx, f in windows[pre["derived_from"]["all_windows"][0]]["__family"].items():
        fams[idx] = f
    # 池规模与逐例计数
    pools = {}
    for dose in ("0", "1", "3"):
        wins, cnt, tot, used = pool_stats(windows, pre, dose)
        mixed = [i for i in tot if 0 < cnt[i] < tot[i]]
        q = 1 - sum(cnt.values()) / max(1, sum(tot.values()))
        n_win_eff = len(used) / 58.0 if used else 0
        e_all = 58 * (1 - q) ** n_win_eff
        sd_all = math.sqrt(max(1e-9, 58 * (1 - q) ** n_win_eff * (1 - (1 - q) ** n_win_eff)))
        obs_all = sum(1 for i in tot if cnt[i] == tot[i])
        pools[dose] = {"windows": len(wins), "arm_windows": len(used),
                       "arms_per_window": sorted({a for _, a in used}),
                       "case_windows": sum(tot.values()),
                       "per_case_obs": round(n_win_eff, 2),
                       "pass": sum(cnt.values()), "fail_rate": round(q, 4),
                       "mixed_n": len(mixed), "mixed_cases": sorted(mixed),
                       "all_pass_n": obs_all, "all_fail_n": sum(1 for i in tot if cnt[i] == 0),
                       "uniform_model": {"expect_all_pass": round(e_all, 2), "sd": round(sd_all, 2),
                                         "obs_all_pass": obs_all,
                                         "z": round((obs_all - e_all) / sd_all, 2) if sd_all else None,
                                         "verdict": ("零假设(逐例同质、失败均匀散布)不可拒" if abs(obs_all - e_all) <= 2 * sd_all
                                                     else ("过分散: 观测全过例数远低于均匀模型 ⇒ 失败几乎覆盖每一例"
                                                           if obs_all < e_all else "欠分散: 存在稳定的易错例集"))},
                       "per_case": {str(i): [cnt[i], tot[i]] for i in sorted(tot)}}
    cw, ccnt, ctot = codex_stats(windows, pre)
    codex = {"windows": len([w for w in cw if "C1" in windows.get(w, {})]),
             "case_windows": sum(ctot.values()), "pass": sum(ccnt.values()),
             "all_fail_n": sum(1 for i in ctot if ccnt[i] == 0),
             "per_case": {str(i): [ccnt[i], ctot[i]] for i in sorted(ctot)}}
    # P3 剂量敏感 (逐例 Fisher)
    sens = {}
    for pair in (("0", "3"), ("0", "1")):
        a, b = pair
        n_sens, rows = 0, []
        for i in sorted(pools[a]["per_case"]):
            k0, t0 = pools[a]["per_case"][i]
            k1, t1 = pools[b]["per_case"][i]
            p = fisher2(k0, t0 - k0, k1, t1 - k1)
            d = k1 / t1 - k0 / t0
            if p < ALPHA:
                n_sens += 1
            rows.append({"idx": int(i), "family": fams[int(i)], "p": round(p, 5), "delta_pp": round(100 * d, 2)})
        rate = pools[a]["pass"] / pools[a]["case_windows"]
        sens["%sv%s" % pair] = {"n_sensitive": n_sens, "alpha": ALPHA,
                                "top": sorted(rows, key=lambda r: r["p"])[:8],
                                "delta_min": delta_min(pools[a]["windows"], pools[b]["windows"], rate)}
    # P4 归属
    same_fail, ours_only, codex_only = [], [], []
    for i in sorted(fams):
        k0, t0 = pools["0"]["per_case"][str(i)]
        f0 = 1 - k0 / t0
        kc, tc = codex["per_case"].get(str(i), [0, 0])
        fc = 1 - kc / tc if tc else 0.0
        if f0 >= 0.5 and fc >= 0.5:
            same_fail.append(i)
        elif f0 >= 0.5 and fc < 0.1:
            ours_only.append(i)
        elif fc >= 0.5 and f0 < 0.1:
            codex_only.append(i)
    # 族级
    fam_tab = {}
    for f in sorted(set(fams.values())):
        idxs = [i for i in fams if fams[i] == f]
        row = {}
        for dose in ("0", "1", "3"):
            pk = sum(pools[dose]["per_case"][str(i)][0] for i in idxs)
            pt = sum(pools[dose]["per_case"][str(i)][1] for i in idxs)
            row["dose" + dose] = round(pk / pt, 4) if pt else None
        pk = sum(codex["per_case"][str(i)][0] for i in idxs if str(i) in codex["per_case"])
        pt = sum(codex["per_case"][str(i)][1] for i in idxs if str(i) in codex["per_case"])
        row["codex"] = round(pk / pt, 4) if pt else None
        row["n"] = len(idxs)
        fam_tab[f] = row
    out.update({"pools": pools, "codex": codex, "sensitivity": sens,
                "attribution": {"same_fail_cases": same_fail, "same_fail_n": len(same_fail),
                                "ours_only_fail_cases": ours_only, "ours_only_fail_n": len(ours_only),
                                "codex_only_fail_cases": codex_only, "codex_only_fail_n": len(codex_only)},
                "families": fam_tab})
    # 判据
    checks = {
        "P2_dose0_mixed_ok": pools["0"]["mixed_n"] <= MIXED_MAX,
        "P2_dose1_mixed_ok": pools["1"]["mixed_n"] <= MIXED_MAX,
        "P2_dose3_mixed_ok": pools["3"]["mixed_n"] <= MIXED_MAX,
        "P3_0v3_sens_ok": sens["0v3"]["n_sensitive"] <= SENS_MAX,
        "P3_0v1_sens_ok": sens["0v1"]["n_sensitive"] <= SENS_MAX,
    }
    fam_rates = sorted({v["dose0"] for v in fam_tab.values() if v["dose0"] is not None})
    distinct_case_readings = len({tuple(pools[d]["per_case"][str(i)]) for d in ("0", "1", "3") for i in fams})
    checks["P0_non_trivial"] = (len(fam_rates) >= 2) and (distinct_case_readings >= 2)
    out["checks"] = checks
    ours_fail_any = {i for i in fams if pools["0"]["per_case"][str(i)][0] < pools["0"]["per_case"][str(i)][1]}
    codex_fail_any = {i for i in fams if codex["per_case"].get(str(i), [1, 1])[0] < codex["per_case"].get(str(i), [1, 1])[1]}
    out["non_trivial"] = {"family_dose0_rate_set_size": len(fam_rates),
                          "distinct_case_readings": distinct_case_readings,
                          "fail_any_ours_n": len(ours_fail_any), "fail_any_codex_n": len(codex_fail_any),
                          "fail_any_equal": ours_fail_any == codex_fail_any}
    # ---- 补记面 (事后增补, 明示事后性): 族级池化剂量检验 ---------------------------------
    # 理由 (数据先行, 见 sensitivity[*].delta_min): 逐例面在 n0=27/n3=15 上 Δ_min ≈ 29~39 pp
    # ⇒ 逐例「未检出」不可解读为「无差异」。族级池化 (15 例 × 27 窗 = 405 vs 225 观测) 才有分辨率。
    # 预注册判据 P3 **照原样判** (不翻案); 本面只作 checks_posthoc 单列。
    fam_dose, n_fam_sens = {}, {}
    for f in fam_tab:
        idxs = [i for i in fams if fams[i] == f]
        rec = {}
        for pair in (("0", "3"), ("0", "1")):
            a, b = pair
            ka = sum(pools[a]["per_case"][str(i)][0] for i in idxs)
            ta = sum(pools[a]["per_case"][str(i)][1] for i in idxs)
            kb = sum(pools[b]["per_case"][str(i)][0] for i in idxs)
            tb = sum(pools[b]["per_case"][str(i)][1] for i in idxs)
            p = fisher2(ka, ta - ka, kb, tb - kb)
            rec["%sv%s" % pair] = {"rate_a": round(ka / ta, 4), "rate_b": round(kb / tb, 4),
                                   "delta_pp": round(100 * (kb / tb - ka / ta), 2), "p": round(p, 5),
                                   "n_a": ta, "n_b": tb}
            n_fam_sens["%sv%s" % pair] = n_fam_sens.get("%sv%s" % pair, 0) + (1 if p < ALPHA else 0)
        fam_dose[f] = rec
    out["family_dose"] = fam_dose
    # ---- 配对面 (无窗混淆): 同窗同题、臂对臂 ------------------------------------------------
    # 理由: 并池面里各剂量的**窗集合不同** (dose0 = R559∪R560∪R563∪R566∪R567, dose3 = R559∪R560∪R567)
    # ⇒ 并池差异与「轮次/窗身份」混淆, 不能直接读成剂量效应。同窗对臂比较消除该混淆 (同题面、同夹具、同窗)。
    def mcnemar(b, c):
        n = b + c
        if n == 0:
            return 1.0
        k = min(b, c)
        p = 2 * sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
        return min(1.0, p)

    arms0 = {a for a, d in pre["derived_from"]["arm_dose"].items() if d == 0}
    paired = {}
    for dose in ("1", "3"):
        armsD = {a for a, d in pre["derived_from"]["arm_dose"].items() if str(d) == dose}
        tab = {"both_pass": 0, "both_fail": 0, "dose0_pass_doseD_fail": 0, "dose0_fail_doseD_pass": 0}
        cxp, cxf, cxpD, cxfD = 0, 0, 0, 0
        wins_used, win_rows = [], []
        famStat = {}
        for w in pre["derived_from"]["dose_windows"][dose]:
            a0 = sorted(set(windows[w]) & arms0)
            aD = sorted(set(windows[w]) & armsD)
            if not a0 or not aD:
                continue
            wins_used.append(w)
            p0 = pD = n_w = 0
            for idx in windows[w][a0[0]]:
                o0, oD = windows[w][a0[0]][idx], windows[w][aD[0]][idx]
                p0 += 1 if o0 else 0
                pD += 1 if oD else 0
                n_w += 1
                if o0 and oD:
                    tab["both_pass"] += 1
                elif o0 and not oD:
                    tab["dose0_pass_doseD_fail"] += 1
                elif oD and not o0:
                    tab["dose0_fail_doseD_pass"] += 1
                else:
                    tab["both_fail"] += 1
                f = windows[w]["__family"].get(idx, windows[w]["__family"].get(str(idx), "?"))
                fs = famStat.setdefault(f, {"pairs": 0, "b_0pass_Dfail": 0, "c_0fail_Dpass": 0,
                                           "pass0": 0, "passD": 0})
                fs["pairs"] += 1
                fs["pass0"] += 1 if o0 else 0
                fs["passD"] += 1 if oD else 0
                if o0 and not oD:
                    fs["b_0pass_Dfail"] += 1
                elif oD and not o0:
                    fs["c_0fail_Dpass"] += 1
                if "C1" in windows[w]:
                    oc = windows[w]["C1"][idx]
                    if o0 and not oc:
                        cxp += 1
                    elif oc and not o0:
                        cxf += 1
                    if oD and not oc:
                        cxpD += 1
                    elif oc and not oD:
                        cxfD += 1
            win_rows.append({"win": w, "n": n_w, "pass0": p0, "passD": pD, "delta": pD - p0})
        n = sum(tab.values())
        for f, fs in famStat.items():
            fs["rate0"] = round(fs["pass0"] / fs["pairs"], 4)
            fs["rateD"] = round(fs["passD"] / fs["pairs"], 4)
            fs["delta_pp"] = round(100 * (fs["passD"] - fs["pass0"]) / fs["pairs"], 2)
            fs["mcnemar_p"] = round(mcnemar(fs["b_0pass_Dfail"], fs["c_0fail_Dpass"]), 6)
        deltas = [r["delta"] for r in win_rows]
        paired["0v%s" % dose] = {
            "windows": len(wins_used), "window_names": wins_used, "pairs": n,
            "table": tab, "per_window_delta": win_rows, "per_family": famStat,
            "delta_windows_min": min(deltas) if deltas else None,
            "delta_windows_max": max(deltas) if deltas else None,
            "delta_windows_median": sorted(deltas)[len(deltas) // 2] if deltas else None,
            "delta_windows_negative_ge3": sorted([r["win"] for r in win_rows if r["delta"] <= -3]),
            "rate0": round((tab["both_pass"] + tab["dose0_pass_doseD_fail"]) / n, 4) if n else None,
            "rateD": round((tab["both_pass"] + tab["dose0_fail_doseD_pass"]) / n, 4) if n else None,
            "delta_pp": round(100 * (tab["dose0_fail_doseD_pass"] - tab["dose0_pass_doseD_fail"]) / n, 2) if n else None,
            "mcnemar_p": round(mcnemar(tab["dose0_pass_doseD_fail"], tab["dose0_fail_doseD_pass"]), 6),
            "codex_pairs": {"arm0": {"ours_pass_codex_fail": cxp, "codex_pass_ours_fail": cxf},
                            "armD": {"ours_pass_codex_fail": cxpD, "codex_pass_ours_fail": cxfD}},
        }
    out["paired_face"] = paired
    # ---- 稳健性: 剔除「臂级崩溃窗」(规则: 该 (窗,臂) 通过数 <= 5% × n) 后重算配对面 ----------
    # 事后增补 (规则在看到数据后才表述) ⇒ 两个数**并列报**, 不作挑选:
    #   「臂级崩溃」= 该窗该臂几乎全败 (0/58 类), 属**运行级故障**而非能力读数; 混入均值会把剂量效应放大。
    collapse_cut = int(0.05 * 58)      # = 2
    rob = {}
    for dose in ("1", "3"):
        armsD = {a for a, d in pre["derived_from"]["arm_dose"].items() if str(d) == dose}
        b = c = n = 0
        rf = {}
        dropped = []
        for w in pre["derived_from"]["dose_windows"][dose]:
            a0 = sorted(set(windows[w]) & arms0)
            aD = sorted(set(windows[w]) & armsD)
            if not a0 or not aD:
                continue
            p0 = sum(1 for v in windows[w][a0[0]].values() if v)
            pD = sum(1 for v in windows[w][aD[0]].values() if v)
            if p0 <= collapse_cut or pD <= collapse_cut:
                dropped.append({"win": w, "pass0": p0, "passD": pD})
                continue
            for idx in windows[w][a0[0]]:
                o0, oD = windows[w][a0[0]][idx], windows[w][aD[0]][idx]
                b += 1 if (o0 and not oD) else 0
                c += 1 if (oD and not o0) else 0
                n += 1
                f = windows[w]["__family"].get(idx, windows[w]["__family"].get(str(idx), "?"))
                fs = rf.setdefault(f, {"pairs": 0, "pass0": 0, "passD": 0, "b": 0, "c": 0})
                fs["pairs"] += 1
                fs["pass0"] += 1 if o0 else 0
                fs["passD"] += 1 if oD else 0
                fs["b"] += 1 if (o0 and not oD) else 0
                fs["c"] += 1 if (oD and not o0) else 0
        for f, fs in rf.items():
            fs["delta_pp"] = round(100 * (fs["passD"] - fs["pass0"]) / fs["pairs"], 2)
            fs["mcnemar_p"] = round(mcnemar(fs["b"], fs["c"]), 6)
        rob["0v%s" % dose] = {"collapsed_windows_dropped": dropped, "pairs": n, "b_0pass_Dfail": b,
                              "c_0fail_Dpass": c, "delta_pp": round(100 * (c - b) / n, 2) if n else None,
                              "mcnemar_p": round(mcnemar(b, c), 6), "cut": collapse_cut,
                              "per_family": rf}
    out["robustness"] = rob
    out["posthoc"] = {
        "family_dose_test": {"families": fam_dose, "n_family_sensitive": n_fam_sens, "alpha": ALPHA,
                             "why_added": ("逐例面 Δ_min≈29~39pp (不可判) ⇒ 补一族级池化面; "
                                           "预注册 P3 判决不变")},
        "P2_threshold_calibration": {
            "why": ("P2 阈值 (混合例 <= %d) 与池规模/失败率**数学上不相容**: 在均匀失败模型下 "
                    "exactly-pass 例数 ~ 58·(1-q)^n ⇒ 混合例期望远大于 %d" % (MIXED_MAX, MIXED_MAX)),
            "dose0": {"q": pools["0"]["fail_rate"], "n": pools["0"]["per_case_obs"],
                      "expect_all_pass": pools["0"]["uniform_model"]["expect_all_pass"],
                      "expect_mixed": round(58 - pools["0"]["uniform_model"]["expect_all_pass"], 2)},
            "dose1": {"q": pools["1"]["fail_rate"], "n": pools["1"]["per_case_obs"],
                      "expect_all_pass": pools["1"]["uniform_model"]["expect_all_pass"],
                      "expect_mixed": round(58 - pools["1"]["uniform_model"]["expect_all_pass"], 2)},
            "corrected_form": ("下一轮预注册改为「观测全过例数 >= 均匀模型期望 − 2σ ∧ (过分散 ⇒ 逐窗单点读数不得作能力结论)」"
                               "或在池规模上足够大 (n 使得 (1-q)^n 可分辨) 才用「全同率」作判据"),
        },
    }
    return out


def run(pre, inject_flip=None, inject_dose=None, nc_sha=None):
    windows, mwin, gs, cs, errs = load(pre, inject_flip, inject_dose, nc_sha)
    if errs:
        return {"rc": 3, "why": "input_or_instrument_defect", "errors": errs[:10], "n_errors": len(errs)}
    if len(gs) != 1 or len(cs) != 1:
        return {"rc": 3, "why": "sha_set_not_unique", "grader_sha_set": sorted(gs), "cases_sha_set": sorted(cs)}
    shas = {v for v in pre["derived_from"]["arm_bin_sha"].values() if v}
    if len(shas) != 1:
        return {"rc": 3, "why": "arm_binary_sha_not_unique", "shas": sorted(shas)}
    res = analyze(windows, pre)
    bad = [k for k, v in res["checks"].items() if not v]
    res.update({"rc": 0 if not bad else 2, "failed_checks": bad,
                "grader_sha": sorted(gs)[0], "cases_sha": sorted(cs)[0], "binary_sha": sorted(shas)[0],
                "prereg_sha256": sha256(PREREG), "windows_total": pre["derived_from"]["all_windows_n"]})
    return res


def selftest(pre):
    base = run(pre)
    cases = []
    cases.append({"fixture": "PL_true_pool", "expected_rc": None,
                  "got_rc": base["rc"], "ok": base["rc"] in (0, 2) and base["non_trivial"]["family_dose0_rate_set_size"] >= 2})
    cases.append({"fixture": "NC0_v1_flip_inapplicable(已登记)",
                  "why": ("v1 注入「单窗翻转」在混合例饱和 (58/58) 时混合例数无法再增 ⇒ 负控结构性不可适用; "
                          "v1 读数 retained: mixed_n_base=58, mixed_n_inj=58"),
                  "ok": True})
    n1 = run(pre, nc_sha=pre["derived_from"]["matrices"][0]["path"])
    cases.append({"fixture": "NC1_matrix_sha_mismatch", "expected_rc": 3, "got_rc": n1.get("rc"),
                  "ok": n1.get("rc") == 3})
    worst = int(sorted(base["pools"]["0"]["per_case"].items(), key=lambda kv: kv[1][0])[0][0])
    n2 = run(pre, inject_flip=worst)
    ok2 = (n2.get("rc") != 3
           and n2["pools"]["0"]["mixed_n"] == base["pools"]["0"]["mixed_n"] - 1
           and n2["pools"]["0"]["all_pass_n"] == base["pools"]["0"]["all_pass_n"] + 1)
    cases.append({"fixture": "NC2_push_case_to_all_pass(idx=%d)" % worst, "expected": "mixed_n-1 ∧ all_pass_n+1",
                  "got_rc": n2.get("rc"), "mixed_n_base": base["pools"]["0"]["mixed_n"],
                  "mixed_n_inj": n2.get("pools", {}).get("0", {}).get("mixed_n"),
                  "all_pass_base": base["pools"]["0"]["all_pass_n"],
                  "all_pass_inj": n2.get("pools", {}).get("0", {}).get("all_pass_n"), "ok": bool(ok2)})
    n3 = run(pre, inject_dose=0)
    ok3 = n3.get("rc") == 2 and n3["sensitivity"]["0v3"]["n_sensitive"] >= 1
    cases.append({"fixture": "NC3_injected_dose_sensitivity(idx=0)", "expected_rc": 2, "got_rc": n3.get("rc"),
                  "sens_0v3": n3.get("sensitivity", {}).get("0v3", {}).get("n_sensitive"), "ok": bool(ok3)})
    n_ok = sum(1 for c in cases if c["ok"])
    return {"fixtures": cases, "n": len(cases), "n_ok": n_ok, "has_teeth": n_ok == len(cases)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--nc-sha-mismatch", action="store_true")
    ap.add_argument("--nc-inject-flip", type=int, default=None)
    ap.add_argument("--nc-inject-dose", type=int, default=None)
    a = ap.parse_args()
    if not os.path.isfile(PREREG):
        print("NO_PREREG ⇒ rc=3 (预注册必须先落盘)")
        return 3
    pre = J(PREREG)
    st = None
    if a.selftest:
        st = selftest(pre)
        print(json.dumps(st, ensure_ascii=False))
        if a.out:
            json.dump(st, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 0 if st["has_teeth"] else 2
    res = run(pre, inject_flip=a.nc_inject_flip, inject_dose=a.nc_inject_dose,
              nc_sha=(pre["derived_from"]["matrices"][0]["path"] if a.nc_sha_mismatch else None))
    res["instrument"] = "pool_r568.py"
    res["round"] = "R568"
    if a.out:
        json.dump(res, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ("rc", "failed_checks", "windows_total") if k in res}, ensure_ascii=False))
    for d in ("0", "1", "3"):
        if d in res.get("pools", {}):
            p = res["pools"][d]
            print("池 dose=%s 窗=%d 臂窗=%d 例窗=%d 通过=%d 失败率=%.4f 混合例=%d 全过例=%d(期望%.2f z=%s) 全败=%d" %
                  (d, p["windows"], p["arm_windows"], p["case_windows"], p["pass"], p["fail_rate"],
                   p["mixed_n"], p["all_pass_n"], p["uniform_model"]["expect_all_pass"],
                   p["uniform_model"]["z"], p["all_fail_n"]))
    if "codex" in res:
        print("池 codex 窗=%d 例窗=%d 通过=%d 全败=%d" % (res["codex"]["windows"], res["codex"]["case_windows"],
                                                       res["codex"]["pass"], res["codex"]["all_fail_n"]))
        print("族级:", json.dumps(res["families"], ensure_ascii=False))
        print("族级剂量:", json.dumps(res["family_dose"], ensure_ascii=False))
        print("归属:", json.dumps(res["attribution"], ensure_ascii=False))
        for k, v in res["sensitivity"].items():
            print("敏感 %s: n=%d Δmin=%s" % (k, v["n_sensitive"], json.dumps(v["delta_min"], ensure_ascii=False)))
        print("非平凡:", json.dumps(res["non_trivial"], ensure_ascii=False))
        print("事后补记:", json.dumps(res["posthoc"]["family_dose_test"]["n_family_sensitive"], ensure_ascii=False))
    return res["rc"]


if __name__ == "__main__":
    sys.exit(main())
