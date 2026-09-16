#!/usr/bin/env python3
# R495 泄漏复核 (H2 必错族证伪的**独立**取证面): 关轴臂回复里的码 vs 本臂台账码 (映射无关)。
# 产物: eval/rover/r495/leak-check-<arm>.json
import json, re, sys, os, hashlib

D = "/home/agentuser/AgentFramework/eval/rover/r495"
CODE = re.compile(r"LCM-[0-9a-fA-F]{12}\b")
TURNS = (13, 14, 15)


def main(arm):
    tag = "r495"
    tp = os.path.join(D, "turns-%s%s.jsonl" % (arm, tag))
    lp = os.path.join(D, "ledger-%s%s.jsonl" % (arm, tag))
    doc = json.load(open(tp, encoding="utf-8-sig"))
    led = [json.loads(l) for l in open(lp, encoding="utf-8-sig") if l.strip()]
    codes = {r["code"]: {"n": r["n"], "turn": r["turn"], "kind": r["kind"]} for r in led}
    rows = []
    for t in doc["turns"]:
        if int(t["turn"]) not in TURNS:
            continue
        rep = t.get("reply") or ""
        found = sorted(set(CODE.findall(rep)))
        hit = {c: codes[c] for c in found if c in codes}
        rows.append({"turn": t["turn"], "reply_chars": len(rep), "codes_in_reply": found,
                     "true_codes_leaked": sorted(hit.keys()), "leaked_from_ledger_n": hit,
                     "reply_head": rep[:160]})
    out = {"schema": "r495-leak-check/1", "arm": arm, "ledger_rows": len(led),
           "ledger_codes": len(codes), "turns": rows,
           "verdict": "LEAK" if any(r["true_codes_leaked"] for r in rows) else "no_leak",
           "note": "映射无关: 只比 '回复里的 LCM- 码' 与 '本臂台账落盘码'。命中即证明真值可经盘上文件获得 (必错族证伪)。"}
    p = os.path.join(D, "leak-check-%s%s.json" % (arm, tag))
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:1500])
    print("→", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "B"))
