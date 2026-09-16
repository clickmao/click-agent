#!/usr/bin/env python3
"""R497 台账登记 (行文本在 rows_r497.json, 本脚本只做形式门禁 + 保形写回 + 读回)。

形式门禁 (任一不过 ⇒ rc=2 **零字节写入**):
  必填字段 / id 前缀 r497. / level 合法 / evidence_path 存在 / covers 纯路径且存在 /
  **序列化器逐字节复现原文件** (indent=1 + ensure_ascii=False + 尾 LF; 与 eval/capability/bind_evidence.py 同口径,
  自检在**改动之前**做 —— 否则任何改写都会制造全文件 diff 噪声)。
`evidence_generated_with` 由本脚本按 R496 口径**行内**写死 (pin=audit-pin / audited_by_round=R497);
**不调** bind_evidence --apply (R491 教训: 该调用会把 audited_by_round 刷成纯 churn)。

用法: python3 eval/rover/r497/register_r497.py [--dry]
"""
import collections
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
P = os.path.join(ROOT, "docs", "verification-registry.json")
ROWS = os.path.join(HERE, "rows_r497.json")
ROUND = "R497"
REQ = ("id", "level", "capability", "evidence_cmd", "evidence_path", "owner_round", "covers")

NEW = [collections.OrderedDict(r) for r in json.load(io.open(ROWS, encoding="utf-8"))]
errs = []
for n in NEW:
    for k in REQ:
        if not n.get(k):
            errs.append("%s: 缺字段 %s" % (n.get("id", "?"), k))
    if not str(n.get("id", "")).startswith(ROUND.lower() + "."):
        errs.append("%s: id 前缀非 %s." % (n.get("id"), ROUND.lower()))
    if n.get("level") not in ("L1", "L2", "L3", "L4"):
        errs.append("%s: level 非法 %r" % (n.get("id"), n.get("level")))
    if not os.path.exists(os.path.join(ROOT, n.get("evidence_path", ""))):
        errs.append("%s: evidence_path 不存在 %s" % (n.get("id"), n.get("evidence_path")))
    for c in n.get("covers", []):
        if os.path.isabs(c) or ".." in c:
            errs.append("%s: covers 必须为仓内纯路径 %s" % (n.get("id"), c))
        if not os.path.exists(os.path.join(ROOT, c)):
            errs.append("%s: covers 路径不存在 %s" % (n.get("id"), c))

raw = io.open(P, encoding="utf-8", newline="").read()
doc = json.loads(raw, object_pairs_hook=collections.OrderedDict)
tail = "\n" if raw.endswith("\n") else ""
if json.dumps(doc, ensure_ascii=False, indent=1) + tail != raw:
    errs.append("SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (改动前自检)")
rows = doc["rows"]
added, replaced = [], []
for n in NEW:
    hit = [i for i, r in enumerate(rows) if r["id"] == n["id"]]
    if hit:
        rows[hit[0]] = n
        replaced.append(n["id"])
    else:
        rows.append(n)
        added.append(n["id"])
doc["updated_round"] = ROUND
ser = json.dumps(doc, ensure_ascii=False, indent=1)
if errs:
    print(json.dumps({"verdict": "REJECT", "zero_write": True, "errors": errs}, ensure_ascii=False, indent=1))
    sys.exit(2)
if "--dry" in sys.argv:
    print(json.dumps({"verdict": "DRY-OK", "added": added, "replaced": replaced,
                      "rows_total": len(rows)}, ensure_ascii=False))
    sys.exit(0)
io.open(P, "w", encoding="utf-8", newline="").write(ser + "\n")
back = json.load(io.open(P, encoding="utf-8"))
got = {r["id"]: r for r in back["rows"]}
miss = [i for i in added + replaced if i not in got]
if miss or back["updated_round"] != ROUND:
    print(json.dumps({"verdict": "READBACK-FAIL", "miss": miss}, ensure_ascii=False))
    sys.exit(3)
print("[register] 新增 %d 行 / 覆盖 %d 行; rows=%d; updated_round=%s" % (len(added), len(replaced), len(back["rows"]), ROUND))
for i in added + replaced:
    r = got[i]
    eg = r.get("evidence_generated_with", {})
    print("   %-58s %s artifact_sha12=%s instrument_sha12=%s audited=%s"
          % (i, r["level"], eg.get("artifact_sha12"), eg.get("instrument_sha12"), eg.get("audited_by_round")))


def sha12(rel):
    p = os.path.join(ROOT, rel)
    return None if not os.path.exists(p) else hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
