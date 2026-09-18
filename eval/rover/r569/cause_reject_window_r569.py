#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R569 候选④: 「拒收窗」(R568 记『w104 型臂级崩溃窗』) 的**只读定因**。

零开发 / 零远端 / 零产品改动: 只用既有落盘件 + 冻结快照 (判分在**副本**上做)。

定因三层判据 (逐层给机读读数, 缺一层即 fail-closed):
  L1 落盘层: 该臂窗**产物是否落盘** (快照里 games/*.py 是否存在 + 关键文件 sha/字节);
  L2 判定层: 冻结判分器在**副本**上重跑 ⇒ 逐例 PASS/FAIL 计数 + 失败模式分布;
  L3 交付层: 产品自身 transcript 的 rc / stage / reason / public_probe_* / correctness_asserted。

结论形态 (本文件只给读数, 结论文本在轮志): 「崩溃」与「拒收」必须由 L1+L2+L3 组合判别:
  产物缺失 ∧ 无判定 ⇒ 崩渍; 产物在 ∧ 全例 stdout_mismatch ∧ 产品自测闸报失败 ⇒ **拒收窗**。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
WIN = "w104"
SNAP_B0 = os.path.join(REPO, "eval/rover/r559/snapshots/w104/R559B0/g1")
SNAP_B3 = os.path.join(REPO, "eval/rover/r559/snapshots/w104/R559B3/g1")
REPORT = os.path.join(REPO, "eval/rover/r559/evidence/windows/w104/report.json")


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def l1_artifacts():
    """落盘层: 产物存在性 + 入口文件形态 (只读)。"""
    out = {"snapshot_dir": os.path.relpath(SNAP_B0, REPO), "exists": os.path.isdir(SNAP_B0), "files": []}
    if not out["exists"]:
        return out
    for root, _, files in os.walk(SNAP_B0):
        for fn in sorted(files):
            if "__pycache__" in root or fn.endswith(".pyc"):
                continue
            p = os.path.join(root, fn)
            out["files"].append({"rel": os.path.relpath(p, SNAP_B0), "bytes": os.path.getsize(p),
                                 "sha256": sha(p)})
    main_py = os.path.join(SNAP_B0, "games", "__main__.py")
    if os.path.isfile(main_py):
        body = io.open(main_py, encoding="utf-8", errors="replace").read()
        # 回显桩判据: 正文把 stdin 原样写回 stdout 且**不含**任何游戏逻辑分支
        echo_markers = ["sys.stdin.read()", "sys.stdout.write"]
        game_markers = ["wythoff", "nim", "life", "sub"]
        out["entry_kind"] = {
            "path": "games/__main__.py", "bytes": os.path.getsize(main_py), "sha256": sha(main_py),
            "echo_markers_present": all(m in body for m in echo_markers),
            "game_markers_absent": not any(m in body for m in game_markers),
            "is_stdin_echo_stub": bool(all(m in body for m in echo_markers)
                                       and not any(m in body for m in game_markers)),
            "body_chars": len(body),
        }
    return out


def l2_grade_replay(workroot):
    """判定层: 冻结判分器在**副本**上重跑 (禁在原快照上判分: 判分器会写 _grade.json)。"""
    cp = os.path.join(workroot, "repro-%s-b0" % WIN)
    if os.path.isdir(cp):
        shutil.rmtree(cp)
    os.makedirs(workroot, exist_ok=True)
    shutil.copytree(SNAP_B0, cp)
    grader = os.path.join(REPO, "eval/rover/r560/cases/run_cases_r521.py")
    # 判分器以 cwd=被测工作目录 运行 (与 runner 同形态); 环境剥掉管道变量
    env = {k: v for k, v in os.environ.items()
           if k not in ("AGENTFRAMEWORK_PY_RUN", "AGENTFRAMEWORK_ARTIFACT_REPAIR")}
    r = subprocess.run([sys.executable, "-I", "-B", grader], cwd=cp, capture_output=True, text=True, env=env)
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.startswith("CASE ")]
    pass_n = sum(1 for ln in lines if " PASS" in ln)
    modes = {}
    for ln in lines:
        parts = ln.split()
        if len(parts) >= 4 and parts[2] == "FAIL":
            modes[parts[3]] = modes.get(parts[3], 0) + 1
    return {"grader": os.path.relpath(grader, REPO), "grader_sha256": sha(grader),
            "replay_dir": os.path.relpath(cp, REPO), "rc": r.returncode,
            "cases_total": len(lines), "cases_pass": pass_n, "cases_fail": len(lines) - pass_n,
            "fail_modes": modes, "stderr_tail": (r.stderr or "").strip().splitlines()[-3:]}


def l3_delivery(workroot):
    """交付层: 产品自身 transcript (rc/stage/reason/public_probe_*/correctness_asserted)。"""
    src = "/tmp/r559/%s/agentB0/g1/transcript.json" % WIN
    rep = json.load(io.open(REPORT, encoding="utf-8"))
    row = [x for x in rep["rows"] if x["arm"] == "R559B0"]
    out = {"transcript_src": src, "available": os.path.isfile(src), "report_row": row[0] if row else None}
    if out["available"]:
        t = json.load(io.open(src, encoding="utf-8"))
        keep = ["rc", "stage", "max_exec_repair", "exec_repairs", "public_probe_ran", "public_probe_reason",
                "public_probe_total", "public_probe_failed", "public_probe_trigger_rc", "self_test_unmet",
                "correctness_asserted", "calls", "plan_steps_total", "steps_executed", "repair_rounds"]
        out["transcript"] = {k: t.get(k) for k in keep}
        out["reason_head"] = (t.get("reason") or "")[:420]
        # 持久化一份 (唯一副本只在 /tmp ⇒ 归档防丢, 依 unattended-job-reliability §7)
        dst = os.path.join(workroot, "evidence", "transcript-%s-R559B0.json" % WIN)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        out["transcript_archived"] = os.path.relpath(dst, REPO)
    return out


def l3b_class_census():
    """同类普查: 全部历史臂窗里「rc=8 且 0/N」的窗有几个? 其 stage 分布如何?"""
    import glob
    rows = {}
    for p in glob.glob(os.path.join(REPO, "eval/rover/r5*/evidence/windows/w*/report.json")):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for r in d.get("rows", []):
            if r.get("side") != "agent":
                continue
            rows[(str(d.get("round")), str(d.get("win")), str(r.get("arm")))] = r
    zero = {"/".join(k): {"cases_pass": v.get("cases_pass"), "cases_total": v.get("cases_total"),
                          "rc": v.get("rc"), "stage": v.get("stage"),
                          "public_probe_failed": v.get("public_probe_failed"),
                          "exec_repairs": v.get("exec_repairs")}
            for k, v in rows.items() if v.get("cases_pass") == 0}
    rc8 = {"/".join(k): {"cases_pass": v.get("cases_pass"), "stage": v.get("stage"),
                         "public_probe_failed": v.get("public_probe_failed"),
                         "exec_repairs": v.get("exec_repairs")}
           for k, v in rows.items() if v.get("rc") == 8}
    return {"agent_arm_windows": len(rows), "cases_zero": zero, "rc8": rc8,
            "public_probe_unmet_windows": [k for k, v in rc8.items() if v["stage"] == "public_probe_unmet"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workroot", default="/tmp/r569")
    a = ap.parse_args()
    rec = {"round": "R569", "candidate": "④ 拒收窗定因 (只读)",
           "claim": "R568 所称『w104 型臂级崩溃窗』必须按 L1/L2/L3 三层判定; 本件给机读读数, 不给结论散文",
           "L1_落盘层": l1_artifacts(),
           "L2_判定层": None, "L3_交付层": None, "L3b_同类普查": None}
    if os.path.isdir(SNAP_B0):
        rec["L2_判定层"] = l2_grade_replay(a.workroot)
    rec["L3_交付层"] = l3_delivery(a.workroot)
    rec["L3b_同类普查"] = l3b_class_census()
    # --- 机检 (fail-closed): 三层齐备才允许出结论 ---
    errs = []
    if not rec["L1_落盘层"].get("exists"):
        errs.append("L1_snapshot_missing")
    if rec["L2_判定层"] is None:
        errs.append("L2_replay_missing")
    elif rec["L2_判定层"]["cases_total"] != 58:
        errs.append("L2_case_count_%s" % rec["L2_判定层"]["cases_total"])
    if rec["L3_交付层"]["report_row"] is None:
        errs.append("L3_report_row_missing")
    rec["laters"] = {
        "产物落盘": rec["L1_落盘层"].get("entry_kind", {}).get("is_stdin_echo_stub") is False,
        "入口为 stdin 回显桩": rec["L1_落盘层"].get("entry_kind", {}).get("is_stdin_echo_stub"),
        "判分复现 0/58": (rec["L2_判定层"] or {}).get("cases_pass") == 0,
        "失败模式唯一": list((rec["L2_判定层"] or {}).get("fail_modes", {}).keys()),
        "产品自测闸报未过": (rec["L3_交付层"].get("transcript") or {}).get("public_probe_reason"),
        "产品未宣称正确": (rec["L3_交付层"].get("transcript") or {}).get("correctness_asserted") == 0,
        "rc": (rec["L3_交付层"].get("transcript") or {}).get("rc"),
        "stage": (rec["L3_交付层"].get("transcript") or {}).get("stage"),
    }
    rec["rc"] = 2 if errs else 0
    rec["errors"] = errs
    json.dump(rec, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rec["rc"], "errors": errs, "later": rec["laters"],
                      "L2_fail_modes": (rec["L2_判定层"] or {}).get("fail_modes"),
                      "public_probe_unmet_windows": rec["L3b_同类普查"]["public_probe_unmet_windows"],
                      "cases_zero": list(rec["L3b_同类普查"]["cases_zero"].keys()),
                      "rc8_windows": list(rec["L3b_同类普查"]["rc8"].keys())}, ensure_ascii=False, indent=1))
    return rec["rc"]


if __name__ == "__main__":
    sys.exit(main())
