#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R593 — wythoff 失分只读定因器 **v3**（只加读数面：D 桶机械细分 + codex 侧对照 + V_int 落分布）。

承 R592 v2（`eval/rover/r592/landing_predicate_r592.py`，rc=0 / has_teeth=true）：
v3 **import v2 的 helpers**（`canon` / `legal_moves` / `run_one` / `probe_grid` / `synth_fixture`
/ `audit_strays` / `sha_tree` / `WIN_RE` / `L_over`），**禁重写第二份**；只新增三处读数面：

  ① **D 桶机械细分**（候选②）：`D_delivery_or_shape` 原为 catch-all（4 个语义类折进一桶）
     ⇒ 细分 `D1_empty_or_error / D2_move_shape / D3_move_illegal / D4_label_mismatch
     / D5_win_unparseable / D6_other`，并把 `D1` 再按**原因**二分（`nonzero_rc` vs `empty_body`）。
     **A/B 级桶定义逐字不变**（可比）；守恒式 `Σ D_sub == D_total`（细分不得吞并条目）。
  ② **codex 侧跑次**（候选③）：`--codex-too` 把同 15 窗的 `codex` 跑次纳入同器具同口径，
     两侧**并列不相同减**（分母各自侧）。
  ③ **V_int 分布**（候选④）：只出直方图，**不设阈值、不分层、不作触发**（预注册禁止）。

控制（成对、行为可分；预注册 C1）：`OK / POS / NEG`（承 v2）+ 新增 5 件 D 控制
`D_EMPTY / D_RC / D_SHAPE / D_ILLEGAL / D_LABEL` —— 8 件必须**落点唯一**（(桶, 原因) 签名互异）。
**旧粒度对照臂**：同 5 件 D 控制在 v2 的单一 `D_delivery_or_shape` 粒度下必须**全部折进同一桶**
⇒ 互异 = 1 ⇒ 无牙（证明细分有分辨率，不是装饰）。

rc 语义（fail-closed，编码验收面）：0 = 器具可用 / 2 = 器具缺陷（控制无牙·串桶 / 守恒破 / 残留 / 只读破）
/ 3 = 输入缺失或环境失败。**不放宽任何阈值、不事后调判据。**

用法:
  python3 eval/rover/r593/landing_predicate_r593.py [--codex-too] [--out ...] [--jobs 8] [--controls-only]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
LP592 = os.path.join(REPO, "eval/rover/r592/landing_predicate_r592.py")
SRC562 = os.path.join(REPO, "eval/rover/r562/wythoff_cause_r562.py")
CASES = os.path.join(REPO, "eval/rover/r591/cases/cases-r521.json")
R592_READING = os.path.join(REPO, "eval/rover/r592/landing-predicate-r592.json")
ROUNDS = ["r585", "r586", "r587", "r588", "r591"]
CASE_TIMEOUT = 60
GRID_TIMEOUT = 10


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


v2 = load(LP592, "lp592")          # helpers 一律复用 v2（禁重写第二份）
L = v2.L

D_SUBS = ["D1_empty_or_error", "D2_move_shape", "D3_move_illegal",
          "D4_label_mismatch", "D5_win_unparseable", "D6_other"]
AB_BUCKETS = ["A_landing_loose", "A_selection_order", "B_coldset"]

# ---------------------------------------------------------------- D 细分（机械、无自由度）
def d_sub(klass, got, rc):
    """r592 桶 == D 的记录 → 细分（只看 class + 形态 + rc，无阈值）。"""
    if klass == "EMPTY_OR_ERROR":
        return "D1_empty_or_error"
    if klass == "MOVE_SHAPE":
        return "D2_move_shape"
    if klass == "MOVE_ILLEGAL":
        return "D3_move_illegal"
    if klass == "LOSE_LABEL_MISMATCH":
        return "D4_label_mismatch"
    if klass == "WIN_FOR_LOSE":
        return "D5_win_unparseable" if not v2.WIN_RE.match((got or "").strip()) else "D6_other"
    return "D6_other"


