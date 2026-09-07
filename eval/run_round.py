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

def run_case_repl(case, env):
    """R116: 多轮 REPL 用例 — 单进程多轮 stdin, 断言聚焦最后一轮 (隔离/pivot/长会话覆盖)。
    telemetry 为全程聚合; reply 取最后一个非命令轮的回复。"""
    case_tel = os.path.abspath("data/telemetry/host.jsonl")
    env["AGENTFRAMEWORK_TELEMETRY"] = os.path.dirname(case_tel)
    if os.path.exists(case_tel):
        os.remove(case_tel)
    t0 = time.time()
    stdin_text = "\n".join(case["repl"]) + "\n"
    p = subprocess.run(
        ["dotnet", "run", "--project", "src/agent.host", "-c", "Release", "--no-build", "--", "--log", "/tmp/repl-case.log"],
        input=stdin_text, capture_output=True, text=True, timeout=300, env=env)
    wall_ms = int((time.time() - t0) * 1000)
    out = p.stdout
    blocks = re.findall(r"──+\s*回复\s*──+\n(.*?)(?:\n  · intent=|\n\n❯|\n──+)", out, re.S)
    replies = []
    for b in blocks:
        b = "\n".join(l for l in b.split("\n")
                      if not l.startswith("@chatbox:") and "[20" not in l[:26]).strip()
        if b:
            replies.append(b)
    reply = replies[-1] if replies else ""
    points = read_telemetry(case_tel)
    return {"reply": reply, "raw_tail": out[-300:], "points": points, "wall_ms": wall_ms,
            "replies": replies}
