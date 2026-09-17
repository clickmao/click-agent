#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R545 提交清单声明器 —— 先声明「本轮我改的路径」, 再与索引比对, 产出 /tmp/r545_manifest.txt。

纪律（EXP1-Q31 跨写者提交闸）: 清单只能包含**本轮我写过的**路径; 任何不在白名单内的 staged 路径 ⇒ 拒发清单(fail-closed),
防止兄弟写者在飞文件被 `git add` 混入提交。
"""
from __future__ import annotations
import io
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
OUT = "/tmp/r545_manifest.txt"

EXACT = [
    "src/agent/r1/PublicProbeResult.cs",
    "src/agent/r1/PublicExampleProbe.cs",
    "src/agent/r1/R1Pipeline.cs",
    "src/agent/r1/R1Transcript.cs",
    "src/agent.tests/R1PublicProbeTests.cs",
    "tools/r1gen/gen_csharp.py",
    "src/agent/contract/StructuredPrompt.cs",
    "docs/api-surface.baseline.txt",
    "docs/reports/r545-public-probe-trigger-face-v2.md",
    "docs/improvements.md",
    "docs/evidence/RF0001/EVIDENCE.md",
    "docs/evidence/RF0001/KPI.md",
    "eval/capability/kpi.jsonl",
    "eval/rover/r507pre/precondition-r545.json",
]
PREFIX = ["eval/rover/r545/"]


def staged() -> list[str]:
    p = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=REPO,
                       capture_output=True, text=True, check=True)
    return [l.strip() for l in p.stdout.splitlines() if l.strip()]


def main() -> int:
    st = staged()
    allowed, foreign = [], []
    for s in st:
        (allowed if (s in EXACT or any(s.startswith(p) for p in PREFIX)) else foreign).append(s)
    missing = [e for e in EXACT if e not in set(st)]
    print("staged=%d allowed=%d foreign=%d missing_declared=%d" % (len(st), len(allowed), len(foreign), len(missing)))
    if foreign or missing:
        for f in foreign:
            print("  FOREIGN (拒发清单): %s" % f)
        for m in missing:
            print("  MISSING (已声明未 staged): %s" % m)
        return 2
    io.open(OUT, "w", encoding="utf-8").write("# R545 本轮声明清单 (只含本轮自写路径)\n" + "\n".join(st) + "\n")
    back = [l.strip() for l in io.open(OUT, encoding="utf-8") if l.strip() and not l.startswith("#")]
    print("manifest -> %s (回读 %d 行)" % (OUT, len(back)))
    return 0 if len(back) == len(st) else 3


if __name__ == "__main__":
    sys.exit(main())
