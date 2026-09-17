#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R529 J2c (B3 负控): **历史轮不回归** —— 加策略后重跑 R528, rc 与验收面必须逐字段不变。

机检项: rc / accepted / acceptable_scoped / blocked / blocked_scoped(排序后) / windows.*.arms correct 全等。
差异 ⇒ 打印 DIFF 行并 rc=1 (策略实现污染了历史轮 ⇒ 该实现作废)。"""
import json, io, os, subprocess, sys

REPO = "/home/agentuser/AgentFramework"
OLD = "/tmp/exe_pre_r529_HEAD.py"
NEW = os.path.join(REPO, "eval/rover/r507pre/exec_precondition.py")
RID = "r528"


def run(exe, out):
    p = subprocess.run([sys.executable, exe, "--round", RID, "--out", out],
                       cwd=REPO, capture_output=True, text=True, timeout=3600)
    j = {}
    if os.path.isfile(out):
        j = json.load(io.open(out, encoding="utf-8"))
    return {"rc": p.returncode, "json": j, "tail": (p.stdout or "").strip().splitlines()[-2:]}


def face(j):
    return {
        "accepted": j.get("accepted"),
        "acceptable_scoped": j.get("acceptable_scoped"),
        "blocked": sorted(j.get("blocked") or []),
        "blocked_scoped": sorted(j.get("blocked_scoped") or []),
        "arms_correct": {w: {k: bool(v.get("correct")) for k, v in (r.get("arms") or {}).items()}
                         for w, r in (j.get("windows") or {}).items()},
    }


def main():
    head = subprocess.run(["git", "show", "HEAD:eval/rover/r507pre/exec_precondition.py"],
                          cwd=REPO, capture_output=True, text=True, check=True).stdout
    io.open(OLD, "w", encoding="utf-8", newline="\n").write(head)
    o = run(OLD, "/tmp/pre_r528_old.json")
    n = run(NEW, "/tmp/pre_r528_new.json")
    fo, fn = face(o["json"]), face(n["json"])
    diffs = [k for k in fo if fo[k] != fn[k]]
    out = {"round": RID, "old_rc": o["rc"], "new_rc": n["rc"], "old_exe": OLD,
           "new_exe": NEW, "fields_compared": sorted(fo), "diffs": diffs,
           "invariant_ok": (o["rc"] == n["rc"] and not diffs),
           "new_policy_key": (n["json"].get("policy") is not None),
           "old_has_policy_key": (o["json"].get("policy") is not None),
           "new_declared_absent": n["json"].get("declared_absent"),
           "new_tail": n["tail"], "old_tail": o["tail"]}
    p = os.path.join(REPO, "eval/rover/r529/evidence/nc-historical-round-r529.json")
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("OLD_RC=%s NEW_RC=%s diffs=%s invariant_ok=%s policy_key_new=%s policy_key_old=%s"
          % (o["rc"], n["rc"], diffs, out["invariant_ok"], out["new_policy_key"], out["old_has_policy_key"]))
    for k in diffs:
        print("DIFF", k, "old=", json.dumps(fo[k], ensure_ascii=False)[:400])
        print("DIFF", k, "new=", json.dumps(fn[k], ensure_ascii=False)[:400])
    print("OUT=" + p)
    return 0 if out["invariant_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
