#!/usr/bin/env python3
"""R492 台账登记 (行文本在 rows_r492.json; 本脚本只做形式门禁 + 保形写回 + 读回 + 并发守卫)。

与 R491 版差异 (本回合新增, 其余同源逻辑):
  · **并发守卫**: 写回前记 sha256(原文件); 写回后逐行比对「非本回合 id 的其他行」是否逐字段不变 ⇒
    任何被并发写者改动的行都会让本脚本 rc=4 并打印差异 (防 R486 撞车类事件)。
形式门禁 (任一不过 ⇒ rc=2 零字节写入): 必填字段 / id 前缀 / level 合法 / evidence_path 与 covers 存在 /
  序列化器逐字节复现原文件 (indent=1 + ensure_ascii=False + 尾 LF)。
"""
import collections, hashlib, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
P = os.path.join(ROOT, "docs", "verification-registry.json")
ROWS = os.path.join(HERE, "rows_r492.json")
ROUND = "R492"

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
sha_before = hashlib.sha256(raw.encode("utf-8")).hexdigest()
doc = json.loads(raw, object_pairs_hook=collections.OrderedDict)
tail = "\n" if raw.endswith("\n") else ""
if json.dumps(doc, ensure_ascii=False, indent=1) + tail != raw:
    errs.append("SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (indent=1/ensure_ascii=False/tail=%s)"
                % ("LF" if tail else "NONE"))
rows = doc["rows"]
prev_others = {r["id"]: json.dumps(r, ensure_ascii=False, sort_keys=True)
               for r in rows if not str(r.get("id", "")).startswith(ROUND.lower() + ".")}
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
guard = {r["id"]: json.dumps(r, ensure_ascii=False, sort_keys=True) for r in back["rows"]}
changed = sorted(k for k, v in prev_others.items() if k in guard and guard[k] != v)
lost = sorted(k for k in prev_others if k not in guard)
sha_after = hashlib.sha256(io.open(P, encoding="utf-8", newline="").read().encode("utf-8")).hexdigest()
got = {r["id"]: r for r in back["rows"] if r["id"].startswith(ROUND.lower() + ".")}
ok = all(got.get(n["id"], {}).get("capability") == n["capability"] for n in NEW) and len(got) == len(NEW)
ok = ok and not changed and not lost
print(json.dumps({"verdict": "WRITTEN" if ok else "READBACK_MISMATCH", "added": added, "replaced": replaced,
                  "rows_after": len(back["rows"]), "r492_rows": sorted(got), "readback_ok": ok,
                  "concurrent_changed": changed, "concurrent_lost": lost,
                  "sha_before": sha_before[:16], "sha_after": sha_after[:16]}, ensure_ascii=False))
sys.exit(0 if ok else 3)
