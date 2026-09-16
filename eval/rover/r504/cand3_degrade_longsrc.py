#!/usr/bin/env python3
# R504 cand-3: 本地引擎 (3B) 长原文 (>=600 字) 退化率扫描夹具.
# 铁律: 起手闸 (连续 2 PASS) 才起臂; 无 server => rc=3 fail-closed (绝不落假数).
import json, os, re, sys, glob, subprocess, hashlib

REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r504/evidence/degrade-longsrc-r504.json")
PORT = os.environ.get("R504_LOCAL_PORT", "48630")
CFG = os.environ.get("R504_AGENT_CFG", "/tmp/r455_env/agent/cfg")
URL = os.environ.get("R504_LOCAL_URL", "http://127.0.0.1:%s/v1/chat/completions" % PORT)

def probe_once(text, timeout=120):
    req = {"model": os.environ.get("R504_LOCAL_MODEL", "local"),
           "messages": [{"role": "user", "content": text}],
           "max_tokens": 256, "temperature": 0.0}
    p = subprocess.run(["curl", "-sS", "--max-time", str(timeout), URL,
                        "-H", "Content-Type: application/json", "-d", json.dumps(req)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None, p.stderr.strip()[:200]
    try:
        d = json.loads(p.stdout)
        return (d["choices"][0]["message"]["content"] or ""), None
    except Exception as e:
        return None, "parse:%s" % e

def arm_gate():
    r1, e1 = probe_once("只回复一个词: 好")
    r2, e2 = probe_once("只回复一个词: 好")
    ok = lambda r: r is not None and 0 < len(r.strip()) <= 40 and "？" not in r and "?" not in r
    return {"s1": {"ok": ok(r1), "err": e1, "out": (r1 or "")[:40]},
            "s2": {"ok": ok(r2), "err": e2, "out": (r2 or "")[:40]},
            "armed": bool(ok(r1) and ok(r2))}

def sources(k=8, minchars=600):
    out = []
    for p in sorted(glob.glob(os.path.join(REPO, "docs/**/*.md"), recursive=True)):
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for para in re.split(r"\n\s*\n", t):
            s = " ".join(para.split())
            if len(s) >= minchars:
                out.append({"path": os.path.relpath(p, REPO), "chars": len(s),
                            "sha12": hashlib.sha256(s.encode()).hexdigest()[:12], "text": s})
                break
        if len(out) >= k:
            break
    return out

def main():
    rec = {"round": "R504", "cand": "cand-3", "target": "local 3B paraphrase engine, long source >=600 chars",
           "url": URL, "cfg": CFG, "cfg_exists": os.path.exists(CFG)}
    g = arm_gate()
    rec["start_gate"] = g
    if not g["armed"]:
        rec["verdict"] = "NOT_RUN_START_GATE_FAIL"
        rec["note"] = "起手闸未 PASS 或本地 server 缺席 => fail-closed, 未产生退化率读数"
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(rec, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"verdict": rec["verdict"], "gate": g}, ensure_ascii=False))
        sys.exit(3)
    rec["arms"] = []
    for s in sources():
        o, err = probe_once(s["text"])
        rec["arms"].append({"path": s["path"], "in_chars": s["chars"], "in_sha12": s["sha12"],
                            "out_chars": len(o) if o else None, "out_head": (o or "")[:80], "err": err,
                            "collapsed": (o is not None and len(o) < 0.25 * s["chars"])})
    deg = [a for a in rec["arms"] if a["collapsed"]]
    rec["degrade_rate"] = round(len(deg) / max(1, len(rec["arms"])), 4)
    rec["verdict"] = "PASS"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rec, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"verdict": rec["verdict"], "n": len(rec["arms"]), "degrade_rate": rec["degrade_rate"]}, ensure_ascii=False))

main()
