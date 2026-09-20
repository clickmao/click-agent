#!/usr/bin/env bash
# R608 提交（逐名列名；禁 git add -A）+ 提交后回读
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3

# 0) 测试副作用复原（全量套件重写 ts ⇒ 与本轮无关；读数逐字段相同）
git checkout -- eval/bge/r404/csharp-fusion-replay.json
echo "reverted_r404=$(git status --porcelain -- eval/bge/r404/csharp-fusion-replay.json | wc -l)"

# 1) 本轮清单（逐字取自 git status --porcelain，禁手打）
PATHS=$(git status --porcelain -uall -- \
  src/agent.nlp/RecognitionVerdict.cs src/agent.nlp/RecognitionOutlet.cs \
  src/agent.tests/RecognitionVerdictTests.cs src/agent/IndustrialAgentV2.cs \
  docs/api-surface.baseline.txt docs/reports/status.json \
  docs/research/lit-review-ledger.md docs/verification-registry.json \
  eval/capability/kpi.jsonl docs/evidence/RF0001/R608-recognition-outlet.md \
  eval/rover/r608/ | awk '{ $1=""; sub(/^ /,""); print }')
echo "--- 待提交清单 ---"
echo "$PATHS"

# 2) 暂存（逐路径）
echo "$PATHS" | while IFS= read -r p; do [ -n "$p" ] && git add -- "$p"; done

# 3) 暂存集 == 本轮清单（机检）
STAGED=$(git diff --cached --name-only | sort)
echo "--- staged ---"
echo "$STAGED"
EXPECT=$(echo "$PATHS" | sort)
if [ "$STAGED" != "$EXPECT" ]; then
  echo "STAGE_MISMATCH: 暂存集 != 本轮清单 ⇒ 中止提交"
  echo "--- diff ---"; diff <(echo "$STAGED") <(echo "$EXPECT") | head -20
  exit 2
fi
echo "STAGE_CHECK=OK ($(echo "$STAGED" | wc -l) 件)"

# 4) 提交（`--amend` 传参即修正同一提交，保持「本轮 1 个提交」）
COMMIT_ARGS=(-q -m "R608: RF0004.1 开放域识别统一出口 {标签|abstain,依据} 落地(单变量 AGENTFRAMEWORK_RECOGNITION_VERDICT; T×3/C×3 真机 + AOT 发布形态冒烟; P1/P2/P3/P4/P5 PASS ∧ P2_ablation FAIL 原样判; registry L3 + kpi 行带 baselines)")
[ "${1:-}" = "--amend" ] && COMMIT_ARGS+=(--amend --no-edit) && echo "AMEND_MODE=on"
git commit "${COMMIT_ARGS[@]}" && echo "COMMIT_RC=0"
git log --oneline -1

# 5) 提交后回读 HEAD 关键行（防静默漏提交）
echo "--- HEAD 回读 ---"
git show --stat HEAD | tail -25
git show HEAD:docs/verification-registry.json | python3 -c "import sys,json;d=json.load(sys.stdin);print('HEAD updated_round=',d['updated_round'],'rows=',len(d['rows']),'last_id=',d['rows'][-1]['id'])"
git show HEAD:src/agent.nlp/RecognitionOutlet.cs | grep -c "public static RecognitionVerdict Render"
git status --porcelain | grep -v '^??' | head -5
echo "TREE_TRACKED_CLEAN_IF_EMPTY_ABOVE"
