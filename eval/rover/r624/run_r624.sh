#!/usr/bin/env bash
# R624 复现件：DoD 面 4 达标路径 · 召回面 —— 召回 dense 路**向量源**形态轴
#
# 用法: bash eval/rover/r624/run_r624.sh
#   臂（唯一自由度 = 召回向量源；K 为并列读数轴）:
#     A1 hash x K=50    零回归闸（必须逐位复现 R623）
#     A2 hash x K=200   复现 R623 池宽探针
#     A3 hash x K=1299  兜底形态天花板（全语料）
#     B1 vec  x K=50    主判据（生产形态）
#     B2 vec  x K=200
#     B3 vec  x K=1299  生产形态天花板
#     Z1 zero x K=50    负控（判据必须对向量源有牙）
#
# 前置（必须先跑，rc!=0 即停）: python3 eval/rover/r624/gen_vectors_r624.py
# 纪律: 只在 src/agent.tests 内置形态轴 ⇒ **零产品源码改动**；逐臂 OUT 独立落盘（零串染）；
#       断言失败不吞读数（测试先落盘后断言；本脚本不因 rc!=0 中止，读数照收）。
set -u
cd "$(dirname "$0")/../../.." || exit 1
OUT="$PWD/eval/rover/r624/out"   # 必须绝对：dotnet test 的 cwd = bin/Debug/net10.0（R624 实测器具缺陷，见 verdict 的 posthoc）
mkdir -p "$OUT"

export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$PATH"

echo "BIN_SHA_BEFORE=$(git rev-parse HEAD)"
echo "SRC_DIRTY=$(git status --porcelain -- src/agent.rag src/agent.extensions | wc -l)"

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

run_arm A1 hash 50
run_arm A2 hash 200
run_arm A3 hash 1299
run_arm B1 vec  50
run_arm B2 vec  200
run_arm B3 vec  1299
run_arm Z1 zero 50

echo "BIN_SHA_AFTER=$(git rev-parse HEAD)"
echo "SRC_DIRTY_AFTER=$(git status --porcelain -- src/agent.rag src/agent.extensions | wc -l)"
echo "R624_RUN_DONE"
