#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R591 候选② — wythoff 失分**只读定因**: 「落点/选择谓词层」vs「冷集构造层」。

动因: §12.2 的失效份额里 `MOVE_NOT_COLD` 占 67/131 (51%)，但该分类**不能**区分两种机理:
  (a) **落点/选择谓词层** —— 产物对「冷集」的认知与真值一致，但选出的落点不是冷点
      （例: 先把候选着法排序错 / 只在部分着法上做冷集判定 / 落点谓词取反）。
  (b) **冷集构造层** —— 产物自身声明的 P-位置集合与真值冷集不同（公式/递推写错）。

方法（两路独立读数, 均只读、对**副本**执行）:
  ① **例级重放**: 15 条 wythoff 冻结用例（`eval/rover/r591/cases/cases-r521.json`）→ 例级 got/exp,
     分类器 **import** `eval/rover/r562/wythoff_cause_r562.py`（禁重写第二份）。
  ② **全网格行为探针**: 位置 (a,b), 0≤a≤b≤25 逐个喂 stdin → 产物自报的「冷集」`C_prod`
     = {p : 产物不输出 WIN}；与独立 oracle 冷集 `C_true`（暴力递推 ∧ phi 序交叉校验, 同 import）比。
  判别规则（预注册 C8）:
     · `C_prod == C_true` 而该跑次 wythoff 仍失分 ⇒ 层 (a)（落点/选择谓词）
     · `C_prod != C_true` ⇒ 层 (b)（冷集构造）；其失分例若**落点仍落在 C_prod 内** ⇒ 同样是 (b)
     · 落点 ∉ `C_prod`（违反自身声明）⇒ 层 (a)（落点谓词松）, 与 C_prod 是否等于 C_true 无关
  成对控制: POS（正确冷集 + 故意选非冷落点）必须判 (a)；NEG（冷集删一个位置）必须判 (b)；
            防恒真: 必须观测到 `C_prod == C_true` 的跑次（否则判据退化为恒真门）。

用法: python3 eval/rover/r591/landing_predicate_r591.py [--out ...] [--jobs 4] [--codex-too]
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

REPO = "/home/agentuser/AgentFramework"
CASES = os.path.join(REPO, "eval/rover/r591/cases/cases-r521.json")
SRC589 = os.path.join(REPO, "eval/rover/r589/pool_taskface_r589.py")
SRC562 = os.path.join(REPO, "eval/rover/r562/wythoff_cause_r562.py")
ROUNDS = ["r585", "r586", "r587", "r588"]
L = 25


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_one(tree, game, stdin, timeout=15):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run([sys.executable, "-B", "-m", "games", game], input=stdin,
                           capture_output=True, text=True, cwd=tree, env=env, timeout=timeout)
        return p.stdout, p.returncode
    except Exception as e:  # noqa: BLE001
        return "", -1


WIN_RE = re.compile(r"^WIN\s+(\d+)\s+(\d+)\s*$")


def probe_grid(tree, positions, jobs):
    """对 (a,b) 网格取产物输出 → {pos: ('WIN',i,j)|('NONWIN',None)}"""
    def one(p):
        a, b = p
        out, rc = run_one(tree, "wythoff", "%d %d\n" % (a, b), timeout=15)
        m = WIN_RE.match(out.strip())
        return p, (("WIN", int(m.group(1)), int(m.group(2))) if m else ("NONWIN", None, None)), rc, out.strip()[:40]
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(one, positions))


def discover(codex_too=False):
    runs = []
    for r in ROUNDS:
        root = os.path.join(REPO, "eval/rover", r, "snapshots")
        if not os.path.isdir(root):
            continue
        for win in sorted(os.listdir(root)):
            for sub in sorted(os.listdir(os.path.join(root, win))):
                if not codex_too and not sub.startswith("agentD"):
                    continue
                g1 = os.path.join(root, win, sub, "g1")
                if os.path.isdir(os.path.join(g1, "games")):
                    runs.append({"round": r, "win": win, "sub": sub, "src": g1})
    return runs


