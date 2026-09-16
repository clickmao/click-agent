#!/usr/bin/env bash
# R500 负控补跑: (a) nc_c_absorb 对 R500 C 臂 (注入扰动 ⇒ 期望 rc=1);
#                (b) rootcause K1 阴性对照 (删 P1 的 reject 行 ⇒ 期望 NOT_CONFIRMED rc=1)
set -u
cd /home/agentuser/AgentFramework
echo "== (a) nc_c_absorb on R500 C =="
python3 eval/rover/r499/judge_paraphrase_r499.py --dir eval/rover/r499 --arm C --mode C --nc nc_c_absorb 2>&1 | tail -4
echo "NC_A_RC=${PIPESTATUS[0]}"
echo "== (b) rootcause K1 阴性对照 =="
T=/tmp/rc_nc_r500
rm -rf "$T"; mkdir -p "$T"
ln -s "$PWD/eval/rover/r499/grid" "$T/grid"
for a in C P2 P3; do ln -s "$PWD/eval/rover/r499/tel-$a" "$T/tel-$a"; done
mkdir -p "$T/tel-P1"
python3 - <<'PY'
import io, json, os
src = "eval/rover/r499/tel-P1/host.jsonl"
dst = "/tmp/rc_nc_r500/tel-P1/host.jsonl"
kept = 0
with io.open(dst, "w", encoding="utf-8", newline="\n") as f:
    for ln in io.open(src, encoding="utf-8-sig"):
        if (json.loads(ln).get("point") == "local_turn_gate_reject"):
            continue
        f.write(ln)
        kept += 1
print("K1-NC 删除 reject 行后保留 %d 行" % kept)
PY
python3 eval/rover/r500/rootcause_check_r500.py "$T" /tmp/rc_nc_r500/out.txt 2>&1 | tail -6
echo "NC_B_RC=$?"
