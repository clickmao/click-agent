#!/usr/bin/env python3
# R301 K1 行为级断言: 记忆锚问题 × 有/无画像 → 回复是否引用画像事实 (Web API 等)。
import json, os, subprocess, sys, re, time
LABEL = sys.argv[1] if len(sys.argv) > 1 else "manual"
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for line in open(".env.local", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
os.environ["AGENTFRAMEWORK_LOCAL_DISABLED"] = "1"
os.environ.setdefault("AGENTFRAMEWORK_BGE_MODEL", os.path.expanduser("~/.agentframework/models/bge-q8.gguf"))

CASES = json.load(open("eval/k1-behavior-cases.json"))

def run_one(q, disable):
    env = dict(os.environ)
    if disable:
        # R302: 全隔离臂 (tendency + memory + session + SessionMemory 全断 — R301 实证单关 tendency 不够)
        env["AGENTFRAMEWORK_K1_DISABLE"] = "1"
        env["AGENTFRAMEWORK_K1_FULL_ISOLATION"] = "1"
    r = subprocess.run(["dotnet", "src/agent.host/bin/Release/net10.0/agenthost.dll", "-q", q],
                       capture_output=True, text=True, timeout=120, errors="replace", env=env)
    m = re.search(r"──+\s*回复\s*──+\n(.*?)(?:\n  · intent=|\n──+|$)", r.stdout, re.S)
    return (m.group(1).strip() if m else r.stdout[-1200:])

rows = []
for c in CASES:
    rep_with = run_one(c["input"], disable=False); time.sleep(1)
    rep_without = run_one(c["input"], disable=True); time.sleep(1)
    def behavior_hit(rep):
        # R302 修正: 行为锚 = **画像独有事实** (80% 比例数字), 不用 "Web API" 宽词
        # (系统提示含框架描述, 宽词在零画像臂也命中 — R301 实证)。
        strong = [w for w in c["must_contain_behavior"] if any(ch.isdigit() for ch in w)]
        return any(w.lower() in rep.lower() for w in strong) if strong else \
            any(kw.lower() in rep.lower() for kw in c["must_contain_behavior"])
    hit_with, hit_without = behavior_hit(rep_with), behavior_hit(rep_without)
    rows.append({"id": c["id"], "hit_with": hit_with, "hit_without": hit_without,
                 "head_with": rep_with[:80], "head_without": rep_without[:80]})
    print(f"[{c['id']}] with={hit_with} without={hit_without}", flush=True)

n_with = sum(1 for r in rows if r["hit_with"])
n_without = sum(1 for r in rows if r["hit_without"])
summary = {"label": LABEL, "cases": len(rows), "behavior_hits_with": n_with, "behavior_hits_without": n_without, "rows": rows}
out = f"eval/results/k1-behavior-{LABEL}.json"
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"=== 行为命中: 有画像 {n_with}/{len(rows)} vs 无画像 {n_without}/{len(rows)} ===")
print("saved →", out)
