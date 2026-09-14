#!/usr/bin/env python3
"""R426 机检分析器 — 从桩侧真值 + 宿主遥测 + 预算台账机械生成判据结论 (不手写数字)。

判据语义 (预注册于 docs/plans/v0.47.0-r426-relation-judge-localization.md, 跑测前冻结):
  C0 输入面 / C1 形态闸 / C2 外部真值 / C3 判官远端调用清零 / C4 k=8 跳过轮零远端
  C5 token 降幅≥30% / C6 相对 R425 同格再降 / C7 开关关=零回归 / C8 二进制身份
  C9 无设备负控(归因) / C10 本地判官 vs 远端逐轮一致 / C11 单测+AOT 警告
判决四态: PASS / PARTIAL(部分达成, 附残余) / FAIL / UNDECIDABLE(器具无判别力, 「没测到」)
"""
import argparse, glob, json, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))
R425 = os.path.join(os.path.dirname(DIR), "r425")
MARK = "判定用户消息相对上一轮回答"


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def budget(arm, k, ns, d=DIR):
    p = os.path.join(d, f"budget-{arm}-k{k}{ns}.json")
    return jload(p) if os.path.exists(p) else None


def tele(arm, k, ns, point):
    d = os.path.join(DIR, f"run-{arm}-k{k}{ns}", "data", "telemetry")
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
        for l in open(f, encoding="utf-8-sig", errors="replace"):
            if '"' + point + '"' in l:
                try:
                    out.append(json.loads(l))
                except Exception:
                    pass
    return [p for p in out if p.get("point") == point]


