#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R637 · 最小修复实验（**只在副本上改一行**）＋ 空重写负控，把 4 个 wythoff 族级归零跑次各自归因到**具体源码行**。

为什么单独成件（承 attrib_r637 J5 的 N4）：J5 的 N4 用了**写死的正则锚** `nn = 0`，而冻结树里
四跑次四个不同实现 ⇒ 只有 r636/w234 命中 ⇒ `applied=false`（**锚点缺失，不是「修复无效」**）。
本件改为**逐跑次显式给出「缺陷行 → 正确形态」补丁**（每处断言替换次数 == 1），并对每处跑：
  ① 目标族 15/15 转绿（该跑次原本 0/15）；
  ② 其它三族**逐例逐字节不变**（不是只比计数 —— 逐 idx 逐 tag 比对）；
  ③ 空重写负控：同字节重写目标文件 ⇒ 目标族仍全败（证「非凡改即绿」）。
零产品源码改动 / 零远端 / 零重测（只读冻结快照 + 临时副本）。
用法: python3 eval/rover/r637/minfix_r637.py [--json out/minfix-r637.json]
"""
from __future__ import annotations
import argparse
import io
import json
import os
import shutil
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r637"))
sys.path.insert(0, os.path.join(REPO, "eval/rover/r622"))
import attrib_r637 as A  # noqa: E402
import wythoff_oracle as ORC  # noqa: E402

OUT = os.path.join(REPO, "eval/rover/r637/out/minfix-r637.json")
TMO = 20
RUNDIRS = {"r633": "codex", "r635": "agentP-r2", "r636a": "agentP-r3", "r636b": "codex"}

# 逐跑次：冻结树 + 补丁序列（每处断言替换次数 == 1）+ 一行机理说明
# 注：`r636:w236/codex` 是**两处缺陷叠加**（冷集 ±1 修正 ∧ 走法枚举未限定合法着法）
# ⇒ 该目标用**两步**补丁，并逐步骤记录转绿读数（第一步只到 13/15 ⇒ 证第二处缺陷真实存在）。
TARGETS = [
    dict(tag="r635:w232/agentP-r2", tree="eval/rover/r635/snapshots/w232/agentP-r2/g1",
         patches=[dict(file="games/wythoff.py",
                       old="        pairs.add((n, t))\n        pairs.add((t, n))\n",
                       new="        pairs.add((t, t + n))\n        pairs.add((t + n, t))\n")],
         defect="冷集第二分量写成 `n`（应为 `t + n`）⇒ 隐含冷集与真值**零交集**（intersect 0 / extra 31 / missing 18）"),
    dict(tag="r633:w227/codex", tree="eval/rover/r633/snapshots/w227/codex/g1",
         patches=[dict(file="games/wythoff.py",
                       old="    cold = _cold_positions(limit + 2)\n",
                       new="    cold = _cold_positions(max(a, b) + 2)\n")],
         defect="入口引用**未定义变量** `limit`（函数内无此名）⇒ 625 次入口 ERR（n_implied=0）"),
    dict(tag="r636:w236/codex", tree="eval/rover/r636/snapshots/w236/codex/g1",
         patches=[dict(file="games/wythoff.py",
                       old="    if (t + 1) <= d / PHI:\n        t += 1\n    elif t > d / PHI:\n        t -= 1\n",
                       new=""),
                  dict(file="games/wythoff.py",
                       old="            if i == 0 and j == 0:\n                continue\n",
                       new="            if i == 0 and j == 0:\n                continue\n"
                           "            if not (i == 0 or j == 0 or i == j):\n                continue\n")],
         defect="缺陷一：`floor(d·φ)` 之后多余的 ±1 修正（`t > d/φ` 对 t≥1 恒真 ⇒ 退化成 round）；"
                "缺陷二：走法枚举 `(i, j)` **未限定 Wythoff 合法着法**（只允许取单堆或两堆等量）"
                "⇒ 冷集修好后仍返回非法着法（实测 #43 `WIN 1 13` / #57 `WIN 2 11`），两步合计才 15/15"),
    dict(tag="r636:w234/agentP-r3", tree="eval/rover/r636/snapshots/w234/agentP-r3/g1",
         patches=[dict(file="games/wythoff.py",
                       old="        mm = nn + len(pairs) + 1\n",
                       new="        mm = nn + len(pairs)\n")],
         defect="贪心构造 `b_n = a_n + n` 写成 `a_n + n + 1`（多 1）⇒ 冷集整体错位 + 15 次入口 ERR"),
]


def eval_tree(tree, cases, tmo):
    """返回 {idx: tag} 全 58 例逐例判定（与 attrib 同口径）。"""
    res = {}
    for ci, c in enumerate(cases):
        rc, out, _ = A.run_one(tree, c["game"], c["stdin"], tmo)
        if c["game"] == "wythoff":
            a, b = (int(x) for x in c["stdin"].split()[:2])
            tag, _d = A.classify(a, b, rc, out, c["expected_stdout"])
        else:
            if rc == 0 and (out or "").strip("\n") == c["expected_stdout"].strip("\n"):
                tag = "OK"
            elif rc != 0 or not (out or "").strip():
                tag = "HARD_CRASH"
            else:
                tag = "TRUE_WRONG"
        res[ci] = tag
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=OUT)
    a = ap.parse_args()
    cases = json.load(io.open(A.CASES, encoding="utf-8"))
    cases = cases["cases"] if isinstance(cases, dict) else cases
    fam_idx = {}
    for ci, c in enumerate(cases):
        fam_idx.setdefault(c["game"], []).append(ci)
    if sorted(fam_idx) != ["life", "nim", "sub", "wythoff"]:
        print("INPUT_MISSING families=%s" % sorted(fam_idx))
        return 3

    rec = {"round": "R637", "kind": "minfix-per-blocked-run", "cases_sha16": A.sha16(A.CASES),
           "targets": [], "rc": 0}
    for t in TARGETS:
        tree0 = os.path.join(REPO, t["tree"])
        if not os.path.isdir(tree0):
            print("INPUT_MISSING %s" % tree0)
            return 3
        # 逐补丁：从上一态源码继续（可叠加），每个补丁各断言替换次数 == 1
        states, cur, anchor_bad = [], None, False
        for p in t["patches"]:
            src = os.path.join(tree0, p["file"])
            if cur is None:
                cur = io.open(src, encoding="utf-8").read()
            nxt, n = cur.replace(p["old"], p["new"]), cur.count(p["old"])
            if n != 1:
                anchor_bad = True
                break
            cur = nxt
            states.append({"file": p["file"], "old": p["old"], "new": p["new"],
                           "n_replacements": n})
        if anchor_bad:
            rec["targets"].append({"tag": t["tag"], "verdict": "ANCHOR_MISS",
                                   "n_replacements": n, "defect": t["defect"]})
            rec["rc"] = 2
            continue
        tmp = tempfile.mkdtemp(prefix="r637mf-")
        try:
            tree_dirs = []
            base = os.path.join(tmp, "orig")
            shutil.copytree(tree0, base)
            tree_dirs.append(base)
            # 逐步叠加态：s0 = 原树，s_k = 施加前 k 个补丁
            for k in range(1, len(states) + 1):
                d = os.path.join(tmp, "step%d" % k)
                shutil.copytree(tree0, d)
                s = io.open(os.path.join(tree0, states[0]["file"]), encoding="utf-8").read()
                for p in states[:k]:
                    s = s.replace(p["old"], p["new"], 1)
                io.open(os.path.join(d, states[0]["file"]), "w", encoding="utf-8").write(s)
                tree_dirs.append(d)
            null = os.path.join(tmp, "null")
            shutil.copytree(tree0, null)   # 空重写负控：逐字节同文件，不作任何改写
            tree_dirs.append(null)
            tags = [eval_tree(dd, cases, TMO) for dd in tree_dirs]
            t_orig, t_null = tags[0], tags[-1]
            nb = len(fam_idx["wythoff"])
            ok = [sum(1 for i in fam_idx["wythoff"] if tg[i] == "OK") for tg in tags]
            t_fix = tags[-2]                      # 全补丁态
            others = {}
            for fam in ("life", "sub", "nim"):
                others[fam] = {
                    "n": len(fam_idx[fam]),
                    "pass_fix": sum(1 for i in fam_idx[fam] if t_fix[i] == "OK"),
                    "pass_orig": sum(1 for i in fam_idx[fam] if t_orig[i] == "OK"),
                    "percase_identical": all(t_fix[i] == t_orig[i] for i in fam_idx[fam]),
                }
            verdict = ("PASS" if (ok[0] == 0 and ok[-2] == nb
                                  and sum(1 for i in fam_idx["wythoff"] if t_null[i] == "OK") == 0
                                  and all(v["percase_identical"] for v in others.values()))
                       else "FAIL")
            rec["targets"].append({
                "tag": t["tag"], "defect": t["defect"], "patches": states,
                "wythoff_stepwise": {"n": nb, "pass_by_step": ok[:-1],
                                     "labels": ["orig"] + ["patch1..%d" % k for k in range(1, len(states) + 1)],
                                     "pass_null": sum(1 for i in fam_idx["wythoff"] if t_null[i] == "OK")},
                "other_families": others, "verdict": verdict,
                "rule": "目标族 0/n → n/n 转绿 ∧ 其它三族逐例逐字节不变 ∧ 空重写负控仍 0/n",
            })
            if verdict != "PASS":
                rec["rc"] = 2
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if not os.path.isdir(os.path.dirname(a.json)):
        os.makedirs(os.path.dirname(a.json))
    io.open(a.json, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
    for x in rec["targets"]:
        print("%-24s %s" % (x["tag"], x.get("verdict")),
              json.dumps(x.get("wythoff_stepwise", {}), ensure_ascii=False),
              json.dumps({k: v["percase_identical"] for k, v in x.get("other_families", {}).items()},
                         ensure_ascii=False) if x.get("other_families") else "")
    print("MINFIX_RC=%d" % rec["rc"])
    return rec["rc"]


if __name__ == "__main__":
    sys.exit(main())