def d1_reason(got, rc):
    """D1 的**原因**二分：进程非零退出 vs 空正文（交付形态 vs 崩溃面）。"""
    return "nonzero_rc" if rc != 0 else "empty_body"


# ---------------------------------------------------------------- D 控制夹具（行为可分）
def synth_d_fixture(kind, dst):
    os.makedirs(os.path.join(dst, "games"), exist_ok=True)
    io.open(os.path.join(dst, "games", "__init__.py"), "w").close()
    head = (v2.FIX_BODY["mex"] + v2.LEX +
            "def _solve(a, b):\n"
            "    cold = _cold_positions(max(a, b))\n"
            "    mv = [(k, 0) for k in range(1, a + 1)] + [(0, k) for k in range(1, b + 1)] + "
            "[(k, k) for k in range(1, min(a, b) + 1)]\n"
            "    return _pick(a, b, cold, mv), cold\n\n\n") if kind in ("D_SHAPE", "D_ILLEGAL", "D_LABEL") else ""
    if kind == "D_EMPTY":
        body = head + "def solve(text):\n    return ''\n"
    elif kind == "D_RC":
        body = head + "def solve(text):\n    return ''\n"
    elif kind == "D_SHAPE":
        body = (head + "def solve(text):\n    a, b = map(int, text.split()[:2])\n"
                "    p, cold = _solve(a, b)\n    return 'WIN' if p is not None else 'LOSE'\n")
    elif kind == "D_ILLEGAL":
        body = (head + "def solve(text):\n    a, b = map(int, text.split()[:2])\n"
                "    p, cold = _solve(a, b)\n    return 'WIN 1 2' if p is not None else 'LOSE'\n")
    else:  # D_LABEL: LOSE 支改词标（非 WIN、与期望不符）
        body = (head + "def solve(text):\n    a, b = map(int, text.split()[:2])\n"
                "    p, cold = _solve(a, b)\n    return ('WIN %d %d' % p) if p is not None else 'NONE'\n")
    with io.open(os.path.join(dst, "games", "wythoff.py"), "w") as fh:
        fh.write(body)
    main = "import sys\nfrom . import wythoff\nif __name__ == '__main__':\n"
    if kind == "D_RC":
        main += "    sys.stdin.read()\n    sys.exit(3)\n"      # 非零退出 + 空正文
    else:
        main += "    print(wythoff.solve(sys.stdin.read()))\n"
    with io.open(os.path.join(dst, "games", "__main__.py"), "w") as fh:
        fh.write(main)


def synth_control(kind, dst):
    if kind in ("OK", "POS", "NEG"):
        v2.synth_fixture(kind, dst)
    else:
        synth_d_fixture(kind, dst)


