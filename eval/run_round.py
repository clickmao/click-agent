#!/usr/bin/env python3
"""Round 跑批 harness — 每用例独立 dotnet run 进程, 采集回复 + telemetry JSONL → rounds/<round>.json"""
import json, os, re, subprocess, sys, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
TELEMETRY = "data/telemetry/host.jsonl"
ROUNDS = "data/logs/eval/rounds"
os.makedirs(ROUNDS, exist_ok=True)

def load_env():
    env = dict(os.environ)
    if os.path.exists(".env.local"):
        for line in open(".env.local"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k] = v
    return env

def read_telemetry():
    """读打点 JSONL (容错解析)"""
    points = []
    if not os.path.exists(TELEMETRY):
        return points
    for line in open(TELEMETRY, encoding="utf-8-sig"):
        line = line.strip()
        if not line:
            continue
        try:
            points.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return points

def run_case(case, env):
    """跑单用例 → {reply, points, wall_ms}"""
    if os.path.exists(TELEMETRY):
        os.remove(TELEMETRY)
    t0 = time.time()
    p = subprocess.run(
        ["dotnet", "run", "--project", "src/agent.host", "-c", "Release", "--no-build", "--", "-q", case["input"]],
        capture_output=True, text=True, timeout=180, env=env)
    wall_ms = int((time.time() - t0) * 1000)
    out = p.stdout
    # 提取回复正文 (── 回复 ── 与 · intent= 之间)
    m = re.search(r"──+\s*回复\s*──+\n(.*?)(?:\n  · intent=|\n──+|$)", out, re.S)
    reply = m.group(1).strip() if m else ""
    # 过滤 chatbox 协议行 / thinking 日志行
    reply = "\n".join(l for l in reply.split("\n")
                      if not l.startswith("@chatbox:") and "[20" not in l[:26])
    points = read_telemetry()
    return {"reply": reply, "raw_tail": out[-300:], "points": points, "wall_ms": wall_ms}

def summarize_points(points):
    """聚合打点 → 指标 dict"""
    s = {"points": len(points), "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
         "total_tokens": 0, "llm_ms_est": None, "skill_hits": [], "skill_force": None,
         "intent": None, "subtasks": 0, "assembly_ok": None, "loop_success": None,
         "loop_ms": None, "models": [],
         "snippets": 0, "sources_recall": "", "assembly_ms": None, "from_cache": None,
         "prompt_total_tokens": None, "history_tokens": None, "gate_to_ask": None}
    for pt in points:
        kv = pt.get("kv", {}) or {}
        tag = pt.get("point")
        if tag == "llm_call":
            s["llm_calls"] += 1
            s["prompt_tokens"] += kv.get("prompt_tokens", 0) or 0
            s["completion_tokens"] += kv.get("completion_tokens", 0) or 0
            s["total_tokens"] += kv.get("total_tokens", 0) or 0
            s["models"].append(kv.get("model"))
        elif tag == "skill":
            mid = kv.get("matched")
            if mid and mid != "(none)":
                s["skill_hits"].append({"skill": mid, "level": kv.get("level"), "precision": kv.get("precision")})
        elif tag == "intent":
            s["intent"] = kv.get("primary")
            s["subtasks"] = kv.get("subtask_count", 0)
        elif tag == "assembly":
            s["assembly_ok"] = kv.get("success")
            s["snippets"] = kv.get("snippets", 0)
            s["sources_recall"] = kv.get("sources", "")
            s["assembly_ms"] = kv.get("assembly_ms")
            s["from_cache"] = kv.get("from_cache")
        elif tag == "prompt_build":
            s["prompt_total_tokens"] = kv.get("total_tokens")
            s["history_tokens"] = kv.get("history_tokens")
        elif tag == "evidence_gate":
            s["gate_to_ask"] = kv.get("to_ask")
        elif tag == "loop_turn":
            s["loop_success"] = kv.get("success")
            s["loop_ms"] = kv.get("total_ms")
    return s

def check_expect(case, reply, agg, raw_tail):
    """断言 → (pass, notes)"""
    exp = case.get("expect", {})
    notes, ok = [], True
    def req(cond, msg):
        nonlocal ok
        if not cond:
            ok = False
            notes.append("FAIL:" + msg)
    if "intent" in exp:
        req(agg["intent"] == exp["intent"], f"intent={agg['intent']} want {exp['intent']}")
    if "min_subtasks" in exp:
        req((agg["subtasks"] or 0) >= exp["min_subtasks"], f"subtasks={agg['subtasks']}")
    if "llm" in exp:
        req(agg["llm_calls"] >= 1 if exp["llm"] else agg["llm_calls"] == 0,
            f"llm_calls={agg['llm_calls']} want {'≥1' if exp['llm'] else '0'}")
    if "min_reply_chars" in exp:
        req(len(reply) >= exp["min_reply_chars"], f"reply {len(reply)} < {exp['min_reply_chars']}")
    if "skill" in exp:
        req(any(h["skill"] == exp["skill"] for h in agg["skill_hits"]), f"skill {exp['skill']} not hit")
    if "skill_force" in exp:
        forced = any(h["skill"] == exp["skill_force"] for h in agg["skill_hits"]) and agg["llm_calls"] == 0
        req(forced, f"skill_force {exp['skill_force']} failed (hits={agg['skill_hits']}, llm={agg['llm_calls']})")
    if "cmd_json" in exp:
        req(reply.strip().startswith("{"), f"cmd output not JSON: {reply[:60]!r}")
    if exp.get("cmd_json") and exp.get("ok"):
        req('"ok":true' in reply.lower().replace(" ", "") or '"ok": true' in reply.lower(),
            f"cmd ok!=true: {reply[:80]!r}")
    if exp.get("cmd_json") and "min_models" in exp:
        n = len(re.findall(r'"[iI]d"\s*:', reply))
        req(n >= exp["min_models"], f"models {n} < {exp['min_models']}")
    return ok, notes

def main():
    rnd = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    label = sys.argv[2] if len(sys.argv) > 2 else ""
    cases = json.load(open("eval/cases.json"))
    env = load_env()
    results = []
    for c in cases:
        r = run_case(c, env)
        agg = summarize_points(r["points"])
        ok, notes = check_expect(c, r["reply"], agg, r["raw_tail"])
        results.append({"id": c["id"], "input": c["input"], "pass": ok, "notes": notes,
                        "reply": r["reply"][:400], "wall_ms": r["wall_ms"], **agg})
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {c['id']}  wall={r['wall_ms']}ms tokens={agg['total_tokens']} intent={agg['intent']} skill={len(agg['skill_hits'])}")
        for n in notes:
            print("    ", n)
    # round 汇总
    summary = {"round": rnd, "label": label, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "cases": len(results), "passed": sum(1 for x in results if x["pass"]),
               "tokens_total": sum(x["total_tokens"] for x in results),
               "prompt_total": sum(x["prompt_tokens"] for x in results),
               "completion_total": sum(x["completion_tokens"] for x in results),
               "wall_total_ms": sum(x["wall_ms"] for x in results),
               "results": results}
    path = f"{ROUNDS}/{rnd}.json"
    json.dump(summary, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"\n=== round={rnd} passed={summary['passed']}/{summary['cases']} tokens={summary['tokens_total']} wall={summary['wall_total_ms']}ms → {path}")

if __name__ == "__main__":
    main()
