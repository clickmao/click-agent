#!/usr/bin/env python3
"""打印 Q18 两次 Q17-检查器输出的分类与键处置。"""
import json
import pathlib

Q18 = pathlib.Path(__file__).resolve().parent
for tag in ("v270", "v260"):
    p = Q18 / ("verdict_q18_provenance.json" if tag == "v270" else "verdict_q18_provenance_old.json")
    d = json.loads(p.read_text(encoding="utf-8"))
    print("=" * 70)
    print(tag, p.name, "| top keys:", sorted(d.keys())[:14])
    cc = d.get("class_counts") or (d.get("provenance") or {}).get("class_counts")
    print("class_counts:", json.dumps(cc, ensure_ascii=False))
    for k in ("A_size", "D_size", "P_size", "sum_check", "conserved", "totals"):
        if k in d:
            print(" ", k, "=", json.dumps(d[k], ensure_ascii=False)[:200])
    cbk = d.get("class_by_key") or (d.get("provenance") or {}).get("class_by_key") or {}
    om = sorted(k for k, v in cbk.items() if "omission" in str(v))
    bu = sorted(k for k, v in cbk.items() if "branch_unhit" in str(v))
    print("  omission keys (%d):" % len(om), om)
    print("  branch_unhit keys (%d):" % len(bu), bu)
    arch = d.get("archived_keys") or (d.get("provenance") or {}).get("archived_keys")
    if arch:
        print("  archived n=%d" % len(arch))
    for k in ("symbol_faces", "relocated_symbol_faces"):
        print("   disp", k, "->", cbk.get(k))
