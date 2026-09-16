#!/usr/bin/env python3
# R494 读数器 —— 从**真实臂产物**派生 KPI (禁手抄数字)。
# 输入: eval/rover/r496/{calls,usage,tel-*}-<arm>.jsonl + flags-<arm>.json
# 输出: eval/rover/r496/kpi-r496.json (逐臂明细 + 阶梯差 + 验收口径读数)
#
# 口径 (与 R493 逐字同):
#   calls            = 中继请求条数 (真远端调用次数; 每请求一条)
#   total_tokens     = Σ usage.total_tokens (嵌套在 usage 下; 顶层没有该键 —— R493 踩过)
#   cached_tokens    = Σ usage.prompt_tokens_details.cached_tokens
#   tools_n          = sampling.tools_n (实发面工具条数)
#   隔离通道调用      = messages 含 [微步骤隔离问询] 或 system 为隔离声明
#   空正文调用        = 响应侧空正文 (usage 有而正文空) —— 由 calls 的 tail 标记派生, 见 R493 归因
import argparse, json, os, sys

def jl(p):
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig") as f:
        return [json.loads(l) for l in f if l.strip()]

ISO_MARK = "微步骤隔离问询"
ISO_SYS = ("你是隔离执行的微步骤助手", "你是一个一次性隔离子任务执行器")

def iso_of(row):
    for m in (row.get("messages") or []):
        c = m.get("content")
        if isinstance(c, str):
            if ISO_MARK in c:
                return True
            if m.get("role") == "system" and any(s in c for s in ISO_SYS):
                return True
    return False

TAG = os.environ.get("R496_TAG", "r496")


def rp(d, name):
    """带 tag 的产物解析: 先试原名, 再试 <名>-<TAG> 与 <名><TAG> (R496 臂以 tag=r496 跑, 无分隔符)。"""
    base = name[:-6] if name.endswith(".jsonl") else name
    for cand in (name, "%s-%s.jsonl" % (base, TAG), "%s%s.jsonl" % (base, TAG)):
        p = os.path.join(d, cand)
        if os.path.exists(p):
            return p
    return None


