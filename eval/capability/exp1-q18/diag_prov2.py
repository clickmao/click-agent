#!/usr/bin/env python3
"""打印 Q18 两次 Q17-检查器输出的 readings 结构 (定位分类计数字段)。"""
import json
import pathlib

Q18 = pathlib.Path(__file__).resolve().parent
for tag in ("v270", "v260"):
    p = Q18 / ("verdict_q18_provenance.json" if tag == "v270" else "verdict_q18_provenance_old.json")
    d = json.loads(p.read_text(encoding="utf-8"))
    print("=" * 70)
    print(tag, "exit_code", d.get("exit_code"), "determinism", json.dumps(d.get("determinism"), ensure_ascii=False)[:120])
    print("checks:", json.dumps(d.get("checks"), ensure_ascii=False)[:400])
    r = d.get("readings")
    print("readings type", type(r).__name__)
    if isinstance(r, dict):
        for k, v in r.items():
            s = json.dumps(v, ensure_ascii=False)
            print("  ", k, "=", s[:300])
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if any(t in str(k2) for t in ("class", "count", "size", "sum", "omission", "unhit")):
                        print("       .", k2, "=", json.dumps(v2, ensure_ascii=False)[:260])