def synth_fixture(kind, dst):
    """合成控制夹具: POS = 冷集正确但落点选错; NEG = 冷集删一个位置."""
    if kind == "POS":
        cold_line = "    cold = _cold_positions(max(a, b))\n"
        pick = ("    for i in range(0, a + 1):\n"
                "        for j in range(0, b + 1):\n"
                "            if i == 0 and j == 0:\n"
                "                continue\n"
                "            if not (i == 0 or j == 0 or i == j):\n"
                "                continue\n"
                "            if (a - i, b - j) not in cold:\n"          # 落点谓词取反 ⇒ 层 (a)
                "                return 'WIN %d %d' % (i, j)\n"
                "    return 'LOSE'\n")
    else:
        cold_line = "    cold = _cold_positions(max(a, b))\n    cold.discard((3, 5))\n"   # 冷集错 ⇒ 层 (b)
        pick = ("    for i in range(0, a + 1):\n"
                "        for j in range(0, b + 1):\n"
                "            if i == 0 and j == 0:\n"
                "                continue\n"
                "            if not (i == 0 or j == 0 or i == j):\n"
                "                continue\n"
                "            if (a - i, b - j) in cold:\n"
                "                return 'WIN %d %d' % (i, j)\n"
                "    return 'LOSE'\n")
    body = ("def _cold_positions(n):\n"
            "    cold = {(0, 0)}\n    taken = {0}\n    i = 1\n    while True:\n"
            "        a = i\n        while a in taken:\n            a += 1\n        b = a + i\n"
            "        if b > n:\n            break\n        cold.add((a, b))\n        cold.add((b, a))\n"
            "        taken.add(a)\n        taken.add(b)\n        i += 1\n    return cold\n\n\n"
            "def solve(text):\n    a, b = map(int, text.split()[:2])\n" + cold_line + pick)
    os.makedirs(os.path.join(dst, "games"), exist_ok=True)
    with io.open(os.path.join(dst, "games", "__init__.py"), "w") as fh:
        fh.write("")
    with io.open(os.path.join(dst, "games", "wythoff.py"), "w") as fh:
        fh.write(body)
    with io.open(os.path.join(dst, "games", "__main__.py"), "w") as fh:
        fh.write("import sys\nfrom . import wythoff\nif __name__ == '__main__':\n"
                 "    print(wythoff.solve(sys.stdin.read()))\n")