def arm_stats(d, arm):
    pc, pu = rp(d, "calls-%s.jsonl" % arm), rp(d, "usage-%s.jsonl" % arm)
    calls = jl(pc) if pc else None
    usage = jl(pu) if pu else None
    if calls is None or usage is None:
        return None
    tot = sum(((r.get("usage") or {}).get("total_tokens") or 0) for r in usage)
    pt = sum(((r.get("usage") or {}).get("prompt_tokens") or 0) for r in usage)
    ct = sum(((r.get("usage") or {}).get("completion_tokens") or 0) for r in usage)
    cached = sum((((r.get("usage") or {}).get("prompt_tokens_details") or {}).get("cached_tokens") or 0) for r in usage)
    blocked = sum(1 for r in usage if r.get("blocked") is True)
    iso = [r for r in calls if iso_of(r)]
    iso_tools = [r for r in iso if int(((r.get("sampling") or {}).get("tools_n") or 0)) > 0]
    tools_calls = [r for r in calls if int(((r.get("sampling") or {}).get("tools_n") or 0)) > 0]
    return {
        "arm": arm, "calls": len(calls), "usage_rows": len(usage),
        "total_tokens": tot, "prompt_tokens": pt, "completion_tokens": ct, "cached_tokens": cached,
        "blocked_rows": blocked,
        "tok_per_call": round(tot / max(1, len(calls)), 1),
        "new_tokens_per_call": round((pt - cached) / max(1, len(calls)), 1),
        "iso_calls": len(iso), "iso_calls_with_tools": len(iso_tools), "iso_tok": None,
        "calls_with_tools": len(tools_calls),
        "iso_seqs": [r.get("seq") for r in iso][:12],
        "tools_seqs": [r.get("seq") for r in tools_calls][:12],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/home/agentuser/AgentFramework/eval/rover/r496")
    ap.add_argument("--baseline", default="/home/agentuser/AgentFramework/eval/rover/r496/baseline-r493-kpi.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = a.dir
    arms = [x for x in ("B", "T0", "T1") if rp(d, "calls-%s.jsonl" % x)]
    if not arms:
        print("[kpi] 无臂产物 ⇒ 拒出读数"); return 14
    st = {}
    for x in arms:
        s = arm_stats(d, x)
        if s is None:
            print("[kpi] %s 产物不全" % x); return 14
        f = os.path.join(d, "flags-%s.json" % x)
        s["flags"] = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
        st[x] = s
    rep = {"schema": "r496-kpi/1", "arms": st, "ladder": [], "baseline_r493": None, "acceptance": {}}
    if os.path.exists(a.baseline):
        rep["baseline_r493"] = json.load(open(a.baseline, encoding="utf-8"))
    def delta(x, y):
        if x not in st or y not in st:
            return None
        fx, fy = st[x], st[y]
        return {
            "pair": "%s→%s" % (x, y),
            "calls": [fx["calls"], fy["calls"]],
            "calls_drop_pct": round(100.0 * (fx["calls"] - fy["calls"]) / max(1, fx["calls"]), 2),
            "total_tokens": [fx["total_tokens"], fy["total_tokens"]],
            "total_tokens_drop_pct": round(100.0 * (fx["total_tokens"] - fy["total_tokens"]) / max(1, fx["total_tokens"]), 2),
            "iso_calls": [fx["iso_calls"], fy["iso_calls"]],
            "iso_calls_with_tools": [fx["iso_calls_with_tools"], fy["iso_calls_with_tools"]],
        }
    rep["ladder"] = [x for x in (delta("B", "T0"), delta("T0", "T1"), delta("B", "T1")) if x]
    b, t1 = st.get("B"), st.get("T1")
    if b and t1:
        rep["acceptance"] = {
            "same_window_denominator": "B (本轮同窗同网格/同上游/同产物)",
            "calls_before": b["calls"], "calls_after": t1["calls"],
            "tokens_before": b["total_tokens"], "tokens_after": t1["total_tokens"],
            "tokens_drop_pct": round(100.0 * (b["total_tokens"] - t1["total_tokens"]) / max(1, b["total_tokens"]), 2),
            "target_pct": 30.0,
            "met": (b["total_tokens"] - t1["total_tokens"]) / max(1, b["total_tokens"]) >= 0.30,
        }
    else:
        rep["acceptance"] = {"note": "B 或 T1 缺失 ⇒ 验收口径未构成 (禁跨轮相减)"}
    out = a.out or os.path.join(d, "kpi-r496.json")
    json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for x in arms:
        s = st[x]
        print("[kpi] %-3s calls=%-3d tokens=%-7d cached=%-7d iso=%-2d iso带工具=%-2d 带工具调用=%-3d" %
              (x, s["calls"], s["total_tokens"], s["cached_tokens"], s["iso_calls"], s["iso_calls_with_tools"], s["calls_with_tools"]))
    for l in rep["ladder"]:
        print("[阶梯] %-8s calls %s (%+.1f%%) tokens %s (%+.1f%%) 隔离带工具 %s→%s" %
              (l["pair"], l["calls"], l["calls_drop_pct"], l["total_tokens"], l["total_tokens_drop_pct"],
               l["iso_calls_with_tools"][0], l["iso_calls_with_tools"][1]))
    if rep["acceptance"].get("met") is not None:
        ac = rep["acceptance"]
        print("[验收] 同窗 B→T1 tokens %d→%d = %+.2f%% (目标 ≤-30%%) ⇒ %s" %
              (ac["tokens_before"], ac["tokens_after"], -float(ac["tokens_drop_pct"]), "达标" if ac["met"] else "未达标"))
    print("[kpi] → " + out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
