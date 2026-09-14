#!/usr/bin/env python3
"""R432 通道分离分析 (post-hoc): 把桩侧调用按提示签名分成
   通道 G (生成/回答: system 含「你是一个智能助手」) 与
   通道 J (关系判官: system == 「只输出一个字母。」)。
目的: 预注册判据 C3 的「Pass ⇔ 窗内远端调用」被证伪 ⇒ 用通道分离核对「Skip 到底省掉了哪条通道」。
"""
import json, pathlib, sys

D = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r432")
ARMS = [("dp1", "C-r432dp-r432dp1"), ("dp2", "C-r432dp2-r432dp2")]


def sig(msgs):
    sysmsg = next((m.get("content") or "" for m in msgs if m.get("role") == "system"), "")
    if sysmsg.strip() == "\u53ea\u8f93\u51fa\u4e00\u4e2a\u5b57\u6bcd\u3002":
        return "J"
    if "\u4f60\u662f\u4e00\u4e2a\u667a\u80fd\u52a9\u624b" in sysmsg:
        return "G"
    return "?"


def run(tag, name):
    calls = [json.loads(l) for l in (D / f"calls-{name}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for c in calls:
        c["chan"] = sig(c["messages"])
    T = json.loads((D / f"turns-{name}.jsonl").read_text(encoding="utf-8"))["turns"]
    V = json.loads((D / f"verdict-{name}.json").read_text(encoding="utf-8"))
    fam = {s["pos"]: s["family"] for s in V["sequence"]}
    dec = {s["pos"]: s["decision"] for s in V["sequence"]}
    rows = []
    for t in T:
        win = [c for c in calls if float(t["t_start"]) <= c["ts"] <= float(t["t_end"])]
        rows.append({
            "turn": int(t["turn"]),
            "family": fam.get(int(t["turn"]), "-"),
            "decision": dec.get(int(t["turn"]), "ungated"),
            "secs": t["secs"],
            "G": sum(1 for c in win if c["chan"] == "G"),
            "J": sum(1 for c in win if c["chan"] == "J"),
            "other": sum(1 for c in win if c["chan"] == "?"),
            "G_tokens": sum(c.get("prompt_tokens_est", 0) or 0 for c in win if c["chan"] == "G"),
            "J_tokens": sum(c.get("prompt_tokens_est", 0) or 0 for c in win if c["chan"] == "J"),
        })
    out = {
        "arm": tag, "calls_total": len(calls),
        "channels": {ch: sum(1 for c in calls if c["chan"] == ch) for ch in ("G", "J", "?")},
        "tokens": {ch: sum((c.get("prompt_tokens_est") or 0) + (c.get("completion_tokens_est") or 0)
                           for c in calls if c["chan"] == ch) for ch in ("G", "J", "?")},
        "per_turn": rows,
        "checks": {
            "gate_Pass_iff_G_in_window": all(r["G"] >= 1 for r in rows if r["decision"] == "Pass")
                                          and all(r["G"] == 0 for r in rows if r["decision"] == "Skip"),
            "skip_turns_with_J": sum(1 for r in rows if r["decision"] == "Skip" and r["J"] >= 1),
            "skip_turns_total": sum(1 for r in rows if r["decision"] == "Skip"),
            "pass_turns": sum(1 for r in rows if r["decision"] == "Pass"),
        },
    }
    (D / f"channels-{name}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"=== {tag} ({name}) ===")
    print(f"  桩调用总数 {out['calls_total']} | 通道 G(生成) {out['channels']['G']} / J(关系判官) {out['channels']['J']} / ? {out['channels']['?']}")
    print(f"  token: G {out['tokens']['G']} / J {out['tokens']['J']} / ? {out['tokens']['?']}")
    print(f"  Pass⇔G窗内: {out['checks']['gate_Pass_iff_G_in_window']} | Skip 轮数 {out['checks']['skip_turns_total']}，其中带 J 调用 {out['checks']['skip_turns_with_J']}")
    for r in rows:
        print(f"    t{r['turn']:>2} {r['family']:<20} {r['decision']:<8} secs={r['secs']:>6} G={r['G']} J={r['J']} (Gtok {r['G_tokens']}, Jtok {r['J_tokens']})")
    return out


if __name__ == "__main__":
    for tag, name in ARMS:
        if (D / f"verdict-{name}.json").exists():
            run(tag, name)
