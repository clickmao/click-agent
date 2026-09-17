#!/usr/bin/env bash
# EXP1-Q46: 后态读数 + 盘面证伪读数 + 前态锚臂 + 探针自检 (分步落盘, 标记显式)
set -u
cd /home/agentuser/AgentFramework || exit 3
D=eval/capability/exp1-q46
DOC=docs/reports/dynamic-telemetry-eval-rollback-strategy.md

python3 scripts/capability_cycle_status.py > "$D/status_post.json" 2>&1
echo "POST_RC=$?" > "$D/post_marks.txt"

python3 eval/capability/r518/scan_round_sections.py > "$D/scan_now.txt" 2>&1
echo "SCAN_RC=$?" >> "$D/scan_now.txt"

git show 32125b7:"$DOC" > "$D/nc_prestate_doc.md"
{
  echo "ANCHOR_SHA=32125b7"
  if git merge-base --is-ancestor 32125b7 HEAD; then echo "ANCHOR_ANCESTOR=TRUE"; else echo "ANCHOR_ANCESTOR=FALSE"; fi
  if cmp -s "$D/nc_prestate_doc.md" "$DOC"; then echo "BLOB_DIFFERS=FALSE"; else echo "BLOB_DIFFERS=TRUE"; fi
  echo "ANCHOR_STALE_HITS=$(grep -c '未在本轮动' "$D/nc_prestate_doc.md")"
} > "$D/nc_anchor_marks.txt"

python3 scripts/capability_cycle_status.py --master "$D/nc_prestate_doc.md" > "$D/status_nc_prestate.json" 2>&1
echo "NC_RC=$?" >> "$D/nc_anchor_marks.txt"

python3 scripts/capability_cycle_status.py --selftest > "$D/selftest_post.txt" 2>&1
echo "SELFTEST_RC=$?" >> "$D/selftest_post.txt"

grep -n "EXP1-Q45\|EXP1-Q46" "$DOC" | head -5 > "$D/scan_now_refs.txt"
echo "STEP_ALL_DONE=1"
