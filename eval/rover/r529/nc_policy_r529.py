#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 J4 负控套件: 机检 `unreliable_policy` (验收面剔除外部真值失败窗) 是否真有牙。

四个沙盒 (落 /tmp, 不入仓) 只差三件事: 外侧(truth=codex)臂对/错、本侧(agent)臂对/错、是否声明策略。
  NC1 外侧错 + 本侧对 + 有策略 ⇒ 期望 rc=0 且 POLICY_DEMOTED 含 w1/codex (策略按预注册生效)
  NC2 外侧错 + **本侧也错** + 有策略 ⇒ 期望 rc=1 (B1: 本侧失败一律不得被规则吞掉)
  NC3 外侧错 + 本侧对 + 有策略但 artifacts.json **背时序** ⇒ 期望 rc=1 且 POLICY_ACTIVE=False (B2: 先声明再跑)
  NC4 外侧错 + 本侧对 + **无策略** ⇒ 期望 rc=1 (无预注册声明 ⇒ 不放水; 历史轮行为)
用例脚本 `nc_case.py` 只做一件事: `ok.txt` 存在 ⇒ PASS。判分只读前置器 `--out` JSON 的 rc/字段。
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

REPO = "/home/agentuser/AgentFramework"
EXEC = os.path.join(REPO, "eval/rover/r507pre/exec_precondition.py")
CASE_PY = '''import os, sys
ok = os.path.exists("ok.txt")
print("CASE n1#00 " + ("PASS" if ok else "FAIL") + (" " if ok else " ok.txt 缺失"))
print("SUMMARY %d/1" % (1 if ok else 0))
sys.exit(0 if ok else 1)
'''
TASKSET = {"round": "R529nc", "tasks": [{"tid": "n1", "kind": "project", "family": "nc-stub",
                                         "cases": "cases/nc_case.py", "hidden_cases": 1,
                                         "prompt": "nc stub", "prompt_sha256": "0" * 12 + "deadbeef"}]}
SCOPE = {"require": ["w1/agentA1-on", "w1/codex"], "nonrequired": [],
         "note": "NC 验收面"}
POLICY = {"rule": "truth_arm_window_unavailable", "truth_arm_patterns": ["*/codex", "*/C-codex*"],
          "effect": "exclude_from_acceptance_face", "declared_before_run": True,
          "bars": ["本侧(agent*)臂失败一律不得被本规则吞掉"]}


def build(tag, truth_ok, agent_ok, policy, backdate=False, truth_present=True, require=None):
    d = "/tmp/r529nc_%s" % tag
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "cases"))
    with open(os.path.join(d, "cases/nc_case.py"), "w", encoding="utf-8") as fh:
        fh.write(CASE_PY)
    with open(os.path.join(d, "taskset-nc.json"), "w", encoding="utf-8") as fh:
        json.dump(TASKSET, fh)
    ts = datetime.now(timezone.utc) - timedelta(seconds=3)
    sc = dict(SCOPE) if require is None else dict(SCOPE, require=list(require))
    pr = {"round": "R529nc", "prereg_sealed_ts": ts.isoformat().replace("+00:00", "Z"),
          "evidence_scope": sc}
    if policy:
        pr["unreliable_policy"] = dict(POLICY, policy_declared_ts=ts.isoformat().replace("+00:00", "Z"))
    with open(os.path.join(d, "prereg-nc.json"), "w", encoding="utf-8") as fh:
        json.dump(pr, fh, ensure_ascii=False, indent=1)
    time.sleep(1.2)                      # 声明必须早于任何窗产物 (B2 时序硬门)
    for arm, ok in (("agentA1-on", agent_ok), ("codex", truth_ok)):
        if arm == "codex" and not truth_present:
            continue                        # NC5: 外侧臂**整目录缺席** (真值臂崩在产物之前)
        w = os.path.join(d, "snapshots/w1", arm, "n1")     # 前置器物化的是 <tid> 目录本身 = 产物根 (承 r521 约定)
        os.makedirs(w, exist_ok=True)
        if ok:
            open(os.path.join(w, "ok.txt"), "w").write("ok\n")
    ev = os.path.join(d, "evidence/windows/w1")
    os.makedirs(ev, exist_ok=True)
    ap = os.path.join(ev, "artifacts.json")
    with open(ap, "w", encoding="utf-8") as fh:
        json.dump({"window": "w1", "artifacts": []}, fh)
    if backdate:
        old = (ts - timedelta(hours=1)).timestamp()
        os.utime(ap, (old, old))
    return d


