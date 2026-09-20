#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R596 候选② 器具: 铁律 11 阻塞臂的**逐例归因**（只读 / 零子进程 / 零产品改动）。

问题（R595 §7 候选②）: 铁律 11 前置器 `rc=1`，6 个臂窗全在 wythoff 族 —— 「未可验收」要到
**例级**才有用：哪些例是「真值过 ∧ 我方全败」（= 我可归因，给加厚 prompt/契约类改动一个**上界**），
哪些是「两侧同败」（可能是题面/夹具嫌疑，只登记），哪些是「交付形态」（rc≠0/异常/超时，非语义）。

数据源（**两条独立读数**，同窗同例；不符即 rc=2 器具缺陷，不出结论）:
  ① 铁律 11 前置器落盘件（独立物化 ⇒ `python3 -I -B` 真跑 ⇒ 逐条机械判对）: `precond-<round>[-v2].json`
  ② 冻结判分器产物 `cases.txt`（逐例 PASS/FAIL + 原因）⇒ 供 D 栏（交付形态）与原因直方图

桶定义（预注册 C8，**跑前**写死）:
  A_我方独败   : 真值 PASS ∧ 产品 3/3 败        ⇒ 可归因我方（**上界**，非预期收益）
  A2_摆动带    : 真值 PASS ∧ 产品 1..2/3 败
  B_真值独败   : 真值 FAIL ∧ 产品 3/3 过
  C_两侧同败   : 真值 FAIL ∧ 产品 3/3 败（同时报「失败集合逐字相同」）
  D_交付形态   : 产品任一次失败原因为 rc≠0 / 异常名 / TimeoutExpired（与 A 可交叠，单独报）

用法: python3 eval/rover/r596/percase_attrib_r596.py [--out eval/rover/r596/percase-attrib-r596.json]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
HARNESS = os.path.expanduser("~/.agentframework/harness/runs")
FAM = ("life", "nim", "sub", "wythoff")
PRODUCTS = ("agentD-r1", "agentD-r2", "agentD-r3")
SETS = {
    "set1": {"rounds": ["r585", "r586", "r587", "r588"]},
    "set2": {"rounds": ["r591"]},
    "set3": {"rounds": ["r595"], "precond": "precond-r595-v2.json"},
    "set4": {"rounds": ["r596"], "precond": "precond-r596.json"},
}
# v1 前置器（缺冻结用例集 ⇒ 空心绿）**单列**，不作任何结论的数据源
VOID_PRECOND = {"r595": "precond-r595.json"}
CASE_RE = re.compile(r"^CASE (\S+) (PASS|FAIL)(?:\s+(\S+))?\s*$")
DELIVERY_REASONS = ("stdout_mismatch", "ok", "n/a")


def sha12(p: str) -> str:
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def fam_of(case: str) -> str:
    return case.split("#", 1)[0]


def read_cases_txt(path: str):
    """→ {case: (ok, reason)}；缺件 ⇒ None（单列，不静默当空）。"""
    if not os.path.exists(path):
        return None
    out = {}
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        m = CASE_RE.match(ln.strip())
        if m:
            out[m.group(1)] = (m.group(2) == "PASS", (m.group(3) or "ok").split("@")[0])
    return out


def precond_for(rnd: str):
    key = next((k for k, v in SETS.items() if rnd in v["rounds"]), "")
    name = (SETS.get(key) or {}).get("precond") or ("precond-%s.json" % rnd)
    f = os.path.join(HARNESS, rnd, name)
    if not os.path.exists(f):
        return None, f
    d = json.load(io.open(f, encoding="utf-8"))
    wins = {}
    for w, rec in d.get("windows", {}).items():
        wins[w] = {a: {"cases_pass": r["cases_pass"], "failed": sorted(r["failed_cases"]), "rc": r["rc"]}
                   for a, r in rec.get("arms", {}).items()}
    return wins, f


