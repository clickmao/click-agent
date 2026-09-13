#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""闲时数据采集: 为 bge-small-zh-v1.5 积累"中文查询 → 正例块"训练对。

铁律: 评测金标准块 (eval fixtures 的 120 块) 永久排除在训练正例外 (机检 assert)。
用法:
  python3 collect_pairs.py --harvest            # 只收割真实 query 到池子 (免费)
  python3 collect_pairs.py --gen --budget 300 --max-pairs 120
输出: data/bge/train_pairs.jsonl, data/bge/query_pool.jsonl
"""
import os, sys, json, re, time, glob, random, hashlib, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bge_lib as L

URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = os.environ.get("QUERY_MODEL", "deepseek-flash")
KEY = os.environ.get("AGENTFRAMEWORK_KEYS_DEEPSEEK", "")
PAIRS = os.path.join(L.DATA, "train_pairs.jsonl")
POOL = os.path.join(L.DATA, "query_pool.jsonl")
ASCII_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]{4,}")
BATCH = 5

SYS = ("你是检索评测的出题器。给定若干代码/文档片段，为**每一个**片段写一个中文用户提问，"
       "使得该片段是回答该问题的最佳依据。要求：\n"
       "1) 提问像真实用户的口语化中文提问，一句话，10~40 字；\n"
       "2) 禁止照抄片段中的类名/函数名/文件名/变量名等独特标识符（英文名词一律不出现）；\n"
       "3) 提问概括片段表达的意图或知识点，并具体到能与其它片段的主题区分开，"
       "禁止\"怎么做\"\"有哪些\"这类泛问；\n"
       "4) 只输出严格 JSON：{\"questions\":[{\"idx\":1,\"q\":\"...\"}]}，不要解释。")


def llm(messages, retries=3, timeout=90):
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.7,
                       "max_tokens": 900}).encode("utf-8")
    for a in range(retries):
        req = urllib.request.Request(URL, data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  llm retry {a+1}: {type(e).__name__}", file=sys.stderr)
            time.sleep(2 + 3 * a)
    return ""


def parse(content):
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    out = {}
    for it in d.get("questions", []):
        try:
            out[int(it["idx"])] = str(it["q"]).strip()
        except Exception:
            pass
    return out


def load_jsonl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def harvest_real_queries():
    """从 514 轮评测结果收割真实用户 query (去重) → query_pool.jsonl"""
    seen, rows = set(), []
    for f in sorted(glob.glob(os.path.join(L.REPO, "eval", "results", "*.json"))):
        try:
            dd = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        cs = dd if isinstance(dd, list) else (dd.get("results") if isinstance(dd, dict) else None)
        if isinstance(cs, dict):
            cs = list(cs.values())
        if not isinstance(cs, list):
            continue
        for c in cs:
            if not isinstance(c, dict):
                continue
            q = (c.get("input") or "").strip()
            if 4 <= len(q) <= 300 and q not in seen:
                seen.add(q)
                rows.append({"query": q, "source": "eval-log", "case_id": c.get("id", ""),
                             "ts": ""
                             })
    os.makedirs(L.DATA, exist_ok=True)
    old = {r["query"] for r in load_jsonl(POOL)}
    new = [r for r in rows if r["query"] not in old]
    with open(POOL, "a", encoding="utf-8") as fh:
        for r in new:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows), len(new)


def gen_pairs(budget_s, max_new):
    corpus, queries = L.load_fixtures()
    gold_eval = {q["gold_id"] for q in queries}
    existing = load_jsonl(PAIRS)
    used = {p["positive_id"] for p in existing}
    assert not (used & gold_eval), "训练正例与评测金标准相交 — 违反隔离铁律"

    pool = [c for c in corpus if c["id"] not in gold_eval and c["id"] not in used]
    random.Random(20260913).shuffle(pool)

    if not KEY:
        print("FATAL: 缺 AGENTFRAMEWORK_KEYS_DEEPSEEK", file=sys.stderr)
        return 0
    added, t0, i = 0, time.time(), 0
    while i < len(pool) and added < max_new and time.time() - t0 < budget_s:
        batch = pool[i:i + BATCH]; i += BATCH
        user = "\n\n".join(f"片段{k+1}:\n{c['text'][:1100]}" for k, c in enumerate(batch))
        qs = parse(llm([{"role": "system", "content": SYS}, {"role": "user", "content": user}]))
        for k, c in enumerate(batch, start=1):
            q = qs.get(k, "")
            if not q or len(q) < 6 or ASCII_ID.search(q):
                continue
            row = {"pair_id": hashlib.sha1(f"{q}|{c['id']}".encode()).hexdigest()[:12],
                   "query": q, "positive_id": c["id"], "positive_src": c["src"],
                   "positive_text": c["text"][:400], "negatives": [],
                   "source": "llm-from-chunk", "llm_model": MODEL,
                   "corpus_version": "corpus_r370_1299", "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
            existing.append(row); added += 1
        if added:
            print(f"  ... {added}/{max_new} (t={time.time()-t0:.0f}s)", file=sys.stderr)
    os.makedirs(L.DATA, exist_ok=True)
    with open(PAIRS, "w", encoding="utf-8") as fh:
        for r in existing:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    assert not ({p["positive_id"] for p in existing} & gold_eval), "写盘后隔离机检失败"
    return added


def main():
    total_pairs = len(load_jsonl(PAIRS))
    out = {"harvested_total": 0, "harvested_new": 0, "pairs_added": 0, "pairs_total": total_pairs}
    if "--harvest" in sys.argv or "--gen" in sys.argv:
        t, n = harvest_real_queries()
        out["harvested_total"], out["harvested_new"] = t, n
    if "--gen" in sys.argv:
        budget = int(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else 300
        max_new = int(sys.argv[sys.argv.index("--max-pairs") + 1]) if "--max-pairs" in sys.argv else 120
        out["pairs_added"] = gen_pairs(budget, max_new)
        out["pairs_total"] = len(load_jsonl(PAIRS))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
