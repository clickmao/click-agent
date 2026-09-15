#!/usr/bin/env python3
"""R462 W-臂 器具自检 (轻量): ① 语料 vs 产品落盘 dump **逐位**比对 (器具镐铁律)
                                ② 判据可分辨性 (恒 S / 恒 P / oracle 三档合成)
用法: python3 r462_w_selftest.py
"""
import glob
import json
import os
import sys

DUMPS = ["/home/agentuser/AgentFramework/eval/rover/r452/dump-RJ-REAL-j1.jsonl",
         "/home/agentuser/AgentFramework/eval/rover/r452/dump-RC-M20-c1.jsonl",
         "/home/agentuser/AgentFramework/eval/rover/r452/dump-RC-M20-c2.jsonl"]
CORPUS = "/tmp/r462_corpus.json"


def dump_prompts():
    out = []
    for p in DUMPS:
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8-sig"):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if isinstance(d.get("prompt"), str):
                out.append(d["prompt"])
    return out


def metrics(rows, force=None):
    def got(r):
        return force if force else r.get("got")
    def exp(r):
        return "S" if str(r["want"]).lower().startswith("skip") else "P"
    neg = [r for r in rows if exp(r) == "P"]
    pos = [r for r in rows if exp(r) == "S"]
    ok = sum(1 for r in rows if got(r) == exp(r))
    return {"acc": round(ok / len(rows), 4),
            "false_skip_rate": round(sum(1 for r in neg if got(r) == "S") / len(neg), 4),
            "miss_skip_rate": round(sum(1 for r in pos if got(r) == "P") / len(pos), 4)}


def main():
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    dmps = dump_prompts()
    exact = sum(1 for c in corpus if c["prompt"] in dmps)
    print(f"[1] 语料 n={len(corpus)} (负类 {sum(1 for c in corpus if c['want']=='pass')} / 正类 {sum(1 for c in corpus if c['want']=='skip')})")
    print(f"[1] 与产品落盘 dump 逐位命中: {exact}/{len(corpus)}  (dump 侧候选 {len(dmps)} 条)")
    syn = [dict(r, got=("S" if str(r["want"]).lower().startswith("skip") else "P")) for r in corpus]
    print("[2] oracle 恒对 ⇒", metrics(syn))
    alls = [dict(r, got="S") for r in corpus]
    allp = [dict(r, got="P") for r in corpus]
    print("[2] 恒 S ⇒", metrics(alls))
    print("[2] 恒 P ⇒", metrics(allp))
    ok = (exact == len(corpus)
          and metrics(syn)["acc"] == 1.0
          and metrics(alls)["false_skip_rate"] == 1.0 and metrics(alls)["miss_skip_rate"] == 0.0
          and metrics(allp)["false_skip_rate"] == 0.0 and metrics(allp)["miss_skip_rate"] == 1.0)
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
