#!/usr/bin/env python3
"""R491 付费调用**明文导出**（用户要求：把省了 70%+ 付费的输入/输出明文拿出来看）。

输入（全部只读，零手抄）:
  eval/rover/r491/calls-<arm>.jsonl   ← 中继侧**请求**明文（messages 全文 + tools_n + prompt_tokens_est）
  eval/rover/r491/usage-<arm>.jsonl   ← 中继侧**响应**度量（prompt/completion/cache/成本/finish_reason/content_len/reasoning_len）
  eval/rover/r491/tel-<arm>/host.jsonl← 宿主遥测（llm_call 的 turn / empty_reply；tool_decl_gate 的 declared/reason）
  eval/rover/r491/turns-<arm>.jsonl   ← 驱动落盘的**每轮可见答复**（输出侧明文）
输出: eval/rover/r491/paid-plaintext/*.md + tools-declaration.json
诚实边界: 中继**不落响应正文**（只有 content_len/reasoning_len/finish_reason）⇒ 逐调用输出只能给度量 + 轮级可见答复明文。
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "paid-plaintext")
ARMS = [("B(B 门关)", "Aroleb"), ("T1(声明门开)", "T1"), ("T2", "T2"), ("T3", "T3")]


def jl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in io.open(p, encoding="utf-8-sig") if l.strip()]


def render_msgs(msgs):
    out = []
    for i, m in enumerate(msgs):
        role = m.get("role")
        content = m.get("content")
        if content is None:
            content = json.dumps({k: v for k, v in m.items() if k != "role"}, ensure_ascii=False)
        tc = m.get("tool_calls")
        head = f"--- [{i}] role={role} len={len(str(content))}"
        if tc:
            head += f" tool_calls={json.dumps(tc, ensure_ascii=False)[:300]}"
        out.append(head + "\n" + str(content))
    return "\n\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for label, arm in ARMS:
        calls, usage, turns = (jl(f"{HERE}/calls-{arm}.jsonl"), jl(f"{HERE}/usage-{arm}.jsonl"),
                               os.path.join(HERE, f"turns-{arm}.jsonl"))
        tel = jl(f"{HERE}/tel-{arm}/host.jsonl")
        gate = [r["kv"] for r in tel if r.get("point") == "tool_decl_gate"]
        llm = [r["kv"] for r in tel if r.get("point") == "llm_call"]
        # 宿主打点行按 (prompt_tokens, completion_tokens) 与中继付费调用配对（禁按下标: 打点可能漏行）
        pool = list(llm)
        paired = []
        for u in usage:
            hit = None
            for j, t in enumerate(pool):
                if t.get("prompt_tokens") == u.get("prompt_tokens") and t.get("completion_tokens") == u.get("completion_tokens"):
                    hit = pool.pop(j)
                    break
            paired.append(hit)
        lines = [f"# {label} · 付费调用明文（arm={arm}）", ""]
        lines.append(f"- 付费调用数 = **{len(calls)}**；宿主 `llm_call` 行 = {len(llm)}；"
                     f"`tool_decl_gate` 行 = {len(gate)}")
        if calls:
            lines.append(f"- 每次请求的 `tools_n`（下发给上游的工具声明个数）= **{sorted({c['sampling'].get('tools_n') for c in calls})}**")
        lines.append("")
        tot_p = tot_c = tot_cost = 0.0
        for k, c in enumerate(calls):
            u = usage[k] if k < len(usage) else {}
            teli = paired[k] if k < len(paired) else None
            turn = teli.get("turn") if teli else None
            tot_p += u.get("prompt_tokens") or 0
            tot_c += u.get("completion_tokens") or 0
            tot_cost += u.get("cost_cny_upper") or 0.0
            msgs = c["messages"] if isinstance(c["messages"], list) else json.loads(c["messages"])
            lines.append(f"## 调用 #{k+1}（seq={c['seq']} turn≈{turn}）")
            lines.append("")
            lines.append("| 项 | 值 |")
            lines.append("|---|---|")
            lines.append(f"| 请求 messages 条数 | {c['n_messages']} |")
            lines.append(f"| 下发工具声明数 `tools_n` | **{c['sampling'].get('tools_n')}** |")
            lines.append(f"| 请求估算 tokens（中继） | {c['prompt_tokens_est']} |")
            lines.append(f"| 供应商真值 prompt/completion | {u.get('prompt_tokens')} / {u.get('completion_tokens')} |")
            lines.append(f"| 缓存命中/未命中 | {u.get('cache_hit_tokens')} / {u.get('cache_miss_tokens')} |")
            lines.append(f"| finish_reason | `{u.get('finish_reason')}` |")
            lines.append(f"| content_len / reasoning_len / empty_body | {u.get('content_len')} / {u.get('reasoning_len')} / {u.get('empty_body')} |")
            lines.append(f"| 输出侧: tool_calls_n / empty_cause | {teli.get('tool_calls_n') if teli else None} / `{teli.get('empty_cause') if teli else None}` |")
            lines.append(f"| 本调用成本上界(¥) | {u.get('cost_cny_upper')} |")
            lines.append("")
            lines.append("**输入明文（逐条 messages）**")
            lines.append("")
            lines.append("```text")
            lines.append(render_msgs(msgs))
            lines.append("```")
            lines.append("")
        lines.append(f"**合计**: prompt {int(tot_p)} + completion {int(tot_c)} = **{int(tot_p+tot_c)} tok**；成本上界 **¥{round(tot_cost,6)}**")
        p = os.path.join(OUT, f"{arm}__paid-calls.md")
        io.open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        index.append((label, arm, len(calls), int(tot_p), int(tot_c), round(tot_cost, 6), p))

        # 轮级可见答复（输出侧明文）
        if os.path.exists(turns):
            t = json.load(io.open(turns, encoding="utf-8-sig"))
            tl = [f"# {label} · 每轮可见答复（输出侧明文；arm={arm}）", ""]
            for x in t["turns"]:
                tl.append(f"## 第 {x['turn']} 轮（user: {x['text']!r}）")
                tl.append("")
                tl.append("```text")
                tl.append((x.get("reply") or "").strip() or "(空)")
                tl.append("```")
                tl.append("")
            io.open(os.path.join(OUT, f"{arm}__turn-replies.md"), "w", encoding="utf-8").write("\n".join(tl) + "\n")

    # 汇总
    s = ["# R491 付费调用汇总（同 AOT sha 8b4efbb7…、同夹具 p12、同窗）", "", "| 臂 | 付费调用 | prompt | completion | total | ¥ |", "|---|---|---|---|---|---|"]
    base = index[0][4] + index[0][3]
    for label, arm, n, p_, c_, cost, _ in index:
        s.append(f"| {label} | {n} | {p_} | {c_} | **{p_+c_}** | {cost} |")
    b = index[0][4] + index[0][3]
    for label, arm, n, p_, c_, cost, _ in index[1:]:
        s.append(f"\n- {label} vs B: token **{100.0*(1-(p_+c_)/b):+.2f}%**，调用 **{100.0*(1-n/index[0][2]):+.2f}%**")
    io.open(os.path.join(OUT, "SUMMARY.md"), "w", encoding="utf-8").write("\n".join(s) + "\n")
    for r in index:
        print("%-14s calls=%d prompt=%d completion=%d cost=%.6f -> %s" % (r[0], r[2], r[3], r[4], r[5], os.path.relpath(r[6], HERE)))
    print("[out]", os.path.relpath(OUT, os.path.dirname(HERE)))


if __name__ == "__main__":
    main()
