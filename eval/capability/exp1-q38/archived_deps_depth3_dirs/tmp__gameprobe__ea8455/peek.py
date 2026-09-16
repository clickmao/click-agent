
import json
for f in ("r374_A_run1","r374_A_run2"):
    p=f"/tmp/gameprobe/{f}.telemetry"
    pts={}
    for ln in open(p,encoding="utf-8-sig"):
        ln=ln.strip()
        if not ln: continue
        o=json.loads(ln); pts.setdefault(o["point"],[]).append(o.get("kv",{}))
    print("==",f)
    for k in ("llm_call","script_artifact","script_run","artifact_feedback"):
        v=pts.get(k,[])
        print(" ",k,len(v), json.dumps(v[:3],ensure_ascii=False)[:420])
