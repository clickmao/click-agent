#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R604 C3：真值掉线面**跨轮 census**（只读；13 轮 × 3 窗 × 4 臂的 `cases.txt`）。

问题：R596–R599 与 R603 的 S3（我方过 ∧ 真值败）在 `wythoff#43-public` / `wythoff#57-hidden` 上逐字复现，
但**无跨轮全窗集读数** ⇒ 无法判「低区分度用例」还是「真值臂自身漂移」。

口径（与 `judge_r603.read_cases` 同源，避免第二套解析）：
  源 = run roots（`~/.agentframework/harness/runs/<round>/<win>/<sub>/g1/cases.txt`）；
  真值臂 = `sub == codex`；产品臂 = `sub` 前缀 `agentD`；域 = 该轮冻结题集（58 例）。
判据（prereg C3，写死）：
  T1 真值侧掉线用例：真值失败窗数 >= 3 ∧ 跨 >= 2 轮
  T2 我方面：同窗产品 3 跑次中 >=2 通过 ⇒ 我方稳定通过（真值孤立失败）；<=1 ⇒ 两侧摆动带
  T3 低区分度窗：该类用例占该窗 >= 1/2（29/58）⇒ 该窗剔除配对并单列
控制：POS（把一条「真值 0 失败 ∧ 产品全过」用例伪改真值失败 ⇒ 计数必 +1 窗）· NEG（用例越域 ⇒ rc=2）·
      非平凡（全库真值失败用例集合基数 >=1 ∧ 不得为单一常量）· 守恒（逐窗记录数 == 58×(产品跑次+1)）。

