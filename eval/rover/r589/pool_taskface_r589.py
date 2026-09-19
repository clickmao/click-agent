#!/usr/bin/env python3
# R589 只读并池器 —— 判据面切换（用例级通过数 -> 整题全对率 + 按族分列）
#   **零新臂 / 零远端 / 零产品源码改动**：只在 R585–R588 的在盘机械判分件（cases.txt）上重算。
#   外部真值 = 隐藏用例脚本 stdout（cases.txt），非产品自报。
#   契约（读法）: 每个跑次目录 <runs>/<round>/<win>/<arm>/g1/cases.txt
#      - 行 `CASE <family>#<idx>-<public|hidden> PASS|FAIL`（58 行，机械判分输出）
#      - 末行 `R521_CASES <pass>/58`
#    产品臂 = agentD-r*（每窗 3 跑次）；真值臂 = codex（每窗 1 跑次）。
#   判据见 eval/rover/r589/prereg-r589.json（先写后跑）。
import argparse, glob, hashlib, io, json, os, re, statistics, sys

RUNS = os.path.expanduser("~/.agentframework/harness/runs")
REPO = "/home/agentuser/AgentFramework"
ROUNDS = ["r585", "r586", "r587", "r588"]
FAM_TOTAL = {"life": 14, "nim": 15, "sub": 14, "wythoff": 15}
CASES_N = 58
# 读法契约（首跑 rc=3 假红定因，R589 自捕 #1）：真实行形态为
#   `CASE <id> PASS ` (尾随空格) 与 `CASE <id> FAIL <reason>`（如 TimeoutExpired）
#   ⇒ 首版 `... (PASS|FAIL)\s*$` 漏掉带 reason 的 FAIL 行 ⇒ 15 行读空 ⇒ cases_n!=58。
#   修法 = 允许 FAIL 后带 reason 并在读数里保留 reason 直方图（不改任何判据阈值）。
CASE_RE = re.compile(r"^CASE\s+(\S+)\s+(PASS|FAIL)\b[ \t]*(.*)$", re.M)
SUM_RE = re.compile(r"^R521_CASES\s+(\d+)/(\d+)\s*$", re.M)


def read_run(path):
    """读一个跑次的 cases.txt -> {'cases': {id: bool}, 'why': {id: reason}, ...}"""
    p = os.path.join(path, "cases.txt")
    if not os.path.exists(p):
        return None
    t = open(p, encoding="utf-8", errors="replace").read()
    cs, why = {}, {}
    for m in CASE_RE.finditer(t):
        cs[m.group(1)] = (m.group(2) == "PASS")
        why[m.group(1)] = (m.group(3) or "").strip()
    sm = SUM_RE.search(t)
    return {"path": p, "cases": cs, "why": why, "n": len(cs),
            "summary": (int(sm.group(1)), int(sm.group(2))) if sm else None,
            "present": True}


def fam_of(cid):
    return cid.split("#", 1)[0]


def fingerprint(roots):
    """逐文件 sha256 清单 -> (n, 聚合 sha256)。只读。"""
    h = hashlib.sha256()
    n = 0
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for fn in sorted(filenames):
                fp = os.path.join(dirpath, fn)
                try:
                    st = os.stat(fp)
                except OSError:
                    continue
                h.update(("%s|%d|%d\n" % (os.path.relpath(fp, root), st.st_size, int(st.st_mtime))).encode())
                try:
                    with open(fp, "rb") as fh:
                        h.update(hashlib.sha256(fh.read()).digest())
                except OSError:
                    h.update(b"<unreadable>")
                n += 1
    return n, h.hexdigest()


def load_all(runs_root):
    data = {}   # round -> win -> {'truth': run|None, 'prod': [run,...]}
    for r in ROUNDS:
        base = os.path.join(runs_root, r)
        if not os.path.isdir(base):
            continue
        for wd in sorted(glob.glob(os.path.join(base, "w1*"))):
            win = os.path.basename(wd)
            if not os.path.isdir(wd):
                continue
            rec = {"truth": None, "prod": [], "truth_rc": None, "prod_rc": []}
            for arm in sorted(os.listdir(wd)):
                g1 = os.path.join(wd, arm, "g1")
                run = read_run(g1)
                if run is None:
                    continue
                rcp = os.path.join(g1, "cli_rc.txt")
                rc = open(rcp, encoding="utf-8", errors="replace").read().strip() if os.path.exists(rcp) else None
                if arm == "codex":
                    rec["truth"] = run
                    rec["truth_rc"] = rc
                elif arm.startswith("agentD"):
                    rec["prod"].append(run)
                    rec["prod_rc"].append(rc)
            data.setdefault(r, {})[win] = rec
    return data


