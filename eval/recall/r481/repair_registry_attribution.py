#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R481 台账卫生修复: 回退 bind_evidence `--apply --round` 造成的**纯归属churn**。

现象 (本轮实测): `bind_evidence.py --apply --round R481` 后 registry 出现 147+/122- 行级改动, 其中
  · 96 行**除 `audited_by_round` 外逐字段相同** —— 这不是重派生, 是"把并发写者上一轮的审计戳改成自己的轮号"
    (器具有注释自陈该风险, 但其最小 diff 判据把 audited_by_round 也算进"派生内容" ⇒ 换轮号必刷全部行);
  · 6 行是真重派生 (R478×3 / R479×3: `live/worktree-only` → `frozen/archived-per-round` + 真 pin,
    因其证据本轮已入库且工作区未改) ⇒ 保留;
  · 1 行是 R481 新增行 ⇒ 保留。

修法: 以 HEAD 为基准, 只把"仅轮号变"的行整块回退到 HEAD 值 (逐字段), 其余保持现盘。
纪律: 写前断言序列化器逐字节复现现盘; 只允许上述 id 集合变化; 写后读回; 打印 numstat。
"""
import collections
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
R = os.path.join(ROOT, "docs/verification-registry.json")
KEEP_NEW_ID = "r481.recall-d9-alternating-verify"


def strip(d):
    return {k: v for k, v in (d or {}).items() if k != "audited_by_round"}


def main():
    head_raw = subprocess.run(["git", "show", "HEAD:docs/verification-registry.json"],
                              cwd=ROOT, capture_output=True, text=True, check=True).stdout
    head = json.loads(head_raw, object_pairs_hook=collections.OrderedDict)
    hm = {r["id"]: r for r in head["rows"]}

    cur_raw = io.open(R, encoding="utf-8", newline="").read()
    doc = json.loads(cur_raw, object_pairs_hook=collections.OrderedDict)
    if json.dumps(doc, indent=1, ensure_ascii=False) + "\n" != cur_raw:
        print("SER_ASSERT=FAIL (现盘不可逐字节复现 ⇒ 禁改写)")
        return 3
    print("SER_ASSERT=OK")

    reverted = []
    for row in doc["rows"]:
        i = row.get("id")
        old = hm.get(i)
        if old is None:
            continue                                     # 新增行 (本轮登记行) ⇒ 保留
        a, b = row.get("evidence_generated_with"), old.get("evidence_generated_with")
        if a == b:
            continue
        if strip(a) == strip(b):
            if "evidence_generated_with" in old:
                row["evidence_generated_with"] = old["evidence_generated_with"]
            else:
                row.pop("evidence_generated_with", None)
            reverted.append(i)

    out = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if out == cur_raw:
        print("IDEMPOTENT=OK (无纯归属 churn 可回退)")
    else:
        # 只允许被回退行的 evidence_generated_with 变化 —— 逐行复核 (基准 = 写前快照 cur_raw, 不是被就地改过的 doc), 不许夹带
        before = json.loads(cur_raw, object_pairs_hook=collections.OrderedDict)
        after = json.loads(out, object_pairs_hook=collections.OrderedDict)
        bm = {r["id"]: r for r in before["rows"]}
        am = {r["id"]: r for r in after["rows"]}
        if set(bm) != set(am):
            print("SCOPE_VIOLATION 行集合变化: %s" % (set(bm) ^ set(am)))
            return 4
        dirty = [i for i in am if json.dumps(am[i], ensure_ascii=False, sort_keys=True)
                 != json.dumps(bm[i], ensure_ascii=False, sort_keys=True)]
        if sorted(dirty) != sorted(reverted):
            print("SCOPE_VIOLATION 变更行与声明的回退集不符: %s" % sorted(set(dirty) ^ set(reverted))[:10])
            return 4
        io.open(R, "w", encoding="utf-8", newline="\n").write(out)
        back = io.open(R, encoding="utf-8", newline="").read()
        print("WRITE_READBACK=%s" % ("OK" if back == out else "MISMATCH"))
        print("CHANGED_ROWS=%d (与声明回退集逐行相同)" % len(dirty))

    print(json.dumps({"rows": len(doc["rows"]), "reverted_pure_attribution_rows": len(reverted),
                      "kept_new": KEEP_NEW_ID in {r["id"] for r in doc["rows"]},
                      "updated_round": doc.get("updated_round")}, ensure_ascii=False))
    print(subprocess.run(["git", "diff", "--numstat", "docs/verification-registry.json"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