rc: 0 已算 / 2 器具缺陷 / 3 输入缺失。
用法: python3 eval/rover/r604/truthcase_census_r604.py [--json <out>]
"""
from __future__ import annotations
import argparse
import copy
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
ROUNDS = ("r585", "r586", "r587", "r588", "r591", "r595", "r596", "r597",
          "r598", "r599", "r600", "r602", "r603")
FOCUS = ("wythoff#43-public", "wythoff#57-hidden")
T1_MIN_WINDOWS = 3
T1_MIN_ROUNDS = 2


def read_cases(path):
    tot, pas, fails = 0, 0, []
    for x in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        if not x.startswith("CASE"):
            continue
        parts = x.split()
        cid = parts[1] if len(parts) > 1 else "?"
        tot += 1
        if "PASS" in x:
            pas += 1
        else:
            fails.append(cid)
    return {"total": tot, "pass": pas, "fails": fails}


def load(runs_root):
    data, missing, identity = {}, [], []
    n_records = 0
    for rid in ROUNDS:
        rdir = os.path.join(runs_root, rid)
        if not os.path.isdir(rdir):
            missing.append(rdir)
            continue
        wins = sorted([d for d in os.listdir(rdir) if re.match(r"^w\d+$", d)], key=lambda w: int(w[1:]))
        for w in wins:
            wdir = os.path.join(rdir, w)
            if not os.path.isdir(wdir):
                continue
            rec = {"truth_fails": set(), "prod": {}, "n_prod": 0, "domain": None}
            for sub in sorted(os.listdir(wdir)):
                g = os.path.join(wdir, sub, "g1", "cases.txt")
                if not os.path.isfile(g):
                    continue
                cs = read_cases(g)
                if cs["total"] == 0:
                    continue
                ids = set(cs["fails"]) | set()
                # 域 = 该 cases.txt 的用例全集（PASS + FAIL 同名集合，行数为 total）
                all_ids = set()
                for x in io.open(g, encoding="utf-8", errors="replace").read().splitlines():
                    if x.startswith("CASE"):
                        all_ids.add(x.split()[1])
                if rec["domain"] is None:
                    rec["domain"] = all_ids
                elif all_ids != rec["domain"]:
                    identity.append("%s/%s/%s 域不符" % (rid, w, sub))
                n_records += cs["total"]
                if sub == "codex":
                    rec["truth_fails"] |= ids
                elif sub.startswith("agentD"):
                    rec["n_prod"] += 1
                    for cid in all_ids:
                        rec["prod"][cid] = rec["prod"].get(cid, 0) + (0 if cid in ids else 1)
            if rec["domain"] is None or rec["n_prod"] == 0:
                missing.append("%s/%s（缺真值臂或产品臂）" % (rid, w))
                continue
            data.setdefault(rid, {})[w] = rec
    return data, missing, identity, n_records


def aggregate(data, focus=FOCUS):
    per_case = {}
    per_window = {}
    windows_n = 0
    for rid, wins in sorted(data.items()):
        for w, rec in sorted(wins.items(), key=lambda kv: int(kv[0][1:])):
            windows_n += 1
            dom = rec["domain"]
            tf = rec["truth_fails"]
            n_prod = rec["n_prod"]
            pw = {"truth_fail_n": len(tf), "truth_fail_cases": sorted(tf),
                  "prod_all_pass_cases": sorted(c for c in dom if rec["prod"].get(c, 0) == n_prod),
                  "s3_cases": sorted(c for c in dom if c in tf and rec["prod"].get(c, 0) == n_prod),
                  "s3_share_of_58": round(len([c for c in dom if c in tf]) / max(len(dom), 1), 4)}
            per_window["%s/%s" % (rid, w)] = pw
            for c in dom:
                d = per_case.setdefault(c, {"windows": 0, "truth_fail_windows": 0, "truth_fail_rounds": set(),
                                            "prod_pass_runs": 0, "prod_runs": 0,
                                            "windows_prod_all_pass": 0, "windows_prod_all_fail": 0})
                d["windows"] += 1
                d["prod_runs"] += n_prod
                k = rec["prod"].get(c, 0)
                d["prod_pass_runs"] += k
                if c in tf:
                    d["truth_fail_windows"] += 1
                    d["truth_fail_rounds"].add(rid)
                if k == n_prod:
                    d["windows_prod_all_pass"] += 1
                if k == 0:
                    d["windows_prod_all_fail"] += 1
    for c, d in per_case.items():
        d["truth_fail_rounds"] = sorted(d["truth_fail_rounds"])
        d["truth_fail_round_n"] = len(d["truth_fail_rounds"])
        d["prod_pass_rate"] = round(d["prod_pass_runs"] / d["prod_runs"], 4) if d["prod_runs"] else None
    return per_case, per_window, windows_n


def focus_verdict(per_case, per_window):
    out = {}
    for c in FOCUS:
        d = per_case.get(c)
        if d is None:
            out[c] = {"present": False}
            continue
        t1 = d["truth_fail_windows"] >= T1_MIN_WINDOWS and d["truth_fail_round_n"] >= T1_MIN_ROUNDS
        st = ("我方稳定通过" if (d["prod_runs"] and d["prod_pass_runs"] / d["prod_runs"] >= 2 / 3)
              else "两侧摆动带")
        wins_with = [k for k, v in per_window.items() if c in v["s3_cases"]]
        out[c] = {"present": True, "truth_fail_windows": d["truth_fail_windows"],
                  "truth_fail_rounds": d["truth_fail_rounds"], "prod_pass_rate": d["prod_pass_rate"],
                  "T1_truth_dropout_case": t1, "T2_our_side": st, "s3_windows": wins_with,
                  "s3_window_n": len(wins_with)}
    return out


def census(per_case, per_window, windows_n):
    """T3：低区分度窗 = S3 用例数占该窗域 >= 1/2。"""
    low = []
    for k, v in per_window.items():
        dom_n = 58
        if v["s3_share_of_58"] >= 0.5 and v["s3_share_of_58"] > 0:
            low.append(k)
    truth_fail_cases = sorted(c for c, d in per_case.items() if d["truth_fail_windows"] > 0)
    return {"windows": windows_n, "truth_fail_case_n": len(truth_fail_cases),
            "truth_fail_cases": truth_fail_cases,
            "truth_fail_windows_total": sum(d["truth_fail_windows"] for d in per_case.values()),
            "low_discrimination_windows": low}


def identity_violations(data):
    """越域 = 真值失败集合含域外 id ⇒ 身份闸（rc=2）。"""
    bad = []
    for rid, wins in sorted(data.items()):
        for w, rec in sorted(wins.items()):
            ext = set(rec["truth_fails"]) - set(rec["domain"])
            if ext:
                bad.append({"round": rid, "window": w, "outside": sorted(ext)[:4]})
    return bad


def controls(data):
    out = {"pos_ok": False, "neg_ok": False, "note": ""}
    base_case, base_pt, _bw = aggregate(data)
    windows_n = len(base_pt)
    # POS 靶：真值 0 失败 ∧ 产品全过 ≥3 窗
    tgt = None
    for c, d in sorted(base_case.items()):
        if d["truth_fail_windows"] == 0 and d["windows_prod_all_pass"] >= 3:
            tgt = c
            break
    if tgt is None:
        out["note"] = "无「真值 0 失败 ∧ 产品全过 ≥3 窗」用例 ⇒ POS 无靶"
        return out
    inj = copy.deepcopy(data)
    rid, w = sorted(inj.keys())[0], sorted(inj[sorted(inj.keys())[0]].keys(), key=lambda x: int(x[1:]))[0]
    inj[rid][w]["truth_fails"] = set(inj[rid][w]["truth_fails"]) | {tgt}
    pos_case, pos_pt, pos_w = aggregate(inj)
    got = pos_case[tgt]["truth_fail_windows"] - base_case[tgt]["truth_fail_windows"]
    out["pos_ok"] = (got == 1 and pos_case[tgt]["truth_fail_round_n"] >= 1 and pos_w == windows_n)
    out["pos_detail"] = {"case": tgt, "delta_windows": got,
                         "rounds": pos_case[tgt]["truth_fail_rounds"], "windows": pos_w}
    # NEG：越域用例 id 必须被身份闸抓住（rc=2），且不得被计数
    bad = copy.deepcopy(data)
    bad[rid][w]["truth_fails"] = set(bad[rid][w]["truth_fails"]) | {"wythoff#99-public"}
    bad_case, _bp, _bwn = aggregate(bad)
    v_base = identity_violations(data)
    v_bad = identity_violations(bad)
    out["neg_ok"] = (not v_base) and bool(v_bad) and ("wythoff#99-public" not in bad_case)
    out["neg_detail"] = {"injected": "wythoff#99-public", "base_violations": len(v_base),
                         "injected_violations": len(v_bad), "counted": "wythoff#99-public" in bad_case}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default=RUNS)
    ap.add_argument("--json", default=os.path.join(REPO, "eval/rover/r604/truthcase-census-r604.json"))
    a = ap.parse_args()

    out = {"tool": "truthcase_census_r604", "round": "R604", "verdict": "PENDING", "rc": 3,
           "criteria": "prereg-r604.json C3（T1 真值掉线用例 / T2 我方面 / T3 低区分度窗）",
           "rounds": list(ROUNDS), "focus": list(FOCUS)}
    data, missing, identity, n_records = load(a.runs_root)
    if not data:
        out.update({"verdict": "INPUT_MISSING", "rc": 3, "missing": missing[:5]})
        print("[census-r604] rc=3 INPUT_MISSING %s" % missing[:3])
        with io.open(a.json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        return 3

    defects = []
    if identity:
        defects.append("域身份不符: %s" % identity[:3])
    v_base = identity_violations(data)
    if v_base:
        defects.append("真值失败集合越域（身份闸）: %s" % v_base[:3])
    per_case, per_window, windows_n = aggregate(data)
    summ = census(per_case, per_window, windows_n)
    foc = focus_verdict(per_case, per_window)
    ctl = controls(data)

    # 守恒：逐窗记录数 == 58 ×（产品跑次 + 1）
    expect = 0
    for rid, wins in data.items():
        for w, rec in wins.items():
            expect += len(rec["domain"]) * (rec["n_prod"] + 1)
    out["conservation"] = {"records": n_records, "expect": expect, "ok": n_records == expect}
    if n_records != expect:
        defects.append("守恒判据不成立: %d != %d" % (n_records, expect))
    if not ctl.get("pos_ok"):
        defects.append("POS 控制无牙: %s" % ctl)
    if not ctl.get("neg_ok"):
        defects.append("NEG 控制不成立: %s" % ctl)
    if summ["truth_fail_case_n"] == 0:
        defects.append("非平凡失败：全库真值失败用例集合为空（退化为恒真门）")

    out.update({"windows": windows_n, "cases": len(per_case), "summary": summ,
                "focus_verdict": foc, "controls": ctl,
                "per_case_top": sorted(
                    [{"case": c, "truth_fail_windows": d["truth_fail_windows"],
                      "truth_fail_rounds": d["truth_fail_rounds"], "prod_pass_rate": d["prod_pass_rate"]}
                     for c, d in per_case.items() if d["truth_fail_windows"] > 0],
                    key=lambda x: (-x["truth_fail_windows"], x["case"]))[:12],
                "per_window": per_window})
    if missing:
        out["missing"] = missing[:5]

    if defects:
        out.update({"verdict": "INSTRUMENT_DEFECT", "rc": 2, "defects": defects})
    else:
        out.update({"verdict": "COMPUTED", "rc": 0})

    print("[census-r604] rc=%d verdict=%s windows=%d truth_fail_case_n=%d records=%d/%d"
          % (out["rc"], out["verdict"], windows_n, summ["truth_fail_case_n"], n_records, expect))
    for c, v in foc.items():
        print("  focus %s: truth_fail_windows=%s rounds=%s prod_pass_rate=%s T1=%s T2=%s"
              % (c, v.get("truth_fail_windows"), v.get("truth_fail_rounds"), v.get("prod_pass_rate"),
                 v.get("T1_truth_dropout_case"), v.get("T2_our_side")))
    print("  controls=%s" % json.dumps(ctl, ensure_ascii=False))
    if defects:
        print("  defects=%s" % defects)
    with io.open(a.json, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("  wrote %s" % a.json)
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
