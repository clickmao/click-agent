#!/usr/bin/env bash
# R625 复现件：DoD 面 4 生产口径对齐（召回池宽 K=10）+ 精排段成本列首测
#
# 用法: bash eval/rover/r625/run_r625.sh
#   臂（唯一自由度 = 召回池宽 K；形态为并列读数轴）:
#     A50 hash x K=50   零回归闸（必须逐位复现 R624 A1，gated=90）
#     A10 hash x K=10   兜底形态 × 生产口径
#     B50 vec  x K=50   零回归闸（必须逐位复现 R624 B1，gated=97）
#     B10 vec  x K=10   主判据（生产形态 × 生产口径）
#     Z10 zero x K=10   负控（判据必须对向量源有牙）
#
# 前置: 向量件 eval/rover/r624/vec（R624 产出，逐字节复用；无 = fail-closed 退出）
# 纪律: 只在 src/agent.tests 内加**成本列信息字段** ⇒ **零产品源码改动**；
#       逐臂独立落盘（绝对路径，承 R624 器具缺陷①）；断言失败不吞读数。
set -u
cd "$(dirname "$0")/../../.." || exit 1
OUT="$PWD/eval/rover/r625/out"
mkdir -p "$OUT"

export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$PATH"

VEC="$PWD/eval/rover/r624/vec/corpus-trunc440.f32"
if [ ! -s "$VEC" ]; then echo "PRECOND_FAIL: 向量件缺失 $VEC"; exit 3; fi
echo "VEC_SHA12=$(sha256sum "$VEC" | cut -c1-12)"

echo "BIN_SHA_BEFORE=$(git rev-parse HEAD)"
echo "SRC_DIRTY=$(git status --porcelain -- src/agent.rag src/agent.extensions src/agent | wc -l)"

dotnet build src/agent.tests/agentframework.tests.csproj --nologo -v q || { echo "BUILD_FAIL"; exit 2; }

run_arm() {
  local arm="$1" embed="$2" k="$3"
  AGENTFRAMEWORK_R623_SHAPE=fusion \
  AGENTFRAMEWORK_R623_TOPK="$k" \
  AGENTFRAMEWORK_R623_EMBED="$embed" \
  AGENTFRAMEWORK_R623_OUT="$OUT/$arm.json" \
    dotnet test src/agent.tests/agentframework.tests.csproj --no-build \
      --filter "FullyQualifiedName~RerankFaceTests" --nologo -v q >"$OUT/$arm.console.txt" 2>&1
  local rc=$?
  local line
  line=$(grep -E '^(Passed!|Failed!)' "$OUT/$arm.console.txt" | head -1)
  local has=no
  [ -s "$OUT/$arm.json" ] && has=yes
  echo "ARM=$arm embed=$embed k=$k rc=$rc payload=$has :: $line"
}

run_arm A50 hash 50
run_arm A10 hash 10
run_arm B50 vec  50
run_arm B10 vec  10
run_arm Z10 zero 10

echo "BIN_SHA_AFTER=$(git rev-parse HEAD)"
echo "SRC_DIRTY_AFTER=$(git status --porcelain -- src/agent.rag src/agent.extensions src/agent | wc -l)"
echo "R625_RUN_DONE"
