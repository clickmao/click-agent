
import json
p="/tmp/gameprobe/r374_B_run1.telemetry"
for ln in open(p,encoding="utf-8-sig"):
    ln=ln.strip()
    if not ln: continue
    o=json.loads(ln); kv=o.get("kv",{})
    if o["point"] in ("llm_call","script_artifact","script_run","artifact_feedback","llm_call_continue","llm_call_recover"):
        print(o["point"],"|",json.dumps(kv,ensure_ascii=False)[:300])
