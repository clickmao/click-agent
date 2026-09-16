#!/usr/bin/env python3
"""R505 证据可重放检查器（判据 H9 的取证器 / R504 缺陷的检出器）。

缺陷背景（R504 实测, 本轮机检坐实）:
  `eval/rover/r455/adapter_tools.py` 的文件名是 `side-<side>-<NNN>.json`, NNN 是**进程内计数器**,
  落盘目录取 `DEMO_OUT`。R504 的候选② 脚本（cand2_vmrun_n3.sh）**复用同一个 DEMO_OUT**,
  新进程计数器从 001 重来 ⇒ **静默覆盖**已判分的 side-agent-001..009.json
  ⇒ 判分当时的读数（verdict-r504.json: agent 17 调用 / 94,802 tok）在盘上**不可重放**。

本检查器把「冻结读数 vs 现存文件」做成机械断言:
  输入 --usage  = runner 在**阶段结束时立即**落盘的逐调用清单（file side in out model）
       --dir    = 现存 adapter 目录（或快照目录）
  判定: 清单每一行的 in/out 必须与现存文件逐位相同; 文件缺失或数值不同 ⇒ 报 MISMATCH ⇒ rc=2
  fail-closed: 清单/目录缺失 ⇒ rc=3（不得算过）

rc: 0 可重放; 2 不可重放（点名到文件）; 3 输入缺失
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

LINE = re.compile(r"^(side-\w+-\d+\.json)\s+side=(\w+)\s+in=(\d+|None)\s+out=(\d+|None)\s+model=(\S+)")


def parse_usage(path: str):
    rows = {}
    for ln in open(path, encoding="utf-8-sig"):
        m = LINE.match(ln.strip())
        if m:
            rows[m.group(1)] = (None if m.group(3) == "None" else int(m.group(3)),
                                None if m.group(4) == "None" else int(m.group(4)))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--usage", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if not os.path.exists(a.usage):
        print("[致命] 缺冻结清单: %s ⇒ fail-closed (rc=3)" % a.usage)
        return 3
    if not os.path.isdir(a.dir):
        print("[致命] 缺目录: %s ⇒ fail-closed (rc=3)" % a.dir)
        return 3

    rows = parse_usage(a.usage)
    if not rows:
        print("[致命] 冻结清单无有效行 ⇒ fail-closed (rc=3)")
        return 3

    mismatch, missing, extra = [], [], []
    for f, (i, o) in sorted(rows.items()):
        p = os.path.join(a.dir, f)
        if not os.path.exists(p):
            missing.append(f)
            continue
        d = json.load(open(p, encoding="utf-8-sig"))
        u = ((d.get("response") or {}).get("usage") or {})
        ci = u.get("prompt_tokens") if u.get("prompt_tokens") is not None else u.get("input_tokens")
        co = u.get("completion_tokens") if u.get("completion_tokens") is not None else u.get("output_tokens")
        ci = None if ci is None else int(ci)
        co = None if co is None else int(co)
        if (ci, co) != (i, o):
            mismatch.append({"file": f, "frozen": {"in": i, "out": o}, "now": {"in": ci, "out": co}})
    for f in sorted(os.listdir(a.dir)):
        if f.startswith("side-") and f.endswith(".json") and f not in rows:
            extra.append(f)

    ok = not (mismatch or missing)
    res = {"usage": a.usage, "dir": a.dir, "n_frozen": len(rows), "replayable": ok,
           "mismatch": mismatch, "missing": missing, "extra_files": extra}
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    for m in mismatch:
        print("MISMATCH %s frozen in=%s out=%s -> now in=%s out=%s" % (
            m["file"], m["frozen"]["in"], m["frozen"]["out"], m["now"]["in"], m["now"]["out"]))
    for f in missing:
        print("MISSING  %s" % f)
    if extra:
        print("EXTRA(非清单文件, 只报不判红) %d: %s" % (len(extra), ", ".join(extra[:6])))
    print("证据可重放: %s (清单 %d 行, 失配 %d, 缺失 %d)" % (
        "PASS" if ok else "FAIL", len(rows), len(mismatch), len(missing)))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
