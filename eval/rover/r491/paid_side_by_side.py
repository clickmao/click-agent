#!/usr/bin/env python3
"""R491 付费调用**逐调用对照**：B(门关) vs T1(声明门开)，同夹具同窗。
  机取: 首调用输入是否**逐字相同**(除工具声明面) + 空正文工具轮清单 + 逐调用输出度量。
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "paid-plaintext")


def jl(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8-sig") if l.strip()] if os.path.exists(p) else []


def msgs_of(c):
    return c["messages"] if isinstance(c["messages"], list) else json.loads(c["messages"])


def main():
    b, t = jl(f"{HERE}/calls-Aroleb.jsonl"), jl(f"{HERE}/calls-T1.jsonl")
    bu, tu = jl(f"{HERE}/usage-Aroleb.jsonl"), jl(f"{HERE}/usage-T1.jsonl")
    L = ["# R491 逐调用对照（B=工具声明门**关** vs T1=门**开**）", ""]

    # 1) 首调用输入逐字比较
    m0b, m0t = msgs_of(b[0]), msgs_of(t[0])
    same = m0b == m0t
    L += ["## 1 · 首调用输入是否逐字相同（除工具声明）", ""]
    L.append(f"- B 首调用 messages = {len(m0b)} 条, T1 首调用 = {len(m0t)} 条；**messages 逐字相同 = {same}**")
    if m0b and m0t:
        L.append(f"- 字符长度逐条: B={[len(str(m.get('content')) ) for m in m0b]} vs T1={[len(str(m.get('content'))) for m in m0t]}")
    L.append(f"- 工具声明数 `tools_n`: B=**{b[0]['sampling'].get('tools_n')}** vs T1=**{t[0]['sampling'].get('tools_n')}**")
    L.append(f"- 供应商真值 prompt_tokens: B=**{bu[0].get('prompt_tokens')}** vs T1=**{tu[0].get('prompt_tokens')}** "
             f"⇒ 差 **{bu[0].get('prompt_tokens')-tu[0].get('prompt_tokens')} tok**（同输入 ⇒ 该差即工具声明面成本）")
    L.append("")

    # 2) 逐调用
    for name, calls, usage in (("B(门关)", b, bu), ("T1(门开)", t, tu)):
        L += [f"## 2 · {name} 逐调用输入/输出度量", "",
              "| # | messages | tools_n | prompt | completion | finish_reason | 正文长 | 思考长 | 空正文 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for k, c in enumerate(calls):
            u = usage[k] if k < len(usage) else {}
            L.append(f"| {k+1} | {c['n_messages']} | {c['sampling'].get('tools_n')} | {u.get('prompt_tokens')} | "
                     f"{u.get('completion_tokens')} | `{u.get('finish_reason')}` | {u.get('content_len')} | "
                     f"{u.get('reasoning_len')} | {u.get('empty_body')} |")
        empt = [k + 1 for k, u in enumerate(usage) if u.get("empty_body")]
        L += ["", f"- **空正文调用**（模型只回 `tool_calls`、正文 0 字符，但仍按全量 prompt 计费）= {empt or '无'}", ""]

    # 3) 结论
    tp = sum(u.get("prompt_tokens") or 0 for u in bu) + sum(u.get("completion_tokens") or 0 for u in bu)
    tt = sum(u.get("prompt_tokens") or 0 for u in tu) + sum(u.get("completion_tokens") or 0 for u in tu)
    L += ["## 3 · 结论", "",
          f"- B = {len(b)} 次付费调用 / **{tp} tok** / ¥{round(sum(u.get('cost_cny_upper') or 0 for u in bu),6)}",
          f"- T1 = {len(t)} 次付费调用 / **{tt} tok** / ¥{round(sum(u.get('cost_cny_upper') or 0 for u in tu),6)}",
          f"- 降幅 = **{100.0*(1-tt/tp):.2f}%**（token） / **{100.0*(1-len(t)/len(b)):.2f}%**（调用）",
          "",
          "机制（逐条可核）: 门关时每次请求都下发 4 个工具声明；上游据此回 `tool_calls`（正文空）⇒ 该轮作废且**再灌一次全量 prompt**；"
          "门开后 0 工具声明 ⇒ `finish_reason` 全 `stop`、空正文轮 0 ⇒ 付费调用 17→6。"]
    io.open(os.path.join(OUT, "side-by-side.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # 修 SUMMARY 符号（降幅口径）
    s = ["# R491 付费调用汇总（同 AOT sha 8b4efbb7…、同夹具 p12、同窗）", "",
         "| 臂 | 付费调用 | prompt | completion | total | ¥ | vs B(降幅) |", "|---|---|---|---|---|---|---|"]
    rows = [("B(B 门关)", "Aroleb"), ("T1(声明门开)", "T1"), ("T2", "T2"), ("T3", "T3")]
    agg = {}
    for label, arm in rows:
        c, u = jl(f"{HERE}/calls-{arm}.jsonl"), jl(f"{HERE}/usage-{arm}.jsonl")
        p_ = sum(x.get("prompt_tokens") or 0 for x in u)
        c_ = sum(x.get("completion_tokens") or 0 for x in u)
        agg[label] = (len(c), p_, c_, round(sum(x.get("cost_cny_upper") or 0 for x in u), 6))
    bn, bp, bc, bcost = agg["B(B 门关)"]
    btot = bp + bc
    for label, _ in rows:
        n, p_, c_, cost = agg[label]
        d = "分母" if label.startswith("B(") else f"**−{100.0*(1-(p_+c_)/btot):.2f}% token / −{100.0*(1-n/bn):.2f}% 调用**"
        s.append(f"| {label} | {n} | {p_} | {c_} | **{p_+c_}** | {cost} | {d} |")
    io.open(os.path.join(OUT, "SUMMARY.md"), "w", encoding="utf-8").write("\n".join(s) + "\n")
    print("\n".join(s))


if __name__ == "__main__":
    main()