# ---------------------------------------------------------------- 单跑次分析（v2 逻辑 + 新增读数面）
def analyse_run(run, cases, ora, jobs, tmp, side):
    from concurrent.futures import ThreadPoolExecutor  # noqa: F401  (v2.probe_grid 内部自持)
    tree = os.path.join(tmp, "run-%s-%s-%s" % (run["round"], run["win"], run["sub"]))
    if os.path.isdir(tree):
        shutil.rmtree(tree)
    shutil.copytree(run["src"], tree)
    wy = [c for c in cases if c["game"] == "wythoff"]
    out = []
    for i, c in enumerate(wy):
        got, rc = v2.run_one(tree, "wythoff", c["stdin"], CASE_TIMEOUT)
        cls, extra = ora["classify"](c, got, rc, ora["ora"])
        out.append({"idx": i, "stdin": c["stdin"].strip(), "exp": c["expected_stdout"].strip(),
                    "got": got.strip()[:40], "class": cls, "detail": extra, "rc": rc})
    positions = [(a, b) for a in range(0, L + 1) for b in range(a, L + 1)]
    grid = v2.probe_grid(tree, positions, jobs)
    c_prod, n_win, n_err = set(), 0, 0
    win_moves = {}
    for p, res, rc, _raw in grid:
        if res[0] == "LOSE":
            c_prod.add(p)
        elif res[0] == "WIN":
            n_win += 1
            win_moves[p] = (res[1], res[2], v2.canon((p[0] - res[1], p[1] - res[2])))
        else:
            n_err += 1
    c_true = {v2.canon(p) for p in ora["cold"] if max(p) <= L}
    only_prod = sorted(c_prod - c_true)
    only_true = sorted(c_true - c_prod)
    set_equal = (c_prod == c_true)
    v_land = []
    for p, (i, j, t) in sorted(win_moves.items()):
        if (i, j) == (0, 0) or i < 0 or j < 0:
            continue
        if not ((i > 0 and j == 0) or (i == 0 and j > 0) or (i == j)):
            continue
        if t not in c_prod:
            v_land.append({"pos": list(p), "move": [i, j], "target": list(t)})
    v_int = []
    for p in sorted(c_prod):
        for (i, j) in v2.legal_moves(p[0], p[1]):
            if v2.canon((p[0] - i, p[1] - j)) in c_prod:
                v_int.append({"pos": list(p), "target": list(v2.canon((p[0] - i, p[1] - j)))})
                break
    layer = ("(a) 落点/选择谓词层" if v_land else
             ("(b) 冷集构造层" if not set_equal else "(c) 本轴外"))
    buckets, d_subs, d1s, detail = {}, {}, {}, []
    for x in out:
        if x["class"] == "OK":
            continue
        if x["class"] == "MOVE_NOT_COLD":
            m = re.search(r"target\((\d+),\s*(\d+)\)", x["detail"] or "")
            t = v2.canon((int(m.group(1)), int(m.group(2)))) if m else None
            b = "A_landing_loose" if (t is not None and t not in c_prod) else "B_coldset"
        elif x["class"] == "WIN_FOR_LOSE":
            a0, b0 = [int(v) for v in x["stdin"].split()]
            gm = v2.WIN_RE.match(x["got"])
            if gm:
                t = v2.canon((a0 - int(gm.group(1)), b0 - int(gm.group(2))))
                b = "B_coldset" if t in c_prod else "A_landing_loose"
            else:
                b = "D_delivery_or_shape"
        elif x["class"] == "LOSE_FOR_WIN":
            b = "B_coldset"
        elif x["class"] == "MOVE_NOT_LEXMIN":
            b = "A_selection_order"
        else:
            b = "D_delivery_or_shape"
        buckets[b] = buckets.get(b, 0) + 1
        rec = dict(x, bucket=b)
        if b == "D_delivery_or_shape":
            ds = d_sub(x["class"], x["got"], x["rc"])
            rec["d_sub"] = ds
            d_subs[ds] = d_subs.get(ds, 0) + 1
            if ds == "D1_empty_or_error":
                r = d1_reason(x["got"], x["rc"])
                rec["d1_reason"] = r
                d1s[r] = d1s.get(r, 0) + 1
        detail.append(rec)
    fail_total = sum(buckets.values())
    d_total = buckets.get("D_delivery_or_shape", 0)
    return {"round": run["round"], "win": run["win"], "sub": run["sub"], "side": side,
            "cases_pass_wythoff": sum(1 for x in out if x["class"] == "OK"), "cases_n": len(out),
            "cases_rc_nonzero": sum(1 for x in out if x["rc"] != 0),
            "declared_cold_n": len(c_prod), "grid_win_n": n_win, "grid_err_n": n_err,
            "cold_set_equal": bool(set_equal),
            "cold_only_prod": [list(p) for p in only_prod], "cold_only_true": [list(p) for p in only_true],
            "v_land_n": len(v_land), "v_int_n": len(v_int), "v_int_samples": v_int[:5],
            "layer": layer, "buckets": buckets, "d_subs": d_subs, "d1_reason": d1s,
            "fail_total": fail_total, "d_total": d_total,
            "conservation": (sum(d_subs.values()) == d_total),
            "failures": detail}


