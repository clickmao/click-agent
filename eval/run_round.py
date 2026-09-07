#!/usr/bin/env python3
"""Round 跑批 harness — 每用例独立 dotnet run 进程, 采集回复 + telemetry JSONL → rounds/<round>.json"""
import glob, json, os, re, subprocess, sys, time, urllib.parse

try:
    import fcntl  # Unix 单实例互斥 (评测环境 Linux)
except ImportError:
    fcntl = None  # Windows 退化无锁 (评测不跑 Windows)

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

def read_telemetry(path=None):
    """读打点 JSONL (容错解析); R110: 支持每用例独立文件路径"""
    points = []
    path = path or TELEMETRY
    if not os.path.exists(path):
        return points
    for line in open(path, encoding="utf-8-sig"):
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
    # v0.11.0 R110 (fix#42): 每用例独立 telemetry 文件 (绝对路径 env 覆写) —
    # 共享单文件的 remove→append→read 时序竞争曾致间歇 llm_calls=0 误判 (mass_99/99b/99c/99d)。
    case_tel = os.path.abspath("data/telemetry/host.jsonl")  # CLI 固定写 host.jsonl, 每用例独占目录
    env["AGENTFRAMEWORK_TELEMETRY"] = os.path.dirname(case_tel)
    if os.path.exists(case_tel):
        os.remove(case_tel)
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
    points = read_telemetry(case_tel)
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
    if "reply_contains" in exp:
        req(exp["reply_contains"].lower() in (reply or "").lower(),
            f"reply 缺少 '{exp['reply_contains']}'")
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
    # v0.11.0 R93: JSON 格式返回校验器 (用户注意点 1 — 格式正确性额外打点):
    if "json_valid" in exp or "json_fields" in exp:
        parsed, jerr = try_parse_json_reply(reply or "")
        if "json_valid" in exp:
            req(parsed is not None, f"reply 非合法 JSON ({jerr}): {reply[:80]!r}")
        if parsed is not None and "json_fields" in exp:
            for k, v in exp["json_fields"].items():
                req(str(parsed.get(k, "")).strip().lower() == str(v).lower(),
                    f"json 字段 {k}={parsed.get(k)!r} want {v!r}")
    return ok, notes

def try_parse_json_reply(reply):
    """从回复中提取首个 JSON 对象 (容错 markdown 代码块/前后缀文字) → (dict|None, err)"""
    text = reply.strip()
    # 剥 markdown 代码块
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S)
    if m:
        text = m.group(1)
    else:
        # 提取首个 {...} 平衡块
        i = text.find('{')
        if i < 0:
            return None, "no '{' in reply"
        depth, end = 0, -1
        in_str = False
        for j in range(i, len(text)):
            c = text[j]
            if c == '"' and text[j-1] != '\\':
                in_str = not in_str
            if in_str:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end < 0:
            return None, "unbalanced braces"
        text = text[i:end+1]
    try:
        return json.loads(text), ""
    except Exception as e:
        return None, str(e)[:60]

def main():
    # v0.11.0 R113: -h/--help 防护 — 无位置参数时默认 rnd="baseline" 会真跑全量轮
    # (2026-09-07 实证: `run_round.py --help` 被 flag 过滤吞掉 → 真跑 baseline 180s 被杀,
    #  浪费 + 扰动 eval 隔离态)。帮助请求必须零副作用退出。
    if any(a in ("-h", "--help", "/?") for a in sys.argv[1:]):
        print(__doc__)
        print("用法: python3 eval/run_round.py [--quick] <round> [label]")
        print("  --quick   高频回归模式 (C01/C03/C06/C08/C11 五用例)")
        print("  <round>   落盘名 (如 mass_118); 无则 baseline")
        print("  label     账本标签 (如 'R113 batch25 118')")
        return 0
    # v0.11.0 R110 (真缺陷 43): 单实例互斥 — 遥测路径与轮间清理 (RAG 落盘/会话记忆删除) 是
    # 全仓库全局资源, 并发 runner 互相删除/覆盖对方打点 (2026-09-07 实证: 双 tick 并行 →
    # mass_95/96 假 llm_calls=0 → 假 REVERT, 批 95-100 全 RETIRED)。fcntl 非阻塞独占锁:
    # 抢不到 = 另一 runner 在跑 → 诚实退出 3 (与 llm-service IsAlive 互斥同语义), 不等待
    # 不重试 (排队会把两批数据在时间轴上焊死, 比失败更糟)。
    lockf = open("data/eval_run.lock", "w")
    if fcntl is not None:
        try:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("eval_run: 另一 runner 实例运行中 (data/eval_run.lock 被占) — 本实例诚实退出, 不写任何数据")
            return 3
    # v0.11.0 R107 (真缺陷 39): --quick 是 flag 不是位置参数 — argv[1] 被它占用时轮名错位
    # (实测 "round=--quick" 落盘 --quick.json, 轮名丢失)。
    # v0.11.0 R110 (真缺陷 42): 39 的修复只硬编码过滤了 --quick 一个 flag — 实证复发:
    # 批跑包装脚本把 "--batch mass_71" 传进来, "--batch" 被当轮名落盘 --batch.json
    # (2026-09-07 00:06, 数据 1 case tokens=0)。改为通用规则: 所有 '-' 开头的 argv
    # 一律不算位置参数 (当前接口仅 --quick 无值 flag; 引入带值 flag 时须同步改此处)。
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    quick = "--quick" in sys.argv
    rnd = args[0] if args else "baseline"
    label = args[1] if len(args) > 1 else ""
    # v0.11.0 R27: --quick 高频回归模式 — 4 关键用例 (普通/多步/executive/推理),
    # 约 25s 一轮 (全量 70-140s), 供千轮级循环高频迭代; 全量轮仍用默认模式。
    all_cases = json.load(open("eval/cases.json"))
    if quick:
        # v0.11.0 R94: quick 4→5 — 加 C11 JSON 格式哨兵 (每批产出格式合规率, PGO 新维度)
        keep = ("C01", "C03", "C06", "C08", "C11")
        all_cases = [c for c in all_cases if c["id"].startswith(keep)]
    cases = all_cases
    env = load_env()
    # v0.11.0 R107 (真缺陷 40): 本地通道批测泄漏 — qwen gguf 就绪后 llm-service 守护使 local
    # IsAvailable=true, 批测未设 AGENTFRAMEWORK_LOCAL_DISABLED=1 时全部用例被 local 优先抢走
    # (tokens=0, 0.5B CPU 71s/轮, C11 ctx 4096 溢出真失败, 2026-09-07 实证 mass_79 retired)。
    # harness 层强制兜底: 本地通道对评测是确定性污染源, 不依赖调用方记得设环境变量。
    env.setdefault("AGENTFRAMEWORK_LOCAL_DISABLED", "1")
    if os.environ.get("AGENTFRAMEWORK_EVAL_ALLOW_LOCAL") == "1":
        env.pop("AGENTFRAMEWORK_LOCAL_DISABLED", None)  # 显式逃生口: 本地通道专项评测时用
    # v0.11.0 R81: 评测隔离 — R79 RAG 索引落盘会让前轮记忆泄入本轮 (真机是功能, 评测是污染),
    # 每轮启动前清空 RAG 落盘 + 会话记忆, 保证轮间独立可比。
    for stale in ("data/rag/index.jsonl",):
        if os.path.exists(stale):
            os.remove(stale)
    for sess in glob.glob("data/sessions/cli-*_memory.json"):
        os.remove(sess)
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
    sys.exit(main())
