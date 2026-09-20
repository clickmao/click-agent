#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R604 C2：J3 成本判据**形态收口**（v1 `max-of-9` 单点极值 ⇒ v2 池化 ∧ 逐窗池化 ∧ 单位调用新算 prompt）。

纪律（预注册 eval/rover/r604/prereg-r604.json 先写后跑）：
  · v1 形态**照原样重算**并与各轮已登记值**逐位复现**（r600 4/4 PASS · r602 2/3 PASS · r603 4/3 FAIL）——不符即 rc=2；
  · v2 形态**并列**呈现，**不翻案**任何已作判决；v2 三条**不含拍出来的阈值**（无自由参数）；
  · 每跑次 调用/新算 prompt/completion 由 **run root adapter dump**（import `kpi_r599.arm_stats`，禁重写第二份）重算，
    并与各轮 `kpi-table-r*.json` 的逐臂数组**逐位比对**（两路径交叉校验；不符 ⇒ 器具读法错 ⇒ rc=2，禁计入被测读数）；
  · 控制：POS（注入一条 T 跑次 calls+=2 ⇒ v2 必判红且点名 a1/a2）· NEG（无注入 ≡ base）· 非平凡（三轮读数互异）。

rc: 0 已算 / 2 器具缺陷 / 3 输入缺失。
用法: python3 eval/rover/r604/judge_j3v2_r604.py [--json <out>]
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
SRC = os.path.join(REPO, "eval/rover/r599/kpi_r599.py")
KPI_LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")
ROUNDS = ("r600", "r602", "r603")


