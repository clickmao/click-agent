import json, os, re, subprocess, sys

P = "/tmp/gameprobe"
TEL = P + "/r376_run1.telemetry"
LOG = P + "/r376_run1.md"

calls, tokens, arts, runs, feedback = [], 0, [], [], []
for line in open(TEL, encoding="utf-8-sig", errors="replace"):
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        e = json.loads(line)
    except Exception:
        continue
    pt = e.get("point", "")
    if pt == "llm_call":
        calls.append(e)
        for k in ("total_tokens", "tokens", "totalTokens"):
            if isinstance(e.get(k), (int, float)):
                tokens += int(e[k])
                break
    elif pt == "script_artifact":
        arts.append(e)
    elif pt == "script_run":
        runs.append(e)
    elif pt == "artifact_feedback":
        feedback.append(e)

print("telemetry: calls=%d tokens=%d artifacts=%d script_run=%d feedback=%d" % (
    len(calls), tokens, len(arts), len(runs), len(feedback)))
for a in arts:
    print("  artifact:", a.get("path") or a.get("name"), "origin=", a.get("origin"))
for r in runs:
    print("  script_run: exit=", r.get("exit_code", r.get("exit")), "path=", r.get("path"))
for f in feedback:
    print("  artifact_feedback:", {k: f.get(k) for k in ("fixed", "error_kind", "attempts", "ms", "detail")})

# ---- 独立复核: 不信任遥测自报, 自己跑闸门 ----
cand = []
for a in arts:
    p = a.get("path") or a.get("file") or a.get("name")
    if p and os.path.exists(p):
        cand.append(p)
if not cand:
    # 兜底: data/artifacts 下最新 py_*.py
    d = "/home/agentuser/AgentFramework/data/artifacts"
    if os.path.isdir(d):
        py = sorted((os.path.join(d, x) for x in os.listdir(d) if x.endswith(".py")),
                    key=os.path.getmtime)
        cand = py[-1:]
for p in cand[-2:]:
    r = subprocess.run(["python3", "-I", p, "--selftest"], capture_output=True, text=True, timeout=120)
    tail = (r.stdout or "").strip().splitlines()[-2:]
    print("INDEPENDENT selftest: %s exit=%d tail=%s" % (os.path.basename(p), r.returncode, tail))

if os.path.exists(LOG):
    size = os.path.getsize(LOG)
    txt = open(LOG, encoding="utf-8", errors="replace").read()
    print("log: %d bytes; 含 PASS=%s 含 FAIL=%s" % (size, "PASS" in txt, "FAIL" in txt))
