#!/usr/bin/env python3
"""R374 真机 A/B 聚合: 逐轮抽取 调用次数/tokens/产物校验/回流修复结论 → 汇总表 + JSON。"""
import json, glob, os, sys

P = "/tmp/gameprobe"
OUT = os.path.join(P, "r374_agg.json")


def load(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    return rows


def summarize(rows):
    llm = [r for r in rows if r.get("point") == "llm_call"]
    arts = [r for r in rows if r.get("point") == "script_artifact"]
    runs = [r for r in rows if r.get("point") == "script_run"]
    fb = [r for r in rows if r.get("point") == "artifact_feedback"]
    cont = [r for r in rows if r.get("point") in ("llm_call_continue", "llm_call_recover")]

    def valid(a):
        kv = a.get("kv", {})
        if not kv.get("compile_valid"):
            return False
        run = next((x for x in runs if x.get("kv", {}).get("path") == kv.get("path")), None)
        if run is None:
            return True  # 未实跑 → 只到编译级
        rk = run.get("kv", {})
        return bool(rk.get("ran")) and rk.get("exit") == 0

    return {
        "calls": len(llm),
        "prompt_tokens": sum(r["kv"].get("prompt_tokens", 0) or 0 for r in llm),
        "completion_tokens": sum(r["kv"].get("completion_tokens", 0) or 0 for r in llm),
        "total_tokens": sum(r["kv"].get("total_tokens", 0) or 0 for r in llm),
        "content_lens": [r["kv"].get("content_len") for r in llm],
        "empty_reply": sum(1 for r in llm if r["kv"].get("empty_reply")),
        "recover_or_continue": len(cont),
        "artifacts": [
            {
                "path": a["kv"].get("path"),
                "compile_valid": a["kv"].get("compile_valid"),
                "exit": a["kv"].get("exit"),
                "origin": a["kv"].get("origin"),
                "valid": valid(a),
                "out_chars": a["kv"].get("out_chars"),
            }
            for a in arts
        ],
        "valid_count": sum(1 for a in arts if valid(a)),
        "artifact_count": len(arts),
        "feedback": [r["kv"] for r in fb],
        "fixed": sum(1 for r in fb if r["kv"].get("fixed")),
    }


res = {}
for arm in ("A", "B"):
    per = []
    for i in (1, 2, 3):
        p = os.path.join(P, f"r374_{arm}_run{i}.telemetry")
        if not os.path.exists(p):
            per.append({"run": i, "missing": True, "file": p})
            continue
        s = summarize(load(p))
        s["run"] = i
        s["elapsed_hint"] = None
        per.append(s)
    res[arm] = per


def line(s):
    return (f"run{s['run']}: calls={s['calls']} tokens={s['total_tokens']} "
            f"artifacts={s['artifact_count']} valid={s['valid_count']} "
            f"fixed={s['fixed']} recover={s['recover_or_continue']} "
            f"fb={json.dumps(s['feedback'], ensure_ascii=False)}")


for arm in ("A", "B"):
    label = "A(回流关)" if arm == "A" else "B(回流开)"
    print(f"=== 臂 {label} ===")
    for s in res[arm]:
        if s.get("missing"):
            print(f"  run{s['run']}: MISSING ({s['file']})")
        else:
            print("  " + line(s))
            for a in s["artifacts"]:
                print("     art:", json.dumps(a, ensure_ascii=False))

for arm in ("A", "B"):
    ok = [s for s in res[arm] if not s.get("missing")]
    if ok:
        print(f"合计 {arm}: calls={sum(s['calls'] for s in ok)} tokens={sum(s['total_tokens'] for s in ok)} "
              f"valid={sum(s['valid_count'] for s in ok)}/{sum(s['artifact_count'] for s in ok)} "
              f"fixed={sum(s['fixed'] for s in ok)} recover={sum(s['recover_or_continue'] for s in ok)}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("JSON:", OUT)
