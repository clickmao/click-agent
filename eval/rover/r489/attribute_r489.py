#!/usr/bin/env python3
"""R489 方差归因 (post-hoc, 预注册外): 调用数差异由**谁**贡献 —— 本地闸决策 vs 上游行为。

输入 (全部机取, 零手抄):
  eval/rover/r489/usage-<key>.jsonl      ← 中继真供应商 usage (每调用一行)
  eval/rover/r489/tel-<key>/host.jsonl   ← 宿主遥测 (local_turn_gate / llm_call_empty_body / micro_session)

输出: eval/rover/r489/attribution-r489.json
"""
import io, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = [("B", "Aroleb"), ("R1", "R1"), ("R2", "R2"), ("R3", "R3")]


def read_jsonl(p):
    return [json.loads(l) for l in io.open(p, encoding="utf-8-sig") if l.strip()]


def main():
    out = {"round": "R489", "kind": "post-hoc 方差归因", "arms": {}}
    for arm, key in ARMS:
        up, tp = f"{HERE}/usage-{key}.jsonl", f"{HERE}/tel-{key}/host.jsonl"
        if not os.path.exists(up) or not os.path.exists(tp):
            sys.exit("缺输入 (fail-closed): %s" % (up if not os.path.exists(up) else tp))
        u = read_jsonl(up)
        tel = read_jsonl(tp)
        gates = [r["kv"] for r in tel if r.get("point") == "local_turn_gate"]
        empty = [r["kv"] for r in tel if r.get("point") == "llm_call_empty_body"]
        micro = [r["kv"] for r in tel if r.get("point") == "micro_session"]
        d = {
            "usage_rows": len(u),
            "usage_by_finish_reason": dict(Counter(str(r.get("finish_reason")) for r in u)),
            "usage_by_route": dict(Counter(str(r.get("routed_to")) for r in u)),
            "usage_empty_body": sum(1 for r in u if r.get("empty_body")),
            "usage_empty_mode": dict(Counter(("empty" if r.get("empty_body") else "nonempty") + "/" +
                                             str(r.get("finish_reason")) for r in u)),
            "usage_tokens_empty": sum((r.get("prompt_tokens") or 0) + (r.get("completion_tokens") or 0)
                                      for r in u if r.get("empty_body")),
            "telemetry_gate_rows": len(gates),
            "telemetry_gate_verdicts": dict(Counter(g.get("verdict") for g in gates)),
            "telemetry_gate_skip_basis": dict(Counter(g.get("basis") for g in gates if g.get("verdict") == "Skip")),
            "telemetry_empty_body_events": len(empty),
            "telemetry_empty_body_cause": dict(Counter(e.get("cause") for e in empty)),
            "telemetry_empty_retry_skipped": dict(Counter(str(e.get("retry_skipped")) for e in empty)),
            "telemetry_micro_sessions": len(micro),
            "telemetry_micro_skipped": sum(int(m.get("skipped") or 0) for m in micro),
            "telemetry_micro_counts": sum(int(m.get("count") or 0) for m in micro),
        }
        # 调用数分解: 远端轮 = gate_rows − skip_rows; 其余调用 = 微步骤/空正文重试/压缩等
        d["remote_turns_expected"] = d["telemetry_gate_rows"] - int(d["telemetry_gate_verdicts"].get("Skip", 0))
        d["calls_vs_remote_turns"] = d["usage_rows"] - d["remote_turns_expected"]
        out["arms"][arm] = d
        d["tokens_nonempty_only"] = sum((r.get("prompt_tokens") or 0) + (r.get("completion_tokens") or 0)
                                        for r in u if not r.get("empty_body"))
        d["calls_nonempty_only"] = sum(1 for r in u if not r.get("empty_body"))
    # post-hoc 分母分解: 剔除「上游空正文调用」后重算降幅 (R489 方差归因结论)
    b = out["arms"]["B"]
    out["excl_empty_body"] = {
        "note": "剔除空正文(带 tool_calls)调用后的同窗降幅 —— 上游行为面, 非臂内噪声",
        "B_tokens": b["tokens_nonempty_only"], "B_calls": b["calls_nonempty_only"],
        "deltas": {k: {"tokens": out["arms"][k]["tokens_nonempty_only"],
                       "calls": out["arms"][k]["calls_nonempty_only"],
                       "降幅_pct": round(100.0 * (1 - out["arms"][k]["tokens_nonempty_only"] / b["tokens_nonempty_only"]), 2),
                       "调用降幅_pct": round(100.0 * (1 - out["arms"][k]["calls_nonempty_only"] / b["calls_nonempty_only"]), 2)}
                   for k in ("R1", "R2", "R3")}}
    io.open(os.path.join(HERE, "attribution-r489.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for arm, d in out["arms"].items():
        print(arm, "calls=%d 远端轮=%d 超出=%+d 空正文=%d(事件%d) 空正文tok=%d 微会话=%d" % (
            d["usage_rows"], d["remote_turns_expected"], d["calls_vs_remote_turns"],
            d["usage_empty_body"], d["telemetry_empty_body_events"], d["usage_tokens_empty"],
            d["telemetry_micro_sessions"]))
        print("    finish_reason:", d["usage_by_finish_reason"], "empty/mode:", d["usage_empty_mode"],
              "retry_skipped:", d["telemetry_empty_retry_skipped"])
    print("[written] eval/rover/r489/attribution-r489.json")


if __name__ == "__main__":
    main()
