#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R500 根因机检 (fail-closed): 断言「改写吸收支生效 ∧ 被 R444 后置否决吞掉」。

判据 (全部为结构量, 逐臂):
  K1 P 臂 t8 消息 = 网格第 8 轮文本, 且其 sha16 出现在 1 条 local_turn_gate_reject 行
  K2 该行 kv.r1_raw_len == len("mechanical:paraphrase") == 21  (⇒ 判决来自吸收支, 非 r1 调用)
  K3 该行同轮伴随 gate_prefilter_invariant_violation (前置门开启时本支不可达 ⇒ 不变量被破坏)
  K4 该轮 local_turn_gate.basis == "gate:skip_rejected_nonack→remote" (⇒ 已降级远端)
  K5 C 臂 同消息 sha16 ⇒ 0 条 reject / 0 条 violation, 且 basis == "mechanical:nonack→remote"
任一不成立 ⇒ rc=1 (RED), 不写"绿"结论。
"""
import hashlib
import io
import json
import os
import sys

D = sys.argv[1] if len(sys.argv) > 1 else "eval/rover/r499"
OUT = sys.argv[2] if len(sys.argv) > 2 else "eval/rover/r500/rootcause_r500.txt"
LABEL = "mechanical:paraphrase"

task = json.load(io.open(os.path.join(D, "grid", "task-p17-code.json"), encoding="utf-8-sig"))
turns = task.get("turns") or task.get("user_turns") or []
t8 = turns[7] if isinstance(turns[7], str) else (turns[7].get("user") or turns[7].get("content"))
sha8 = hashlib.sha256(t8.encode("utf-8")).hexdigest()[:16]

def rows(arm, point):
    p = os.path.join(D, "tel-%s" % arm, "host.jsonl")
    out = []
    if not os.path.isfile(p):
        return out
    for ln in io.open(p, encoding="utf-8-sig"):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if (d.get("point") or d.get("Point")) == point:
            out.append(d)
    return out

def bases(arm):
    return [((d.get("kv") or {}).get("basis")) for d in rows(arm, "local_turn_gate")]

lines = []
rc = 0
lines.append("t8 文本=%r sha16=%s" % (t8, sha8))
lines.append("len(%r)=%d" % (LABEL, len(LABEL)))
for arm in ("C", "P1", "P2", "P3"):
    rej = [d for d in rows(arm, "local_turn_gate_reject") if (d.get("kv") or {}).get("msg_sha16") == sha8]
    vio = [d for d in rows(arm, "gate_prefilter_invariant_violation") if (d.get("kv") or {}).get("msg_sha16") == sha8]
    gg = rows(arm, "local_turn_gate")
    b8 = None
    if len(gg) >= 8:
        b8 = (gg[7].get("kv") or {}).get("basis")
    raw = (rej[0].get("kv") or {}).get("r1_raw_len") if rej else None
    lines.append("%-3s reject=%d violation=%d r1_raw_len=%s t8_basis=%s" % (arm, len(rej), len(vio), raw, b8))
    if arm.startswith("P"):
        if not rej or str(raw) != str(len(LABEL)):
            rc = 1
            lines.append("    K1/K2 RED")
        if len(vio) != 1:
            rc = 1
            lines.append("    K3 RED")
        if b8 != "gate:skip_rejected_nonack→remote":
            rc = 1
            lines.append("    K4 RED")
    else:
        if rej or vio:
            rc = 1
            lines.append("    K5 RED")
        if b8 != "mechanical:nonack→remote":
            rc = 1
            lines.append("    K5 RED (basis)")
lines.append("VERDICT=%s rc=%d" % ("ROOTCAUSE_CONFIRMED" if rc == 0 else "NOT_CONFIRMED", rc))
txt = "\n".join(lines) + "\n"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(txt)
print(txt, end="")
sys.exit(rc)
