#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R523 器具改动的正/负控面板 (7 项) —— 证明 `exec_precondition.py` 验收面语义修复**未放水**。

被改语义 (R523 prereg line 66 已预注册):
  旧: rc 由**全局 blocked** 判定 ⇒ 已声明「非验收面」的臂失败也能把 rc 顶成 1 (R522「blocked 非空即 rc=1」补丁修过头)。
  新: rc 由**验收面** (require ∪ undeclared) 判定; 非验收面失败只进全局 blocked 并单列 NONREQUIRED ⇒ 判据不降级。

沙盒 (每控一目录, 根自定, 不依赖 --round 命名约定):
  <root>/<ctrl>/taskset-<ctrl>.json + prereg-<ctrl>.json + cases/ + snapshots/w1/<arm>/<tid>/
  + evidence/windows/w1/{artifacts.json,report.json}
真值树复用 R523 仓内快照: CORRECT=w1/agentA1-on/g1 (58/58) ; FAILING=w2/codex/g1 (46/58)。
A/B: 同一沙盒分别跑「HEAD 前修复版」与「修复后版」, 逐控对照 rc。
"""
from __future__ import annotations
import io, json, os, shutil, subprocess, sys

REPO = "/home/agentuser/AgentFramework"
GATE = os.path.join(REPO, "eval/rover/r507pre/exec_precondition.py")
GATE_OLD = "/tmp/r523nc/exec_precondition_HEAD.py"
ROOT = "/tmp/r523nc/panel"
SRC_TS = os.path.join(REPO, "eval/rover/r523/taskset-r523.json")
SRC_CASES = os.path.join(REPO, "eval/rover/r523/cases")
CORRECT = os.path.join(REPO, "eval/rover/r523/snapshots/w1/agentA1-on/g1")
FAILING = os.path.join(REPO, "eval/rover/r523/snapshots/w2/codex/g1")
VALID = "cases/run_cases_r521.py"
MISSING = "cases/does_not_exist_<X>.py"


def w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def task(tid, cases):
    d = json.load(io.open(SRC_TS, encoding="utf-8"))
    t = dict(d["tasks"][0])
    t["tid"] = tid
    t["cases"] = cases
    return t


def build(ctrl, arms, tasks, scope, claimed):
    """arms: [(snapdir, tid, src_tree|None)] ; tasks: [(tid, cases)] ; scope: dict|None"""
    d = os.path.join(ROOT, ctrl)
    w(os.path.join(d, "taskset-%s.json" % ctrl),
      {"round": "R523", "family": "games-longtask-v1", "source": "NC 沙盒", "tasks": tasks})
    if scope is not None:
        w(os.path.join(d, "prereg-%s.json" % ctrl), {"round": "R523", "made_before_run": True,
                                                     "evidence_scope": scope})
    os.makedirs(os.path.join(d, "cases"), exist_ok=True)
    for f in os.listdir(SRC_CASES):
        shutil.copy2(os.path.join(SRC_CASES, f), os.path.join(d, "cases", f))
    for snapdir, tid, src in arms:
        dst = os.path.join(d, "snapshots/w1", snapdir, tid)
        os.makedirs(dst, exist_ok=True)
        if src:
            for r, _, fs in os.walk(src):
                rl = os.path.relpath(r, src)
                tgt = dst if rl == "." else os.path.join(dst, rl)
                os.makedirs(tgt, exist_ok=True)
                for f in fs:
                    shutil.copy2(os.path.join(r, f), os.path.join(tgt, f))
        else:
            w(os.path.join(dst, "placeholder.txt"), "arm dir 存在即可 (本控只看脚本缺失分支)\n")
    w(os.path.join(d, "evidence/windows/w1/artifacts.json"), {"round": "R523", "window": "w1"})
    w(os.path.join(d, "evidence/windows/w1/report.json"),
      {"rows": [{"arm": a, "tid": t, "side": s, "all_pass": p} for (a, t, s, p) in claimed]})
    return d


def run(gate, ctrl):
    d = os.path.join(ROOT, ctrl)
    out = os.path.join(d, "out-%s.json" % os.path.basename(gate))
    p = subprocess.run([sys.executable, gate, "--layout", "project",
                        "--taskset", os.path.join(d, "taskset-%s.json" % ctrl),
                        "--out", out, "--label", ctrl, "--proj-timeout", "300"],
                       capture_output=True, text=True)
    blob = {}
    if os.path.isfile(out):
        blob = json.load(io.open(out, encoding="utf-8"))
    return p.returncode, blob, (p.stdout + p.stderr)


REQ_A1 = ["w1/agentA1-on"]          # require 项是 fnmatch 字符串 (非 dict)
REQ_A0 = ["w1/agentA0-off"]
NON_A0 = [{"pattern": "w*/agentA0-off", "reason": "消融控制臂, 非交付面 (NC)"}]
NON_A1 = [{"pattern": "w*/agentA1-on", "reason": "NC 反向声明"}]


def main():
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    os.makedirs(os.path.dirname(GATE_OLD), exist_ok=True)
    subprocess.run(["git", "-C", REPO, "show", "HEAD:eval/rover/r507pre/exec_precondition.py"],
                   stdout=io.open(GATE_OLD, "w", encoding="utf-8"), check=True)

    C = []   # (name, arms, tasks, scope, claimed, expect_new, expect_old, must_contain)
    C.append(("NC1_pc_all_correct",
              [("agentA1-on", "g1", CORRECT), ("agentA0-off", "g1", CORRECT)],
              [task("g1", VALID)], {"require": REQ_A1, "nonrequired": NON_A0},
              [("A1-on", "g1", "agent", True), ("A0-off", "g1", "agent", True)], 0, 0, []))
    C.append(("NC2_nonrequired_arm_fails",
              [("agentA1-on", "g1", CORRECT), ("agentA0-off", "g1", FAILING)],
              [task("g1", VALID)], {"require": REQ_A1, "nonrequired": NON_A0},
              [("A1-on", "g1", "agent", True), ("A0-off", "g1", "agent", False)], 0, 1, ["NONREQUIRED"]))
    C.append(("NC3_required_arm_fails",
              [("agentA1-on", "g1", CORRECT), ("agentA0-off", "g1", FAILING)],
              [task("g1", VALID)], {"require": REQ_A0, "nonrequired": NON_A1},
              [("A1-on", "g1", "agent", True), ("A0-off", "g1", "agent", False)], 1, 1, ["BLOCKED"]))
    C.append(("NC4_undeclared_arm",
              [("agentA1-on", "g1", CORRECT), ("agentA0-off", "g1", CORRECT)],
              [task("g1", VALID)], {"require": REQ_A1, "nonrequired": []},
              [("A1-on", "g1", "agent", True), ("A0-off", "g1", "agent", True)], 1, 1, ["UNDECLARED"]))
    C.append(("NC5_missing_script_required",
              [("agentA1-on", "g1", None)],
              [task("g1", MISSING.replace("<X>", "5"))], {"require": REQ_A1, "nonrequired": []},
              [("A1-on", "g1", "agent", False)], 1, 1, ["missing_case_script"]))
    C.append(("NC6_missing_script_nonrequired",
              [("agentA1-on", "g1", CORRECT), ("agentA0-off", "g2", None)],
              [task("g1", VALID), task("g2", MISSING.replace("<X>", "6"))],
              {"require": REQ_A1, "nonrequired": NON_A0},
              [("A1-on", "g1", "agent", True), ("A0-off", "g2", "agent", False)], 0, 1, ["NONREQUIRED"]))
    C.append(("NC7_no_prereg_all_arms_required",
              [("agentA1-on", "g1", CORRECT), ("agentA0-off", "g1", FAILING)],
              [task("g1", VALID)], None,
              [("A1-on", "g1", "agent", True), ("A0-off", "g1", "agent", False)], 1, 1, ["BLOCKED"]))

    fails, rows = [], []
    for name, arms, tasks, scope, claimed, exp_new, exp_old, must in C:
        build(name, arms, tasks, scope, claimed)
        rc_new, blob_new, out_new = run(GATE, name)
        rc_old, _, _ = run(GATE_OLD, name)
        ok = (rc_new == exp_new) and (rc_old == exp_old) and all(m in out_new for m in must)
        if not ok:
            fails.append(name)
        rows.append({"ctrl": name, "rc_new": rc_new, "rc_old": rc_old,
                     "expect_new": exp_new, "expect_old": exp_old,
                     "acceptable_scoped": blob_new.get("acceptable_scoped"),
                     "blocked_n": len(blob_new.get("blocked") or []),
                     "blocked_scoped_n": len(blob_new.get("blocked_scoped") or []),
                     "nonrequired_n": len(blob_new.get("nonrequired_arms") or []),
                     "undeclared_n": len(blob_new.get("undeclared_arms") or []),
                     "ok": ok, "flips": ("rc %d→%d" % (rc_old, rc_new)) if rc_old != rc_new else "-"})
        print("%-34s rc_old=%d rc_new=%d (期望 old=%d new=%d) blocked=%d/%-2d nonreq=%d %s"
              % (name, rc_old, rc_new, exp_old, exp_new, len(blob_new.get("blocked") or []),
                 len(blob_new.get("blocked_scoped") or []), len(blob_new.get("nonrequired_arms") or []),
                 "OK" if ok else "**FAIL**"))
    res = {"round": "R523", "panel": "exec_precondition 验收面语义 正/负控", "gate_md5": None, "rows": rows,
           "fails": fails, "verdict": ("NC_PANEL_PASS" if not fails else "NC_PANEL_FAIL"),
           "note": "flips 一行 = 本轮修复的实际行为改变 (仅非验收面臂); require/undeclared/无预注册 三类的阻断行为**未变**"}
    res["gate_md5"] = subprocess.run(["md5sum", GATE], capture_output=True, text=True).stdout.split()[0]
    w(os.path.join(REPO, "eval/rover/r523/evidence/nc-panel-r523.json"), res)
    print(json.dumps({k: res[k] for k in ("gate_md5", "verdict", "fails")}, ensure_ascii=False))
    print("FLIPS: " + " | ".join("%s %s" % (r["ctrl"], r["flips"]) for r in rows if r["flips"] != "-"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
