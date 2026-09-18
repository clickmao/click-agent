#!/usr/bin/env python3
"""R549 离线重放: 用本轮修好的执行路径对 r547/w2 仓内不可变快照重跑隐藏用例。

二合一用途 (零远端调用, 只读仓内快照):
  (a) 保形回归 —— 新执行路径(独立进程组收口)必须复现 R547 窗口已落盘的 cases_pass;
  (b) 定因 —— 落 failed_cases 逐条名单, 供失败族归因(wythoff 等)。

口径声明: 重放只在 --proj-timeout 与 R547 落盘口径一致时与人读可比; 若改小超时,
只用于族归因, **不得与历史读数相减**(挂死臂的 cases_n 会变)。
"""
import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "r507pre"))
import exec_precondition as EP  # noqa: E402


def _norm(arm):
    """臂名归一: 快照目录名 `agentE0a-g1` 与落盘行名 `E0a-g1` 视为同一臂。"""
    return arm.replace("agent", "").split("-")[0]


def recorded_rows(round_id, window):
    p = os.path.join(EP.REPO, "eval/rover", round_id, "evidence/windows", window, "report.json")
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8-sig") as fh:
        d = json.load(fh)
    out = {}
    for r in (d.get("rows") or []):
        out[_norm(r.get("arm") or "")] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="r547")
    ap.add_argument("--window", default="w2")
    ap.add_argument("--arms", default="", help="逗号分隔臂名(形如 agentE0a-g1); 空=全部")
    ap.add_argument("--proj-timeout", type=float, default=420.0)
    ap.add_argument("--tag", default="replay")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    snap = os.path.join(EP.REPO, "eval/rover", a.round, "snapshots", a.window)
    taskset = os.path.join(EP.REPO, "eval/rover", a.round, "taskset-%s.json" % a.round)
    arms = [x for x in sorted(os.listdir(snap)) if os.path.isdir(os.path.join(snap, x))]
    if a.arms:
        want = {x.strip() for x in a.arms.split(",") if x.strip()}
        arms = [x for x in arms if x in want or x.split("-")[0].lstrip("agent") in want]
    root = tempfile.mkdtemp(prefix="r549-replay-%s-" % a.tag)
    for arm in arms:
        EP._copy_tree(os.path.join(snap, arm), os.path.join(root, a.window, arm))
    claims = tempfile.mkdtemp(prefix="r549-claims-")  # 空 ⇒ 无自报行, 不吃对照
    outp = a.out or os.path.join(HERE, "replay-%s-%s.json" % (a.round, a.tag))
    t0 = time.time()
    res = EP.run_project("R549-replay-%s" % a.tag, taskset, claims, root, [a.window],
                         out_path=outp + ".raw.json", timeout=a.proj_timeout)
    dur = time.time() - t0
    raw = json.load(io.open(outp + ".raw.json", encoding="utf-8-sig"))   # 逐臂行只在落盘文档里
    rows = raw["windows"][a.window]["arms"]                              # (run_project 返回值是摘要)
    rec = recorded_rows(a.round, a.window)

    table = []
    for key, r in sorted(rows.items()):
        arm = r["arm"]
        base = rec.get(_norm(arm)) or {}
        table.append({
            "arm": arm, "cases_pass": r.get("cases_pass"), "cases_n": r.get("cases_n"),
            "cases_expected": r.get("cases_expected"), "rc": r.get("rc"), "correct": r.get("correct"),
            "recorded_cases_pass": base.get("cases_pass"),
            "same_as_recorded": (base.get("cases_pass") == r.get("cases_pass")) if base else None,
            "failed_cases": r.get("failed_cases"), "stderr_tail": (r.get("stderr_tail") or "")[-120:],
        })
    fam = {}
    for t in table:
        for fc in (t["failed_cases"] or []):
            g = fc.split("#")[0]
            fam[g] = fam.get(g, 0) + 1
    payload = {"round": "R549", "kind": "offline-replay", "src_round": a.round, "window": a.window,
               "proj_timeout": a.proj_timeout, "duration_s": round(dur, 1), "arms_n": len(arms),
               "arms": table, "failed_family_census": fam,
               "note": "只读仓内快照; 零远端调用; 保形可比性=仅当 proj_timeout 与源轮落盘口径一致"}
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(claims, ignore_errors=True)
    with open(outp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1))
    print("== %s/%s replay tag=%s arms=%d dur=%.1fs timeout=%.0fs" % (a.round, a.window, a.tag, len(arms), dur, a.proj_timeout))
    for t in table:
        print("  %-14s pass=%s/%s rc=%s recorded=%s same=%s failed=%s" % (
            t["arm"], t["cases_pass"], t["cases_expected"], t["rc"], t["recorded_cases_pass"],
            t["same_as_recorded"], ",".join(t["failed_cases"] or []) or "-"))
    print("  failed_family_census:", json.dumps(fam, ensure_ascii=False))
    print("  out:", outp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
