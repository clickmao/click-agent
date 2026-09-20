#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R604 收口（第二次）：只改 kpi.jsonl 中 **R604 行** 的 `deferred` 字段（外科式，逐行保持其余字节不变）。"""
import io
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KP = os.path.join(REPO, "eval", "capability", "kpi.jsonl")

OLD = "后台起（landing_predicate_r593 --rounds r602,r603）；收口前未完成 ⇒ 如实再顺延"
NEW = ("后台起（landing_predicate_r593 --rounds r602,r603）；壁钟 424s 零输出、vint json 未落盘 "
       "⇒ 按 pid 清场（4 进程含 oracle 子进程）、零读数入库、如实再顺延（R602/R603 同因）")

with io.open(KP, encoding="utf-8") as fh:
    lines = fh.read().split("\n")

n_before = len(lines)
hits = [i for i, l in enumerate(lines) if '"round": "R604"' in l]
assert len(hits) == 1, "R604 行数异常: %d" % len(hits)
i = hits[0]
assert OLD in lines[i], "旧字段措辞未命中（禁盲改）"
lines[i] = lines[i].replace(OLD, NEW)

with io.open(KP, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

# ── 读回校验：行数不变 ∧ 全行可解析 ∧ 仅 R604 行变化 ∧ 其余行逐字节 == 备份
with io.open(KP, encoding="utf-8") as fh:
    after = fh.read().split("\n")
assert len(after) == n_before, "行数变化: %d -> %d" % (n_before, len(after))
diff = [k for k in range(n_before) if after[k] != lines[k] or k == i]
assert diff == [i], "非预期改动行: %s" % diff[:5]
parsed = 0
for l in after:
    if l.strip():
        json.loads(l)
        parsed += 1
row = json.loads(after[i])
assert row["readings"]["C3_truth_census"]["windows"] == 39
print("[kpi-patch] rows=%d (unchanged) · only line %d changed · all parse OK" % (parsed, i + 1))
print("[kpi-patch] deferred = %s" % row["readings"]["deferred"]["V_int_r602_r603"])
