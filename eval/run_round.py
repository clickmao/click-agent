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
    for line in open(path, encoding="utf-8-sig", errors="replace"):  # R299: 非UTF8字节容错 (llama日志噪声)
        line = line.strip()
        if not line:
            continue
        try:
            points.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return points

def _apply_charter_setup(case):
    """v0.15.1-a (R322): 用例级 fixture — setup.charter 预写 active.json + setup.guardrails 预置 guardrails.json;
    返回还原函数 (同时还原两文件)。"""
    setup = case.get("setup") or {}
    charter_setup = setup.get("charter")
    guardrails = setup.get("guardrails")
    if not charter_setup and not guardrails:
        return lambda: None
    import json as _j
    restores = []
    if charter_setup:
        _charters_dir = os.path.abspath("data/task-charters")
        _charter_active = os.path.join(_charters_dir, "active.json")
        os.makedirs(_charters_dir, exist_ok=True)
        backup = open(_charter_active, encoding="utf-8").read() if os.path.exists(_charter_active) else None
        c = dict(charter_setup)
        c.setdefault("Id", f"tc{int(time.time()*1000)%10**12:012d}")
        c.setdefault("Status", "running")
        for k, v in (("PendingInputs", []), ("KeyEntities", []), ("AcceptanceCriteria", []), ("ScopeOut", [])):
            c.setdefault(k, v)
        c.setdefault("CreatedUtc", "2026-09-09T00:00:00Z")
        open(_charter_active, "w", encoding="utf-8").write(_j.dumps(c, ensure_ascii=False))
        def restore_charter():
            if backup is not None:
                open(_charter_active, "w", encoding="utf-8").write(backup)
            elif os.path.exists(_charter_active):
                os.remove(_charter_active)
        restores.append(restore_charter)
    if guardrails:
        _gr_path = os.path.abspath("data/guardrails.json")
        gr_backup = open(_gr_path, encoding="utf-8").read() if os.path.exists(_gr_path) else None
        open(_gr_path, "w", encoding="utf-8").write(_j.dumps(guardrails, ensure_ascii=False))
        def restore_guardrails():
            if gr_backup is not None:
                open(_gr_path, "w", encoding="utf-8").write(gr_backup)
            elif os.path.exists(_gr_path):
                os.remove(_gr_path)
        restores.append(restore_guardrails)
    def restore_all():
        for fn in restores:
            fn()
    return restore_all


def run_case_with_setup(case, env):
    """统一入口: setup 钩子 (repl/非 repl 通用) → 原执行函数。"""
    restore = _apply_charter_setup(case)
    try:
        return run_case_repl(case, env) if case.get("repl") else run_case(case, env)
    finally:
        restore()


