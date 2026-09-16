#!/usr/bin/env bash
# R499 离线证据落盘 (不起上游、不重发布、不跑构建): 探针 / 二进制检查 / 判据自检 / 起手闸让行记录
set -u
cd /home/agentuser/AgentFramework
D=eval/rover/r499

echo "== ① AOT 字符串存在性方法探针 ==" | tee $D/aot-string-presence-r499.txt
python3 $D/probe_aot_string_presence.py /tmp/pub_r498/agenthost /tmp/pub_r499/agenthost 2>&1 | tee -a $D/aot-string-presence-r499.txt

echo "== ② 被测二进制检查 (sha/类名表/smoke) ==" | tee $D/binary-check-r499.txt
{ ls -l /tmp/pub_r499/agenthost | awk '{print "BIN_BYTES="$5}'
  sha256sum /tmp/pub_r499/agenthost
  printf '/exit\n' | timeout 30 env -i /tmp/pub_r499/agenthost --version 2>&1 | head -1
  echo "SMOKE_RC=${PIPESTATUS[1]}"; } 2>&1 | tee -a $D/binary-check-r499.txt

echo "== ③ 判据器自检 (R497/Aroleb 干跑 + 负控) ==" | tee $D/judge-selftest-r499.txt
{ python3 $D/judge_paraphrase_r499.py --dir eval/rover/r497 --arm T1 --mode C 2>&1 | tail -4
  echo "DRYRUN_RC=${PIPESTATUS[0]}"
  python3 $D/judge_paraphrase_r499.py --dir eval/rover/r497 --arm T1 --mode C --nc nc_c_absorb 2>&1 | tail -2
  echo "NC_C_ABSORB_RC=${PIPESTATUS[0]}"; } 2>&1 | tee -a $D/judge-selftest-r499.txt

echo "== ④ 起手闸让行记录 ==" | tee $D/gate-hold-r499.txt
for f in /tmp/pf_r499.json /tmp/pf_r499b.json /tmp/pf_r499_c1.json /tmp/pf_r499_c2.json /tmp/pf_r499_c3.json /tmp/pf_r499d.json; do
  [ -f "$f" ] || continue
  python3 - "$f" <<'PY' 2>&1 | tee -a $D/gate-hold-r499.txt
import io, json, sys
p = sys.argv[1]; d = json.load(io.open(p, encoding="utf-8-sig"))
print("%-24s verdict=%s mem_avail_mb=%s cause=%s src_writes_120s=%s build_nodes=%s refused=%s" % (
    p.split("/")[-1], d.get("verdict"), d.get("mem_available_mb"), d.get("blocker_cause"),
    d.get("recent_src_writes_120s"), (d.get("build_node_reap") or {}).get("candidates"),
    (d.get("build_node_reap") or {}).get("refused")))
PY
done
grep -E "MemAvailable" /proc/meminfo | tee -a $D/gate-hold-r499.txt
echo "让行判据: MemAvailable < 2650 MB (阈值) ⇒ 不起真机测量 (R486/R495 纪律)"