def per_run_stats(run):
    c = run["cases"]
    why = run.get("why", {})
    fams, reasons = {}, {}
    for cid, ok in c.items():
        f = fam_of(cid)
        d = fams.setdefault(f, [0, 0])
        d[1] += 1
        if ok:
            d[0] += 1
        else:
            r = (why.get(cid) or "FAIL").strip()
            reasons.setdefault(f, {})
            reasons[f][r] = reasons[f].get(r, 0) + 1
    return {"pass": sum(1 for v in c.values() if v), "n": len(c),
            "all_pass": sum(1 for v in c.values() if v) == CASES_N,
            "fams": fams, "reasons": reasons}


def face_by_window(data, mutate=None):
    """两判据面逐窗重算。
    mutate(win, side, cid, ok) -> bool|None；side ∈ {'truth','prod'}（C7 负控**只改单侧**，
    否则两侧同步位移 ⇒ D 不变、负控假阴性 —— R589 自捕 #2 的定因）。"""
    rows = []
    for r in ROUNDS:
        for win, rec in sorted(data.get(r, {}).items()):
            if rec["truth"] is None or not rec["prod"]:
                continue
            def rd(run, side):
                if mutate is None:
                    return per_run_stats(run)
                c = dict(run["cases"])
                for cid, ok in list(c.items()):
                    m = mutate(win, side, cid, ok)
                    if m is not None:
                        c[cid] = m
                return per_run_stats({"cases": c, "n": len(c), "why": run.get("why", {})})
            t = rd(rec["truth"], "truth")
            ps = [rd(x, "prod") for x in rec["prod"]]
            prod_pass = [p["pass"] for p in ps]
            prod_rate_task = sum(1 for p in ps if p["all_pass"]) / len(ps)
            truth_task = 1.0 if t["all_pass"] else 0.0
            prod_med = statistics.median(prod_pass)
            # 族分列（用例级 + 族整题面 + 失败原因直方图）
            fam = {}
            for f, tot in FAM_TOTAL.items():
                tpass = t["fams"].get(f, [0, 0])[0]
                pr = [p["fams"].get(f, [0, 0])[0] for p in ps]
                rsn = {}
                for p in ps:
                    for k, v in p["reasons"].get(f, {}).items():
                        rsn[k] = rsn.get(k, 0) + v
                fam[f] = {"n": tot, "truth_pass": tpass,
                          "prod_pass_med": statistics.median(pr),
                          "prod_all_pass_rate": sum(1 for x in pr if x == tot) / len(pr),
                          "truth_all_pass": 1.0 if tpass == tot else 0.0,
                          "prod_fail_reasons": rsn}
            rows.append({
                "round": r, "win": win,
                "truth_pass": t["pass"], "truth_all_pass": int(t["all_pass"]),
                "truth_rc": rec["truth_rc"],
                "prod_pass": prod_pass, "prod_rc": rec["prod_rc"],
                "prod_rate_task": prod_rate_task,
                "D_case": prod_med - t["pass"],
                "D_task": round(prod_rate_task - truth_task, 4),
                "valid_task": bool(t["all_pass"]),
                "families": fam,
            })
    return rows


def summarize(rows, key_case="D_case", key_task="D_task"):
    valid = [r for r in rows if r["valid_task"]]
    allD_case = [r[key_case] for r in rows]
    allD_task = [r[key_task] for r in rows]
    vD_case = [r[key_case] for r in valid]
    vD_task = [r[key_task] for r in valid]
    def st(v):
        if not v:
            return {"n": 0}
        return {"n": len(v), "median": statistics.median(v), "min": min(v), "max": max(v),
                "range": round(max(v) - min(v), 4),
                "sign": {"neg": sum(1 for x in v if x < 0), "zero": sum(1 for x in v if x == 0),
                         "pos": sum(1 for x in v if x > 0)}}
    return {"valid_windows": len(valid), "unreliable_windows_truth_self_fail": [r["win"] for r in rows if not r["valid_task"]],
            "all_windows": {"n": len(rows)},
            "case_face_valid": st(vD_case), "case_face_all": st(allD_case),
            "task_face_valid": st(vD_task), "task_face_all": st(allD_task),
            "case_face_all_median": statistics.median(allD_case) if allD_case else None,
            "task_face_all_median": statistics.median(allD_task) if allD_task else None}


