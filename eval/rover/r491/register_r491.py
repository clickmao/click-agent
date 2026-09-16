#!/usr/bin/env python3
"""R491 台账登记 (行文本在 rows_r491.json, 本脚本只做形式门禁 + 保形写回 + 读回)。

形式门禁 (任一不过 ⇒ rc=2 零字节写入): 必填字段 / id 前缀 / level 合法 / evidence_path 与 covers 路径存在 /
  **序列化器逐字节复现原文件** (indent=1 + ensure_ascii=False + 尾 LF; 与 eval/capability/bind_evidence.py 同口径)。
注意: `evidence_generated_with` (R2f) **不由本脚本写** —— 单一源是 eval/capability/bind_evidence.py
  (本脚本写完行后调 `bind_evidence.py --apply --only <ids> --round R491` 补绑定)。
"""
import collections, io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
P = os.path.join(ROOT, "docs", "verification-registry.json")
ROWS = os.path.join(HERE, "rows_r491.json")
ROUND = "R491"

NEW = [collections.OrderedDict(r) for r in json.load(io.open(ROWS, encoding="utf-8"))]

errs = []
REQ = ("id", "level", "capability", "evidence_cmd", "evidence_path", "owner_round", "covers")
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
        if not os.path.exists(os.path.join(ROOT, c)):
            errs.append("%s: covers 路径不存在 %s" % (n.get("id"), c))

raw = io.open(P, encoding="utf-8", newline="").read()
doc = json.loads(raw, object_pairs_hook=collections.OrderedDict)
tail = "\n" if raw.endswith("\n") else ""
# (1) 原样复现自检 —— 必须在**改动之前**做: 序列化器若不能逐字节复现原文件, 任何改写都会制造全文件 diff 噪声。
if json.dumps(doc, ensure_ascii=False, indent=1) + tail != raw:
    errs.append("SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (indent=1/ensure_ascii=False/tail=%s)"
                % ("LF" if tail else "NONE"))
rows = doc["rows"]
ids = {r["id"] for r in rows}
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

io.open(P, "w", encoding="utf-8", newline="").write(ser + "\n")
back = json.load(io.open(P, encoding="utf-8"))
got = {r["id"]: r for r in back["rows"] if r["id"].startswith(ROUND.lower() + ".")}
ok = all(got.get(n["id"], {}).get("capability") == n["capability"] for n in NEW) and len(got) == len(NEW)
print(json.dumps({"verdict": "WRITTEN" if ok else "READBACK_MISMATCH", "added": added, "replaced": replaced,
                  "rows_after": len(back["rows"]), "r491_rows": sorted(got), "readback_ok": ok},
                 ensure_ascii=False))
if ok and "--bind" in sys.argv:
    only = ",".join(n["id"] for n in NEW)
    rc = subprocess.call([sys.executable, os.path.join(ROOT, "eval", "capability", "bind_evidence.py"),
                          "--apply", "--only", only, "--round", ROUND])
    print("bind_evidence_rc=%d" % rc)
    ok = ok and rc == 0
sys.exit(0 if ok else 3)
