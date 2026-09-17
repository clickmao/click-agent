#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""起臂前闸: 预注册声明面 ⊇ (计划窗 × 计划臂) —— 缺一声明即拒跑 (fail-closed)。

由来（R530 定因）: R529 起臂后跑了 w1/w2/w3 三窗, 但 `prereg-r529.json` 的
`window_plan.window` 只声明 `w1`、`evidence_scope.require` 也只写 w1 的臂 ⇒ w2/w3 全部落
`UNDECLARED_SCOPE`(前置器 fail-closed) ⇒ 终局 `exec_precondition --round r529` **结构性不可能 rc=0**,
整轮 (3 窗 × 3 臂 × 2 族 = 18 格真机读数) 只能标「参考(未可验收)」。该损失**在起臂前完全可判定** ——
本闸就是把它提前成一次零成本拒跑 (skill: 廉价必要条件前置 / 把纪律做成机检)。

判据 (单变量, 只读):
  planned = { (w, snapdir) | w ∈ --windows, snapdir ∈ prereg.window_plan.arms[*].snapdir }
  require = prereg.evidence_scope.require
  rc = 0 ⇔ missing == []          (可起臂)
  rc = 1 ⇔ missing ≠ []           (拒跑, 逐项点名缺哪条声明)
  rc = 3 ⇔ 输入缺失/不可解析      (器具/输入问题, 与被测无关; fail-closed)
注意: 本闸**只**判声明面覆盖; 不判策略 (unreliable_policy) 是否生效、不判臂跑得好不好。

自检: `python3 prereg_scope_gate.py --selftest` (3 合成用例: 覆盖 ⇒ rc=0 / 缺一窗 ⇒ rc=1 点名 / 缺文件 ⇒ rc=3)
真数据负控: `python3 prereg_scope_gate.py --prereg eval/rover/r529/prereg-r529.json --windows w1,w2,w3`
            ⇒ 必须 rc=1 且 missing 含 w2/w3 各臂 (证明本闸能拦住 R529 的真实事故)。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"


def gate(prereg_path, windows, out_path=None):
    if not prereg_path or not os.path.isfile(prereg_path):
        return {"ok": False, "rc": 3, "reason": "prereg_missing:%s" % prereg_path,
                "planned": [], "missing": [], "declared_not_planned": []}
    try:
        pr = json.load(io.open(prereg_path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "rc": 3, "reason": "prereg_unparsable:%s" % type(e).__name__,
                "planned": [], "missing": [], "declared_not_planned": []}
    wp = pr.get("window_plan") or {}
    snapdirs = [a.get("snapdir") for a in (wp.get("arms") or []) if a.get("snapdir")]
    if not snapdirs:
        return {"ok": False, "rc": 3, "reason": "window_plan.arms 无可读 snapdir",
                "planned": [], "missing": [], "declared_not_planned": []}
    wins = [w.strip() for w in windows if w.strip()]
    planned = sorted({"%s/%s" % (w, s) for w in wins for s in snapdirs})
    require = list((pr.get("evidence_scope") or {}).get("require") or [])
    missing = [k for k in planned if k not in set(require)]
    declared_not_planned = [k for k in require if k not in set(planned)]
    res = {"ok": not missing, "rc": 0 if not missing else 1,
           "prereg": os.path.relpath(prereg_path, REPO) if prereg_path.startswith(REPO) else prereg_path,
           "windows": wins, "snapdirs": snapdirs, "planned": planned, "require": require,
           "missing": missing, "declared_not_planned": declared_not_planned,
           "reason": "" if not missing else "UNDECLARED_IN_PREREG:%d" % len(missing)}
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        io.open(out_path, "w", encoding="utf-8", newline="\n").write(
            json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    return res


def selftest():
    d = "/tmp/r530_scope_gate"
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    arms = [{"snapdir": "agentA0-off", "side": "agent"}, {"snapdir": "codex", "side": "codex"}]
    base = {"round": "T", "window_plan": {"window": "w1", "arms": arms}}

    def mk(name, require, missing_file=False):
        p = os.path.join(d, "prereg-%s.json" % name)
        if missing_file:
            return p
        pr = dict(base, evidence_scope={"require": require})
        io.open(p, "w", encoding="utf-8").write(json.dumps(pr, ensure_ascii=False))
        return p

    cases = [
        ("NC1_all_declared", mk("nc1", ["w1/agentA0-off", "w1/codex", "w2/agentA0-off", "w2/codex"]),
         ["w1", "w2"], 0),
        ("NC2_missing_window", mk("nc2", ["w1/agentA0-off", "w1/codex"]), ["w1", "w2"], 1),
        ("NC3_prereg_absent", mk("nc3", [], missing_file=True), ["w1"], 3),
    ]
    rows, allok = [], True
    for name, p, wins, exp in cases:
        r = gate(p, wins)
        ok = (r["rc"] == exp)
        if name == "NC2_missing_window":
            ok = ok and r["missing"] == ["w2/agentA0-off", "w2/codex"]
        allok = allok and ok
        rows.append({"nc": name, "rc": r["rc"], "expect_rc": exp, "missing": r["missing"],
                     "reason": r["reason"], "ok": ok})
        print("%-24s rc=%d(exp %d) missing=%s -> %s" % (name, r["rc"], exp, r["missing"], "PASS" if ok else "FAIL"))
    print("SCOPE_GATE_SELFTEST_ALL_OK=%s" % allok)
    return 0 if allok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default=os.path.join(REPO, "eval/rover/r520/prereg-r520.json"))
    ap.add_argument("--windows", default="w1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    r = gate(a.prereg, a.windows.split(","), a.out)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print("SCOPE_GATE_RC=%d" % r["rc"])
    return r["rc"]


if __name__ == "__main__":
    sys.exit(main())
