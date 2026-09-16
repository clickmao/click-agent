#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R500 根因取证: 定位 P 臂 local_turn_gate_reject / gate_prefilter_invariant_violation 的轮次与文本。"""
import io, json, os

D = "eval/rover/r499"
G = os.path.join(D, "grid", "task-p17-code.json")
task = json.load(io.open(G, encoding="utf-8-sig"))
turns = task.get("turns") or task.get("user_turns") or []
def sha16(s):
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

print("== 网格 t1..t9 (前 16 位哈希) ==")
for i, t in enumerate(turns[:12], 1):
    txt = t if isinstance(t, str) else (t.get("user") or t.get("content") or json.dumps(t, ensure_ascii=False))
    print("t%-2d sha16=%-16s len=%-3d %s" % (i, sha16(txt), len(txt), txt[:28]))

for arm in ("P1", "P2", "P3"):
    p = os.path.join(D, "tel-%s" % arm, "host.jsonl")
    print("\n== %s 关键行 ==" % arm)
    for ln in io.open(p, encoding="utf-8-sig"):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        pt = d.get("point") or d.get("Point")
        if pt in ("local_turn_gate_reject", "gate_prefilter_invariant_violation", "paraphrase_degrade_remote"):
            print(json.dumps(d, ensure_ascii=False)[:400])
    # 门行 basis 序列
    for ln in io.open(p, encoding="utf-8-sig"):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if (d.get("point") or d.get("Point")) == "local_turn_gate":
            kv = d.get("kv") or d.get("Kv") or {}
            print("  gate t=%s basis=%s" % (d.get("turn") or d.get("Turn") or kv.get("turn"), kv.get("basis") if isinstance(kv, dict) else kv))
