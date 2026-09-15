#!/usr/bin/env python3
"""EXP1-Q18 判决读取: 两臂 C1 重放保真 + 不可重放集合 (臂间 + 与 Q16 登记值对比)。"""
import json
import pathlib

Q18 = pathlib.Path(__file__).resolve().parent
TARGET = ("n_symbol_faces", "symbol_face_rungs")
pairs = {"v270(治疗)": Q18 / "verdict_q18_replay.json", "v260(对照)": Q18 / "verdict_q18_replay_old.json"}

for label, p in pairs.items():
    d = json.loads(p.read_text(encoding="utf-8"))
    print("=" * 72)
    print(label, "verdict", d.get("verdict"), "exit", d.get("exit"),
          "artifacts", list(d.get("artifacts", {})), "mf", bool(d.get("measurement_failures")))
    for aname, art in d.get("artifacts", {}).items():
        c1 = art.get("C1_replay", {})
        print("  artifact", aname, "C1 checked", c1.get("checked"), "all_equal", c1.get("all_equal"))
        rows = {r["emitted_key"]: r for r in (c1.get("rows") or [])}
        for k in TARGET:
            r = rows.get(k)
            print("   TARGET", k, "->", json.dumps(r, ensure_ascii=False)[:220] if r else "<ABSENT>")
        nr = art.get("not_replayable") or []
        print("   not_replayable", len(nr), sorted(nr))
        print("   typed", json.dumps(art.get("not_replayable_typed"), ensure_ascii=False)[:300])
        eq = [k for k, r in rows.items() if r.get("equal") is True]
        ne = [k for k, r in rows.items() if r.get("equal") is False]
        bnd = [k for k, r in rows.items() if r.get("equal") is None]
        print("   C1 equal", len(eq), "unequal", len(ne), "boundary", len(bnd), "| unequal:", sorted(ne)[:8])
        print("   counts", json.dumps(art.get("counts"), ensure_ascii=False)[:300])