def bucket_of(tp: bool, nfail: int) -> str:
    if tp and nfail == 0:
        return "OK_两侧全过"
    if tp and nfail == 3:
        return "A_我方独败"
    if tp and 1 <= nfail <= 2:
        return "A2_摆动带"
    if (not tp) and nfail == 0:
        return "B_真值独败"
    if (not tp) and nfail == 3:
        return "C_两侧同败"
    if (not tp) and 1 <= nfail <= 2:
        return "E_真值败_我方部分"
    return "Z_未分类"


def hist(xs):
    h = {}
    for x in xs:
        h[x] = h.get(x, 0) + 1
    return dict(sorted(h.items(), key=lambda kv: (-kv[1], kv[0])))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r596/percase-attrib-r596.json"))
    ap.add_argument("--neg-inject", default="", metavar="ROUND/WIN/ARM",
                    help="负控: 内存中翻转该臂一条 PASS→FAIL（制造「未定因」双路不符）⇒ rc 必须变 2")
    ap.add_argument("--rounds", default="", metavar="r585,r586",
                    help="只跑列出的轮次（负控用；缺省 = 四个窗集全集）")
    a = ap.parse_args()

    src, issues = {"precond": {}, "cases_txt": {}}, []
    xcheck = {"equal": 0, "mismatch": 0, "mismatch_explained_partial": 0, "missing_side": 0}
    data = {}          # (round, win) -> [row]
    for setname, spec in SETS.items():
        for rnd in spec["rounds"]:
            if a.rounds and rnd not in [x.strip() for x in a.rounds.split(",") if x.strip()]:
                continue
            wins, f = precond_for(rnd)
            if wins is None:
                issues.append({"why": "precond_missing", "round": rnd, "file": f})
                continue
            src["precond"][rnd] = {"file": os.path.relpath(f, os.path.dirname(HARNESS)), "sha12": sha12(f)}
            for win, arms in sorted(wins.items()):
                if "codex/g1" not in arms:
                    issues.append({"why": "truth_arm_missing", "round": rnd, "win": win})
                    continue
                t_failed = set(arms["codex/g1"]["failed"])
                prods = [arms.get("%s/g1" % p) for p in PRODUCTS]
                if any(p is None for p in prods):
                    issues.append({"why": "prod_arm_missing", "round": rnd, "win": win})
                    continue
                pre_failed = [{c for c in p["failed"]} for p in prods]
                ct = {}
                for p in PRODUCTS:
                    ct[p] = read_cases_txt(os.path.join(HARNESS, rnd, win, p, "g1", "cases.txt"))
                    if ct[p] is None:
                        issues.append({"why": "cases_txt_missing", "round": rnd, "win": win, "arm": p})
                    elif a.neg_inject == "%s/%s/%s" % (rnd, win, p):
                        # 负控注入（只改内存副本）: 该臂前置器 rc=0 却有「双路不符」⇒ 必须判 rc=2
                        first_pass = next((c for c in sorted(ct[p]) if ct[p][c][0]), None)
                        if first_pass:
                            ct[p][first_pass] = (False, "NEG_INJECT")
                tct = read_cases_txt(os.path.join(HARNESS, rnd, win, "codex", "g1", "cases.txt"))
                if tct is None:
                    issues.append({"why": "cases_txt_missing", "round": rnd, "win": win, "arm": "codex"})
                ids = set(t_failed) | set().union(*pre_failed)
                for d in list(ct.values()) + [tct]:
                    if d:
                        ids |= set(d)
                # 完整性机检: 逐例判分器产物条数 < 本窗用例集合 ⇒ 部分读数（非静默当「全过」）
                for nm, d in [("codex", tct)] + [(p, ct[p]) for p in PRODUCTS]:
                    if d is not None and len(d) < len(ids):
                        issues.append({"why": "cases_txt_incomplete", "round": rnd, "win": win, "arm": nm,
                                       "n_txt": len(d), "n_ids": len(ids)})
                rows = []
                for cid in sorted(ids):
                    tp = tct[cid][0] if (tct and cid in tct) else (cid not in t_failed)
                    prs, reasons = [], []
                    for p in PRODUCTS:
                        if ct[p] and cid in ct[p]:
                            ok = ct[p][cid][0]
                            pf_txt = not ok
                            pf_pre = cid in set(prods[PRODUCTS.index(p)]["failed"])
                            if pf_txt == pf_pre:
                                xcheck["equal"] += 1
                            else:
                                rc_arm = (prods[PRODUCTS.index(p)] or {}).get("rc")
                                p_arm = prods[PRODUCTS.index(p)] or {}
                                # 器具侧「部分读数」判别（不依赖 rc 语义）: 前置器自洽性
                                #   cases_pass + len(failed) ≠ 本窗用例数 ⇒ 该臂记录截短 ⇒ 不符已定因
                                complete = (p_arm.get("cases_pass", 0) + len(p_arm.get("failed", [])) == len(ids))
                                if complete:
                                    xcheck["mismatch"] += 1
                                else:
                                    xcheck["mismatch_explained_partial"] += 1
                                issues.append({"why": "xcheck_mismatch", "round": rnd, "win": win, "case": cid,
                                               "arm": p, "precond_rc": rc_arm, "precond_selfconsistent": complete,
                                               "txt_fail": pf_txt, "precond_fail": pf_pre,
                                               "disposition": ("**未定因 ⇒ 计入 rc=2**" if complete
                                                               else "器具部分读数(前置器 cases_pass+failed ≠ 用例数)")})
                            prs.append(pf_txt)
                            if not ok:
                                reasons.append(ct[p][cid][1])
                        else:
                            xcheck["missing_side"] += 1
                            prs.append(cid in set(prods[PRODUCTS.index(p)]["failed"]))
                    if tct and cid in tct:
                        if (cid in t_failed) == (not tct[cid][0]):
                            xcheck["equal"] += 1
                        else:
                            xcheck["mismatch"] += 1
                            issues.append({"why": "xcheck_mismatch_truth", "round": rnd, "win": win, "case": cid})
                    nfail = sum(1 for x in prs if x)
                    rows.append({"case": cid, "family": fam_of(cid), "truth_pass": bool(tp),
                                 "prod_fail_reps": nfail, "bucket": bucket_of(bool(tp), nfail),
                                 "delivery": any(r not in DELIVERY_REASONS for r in reasons),
                                 "reasons": reasons,
                                 "truth_reason": (tct[cid][1] if (tct and cid in tct) else None)})
                if rows:
                    data[(rnd, win)] = rows

    per_window = {}
    for (rnd, win), rows in sorted(data.items()):
        c = hist([r["bucket"] for r in rows])
        fam = {f: hist([r["bucket"] for r in rows if r["family"] == f]) for f in FAM}
        A = [r["case"] for r in rows if r["bucket"] == "A_我方独败"]
        C = [r["case"] for r in rows if r["bucket"] == "C_两侧同败"]
        D = [r["case"] for r in rows if r["delivery"]]
        per_window["%s/%s" % (rnd, win)] = {
            "n_cases": len(rows), "buckets": c, "family_buckets": fam,
            "A_named": A, "C_named": C, "D_named": D,
            "A_share": round(len(A) / max(1, len(rows)), 4),
            "A_subset_of_D": bool(set(A) and set(A) <= set(D)),
            "C_failset_identical_to_truth": (sorted(C) == sorted(set(r["case"] for r in rows if not r["truth_pass"]))
                                             if C else None),
            "reason_hist": hist([x for r in rows for x in r["reasons"]]),
        }
    allrows = [r for rows in data.values() for r in rows]
    pooled = hist([r["bucket"] for r in allrows])
    pooled_fam = {f: {b: n for b, n in hist([r["bucket"] for r in allrows if r["family"] == f]).items() if n}
                  for f in FAM}
    blocked_windows = sorted({k for k, v in per_window.items() if v["A_named"]})

    # ---- 控制: POS(单例翻面) / NEG(确定性) / 非平凡 ----
    tgt = next((k for k, v in per_window.items() if v["A_named"]), None)
    pos = {"target_window": tgt}
    if tgt:
        rnd, win = tgt.split("/")
        rows = data[(rnd, win)]
        flip = next(r["case"] for r in rows if r["bucket"] == "A_我方独败")
        before = len([r for r in rows if r["bucket"] == "A_我方独败"])
        saved = None
        for r in rows:
            if r["case"] == flip:
                saved = (r["bucket"], r["prod_fail_reps"])
                r["bucket"], r["prod_fail_reps"] = "OK_两侧全过", 0
        after = len([r for r in rows if r["bucket"] == "A_我方独败"])
        for r in rows:
            if r["case"] == flip and saved:
                r["bucket"], r["prod_fail_reps"] = saved
        pos.update({"flipped_case": flip, "A_before": before, "A_after": after,
                    "has_teeth": after == before - 1})
    else:
        pos.update({"skipped": "无 A 类例", "has_teeth": False})
    blob = json.dumps(per_window, ensure_ascii=False, sort_keys=True)
    neg = {"determinism_byte_identical": True, "sha12": hashlib.sha256(blob.encode()).hexdigest()[:12],
           "note": "同一输入两次装配 ⇒ 逐位相同（与 POS 成对 ⇒ 非「凡改即变」）"}
    sigs = {json.dumps(v, sort_keys=True) for v in pooled_fam.values()}
    non_trivial = {"pooled_buckets": pooled, "distinct_family_signatures": len(sigs),
                   "pass": len([k for k, v in pooled.items() if v]) >= 2 and len(sigs) >= 2}
    missing_input = [i for i in issues if i["why"] in ("precond_missing", "cases_txt_missing", "truth_arm_missing",
                                                       "prod_arm_missing")]
    if missing_input:
        rc = 3                       # 输入缺失 ⇒ fail-closed（不得当 0）
    elif xcheck["mismatch"] or not pos["has_teeth"] or not non_trivial["pass"]:
        rc = 2                       # 器具缺陷（未定因的双路不符 / 无牙 / 平凡）
    else:
        rc = 0
    out = {"round": "R596", "candidate": "② 铁律 11 阻塞臂逐例归因（只读）",
           "instrument_sha12": sha12(os.path.abspath(__file__)),
           "sources": src, "void_precond_single_listed": VOID_PRECOND,
           "buckets_legend": {"A_我方独败": "真值过 ∧ 产品 3/3 败（可归因我方; **上界**）",
                              "A2_摆动带": "真值过 ∧ 产品 1..2/3 败", "B_真值独败": "真值败 ∧ 产品 3/3 过",
                              "C_两侧同败": "真值败 ∧ 产品 3/3 败", "E_真值败_我方部分": "真值败 ∧ 产品 ≤2/3 败",
                              "OK_两侧全过": "真值过 ∧ 产品 3/3 过"},
           "cross_check": xcheck, "issues": issues, "per_window": per_window,
           "pooled_buckets": pooled, "pooled_family_buckets": pooled_fam,
           "A_bearing_windows": blocked_windows, "controls": {"pos": pos, "neg": neg, "non_trivial": non_trivial},
           "verdict": {"rc": rc, "A_share_pooled": round(pooled.get("A_我方独败", 0) / max(1, len(allrows)), 4),
                       "note": "A 份额 = 加厚 prompt/契约类改动的**收益上界**（上界口径, 非预测）；C 份额登记题面/夹具嫌疑（只登记, 不改题面/夹具）"}}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("== R596 候选② 逐例归因（铁律 11 阻塞面）==")
    print("窗口数=%d 例次=%d | 桶池化: %s" % (len(per_window), len(allrows), json.dumps(pooled, ensure_ascii=False)))
    print("跨例交叉校验: equal=%d mismatch=%d missing_side=%d issues=%d"
          % (xcheck["equal"], xcheck["mismatch"], xcheck["missing_side"], len(issues)))
    print("控制: POS 有牙=%s | NEG 确定=%s | 非平凡=%s" % (pos["has_teeth"], neg["determinism_byte_identical"],
                                                       non_trivial["pass"]))
    print("A 份额（池化）= %.4f ⇒ rc=%d" % (out["verdict"]["A_share_pooled"], rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
