#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R599 候选④-b 器具: **landing 零回归面的 scope 绑定机检**（消除单窗集读法伪影）。

背景（R598 checks_posthoc）: `landing_predicate_r593.py --rounds r598` 只覆盖 9 跑次，而该器具的零回归面
钉在 **R592 登记件的全 scope**（r585–r588 + r591，59 跑次）⇒ 单窗集读法下 `zero_regression.match=False`
是**读法伪影**，不是器具或被测回归（历史全 scope 复算逐位相同已证）。

本机检把「请求轮集」与「登记件 scope」**绑成机检**（不改共享器具内部，边界见报告）:
  · 请求 == 登记全 scope          ⇒ 零回归面 `applicable=true`，正常判定并进 rc。
  · 请求 ⊊ 登记全 scope（单窗集） ⇒ 零回归面 `applicable=false, reason=partial_scope`（**不进 rc**，读数只作并列信息）。
  · 请求 ⊄ 登记全 scope           ⇒ rc=3 fail-closed（不许在未登记 scope 上给判定）。
另: `--recompute-full` 复算全 scope 并与登记件读数**逐位**比对（器具中性证明）。

成对控制（影子自检，不依赖真机）: ①partial ⇒ applicable=false ②full ⇒ applicable=true ③未登记轮 ⇒ rc=3
④注入读数漂移 ⇒ 必须报 not_matched（防恒真门）。

用法: python3 eval/rover/r599/scope_bind_r599.py --landing eval/rover/r599/landing-predicate-r599.json \
        --out eval/rover/r599/scope-bind-r599.json [--recompute-full --predicate eval/rover/r593/landing_predicate_r593.py]
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
FULL_SCOPE = ["r585", "r586", "r587", "r588", "r591"]
REGISTRY = os.path.join(REPO, "eval/rover/r592/landing-predicate-r592.json")


def rd(p):
    return json.load(io.open(p, encoding="utf-8"))


def relation(req, full):
    req, full = set(req), set(full)
    if req == full:
        return "full"
    if req < full:
        return "partial"
    return "unregistered"


def face_readings(j):
    zr = j.get("zero_regression", {})
    return {"match": zr.get("match"), "expected": zr.get("expected"), "actual": zr.get("actual")}


def judge(req_rounds, landing, registry, recompute_full=None):
    rel = relation(req_rounds, FULL_SCOPE)
    out = {"requested_rounds": sorted(req_rounds), "registered_scope": FULL_SCOPE, "relation": rel,
           "zero_regression_applicable": rel == "full",
           "landing_reading": face_readings(landing) if landing else None,
           "registry_readings": (registry or {}).get("expected")}
    if rel == "full":
        out["zero_regression_verdict"] = ("match" if out["landing_reading"]["match"] else "mismatch")
    elif rel == "partial":
        out["zero_regression_verdict"] = "not_applicable(partial_scope)"
        out["note"] = ("单窗集读法: 器具零回归面钉在全 scope，本请求只覆盖子集 ⇒ 该面 False 不得读作回归"
                       "（R598 checks_posthoc 的同源伪影）")
    else:
        out["zero_regression_verdict"] = "blocked(unregistered_scope)"
    if recompute_full is not None:
        exp = (registry or {}).get("expected") or {}
        got = recompute_full.get("actual") or {}
        out["full_scope_recompute"] = {"match": bool(exp and got == exp), "expected": exp, "actual": got,
                                       "reads": recompute_full}
    rc = 3 if rel == "unregistered" else (0 if (out["zero_regression_verdict"] in
                                               ("match", "not_applicable(partial_scope)")) else 2)
    out["rc"] = rc
    return out


