#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R514 · 判据稳健化 (候选①): 主判据 = **不必要的远端调用数下降**; token 降幅取 n≥5 中位数并三态判决。

R512/R513 实证的问题: token 降幅跨跑次摆动达 2 倍级 (codex 侧 849,925–1,266,833), 单跑以 token 判「达标」不稳;
调用数判据跨跑次稳定 (7 vs 14/8 ⇒ 0.50–0.875) —— 故把**调用数**提为主判据, token 降为需 n≥5 的次要判据。

口径 (全部从预注册机取, 禁硬编码常数):
  C1 (主) 不必要的远端调用数下降: 逐 (窗口,题) 求 `agent_calls / codex_calls`;
       判据 = `max(比值) <= 1.0` (规则式, 无常数) ∧ `min(比值) < 1.0` (须有真实下降, 否则「不更差」被当成「更好」)。
  C2 (次) token 降幅: 取**中位数**且要求**两侧跑次 n >= n_min**; 阈值来自预注册规则里的常数。
       三态: 达标 / 越线 / **弃权**(n < n_min; 或缺 usage 未上报) —— 弃权单列计数, 不判红也不判绿。
  C3 (质) 质量不降: 逐 (窗口,题) 断言 `agent_cases >= codex_cases`。
  C4 (前置) 铁律 11 可验收前置: 由 `eval/rover/r507pre/exec_precondition.py` 的 rc 提供 (缺 ⇒ 弃权单列)。

退出码: 0 = 全部达标 / 1 = 判据未达标 / 2 = 器具缺陷(fail-closed) / 3 = 缺侧(只有单侧)。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys


def _ratio_rows(rows):
    """(窗口, 题) → {侧: 行}; 窗口由 run 尾号派生 (A-r1/C-r1 → w1)。"""
    win_of = {}
    for r in rows:
        m = re.search(r"-r(\d+)$", r.get("run") or "")
        win_of.setdefault(r.get("run"), "w%s" % (m.group(1) if m else "?"))
    buckets = {}
    for r in rows:
        key = (win_of.get(r.get("run")), r.get("tid"), r.get("arm"))
        buckets[key] = r
    pairs = {}
    for (w, tid, arm), r in buckets.items():
        pairs.setdefault((w, tid), {})[arm] = r
    return pairs


def _median(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return statistics.median(vals) if vals else None


def evaluate(rep, pre):
    rows = rep.get("rows")
    if not isinstance(rows, list) or not rows:
        raise InstrumentError("report 缺 rows ⇒ 器具缺陷")
    rules = (pre or {}).get("criteria")
    if not isinstance(rules, dict):
        raise InstrumentError("预注册缺 criteria ⇒ 器具缺陷 (禁硬编码判据)")
    noise = (pre or {}).get("declared_noise_sources")
    if not isinstance(noise, list) or not noise:
        raise InstrumentError("预注册缺 declared_noise_sources ⇒ 器具缺陷 (噪声源必须预声明)")
    m = re.search(r"<=\s*([0-9.]+)\s*\*", rules.get("C2_token_median", {}).get("rule", ""))
    tok_thr = float(m.group(1)) if m else None
    m2 = re.search(r"n\s*>=\s*(\d+)", rules.get("C2_token_median", {}).get("rule", ""))
    n_min = int(m2.group(1)) if m2 else None
    if tok_thr is None or n_min is None:
        raise InstrumentError("预注册 C2 规则里取不到阈值/最小跑次数 ⇒ fail-closed")
    pairs = _ratio_rows(rows)
    sides = {r.get("arm") for r in rows}
    if len(sides) < 2 or "A" not in sides or "C" not in sides:
        return {"verdict": "MISSING_SIDE", "sides": sorted(str(s) for s in sides)}
    per_pair, call_ratios, tok_ratios, qual_ok = [], [], [], True
    for (w, tid), byarm in sorted(pairs.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or "")):
        a, c = byarm.get("A"), byarm.get("C")
        if not a or not c:
            return {"verdict": "MISSING_SIDE", "pair": [w, tid], "have": sorted(byarm)}
        cr = (a["calls"] / c["calls"]) if c.get("calls") else None
        tr = (a["total_tokens"] / c["total_tokens"]) if c.get("total_tokens") else None
        per_pair.append({"window": w, "tid": tid, "agent_calls": a["calls"], "codex_calls": c["calls"],
                         "calls_ratio": cr, "agent_tokens": a["total_tokens"], "codex_tokens": c["total_tokens"],
                         "token_ratio": tr, "agent_cases": a.get("cases_pass"), "codex_cases": c.get("cases_pass"),
                         "agent_unreported_usage": a.get("unreported_usage"),
                         "codex_unreported_usage": c.get("unreported_usage")})
        if cr is not None:
            call_ratios.append(cr)
        if tr is not None:
            tok_ratios.append(tr)
        if (a.get("cases_pass") or 0) < (c.get("cases_pass") or 0):
            qual_ok = False
    c1_ok = bool(call_ratios) and max(call_ratios) <= 1.0 and min(call_ratios) < 1.0
    # 跑次数 = **每侧** (逐 (题,臂)) 的独立跑次数, 不是两臂 run 标签的并集 (否则 N 被两倍化)。
    runs_by_side = {}
    for r in rows:
        runs_by_side.setdefault((r.get("tid"), r.get("arm")), set()).add(r.get("run"))
    n_runs = max((len(v) for v in runs_by_side.values()), default=0)
    unreported = sum((r.get("unreported_usage") or 0) for r in rows)
    if n_runs < n_min:
        c2 = {"state": "ABSTAIN_N_BELOW_MIN", "n_runs": n_runs, "n_min": n_min}
    elif unreported:
        c2 = {"state": "ABSTAIN_UNREPORTED_USAGE", "unreported_usage": unreported, "n_runs": n_runs}
    else:
        med = _median(tok_ratios)
        c2 = {"state": "PASS" if (med is not None and med <= tok_thr) else "BREACH",
              "median_token_ratio": med, "threshold": tok_thr, "n_runs": n_runs}
    checks = {"C1_remote_calls_no_worse": {"pass": c1_ok, "max_ratio": max(call_ratios) if call_ratios else None,
                                           "min_ratio": min(call_ratios) if call_ratios else None,
                                           "rule": rules.get("C1_calls_primary", {}).get("rule")},
              "C2_token_median_n_ge_min": c2, "C2_context": rules.get("C2_token_median", {}).get("rule"),
              "C3_quality_not_lower": {"pass": qual_ok}, "C4_exec_precondition": (pre or {}).get("precond", {})}
    bad = (not c1_ok) or (not qual_ok) or c2["state"] == "BREACH"
    return {"verdict": "BREACH" if bad else "PASS", "checks": checks, "pairs": per_pair,
            "declared_noise_sources": noise}


class InstrumentError(Exception):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    try:
        rep = json.load(open(a.report, encoding="utf-8-sig"))
        pre = json.load(open(a.prereg, encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        print("[器具缺陷 rc=2] 输入不可解析: %s" % exc)
        return 2
    try:
        out = evaluate(rep, pre)
    except InstrumentError as exc:
        print("[器具缺陷 rc=2] %s" % exc)
        return 2
    if out["verdict"] == "MISSING_SIDE":
        print("[缺侧 rc=3] %s" % json.dumps(out, ensure_ascii=False))
        return 3
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1))
    for k, v in out["checks"].items():
        print("%-28s %s" % (k, json.dumps(v, ensure_ascii=False)[:200]))
    print("verdict=%s" % out["verdict"])
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
