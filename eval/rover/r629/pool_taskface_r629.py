#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R629 · 候选① 主体：**主判据池化器（窗名枚举参数化）** —— 判据 v3 的**主判据**在 w220+ 窗集上真正落地。

R628 自捕缺陷 ① 的三层根因（本轮行号级取证）：
  (i)  `eval/rover/r628/run_r628.sh` **从不调用** `pool_taskface_r628.py`（仅在第 12/27 行注释里提到）
       ⇒ 预注册声明的**主判据器具轮内零调用** ⇒ 主判据从未计算；
  (ii) 该器具复用 `eval/rover/r589/pool_taskface_r589.py::load_all`，其窗名枚举为
       `glob(base + "/w1*")` **硬编码前缀 `w1`** ⇒ 对 `w220..w222` 读 **0 窗 / 0 跑次**
       ⇒ `data_scope={windows:0,runs:0,products:0}` ∧ `C7 有牙=False`（变异无靶）
       ⇒ rc=3 BLOCKED（**分母归零 ⇒ 分辨力归零且静默**）；
  (iii) 记录判决 `rc=1 FAIL(质量配对未过)` 实由 `C1` 出，而 C1 自述「仅作同向参照、不出判决」
       ⇒ **判决面 ≠ 预注册主判据面**，且主判据实为「不可判」而非「未过」⇒ 判决方向错误。

本器具 = **只参数化窗名枚举**（唯一单变量），解析逻辑仍调用 r589 的 `read_run`（零逻辑复制）。
成对控制：
  C-A 等价性：legacy 枚举（`w1*`）vs derived 枚举，在 **set1（r585–r588）** 上必须**逐位相同**
              ⇒ 证明本轮唯一变量确为「窗名枚举」，不夹带读法改动。
  C-B 有牙  ：legacy 枚举在 **r628** 上 ⇒ `windows == 0`（复现 R628 的 rc=3 静默弃权）；
              derived 枚举在 r628 上 ⇒ `windows == 3 ∧ runs == 12`（主判据真正落地）。