def agg(runs, side):
    runs = [r for r in runs if r.get("side") == side and "err" not in r]
    b, d, d1, lyr, viol, vih, cases_ok, cases_n = {}, {}, {}, {}, {}, {}, 0, 0
    for r in runs:
        for k, v in r["buckets"].items():
            b[k] = b.get(k, 0) + v
        for k, v in r["d_subs"].items():
            d[k] = d.get(k, 0) + v
        for k, v in r["d1_reason"].items():
            d1[k] = d1.get(k, 0) + v
        lyr[r["layer"]] = lyr.get(r["layer"], 0) + 1
        viol[r["v_int_n"]] = viol.get(r["v_int_n"], 0) + 1
        vih[str(r["v_int_n"])] = vih.get(str(r["v_int_n"]), 0) + 1
        cases_ok += r["cases_pass_wythoff"]
        cases_n += r["cases_n"]
    fail_total = sum(b.values())
    shares = {k: round(v / max(1, fail_total), 4) for k, v in b.items()}
    dshares = {k: round(v / max(1, sum(d.values())), 4) for k, v in sorted(d.items())}
    return {"runs": len(runs), "cases_pass": cases_ok, "cases_n": cases_n,
            "fail_total": fail_total, "buckets": b, "bucket_shares": shares,
            "d_subs": d, "d_sub_shares": dshares, "d1_reason": d1,
            "layer": lyr, "v_int_hist": vih,
            "d_total": b.get("D_delivery_or_shape", 0),
            "conservation": (sum(d.values()) == b.get("D_delivery_or_shape", 0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r593/landing-predicate-r593.json"))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--rounds", default=",".join(ROUNDS))
    ap.add_argument("--codex-too", action="store_true")
    ap.add_argument("--controls-only", action="store_true")
    a = ap.parse_args()
    rounds = [x.strip() for x in a.rounds.split(",") if x.strip()]
    m562 = load(SRC562, "we562")
    cases = json.load(io.open(CASES, encoding="utf-8"))
    ora_built = m562.build_oracle(cases)
    if not ora_built["fixture_agrees"]:
        raise SystemExit("冻结夹具与独立 oracle 不一致 ⇒ 夹具缺陷, 停")
    ora = {"cold": ora_built["cold"], "lexmin": ora_built["lexmin"],
           "fixture_agrees": ora_built["fixture_agrees"], "classify": m562.classify,
           "ora": {"cold": ora_built["cold"], "lexmin": ora_built["lexmin"]}}
    strays_before = v2.audit_strays()
    tmp = tempfile.mkdtemp(prefix="r593lp-")
    plan = v2.discover(rounds, include_codex=True) if a.codex_too else v2.discover(rounds)
    pre_sha = {r["round"] + "/" + r["win"] + "/" + r["sub"]: v2.sha_tree(r["src"]) for r in plan}
    pre_sha["cases-r521.json"] = hashlib.sha256(open(CASES, "rb").read()).hexdigest()
    src_probe = os.path.join(REPO, "src")
    src_pre = v2.sha_tree(src_probe) if os.path.isdir(src_probe) else None

    # ---- 控制面（8 件；落点唯一 = (桶, 原因) 签名互异）
    KINDS = ["OK", "POS", "NEG", "D_EMPTY", "D_RC", "D_SHAPE", "D_ILLEGAL", "D_LABEL"]
    ctrl = {}
    for kind in KINDS:
        d = os.path.join(tmp, "ctrl-" + kind)
        synth_control(kind, d)
        r = analyse_run({"round": "ctrl", "win": "ctrl", "sub": kind, "src": d}, cases, ora, a.jobs, tmp, "ctrl")
        ctrl[kind] = {"layer": r["layer"], "cold_set_equal": r["cold_set_equal"], "v_land_n": r["v_land_n"],
                      "v_int_n": r["v_int_n"], "declared_cold_n": r["declared_cold_n"],
                      "grid_err_n": r["grid_err_n"], "cases_pass_wythoff": r["cases_pass_wythoff"],
                      "cases_n": r["cases_n"], "buckets": r["buckets"], "d_subs": r["d_subs"],
                      "d1_reason": r["d1_reason"], "fail_total": r["fail_total"]}
    ok_ok = (ctrl["OK"]["cold_set_equal"] and ctrl["OK"]["v_land_n"] == 0
             and ctrl["OK"]["cases_pass_wythoff"] == ctrl["OK"]["cases_n"])
    pos_a = ctrl["POS"]["layer"].startswith("(a)")
    neg_b = ctrl["NEG"]["layer"].startswith("(b)")

    # 新粒度签名 = (桶, 子桶[, 原因])；8 件必须互异
    def sig(kind):
        c = ctrl[kind]
        if kind in ("OK", "POS", "NEG"):
            return ("LAYER", c["layer"])
        sub = max(c["d_subs"], key=lambda k: c["d_subs"][k]) if c["d_subs"] else None
        reason = (max(c["d1_reason"], key=lambda k: c["d1_reason"][k])
                  if sub == "D1_empty_or_error" and c["d1_reason"] else None)
        return ("D", sub, reason)
    sigs = {k: sig(k) for k in KINDS}
    # 唯一落点：5 件 D 控制签名互异（且每件只落一个子桶）
    d_kinds = [k for k in KINDS if k.startswith("D_")]
    d_sigs = [sigs[k] for k in d_kinds]
    d_unique = (len(set(d_sigs)) == len(d_sigs))
    d_single = all(len(ctrl[k]["d_subs"]) == 1 for k in d_kinds)
    # 声明命中：D_EMPTY→D1(empty_body) / D_RC→D1(nonzero_rc) / D_SHAPE→D2 / D_ILLEGAL→D3 / D_LABEL→D4
    declared = {"D_EMPTY": ("D1_empty_or_error", "empty_body"), "D_RC": ("D1_empty_or_error", "nonzero_rc"),
                "D_SHAPE": ("D2_move_shape", None), "D_ILLEGAL": ("D3_move_illegal", None),
                "D_LABEL": ("D4_label_mismatch", None)}
    declared_ok = all(sigs[k][1] == declared[k][0] and (declared[k][1] is None or sigs[k][2] == declared[k][1])
                      for k in d_kinds)
    has_teeth = bool(ok_ok and pos_a and neg_b and d_unique and d_single and declared_ok)
    # 旧粒度对照臂：5 件 D 控制在 v2 单一 catch-all 下的签名（全部 = D_delivery_or_shape）
    old_sigs = {k: ("D", "D_delivery_or_shape") for k in d_kinds}
    old_unique = len(set(old_sigs.values()))
    has_teeth_old = bool(old_unique >= 2)          # 旧粒度必然 false

    ctrl_forms = {}
    for k in KINDS:
        key = "%s|v_land>0=%s" % ("equal" if ctrl[k]["cold_set_equal"] else "diff", ctrl[k]["v_land_n"] > 0)
        ctrl_forms[key] = ctrl_forms.get(key, 0) + 1
    non_trivial_ctrl = len(ctrl_forms) >= 2

    # ---- 真实跑次面
    res = []
    if not a.controls_only:
        for r in plan:
            side = "codex" if r["sub"] == "codex" else "agent"
            try:
                res.append(analyse_run(r, cases, ora, a.jobs, tmp, side))
            except Exception as e:  # noqa: BLE001
                res.append({"round": r["round"], "win": r["win"], "sub": r["sub"], "side": side,
                            "err": "%s: %s" % (type(e).__name__, str(e)[:120])})
    ok = [r for r in res if "err" not in r]
    ag_agent = agg(res, "agent")
    ag_codex = agg(res, "codex")
    forms = {}
    for r in ok:
        key = "%s|v_land>0=%s" % ("equal" if r["cold_set_equal"] else "diff", r["v_land_n"] > 0)
        forms[key] = forms.get(key, 0) + 1
    non_trivial_runs = (a.controls_only or len(forms) >= 2)
    # 守恒（逐跑次 + 全量；controls-only 模式下轮次面为空 ⇒ 以控制面守恒为准，不把「无跑次」读成器具坏）
    conservation_ctrl = all(sum(ctrl[k]["d_subs"].values()) == ctrl[k]["buckets"].get("D_delivery_or_shape", 0)
                            for k in d_kinds)
    conservation_runs = (all(r["conservation"] for r in ok) and ag_agent["conservation"]
                         and ag_codex["conservation"]) if ok else bool(a.controls_only)
    conservation = bool(conservation_ctrl and conservation_runs)
    # 零回归：与 r592 登记值逐位比对（读盘，不硬编码）
    zero_reg = {"registered_from": R592_READING, "match": None, "expected": None, "actual": None,
                "note": "controls-only 模式轮次面为空 ⇒ 不评（不得读成失败）"}
    if os.path.isfile(R592_READING) and not a.controls_only:
        reg = json.load(io.open(R592_READING, encoding="utf-8"))
        exp_b = {k: reg["bucket_totals"].get(k, 0) for k in AB_BUCKETS}
        exp_l = reg["layer_by_run"]
        actual_b = {k: ag_agent["buckets"].get(k, 0) for k in AB_BUCKETS}
        zero_reg.update({"expected": {"buckets": exp_b, "layer": exp_l},
                         "actual": {"buckets": actual_b, "layer": ag_agent["layer"]},
                         "match": bool(exp_b == actual_b and exp_l == ag_agent["layer"])})
    strays_after = v2.audit_strays()
    post_sha = {k: (v2.sha_tree(os.path.join(REPO, "eval/rover", k.split("/")[0], "snapshots",
                                             k.split("/")[1], k.split("/")[2], "g1"))
                    if k != "cases-r521.json" else hashlib.sha256(open(CASES, "rb").read()).hexdigest())
                for k in pre_sha}
    src_post = v2.sha_tree(src_probe) if os.path.isdir(src_probe) else None
    readonly_ok = (pre_sha == post_sha and src_pre == src_post)

    rc = 0
    if not has_teeth or not non_trivial_ctrl or not non_trivial_runs:
        rc = 2
    elif not conservation:
        rc = 2
    elif zero_reg["match"] is False:
        rc = 2
    elif strays_after:
        rc = 2
    elif not readonly_ok:
        rc = 2
    elif not a.controls_only and (len(ok) == 0 or (a.codex_too and ag_codex["runs"] == 0)):
        rc = 3

    out = {"round": "R593",
           "instrument": {"path": __file__, "version": "v3",
                          "supersedes_criterion_readings": False,
                          "note": "A/B 级桶定义与 R592 逐字不变（零回归对照臂 C4）；只加 D 细分 / codex 面 / V_int 分布",
                          "imports": {"helpers_from": LP592, "oracle_and_classify": SRC562,
                                      "cases": CASES},
                          "v2_profile": os.path.isfile(R592_READING)},
           "scope": {"rounds": rounds, "codex_too": a.codex_too,
                     "runs_total": len(res), "runs_ok": len(ok),
                     "grid_L": L, "positions": (L + 1) * (L + 2) // 2,
                     "oracle": {"fixture_agrees": ora["fixture_agrees"]}},
           "controls": ctrl,
           "teeth": {"has_teeth": has_teeth, "OK_ok": ok_ok, "POS_layer_a": pos_a, "NEG_layer_b": neg_b,
                     "d_unique_landing": d_unique, "d_single_sub": d_single, "declared_ok": declared_ok,
                     "sigs_new": {k: list(v) for k, v in sigs.items()},
                     "old_granularity": {"sigs": {k: list(v) for k, v in old_sigs.items()},
                                         "distinct": old_unique, "has_teeth": has_teeth_old}},
           "non_trivial": {"ctrl_forms": ctrl_forms, "run_forms": forms,
                           "ctrl_ok": non_trivial_ctrl, "runs_ok": non_trivial_runs},
           "strays": {"before": strays_before, "after": strays_after},
           "readonly": {"pre": pre_sha, "post": post_sha, "src_pre": src_pre, "src_post": src_post,
                        "ok": readonly_ok},
           "conservation": conservation,
           "zero_regression": zero_reg,
           "agent": ag_agent, "codex": ag_codex,
           "compare": {"note": "两侧并列不相同减；分母 = 各自侧失败例次",
                       "bucket_share_diff": {k: (round(ag_agent["bucket_shares"].get(k, 0.0)
                                                      - ag_codex["bucket_shares"].get(k, 0.0), 4))
                                             for k in sorted(set(list(ag_agent["bucket_shares"])
                                                                 + list(ag_codex["bucket_shares"])))},
                       "d_sub_share_diff": {k: (round(ag_agent["d_sub_shares"].get(k, 0.0)
                                                      - ag_codex["d_sub_shares"].get(k, 0.0), 4))
                                            for k in sorted(set(list(ag_agent["d_sub_shares"])
                                                                + list(ag_codex["d_sub_shares"])))}},
           "runs": res,
           "verdict": {"rc": rc,
                       "d_main_sub": (max(ag_agent["d_subs"], key=lambda k: ag_agent["d_subs"][k])
                                      if ag_agent["d_subs"] else None),
                       "d_sub_resolution": (len([1 for v in ag_agent["d_subs"].values() if v > 0])),
                       "layer_rule": "(a) v_land>0 / (b) v_land==0 ∧ C_prod!=C_true / (c) 两者皆无"}}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("== R593 定因器 v3 ==")
    print("跑次 %d/%d (err=%d) | oracle 一致=%s | codex_too=%s"
          % (len(ok), len(res), len(res) - len(ok), ora["fixture_agrees"], a.codex_too))
    print("控制: OK=%s POS=%s NEG=%s | D 控制落点唯一=%s 单子桶=%s 声明命中=%s"
          % (ok_ok, ctrl["POS"]["layer"], ctrl["NEG"]["layer"], d_unique, d_single, declared_ok))
    print("旧粒度互异桶数=%d (has_teeth=%s) | 新粒度 has_teeth=%s" % (old_unique, has_teeth_old, has_teeth))
    print("签名: %s" % json.dumps({k: list(v) for k, v in sigs.items()}, ensure_ascii=False))
    print("守恒=%s | 零回归=%s | 残留 before=%d after=%d | 只读=%s"
          % (conservation, zero_reg["match"], len(strays_before), len(strays_after), readonly_ok))
    print("agent: runs=%d 桶=%s D子桶=%s" % (ag_agent["runs"], json.dumps(ag_agent["buckets"], ensure_ascii=False),
                                            json.dumps(ag_agent["d_subs"], ensure_ascii=False)))
    if a.codex_too:
        print("codex: runs=%d 桶=%s D子桶=%s" % (ag_codex["runs"], json.dumps(ag_codex["buckets"], ensure_ascii=False),
                                                 json.dumps(ag_codex["d_subs"], ensure_ascii=False)))
        print("份额差(agent−codex): %s" % json.dumps(out["compare"]["bucket_share_diff"], ensure_ascii=False))
    print("V_int 直方图 agent=%s codex=%s" % (json.dumps(ag_agent["v_int_hist"], ensure_ascii=False),
                                              json.dumps(ag_codex["v_int_hist"], ensure_ascii=False)))
    print("层分布 agent=%s codex=%s" % (json.dumps(ag_agent["layer"], ensure_ascii=False),
                                        json.dumps(ag_codex["layer"], ensure_ascii=False)))
    print("rc=%d" % rc)
    shutil.rmtree(tmp, ignore_errors=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