def analyse_run(run, cases, ora, jobs, tmp):
    tree = os.path.join(tmp, "%s-%s-%s" % (run["round"], run["win"], run["sub"]))
    if os.path.isdir(tree):
        shutil.rmtree(tree)
    shutil.copytree(run["src"], tree)
    # ① 例级重放 (复用 r562 分类器)
    wy = [c for c in cases if c["game"] == "wythoff"]
    out = []
    for i, c in enumerate(wy):
        got, rc = run_one(tree, "wythoff", c["stdin"], timeout=60)
        cls, extra = ora["classify"](c, got, rc, ora["ora"])
        out.append({"idx": i, "stdin": c["stdin"].strip(), "exp": c["expected_stdout"].strip(),
                    "got": got.strip()[:40], "class": cls, "detail": extra})
    # ② 全网格探针 → 产物自报冷集
    positions = [(a, b) for a in range(0, L + 1) for b in range(a, L + 1)]
    grid = probe_grid(tree, positions, jobs)
    c_prod = set()
    weird = {}
    for p, res, rc, raw in grid:
        if res[0] == "NONWIN":
            c_prod.add(p)
        else:
            i, j = res[1], res[2]
            t = (max(p[0] - i, p[1] - j), min(p[0] - i, p[1] - j))
            weird[p] = t                     # 产物声明的落点
    c_true = {p for p in ora["ora"]["cold"] if max(p) <= L}
    only_prod = sorted(c_prod - c_true)
    only_true = sorted(c_true - c_prod)
    set_equal = (c_prod == c_true)
    # 逐失败例归属
    buckets, detail = {}, []
    for x in out:
        if x["class"] == "OK":
            continue
        b = None
        if x["class"] in ("MOVE_NOT_COLD",):
            m = re.search(r"target\((\d+),\s*(\d+)\)", x["detail"] or "")
            t = (int(m.group(1)), int(m.group(2))) if m else None
            if t is not None:
                if t not in c_prod:
                    b = "A_landing_loose"      # 落点违反自身声明 ⇒ 层 (a)
                else:
                    b = "B_coldset"            # 落点 = 它自己声称的冷点 ⇒ 层 (b)
        elif x["class"] in ("LOSE_FOR_WIN", "WIN_FOR_LOSE"):
            a, bb = [int(v) for v in x["stdin"].split()]
            p = (max(a, bb), min(a, bb))
            b = "B_coldset" if set_equal is False else "A_landing_loose"
        elif x["class"] in ("MOVE_NOT_LEXMIN",):
            b = "A_selection_order"
        else:
            b = "D_delivery_or_shape"          # EMPTY_OR_ERROR / MOVE_SHAPE / MOVE_ILLEGAL / LOSE_LABEL_MISMATCH
        buckets[b] = buckets.get(b, 0) + 1
        detail.append({"idx": x["idx"], "stdin": x["stdin"], "exp": x["exp"], "got": x["got"],
                       "class": x["class"], "detail": x["detail"], "bucket": b})
    return {"round": run["round"], "win": run["win"], "sub": run["sub"],
            "cases_pass_wythoff": sum(1 for x in out if x["class"] == "OK"), "cases_n": len(out),
            "cold_set_equal": bool(set_equal),
            "cold_only_prod": [list(p) for p in only_prod], "cold_only_true": [list(p) for p in only_true],
            "declared_targets_n": len(weird),
            "buckets": buckets, "failures": detail,
            "layer": ("(a) 落点/选择谓词层" if set_equal else "(b) 冷集构造层"),
            "layer_evidence": ("C_prod == C_true (%d 位置) 而仍失分" % len(c_true)) if set_equal
            else ("C_prod != C_true: 仅产物 %d / 仅真值 %d" % (len(only_prod), len(only_true)))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r591/landing-predicate-r591.json"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--codex-too", action="store_true")
    ap.add_argument("--rounds", default=",".join(ROUNDS),
                    help="窗集范围内的轮号（逗号分隔）；默认 = 模块常量（第一窗集 r585-588）")
    a = ap.parse_args()
    globals()["ROUNDS"] = [x.strip() for x in a.rounds.split(",") if x.strip()]
    m589, m562 = load(SRC589, "pool589"), load(SRC562, "we562")
    cases = json.load(io.open(CASES, encoding="utf-8"))
    ora = m562.build_oracle(cases)
    assert ora["fixture_agrees"], "冻结夹具与独立 oracle 不一致 ⇒ 夹具缺陷, 停"
    # 分类器适配 (r562: classify(case, got, rc, ora) 需要 {'cold','lexmin'})
    ora["classify"] = m562.classify
    ora["ora"] = {"cold": ora["cold"], "lexmin": ora["lexmin"]}
    # 成对控制: POS / NEG 合成夹具
    tmp = tempfile.mkdtemp(prefix="r591lp-")
    ctrl = {}
    for kind in ("POS", "NEG"):
        d = os.path.join(tmp, "ctrl-" + kind)
        synth_fixture(kind, d)
        r = analyse_run({"round": "ctrl", "win": "ctrl", "sub": kind, "src": d}, cases, ora, a.jobs, tmp)
        ctrl[kind] = {"cold_set_equal": r["cold_set_equal"], "layer": r["layer"],
                      "cold_only_prod": r["cold_only_prod"], "buckets": r["buckets"]}
    runs = discover(codex_too=a.codex_too)
    res = []
    for r in runs:
        try:
            res.append(analyse_run(r, cases, ora, a.jobs, tmp))
        except Exception as e:  # noqa: BLE001
            res.append({"round": r["round"], "win": r["win"], "sub": r["sub"], "err": "%s: %s" % (type(e).__name__, str(e)[:120])})
    ok = [r for r in res if "err" not in r]
    agg_b = {}
    for r in ok:
        for k, v in r["buckets"].items():
            agg_b[k] = agg_b.get(k, 0) + v
    lyr = {}
    for r in ok:
        lyr[r["layer"]] = lyr.get(r["layer"], 0) + 1
    has_true_equal = any(r["cold_set_equal"] for r in ok)
    ctrl_ok = (ctrl["POS"]["cold_set_equal"] is True and ctrl["NEG"]["cold_set_equal"] is False)
    nc = {"POS_expect_layer_a": ctrl["POS"]["layer"].startswith("(a)"),
          "NEG_expect_layer_b": ctrl["NEG"]["layer"].startswith("(b)"),
          "pair_pass": bool(ctrl_ok and ctrl["POS"]["layer"].startswith("(a)") and ctrl["NEG"]["layer"].startswith("(b)")),
          "anti_constant_gate": has_true_equal,
          "has_teeth": bool(ctrl_ok and has_true_equal)}
    shares = {k: round(v / max(1, sum(agg_b.values())), 4) for k, v in agg_b.items()}
    out = {"round": "R591", "criterion": "C8 候选② 落点谓词 vs 冷集构造（只读定因）",
           "instrument": {"path": __file__, "logic_source_562": SRC562, "runs_analysed": len(ok),
                          "runs_total": len(res), "grid_L": L, "positions": (L + 1) * (L + 2) // 2,
                          "oracle": {"phi_vs_brute_equal": ora["phi_vs_brute_equal"],
                                     "fixture_agrees": ora["fixture_agrees"], "cold_n": len(ora["cold"])}},
           "controls": ctrl, "negative_control": nc,
           "layer_by_run": lyr, "bucket_totals": agg_b, "bucket_shares": shares,
           "runs": res,
           "verdict": {"main_cause": max(shares, key=shares.get) if shares else None,
                       "rule": "份额 ≥50% 者记主因; 层 (a)/(b) 由 C_prod == C_true 机械决定（非人工口径）",
                       "rc": 0 if nc["has_teeth"] else 2}}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("== R591 候选② 定因 ==")
    print("跑次: %d/%d (err=%d) | 夹具 oracle 一致=%s" % (len(ok), len(res), len(res) - len(ok), ora["fixture_agrees"]))
    print("成对控制: POS=%s NEG=%s 有牙=%s 防恒真=%s" % (ctrl["POS"]["layer"], ctrl["NEG"]["layer"], nc["pair_pass"], nc["anti_constant_gate"]))
    print("层分布(跑次): %s" % json.dumps(lyr, ensure_ascii=False))
    print("失败例次分桶: %s" % json.dumps(agg_b, ensure_ascii=False))
    print("份额: %s | 主因=%s rc=%d" % (json.dumps(shares, ensure_ascii=False), out["verdict"]["main_cause"], out["verdict"]["rc"]))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
