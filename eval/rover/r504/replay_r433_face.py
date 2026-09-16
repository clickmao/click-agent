#!/usr/bin/env python3
# R504 cand-4: r433 行证据面可重放夹具
import json, subprocess, sys, hashlib, os, re, shutil
REPO = "/home/agentuser/AgentFramework"
OUT = os.path.join(REPO, "eval/rover/r504/evidence")
SCRATCH = "/tmp/r504_replay"
FROZEN = os.path.join(REPO, "eval/capability/r433/kpi-report.md")

def run(cmd):
    p = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()[:12]

def counts(txt):
    return re.findall(r"selftest\s+(\d+)/(\d+)", txt)

rep = {"round": "R504", "row": "r433.probe-code-source-artifact-channel", "stages": {}}
rc1, o1 = run("python3 eval/probe/grade.py --selftest")
rc2, o2 = run("python3 eval/probe/run_probe.py --selftest")
rep["stages"]["grade_selftest"] = {"rc": rc1, "counts": counts(o1)}
rep["stages"]["runprobe_selftest"] = {"rc": rc2, "counts": counts(o2)}
rep["stages"]["kpi_selftest"] = dict(zip(("rc", "out"), run("python3 scripts/kpi_probe.py --selftest")))
os.makedirs(SCRATCH, exist_ok=True)
replay = os.path.join(SCRATCH, "kpi-report-replay.md")
rc3, o3 = run("python3 scripts/kpi_probe.py --glob 'data/probe/probe-*r433*.json' --report %s --no-ledger" % replay)
rep["stages"]["kpi_replay_report"] = {"rc": rc3, "path": replay}
rep["frozen_report"] = {"path": FROZEN, "md5_12": md5(FROZEN) if os.path.exists(FROZEN) else None}
rep["replay_report"] = {"md5_12": md5(replay) if os.path.exists(replay) else None}

def rows(path):
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.startswith("| "):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 11 or not c[0].isdigit():
            continue
        out[c[1]] = {"set": c[3], "tasks": c[4], "cases": c[5], "whole": c[6],
                     "rate": c[7], "elapsed": c[8], "tokens": c[10]}
    return out

fr, rr = rows(FROZEN), rows(replay)
rep["rows_frozen"] = len(fr); rep["rows_replay"] = len(rr)
rep["missing_in_replay"] = sorted([k for k in fr if k not in rr])
rep["drift"] = []
for k in rr:
    if k in fr:
        for f in ("set", "tasks", "cases", "whole", "rate", "tokens"):
            if fr[k][f] != rr[k][f]:
                rep["drift"].append({"run": k, "field": f, "frozen": fr[k][f], "replay": rr[k][f]})
rep["repro_gap_declared"] = rep["missing_in_replay"]
ok = (rc1 == 0 and rc2 == 0 and rc3 == 0 and not rep["drift"])
rep["verdict"] = ("PASS" if ok and not rep["missing_in_replay"] else ("PASS_DECLARED_GAP" if ok else "FAIL"))
os.makedirs(OUT, exist_ok=True)
p = os.path.join(OUT, "replay-r433-face.json")
json.dump(rep, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: rep[k] for k in ("verdict", "rows_frozen", "rows_replay", "drift", "missing_in_replay")}, ensure_ascii=False))
sys.exit(0 if ok else 1)
