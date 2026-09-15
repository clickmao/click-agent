#!/usr/bin/env python3
"""R455 套件判分器 —— 只读落盘证据（不重跑、不猜）：
  ① 产物正确性（机械）：count.txt / merged.txt / stats.txt / first.txt
  ② 逐调用 token+cache（我方 adapter 落盘的 side-agent-*；codex 侧 side-codex-*）
  ③ 逐轮归因：我方按 agent-turns.jsonl 顺序；codex 按 codex-t*.jsonl 里 turn.completed 顺序
  ④ 模块表：缓存/闸门/吸收/执行/多步
用法: judge_suite.py [--ns r455] -> eval/rover/r455/verdict-suite.json
"""
import glob
import json
import os
import sys

ENV = os.environ.get("R455_ENV", "/tmp/r455_env")
LOGS = os.path.join(ENV, "logs")
ADA = os.path.join(LOGS, "adapter")
EXPECT = {"count.txt": "4", "merged.txt": "ALPHA\nBETA\nGAMMA\n", "stats.txt": "chars=14"}


def norm(s):
    return (s or "").replace("\r\n", "\n").strip("\n")


def artifacts(side):
    d = os.path.join(ENV, side, "work")
    out = {}
    for name, exp in EXPECT.items():
        p = os.path.join(d, name)
        got = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
        out[name] = {"exists": got is not None, "value": (got or "").strip()[:60], "expected": exp,
                     "ok": got is not None and norm(got) == norm(exp)}
    p = os.path.join(d, "first.txt")
    got = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    out["first.txt"] = {"exists": got is not None, "value": (got or "").strip()[:60], "expected": "含 'R455 fixture note'",
                        "ok": got is not None and "R455 fixture note" in got}
    return out


def calls(side):
    rows = []
    for p in sorted(glob.glob(os.path.join(ADA, f"side-{side}-*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        u = (d.get("response") or {}).get("usage") or {}
        req = d.get("request") or {}
        rows.append({"file": os.path.basename(p),
                     "in": u.get("prompt_tokens"), "cached": u.get("prompt_cache_hit_tokens") or u.get("prompt_tokens_details", {}).get("cached_tokens"),
                     "out": u.get("completion_tokens"), "total": u.get("total_tokens"),
                     "n_messages": req.get("n_messages") or req.get("input_items"),
                     "tools_n": req.get("passed_tools_n") if side == "codex" else req.get("tools_n"),
                     "tool_calls": [t["name"] for t in ((d.get("response") or {}).get("tool_calls") or [])]})
    return rows


def agent_turns():
    p = os.path.join(LOGS, "agent-turns.jsonl")
    if not os.path.exists(p):
        return []
    d = json.load(open(p, encoding="utf-8"))
    out = []
    for i, r in enumerate(d.get("turns") or []):
        rep = r.get("reply") or ""
        out.append({"turn": i + 1, "reply_len": len(rep), "reply": rep,
                    "ask_like": any(k in rep for k in ("请回复", "等你回答", "你自己", "需要确认", "指哪个", "就用默认")),
                    "toolcalls_as_text": ("<tool_calls>" in rep) or ("invoke name=" in rep),
                    "ms": r.get("ms") or r.get("elapsed_ms")})
    return out


def codex_turns():
    out = []
    for p in sorted(glob.glob(os.path.join(LOGS, "codex-t*.jsonl")), key=lambda x: int(x.split("-t")[1].split(".")[0])):
        t = int(p.split("-t")[1].split(".")[0])
        ev = []
        for l in open(p, encoding="utf-8"):
            try:
                ev.append(json.loads(l))
            except Exception:
                pass
        cmds, msg, usage, errs = [], None, None, []
        for e in ev:
            it = e.get("item") or {}
            ty = e.get("type")
            if ty == "item.completed" and (it.get("type") == "command_execution"):
                cmds.append({"cmd": it.get("command"), "rc": it.get("exit_code"), "out": str(it.get("aggregated_output"))[:80]})
            elif ty == "item.completed" and it.get("type") == "agent_message":
                msg = it.get("text")
            elif ty == "turn.completed":
                usage = e.get("usage")
            elif ty == "error":
                errs.append(str(e.get("message"))[:100])
        out.append({"turn": t, "cmds": len(cmds), "cmd_detail": cmds, "msg": msg, "usage": usage, "errors": errs})
    return out


def gate_events():
    """我方门相关证据：落盘 dump(若开) + 宿主遥测里的 basis 计数"""
    dumps = glob.glob(os.path.join(LOGS, "gate-dump*.jsonl"))
    ev = 0
    for p in dumps:
        ev += sum(1 for l in open(p, encoding="utf-8") if l.strip())
    telem = {}
    for p in glob.glob(os.path.join(ENV, "agent", "work", "data", "*.jsonl")):
        n = 0
        for l in open(p, encoding="utf-8", errors="replace"):
            if '"gate' in l or '"basis"' in l:
                n += 1
        if n:
            telem[os.path.basename(p)] = n
    return {"gate_dump_files": len(dumps), "gate_prompt_lines": ev, "telemetry_gate_hits": telem}


def main():
    ns = "r455"
    if "--ns" in sys.argv:
        ns = sys.argv[sys.argv.index("--ns") + 1]
    res = {"ns": ns, "env": ENV,
           "artifacts": {s: artifacts(s) for s in ("codex", "agent")},
           "calls": {s: calls(s) for s in ("codex", "agent")},
           "agent_turns": agent_turns(), "codex_turns": codex_turns(), "gate": gate_events()}
    for s in ("codex", "agent"):
        ok = sum(1 for v in res["artifacts"][s].values() if v["ok"])
        res[f"{s}_artifacts_ok"] = f"{ok}/4"
        cs = res["calls"][s]
        res[f"{s}_totals"] = {"calls": len(cs),
                              "in": sum(c["in"] or 0 for c in cs), "cached": sum(c["cached"] or 0 for c in cs),
                              "out": sum(c["out"] or 0 for c in cs)}
        res[f"{s}_cache_hit_pct"] = round(100.0 * sum(c["cached"] or 0 for c in cs) / max(1, sum(c["in"] or 0 for c in cs)), 1)
    o = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"verdict-{ns}.json")
    json.dump(res, open(o, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("modules:")
    print("  M4 执行: codex", res["codex_artifacts_ok"], "| agent", res["agent_artifacts_ok"])
    print("  M1 缓存: codex", res["codex_cache_hit_pct"], "% | agent", res["agent_cache_hit_pct"], "%")
    print("  M6 token: codex", res["codex_totals"], "| agent", res["agent_totals"])
    print("  M2 闸门:", res["gate"])
    print("  M3 吸收: agent ask_like=", sum(1 for t in res["agent_turns"] if t["ask_like"]), "伪工具调用=", sum(1 for t in res["agent_turns"] if t["toolcalls_as_text"]))
    print("verdict ->", o)


if __name__ == "__main__":
    main()