def run(d, out):
    p = subprocess.run([sys.executable, EXEC, "--layout", "project", "--taskset", os.path.join(d, "taskset-nc.json"),
                        "--out", out, "--round", "R529nc"], capture_output=True, text=True)
    txt = p.stdout + p.stderr
    try:
        j = json.load(open(out, encoding="utf-8"))
    except Exception:
        j = {"_parse": False, "verdict": "?", "blocked_scoped": []}
    return p.returncode, txt, j


NC = [("NC1_truth_fail_demoted", False, True, True, 0, True, False, True),
      ("NC2_agent_fail_not_swallowed", False, False, True, 1, True, False, True),
      ("NC3_backdated_artifacts", False, True, True, 1, False, True, True),
      ("NC4_no_policy_key", False, True, False, 1, False, False, True),
      ("NC5_absent_truth_arm", False, True, True, 0, True, False, False),
      # NC6 = 本轮真实场景的回归陷阱: 外侧臂**未写进 evidence_scope.require** (未声明窗) 且失败。
      # 修好前 `seen` 用带 tid 的键匹配臂级模式 "*/codex" ⇒ 恒不匹配 ⇒ 该窗不剔除 (rc 假红).
      ("NC6_truth_arm_undeclared_window", False, True, True, 0, True, False, True)]
rows, allok = [], True
for tag, truth_ok, agent_ok, policy, exp_rc, exp_pol, backdate, truth_present in NC:
    rq = ["w1/agentA1-on"] if tag.startswith("NC6") else None
    d = build(tag, truth_ok, agent_ok, policy, backdate, truth_present, rq)
    out = os.path.join(d, "precond-%s.json" % tag)
    rc, txt, j = run(d, out)
    demoted = j.get("policy_demoted") or []
    pol_active = bool((j.get("policy") or {}).get("active"))
    ok = (rc == exp_rc) and (pol_active == exp_pol) and (bool(demoted) == exp_pol or (not exp_pol and not demoted))
    if exp_pol and exp_rc == 0:
        ok = ok and demoted == ["w1/codex"] and not j.get("blocked_scoped")
    if tag == "NC2":
        ok = ok and any("codex/t1" in m or "codex" in m for m in j.get("blocked_scoped") or [])
    if tag == "NC5":
        # 缺目录被记为 declared_absent (硬闸), 策略生效后该条必须被剔除 ⇒ 既不假绿也不残留
        ok = ok and (j.get("declared_absent") == [])
    allok = allok and ok
    rows.append({"nc": tag, "rc": rc, "expect_rc": exp_rc, "policy_active": pol_active, "expect_policy": exp_pol,
                 "demoted": demoted, "blocked_scoped": len(j.get("blocked_scoped") or []),
                 "policy_reason": (j.get("policy") or {}).get("reason"), "ok": bool(ok),
                 "unreliable_windows": j.get("unreliable_windows")})
    print("%-32s rc=%d(exp %d) policy=%s demoted=%s -> %s  [reason=%s]" %
          (tag, rc, exp_rc, pol_active, demoted, "PASS" if ok else "FAIL", (j.get("policy") or {}).get("reason")))
    if tag == "NC2":
        print("   NC2 blocked_scoped=%s" % (j.get("blocked_scoped") or [])[:2])
blob = {"round": "R529", "instrument": "eval/rover/r507pre/exec_precondition.py",
        "exec_sha256": __import__("hashlib").sha256(open(EXEC, "rb").read()).hexdigest(),
        "cases": rows, "all_ok": allok}
open(os.path.join(REPO, "eval/rover/r529/evidence/nc-policy-r529.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
print("NC_POLICY_ALL_OK=%s" % allok)
sys.exit(0 if allok else 1)
