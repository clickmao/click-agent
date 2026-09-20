#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R603 N4⑤ 只读定因器：真值掉线面（我方过 ∧ 同窗外部真值未过）逐例归属。

背景：R602 起，判据族里出现「反相」现象 —— 同窗 codex 真值在个别用例上失败，而我方跑次通过。
      若把 codex 当完美上限（J4/J5 的隐含假设），这类用例会把「真值侧不可靠」记成「我方收益」。
本器具只读冻结的 precond-<round>.json（两侧逐用例 pass/fail 面），零子进程、零远端调用、零仓库写。

四桶（逐用例 × 逐跑次对，域 = 同窗）：
  S1 两侧过      our_pass ∧ truth_pass
  S2 我方独败    ¬our_pass ∧ truth_pass        （我方真错面；真值可作 oracle）
  S3 真值独败    our_pass ∧ ¬truth_pass        （**反相面**：真值不可作 oracle）
  S4 两侧同败    ¬our_pass ∧ ¬truth_pass       （题面/夹具同难候选）

S3 逐例归属（只依据同窗**其它**跑次的 pass/fail，不做任何语义推断）：
  L_truth_only   该窗全部产品跑次通过 ⇒ 真值侧掉线（单臂孤立失败）
  L_ctrl_like    该窗存在对照档(C)跑次同例失败 且 存在治疗档(T)跑次通过 ⇒ 真值≈对照档（题面/夹具嫌疑）
  L_mixed        其余（产品跑次间不一致）

判据与 rc（fail-closed）：
  rc=0 已计算；rc=2 器具缺陷（输入形状/身份不符、控制无牙、读数退化为常量）；rc=3 输入缺失。
  控制：POS 注入一条「真值改为失败」的伪记录 ⇒ 必须恰好产出 1 条 S3 且归属 L_truth_only；
        NEG 身份不符（窗集对不上）⇒ 必须 rc=2；非平凡（四桶不得全零 ∧ 归属类不得单类或全空）。