def run_case(case, env):
    """跑单用例 → {reply, points, wall_ms}"""
    # v0.11.0 R110 (fix#42): 每用例独立 telemetry 文件 (绝对路径 env 覆写) —
    # 共享单文件的 remove→append→read 时序竞争曾致间歇 llm_calls=0 误判 (mass_99/99b/99c/99d)。
    case_tel = os.path.abspath("data/telemetry/host.jsonl")  # CLI 固定写 host.jsonl, 每用例独占目录
    env["AGENTFRAMEWORK_TELEMETRY"] = os.path.dirname(case_tel)
    if os.path.exists(case_tel):
        os.remove(case_tel)
    t0 = time.time()
    # v0.11.0 R172 (真缺陷 59): per-case 超时容错 — 此前 TimeoutExpired 直接冒泡,
    # 一个用例 180s 超时 = 整批崩死、后续用例全不跑、轮 JSON 不落盘 (批113 死于 C13 实证)。
    # v0.12.0 A2: 图像用例 (case["image"]) → -img 传给 CLI vision 链
    img_args = ["-img", case["image"]] if case.get("image") else []
    try:
        p = subprocess.run(
            ["dotnet", "run", "--project", "src/agent.host", "-c", "Release", "--no-build", "--", "-q", case["input"], *img_args],
            capture_output=True, text=True, timeout=180, env=env)
    except subprocess.TimeoutExpired:
        # R174: LLM 瞬态挂起 (C08/C13 实证, 历史 wall 12-22s) — 重试 1 次; 再超时才记 FAIL (保留首次事实)。
        print(f"[TIMEOUT] {case['id']} wall=180s — 重试 1/1 (LLM 瞬态假设)", flush=True)
        try:
            p = subprocess.run(
                ["dotnet", "run", "--project", "src/agent.host", "-c", "Release", "--no-build", "--", "-q", case["input"], *img_args],
                capture_output=True, text=True, timeout=180, env=env)
        except subprocess.TimeoutExpired:
            wall_ms = 180_000
            p = None
            print(f"[TIMEOUT] {case['id']} 重试仍 180s — 记 FAIL 批继续", flush=True)
    wall_ms = int((time.time() - t0) * 1000)
    out = p.stdout if p is not None else ""
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
         "total_tokens": 0, "llm_ms_est": None, "skill_hits": [], "skill_force": None, "skill_match": None, "skill_decisions": [],
         "intent": None, "subtasks": 0, "assembly_ok": None, "loop_success": None,
         "loop_ms": None, "models": [],
         "snippets": 0, "sources_recall": "", "assembly_ms": None, "from_cache": None,
         "prompt_total_tokens": None, "history_tokens": None, "gate_to_ask": None,
         "isolated": None, "isolated_score": None, "bge_provider": None, "bge_ms": None,
         "intent_ms": None, "llm_ms_total": 0, "phase_llm_ms": None,
         # R142 (用户钦定历史缺口回接): compression 防漂移指数 — 打点 2026-09 R129 起就有,
         # 但 summarize_points 从未消费 → 轮 JSON/报告层不可见 (数据蒸发)。
         # R151 (真缺陷 56): pivot_n 缺初始化 — C15 pivot_reanchor 全量批一跑即 KeyError
         # (quick-11 不含 C15 所以 batch75 侥幸通过; 与 R142 compression 同源教训:
         #  新增打点消费必须同步补 init 键)。
         "compress_n": 0, "compress_drift_ok": 0, "compress_semantic": [],
         "compress_chars_in": 0, "compress_chars_out": 0, "pivot_n": 0,
         "topic_relevance_score": 0, "topic_relevance_verdict": None, "topic_drift_n": 0,
         "topic_clarify_pulled": 0, "task_input_routes": [],
         "gate_mode": None, "gate_est": None,
         "guardrail_injected": 0, "guardrail_writes": 0}
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
        elif tag == "skill_match":
            if s.get("skill_match") is None:
                s["skill_match"] = {"top1": kv.get("top1"), "level": kv.get("level"),
                                     "precision": kv.get("precision"), "runner_up_gap": kv.get("runner_up_gap")}
        elif tag == "skill_trigger":
            s.setdefault("skill_decisions", []).append(kv.get("decision"))
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
        elif tag == "context_gate":
            # v0.13.3 M4: 上下文预算门 (normal/isolated_micro/hard_drop) — 微隔离触发观测点
            s["gate_mode"] = kv.get("mode")
            s["gate_est"] = kv.get("est_tokens")
        elif tag == "guardrail":
            s["guardrail_injected"] = kv.get("injected") or 0
        elif tag == "guardrail_write":
            s["guardrail_writes"] += 1
        elif tag == "task_input":
            # v0.15.1: 任务进行中新输入路由观测 (supplement/isolate/pivot)
            s["task_input_routes"].append(f"{kv.get('route')}@{kv.get('score')}")
        elif tag == "topic_clarify":
            # R315: L3 拉回率观测 (clarify 问句后 ≤2 轮回锚)
            if kv.get("pulled_back"):
                s["topic_clarify_pulled"] += 1
        elif tag == "topic_relevance":
            # R308c: 合并判定打点消费 — no-anchor 轮也记 (stage 字段区分, 消除观测盲区)
            if kv.get("stage") == "no-anchor":
                s["topic_relevance_verdict"] = "NoAnchor"
                s["topic_drift_n"] += 1 if kv.get("drift") else 0
            else:
                s["topic_relevance_score"] = kv.get("score") or 0
                s["topic_relevance_verdict"] = kv.get("verdict")
                if kv.get("verdict") == "SteerHint":
                    s["topic_drift_n"] += 1
        elif tag == "loop_turn":
            s["loop_success"] = kv.get("success")
            s["loop_ms"] = kv.get("total_ms")
        elif tag == "subagent":
            # R116: 隔离维度 (无关话题隔离 E2E 判定)
            s["isolated"] = bool(kv.get("isolated"))
            s["isolated_score"] = kv.get("relevance_score")
        elif tag == "goal" and kv.get("op") == "pivot":
            # R151: pivot 重锚打点消费 (打点源 IndustrialAgentV2 goal/pivot; 防 C15 断言空心 — 同 R142 compression 教训)
            s["pivot_n"] += 1
        elif tag == "bge_embed":
            # R116: P3 真链维度 (bge-local=真向量 / hash-fallback=词袋)
            s["bge_provider"] = kv.get("provider")
            s["bge_ms"] = kv.get("ms")
        elif tag == "compression":
            # R142: 防漂移指数聚合 — drift_ok 通过率 / 语义相似度均值 / 字符压缩率
            s["compress_n"] += 1
            if kv.get("drift_ok"):
                s["compress_drift_ok"] += 1
            if isinstance(kv.get("semantic"), (int, float)) and kv["semantic"] >= 0:
                s["compress_semantic"].append(kv["semantic"])
            chars = str(kv.get("chars", ""))
            if "->" in chars:
                a, b = chars.split("->")
                if a.isdigit() and b.isdigit():
                    s["compress_chars_in"] += int(a)
                    s["compress_chars_out"] += int(b)
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
    if "must_not_contain" in exp:
        # R138 (N5 幻觉防线): 诱饵用例 — 回复不得包含编造的具体内容 (如不存在的 API 签名)
        # R155: 支持字符串或列表 (C15 隔离前缀多模式拒绝断言)
        # R234 (C17 断言脆性实证): 深度求索类兜底模型拒答风格=「如 <签名>…但属推测」—
        # 字面子串命中把"显式标注的推测示例"误判为编造 (批203r C17 FAIL, models 链含 deepseek-v4-flash)。
        # 语义修正: 若用例配置 neg_context_markers (推测标记词表), 禁止模式前 80ch 内含任一标记
        # (如/例/推断/推测/假设/仅/只/按常规/但这属) → 视为元评论, 不判死, 记 suspect 观察;
        # 无标记的禁止模式出现 → 仍硬 FAIL (真编造是自信陈述, 不带推测围栏)。未配置的用例行为不变。
        _mnc = exp["must_not_contain"]
        if isinstance(_mnc, str):
            _mnc = [_mnc]
        _neg_markers = tuple(exp.get("neg_context_markers") or [])
        _reply_l = (reply or "").lower()
        for _pat in _mnc:
            _pat_l = _pat.lower()
            _pos = _reply_l.find(_pat_l)
            if _pos < 0:
                continue
            if _neg_markers:
                _ctx = _reply_l[max(0, _pos - 80):_pos]
                if any(mk in _ctx for mk in _neg_markers):
                    sus_note = f"禁止模式 '{_pat[:30]}' 出现在推测标记后 (元评论, 非事实陈述)"
                    if "suspects" not in agg or agg["suspects"] is None:
                        agg["suspects"] = []
                    agg["suspects"].append(sus_note)
                    continue
            # R299 (缺陷 68 围栏语义一般化; explore_eval 同源): 否定/纠错围栏 — 禁词出现在
            # 否定上下文 ("不是蓝色的/并非/没有") = 正确拒诱饵, 不是误信。用例无需配置。
            _neg_ctx = _reply_l[max(0, _pos - 40):_pos] + _reply_l[_pos + len(_pat_l):_pos + len(_pat_l) + 20]  # R311: 双向窗口 (前 40ch 长引用 + 后 20ch 后置否定)
            if any(nk in _neg_ctx for nk in ("不", "不是", "并非", "没有", "不能", "错误", "不会", "无法", "并非是", "incorrect", "false", "不是的")):
                if "suspects" not in agg or agg["suspects"] is None:
                    agg["suspects"] = []
                agg["suspects"].append(f"禁止模式 '{_pat[:30]}' 出现在否定上下文 (正确拒诱饵)")
                continue
            req(False, f"reply 命中禁止模式 '{_pat[:40]}'")
    if "guardrail_injected" in exp:
        got = agg.get("guardrail_injected") or 0
        req(got >= exp["guardrail_injected"], f"guardrail_injected={got} want >={exp['guardrail_injected']}")
    if "guardrail_write" in exp:
        got_w = agg.get("guardrail_writes") or 0
        req(got_w >= exp["guardrail_write"], f"guardrail_write={got_w} want >={exp['guardrail_write']}")

    if "task_route" in exp:
        # v0.15.1-a (R149 真断言): 章程路由判定的批测断言 — task_input_routes 含指定 route
        routes = agg.get("task_input_routes") or []
        want = exp["task_route"]
        if not any(r.startswith(want + "@") for r in routes):
            req(False, f"task_route={routes} want {want}")

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
    # v0.11.0 R149 (用户质疑核实: TaskRelevance 判定空心): C14/C15 既往 expect 只有 llm:true —
    # "隔离是否真的发生"从未绑定到 pass, 通过率对 TaskRelevanceChecker 无证明力 (判定空心)。
    # 补真实断言族: isolated_true/false 消费 telemetry isolated 打点, pivot_reanchor 消费回复。
    if "isolated_true" in exp:
        req(agg["isolated"] is True, f"isolated={agg['isolated']} (score={agg['isolated_score']}) want True")
    if "isolated_false" in exp:
        req(agg["isolated"] is not True, f"isolated={agg['isolated']} (score={agg['isolated_score']}) want False")
    if "pivot_reanchor" in exp:
        req(agg["isolated"] is not True, f"pivot 轮被隔离误吞 (isolated={agg['isolated']} score={agg['isolated_score']})")
        # R151: 重锚必须真实发生 (op=pivot 打点) — 防判定空心 (None 伪装"未隔离")
        req((agg.get("pivot_n") or 0) >= 1, f"pivot 重锚未发生 (pivot_n={agg.get('pivot_n')})")
        req(len(reply) >= 10, f"pivot 后回复过短 ({len(reply)}ch, 未产出新任务链)")
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
    # v0.13.3 M4 (用户钦定 Baseline 换血): --suite=xl — 大上下文/微隔离触发族 (cases-xl.json)
    suite = "default"
    for a in sys.argv[1:]:
        if a.startswith("--suite="):
            suite = a.split("=", 1)[1]
    # v0.11.0 R154 (真缺陷 58): harness 对 dotnet 的 PATH 依赖自兜底 — 新 shell/cron 忘 export
    # PATH 时 repl 用例 FileNotFoundError 半途崩批 (批83 首跑实证), fail-fast 带修复提示。
    import shutil as _sh
    if not _sh.which("dotnet"):
        _hint = os.path.expanduser("~/.dotnet")
        print(f"FATAL: dotnet not on PATH — repl 用例无法启动。修复: export PATH=\"{_hint}:$PATH\" (或 source .env.local 前先 export)", file=sys.stderr)
        sys.exit(2)
    rnd = args[0] if args else "baseline"
    label = args[1] if len(args) > 1 else ""
    # v0.11.0 R27: --quick 高频回归模式 — 4 关键用例 (普通/多步/executive/推理),
    # 约 25s 一轮 (全量 70-140s), 供千轮级循环高频迭代; 全量轮仍用默认模式。
    if suite == "xl":
        all_cases = json.load(open("eval/cases-xl.json"))
    elif suite == "explore":
        # R296: 探索族入批测轮换 — explore_cases.json (24 样本: 12 原始 + 12 可达 URL);
        # 字段适配: explore 平铺 must_contain/must_not_contain → expect{} 结构 (与判定器兼容)。
        _ec = json.load(open("eval/explore_cases.json"))
        _raw = _ec["cases"] if isinstance(_ec, dict) else _ec
        all_cases = []
        for c in _raw:
            all_cases.append({
                "id": c["id"],
                "input": c["input"],
                "expect": {
                    "llm": True,
                    "must_contain": c.get("must_contain", []),
                    "must_not_contain": c.get("must_not_contain", []),
                },
            })
    else:
        all_cases = json.load(open("eval/cases.json"))
    ids_filter = None
    for a in list(sys.argv[1:]):
        if a.startswith("--ids="):
            sys.argv.remove(a)
            ids_filter = tuple(a[6:].split(","))
    if ids_filter:
        all_cases = [c for c in all_cases if c["id"].startswith(ids_filter) or c["id"] in ids_filter]
    if quick and not ids_filter:
        # v0.11.0 R94: quick 4→5 — 加 C11 JSON 格式哨兵 (每批产出格式合规率, PGO 新维度)
        # v0.11.0 R143 (用户钦定): quick 5→10 + 广泛度扩展 — 5 关键 + 5 多样性
        # (记忆 C07 / 敏感 C13 / 幻觉诱饵 C17 / 格式陷阱 C18 / skill 身份 C04):
        # 每批覆盖 10/19 用例 → 记忆链/负面族/skill 链进常态采集, 不再只在全量批可见。
        # v0.11.0 R149 (用户质疑 TaskRelevance 覆盖空心): quick 10→11 — C14 隔离用例进常态
        # (isolated_true 断言绑定后, TaskRelevanceChecker 每批真实验证, 健康带口径随之 quick-11)。
        # v0.13.3 R317 (拉回率进常态): quick 11→12 — C19 clarify 6 轮案 (pulled_back 每批观测,
        # 与 R149 同理由: L3 牵引链真断言, 批均 token 带宽 +6 轮 repl ~2.4k)。
        # v0.15.1-b (R322): quick 12→13 — C26 critic 假阳性负样本 (无代码块零触发, R149 真断言)
        keep = ("C01", "C03", "C04", "C06", "C07", "C08", "C11", "C13", "C14", "C17", "C18", "C19", "C26")
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
        r = run_case_with_setup(c, env)
        agg = summarize_points(r["points"])
        ok, notes = check_expect(c, r["reply"], agg, r["raw_tail"])
        results.append({"id": c["id"], "input": c.get("input") or " | ".join(c.get("repl", [])), "pass": ok, "notes": notes,
                        "reply": r["reply"][:400], "wall_ms": r["wall_ms"], **agg})
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {c['id']}  wall={r['wall_ms']}ms tokens={agg['total_tokens']} intent={agg['intent']} skill={len(agg['skill_hits'])}")
        for n in notes:
            print("    ", n)
    # R136 (D4 reply_rel): 离线语义质量打点 — 每用例 (question, reply) bge 余弦 <0.5 → quality_suspect。
    # 用 --embed 子命令 (bge 真链, 512dim), 模型缺失 → 全部 rel=None (诚实缺省, 不造假数据)。
    host_dll = "src/agent.host/bin/Release/net10.0/agenthost.dll"
    # v0.11.0 R153 (真缺陷 57): gate 读 os.environ 但 bge 路径只在 .env.local → 未 export 的
    # 启动环境 (cron/新 shell) 下 D4 整块静默跳过, reply_rel 全 None (批79/80 实证 n=0)。
    # 修: gate 与子进程同源 — 都读 load_env() 合并后的 env (.env.local 兜底)。
    if os.path.exists(host_dll) and env.get("AGENTFRAMEWORK_BGE_MODEL"):
        def _embed(text):
            try:
                p = subprocess.run(["dotnet", host_dll, "--embed", text[:2000]],
                                   capture_output=True, text=True, timeout=60, env=env)
                return json.loads(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip().startswith("[") else None
            except Exception:
                return None
        vecs = {}
        cases_by_id = {c["id"]: c for c in cases}
        for c in cases:
            vecs[c["id"]] = (_embed(c.get("input", c.get("query", ""))), None)
        exp_llm = {c["id"]: c.get("expect", {}).get("llm", True) for c in cases}
        for x in results:
            qv = vecs.get(x["id"], (None,))[0]
            rv = _embed(x.get("reply", "")) if x.get("reply") else None
            if qv and rv and len(qv) == len(rv):
                dot = sum(a*b for a, b in zip(qv, rv))
                x["reply_rel"] = round(dot / ((sum(a*a for a in qv) ** 0.5) * (sum(b*b for b in rv) ** 0.5) or 1), 4)
                # R136 校准 (批46 实证): executive 模板回复 ("97.88°F") 与自然语言问句结构性低余弦
                # (0.436 假阳性) — 阈值分层: LLM 回复 <0.5 suspect, 模板回复 <0.3 才 suspect。
                # R144 校准 (批50/53/56/57 四批实证): 记忆元问题 (session_aware) 的 rel 0.40-0.44 —
                # "问记不记得" vs "复述内容" 词汇面无重叠但回复正确 (人工核对 C07 四批全对),
                # 阈值降 0.4: 会话感知类假阳性消除, 真记忆丢失 (<0.4) 仍能抓到。
                # R147 再校准 (批56-65 十批): C07 rel 波动带 0.37-0.60 (内容全对), 0.4 仍截出 2 假阳性
                # (批63 0.3716/批65 0.399) — 阈值 0.35 (正确回复实测最低 0.37 之下留 0.02 裕度,
                # 真丢失=复述不出上文内容, 语义面完全跑偏才会 <0.35)。
                is_template = (exp_llm.get(x["id"], True) is False) or x.get("total_tokens", 0) == 0
                is_session_aware = bool(cases_by_id.get(x["id"], {}).get("expect", {}).get("session_aware"))
                thr = 0.3 if is_template else (0.35 if is_session_aware else 0.5)
                # R148 (第 3 次假阳性批67 0.3458 根治): session_aware 判定改内容命中 —
                # "元问题 vs 复述" 余弦信噪比不足 (正确回复波动带 0.345-0.60, 三次校准均追波动),
                # rel 保留为参考打点, suspect 判定改由 must_contain 关键词命中承担 (真实内容断言)。
                # R150: C14 隔离用例的 rel 天然低 (离题消息 vs 任务锚, 语义本就远) — suspect 判定
                # 已由 isolated_true 真断言承担, rel 同 C07 一样降为纯参考。
                has_real_assert = bool(cases_by_id.get(x["id"], {}).get("expect", {}).get("isolated_true")) or \
                    bool(cases_by_id.get(x["id"], {}).get("expect", {}).get("pivot_reanchor"))
                if is_session_aware or has_real_assert:
                    kws = cases_by_id.get(x["id"], {}).get("expect", {}).get("must_contain", [])
                    reply_l = (x.get("reply") or "").lower()
                    if kws and not any(k.lower() in reply_l for k in kws):
                        # R180 (R149 判定空心原则的收口): must_contain 观察期结束 —
                        # C07 批337-339 内容断言 4 轮实证全对, 批340 记忆丢失 (回复"没收到") 被 suspect 放过 = 判定空心复发。
                        # 未命中关键词 = 真断言 FAIL (不再只是 suspect)。
                        x["quality_suspect"] = True
                        # R181 (真缺陷 60): R180 误用 check_expect 作用域的 req() 于 summarize 区 → NameError 崩批
                        # (批128 首跑实证)。此处直接置 pass=False + fail_reason (passed 计数消费 x["pass"])。
                        x["pass"] = False
                        x["fail_reason"] = f"must_contain 未命中 {kws[:3]} — 内容断言真判定 (R180)"
                elif x["reply_rel"] < thr:
                    x["quality_suspect"] = True
            else:
                x["reply_rel"] = None
        rels = [x["reply_rel"] for x in results if x.get("reply_rel") is not None]
        print(f"D4 reply_rel: n={len(rels)} avg={sum(rels)/len(rels):.3f}" if rels else "D4 reply_rel: unavailable (model missing)")
    else:
        for x in results:
            x["reply_rel"] = None

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
    # KPI 健康带 (D2): R139 重校准 — 批50 (mass_266) 19 用例新口径首批基线 (1100tok/case)。
    # 旧带 (500,950) 为 17 用例口径, 19 用例含 C16 长会话+C17/C18 负面必越界 (口径切换非劣化)。
    # 口径分带: full-19 (批50 基线) vs quick-10 (R143 扩容: 5 关键+5 多样性含负面/skill/记忆)
    # quick-10 估 tok/case ≈ 780 (批49 全量 per-case 推导); wall 上限放宽 (C13/C17 LLM 用例拖尾)
    if len(results) <= 12:
        # R149: quick-11 口径 (+C14 repl 双轮) — tok 均值摊薄带不变; C14 双 LLM 轮 wall 拖尾 → 上限 40→55s
        # R182: C07 改 repl 双轮 (真缺陷 61 修复配套) → +1 轮 LLM 成本, tok 上界 1100→1250 (批131 1193 实证锚定)
        KPI = {"tokens_per_case": (600, 1250), "wall_per_case_ms": (8000, 55000)}
    else:
        KPI = {"tokens_per_case": (900, 1300), "wall_per_case_ms": (12000, 45000)}
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
    # R142 (防漂移/意图指数, 用户钦定历史缺口回接): 轮级派生 —
    # drift_rate=锚词校验通过率, semantic_avg=bge 语义保真均值, compress_ratio=字符压缩率
    cn = sum(x.get("compress_n", 0) for x in results)
    dok = sum(x.get("compress_drift_ok", 0) for x in results)
    sems = [v for x in results for v in x.get("compress_semantic", [])]
    cin = sum(x.get("compress_chars_in", 0) for x in results)
    cout = sum(x.get("compress_chars_out", 0) for x in results)
    summary["compression_index"] = {
        "segments": cn,
        "drift_pass_rate": round(dok / cn, 3) if cn else None,
        "semantic_avg": round(sum(sems) / len(sems), 3) if sems else None,
        "chars_ratio": round(cout / cin, 3) if cin else None,
    }
    int_ms = [x["intent_ms"] for x in results if x.get("intent_ms") is not None]
    summary["intent_index"] = {
        "n": len(int_ms),
        "ms_avg": round(sum(int_ms) / len(int_ms), 1) if int_ms else None,
        "dist": {},  # 下面填
    }
    from collections import Counter as _C
    summary["intent_index"]["dist"] = dict(_C(x.get("intent") for x in results if x.get("intent")))
    path = f"{ROUNDS}/{rnd}.json"
    json.dump(summary, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"\n=== round={rnd} passed={summary['passed']}/{summary['cases']} tokens={summary['tokens_total']} wall={summary['wall_total_ms']}ms → {path}")
    # v0.13.3 (KPI-2 承诺③): history/prompt 构成单列 — 上下文注入膨胀的观测点:
    _pts = [x.get("prompt_total_tokens") or 0 for x in results if x.get("prompt_total_tokens")]
    _hts = [x.get("history_tokens") or 0 for x in results if x.get("history_tokens")]
    if _pts:
        _hist_share = (sum(_hts) / sum(_pts) * 100) if _hts and sum(_pts) > 0 else 0
        print(f"token-breakdown: prompt={sum(_pts)} history={sum(_hts)} ({_hist_share:.0f}%) completion={sum(x.get('completion_tokens') or 0 for x in results)}")
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
            # R142: 防漂移/意图指数入报告 (用户钦定历史缺口回接)
            ci = summary.get("compression_index") or {}
            if ci.get("segments"):
                f.write(f"- **防漂移指数**: segments={ci['segments']}, "
                        f"drift_pass={ci['drift_pass_rate']}, "
                        f"semantic_avg={ci['semantic_avg']}, "
                        f"chars_ratio={ci['chars_ratio']}\n")
            ii = summary.get("intent_index") or {}
            if ii.get("n"):
                f.write(f"- **意图指数**: n={ii['n']}, ms_avg={ii['ms_avg']}, "
                        f"dist={ii.get('dist', {})}\n")
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