def _sum_reasons(rows, f):
    agg = {}
    for r in rows:
        for k, v in r["families"][f].get("prod_fail_reasons", {}).items():
            agg[k] = agg.get(k, 0) + v
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=RUNS)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    roots = [os.path.join(a.runs, r) for r in ROUNDS] + \
            [os.path.join(REPO, "eval/rover", r, "snapshots") for r in ROUNDS]
    fp_before = fingerprint(roots)

    data = load_all(a.runs)

    # ---- C0 数据完整性 ----
    runs_seen, bad = 0, []
    for r, wins in data.items():
        for win, rec in wins.items():
            allruns = ([rec["truth"]] if rec["truth"] else []) + rec["prod"]
            if rec["truth"] is None:
                bad.append({"why": "missing_truth", "round": r, "win": win})
            if len(rec["prod"]) != 3:
                bad.append({"why": "prod_reps!=3", "round": r, "win": win, "n": len(rec["prod"])})
            for x in allruns:
                runs_seen += 1
                if x["n"] != CASES_N:
                    bad.append({"why": "cases_n!=58", "round": r, "win": win, "n": x["n"]})
                if x["summary"] and x["summary"][0] != sum(1 for v in x["cases"].values() if v):
                    bad.append({"why": "summary_mismatch", "round": r, "win": win,
                                "summary": x["summary"], "recount": sum(1 for v in x["cases"].values() if v)})
    C0 = {"runs_seen": runs_seen, "expected_runs": 48, "windows": sum(len(v) for v in data.values()),
          "expected_windows": 12, "issues": bad, "pass": (not bad and runs_seen == 48)}

    rows = face_by_window(data)
    summ = summarize(rows)

    # ---- 非平凡判据 C6 ----
    d_task_vals = sorted({r["D_task"] for r in rows})
    d_case_vals = sorted({r["D_case"] for r in rows})
    C6 = {"determinism": "n/a (只读读数, 无重复取样面 → 确定性由 C5 零写入 + 幂等重算承担)",
          "d_task_distinct": len(d_task_vals), "d_case_distinct": len(d_case_vals),
          "face_switch_trivial": (len(d_task_vals) <= 1 and len(d_case_vals) <= 1),
          "note": "operationalization: 两面读数在全窗上各自零方差 ⇒ 换面无信息量"}

    # ---- C7 负控（器具有牙，成对；**只改产品侧单侧**，避免两侧同步位移 ⇒ 假阴性）----
    def mutate_one(win, side, cid, ok):
        if side == "prod" and win == "w155" and ok is False:
            return True   # 把产品侧任一失败例翻成通过 ⇒ 产品面必须变化、真值侧不动
        return None
    rows_nc = face_by_window(data, mutate=mutate_one)
    nc_changed = (json.dumps([(r["win"], r["D_case"], r["D_task"]) for r in rows]) !=
                  json.dumps([(r["win"], r["D_case"], r["D_task"]) for r in rows_nc]))
    nc_prod_only = all(r_nc["truth_pass"] == r["truth_pass"] and r_nc["truth_all_pass"] == r["truth_all_pass"]
                       for r, r_nc in zip(rows, rows_nc))
    C7 = {"mutation": "w155 产品侧任一失败例 FAIL->PASS (副本内, 单侧)",
          "readings_changed": nc_changed, "truth_side_untouched": nc_prod_only,
          "has_teeth": bool(nc_changed and nc_prod_only)}
    # 正控: 源路径未被写 (指纹)
    fp_mid = fingerprint(roots)
    C7["source_untouched_after_nc"] = (fp_before == fp_mid)

    # ---- C1 整题面判据 ----
    valid = [r for r in rows if r["valid_task"]]
    vD_task = [r["D_task"] for r in valid]
    med = statistics.median(vD_task) if vD_task else None
    neg = sum(1 for x in vD_task if x < 0)
    thr_need = -0.34
    c1_pass = bool(vD_task) and med is not None and med <= thr_need and neg >= (len(vD_task) + 1) // 2
    C1 = {"median_D_task": med, "neg_windows": neg, "valid_windows": len(vD_task),
          "threshold_median": thr_need, "threshold_sign": "neg >= ceil(valid/2)",
          "pass": c1_pass,
          "verdict": ("整题面缺口成立" if c1_pass else ("整题面无缺口" if vD_task else "不可判"))}

    # ---- C2 两面同向 ----
    cm, tm = summ.get("case_face_valid", {}).get("median"), summ.get("task_face_valid", {}).get("median")
    same_sign = (cm is not None and tm is not None and ((cm < 0) == (tm < 0)) and cm != 0 and tm != 0) or \
                (cm == 0 and tm == 0)
    C2 = {"case_face_median": cm, "task_face_median": tm, "same_sign": bool(same_sign),
          "pass": bool(same_sign), "note": "量纲不同 ⇒ 只作同向判定, 禁跨面比数值大小"}

    # ---- 族分列聚合（全窗，产品 36 跑次 vs 真值 12 跑次）----
    fam_agg = {}
    for f, tot in FAM_TOTAL.items():
        tp = sum(r["families"][f]["truth_pass"] for r in rows)
        t_all = sum(int(r["families"][f]["truth_pass"] == tot) for r in rows)
        pp = [r["families"][f]["prod_pass_med"] for r in rows]
        p_rates = [r["families"][f]["prod_all_pass_rate"] for r in rows]
        fam_agg[f] = {"n_cases": tot, "truth_pass_cases": tp, "truth_runs": len(rows),
                      "truth_all_pass_runs": t_all,
                      "prod_pass_cases_median_per_window": statistics.median(pp),
                      "prod_all_pass_rate_mean": round(sum(p_rates) / len(p_rates), 4),
                      "prod_fail_reasons_total": _sum_reasons(rows, f)}
    # ---- C10 自报期待 vs 外部用例脱钩 ----
    dec = []
    for r, wins in data.items():
        for win, rec in wins.items():
            for run, rc in zip(rec["prod"], rec["prod_rc"]):
                k = sum(1 for v in run["cases"].values() if v)
                if rc is not None and rc != "0" and k == CASES_N:
                    dec.append("%s/%s rc=%s cases=58/58" % (r, win, rc))
    C10 = {"product_runs": sum(len(v["prod"]) for w in data.values() for v in w.values()),
           "rc_nonzero_and_allpass": len(dec), "named": dec,
           "share": round(len(dec) / max(1, sum(len(v["prod"]) for w in data.values() for v in w.values())), 4)}

    # ---- C11 R588 per-tag gap 复读 ----
    C11 = {"source": "eval/rover/r588/subspec-v2-r588.json", "found": False}
    p = os.path.join(REPO, "eval/rover/r588/subspec-v2-r588.json")
    if os.path.exists(p):
        d = json.load(io.open(p, encoding="utf-8"))
        C11["found"] = True
        C11["top_keys"] = sorted(d.keys())[:12]

        def gaps(o, out):
            if isinstance(o, dict):
                for k, v in o.items():
                    if "gap" in str(k).lower() and isinstance(v, (int, float)):
                        out.append([k, v])
                    else:
                        gaps(v, out)
            elif isinstance(o, list):
                for v in o:
                    gaps(v, out)
        g = []
        gaps(d, g)
        C11["gap_fields"] = g[:20]
        if g:
            mx = max(abs(v) for _, v in g)
            C11["max_abs_gap"] = mx
            C11["decision"] = "描述项(定案)" if mx < 0.05 else "保留候选轴"
            C11["rule"] = "max|gap| < 0.05 ⇒ 分类轴降为描述项; 不改判据不宣称能力"

    fp_after = fingerprint(roots)
    C5 = {"files": fp_after[0], "sha_before": fp_before[1], "sha_after": fp_after[1],
          "identical": fp_before == fp_after, "pass": fp_before == fp_after}

    rc = 0 if (C0["pass"] and C5["pass"] and C7["has_teeth"]) else (3 if not C0["pass"] else 2)
    out = {"round": "R589", "mode": "read_only pooled face-switch (零新臂/零远端/零产品源码改动)",
           "instrument_sha12": hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:12],
           "data_scope": {"rounds": ROUNDS, "windows": sum(len(v) for v in data.values()), "runs": runs_seen},
           "C0": C0, "C5_readonly": C5, "C6_nontriviality": C6, "C7_negative_control": C7,
           "C1_task_face": C1, "C2_face_direction": C2,
           "summary": summ, "family_aggregate": fam_agg, "C10_decoupling": C10, "C11_subspec_gap": C11,
           "per_window": rows,
           "verdict": {"rc": rc, "judge": ("PASS" if rc == 0 else ("FAIL(数据/器具)" if rc == 2 else "BLOCKED(数据残缺)"))}}
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("== R589 并池（判据面切换）==")
    print("C0 数据: runs=%d/%d windows=%d issues=%d" % (runs_seen, 48, out["data_scope"]["windows"], len(bad)))
    print("C5 只读: %s (%d files)" % (C5["pass"], C5["files"]))
    print("C7 负控: has_teeth=%s" % C7["has_teeth"])
    print("C6 非平凡: trivial=%s (D_task 取值 %d / D_case 取值 %d)" % (C6["face_switch_trivial"], C6["d_task_distinct"], C6["d_case_distinct"]))
    print("用例级面 有效窗: %s" % (summ["case_face_valid"],))
    print("整题面   有效窗: %s" % (summ["task_face_valid"],))
    print("C1 整题面判据: %s (median_D_task=%s neg=%d/%d thr=%s)" % (C1["verdict"], C1["median_D_task"], C1["neg_windows"], C1["valid_windows"], C1["threshold_median"]))
    print("C2 两面同向: %s (%s vs %s)" % (C2["pass"], C2["case_face_median"], C2["task_face_median"]))
    print("C10 脱钩: %d/%d %s" % (C10["rc_nonzero_and_allpass"], C10["product_runs"], C10["named"]))
    print("C11: %s" % (C11.get("decision", "n/a"),))
    print("rc=%d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