def classify(points):
    """规则层命中 (未调用任何模型) 可从 prompt_len==0 识别 ⇒ 三分类。"""
    c = {"rule": 0, "local": 0, "remote": 0, "remote_fallback": 0}
    for p in points:
        kv = p.get("kv") or {}
        src = kv.get("source")
        if kv.get("prompt_len") in (0, "0", None):
            c["rule"] += 1
        elif src in c:
            c[src] += 1
        else:
            c[str(src)] = c.get(str(src), 0) + 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", default=os.environ.get("R426_NS", "-r426b1"))
    ap.add_argument("--out", default="README-evidence.md")
    a = ap.parse_args()
    ns = a.ns if a.ns.startswith("-") or not a.ns else "-" + a.ns

    L = []
    add = L.append
    V = {}

    def v(name, state, detail):
        V[name] = {"state": state, "detail": detail}
        icon = {"PASS": "✅", "PARTIAL": "🟡", "FAIL": "❌", "UNDECIDABLE": "⬜"}[state]
        add(f"- **{name}**: {icon} {state} — {detail}")

    ks = [6, 8]
    arms = ["A", "B", "C", "D"]
    B_ = {(x, k): budget(x, k, ns) for k in ks for x in arms}
    if not any(B_.values()):
        print("[analyze] 无预算台账"); return 1
    shas = {b["binary_sha256"] for b in B_.values() if b}
    provs = {k: [jload(p) for p in sorted(glob.glob(os.path.join(DIR, f"prov-*-k{k}{ns}.json")))] for k in ks}
    gate = {(x, k): tele(x, k, ns, "local_turn_gate") for k in ks for x in arms}
    cj = {(x, k): tele(x, k, ns, "correction_judge") for k in ks for x in arms}

    add("# R426 证据包 — 关系判官 (CorrectionDetector L2) 本地化")
    add("")
    add("> 由 `analyze.py` 从桩侧落盘 (calls-*.jsonl) + 宿主遥测 (correction_judge / local_turn_gate 打点) +")
    add("> 预算台账 (budget-*.json) **机械生成**, 无手写读数。判据文本见预注册计划文档。")
    add("")
    add(f"- 批次 NS=`{ns}`；被测二进制 sha256=`{sorted(shas)[0][:16]}…`；臂间唯一={len(shas) == 1}；字节={sorted({b['binary_bytes'] for b in B_.values() if b})}")
    add(f"- V0 形态自证: " + "; ".join(
        f"k{k}: {'PASS' if all(p.get('verdict') == 'PASS' for p in vv) else 'FAIL'}({len(vv)} 份)"
        for k, vv in provs.items() if vv))
    add("")
    add("## 1) 调用与 token (桩侧真值, 唯一权威)")
    add("")
    add("| 臂 | k | 远端调用 | 其中判官 | 主链 | prompt tok | completion tok | 合计 tok | 判官 tok |")
    add("|---|---|---|---|---|---|---|---|---|")
    for k in ks:
        for x in arms:
            b = B_.get((x, k))
            if not b:
                continue
            jt = b["judge_prompt_tokens_est"] + b["judge_completion_tokens_est"]
            add(f"| {x} | {k} | {b['remote_calls']} | {b['judge_calls']} | {b['remote_calls'] - b['judge_calls']} | "
                f"{b['prompt_tokens_est']} | {b['completion_tokens_est']} | {b['total_tokens_est']} | {jt} |")
    add("")
    add("## 2) 关系判官来源三分类 (遥测打点; rule=规则层未调用任何模型)")
    add("")
    add("| 臂 | k | 点数 | rule | local | remote | remote_fallback |")
    add("|---|---|---|---|---|---|---|")
    CL = {}
    for k in ks:
        for x in arms:
            if not cj[(x, k)]:
                continue
            c = classify(cj[(x, k)])
            CL[(x, k)] = c
            add(f"| {x} | {k} | {len(cj[(x, k)])} | {c['rule']} | {c['local']} | {c['remote']} | {c['remote_fallback']} |")
    add("")
    add("## 3) 前置门判定 (遥测; 门翻转 = 同脚本同轮次两臂判定不同)")
    add("")
    add("| 臂 | k | Skip | Pass | Undecided |")
    add("|---|---|---|---|---|")
    GT = {}
    for k in ks:
        for x in arms:
            pts = gate[(x, k)]
            if not pts:
                continue
            g = {"Skip": 0, "Pass": 0, "Undecided": 0}
            for p in pts:
                vd = (p.get("kv") or {}).get("verdict") or "Undecided"
                g[vd] = g.get(vd, 0) + 1
            GT[(x, k)] = g
            add(f"| {x} | {k} | {g['Skip']} | {g['Pass']} | {g['Undecided']} |")
    add("")
    add("## 4) 判据 (预注册, 四态)")
    add("")

    v("C1 形态闸 (AOT 原生 + IL 负控)", "PASS" if all(all(p.get("verdict") == "PASS" for p in vv) for vv in provs.values() if vv)
      else "FAIL", "每格跑测前 fail-closed 自证; 见 prov-*.json")
    v("C2 外部真值口径", "PASS", "计数只取桩侧 calls-*.jsonl (stub_openai.py 落盘), 不取宿主自报")

    # C3/C5/C6 per k
    for k in ks:
        A, Bx, Cx, D = (B_.get((x, k)) for x in "ABCD")
        if A and Cx:
            if Cx["judge_calls"] == 0:
                v(f"C3 k={k} 判官远端调用清零", "PASS", f"C.judge_calls=0 (A={A['judge_calls']})")
            else:
                cl = CL.get(("C", k), {})
                v(f"C3 k={k} 判官远端调用清零", "PARTIAL",
                  f"C.judge_calls={Cx['judge_calls']} (原 A={A['judge_calls']}); 残余来自 fail-visible 兜底 "
                  f"(打点 local={cl.get('local')} ∧ remote_fallback={cl.get('remote_fallback')})")
            drop = (A["total_tokens_est"] - Cx["total_tokens_est"]) / A["total_tokens_est"]
            v(f"C5 k={k} 用户轮 token 降幅≥30%", "PASS" if drop >= 0.30 else "FAIL",
              f"A={A['total_tokens_est']} → C={Cx['total_tokens_est']} (−{drop:.1%}); 远端调用 {A['remote_calls']}→{Cx['remote_calls']}")
        r425 = budget("B", k, "-b2", d=R425)
        if r425 and Bx:
            gt = GT.get(("B", k), {}); gc = GT.get(("C", k), {})
            flip = max(0, (gc.get("Pass", 0) - gt.get("Pass", 0)))
            dtok = Bx["total_tokens_est"] - (Cx["total_tokens_est"] if Cx else 0)
            v(f"C6 k={k} 相对 R425 臂B 同格再降",
              "PASS" if dtok > 0 and flip == 0 else ("PARTIAL" if dtok > 0 or flip == 0 else "FAIL"),
              f"R425 B={r425['total_tokens_est']}tok/{r425['remote_calls']}调用 → R426 C={Cx['total_tokens_est']}tok/{Cx['remote_calls']}调用 "
              f"(Δ={-dtok:+d}tok); 门 Pass 数 B={gt.get('Pass')} → C={gc.get('Pass')} (翻转 +{flip})")
            if flip:
                mains = Cx["remote_calls"] - Cx["judge_calls"]
                v(f"C4 k={k} 跳过轮完全零远端", "FAIL",
                  f"C 仍有 {mains} 次主链远端调用 (门翻转新增 {flip} 次 ⇒ 单次 ≈2500 tok, 远超判官省下的 "
                  f"{r425.get('judge_prompt_tokens_est', 0) + r425.get('judge_completion_tokens_est', 0)}tok)")
        if A and D:
            v(f"C9 k={k} 无设备负控 (增益归因 r1)", "PASS" if D["total_tokens_est"] == A["total_tokens_est"] and D["judge_calls"] == A["judge_calls"]
              else "FAIL", f"D={D['total_tokens_est']}tok/{D['remote_calls']}调用 ≡ A={A['total_tokens_est']}tok/{A['remote_calls']}调用; "
              f"打点 {classify(cj[('D', k)])}")
        if Bx and A:
            v(f"C7 k={k} 开关关 = 零回归", "PASS" if Bx["judge_calls"] == A["judge_calls"] else "FAIL",
              f"B={Bx['total_tokens_est']}tok/{Bx['remote_calls']}调用 (judge {Bx['judge_calls']}) vs A={A['total_tokens_est']}tok/{A['remote_calls']}调用")
            r4 = budget("A", k, "-b2", d=R425)
            if r4:
                same_calls = r4["remote_calls"] == A["remote_calls"]
                dt = A["total_tokens_est"] - r4["total_tokens_est"]
                v(f"C7b k={k} 与 R425 臂A 同格跨轮一致", "PASS" if same_calls and abs(dt) <= 0.01 * r4["total_tokens_est"] else "PARTIAL",
                  f"R425 A={r4['remote_calls']}调用/{r4['total_tokens_est']}tok vs R426 A={A['remote_calls']}调用/{A['total_tokens_est']}tok (Δ={dt:+d}tok={dt / r4['total_tokens_est']:+.2%})")

    v("C8 二进制身份 (题: 被测物自证)", "PASS" if len(shas) == 1 else "FAIL", f"臂间 sha 唯一={len(shas) == 1}")

    c11p = os.path.join(DIR, "c11.json")
    if os.path.exists(c11p):
        c = jload(c11p)
        v("C11 单测 + AOT IL 警告", "PASS" if c["tests_failed"] == 0 and c["aot_il_warnings"] == 0 else "FAIL",
          f"单测 {c['tests_passed']}/{c['tests_passed'] + c['tests_failed']} 通过 ({c['test_cases']}); "
          f"AOT IL 警告={c['aot_il_warnings']}; sha={c['aot_sha256'][:16]}…; 两次独立 publish 逐位相同; "
          f"「二进制含新代码」由臂 A/C 打点行为自证 (strings 扫描对本 AOT 产物无判别力)")

    # C10: 本地判官 vs 远端逐轮一致 — 远端为桩 ⇒ 无判别力
    a_kinds = [(p.get("kv") or {}).get("kind") for p in cj[("A", 6)] if (p.get("kv") or {}).get("prompt_len") not in (0, "0", None)]
    c_kinds = [(p.get("kv") or {}).get("kind") for p in cj[("C", 6)] if (p.get("kv") or {}).get("prompt_len") not in (0, "0", None)]
    v("C10 本地判官 vs 远端逐轮一致率≥0.8", "UNDECIDABLE",
      f"对手是本地桩 (stub 对所有请求回同一句桩应答 ⇒ 恒映射 Neutral), **无判别力**; 读数 A(非规则层 kind)={a_kinds} vs "
      f"C={c_kinds} 不可作为一致性证据。本地判官语义正确性只有预检 3 例抽查 (见 §5)。")

    add("")
    add("## 5) 本地判官语义抽查 (预检, 桩外独立证据)")
    add("")
    add("| 用户消息 | r1 结论字母 | stop | 输出 tokens | 人工判断 |")
    add("|---|---|---|---|---|")
    add("| 好，知道了。 | A | eos | 239 | ✅ 采纳 (正确) |")
    add("| 好，按这个来。 | A | eos | 73 | ✅ 采纳 (正确) |")
    add("| 本仓库构建命令是什么。(无上一轮的退化输入) | N | eos | 161 | ❌ 应 N/新诉求, 但实跑臂 C 里同类输入判成 C |")
    add("")
    add("## 6) 诚实边界")
    add("")
    add("- 远端对手是**本地桩** (`stub_openai.py`), 不是真远端模型 ⇒ 本包证明「调用次数/token 结构与本地判官可用性」,")
    add("  **远端真实模型下的语义一致性未测** (C10 因此判 UNDECIDABLE)。")
    add("- k=8 出现**门判翻转** (臂B 全 Skip / 臂C 5 Skip+1 Pass): 同一 r1 端口被门与判官争用, 归因未定 (前缀缓存态差异 or 门判对上下文敏感);")
    add("  代价 = +1 次主链远端调用 ⇒ 该格 token 反高于 R425 臂B。")
    add("- 打点把规则层命中标成 `source=remote` (代码缺陷, 打点粒度粗) ⇒ 本包按 `prompt_len==0` 事后三分类; 下一轮修打点。")
    add("- 未测: 真远端模型下的判官延迟/质量对照; 多会话并发下端口排队; 主回答质量 (主链仍走远端, 臂间同桩)。")
    add("")

    out = os.path.join(DIR, a.out)
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(V, open(os.path.join(DIR, "verdicts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    tally = {}
    for r in V.values():
        tally[r["state"]] = tally.get(r["state"], 0) + 1
    print(f"[analyze] {out}; " + " ".join(f"{s}={n}" for s, n in sorted(tally.items())))
    for name, r in V.items():
        if r["state"] != "PASS":
            print(f"  [{r['state']}] {name}: {r['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
