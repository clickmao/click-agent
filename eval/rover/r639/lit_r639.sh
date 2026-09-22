#!/usr/bin/env bash
# R639 文献小步（预算：arXiv ≤3 query / 间隔 ≥4s / 全文抓取 ≤2）
set -u
cd /home/agentuser/AgentFramework
OUT=eval/rover/r639/lit
mkdir -p "$OUT"
S="$HOME/.hermes/skills/research/arxiv/scripts/search_arxiv.py"
# 出口直探（fail-closed 前置：出口不可达 ⇒ 空采信不计入降频计数）
curl -sS -o /dev/null -w 'ARXIV_PROBE http=%{http_code} t=%{time_total}s\n' -m 20 \
  'https://export.arxiv.org/api/query?id_list=2402.03300' > "$OUT/probe.txt" 2>&1
cat "$OUT/probe.txt"
q1='subgroup worst-case aggregation evaluation'
q2='prefix cache reuse long-context agent cost'
q3='agent repair loop failed artifact feedback'
i=0
for q in "$q1" "$q2" "$q3"; do
  i=$((i+1))
  echo "=== Q$i: $q ==="
  python3 "$S" "$q" --category cs.CL --max 6 --sort date > "$OUT/q$i.txt" 2>&1
  head -32 "$OUT/q$i.txt"
  sleep 5
done
