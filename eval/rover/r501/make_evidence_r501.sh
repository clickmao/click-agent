#!/usr/bin/env bash
# R501 证据落盘 (日志→repo 内 .txt; .log 被 gitignore ⇒ 必须转 .txt 才能入库)
set -eu
cd /home/agentuser/AgentFramework
D=eval/rover/r501
for pair in "/tmp/r501_gate.txt:gate_r501.txt" "/tmp/r501_test.log:test_all_r501.txt" \
            "/tmp/r501_test_focus.log:test_focus_r501.txt" "/tmp/r501_publish.log:publish_r501.txt" \
            "/tmp/r501_arms.log:arms_r501.txt"; do
  s="${pair%%:*}"; d="${pair##*:}"
  if [ -f "$s" ]; then cp -f "$s" "$D/$d"; fi
done
ls -l "$D" | awk '{print $5, $9}'
