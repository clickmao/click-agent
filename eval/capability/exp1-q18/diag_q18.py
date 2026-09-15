#!/usr/bin/env python3
"""EXP1-Q18 诊断: 打印 v260 臂 replay 的测量失败细节与 C1 行级差异。"""
import json
import pathlib
import sys

D = pathlib.Path(__file__).resolve().parent
p = D / (sys.argv[1] if len(sys.argv) > 1 else "verdict_q18_replay_old.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("schema", d.get("schema"), "verdict", d.get("verdict"), "exit", d.get("exit"))
print("src", d.get("src"), "src_sha12", d.get("src_sha256_12"))
print("cites", d.get("cites"))
print("measurement_failures:", json.dumps(d.get("measurement_failures"), ensure_ascii=False)[:600])
for name, art in d.get("artifacts", {}).items():
    print("== artifact", name, "verdict", art.get("verdict"), "exit", art.get("exit"))
    c1 = art.get("C1_replay", {})
    print("   C1 checked:", c1.get("checked"), "all_equal:", c1.get("all_equal"))
    rows = c1.get("rows") or []
    ne = [r for r in rows if r.get("equal") is False]
    print("   C1 unequal rows:", len(ne), "/", len(rows))
    for r in ne[:12]:
        print("     -", json.dumps(r, ensure_ascii=False)[:280])
    print("   not_replayable:", art.get("not_replayable"))
    print("   typed:", json.dumps(art.get("not_replayable_typed"), ensure_ascii=False)[:400])
    print("   findings:", json.dumps(art.get("counts"), ensure_ascii=False)[:400])
