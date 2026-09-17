#!/usr/bin/env bash
# R527 判据机检 (J1..J5 + 全局) — 输出落 eval/rover/r527/evidence/j-criteria.txt
cd /home/agentuser/AgentFramework || exit 1
OUT=eval/rover/r527/evidence/j-criteria.txt
{
  echo "# R527 判据机检 (预注册 eval/rover/r527/prereg-r527.json / 计划 §1)"
  date -Is
  echo
  echo "## J1 命名空间收敛: src 下 (排除 obj/bin) 的 agent.userinteraction / agent.subagent 出现"
  echo "-- 逐目录计数 --"
  grep -rn --include=*.cs -e 'agent\.userinteraction' -e 'agent\.subagent' src \
    | grep -v '/obj/' | grep -v '/bin/' \
    | awk -F: '{print $1}' | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn
  echo "-- 总数 --"
  grep -rn --include=*.cs -e 'agent\.userinteraction' -e 'agent\.subagent' src \
    | grep -v '/obj/' | grep -v '/bin/' | wc -l
  echo "-- 其中 src/agent.core 下 (收敛目标, 应为 0) --"
  grep -rn --include=*.cs -e 'agent\.userinteraction' -e 'agent\.subagent' src/agent.core | wc -l
  echo
  echo "## J2 巨类体量 (候选③)"
  for f in src/agent.modelqueue/ModelQueueRouter*.cs src/agent.contextassembler.ContextAssembler*.cs \
           src/agent/contextassembler/ContextAssembler*.cs src/agent.modelqueue/ModelQueueRouter*.cs; do
    [ -f "$f" ] && printf '%6d  %s\n' "$(wc -l < "$f")" "$f"
  done | sort -rn | head -12
  echo "-- OnProcessAsync 体量 (候选②: 方法起止行) --"
  python3 - <<'PY'
import io, re
src = io.open('src/agent/IndustrialAgentV2.cs', encoding='utf-8').read().split('\n')
start = next(i for i, l in enumerate(src) if 'OnProcessAsync' in l and '(' in l and 'Task' in l)
depth = 0; end = None
for i in range(start, len(src)):
    depth += src[i].count('{') - src[i].count('}')
    if i > start and depth <= 0:
        end = i; break
print(f"方法体行数 = {end - start + 1}  ({start+1}..{end+1})")
print(f"文件总行数 = {len(src)}")
PY
  echo
  echo "## J3 CPM"
  echo "src/*/*.csproj 内联 Version= 计数: $(grep -rn 'Version="' src/*/*.csproj 2>/dev/null | wc -l)"
  echo "Directory.Packages.props PackageVersion 条目数: $(grep -c '<PackageVersion' src/Directory.Packages.props)"
  echo "src 下 PackageReference 总数: $(grep -rn 'PackageReference' src --include=*.csproj | grep -v ValueTuple | wc -l)"
  echo
  echo "## J4 前置闸 / 不变式"
  python3 tools/refactor/new_file_gate.py --selfcheck 2>&1 | tail -2
  python3 tools/refactor/new_file_gate.py 2>&1 | tail -4
  python3 tools/refactor/invariant_check.py 2>&1 | tail -3
  echo
  echo "## J5 候选② 等价性 (夹具比对)"
  tail -3 eval/rover/r527/evidence/equiv-post-compare.txt
  echo
  echo "## 全局: 全量测试 + AOT"
  grep -E "Passed!|Failed!|^RC=" /tmp/r527/test-r527-7.log | tail -2
  echo "AOT: $(grep -E '^RC=' /tmp/r527/aot-r527.log) · IL 警告 $(grep -cE 'warning IL[0-9]{4}' /tmp/r527/aot-r527.log) · 体积 $(stat -c%s /tmp/pub_r527/agenthost) B (R526 $(stat -c%s /tmp/pub_r526/agenthost) B)"
} > "$OUT" 2>&1
tail -30 "$OUT"
