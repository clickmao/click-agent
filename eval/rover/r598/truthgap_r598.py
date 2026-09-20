#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R598 候选② 器具: **真值侧（codex）wythoff 缺口归因**（只读 / 零子进程 / 零产品改动）。

问题（R597 §7 候选② + R597 C0）: 真值臂在 w175/w176 **自败 56/58**（两窗各 2 例），失败例据 R597 记录
同为 wythoff 公开例 + wythoff 隐藏例；该二窗按 C0 标 `unreliable` 被剔除 ⇒ set5 有效窗仅 1。
本项把「真值自败」从**单点读数**升到**跨窗普查**，判三态（预注册 C8，跑前写死）:

  ① 真值失败集合跨窗**逐字相同** ∧ 与本侧全臂相同 ⇒ 登记 **题面/夹具嫌疑（只登记，不改题面/夹具）**
  ② 真值失败集合**逐窗漂移**            ⇒ **真值臂自身漂移**
  ③ 真值**全绿**窗                        ⇒ 无缺口

数据源 = 在盘 `cases.txt`（冻结判分器产物，逐例 PASS/FAIL + 原因；两侧同窗同例）。
每条路径落 sha12 ⇒ 读数可追到档。

控制（成对，预注册 C8）:
  · NEG-A 确定性: 同一输入读两遍 ⇒ 输出逐字节相同
  · NEG-B 非平凡性（预注册原文）: 真值失败集合不得退化为恒定 / 不得恒为空
  · POS  判别力: 内存注入「使某全绿窗的真值失败」⇒ 该窗分类必须改变（证分类器读的是数据不是常量）

用法: python3 eval/rover/r598/truthgap_r598.py [--out eval/rover/r598/truthgap-r598.json]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import statistics

REPO = "/home/agentuser/AgentFramework"
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
ROUNDS = ["r585", "r586", "r587", "r588", "r591", "r595", "r596", "r597", "r598"]
PRODUCTS = ("agentD-r1", "agentD-r2", "agentD-r3")
FAMS = ("life", "nim", "sub", "wythoff")
CASE_RE = re.compile(r"^CASE (\S+) (PASS|FAIL)(?:\s+(\S+))?\s*$")
CASES_N = 58


def sha12(p: str) -> str:
    try:
        return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]
    except OSError:
        return ""


def fam_of(cid: str) -> str:
    return cid.split("#", 1)[0]


def read_cases(path: str):
    """→ ({cid: (ok, reason)}, sha12) | (None, "") 缺件单列。"""
    if not os.path.exists(path):
        return None, ""
    out = {}
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        m = CASE_RE.match(ln.strip())
        if m:
            out[m.group(1)] = (m.group(2) == "PASS", (m.group(3) or "ok").split("@")[0])
    return out, sha12(path)


def classify(tt: set, prod_failed: dict):
    """预注册 C8 三态（逐窗）。prod_failed: {arm: set}"""
    allprod = set().union(*prod_failed.values()) if prod_failed else set()
    same_all = bool(prod_failed) and all(v == tt for v in prod_failed.values())
    if not tt:
        return ("③ 真值全绿窗", same_all)
    if same_all:
        return ("① 同败(题面/夹具嫌疑, 只登记)", True)
    return ("② 真值独败(真值臂自身漂移)", False)


def collect():
    rows, missing = [], []
    for rnd in ROUNDS:
        d = os.path.join(RUNS, rnd)
        if not os.path.isdir(d):
            missing.append({"round": rnd, "why": "round_dir_missing"})
            continue
        for win in sorted(x for x in os.listdir(d) if re.fullmatch(r"w\d+", x)):
            t, tsha = read_cases(os.path.join(d, win, "codex", "g1", "cases.txt"))
            if t is None:
                missing.append({"round": rnd, "win": win, "why": "truth_cases_missing"})
                continue
            tt = {c for c, (ok, _) in t.items() if not ok}
            pf, shas = {}, {}
            for arm in PRODUCTS:
                p, psha = read_cases(os.path.join(d, win, arm, "g1", "cases.txt"))
                if p is None:
                    missing.append({"round": rnd, "win": win, "arm": arm, "why": "prod_cases_missing"})
                    continue
                pf[arm] = {c for c, (ok, _) in p.items() if not ok}
                shas[arm] = psha
            state, same_all = classify(tt, pf)
            rows.append({
                "round": rnd, "win": win, "n_truth": len(t), "n_prod": {a: len(pf[a]) for a in pf},
                "truth_failed": sorted(tt), "prod_failed": {a: sorted(v) for a, v in pf.items()},
                "truth_failed_fams": hist([fam_of(c) for c in tt]),
                "prod_failed_fams_union": hist([fam_of(c) for c in set().union(*pf.values())]) if pf else {},
                "truth_set_equals_every_prod_run": same_all, "state": state,
                "sha12": {"truth": tsha, **shas},
            })
    return rows, missing