退出码：0 = 读数齐备；2 = 成对控制不成立（器具缺陷）；3 = 输入缺失。
"""

import argparse
import glob
import hashlib
import importlib.util
import io
import json
import os
import statistics
import sys

RUNS = os.path.expanduser("~/.agentframework/harness/runs")
SRC_REL = "eval/rover/r589/pool_taskface_r589.py"


def _repo_root(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.isdir(os.path.join(p, "eval", "rover")) and os.path.isdir(os.path.join(p, "src")):
            return p
        p = os.path.dirname(p)
    raise SystemExit("INPUT_MISSING repo root")


REPO = _repo_root(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, SRC_REL)


def load_src():
    spec = importlib.util.spec_from_file_location("pool589_shared", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def enumerate_windows(base, mode):
    """窗名枚举 —— **唯一单变量**。

    mode='legacy' : 逐字复刻 r589 的 `glob(base + "/w1*")`（硬编码前缀）。
    mode='derived': 目录派生 —— 只收「含 `<arm>/g1/cases.txt` 的子目录」，
                    前缀与编号宽度一律不设假设（禁 `w1*` 式硬编码）。
    """
    if mode == "legacy":
        return sorted(os.path.basename(d) for d in glob.glob(os.path.join(base, "w1*"))
                      if os.path.isdir(d))
    wins = []
    if not os.path.isdir(base):
        return wins
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        if any(os.path.exists(os.path.join(d, arm, "g1", "cases.txt")) for arm in os.listdir(d)):
            wins.append(name)
    return wins


def load_all(mod, root, rounds, mode):
    """同 r589 读法契约（`<runs>/<r>/<win>/<arm>/g1/cases.txt`）；解析一律走 mod.read_run。"""
    data = {}
    for r in rounds:
        base = os.path.join(root, r)
        if not os.path.isdir(base):
            continue
        for win in enumerate_windows(base, mode):
            wd = os.path.join(base, win)
            rec = {"truth": None, "prod": [], "truth_rc": None, "prod_rc": []}
            for arm in sorted(os.listdir(wd)):
                g1 = os.path.join(wd, arm, "g1")
                run = mod.read_run(g1)
                if run is None:
                    continue
                rcp = os.path.join(g1, "cli_rc.txt")
                rc = io.open(rcp, encoding="utf-8", errors="replace").read().strip() if os.path.exists(rcp) else None
                if arm == "codex":
                    rec["truth"] = run
                    rec["truth_rc"] = rc
                elif arm.startswith("agentD"):
                    rec["prod"].append(run)
                    rec["prod_rc"].append(rc)
            data.setdefault(r, {})[win] = rec
    return data


def eval_set(mod, rounds, mode):
    mod.ROUNDS = list(rounds)
    data = load_all(mod, RUNS, rounds, mode)
    rows = mod.face_by_window(data)
    summ = mod.summarize(rows)
    runs_seen = 0
    bad = []
    for r, wins in data.items():
        for win, rec in wins.items():
            allruns = ([rec["truth"]] if rec["truth"] else []) + rec["prod"]
            if rec["truth"] is None:
                bad.append({"why": "missing_truth", "round": r, "win": win})
            if len(rec["prod"]) != 3:
                bad.append({"why": "prod_reps!=3", "round": r, "win": win, "n": len(rec["prod"])})
            for x in allruns:
                runs_seen += 1
                if x["n"] != mod.CASES_N:
                    bad.append({"why": "cases_n!=58", "round": r, "win": win, "n": x["n"]})
                if x["summary"] and x["summary"][0] != sum(1 for v in x["cases"].values() if v):
                    bad.append({"why": "summary_mismatch", "round": r, "win": win})
    C0 = {"runs_seen": runs_seen, "expected_runs": 4 * len(rows) and 4 * 3 * len(rounds),
          "windows": sum(len(v) for v in data.values()), "expected_windows": 3 * len(rounds),
          "issues": bad, "pass": (runs_seen == 4 * 3 * len(rounds)) and not bad}
    return data, rows, summ, C0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    mod = load_src()
    out = {"schema": "r629-primary-pool/1", "round": "R629",
           "single_variable": "窗名枚举 = legacy 硬编码 `w1*` vs derived 目录派生",
           "instrument_logic_source": {"path": SRC_REL,
                                       "sha12": hashlib.sha256(io.open(SRC, "rb").read()).hexdigest()[:12],
                                       "driver_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12]},
           "runs_root": RUNS}

    # ---- C-A 等价性：legacy vs derived 在 set1（r585–r588）上逐位相同 ----
    set1_r = ["r585", "r586", "r587", "r588"]
    _, _, s1d, c0d = eval_set(mod, set1_r, "derived")
    _, _, s1l, c0l = eval_set(mod, set1_r, "legacy")
    key = lambda s: (s.get("all_windows", {}).get("n"), s.get("valid_windows"),
                     None if s.get("task_face_all_median") is None else round(s["task_face_all_median"], 6))
    out["C_A_enumeration_equivalence"] = {
        "rounds": set1_r, "legacy": key(s1l), "derived": key(s1d),
        "identical": key(s1l) == key(s1d),
        "legacy_C0_runs": c0l["runs_seen"], "derived_C0_runs": c0d["runs_seen"],
        "rule": "该集窗名全部形如 w1xx ⇒ 两枚举本应读到同一批窗；不同即本轮夹带了读法改动"}

    # ---- C-B 有牙：legacy 在 r628 上读到 0 窗 ----
    ldata, _, ls, lc0 = eval_set(mod, ["r628"], "legacy")
    ddata, rows, ds, dc0 = eval_set(mod, ["r628"], "derived")
    out["C_B_enumeration_teeth"] = {
        "legacy": {"windows": lc0["windows"], "runs_seen": lc0["runs_seen"],
                   "data_scope_windows": sum(len(v) for v in ldata.values()),
                   "valid_windows": ls.get("valid_windows"),
                   "median": ls.get("task_face_all_median")},
        "derived": {"windows": dc0["windows"], "runs_seen": dc0["runs_seen"],
                    "valid_windows": ds.get("valid_windows"),
                    "median": ds.get("task_face_all_median")},
        "teeth": (lc0["windows"] == 0 and dc0["windows"] == 3 and dc0["runs_seen"] == 12),
        "rule": "同一冻结数据、只换窗名枚举；legacy 必须 0 窗（复现 R628 静默弃权），derived 必须 3 窗 12 跑次"}

    # ---- 主判据（判据 v3）set5 真读数 ----
    per_win = []
    for row in rows:
        per_win.append({k: row[k] for k in row if not isinstance(row[k], (dict, list))})

    # ---- 主判据自带的负控 C7（单侧变异；靶点 = 该集首个「产品有失败例」的窗）----
    tgt = None
    for row in rows:
        run = mod.read_run(os.path.join(RUNS, row["round"], row["win"], "agentD-r1", "g1"))
        if run and any(not v for v in run["cases"].values()):
            tgt = row["win"]
            break

    def mutate_one(win, side, cid, ok):
        if side == "prod" and win == tgt and ok is False:
            return True
        return None

    rows_nc = mod.face_by_window(ddata, mutate=mutate_one)
    nc_changed = ([(x["win"], x["D_case"], x["D_task"]) for x in rows] !=
                  [(x["win"], x["D_case"], x["D_task"]) for x in rows_nc])
    nc_prod_only = all(a["truth_pass"] == b["truth_pass"] and a["truth_all_pass"] == b["truth_all_pass"]
                       for a, b in zip(rows, rows_nc))
    C7 = {"mutation": "%s 产品侧任一失败例 FAIL->PASS (副本内, 单侧)" % tgt,
          "target_window": tgt, "readings_changed": nc_changed, "truth_side_untouched": nc_prod_only,
          "has_teeth": bool(nc_changed and nc_prod_only)}
    out["C_B_enumeration_teeth"]["C7_primary_negative_control"] = C7

    valid = [r for r in rows if r["valid_task"]]
    vD = [r["D_task"] for r in valid]
    med = statistics.median(vD) if vD else None
    neg = sum(1 for x in vD if x < 0)
    thr = -0.34
    c1_pass = bool(vD) and med is not None and med <= thr and neg >= (len(vD) + 1) // 2
    out["set5_primary_criterion"] = {
        "criterion": "判据 v3（整题全对率 + 按族分列）—— R628 预注册声明的**主判据**",
        "windows": sorted(ddata.get("r628", {}).keys()),
        "per_window": per_win,
        "summary": ds,
        "C0": dc0,
        "C1_primary": {"median_D_task": med, "neg_windows": neg, "valid_windows": len(vD),
                       "threshold_median": thr, "threshold_sign": "neg >= ceil(valid/2)",
                       "pass": c1_pass,
                       "verdict": ("整题面缺口成立" if c1_pass else ("整题面无缺口" if vD else "不可判"))},
        "C7_negative_control": C7,
        "verdict": {"rc": 0 if dc0["pass"] else 3,
                    "judge": "可判" if dc0["pass"] else "BLOCKED(数据残缺)"},
    }
    rc = 0
    if not out["C_A_enumeration_equivalence"]["identical"]:
        rc = 2
    if not out["C_B_enumeration_teeth"]["teeth"]:
        rc = 2
    if not C7["has_teeth"]:
        rc = 2
    if dc0["windows"] == 0:
        rc = 3
    out["verdict"] = {"rc": rc,
                      "enumeration_single_variable": not (rc == 2),
                      "note": "rc 仅表**器具读数是否成立**；质量面判定另见 verdict-r629.json（判决面 == 主判据面）"}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))

    print("C-A enumeration equivalence (set1 legacy vs derived): identical=%s %s vs %s"
          % (out["C_A_enumeration_equivalence"]["identical"],
             out["C_A_enumeration_equivalence"]["legacy"], out["C_A_enumeration_equivalence"]["derived"]))
    print("C-B teeth: legacy windows=%s runs=%s | derived windows=%s runs=%s | teeth=%s"
          % (lc0["windows"], lc0["runs_seen"], dc0["windows"], dc0["runs_seen"],
             out["C_B_enumeration_teeth"]["teeth"]))
    print("set5 primary: windows=%s valid=%s median=%s neg=%s rc=%s"
          % (sorted(ddata.get("r628", {}).keys()), ds.get("valid_windows"),
             ds.get("task_face_all_median"), ds.get("neg_windows"),
             out["set5_primary_criterion"]["verdict"]["rc"]))
    print("rc=%d" % rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
