#!/usr/bin/env bash
# R499 臂矩阵: C(改写关 = 同窗对照) + P1,P2,P3(改写开, n=3) —— 同网格/同二进制/同窗
# 纪律: 非零 rc 即中止整个矩阵 (禁带残留续跑); 每臂产物齐备性机检。
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r499
LOG=/tmp/r499_arms.log
: > "$LOG"
run(){ echo "=== $(date '+%T') $* ===" >>"$LOG"; "$@" >>"$LOG" 2>&1; rc=$?; echo "--- rc=$rc $* ---" >>"$LOG"; if [ $rc -ne 0 ]; then echo "[致命] rc=$rc ⇒ 中止矩阵"; exit 1; fi; }
run bash "$DIR/run_arm_real_r499.sh" C "" 49910 49912
run bash "$DIR/run_arm_real_r499.sh" P 1 r499 49920 49922
run bash "$DIR/run_arm_real_r499.sh" P 2 r499 49930 49932
run bash "$DIR/run_arm_real_r499.sh" P 3 r499 49940 49942
echo "=== 产物齐备性机检 ===" >>"$LOG"
python3 - "$DIR" >>"$LOG" 2>&1 <<'PY'
import io,os,sys,json
d=sys.argv[1]; missing=[]
for tag,arm in [("C","C"),("P1","P"),("P2","P"),("P3","P")]:
    for f in [f"calls-{arm}{tag if tag!='C' else ''}.jsonl"]:
        pass
arms=[("C","C",""),("P1","P","1"),("P2","P","2"),("P3","P","3")]
for tag,arm,sfx in arms:
    for pat in ["calls","usage","turns","flags"]:
        p=os.path.join(d,f"{pat}-{arm}{sfx}.json" if pat=="flags" else f"{pat}-{arm}{sfx}.jsonl")
        if not (os.path.isfile(p) and os.path.getsize(p)>0): missing.append(os.path.basename(p))
    td=os.path.join(d,f"teardown-{arm}{sfx}.json")
    if not os.path.isfile(td): missing.append(f"teardown-{arm}{sfx}.json")
    else:
        j=json.load(io.open(td,encoding="utf-8-sig"))
        print(f"{tag}: teardown verdict={j.get('verdict')} procs={j.get('procs')} listeners={j.get('listeners')}")
    fl=os.path.join(d,f"flags-{arm}{sfx}.json")
    if os.path.isfile(fl):
        f=json.load(io.open(fl,encoding="utf-8-sig"))
        print(f"{tag}: flags=" + json.dumps({k:v for k,v in f.items() if k in ("local_paraphrase","host_sha256","host_sha16","grid_sha256","replay_pair_trim","tool_decl_channel","local_decision_mount","action_boundary","turn_gate","repeat_skip")},ensure_ascii=False))
print("MISSING="+json.dumps(missing,ensure_ascii=False))
PY
echo "ALLDONE" >>"$LOG"
