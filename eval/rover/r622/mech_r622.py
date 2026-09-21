#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R622 · 失败例**机制归因**探针 v2（行为式谓词，只读、零写入）。

v1 用「产物是否暴露 `_losing` 类函数」做自省 ⇒ 45.3% 落 `NO_PRED`（弱证据桶）。
v2 改成**行为式**探针：任何产物都能问它**自己的接口**「这个局面你是不是判必败」
  tree_says_LOSE(x,y) ⇔ `python3 -m games wythoff` 在输入 "x y" 上输出 `LOSE`
（= 该产物自己的冷点判定，无需它暴露任何函数名）。

对每个失败实例（来自 out/percase-r622.json，tag != OK）取两点：
  真冷点落点 T*  = oracle 的字典序最小着法之落点 (a-i*, b-j*)
  自选落点  T̂   = 该跑次实际报出的着法之落点 (a-i, b-j)
分型（互斥、覆盖 100% 非崩实例）:
  CRASH              产物在该例上非零退出
  ILLEGAL_MOVE       自选着法非法（超量 / 两堆取不同数 / 零着法）
  COLD_PRED_WRONG    **该产物自己说 T̂ 是必败位**（或说 T* 是必胜位）⇒ 判定层（冷点谓词/表）错
  ENUM_ORDER         该产物说 T* 是必败位、且说 T̂ 是必胜位 ⇒ 判定层对、选点/枚举不按自己的判定走
  UNCLASSIFIED       以上皆非（保留原样入档, 不强行归桶）
"""
from __future__ import annotations
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r622"))
import wythoff_oracle as ORC  # noqa: E402

SNAPS = os.path.join(REPO, "eval/rover/r621/snapshots")
TMO = 10.0


def tree_solve(tree: str, a: int, b: int):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": tree,
           "PYTHONPATH": tree, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        p = subprocess.run([sys.executable, "-B", "-m", "games", "wythoff"],
                           input="%d %d\n" % (a, b), capture_output=True, text=True,
                           timeout=TMO, cwd=tree, env=env)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()[-160:]
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # noqa: BLE001
        return 125, "", type(e).__name__


def legal(a, b, i, j):
    if i < 0 or j < 0 or i > a or j > b or (i == 0 and j == 0):
        return False
    return i == j or i == 0 or j == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp",
                    default=os.path.join(REPO, "eval/rover/r622/out/percase-r622.json"))
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r622/out/mech-r622.json"))
    args = ap.parse_args()
    d = json.load(io.open(args.inp, encoding="utf-8"))
    fails = [r for r in d["rows"] if r["tag"] != "OK"]

    tmp = tempfile.mkdtemp(prefix="r622mech-")
    trees, rows, tally = {}, [], {}
    try:
        for r in fails:
            key = (r["win"], r["arm_id"])
            if key not in trees:
                dst = os.path.join(tmp, "%s_%s" % key)
                shutil.copytree(os.path.join(SNAPS, r["win"], r["arm_id"], "g1"), dst)
                trees[key] = dst
            tree = trees[key]
            a, b = r["a"], r["b"]
            i = j = None
            if r["got"].startswith("WIN"):
                parts = r["got"].split()
                if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                    i, j = int(parts[1]), int(parts[2])
            wm = ORC.winning_moves(a, b)
            oi, oj = (min(wm) if wm else (None, None))
            rec = {"win": r["win"], "arm": r["arm"], "arm_id": r["arm_id"], "case": r["case"],
                   "a": a, "b": b, "tag": r["tag"], "got": r["got"],
                   "oracle_move": None if oi is None else [oi, oj]}
            rc0, out0, _ = tree_solve(tree, a, b)
            rec["tree_rc"] = rc0
            if rc0 != 0:
                rec["mech"] = "CRASH"
            else:
                t_star = tree_solve(tree, a - oi, b - oj)[1] if oi is not None else None
                t_hat = tree_solve(tree, a - i, b - j)[1] if i is not None else None
                lost = lambda s: (s or "").startswith("LOSE")
                won = lambda s: (s or "").startswith("WIN")
                rec["tree_says_target_star"] = t_star        # LOSE ⇒ 它认这是必败位（对）
                rec["tree_says_chosen"] = t_hat
                if lost(out0):
                    # 产物自报「本局面必败」而 oracle 判必胜 ⇒ 判定层（冷点谓词/表）错
                    rec["mech"] = "COLD_PRED_WRONG"
                elif i is None or not legal(a, b, i, j):
                    rec["mech"] = "ILLEGAL_MOVE"
                elif lost(t_hat):
                    rec["mech"] = "COLD_PRED_WRONG"
                elif won(t_star):
                    rec["mech"] = "COLD_PRED_WRONG"
                elif lost(t_star) and won(t_hat):
                    rec["mech"] = "ENUM_ORDER"
                else:
                    rec["mech"] = "UNCLASSIFIED"
            tally[rec["mech"]] = tally.get(rec["mech"], 0) + 1
            rows.append(rec)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps({"taxonomy": "v2-behavioral", "tally": tally, "rows": rows},
                   ensure_ascii=False, indent=1))
    tot = sum(tally.values())
    print("机制归因 v2（失败实例 %d，行为式谓词）:" % tot)
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("  %-20s %3d  %5.1f%%" % (k, v, 100.0 * v / tot))
    by_arm = {}
    for r in rows:
        by_arm.setdefault(r["arm"], {}).setdefault(r["mech"], 0)
        by_arm[r["arm"]][r["mech"]] += 1
    for arm, tg in sorted(by_arm.items()):
        n = sum(tg.values())
        print("   %-3s n=%3d  %s" % (arm, n, json.dumps(tg, ensure_ascii=False)))
    # 判定层分辨率（单列）：产物能否认出真冷点
    res = {}
    for r in rows:
        if r.get("tree_says_target_star") is not None and r["mech"] != "CRASH":
            res.setdefault(r["arm"], [0, 0])
            res[r["arm"]][1] += 1
            if (r["tree_says_target_star"] or "").startswith("LOSE"):
                res[r["arm"]][0] += 1
    print("   判定层分辨率（认出真冷点的失败实例数 / 可判实例）:", json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
