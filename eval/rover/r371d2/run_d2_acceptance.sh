#!/usr/bin/env bash
# R371 D2 真机验收 —— 「发布产物自包含 config」：从**仓库外 cwd** 运行发布产物。
#
# 判据（预注册，全部为外部真值：进程 stdout/exit code + 磁盘上的产物）：
#   T  (治疗臂)  /tmp/pub_d2/agenthost     自包含发布（修复后）  → 输出**不得**含「模型目录为空」
#   N1 (负控·撤销修复) 同一二进制，但其自带 config/ 被移走      → 输出**必须**含「模型目录为空」（复现生产症状）
#   N2 (负控·修复前产物) /tmp/pub_aot_r370/agenthost（D2 修复前发布） → 输出**必须**含「模型目录为空」
#   T/N1 成对 ⇒ 探针有判别力（不是「跑起来就算过」）；N2 ⇒ 缺陷可复现。
# 运行环境纪律：cwd=/tmp/d2-cwd（仓库外，其 8 级祖先无 config 目录）；显式 env -u AGENTFRAMEWORK_CONFIG。
# 退出码语义：本脚本结论由 D2_VERDICT 标记给出，**不由末条命令**决定（避免 grep 零匹配冒充失败）。
set -u
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"

ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r371d2
PUB=/tmp/pub_d2
CWD=/tmp/d2-cwd
NEW=$PUB/agenthost
OLD=/tmp/pub_aot_r370/agenthost
MARK="模型目录为空"
LOG=$DIR/acceptance.log
: > "$LOG"

rm -rf "$CWD"; mkdir -p "$CWD"
# 外部 cwd 的祖先链自证：确认没有 config 可被「cwd 上溯」命中（否则 T 的通过不能归因于产物自带）
{ echo "=== cwd=$CWD 祖先链中是否存在 config ==="
  for d in "$CWD" /tmp /; do [ -d "$d/config" ] && echo "ANCESTOR_CONFIG_HIT=$d" || echo "no-config: $d"; done
} >> "$LOG" 2>&1

# 产物自带 config 的静态证据
{ echo "=== 产物自带 config ==="
  ls -l "$PUB/config/base/" 2>&1 | head -20
  echo "--- sha256 对照（产物 vs 仓库）---"
  for f in models.yaml core.yaml skill.yaml; do
    a=$(sha256sum "$PUB/config/base/$f" 2>/dev/null | cut -d' ' -f1)
    b=$(sha256sum "$ROOT/config/base/$f" 2>/dev/null | cut -d' ' -f1)
    echo "CFG_SHA $f pub=${a:-missing} repo=${b:-missing} identical=$([ -n "$a" ] && [ "$a" = "$b" ] && echo 1 || echo 0)"
  done
} >> "$LOG" 2>&1

Q="一句话确认配置已加载。"

run_case() { # $1=name $2=bin
  local name=$1
  local bin=$2
  local raw="$DIR/case-$name.raw"
  local out="$DIR/case-$name.out"
  local rc=999 size=0
  : > "$raw"
  ( cd "$CWD" && env -u AGENTFRAMEWORK_CONFIG timeout 120 "$bin" -q "$Q" ) > "$raw" 2>&1
  rc=$?
  size=$(stat -c%s "$raw" 2>/dev/null || echo 0)
  head -c 2000000 "$raw" > "$out"
  local hit=0
  grep -q "$MARK" "$out" && hit=1
  echo "CASE=$name RC=$rc SIZE=$size EMPTY_CATALOG_HIT=$hit" | tee -a "$LOG"
}

# ── 治疗臂：修复后发布产物，config 就位 ──
run_case treatment "$NEW"

# ── 负控 N1（撤销修复）：把产物自带的 config 移走，其余完全不变 ──
mv "$PUB/config" "$PUB/config.hidden" 2>/dev/null && echo "N1: 已移走 $PUB/config" >> "$LOG"
run_case neg_remove "$NEW"
mv "$PUB/config.hidden" "$PUB/config" 2>/dev/null && echo "N1: 已还原 $PUB/config" >> "$LOG"

# ── 负控 N2（修复前产物）：D2 修复那次 commit 之前的发布，从不自包含 ──
if [ -x "$OLD" ]; then
  run_case neg_prefix "$OLD"
else
  echo "CASE=neg_prefix SKIPPED (no $OLD)" | tee -a "$LOG"
fi

echo "D2_ACCEPT_LOG=$LOG"