def shadow_selftest(landing):
    """影子自检: 四种形态各自的期望判决（不依赖真机）。"""
    res = {}
    res["partial_must_not_apply"] = judge(["r599"], landing, {"expected": {"buckets": {}, "layer": {}}})["zero_regression_applicable"] is False
    res["full_must_apply"] = judge(FULL_SCOPE, landing, {"expected": {"buckets": {}, "layer": {}}})["zero_regression_applicable"] is True
    res["unregistered_must_block"] = judge(["r599", "r777"], landing, {})["rc"] == 3
    # 注入读数漂移: 期望 vs 实际不同 ⇒ 必须报 mismatch（防恒真门）
    fake = {"zero_regression": {"match": False, "expected": {"buckets": {"A": 1}, "layer": {}},
                                "actual": {"buckets": {"A": 2}, "layer": {}}}}
    res["drift_must_report_mismatch"] = judge(FULL_SCOPE, fake, {"expected": {"buckets": {"A": 1}, "layer": {}}})[
        "zero_regression_verdict"] == "mismatch"
    res["all_pass"] = all(res.values())
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--landing", default=os.path.join(REPO, "eval/rover/r599/landing-predicate-r599.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r599/scope-bind-r599.json"))
    ap.add_argument("--predicate", default=os.path.join(REPO, "eval/rover/r593/landing_predicate_r593.py"))
    ap.add_argument("--recompute-full", action="store_true")
    ap.add_argument("--recompute-json", default="", metavar="PATH",
                    help="复用**已落盘**的全 scope 复算件（省一次 22min 复算；与 --recompute-full 二选一）")
    a = ap.parse_args()
    if not os.path.exists(a.landing):
        print("[fail-closed] 缺 landing 读数 %s" % a.landing)
        return 3
    landing = rd(a.landing)
    registry = rd(REGISTRY) if os.path.exists(REGISTRY) else None
    if registry is None:
        print("[fail-closed] 缺登记件 %s" % REGISTRY)
        return 3
    req = landing.get("scope", {}).get("rounds") or []
    recompute = None
    if a.recompute_json:
        # 复用已落盘的全 scope 复算件（契约修正: 登记件 r592 **不含** `zero_regression` 键 ⇒ 不得据其 `expected` 判中性；
        # 权威读法 = 器具自身 `zero_regression.match` ∧ 与 R598 在盘全 scope 件 `actual` 逐位比对（两条独立路径））
        j = rd(a.recompute_json)
        hist = rd(os.path.join(REPO, "eval/rover/r598/landing-hist-r598.json"))
        zr = (j.get("zero_regression") or {})
        hzr = (hist.get("zero_regression") or {})
        recompute = {"source": a.recompute_json, "device_internal_match": zr.get("match"),
                     "actual": zr.get("actual"),
                     "cross_check_against_r598_hist": {"path": "eval/rover/r598/landing-hist-r598.json",
                                                       "match": zr.get("actual") == hzr.get("actual"),
                                                       "hist_actual": hzr.get("actual")},
                     "scope": j.get("scope")}
    elif a.recompute_full:
        tmp = os.path.join(tempfile.mkdtemp(prefix="sb599-"), "full.json")
        r = subprocess.run([sys.executable, a.predicate, "--out", tmp, "--rounds", ",".join(FULL_SCOPE),
                            "--codex-too"], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(tmp):
            j = rd(tmp)
            recompute = {"actual": (j.get("zero_regression") or {}).get("actual"),
                         "match": (j.get("zero_regression") or {}).get("match"),
                         "scope": j.get("scope")}
        else:
            recompute = {"actual": None, "match": None, "rc": r.returncode, "stderr_tail": r.stderr[-200:]}
    verdict = judge(req, landing, registry, recompute)
    ctl = shadow_selftest(landing)
    posthoc = {
        "note": "预注册 C13 分类面缺「新轮集（与登记 scope **不相交**）」一类 ⇒ 本轮按预注册原样判 BLOCKED(rc=3)；"
                "正确形态单列于此，留 R600 预注册（判据不得事后改）。",
        "corrected_classification": "request ⊂ registry ⇒ not_applicable(partial_scope) ; "
                                    "request ∩ registry = ∅（新轮集） ⇒ not_applicable(out_of_registered_scope) ; "
                                    "request 混合已登记与未登记轮 ⇒ blocked(mixed_scope) rc=3",
        "instrument_read_defect": "首版读法把登记件（r592）当含 `expected` 键 ⇒ 读到空 dict ⇒ 中性证明恒否（假红）。"
                                  "修正 = 读器具自身 `zero_regression.match` + 与 R598 在盘件 `actual` 交叉比对。",
    }
    out = {"round": "R599", "purpose": "候选④-b landing 零回归面 scope 绑定机检（读法伪影消除）",
           "instrument": {"path": os.path.abspath(__file__), "registry": REGISTRY,
                          "registered_scope": FULL_SCOPE, "shared_predicate_edited": False},
           "landing_scope": landing.get("scope"), "controls": ctl,
           "full_scope_recompute": recompute, "checks_posthoc": posthoc,
           "judgment": verdict,
           "rc": 0 if (ctl["all_pass"] and verdict["rc"] == 0) else (3 if verdict["rc"] == 3 else 2)}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("[scope-bind] 请求=%s relation=%s 面判定=%s 全scope复算=%s 影子自检=%s ⇒ rc=%d"
          % (verdict["requested_rounds"] or req, verdict["relation"], verdict["zero_regression_verdict"],
             (out["full_scope_recompute"] or {}).get("match"), ctl["all_pass"], out["rc"]))
    return 0 if out["rc"] == 0 else out["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
