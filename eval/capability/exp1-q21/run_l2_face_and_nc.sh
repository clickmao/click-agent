#!/usr/bin/env bash
# EXP1-Q21 · L2 面 + 4 个注入负控的串行执行器。
# 纪律: 每步退出码**当场显式记录** (不让末条命令代表整批结论); 输出各自落盘, 互不覆盖。
set -u
cd /home/agentuser/AgentFramework || exit 99
OUT=eval/capability/exp1-q21
: > "$OUT/l2_face_runs.txt"

run_step () {
  local tag="$1"; shift
  local log="$OUT/l2_face_${tag}.log"
  echo "=== [$tag] cmd: $* ===" >> "$OUT/l2_face_runs.txt"
  python3 "$@" > "$log" 2>&1
  local rc=$?
  echo "[$tag] EXIT=$rc" >> "$OUT/l2_face_runs.txt"
  tail -3 "$log" >> "$OUT/l2_face_runs.txt"
  echo "" >> "$OUT/l2_face_runs.txt"
}

run_step face        eval/capability/instruments_check.py
run_step nc_drift    eval/capability/instruments_check.py --only exp1q17.archive-field-provenance --fingerprint-drift-inject
run_step nc_claim    eval/capability/instruments_check.py --only r444.analyze --surface-claim-inject
run_step nc_unknown  eval/capability/instruments_check.py --only probe.grade --surface-unknown-inject
run_step nc_missing  eval/capability/instruments_check.py --only exp1q4.docref-probe --surface-missing-inject
echo "ALL_STEPS_DONE" >> "$OUT/l2_face_runs.txt"
cat "$OUT/l2_face_runs.txt"
