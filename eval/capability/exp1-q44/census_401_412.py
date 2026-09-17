#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q44 · C4 器具: R401–R412 状态回填 census (机械取来源, 取不到的如实标注).

判据: 每轮必须给出「证据来源集合」(存在/缺失可区分); 禁止凭记忆写轮次主题。
来源优先级: ① docs/plans/v0.*-r<NNN>-*.md (标题正文) ② docs/improvements.md 该轮节
            ③ eval/rover/r<NNN>/ (或 docs/reports/r<NNN>/) 目录与文件数
            ④ eval/capability/kpi.jsonl 该轮条目数
输出: backfill_401_412.json + 供人工审阅的紧凑表 (不直接写文档)。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ROUNDS = [f"R{n}" for n in range(401, 413)]


def read(path: str) -> str:
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def plan_docs(rnd: str) -> list[str]:
    pat = os.path.join(ROOT, "docs", "plans", f"*{rnd.lower()}*.md")
    out = [os.path.relpath(p, ROOT) for p in sorted(glob.glob(pat))]
    return out


def imp_section(rnd: str, text: str) -> list[str]:
    """improvements.md 里该轮的行 (含上下文标题的行在前)."""
    lines = text.splitlines()
    hits = []
    for i, l in enumerate(lines):
        if re.search(rf"\b{rnd}\b", l):
            head = l.strip()
            if head.startswith("#"):
                hits.append(head[:150])
            elif len(hits) < 2:
                hits.append(head[:150])
    return hits[:3]


def main() -> int:
    imp = read(os.path.join(ROOT, "docs", "improvements.md"))
    kpi_path = os.path.join(ROOT, "eval", "capability", "kpi.jsonl")
    kpi_txt = read(kpi_path) if os.path.exists(kpi_path) else ""
    rows = []
    for rnd in ROUNDS:
        d_rover = os.path.join(ROOT, "eval", "rover", rnd.lower())
        d_rep = os.path.join(ROOT, "docs", "reports", rnd.lower())
        ev = []
        for d in (d_rover, d_rep):
            if os.path.isdir(d):
                n = sum(len(f) for _, _, f in os.walk(d))
                ev.append({"path": os.path.relpath(d, ROOT), "files": n})
        pdocs = plan_docs(rnd)
        kpi_hits = len(re.findall(rf"\b{rnd}\b", kpi_txt))
        imp_hits = imp_section(rnd, imp)
        rows.append({
            "round": rnd,
            "evidence_dirs": ev,
            "plan_docs": pdocs,
            "improvements_lines": imp_hits,
            "kpi_mentions": kpi_hits,
            "has_evidence": bool(ev or pdocs),
        })
    out = {"source_root": ".", "rounds": rows,
           "summary": {"with_evidence": sum(1 for r in rows if r["has_evidence"]),
                       "missing": [r["round"] for r in rows if not r["has_evidence"]]}}
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backfill_401_412.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for r in rows:
        print(f"{r['round']}  ev={[e['path'] + ':' + str(e['files']) for e in r['evidence_dirs']] or '-'}"
              f"  plan={r['plan_docs'] or '-'}  kpi={r['kpi_mentions']}"
              f"  imp={r['improvements_lines'][:1]}")
    print(json.dumps(out["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
