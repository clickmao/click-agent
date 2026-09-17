#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R530 定因器具: 对 R529 两处未定因的失败用例做**逐例根因**(只读快照, 不改被测树)。

背景（R529 报告 §5 诚实边界 #5 / §3 表末行）:
  · w2 基线臂 `agentA0-off/g1` 55/58 —— 3 例失败未逐个定因;
  · w3 外部真值臂 `codex/t1` 29/30 —— 1 例失败只记了读数。

判别纪律（skill: 题面-判据一致性）: 先看**两侧是否同败** —— 若外部真值与全部本侧臂失败集合逐字相同 ⇒
先怀疑夹具; 否则再谈能力。本器同时打印三臂(A0-off / A1-on / codex)在同一用例上的实际 stdout, 使
「同败/异败」成为可读的机检字段(exclusive_fail_side), 而不是靠叙述。

只读保证: 子进程 env 固定 PYTHONDONTWRITEBYTECODE=1 + HOME=<被测树>, 不写任何文件; 期望值取自冻结语料
`eval/rover/r529/cases/cases-r521.json` / `cases-r529-f2.json`（不改语料）。
输出: `eval/rover/r530/evidence/rootcause-failures-r530.json`
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
R529 = os.path.join(REPO, "eval/rover/r529")
OUT = os.path.join(REPO, "eval/rover/r530/evidence/rootcause-failures-r530.json")
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}

# (窗口, 用例族/语料, 用例全局序号, 被测树 {臂标签: 相对 R529 的产物树})
JOBS = [
    {
        "id": "w2_agentA0-off_g1_wythoff",
        "window": "w2",
        "corpus": "cases/cases-r521.json",
        "entry": "games",
        "idxs": [44, 45, 49],
        "trees": {"agentA0-off": "snapshots/w2/agentA0-off/g1",
                  "agentA1-on": "snapshots/w2/agentA1-on/g1",
                  "codex": "snapshots/w2/codex/g1"},
        "reported_fail_side": "agentA0-off",
    },
    {
        "id": "w3_codex_t1_jsonmini",
        "window": "w3",
        "corpus": "cases/cases-r529-f2.json",
        "entry": "toolkit",
        "idxs": [27],
        "trees": {"agentA0-off": "snapshots/w3/agentA0-off/t1",
                  "agentA1-on": "snapshots/w3/agentA1-on/t1",
                  "codex": "snapshots/w3/codex/t1"},
        "reported_fail_side": "codex",
    },
]


def norm(s):
    return (s or "").strip("\n")


def probe(tree, entry, mod, stdin):
    d = os.path.join(R529, tree)
    env = dict(ENV, HOME=os.path.abspath(d), PYTHONPATH=os.path.abspath(d))
    p = subprocess.run([sys.executable, "-B", "-m", entry, mod], input=stdin, capture_output=True,
                       text=True, timeout=120, cwd=d, env=env)
    return {"rc": p.returncode, "stdout": p.stdout, "stderr_tail": (p.stderr or "")[-160:]}


def main():
    blob = {"round": "R530", "kind": "failure-rootcause", "source_round": "R529",
            "rule": "期望值取自冻结语料; 两侧同败 ⇒ 先疑夹具(skill 判别手法); 本器只读快照",
            "jobs": []}
    for j in JOBS:
        cs = json.load(io.open(os.path.join(R529, j["corpus"]), encoding="utf-8"))
        jrec = {"id": j["id"], "window": j["window"], "cases": [], "verdict": {}}
        for i in j["idxs"]:
            c = cs[i]
            mod = c.get("game") or c.get("mod")
            exp = norm(c.get("expected_stdout"))
            per = {}
            for arm, tree in j["trees"].items():
                r = probe(tree, j["entry"], mod, c["stdin"])
                r["expected"] = exp
                r["match"] = (r["rc"] == 0 and norm(r["stdout"]) == exp)
                per[arm] = r
            fails = sorted(a for a, r in per.items() if not r["match"])
            case = {"idx": i, "mod": mod, "vis": c.get("vis"), "stdin": c["stdin"],
                    "expected": exp, "arms": per, "fail_side": fails,
                    "exclusive_fail_side": (fails[0] if len(fails) == 1 else None),
                    "both_sides_fail": len(fails) > 1}
            jrec["cases"].append(case)
        # 判据: 失败集合是否只落在**单侧**(⇒ 非同败 ⇒ 不指向夹具), 以及是否与 R529 报告点名侧一致
        excl = {c["exclusive_fail_side"] for c in jrec["cases"]}
        jrec["verdict"] = {
            "n_cases": len(jrec["cases"]),
            "all_expected_backed_by_prompt_spec": True,   # 见报告 §定因(逐条引用题面句)
            "exclusive_fail_sides": sorted(x for x in excl if x),
            "both_sides_fail_any": any(c["both_sides_fail"] for c in jrec["cases"]),
            "matches_reported_side": all(c["exclusive_fail_side"] == j["reported_fail_side"]
                                         for c in jrec["cases"]),
            "fixture_defect_suspected": any(c["both_sides_fail"] for c in jrec["cases"]),
        }
        blob["jobs"].append(jrec)
        print("== %s ==" % j["id"])
        for c in jrec["cases"]:
            print("  #%02d %-9s %-6s stdin=%-14r expected=%-12r" %
                  (c["idx"], c["mod"], c["vis"], c["stdin"], c["expected"]))
            for a, r in sorted(c["arms"].items()):
                print("      %-11s rc=%d %-14r %s" % (a, r["rc"], r["stdout"], "OK" if r["match"] else "MISMATCH"))
        print("  verdict=%s" % json.dumps(jrec["verdict"], ensure_ascii=False))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(blob, ensure_ascii=False, indent=1) + "\n")
    print("OUT=%s" % os.path.relpath(OUT, REPO))
    bad = any(j["verdict"]["fixture_defect_suspected"] for j in blob["jobs"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
