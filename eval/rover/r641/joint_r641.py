#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R641 · J4b **联合最小修复臂**（声明见 prereg-r641.json `addendum_J4b`，先于本臂起臂落盘）。

只跑 w239 两跑次的**合成缺陷**联合臂（单行臂的记录保留在 `out/attrib-r641.json`，不回写、不覆盖）。
零产品改动 / 零远端 / 只读（副本上执行）。
"""
from __future__ import annotations
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import attrib_r641 as M  # noqa: E402

JOINT = {
    "w239/agentP-r1": [
        {"id": "JOINT_L40+L47",
         "why": "`lower_wythoff` 合成缺陷：① 搜索区间 `lo, hi = n, 2n+1` ⇒ 谓词在 mid=n 处即假 ⇒ 循环零次（函数恒返回 n）② 返回只给 ⌊n/φ⌋ ⇒ 缺 +n 分量（⌊nφ⌋ = n + ⌊n/φ⌋）",
         "ops": [("    lo, hi = n, 2 * n + 1", "    lo, hi = 0, n"),
                 ("\n    return lo\n", "\n    return lo + n\n")]},
    ],
    "w239/agentP-r2": [
        {"id": "JOINT_L6+L32",
         "why": "DP 合成缺陷：① (0,0) 被 `continue` 跳过而**未入必败集**（DP 初值缺 ⇒ 整张必败集错位）② 着法选择判的是候选 (i,j) 自身是否在必败集，而非**落点** (a-i,b-j)",
         "ops": [("            if i == 0 and j == 0:\n                continue\n            win = ",
                  "            if i == 0 and j == 0:\n                los.add((i, j))\n                continue\n            win = "),
                 ("            if (i, j) not in los:\n                continue\n",
                  "            if (a - i, b - j) not in los:\n                continue\n")]},
    ],
}

out = {"round": "R641", "block": "J4b_joint_minfix", "kind": "readonly",
       "declared_in": "prereg-r641.json#addendum_J4b",
       "note": "只含联合臂；单行臂记录见 out/attrib-r641.json（不回写、不覆盖）",
       "cases_sha256": M.sha256(M.CASES), "blocks": []}
cases = M.load_cases()
for run, cands in JOINT.items():
    M.MINFIX[run] = cands
    b = M.minfix_run(run, cases)
    out["blocks"].append(b)
    print("[J4b]", run, b["confirmed"], "base_tgt=", b["baseline_families"]["wythoff"],
          "null_nc=", b["null_rewrite_negctl"]["pass"], flush=True)
out["summary"] = {
    "n_targets": len(out["blocks"]),
    "n_confirmed": sum(1 for x in out["blocks"] if x["confirmed"]),
    "null_negctl_pass": all(x["null_rewrite_negctl"]["pass"] for x in out["blocks"]),
    "residual_unattributed": [x["run"] for x in out["blocks"] if not x["confirmed"]],
}
io.open(os.path.join(M.OUTDIR, "joint-r641.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print("SUMMARY", json.dumps(out["summary"], ensure_ascii=False))
