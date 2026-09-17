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


def resolve_windows(prereg_path, windows_arg):
    """窗列表来源优先级: 显式 `--windows` (调用方知道真实窗) > 预注册 `window_plan.windows[]` (机读计划)。
    两者皆无 ⇒ fail-closed (`NO_MACHINE_READABLE_WINDOWS`, rc=3) —— 这正是 R529 事故的根因:
    计划里只写了单数 `window` ⇒ 闸无从知道还计划了 w2/w3 ⇒ 必须由预注册给出机读窗列表。"""
    wins = [w.strip() for w in (windows_arg or []) if w and w.strip()]
    if wins:
        return wins, "cli"
    if not prereg_path or not os.path.isfile(prereg_path):
        return [], "missing_prereg"
    try:
        pr = json.load(io.open(prereg_path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return [], "unparsable"
    wp = pr.get("window_plan") or {}
    decl = wp.get("windows")
    if isinstance(decl, list) and [w for w in decl if str(w).strip()]:
        return [str(w).strip() for w in decl if str(w).strip()], "prereg.window_plan.windows"
    return [], "NO_MACHINE_READABLE_WINDOWS"


def gate(prereg_path, windows, out_path=None):
    if not prereg_path or not os.path.isfile(prereg_path):
        return {"ok": False, "rc": 3, "reason": "prereg_missing:%s" % prereg_path,
                "planned": [], "missing": [], "declared_not_planned": [],
                "windows": [], "windows_source": "missing_prereg"}
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
    if not wins:
        return {"ok": False, "rc": 3, "reason": "NO_MACHINE_READABLE_WINDOWS",
                "prereg": os.path.relpath(prereg_path, REPO), "windows": [], "snapdirs": snapdirs,
                "planned": [], "require": list((pr.get("evidence_scope") or {}).get("require") or []),
                "missing": [], "declared_not_planned": []}
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

    def mk(name, require, missing_file=False, extra_plan=None):
        p = os.path.join(d, "prereg-%s.json" % name)
        if missing_file:
            return p
        plan = dict(base["window_plan"])
        if extra_plan:
            plan.update(extra_plan)
        pr = dict(base, window_plan=plan, evidence_scope={"require": require})
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

    # --- v2 (R531): 窗列表来源机读 + fail-closed ---------------------------------
    # ① 预注册自带 window_plan.windows[] ⇒ 无需调用方传参即可判定 (R529 事故的可机读版本)
    wp = mk("nc4", ["w1/agentA0-off", "w1/codex", "w2/agentA0-off", "w2/codex", "w3/agentA0-off", "w3/codex"],
            extra_plan={"windows": ["w1", "w2", "w3"]})
    w4, s4 = resolve_windows(wp, [])
    r4 = gate(wp, w4)
    ok4 = (s4 == "prereg.window_plan.windows" and r4["rc"] == 0)
    # ② 预注册只有单数 window (R529 真实形态) 且调用方不传参 ⇒ 必须 rc=3 拒判 (不得猜)
    wp2 = mk("nc5", ["w1/agentA0-off", "w1/codex"])
    w5, s5 = resolve_windows(wp2, [])
    r5 = gate(wp2, w5)
    ok5 = (s5 == "NO_MACHINE_READABLE_WINDOWS" and r5["rc"] == 3)
    # ③ 调用方显式窗超出预注册计划 ⇒ rc=1 且逐项点名 (R530 真实数据的机读替代形态)
    wp3 = mk("nc6", ["w1/agentA0-off", "w1/codex"], extra_plan={"windows": ["w1"]})
    w6, s6 = resolve_windows(wp3, ["w1", "w2"])
    r6 = gate(wp3, w6)
    ok6 = (s6 == "cli" and r6["rc"] == 1 and r6["missing"] == ["w2/agentA0-off", "w2/codex"])
    for nm, ok, r, s in (("NC4_windows_from_prereg_ok", ok4, r4, s4),
                         ("NC5_no_machine_readable_windows", ok5, r5, s5),
                         ("NC6_cli_window_superset", ok6, r6, s6)):
        allok = allok and ok
        rows.append({"nc": nm, "rc": r["rc"], "reason": r["reason"], "missing": r["missing"],
                     "windows_source": s, "ok": ok})
        print("%-32s rc=%d src=%s missing=%s -> %s" % (nm, r["rc"], s, r["missing"], "PASS" if ok else "FAIL"))
    print("SCOPE_GATE_SELFTEST_ALL_OK=%s" % allok)
    return 0 if allok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default=os.path.join(REPO, "eval/rover/r520/prereg-r520.json"))
    ap.add_argument("--windows", default="",
                    help="显式窗列表 (逗号分隔); 省略 ⇒ 读预注册 window_plan.windows[]; 两者皆无 ⇒ rc=3 fail-closed")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    wins, src = resolve_windows(a.prereg, a.windows.split(",") if a.windows else [])
    r = gate(a.prereg, wins, a.out)
    r["windows_source"] = src
    if a.out:
        io.open(a.out, "w", encoding="utf-8", newline="\n").write(
            json.dumps(r, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print("WINDOWS_SOURCE=%s WINDOWS=%s" % (src, ",".join(wins) or "-"))
    print("SCOPE_GATE_RC=%d" % r["rc"])
    return r["rc"]


if __name__ == "__main__":
    sys.exit(main())
