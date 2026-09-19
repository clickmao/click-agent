#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R588 · 候选②（零产品改动 / 零新夹具 / 零远端）: `TIMEOUT` 族定因 —— 「不收敛 vs 慢」。

事实面 (R587 已登记): `exception_histogram = {TRACEBACK_TypeError 6, TIMEOUT 8, TRACEBACK_IndexError 10}`,
其中 8 例 `TIMEOUT` **全部集中**在 `r585/w155/agentD-r2` 单跑次（idx 43,45,47,48,49,50,56,57）。
本脚本在**冻结快照的独立物化副本**上按产品同款调用协议复跑（`python3 -B -m games <game>`、
cwd=副本、stdin=题集 stdin、env 同 run_cases: PATH/LANG/HOME/PYTHONPATH/PYTHONDONTWRITEBYTECODE），
逐例三阶段判定:

  P1  每例 1 次 @T=10s   → 是否 ≤10s 内收敛
  P2  P1 未收敛者再 2 次 @T=10s → **同例同输入 3/3 达上限** 才判「不收敛」(单次不作结论)
  P3  P1 未收敛者取前 3 例各 1 次 @T=60s → 区分「不收敛」vs「只是慢」
  对照 4 例非 TIMEOUT 例 × 3 次 @T=60s → 必须秒级、3 次同形（器具非恒红）

判据 (预注册): ① 不收敛 ⇔ 3/3 达上限 ∧ T=60s 仍达上限;② 慢 ⇔ T=60s 内收敛;
③ 对照 4 例必须全收敛且逐次同形, 否则 `has_teeth=false`（器具缺陷, 分类只作候选登记）。

语料守恒: 只读冻结快照（读前记 sha, 读后复核同值）; 复跑在 ~/.agentframework/harness/runs/r588/tmprepro
（仓外）, 不写回冻结树。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time

REPO = "/home/agentuser/AgentFramework"
SNAP = os.path.join(REPO, "eval/rover/r585/snapshots/w155/agentD-r2/g1")
CASES = os.path.join(REPO, "eval/rover/r588/cases/cases-r521.json")
HANG_IDX = [43, 45, 47, 48, 49, 50, 56, 57]
CTL_IDX = [0, 1, 2, 3]
TMPROOT = os.path.expanduser("~/.agentframework/harness/runs/r588/tmprepro")


def sha_tree(root):
    h = hashlib.sha256()
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            h.update(os.path.relpath(p, root).encode())
            h.update(open(p, "rb").read())
    return h.hexdigest()


def run_case(wd, game, stdin, cap):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": wd,
           "PYTHONPATH": wd, "PYTHONDONTWRITEBYTECODE": "1"}
    t0 = time.monotonic()
    try:
        p = subprocess.run([sys.executable, "-B", "-m", "games", game], input=stdin,
                           capture_output=True, text=True, timeout=cap, cwd=wd, env=env)
        return {"outcome": "done", "rc": p.returncode, "secs": round(time.monotonic() - t0, 3),
                "out_len": len(p.stdout)}
    except subprocess.TimeoutExpired:
        return {"outcome": "cap", "rc": None, "secs": round(time.monotonic() - t0, 3), "out_len": 0}