def helpers():
    spec = importlib.util.spec_from_file_location("kpi599", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def load_runs(rid):
    p = os.path.join(RUNS, rid, "logs", "runs.jsonl")
    if not os.path.isfile(p):
        return None, p
    return [json.loads(l) for l in io.open(p, encoding="utf-8", errors="replace") if l.strip()], p


def collect(rid, mod):
    runs, path = load_runs(rid)
    if runs is None:
        return None, {"missing": path}
    recs = []
    for r in runs:
        side = "codex" if r["sub"] == "codex" else "agent"
        st = mod.arm_stats(os.path.join(RUNS, rid, "adapter"), side, tuple(r["range"]))
        recs.append({"arm": r["arm"], "win": r["win"], "rep": r["rep"], "sub": r["sub"],
                     "calls": st["calls"], "new_prompt": st["new_prompt"],
                     "completion": st["completion"], "bad_dumps": len(st["bad_dumps"])})
    return recs, {"runs": len(recs)}


def table_arrays(rid):
    p = os.path.join(REPO, "eval/rover", rid, "kpi-table-%s.json" % rid)
    if not os.path.isfile(p):
        return None
    rows = json.load(io.open(p, encoding="utf-8")).get("rows") or []
    out = {}
    for r in rows:
        a = r.get("臂")
        if a:
            out[a] = {"调用": r.get("调用"), "新算prompt": r.get("新算prompt"),
                      "completion": r.get("completion")}
    return out


def registered_j3(rid):
    if not os.path.isfile(KPI_LEDGER):
        return None
    found = None
    for line in io.open(KPI_LEDGER, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if str(d.get("round")) == rid.upper():
            found = d.get("J3_cost")
    return found


def v1_form(recs):
    t = [r["calls"] for r in recs if r["arm"] == "T"]
    c = [r["calls"] for r in recs if r["arm"] == "C"]
    if not t or not c:
        return None
    return {"T_max_calls": max(t), "C_max_calls": max(c), "pass": max(t) <= max(c)}


def v2_form(recs, inject=None):
    """inject: {"arm":..., "win":..., "rep":..., "d_calls":n} —— 只看调用数注入。"""
    rs = copy.deepcopy(recs)
    if inject:
        for r in rs:
            if (r["arm"], r["win"], r["rep"]) == (inject["arm"], inject["win"], inject["rep"]):
                r["calls"] += inject.get("d_calls", 0)
    T = [r for r in rs if r["arm"] == "T"]
    C = [r for r in rs if r["arm"] == "C"]
    if not T or not C:
        return None
    sumT, sumC = sum(r["calls"] for r in T), sum(r["calls"] for r in C)
    wins = sorted({r["win"] for r in T} | {r["win"] for r in C}, key=lambda w: int(w[1:]))
    perwin = {}
    a2 = True
    for w in wins:
        tw = sum(r["calls"] for r in T if r["win"] == w)
        cw = sum(r["calls"] for r in C if r["win"] == w)
        perwin[w] = {"T": tw, "C": cw, "ok": tw <= cw}
        a2 = a2 and perwin[w]["ok"]
    npT = sum(r["new_prompt"] for r in T)
    npC = sum(r["new_prompt"] for r in C)
    unitT = round(npT / sumT, 4) if sumT else None
    unitC = round(npC / sumC, 4) if sumC else None
    b1 = None if (unitT is None or unitC is None) else unitT <= unitC
    a1 = sumT <= sumC
    fails = []
    if not a1:
        fails.append("a1_pooled_calls")
    if not a2:
        fails.append("a2_per_window_calls:" + ",".join(w for w, v in perwin.items() if not v["ok"]))
    if b1 is False:
        fails.append("b1_unit_new_prompt")
    if b1 is None:
        fails.append("b1_undefined(denominator_zero)")
    return {"a1": a1, "a2": a2, "b1": b1, "pass": bool(a1 and a2 and b1),
            "sum_calls": {"T": sumT, "C": sumC},
            "sum_new_prompt": {"T": npT, "C": npC},
            "unit_new_prompt_per_call": {"T": unitT, "C": unitC},
            "per_window_calls": perwin, "failed_clauses": fails}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(REPO, "eval/rover/r604/j3v2-r604.json"))
    a = ap.parse_args()
    out = {"tool": "judge_j3v2_r604", "round": "R604", "verdict": "PENDING", "rc": 3,
           "criteria": "prereg-r604.json C2（v1 留档 / v2 新注册，无自由参数）", "rounds": {}}
    mod = helpers()
    defects = []
    keys = []
    for rid in ROUNDS:
        recs, meta = collect(rid, mod)
        if recs is None:
            out["rounds"][rid] = meta
            continue
        block = {"meta": meta, "bad_dumps": sum(r["bad_dumps"] for r in recs)}
        # --- 两路径交叉校验：adapter 重算 == kpi-table 数组（多重集相等）---
        tbl = table_arrays(rid)
        mismatch = []
        if tbl is None:
            mismatch.append("kpi-table 缺件")
        else:
            for arm, arrs in tbl.items():
                rs = [r for r in recs if r["arm"] == arm]
                for col, key in (("调用", "calls"), ("新算prompt", "new_prompt"), ("completion", "completion")):
                    want = arrs.get(col)
                    if want is None:
                        continue
                    got = [r[key] for r in rs]
                    if sorted(got) != sorted(want):
                        mismatch.append("%s.%s got=%s want=%s" % (arm, col, sorted(got), sorted(want)))
        block["two_path"] = {"ok": not mismatch, "mismatch": mismatch}
        if mismatch:
            defects.append("%s 两路径不符: %s" % (rid, mismatch[:3]))
        # --- v1 逐位复现 ---
        v1 = v1_form(recs)
        reg = registered_j3(rid)
        block["v1_form"] = v1
        block["registered_j3"] = reg
        if v1 and isinstance(reg, dict):
            agree = (v1["pass"] == bool(reg.get("pass"))
                     and v1["T_max_calls"] == reg.get("T_max_calls")
                     and v1["C_max_calls"] == reg.get("C_max_calls"))
            block["v1_agrees_registered"] = agree
            if not agree:
                defects.append("%s v1 形态与登记值不符: %s vs %s" % (rid, v1, reg))
        else:
            block["v1_agrees_registered"] = None
        # --- v2 ---
        block["v2_form"] = v2_form(recs)
        # --- 控制 ---
        t0 = next((r for r in recs if r["arm"] == "T"), None)
        pos = v2_form(recs, {"arm": "T", "win": t0["win"], "rep": t0["rep"], "d_calls": 2}) if t0 else None
        neg = v2_form(recs, None)
        ctrl = {"pos_fail": bool(pos and not pos["pass"]),
                "pos_named": (pos or {}).get("failed_clauses", []),
                "neg_same_as_base": bool(neg == block["v2_form"])}
        ctrl["has_teeth"] = ctrl["pos_fail"] and bool(ctrl["pos_named"]) and ctrl["neg_same_as_base"]
        block["controls"] = ctrl
        if not ctrl["has_teeth"]:
            defects.append("%s v2 控制无牙: %s" % (rid, ctrl))
        keys.append((rid, (block["v2_form"] or {}).get("sum_calls", {}).get("T"),
                     (block["v2_form"] or {}).get("sum_calls", {}).get("C")))
        out["rounds"][rid] = block

    present = [k for k in keys if k[1] is not None]
    out["non_trivial"] = {"keys": keys, "distinct": len({(k[1], k[2]) for k in present}) == len(present) and len(present) > 1}
    if not out["non_trivial"]["distinct"]:
        defects.append("非平凡失败：三轮 (Σ_T calls, Σ_C calls) 读数不互异: %s" % keys)

    if not out["rounds"]:
        out.update({"verdict": "INPUT_MISSING", "rc": 3})
    elif defects:
        out.update({"verdict": "INSTRUMENT_DEFECT", "rc": 2, "defects": defects})
    else:
        out.update({"verdict": "COMPUTED", "rc": 0})

    print("[j3v2-r604] rc=%d verdict=%s 非平凡=%s" % (out["rc"], out["verdict"], out["non_trivial"]["distinct"]))
    for rid in ROUNDS:
        b = out["rounds"].get(rid)
        if not b or "v1_form" not in b:
            print("  %s MISSING/ERR %s" % (rid, str(b)[:120]))
            continue
        print("  %s v1=%s (登记 %s)  agree=%s" % (rid, b["v1_form"], b["registered_j3"], b["v1_agrees_registered"]))
        v2 = b["v2_form"]
        print("     v2 pass=%s a1=%s a2=%s b1=%s Σcalls T/C=%s/%s Σnew T/C=%s/%s unit T/C=%s/%s fails=%s"
              % (v2["pass"], v2["a1"], v2["a2"], v2["b1"], v2["sum_calls"]["T"], v2["sum_calls"]["C"],
                 v2["sum_new_prompt"]["T"], v2["sum_new_prompt"]["C"],
                 v2["unit_new_prompt_per_call"]["T"], v2["unit_new_prompt_per_call"]["C"], v2["failed_clauses"]))
        print("     ctrl=%s two_path_ok=%s bad_dumps=%d" % (b["controls"], b["two_path"]["ok"], b["bad_dumps"]))
    if defects:
        print("  defects=%s" % defects)
    with io.open(a.json, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("  wrote %s" % a.json)
    return out["rc"]


if __name__ == "__main__":
    sys.exit(main())
