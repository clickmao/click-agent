#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R590 N5 只读性指纹（器具面，非被测判据）。

与 R589 并池器**同一指纹口径**（直接 import `pool_taskface_r589.fingerprint`，禁重写第二份实现）：
逐文件 `relpath|size|mtime` + 内容 sha256 聚合成一棵树的 sha256。

对照物分两层（比 R589 的轮内 before/after **更强**）：
① R589 轮内已登记的 `c5_before == c5_after`（同轮零写入）；
② **跨轮不变式**：本轮（R590）全器具跑完后的现值 == R589 登记值
   ⇒ 覆盖了两轮之间的空档 —— 即 R590 的普查器 / 余量派生器 / 前置器口径器 / 起手闸
     **一件都没有改动只读面**。
mtime 计入指纹 ⇒ 逐位相等含 mtime（任何写都会改 mtime）。
"""
from __future__ import annotations

import hashlib  # noqa: F401 — 与并池器同口径，此处不重实现
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
sys.path.insert(0, os.path.join(REPO, "eval/rover/r589"))
from pool_taskface_r589 import fingerprint, ROUNDS  # noqa: E402


def main():
    roots = [os.path.join(RUNS, r) for r in ROUNDS] + \
            [os.path.join(REPO, "eval/rover", r, "snapshots") for r in ROUNDS]
    n, h = fingerprint(roots)
    prev = json.load(io.open(os.path.join(REPO, "eval/rover/r589/readonly-fingerprint-r589.json"),
                             encoding="utf-8"))
    out = {
        "round": "R590", "node": "N5",
        "mode": "read-only fingerprint (same criterion as R589 N1/N3)",
        "roots": [os.path.relpath(r, REPO) if r.startswith(REPO) else r.replace(os.path.expanduser("~"), "~")
                  for r in roots],
        "files_now": n, "sha_now": h,
        "r589_files": prev.get("files_now"), "r589_sha": prev.get("sha_now"),
        "r589_within_round_before_after_identical": prev.get("c5_pair_identical"),
        "cross_round_invariant": (h == prev.get("sha_now") and n == prev.get("files_now")),
        "note": ("`cross_round_invariant` = 两轮之间的空档 + 本轮全部器具均未改动只读面。"
                 "mtime 计入指纹 ⇒ 逐位相等含 mtime。"),
    }
    out["rc"] = 0 if (out["r589_within_round_before_after_identical"] and out["cross_round_invariant"]) else 2
    if out["rc"] != 0:
        out["rc_reason"] = "只读面被本轮器具改动（跨轮不变式不成立）⇒ 器具缺陷"
    p = os.path.join(REPO, "eval/rover/r590/readonly-fingerprint-r590.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("files_now", "cross_round_invariant", "rc")}, ensure_ascii=False))
    return out["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