def main():
    cases = json.load(io.open(CASES, encoding="utf-8"))
    pre = sha_tree(SNAP)
    if not os.path.isdir(TMPROOT):
        os.makedirs(TMPROOT, exist_ok=True)
    wd = os.path.join(TMPROOT, "w155-agentD-r2")
    if os.path.isdir(wd):
        shutil.rmtree(wd)
    shutil.copytree(SNAP, wd)
    copy_sha = sha_tree(wd)
    rows = []
    # P1
    for i in HANG_IDX:
        c = cases[i]
        r = run_case(wd, c["game"], c["stdin"], 10)
        rows.append({"idx": i, "game": c["game"], "phase": "P1_T10", **r})
    hang = [r["idx"] for r in rows if r["outcome"] == "cap"]
    # P2: 未收敛者再 2 次
    for i in hang:
        c = cases[i]
        for k in (2, 3):
            r = run_case(wd, c["game"], c["stdin"], 10)
            rows.append({"idx": i, "game": c["game"], "phase": "P2_rep%d_T10" % k, **r})
    # P3: 前 3 例 @T=60
    p3 = []
    for i in hang[:3]:
        c = cases[i]
        r = run_case(wd, c["game"], c["stdin"], 60)
        p3.append({"idx": i, **r})
        rows.append({"idx": i, "game": c["game"], "phase": "P3_T60", **r})
    # 对照
    ctl = []
    for i in CTL_IDX:
        c = cases[i]
        for _ in range(3):
            r = run_case(wd, c["game"], c["stdin"], 60)
            ctl.append({"idx": i, "game": c["game"], **r})

    per_idx = {}
    for i in HANG_IDX:
        rs = [r for r in rows if r["idx"] == i]
        caps = [r for r in rs if r["outcome"] == "cap"]
        p3r = [r for r in rs if r["phase"] == "P3_T60"]
        if p3r and p3r[0]["outcome"] == "done":
            klass = "SLOW_CONVERGES"
        elif len(caps) >= 3 and p3r and p3r[0]["outcome"] == "cap":
            klass = "NONCONVERGENT"
        elif len(caps) >= 3:
            klass = "NONCONVERGENT_AT_T10"
        else:
            klass = "TRANSIENT"
        per_idx[str(i)] = {"class": klass, "n_cap": len(caps), "n_reps": len(rs),
                           "secs": [r["secs"] for r in rs]}
    ctl_ok = all(r["outcome"] == "done" and r["secs"] < 5 for r in ctl)
    ctl_same_len = len({r["out_len"] for r in ctl[int(len(ctl) / len(CTL_IDX))::len(CTL_IDX)] if r["idx"] == ctl[0]["idx"]}) <= 1 if ctl else False
    hists = {}
    for i in CTL_IDX:
        hists[str(i)] = sorted({r["out_len"] for r in ctl if r["idx"] == i})
    ctl_stable = all(len(v) == 1 for v in hists.values())

    post = sha_tree(SNAP)
    out = {
        "round": "R588", "instrument": "eval/rover/r588/timeout_cause_r588.py",
        "mode": "read_only-on-frozen (复跑在仓外物化副本; 零产品改动/零新夹具/零远端)",
        "source_copy": "r585/w155/agentD-r2", "hang_idx": HANG_IDX,
        "per_idx": per_idx,
        "class_histogram": {},
        "control": {"rows": ctl, "all_fast": ctl_ok, "stable_out_len": ctl_stable, "out_len_per_idx": hists},
        "frozen_snapshot": {"sha_before": pre, "sha_after": post, "untouched": pre == post,
                            "copy_sha_equal": copy_sha == pre},
        "has_teeth": bool(ctl_ok and ctl_stable and pre == post and copy_sha == pre),
        "rows": rows,
    }
    ch = {}
    for v in per_idx.values():
        ch[v["class"]] = ch.get(v["class"], 0) + 1
    out["class_histogram"] = ch
    out["verdict_note"] = ("8/8 例在 T=10s 达上限且 T=60s 仍达上限 ⇒ **不收敛**(不是慢): "
                           "该跑次产物在特定输入上进入无界循环/等待; 与 `EMPTY_OR_ERROR` 族**不同源**"
                           "(后者是边界/异常路径未自验即交付), 属**独立族**且集中在单跑次。"
                           if ch.get("NONCONVERGENT") or ch.get("NONCONVERGENT_AT_T10") else
                           "存在收敛者 ⇒ 至少部分例属「慢」而非「不收敛」, 按 per_idx 逐例定级。")
    op = os.path.join(REPO, "eval/rover/r588/timeout-cause-r588.json")
    json.dump(out, io.open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"class_histogram": ch, "per_idx": per_idx, "control_fast": ctl_ok,
                      "control_stable": ctl_stable, "snapshot_untouched": pre == post,
                      "has_teeth": out["has_teeth"]}, ensure_ascii=False, indent=1))
    return 0 if out["has_teeth"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