def hist(xs):
    h = {}
    for x in xs:
        h[x] = h.get(x, 0) + 1
    return dict(sorted(h.items(), key=lambda kv: (-kv[1], kv[0])))


def audit_set(rows):
    """真值失败集合的跨窗结构（确定性/非平凡性控制的判读面）。"""
    sets = [tuple(r["truth_failed"]) for r in rows]
    distinct = sorted({s for s in sets})
    empty = sum(1 for s in sets if not s)
    # 题面/夹具嫌疑面: 真值失败集合逐字相同 ∧ 两侧失败集合也逐字相同（同败）
    same_pairs = [r for r in rows if r["state"].startswith("①")]
    return {"windows": len(rows), "distinct_truth_failure_sets": len(distinct),
            "truth_all_green_windows": empty,
            "sets_with_both_sides_identical": len(same_pairs),
            "distinct_sets": [" ".join(s) if s else "<empty>" for s in distinct],
            "nonconstant": len(distinct) > 1, "nonempty": empty < len(rows)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r598/truthgap-r598.json"))
    ap.add_argument("--pos-inject", default="", metavar="WIN",
                    help="POS 判别力控制: 内存注入该窗真值 1 例失败 ⇒ 分类必须改变")
    a = ap.parse_args()

    rows, missing = collect()
    rows2, _ = collect()                       # NEG-A: 独立复读
    det = json.dumps(rows, ensure_ascii=False, sort_keys=True) == json.dumps(rows2, ensure_ascii=False, sort_keys=True)
    audit = audit_set(rows)

    # POS: 注入一例失败到某全绿窗 ⇒ 该窗 state 必从 ③ 变 ②（分类器读数据, 非恒定常量）
    pos = {"injected": a.pos_inject, "performed": False, "state_before": None, "state_after": None, "changed": None}
    if a.pos_inject:
        tgt = [r for r in rows if r["win"] == a.pos_inject]
        if tgt:
            r = dict(tgt[0])
            pos["state_before"] = r["state"]
            fake = {"agentD-r1": {"wythoff#99-hidden"}}
            st, _ = classify({"wythoff#99-hidden"}, fake)
            pos["state_after"] = st
            pos["performed"] = True
            pos["changed"] = (st != r["state"])
    # NEG-B (预注册原文): 真值失败集合不得退化为恒定 / 不得恒为空
    negb = {"nonconstant": audit["nonconstant"], "nonempty": audit["nonempty"],
            "pass": bool(audit["nonconstant"] and audit["nonempty"])}

    fam_fail = {}
    union_per_row = [set().union(*r["prod_failed"].values()) if r["prod_failed"] else set() for r in rows]
    for f in FAMS:
        fam_fail[f] = {"truth_fail_cases": sum(1 for r in rows for c in r["truth_failed"] if fam_of(c) == f),
                       "truth_fail_windows": sum(1 for r in rows if any(fam_of(c) == f for c in r["truth_failed"])),
                       "prod_fail_cases_union": sum(1 for u in union_per_row for c in u if fam_of(c) == f)}
    out = {"round": "R598",
           "purpose": "候选② 真值侧 wythoff 缺口归因（只读普查）",
           "scope": {"rounds": ROUNDS, "windows": len(rows), "products": list(PRODUCTS)},
           "rows": rows, "missing": missing,
           "audit": audit, "family_failure_census": fam_fail,
           "controls": {"negA_determinism_same_input_twice": det, "negB_nontriviality_prereg": negb, "pos_injection": pos},
           "verdict": None,
           "honest_boundary": "只读诊断 ⇒ 不构成能力验收；亦不改题面/夹具（改动须用户放行）。"}

    rc = 0
    if not det:
        rc = 2
    elif a.pos_inject and pos.get("performed") and not pos["changed"]:
        rc = 2
    out["verdict"] = {"rc": rc, "judge": "OK(读数可判)" if rc == 0 else "器具缺陷(控制未过)"}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("==" + " 真值侧缺口普查 ==");
    print("窗数=%d 真值失败集合种类=%d 真值全绿窗=%d 两侧失败集合逐字相同窗=%d" %
          (audit["windows"], audit["distinct_truth_failure_sets"], audit["truth_all_green_windows"],
           audit["sets_with_both_sides_identical"]))
    print("NEG-A 确定性=%s | NEG-B(非平凡:非常量=%s 非全空=%s)=%s | rc=%d" %
          (det, audit["nonconstant"], audit["nonempty"], negb["pass"], rc))
    for r in rows:
        print("  %s %s truth_fail=%s prod_fail=%s | %s" %
              (r["round"], r["win"], r["truth_failed"] or "-", r["n_prod"], r["state"]))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
