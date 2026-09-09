#!/usr/bin/env python3
# R300 K1 行为收益差分: 同 N 题 × 有/无画像 双跑 → bge 离线算 reply_rel → 差分。
# 用法: python3 eval/k1_diff.py <label> [N]
import json, os, subprocess, sys, time
LABEL = sys.argv[1] if len(sys.argv) > 1 else "manual"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 6
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for line in open(".env.local", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
os.environ["AGENTFRAMEWORK_LOCAL_DISABLED"] = "1"
os.environ.setdefault("AGENTFRAMEWORK_BGE_MODEL", os.path.expanduser("~/.agentframework/models/bge-q8.gguf"))

QUESTIONS = [
    "写一个 Python 函数合并两个字典并处理键冲突",
    "如何调用 Web API 时做重试与超时控制?",
    "帮我写个 git 批量删除远程分支的命令",
    "用 Python 分析 CSV 并画出趋势图的步骤",
    "Web API 鉴权 JWT 和 OAuth2 怎么选?",
    "git rebase 和 merge 在团队协作中怎么选?",
]

def run_one(q, disable):
    env = dict(os.environ)
    if disable:
        env["AGENTFRAMEWORK_K1_DISABLE"] = "1"
    r = subprocess.run(["dotnet", "src/agent.host/bin/Release/net10.0/agenthost.dll", "-q", q],
                       capture_output=True, text=True, timeout=120, errors="replace", env=env)
    # 提取回复正文 (run_round 同款正则):
    import re
    m = re.search(r"──+\s*回复\s*──+\n(.*?)(?:\n  · intent=|\n──+|$)", r.stdout, re.S)
    reply = m.group(1).strip() if m else r.stdout[-1500:]
    return reply

def rel(a: str, b: str) -> float:
    """bge 余弦 — 走 --embed (离线, 不走 LLM)。"""
    if not a.strip() or not b.strip():
        return 0.0
    ea = _embed(a); eb = _embed(b)
    if ea is None or eb is None: return 0.0
    import math
    dot = sum(x*y for x, y in zip(ea, eb))
    na = math.sqrt(sum(x*x for x in ea)); nb = math.sqrt(sum(x*x for x in eb))
    return dot/(na*nb) if na and nb else 0.0

def _embed(text):
    import subprocess as sp
    r = sp.run(["./src/agent.host/bin/Release/net10.0/agenthost", "--embed", text[:2000]],
               capture_output=True, text=True, timeout=60, errors="replace", env=os.environ)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None

rows = []
for i, q in enumerate(QUESTIONS[:N]):
    rep_with = run_one(q, disable=False)
    time.sleep(1)
    rep_without = run_one(q, disable=True)
    # 画像臂回复 vs 无画像臂回复 的语义贴近度没有直接意义 — 差分的正确度量:
    # ①有画像臂 rel(回复, 用户画像主题锚) ②无画像臂同锚 rel。
    anchor = "Python Web API git 代码示例 命令行"
    r1 = rel(rep_with, anchor); r0 = rel(rep_without, anchor)
    rows.append({"q": q, "rel_with": round(r1, 4), "rel_without": round(r0, 4),
                 "len_with": len(rep_with), "len_without": len(rep_without)})
    print(f"[{i+1}] with={r1:.3f} without={r0:.3f} delta={r1-r0:+.3f}", flush=True)

import statistics as st
dw = [r["rel_with"] for r in rows]; d0 = [r["rel_without"] for r in rows]
summary = {"label": LABEL, "n": len(rows), "rows": rows,
           "mean_with": round(st.mean(dw), 4), "mean_without": round(st.mean(d0), 4),
           "delta": round(st.mean(dw)-st.mean(d0), 4)}
out = f"eval/results/k1-diff-{LABEL}.json"
json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"=== mean_with={summary['mean_with']} mean_without={summary['mean_without']} delta={summary['delta']} ===")
print("saved →", out)
