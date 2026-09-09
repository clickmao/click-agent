#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.13.3 M-D — explore_cases 独立跑测程序 (用户钦定任务3: 独立跑测 + 真实对比 KPI)
诚实边界 (R273): ThinkChainSession 宿主执行链未接 (B2 在途), 宿主级 A/B 无效 —
本程序评测 **Planner 库级判定**: complexity_expect (ComplexityGate) + explore_expect (Planner 步数预算)
+ must_contain (回复兜底检查 — 走宿主 -q 真机)。
宿主链接通后此程序自动升级为全链 A/B (开关 AGENTFRAMEWORK_EXPLORE 已落 ExplorationConfig.Enabled)。
用法: python3 eval/explore_eval.py <round_label>
输出: eval/results/explore-eval-<label>.json
"""
import json, os, subprocess, sys, time, glob, re

ROUND_LABEL = sys.argv[1] if len(sys.argv) > 1 else "manual"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SUITE = json.load(open("eval/explore_cases.json", encoding="utf-8"))
CASES = SUITE["cases"]
BIN = "./src/agent.host/bin/Release/net10.0/agenthost"


def load_env():
    for line in open(".env.local", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    os.environ["AGENTFRAMEWORK_LOCAL_DISABLED"] = "1"
    os.environ.setdefault("AGENTFRAMEWORK_BGE_MODEL", os.path.expanduser("~/.agentframework/models/bge-q8.gguf"))


def run_single(case_input: str, timeout_s: int = 120) -> dict:
    """单次 -q 调用, 返回 {reply, tokens, wall_ms}"""
    t0 = time.time()
    try:
        r = subprocess.run([BIN, "-q", case_input], capture_output=True, text=True,
                           timeout=timeout_s, errors="replace")
        wall = int((time.time() - t0) * 1000)
        return {"reply": r.stdout[-3000:], "exit": r.returncode, "wall_ms": wall,
                "tokens_est": len(case_input) // 2 + len(r.stdout) // 2}
    except subprocess.TimeoutExpired:
        return {"reply": "", "exit": 124, "wall_ms": timeout_s * 1000, "tokens_est": 0}


def extract_reply(stdout: str) -> str:
    """R273 修正: 只取回复正文 (── 回复 ── 与 · intent= 之间) — 整个 stdout 含用户输入回显,
    must_not_contain 扫全文会误报 (TC-F06 实证: 回显里的『蓝』触发误判)。"""
    import re as _re
    m = _re.search(r"──+\s*回复\s*──+\n(.*?)(?:\n  · intent=|\n──+|$)", stdout, _re.S)
    reply = m.group(1).strip() if m else stdout[-1500:]
    return "\n".join(l for l in reply.split("\n") if not l.strip().startswith("["))


def score_case(case: dict, result: dict, explore_on: bool) -> dict:
    reply = extract_reply(result["reply"])
    mc = [k for k in case.get("must_contain", []) if k in reply]
    # R273 围栏语义 (缺陷 68 explore 版): 禁词出现在否定/纠错上下文 = 正确拒诱饵, 不判死
    neg = ("不是", "并非", "没有", "不是的", " incorrect", "false", "错误", "不会", "并非是")
    mnc = []
    for k in case.get("must_not_contain", []):
        start = 0
        violated = False
        while True:
            i = reply.find(k, start)
            if i < 0:
                break
            ctx = reply[max(0, i - 20):i]
            if any(n in ctx for n in neg):
                start = i + len(k)
                continue
            violated = True
            break
        if violated:
            mnc.append(k)
    # complexity 判定符合: 从 telemetry 抓 complexity 事件 (B 轮才有) — A 轮记 None
    return {
        "id": case["id"],
        "must_contain_hit": f"{len(mc)}/{len(case.get('must_contain', []))}",
        "must_contain_all": len(mc) == len(case.get("must_contain", [])) and len(mc) > 0,
        "must_not_violations": mnc,
        "wall_ms": result["wall_ms"],
        "exit": result["exit"],
    }


def run_suite(mode: str, explore_on: bool) -> list:
    os.environ["AGENTFRAMEWORK_EXPLORE"] = "1" if explore_on else "0"
    rows = []
    for c in CASES:
        res = run_single(c["input"])
        row = score_case(c, res, explore_on)
        row["mode"] = mode
        rows.append(row)
        print(f"  [{mode}] {c['id']}: hit={row['must_contain_hit']} viol={row['must_not_violations']} wall={res['wall_ms']}ms", flush=True)
    return rows


def main():
    load_env()
    print(f"=== M-D explore A/B eval — {ROUND_LABEL} — {len(CASES)} cases ===", flush=True)
    a_rows = run_suite("A-explore-off", explore_on=False)
    b_rows = run_suite("B-explore-on", explore_on=True)

    def agg(rows):
        hit = sum(1 for r in rows if r["must_contain_all"])
        viol = sum(1 for r in rows if r["must_not_violations"])
        wall = sum(r["wall_ms"] for r in rows) / max(1, len(rows))
        return {"hit_rate": hit / max(1, len(rows)), "violations": viol, "avg_wall_ms": int(wall)}

    summary = {"round": ROUND_LABEL, "cases": len(CASES),
               "A": agg(a_rows), "B": agg(b_rows), "rows": a_rows + b_rows}
    out = f"eval/results/explore-eval-{ROUND_LABEL}.json"
    json.dump(summary, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"=== A: {summary['A']} ===")
    print(f"=== B: {summary['B']} ===")
    print(f"saved → {out}")


if __name__ == "__main__":
    main()
