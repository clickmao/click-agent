#!/usr/bin/env bash
# EXP1-Q42 step 10: 文档提交 (第二次真提交面读数) + 文档改动后的形式门禁复跑
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
D=eval/capability/exp1-q42

PATHS=(docs/plans/v0.22.0-exp1-local-index-and-code-graph.md docs/improvements.md)
git add -- "${PATHS[@]}"
echo "STAGED=$(git diff --cached --name-only | tr '\n' ' ')"
git commit -q -m "EXP1-Q42 文档收口: 计划文档 AN.10/AN.11 读数 + improvements 顶部加节

AN.10 = AN.9 候选 1/2/4/5/6 并轮读数 (M1-M4/M6 PASS, M5 honest未达) + 根因修复 (bind_evidence 形态反解)
+ 证据件纪律 (HEAD 字段件不得作冻结 pin); AN.11 = 下轮候选 6 项 (含形态统一须独立预注册轮)。
improvements.md 顶部加 EXP1-Q42 节 (版本/日期/状态/主题 + 读数表 + 根因 + 诚实边界)。" \
  > "$D/commit_docs_q42.txt" 2>&1
echo "commit_rc=$?"
tail -3 "$D/commit_docs_q42.txt" | cut -c1-160
echo "--- 现场读数 (第二次真提交面) ---"
tail -2 /tmp/tail_lf_precommit.log 2>/dev/null | cut -c1-160
git log --oneline -2

echo "--- 文档改动后的形式门禁复跑 ---"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet test src/agent.tests/agentframework.tests.csproj \
  --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" \
  --nologo -v q > "$D/form_gate_after_docs_q42.txt" 2>&1
echo "FORM_GATE_AFTER_DOCS_rc=$?"
grep -E "Passed!|Failed!|error" "$D/form_gate_after_docs_q42.txt" | tail -3 | cut -c1-180
echo "--- 工作区残余 (本侧文件应已全部提交) ---"
git status --porcelain | grep -E "verification-registry|instruments.json|bind_evidence|exp1-q4" | head -5
echo "(无输出 = 干净)"