def summarize_points(points):
    """聚合打点 → 指标 dict"""
    s = {"points": len(points), "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
         "total_tokens": 0, "llm_ms_est": None, "skill_hits": [], "skill_force": None,
         "intent": None, "subtasks": 0, "assembly_ok": None, "loop_success": None,
         "loop_ms": None, "models": [],
         "snippets": 0, "sources_recall": "", "assembly_ms": None, "from_cache": None,
         "prompt_total_tokens": None, "history_tokens": None, "gate_to_ask": None,
         "isolated": None, "isolated_score": None, "bge_provider": None, "bge_ms": None,
         "intent_ms": None, "llm_ms_total": 0, "phase_llm_ms": None}
    for pt in points:
        kv = pt.get("kv", {}) or {}
        tag = pt.get("point")
        if tag == "llm_call":
            s["llm_calls"] += 1
            s["prompt_tokens"] += kv.get("prompt_tokens", 0) or 0
            s["completion_tokens"] += kv.get("completion_tokens", 0) or 0
            s["total_tokens"] += kv.get("total_tokens", 0) or 0
            s["models"].append(kv.get("model"))
            # R129 (D3): LLM 真耗时累计 (成功/失败均含)
            if kv.get("ms") is not None:
                s["llm_ms_total"] += kv.get("ms") or 0
        elif tag == "phase_timing" and kv.get("phase") == "llm":
            # R129 (D3): LLM 全段 (含路由) — 与 llm_ms_total 差值 = 路由/重试开销
            s["phase_llm_ms"] = (s["phase_llm_ms"] or 0) + (kv.get("ms") or 0)
        elif tag == "skill":
            mid = kv.get("matched")
            if mid and mid != "(none)":
                s["skill_hits"].append({"skill": mid, "level": kv.get("level"), "precision": kv.get("precision")})
        elif tag == "intent":
            s["intent"] = kv.get("primary")
            s["subtasks"] = kv.get("subtask_count", 0)
            # R129 (D3): 意图阶段热路径耗时
            if kv.get("ms") is not None:
                s["intent_ms"] = kv.get("ms")
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
        elif tag == "subagent":
            # R116: 隔离维度 (无关话题隔离 E2E 判定)
            s["isolated"] = bool(kv.get("isolated"))
            s["isolated_score"] = kv.get("relevance_score")
        elif tag == "bge_embed":
            # R116: P3 真链维度 (bge-local=真向量 / hash-fallback=词袋)
            s["bge_provider"] = kv.get("provider")
            s["bge_ms"] = kv.get("ms")
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
        # R120: telemetry 瞬时丢失防护 — llm_calls=0 但有实质回复 = 打点链路丢点 (mass_151 C03 实证:
        # reply 完整/wall 正常/复跑 5/5 绿)。评分器自身缺陷不得判被测对象 FAIL → 标记按通过计。
        if (not agg["llm_calls"]) and reply and exp["llm"]:
            notes.append(f"telemetry_anomaly: llm_calls=0 but reply={len(reply)}ch (transient, counted pass)")
        else:
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
        # R116: repl 型用例 (多轮会话) → run_case_repl
        r = run_case_repl(c, env) if c.get("repl") else run_case(c, env)
        agg = summarize_points(r["points"])
        ok, notes = check_expect(c, r["reply"], agg, r["raw_tail"])
        results.append({"id": c["id"], "input": c.get("input") or " | ".join(c.get("repl", [])), "pass": ok, "notes": notes,
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
    # v0.11.0 R128 (PGO v2 D5): 对比基准自动化 — 落盘前读历史轮 (同 quick 口径), 计算 per-case
    # 平滑均值 delta + 全轮 KPI 健康带判定 (D2)。analyze.py 消费 delta 字段, 无需人工对表。
    def _hist_delta(field):
        """近 3 轮同用例均值 → {case_id: base_avg}"""
        hist = {}
        # R128 缺陷 53: 字典序让 stability_* 等老轮排最后 — 按轮内 ts 排序 (ISO 时间戳字典序=时间序)
        def _ts(f):
            try:
                return json.load(open(os.path.join(ROUNDS, f))).get("ts", "")
            except Exception:
                return ""
        fs = sorted((f for f in os.listdir(ROUNDS) if f.endswith(".json")), key=_ts)
        for f in (fs[-6:-1] if len(fs) > 6 else fs[:-1]):  # 最近若干轮 (不含本轮)
            try:
                d = json.load(open(os.path.join(ROUNDS, f)))
                if d.get("cases") != len(results):
                    continue  # quick/全量口径不一致 → 跳过
                for x in d["results"]:
                    hist.setdefault(x["id"], []).append(x.get(field) or 0)
            except Exception:
                pass
        return {k: sum(v[-3:]) / min(3, len(v)) for k, v in hist.items() if v}
    tok_base = _hist_delta("total_tokens")
    wall_base = _hist_delta("wall_ms")
    # KPI 健康带 (D2): 来自批26-39 基线 — 越界即标记, 连续越界由 analyze 判 WATCH
    KPI = {"tokens_per_case": (500, 950), "wall_per_case_ms": (12000, 30000)}
    breaches = []
    n = max(1, len(results))
    avg_tok = summary["tokens_total"] / n
    avg_wall = summary["wall_total_ms"] / n
    if not (KPI["tokens_per_case"][0] <= avg_tok <= KPI["tokens_per_case"][1]):
        breaches.append(f"tokens_per_case={avg_tok:.0f} out {KPI['tokens_per_case']}")
    if not (KPI["wall_per_case_ms"][0] <= avg_wall <= KPI["wall_per_case_ms"][1]):
        breaches.append(f"wall_per_case_ms={avg_wall:.0f} out {KPI['wall_per_case_ms']}")
    for x in results:
        b = tok_base.get(x["id"])
        x["delta_tokens_vs_hist"] = round(x["total_tokens"] - b) if b else None
        w = wall_base.get(x["id"])
        x["delta_wall_vs_hist"] = round(x["wall_ms"] - w) if w else None
    summary["kpi_breaches"] = breaches
    summary["hist_base_rounds"] = len(tok_base)
    path = f"{ROUNDS}/{rnd}.json"
    json.dump(summary, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"\n=== round={rnd} passed={summary['passed']}/{summary['cases']} tokens={summary['tokens_total']} wall={summary['wall_total_ms']}ms → {path}")
    if breaches:
        print(f"KPI_BREACH: {'; '.join(breaches)}")
    else:
        print("KPI: in-band")
    # R130: eval/results 自动镜像 — 报告可恢复迭代的数据源 (历史靠手工 cp 常漏)
    try:
        import shutil
        os.makedirs("eval/results", exist_ok=True)
        shutil.copy2(path, f"eval/results/{rnd}.json")
    except OSError as e:
        print(f"WARN: results mirror failed: {e}")
    # R132 (用户钦定): eval/reports 每轮数据记录 — 人类可读的批测战报 (随轮追加, 一轮一节)
    try:
        os.makedirs("eval/reports", exist_ok=True)
        rp = "eval/reports/round-log.md"
        exists = os.path.exists(rp)
        with open(rp, "a", encoding="utf-8") as f:
            if not exists:
                f.write("# 千轮批测数据记录 (自动追加, 一轮一节)\n\n")
            f.write(f"## {rnd} — {label or 'unlabeled'} ({summary['ts'] if 'ts' in summary else ''})\n\n")
            f.write(f"- **判定**: {summary['passed']}/{summary['cases']} passed, "
                    f"tokens_total={summary['tokens_total']} (avg {avg_tok:.0f}), "
                    f"wall={summary['wall_total_ms']}ms (avg {avg_wall/1000:.1f}s)\n")
            f.write(f"- **KPI**: {'; '.join(breaches) if breaches else 'in-band'}"
                    f" (基准轮数 {summary.get('hist_base_rounds', 0)})\n")
            f.write(f"- **per-case**: ")
            f.write(" | ".join(
                f"{x['id']} {x['total_tokens']}tok {x['wall_ms']/1000:.1f}s"
                + (f" Δ{delta:+d}" if (delta := x.get("delta_tokens_vs_hist")) is not None else "")
                for x in results))
            f.write("\n\n")
        print(f"report appended → {rp}")
    except OSError as e:
        print(f"WARN: report append failed: {e}")

if __name__ == "__main__":
    sys.exit(main())
