#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R449 预检(零测量): think-memory 库普查 —— 判定它能否充当「外部真值通道」.

输出: eval/rover/r449/precheck-tm-census.json (机检字段 + 判定)
纪律: 只读; 不改库; 每个结论绑定字段读数, 不做推测。
"""
import collections
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
STORE = ROOT / "data/think-memory.json"
OUT = ROOT / "eval/rover/r449/precheck-tm-census.json"


def main():
    p = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else STORE
    if not p.exists():
        print(f"[fail-closed] 库文件不存在: {p}")
        return 2
    recs = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(recs, list):
        print("[fail-closed] 顶层非数组")
        return 2

    def g(r, *names, d=None):
        for n in names:
            if n in r and r[n] is not None:
                return r[n]
        return d

    dims = collections.Counter(len(g(r, "QuestionEmbedding", "questionEmbedding", d=[]) or []) for r in recs)
    outc = collections.Counter(str(g(r, "Outcome", "outcome", d="?")) for r in recs)
    refs_n = [len(g(r, "Refs", "refs", d=[]) or []) for r in recs]
    hits = [int(g(r, "HitCount", "hitCount", d=0) or 0) for r in recs]
    conf = [float(g(r, "AvgConfidence", "avgConfidence", d=0.0) or 0.0) for r in recs]
    heads = [str(g(r, "QuestionHead", "questionHead", d="")) for r in recs]
    created = [str(g(r, "CreatedAtUtc", "createdAtUtc", d="")) for r in recs]

    checks = {
        "T1_有负样本": {"pass": outc.get("negative", 0) > 0, "negative": outc.get("negative", 0)},
        "T2_有证据链接": {"pass": sum(1 for x in refs_n if x > 0) > 0,
                          "with_refs": sum(1 for x in refs_n if x > 0), "n": len(recs)},
        "T3_有命中": {"pass": sum(1 for x in hits if x > 0) > 0, "hit_gt0": sum(1 for x in hits if x > 0)},
        "T4_维度唯一": {"pass": len(dims) == 1, "dims": dict(dims)},
        "T5_问题头非空": {"pass": sum(1 for h in heads if h.strip()) > 0,
                          "nonempty": sum(1 for h in heads if h.strip())},
    }
    verdict = "CANNOT_SERVE_AS_TRUTH_CHANNEL" if not all(c["pass"] for c in checks.values()) else "OK"
    doc = {
        "round": "R449", "store": str(p), "bytes": p.stat().st_size,
        "mtime_utc": datetime.datetime.utcfromtimestamp(p.stat().st_mtime).isoformat(),
        "records": len(recs),
        "outcome": dict(outc), "dims": dict(dims),
        "refs_total": sum(refs_n), "hit_gt0": sum(1 for x in hits if x > 0),
        "avg_confidence_mean": round(sum(conf) / len(conf), 4) if conf else None,
        "created_span": [min(created) if created else None, max(created) if created else None],
        "checks": checks, "verdict": verdict,
        "note": "T1-T5 任一为假 ⇒ 该库当前**不能**充当外部真值通道(只能当写入型缓存); 详见计划 v0.69.0 §2/§3",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in checks.items():
        print(("PASS " if v["pass"] else "FAIL ") + k + " " + json.dumps(v, ensure_ascii=False))
    print(f"[结论] {verdict}  records={len(recs)} refs_total={sum(refs_n)} hit>0={sum(1 for x in hits if x>0)} dims={dict(dims)}")
    print(f"[out] {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
