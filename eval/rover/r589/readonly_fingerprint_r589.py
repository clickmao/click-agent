#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R589 N3 只读性指纹（器具面，非被测判据）。

与 N1 并池器**同一指纹口径**（直接 import，禁重写第二份实现）：
逐文件 `relpath|size|mtime` + 内容 sha256 聚合成一棵树的 sha256。
对照物 = N1 在己轮内取的 `sha_before/sha_after`（C5 断言：两者相同 ⇒ 本轮零写入）。
本器现值额外回答「N1 之后又跑过 C8/C9 三个只读器具，树是否仍逐位未动」。
"""
import hashlib, io, json, os, sys
REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "eval/rover/r589"))
from pool_taskface_r589 import fingerprint, ROUNDS  # noqa: E402

RUNS = os.path.expanduser("~/.agentframework/harness/runs")


def main():
    roots = [os.path.join(RUNS, r) for r in ROUNDS] + \
            [os.path.join(REPO, "eval/rover", r, "snapshots") for r in ROUNDS]
    n, h = fingerprint(roots)
    pool = json.load(io.open(os.path.join(REPO, "eval/rover/r589/taskface-pool-r589.json"), encoding="utf-8"))
    c5 = pool["C5_readonly"]
    out = {
        "round": "R589", "node": "N3", "mode": "read-only fingerprint (same criterion as N1)",
        "roots": [os.path.relpath(r, REPO) if r.startswith(REPO) else r.replace(os.path.expanduser("~"), "~") for r in roots],
        "files_now": n, "sha_now": h,
        "c5_before": c5["sha_before"], "c5_after": c5["sha_after"], "c5_files": c5["files"],
        "c5_pair_identical": c5["pass"],
        "now_equals_c5_after": (h == c5["sha_after"] and n == c5["files"]),
        "note": ("C5 断言（before==after）是**本轮零写入**的判据；`now_equals_c5_after` 额外证明 "
                 "N1 之后三个只读器具（C8/C9/N3 自身）也未改动这两棵树。mtime 计入指纹 ⇒ 逐位相等含 mtime。"),
    }
    out["rc"] = 0 if (c5["pass"] and out["now_equals_c5_after"]) else 2
    p = os.path.join(REPO, "eval/rover/r589/readonly-fingerprint-r589.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("files_now", "now_equals_c5_after", "rc")}, ensure_ascii=False))
    return out["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