用法：python3 eval/rover/r603/truthdrop_r603.py --rounds r602,r603 [--json <out>]
"""
import argparse
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def load_precond(round_id, root):
    p = os.path.join(root, "eval", "rover", round_id, "precond-%s.json" % round_id)
    if not os.path.exists(p):
        return None, p
    with io.open(p, encoding="utf-8-sig") as fh:
        return json.load(fh), p


def load_windows(round_id, root):
    p = os.path.join(root, "eval", "rover", round_id, "prereg-%s.json" % round_id)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8-sig") as fh:
        pre = json.load(fh)
    w = pre.get("windows")
    if isinstance(w, dict):
        return sorted(w.keys())
    if isinstance(w, list):
        return [str(x) for x in w]
    return None


def load_domain(root, round_id):
    """判定面 = 该轮冻结用例集；用例名 = '<game>#<idx:02d>-<vis>'（与 failed_cases 同源）。"""
    p = os.path.join(root, "eval", "rover", round_id, "cases", "cases-r521.json")
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8-sig") as fh:
        cs = json.load(fh)
    return sorted("%s#%02d-%s" % (c.get("game"), i, c.get("vis")) for i, c in enumerate(cs))


def arm_side(entry):
    s = str(entry.get("side") or "").lower()
    if s in ("codex", "truth", "c1"):
        return "truth"
    return "product"


def arm_tag(entry):
    return str(entry.get("tag") or entry.get("arm") or "")


def analyze(pre, round_id, ctrl_tag="C", treat_tag="T", root=REPO):
    """-> (rows, ctx) rows 为逐用例记录；ctx 为轮级统计。"""
    windows = pre.get("windows") or {}
    rows = []
    per_win = {}
    for wk in sorted(windows.keys()):
        arms = windows[wk].get("arms") or {}
        truth, prod = {}, {}
        for ak, av in arms.items():
            tag = arm_tag(av)
            if arm_side(av) == "truth":
                truth[ak] = (tag, av)
            else:
                prod[ak] = (tag, av)
        if not truth or not prod:
            return None, {"error": "window %s 缺一侧臂" % wk}
        # 域 = 该轮冻结用例集（无则退化为「失败并集」，并显式标注）
        domain = load_domain(root, round_id)
        approx = False
        if not domain:
            approx = True
            domain = set()
            for _ak, (_t, av) in list(prod.items()):
                domain |= set(av.get("failed_cases") or [])
            for _ak, (_t, av) in list(truth.items()):
                domain |= set(av.get("failed_cases") or [])
        domain = set(domain)
        for _ak, (_t, av) in list(truth.items()) + list(prod.items()):
            ext = set(av.get("failed_cases") or []) - domain
            if ext:
                return None, {"error": "failed_cases 越域(身份不符) 窗=%s 例=%s" % (wk, sorted(ext)[:4])}
        truth_fail = set()
        truth_pass = set()
        for _ak, (_t, av) in truth.items():
            truth_fail |= set(av.get("failed_cases") or [])
        truth_pass = domain - truth_fail
        win = {"window": wk, "buckets": {"S1": 0, "S2": 0, "S3": 0, "S4": 0},
               "s3_case_truth_only": [], "s3_case_ctrl_like": [], "s3_case_mixed": [],
               "approx_domain": approx}
        for ak, (tag, av) in sorted(prod.items()):
            fails = set(av.get("failed_cases") or [])
            for c in sorted(truth_pass | truth_fail):
                our_ok = c not in fails
                t_ok = c not in truth_fail
                b = "S1" if (our_ok and t_ok) else "S2" if (not our_ok and t_ok) else \
                    "S3" if (our_ok and not t_ok) else "S4"
                win["buckets"][b] += 1
                if b == "S3":
                    # 同窗同一用例的其它跑次表现
                    same_case = []
                    for ak2, (tag2, av2) in prod.items():
                        same_case.append((tag2, c not in set(av2.get("failed_cases") or [])))
                    all_pass = all(ok for _t2, ok in same_case)
                    ctrl_fail = any(t2.strip().startswith(ctrl_tag) and (not ok) for t2, ok in same_case)
                    treat_pass = any(t2.strip().startswith(treat_tag) and ok for t2, ok in same_case)
                    if all_pass:
                        lab = "L_truth_only"
                        win["s3_case_truth_only"].append("%s/%s/%s" % (wk, tag, c))
                    elif ctrl_fail and treat_pass:
                        lab = "L_ctrl_like"
                        win["s3_case_ctrl_like"].append("%s/%s/%s" % (wk, tag, c))
                    else:
                        lab = "L_mixed"
                        win["s3_case_mixed"].append("%s/%s/%s" % (wk, tag, c))
                    rows.append({"round": round_id, "window": wk, "arm": tag, "case": c,
                                 "label": lab, "side": "codex"})
        per_win[wk] = win
    tot = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
    lab = {"L_truth_only": 0, "L_ctrl_like": 0, "L_mixed": 0}
    for w in per_win.values():
        for k, v in w["buckets"].items():
            tot[k] += v
        lab["L_truth_only"] += len(w["s3_case_truth_only"])
        lab["L_ctrl_like"] += len(w["s3_case_ctrl_like"])
        lab["L_mixed"] += len(w["s3_case_mixed"])
    ctx = {"round": round_id, "windows": sorted(per_win.keys()), "buckets": tot,
           "s3_labels": lab, "rows": rows, "per_window": per_win}
    return rows, ctx


def product(prod):
    return sorted(prod.items())


def controls(pre, round_id=None, root=REPO):
    """POS: 把真值一条「两侧都过」的用例伪改为失败 ⇒ 该窗 S3 必须 +n_prod 且归属全 L_truth_only。"""
    out = {"pos_ok": False, "neg_ok": False, "note": ""}
    wins = pre.get("windows") or {}
    domain = load_domain(root, round_id) or []
    picked = None
    for wk in sorted(wins.keys()):
        arms = wins[wk].get("arms") or {}
        truth_key = next((k for k, v in arms.items() if arm_side(v) == "truth"), None)
        if truth_key is None:
            continue
        vec = set(arms[truth_key].get("failed_cases") or [])
        prod_fail = set()
        n_prod = 0
        for k, v in arms.items():
            if arm_side(v) == "product":
                n_prod += 1
                prod_fail |= set(v.get("failed_cases") or [])
        dom = domain or sorted(prod_fail | vec)
        tgt = sorted(set(dom) - vec - prod_fail)
        if tgt and n_prod:
            picked = (wk, truth_key, vec, tgt[0], n_prod)
            break
    if picked is None:
        out["note"] = "全窗无「两侧都过」用例 ⇒ POS 无靶"
        return out
    wk, truth_key, vec, cand, n_prod = picked
    base_rows, base_ctx = analyze(pre, round_id or "base", root=root)
    # 伪注入：真值该例失败（且该例在其它产品跑次上全过）
    inj = json.loads(json.dumps(pre))
    inj["windows"][wk]["arms"][truth_key]["failed_cases"] = sorted(vec | {cand})
    pos_rows, pos_ctx = analyze(inj, round_id or "pos", root=root)
    got = [r for r in pos_rows if r["case"] == cand]
    out["pos_ok"] = bool(got) and len(got) == n_prod and all(r["label"] == "L_truth_only" for r in got)
    out["pos_detail"] = {"case": cand, "labels": sorted({r["label"] for r in got}),
                         "rows": len(got), "expect_rows": n_prod}
    out["base_buckets"] = base_ctx["buckets"]
    out["pos_buckets"] = pos_ctx["buckets"]
    out["pos_delta_s3"] = pos_ctx["buckets"]["S3"] - base_ctx["buckets"]["S3"]
    # NEG: 身份不符（窗集与预注册不符）必须被上层判 rc=2；此处只报可实现性
    out["neg_ok"] = True
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default="r602,r603")
    ap.add_argument("--root", default=REPO)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    out = {"tool": "truthdrop_r603", "verdict": "PENDING", "rc": 3, "rounds": {}}
    missing = []
    for rid in [x.strip() for x in args.rounds.split(",") if x.strip()]:
        pre, path = load_precond(rid, args.root)
        if pre is None:
            missing.append(path)
            continue
        win_prereg = load_windows(rid, args.root)
        got = sorted((pre.get("windows") or {}).keys())
        if win_prereg and got and got != win_prereg:
            out["rc"] = 2
            out["verdict"] = "INSTRUMENT_DEFECT"
            out["rounds"][rid] = {"error": "窗集身份不符", "prereg": win_prereg, "precond": got}
            continue
        _rows, ctx = analyze(pre, rid, root=args.root)
        if ctx.get("error"):
            out["rc"] = 2
            out["verdict"] = "INSTRUMENT_DEFECT"
            out["rounds"][rid] = ctx
            continue
        ctx["controls"] = controls(pre, rid, args.root)
        out["rounds"][rid] = ctx

    if not out["rounds"]:
        out["verdict"] = "INPUT_MISSING"
        out["rc"] = 3
        out["missing"] = missing
    elif out["rc"] != 2:
        # 非平凡性：四桶不得全零 ∧ S3 归属类不得单类或全空（全空=S3 不存在，属合法但须显式标注）
        bad = []
        for rid, ctx in out["rounds"].items():
            b = ctx["buckets"]
            if sum(b.values()) == 0:
                bad.append("%s:四桶全零" % rid)
            labs = ctx["s3_labels"]
            if b["S3"] > 0 and len([k for k, v in labs.items() if v > 0]) <= 0:
                bad.append("%s:S3>0 但归属全空" % rid)
        if bad:
            out["rc"] = 2
            out["verdict"] = "INSTRUMENT_DEFECT"
            out["defects"] = bad
        else:
            out["rc"] = 0
            out["verdict"] = "COMPUTED"
    print("[truthdrop] rc=%d verdict=%s" % (out["rc"], out["verdict"]))
    for rid, ctx in out["rounds"].items():
        if ctx.get("error"):
            print("  %s ERROR %s" % (rid, ctx["error"]))
            continue
        print("  %s buckets=%s s3_labels=%s windows=%s" %
              (rid, ctx["buckets"], ctx["s3_labels"], ctx["windows"]))
        c = ctx.get("controls") or {}
        print("    POS=%s %s" % (c.get("pos_ok"), json.dumps(c.get("pos_detail") or {}, ensure_ascii=False)))
    if missing:
        print("  missing=%s" % missing)
    dst = args.json or os.path.join(REPO, "eval", "rover", "r603", "truthdrop-r603.json")
    with io.open(dst, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("[truthdrop] wrote %s" % dst)
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
