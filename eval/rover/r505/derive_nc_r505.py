#!/usr/bin/env python3
"""机械派生 nc_r505.sh = nc_r504.sh + 显式命名空间/判分器替换（逐条列出, 可审计）。

理由: 负控内容(R504 判据器)不变, 只换命名空间与产物路径; 派生而非重写 ⇒ 控制内容逐字节可比。
产出: eval/rover/r505/nc_r505.sh + eval/rover/r505/evidence/nc-derive-r505.json（替换台账 + 两侧 sha256）
"""
from __future__ import annotations

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(REPO, "eval/rover/r504/nc_r504.sh")
DST = os.path.join(HERE, "nc_r505.sh")

SWAPS = [
    ("# R504 负控 (全部本地, 不吃真机窗)", "# R505 负控 (机械派生自 r504/nc_r504.sh; 全部本地, 不吃真机窗)"),
    ("D=${R504_ENV:-/tmp/r504_env}", "D=${R505_ENV:-/tmp/r505_nc}"),
    ("PRE=eval/rover/r504/prereg_r504.json", "PRE=eval/rover/r505/prereg_r505.json"),
    ("[R504-NC]", "[R505-NC]"),
    ("eval/rover/r504/make_prereg_r504.py", "eval/rover/r505/make_prereg_r505.py"),
    ("eval/rover/r504/judge_contrast_r504.py", "eval/rover/r505/judge_contrast_r505.py"),
    ("eval/rover/r504/taskset-r504nc", "eval/rover/r505/taskset-r505nc"),
    ("r504nc-", "r505nc-"),
    ("nc-r504.json", "nc-r505.json"),
]


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main() -> int:
    src = open(SRC, encoding="utf-8").read()
    out = src
    counts = {}
    for a, b in SWAPS:
        n = out.count(a)
        counts[a] = n
        out = out.replace(a, b)
    assert "r504_env" not in out and "prereg_r504" not in out, "替换不完整"
    assert "codex_solver_r504.py" in out, "codex solver 路径必须保持不变(同仪器)"
    open(DST, "w", encoding="utf-8").write(out)
    os.chmod(DST, 0o755)
    rec = {"src": os.path.relpath(SRC, REPO), "dst": os.path.relpath(DST, REPO),
           "src_sha256": sha(SRC), "dst_sha256": sha(DST),
           "swaps": [{"from": a, "to": b, "n": counts[a]} for a, b in SWAPS],
           "invariant": "判据器/负控内容不变; 仅命名空间+判分器+预注册+产物名替换"}
    ev = os.path.join(HERE, "evidence/nc-derive-r505.json")
    json.dump(rec, open(ev, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
