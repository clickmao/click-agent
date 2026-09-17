#!/usr/bin/env bash
# EXP1-Q12 形式校验补跑（附录 C/E/J-K/L 四次结转的债务）— 真机证据 (L3)
# 退出码由解析器/判定器给出: 0=全绿 / 2=断言失败 / 3=测量或环境失败
# 判据先于读数冻结在 prereg_q12.json（+ amend1 修正件）；阈值只有一处字面量。
# runner 修订 v2：**先收尾（编译服务节点）→ 再读闸**。v1 把收尾放在读闸之后，
#   于是上一步 dotnet test 留下的 VBCSCompiler 会触发本步的并发闸（自伤），
#   且它占的内存会把内存闸一起拖红 ⇒ 第二次起门恒红。
set -u
ROOT=/home/agentuser/AgentFramework
# 可重定位：证据目录 = 本脚本所在目录（改后第二跑用 rerun/ 副本，不覆盖首跑证据）
OUT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 3
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
LOG="$OUT/run_form_check.log"

AMEND="$OUT/prereg_q12_amend1.json"
if [ -f "$AMEND" ]; then GATE_SRC="$AMEND"; else GATE_SRC="$OUT/prereg_q12.json"; fi
THR=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("change",{}).get("to_threshold",2800))' "$GATE_SRC" 2>/dev/null || echo 2800)
# 注意：pgrep 模式串只出现在脚本里（不进任何被 pgrep 扫到的 cmdline），避免模式字面量自匹配。
CONC_PAT='MSBuild|VBCSCompiler|agenthost|llama-server|run_round|drive_task|capability_cycle'

: > "$LOG"
echo "=== EXP1-Q12 form-check runner v2 start $(date -Is) ===" >> "$LOG"
echo "gate_source=$(basename "$GATE_SRC") gate_mem_threshold=$THR" >> "$LOG"

# --- 步骤 1：先收尾（编译服务/编译节点），并把匹配到的进程原文落盘 ---
echo "pre_shutdown_matches:" >> "$LOG"
pgrep -af "$CONC_PAT" 2>/dev/null | sed 's/^/  /' >> "$LOG" || true
dotnet build-server shutdown >> "$LOG" 2>&1
echo "build_server_shutdown_exit=$?" >> "$LOG"
sleep 1

# --- 步骤 2：起手闸 (C7): 并发 + 内存 ---
echo "post_shutdown_matches:" >> "$LOG"
pgrep -af "$CONC_PAT" 2>/dev/null | sed 's/^/  /' >> "$LOG" || true
CONC=$(pgrep -f "$CONC_PAT" 2>/dev/null | wc -l)
MEM=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
STUBS=$(pgrep -f 'fake.llama' 2>/dev/null | wc -l)
{
  echo "gate_concurrent_procs=$CONC"
  echo "gate_pattern=$CONC_PAT"
  echo "gate_MemAvailable_MB=$MEM"
  echo "observed_orphan_stubs=$STUBS"
} >> "$LOG"
if [ "$CONC" -ne 0 ]; then
  echo "reason=GATE_CONCURRENT" >> "$LOG"
  echo 3 > "$OUT/raw_rc.txt"
  echo "GATE_BLOCKED_CONCURRENT conc=${CONC}"
  exit 3
fi
if [ "$MEM" -lt "$THR" ]; then
  echo "reason=GATE_MEMORY" >> "$LOG"
  echo 3 > "$OUT/raw_rc.txt"
  echo "GATE_BLOCKED_MEMORY mem=${MEM} thr=${THR}"
  exit 3
fi

# --- 步骤 3：目标面指纹 (C6) ---
{
  echo "head=$(git rev-parse HEAD)"
  echo "head_short=$(git rev-parse --short HEAD)"
  echo "head_subject=$(git log -1 --format=%s)"
  echo "registry_sha256=$(sha256sum docs/verification-registry.json 2>/dev/null | cut -d' ' -f1)"
  echo "skills_md_count=$(find skills -name SKILL.md 2>/dev/null | wc -l)"
  echo "tests_csproj_mtime=$(stat -c %y src/agent.tests/agentframework.tests.csproj 2>/dev/null)"
} >> "$LOG"

# --- 步骤 4：内存采样器（信息字段：本类测量的真实占用峰值） ---
: > "$OUT/mem_samples.txt"
( for _ in $(seq 1 600); do awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo >> "$OUT/mem_samples.txt"; sleep 2; done ) &
SAMPLER=$!

# --- 步骤 5：真机形式校验 ---
rm -rf "$OUT/trx"; mkdir -p "$OUT/trx"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
  dotnet test src/agent.tests/agentframework.tests.csproj \
  --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" \
  --nologo -v q \
  --logger "trx;LogFileName=form_check_q12.trx" \
  --results-directory "$OUT/trx" \
  >> "$LOG" 2>&1
rc=$?
kill "$SAMPLER" 2>/dev/null
wait "$SAMPLER" 2>/dev/null
echo "dotnet_test_exit=$rc" >> "$LOG"
echo "$rc" > "$OUT/raw_rc.txt"
echo "=== dotnet test finished $(date -Is) raw_rc=$rc ===" >> "$LOG"

# --- 步骤 6：判定（结论只由解析器的显式标记给出） ---
python3 "$OUT/parse_form_check_q12.py" --run
pverdict=$?
echo "ROUND_EXIT(from parser)=$pverdict" >> "$LOG"
exit $pverdict
