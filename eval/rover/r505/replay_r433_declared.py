#!/usr/bin/env python3
"""R505 候选④: 闭合 r433 行证据面重放缺口。

R504 的缺口: 重放夹具只跑了 `--glob 'data/probe/probe-*r433*.json'`, **漏掉行内声明的 `--run <基线>`**
⇒ 复现 8 行（缺 `probe-m6-agent.json`）⇒ 记为 PASS_DECLARED_GAP。
本夹具改为**逐字执行行内声明的命令**, 并以「删掉 `--run` 那一版」作前态负控（必须恰好复现缺口 ⇒ 闭合非空心）。

用法: python3 eval/rover/r505/replay_r433_declared.py
rc: 0 闭合且负控成立; 1 比对不上; 3 fail-closed（找不到行/缺冻结面）
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FROZEN = os.path.join(REPO, "eval/capability/r433/kpi-report.md")
REG = os.path.join(REPO, "docs/verification-registry.json")
OUT = os.path.join(HERE, "evidence", "replay-r433-closure-r505.json")
SCRATCH = "/tmp/r505_replay_r433"


def run(cmd):
    p = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def rows(path):
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.startswith("| "):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 6 and re.match(r"^\d+$", c[0] or ""):
            out[c[0]] = tuple(c)
    return out


def main() -> int:
    reg = json.load(open(REG, encoding="utf-8-sig"))
    cmd = None
    rid = None
    for row in reg if isinstance(reg, list) else reg.get("rows", []):
        ec = (row or {}).get("evidence_cmd") or ""
        if "r433" in ec and "kpi_probe" in ec:
            cmd, rid = ec, row.get("id")
            break
    if not cmd:
        print("[致命] 注册表行内找不到 r433 证据命令 ⇒ rc=3")
        return 3
    if not os.path.exists(FROZEN):
        print("[致命] 缺冻结报告 ⇒ rc=3")
        return 3
    os.makedirs(SCRATCH, exist_ok=True)
    replay = os.path.join(SCRATCH, "declared.md")
    pre = os.path.join(SCRATCH, "prestate.md")
    cmd_declared = re.sub(r"--report\s+\S+", "--report %s" % replay, cmd)
    # 前态臂 = R504 老夹具逐字跑的那一版（只有 --glob, 无 --run/--compare）; R504 实测 = 8 行（缺基线行）
    cmd_pre = ("python3 scripts/kpi_probe.py --glob 'data/probe/probe-*r433*.json' "
               "--report %s --no-ledger" % pre)

    rc1, o1 = run(cmd_declared)
    rc2, o2 = run(cmd_pre)
    fr, dr, pr = rows(FROZEN), rows(replay), rows(pre)
    diffs = [k for k in fr if k in dr and fr[k] != dr[k]]
    rec = {
        "round": "R505", "row": rid,
        "declared_cmd": cmd,
        "declared_replay": {"rc": rc1, "rows": len(dr), "path": replay, "tail": o1.strip().splitlines()[-2:]},
        "frozen": {"rows": len(fr), "path": os.path.relpath(FROZEN, REPO)},
        "missing": sorted(set(fr) - set(dr)), "extra": sorted(set(dr) - set(fr)),
        "drifted_rows": diffs,
        "prestate_negative_control": {"rc": rc2, "rows": len(pr),
                                      "missing": sorted(set(fr) - set(pr)),
                                      "expect": "恰好缺 probe-m6-agent.json 一行（8 行）",
                                      "tail": o2.strip().splitlines()[-2:]},
        "closure": bool(len(dr) == len(fr) and not diffs and not (set(fr) - set(dr))),
        "negative_control_ok": bool(len(pr) == len(fr) - 1),
    }
    rec["pass"] = rec["closure"] and rec["negative_control_ok"]
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("行=%s | 逐字执行声明命令: rc=%d 行数 %d/%d 漂移 %d 缺 %s" % (
        rid, rc1, len(dr), len(fr), len(diffs), sorted(set(fr) - set(dr)) or "-"))
    print("前态负控(删 --run): rc=%d 行数 %d (期望 %d) 缺 %s" % (
        rc2, len(pr), len(fr) - 1, sorted(set(fr) - set(pr)) or "-"))
    print("闭合=%s 负控=%s ⇒ %s" % (rec["closure"], rec["negative_control_ok"],
                                     "PASS" if rec["pass"] else "NOT"))
    print("证据 -> %s" % os.path.relpath(OUT, REPO))
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())