
import io, json, os, sys

def load(p):
    rows = []
    for l in io.open(p, encoding="utf-8-sig", errors="replace"):
        l = l.strip()
        if not l.startswith("{"):
            continue
        try:
            o = json.loads(l)
        except Exception:
            continue
        rows.append(o)
    return rows

def kpi(p):
    rows = load(p)
    calls = [r for r in rows if r.get("point") == "llm_call"]
    tok = 0
    ms = 0
    for c in calls:
        kv = c.get("kv") or {}
        tok += int(kv.get("total_tokens") or kv.get("tokens") or 0)
        ms += int(kv.get("ms") or 0)
    arts = [r for r in rows if r.get("point") == "script_artifact"]
    runs = [r for r in rows if r.get("point") == "script_run"]
    fb = [r for r in rows if r.get("point") == "artifact_feedback"]
    gate = [r for r in rows if r.get("point") == "evidence_gate"]
    turn = [r for r in rows if r.get("point") == "loop_turn"]
    out = {"file": os.path.basename(p), "calls": len(calls), "tokens": tok, "llm_ms": ms,
           "artifacts": len(arts), "script_run": len(runs), "feedback": len(fb),
           "gate": [g.get("kv") for g in gate], "turn": [t.get("kv") for t in turn]}
    a0 = (arts[0].get("kv") or {}) if arts else {}
    out["artifact_detail"] = a0
    r0 = (runs[0].get("kv") or {}) if runs else {}
    out["run_detail"] = r0
    return out

for p in sys.argv[1:]:
    print(json.dumps(kpi(p), ensure_ascii=False))
