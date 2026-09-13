#!/usr/bin/env bash
# bge 闸门+融合 静默自动巡检 (no_agent cron 直接跑本脚本)。
# 设计: 一切正常 -> **零输出**(watchdog 形态, 不打扰用户); 异常 -> 告警行, cron 直投给用户。
# 与 bge_idle_train.sh 同约定: 锁防重入 / 资产候选 / .env.local / 零输出静默。
set -uo pipefail
REPO="/home/agentuser/AgentFramework"
cd "$REPO" || exit 0
mkdir -p data/bge docs/reports/bge
LOG="data/bge/auto_cycle.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# 防重入 (与训练脚本共用同一把锁语义, 但独立文件避免互相阻塞)
exec 9>data/bge/.auto.lock
flock -n 9 || { log "skip: lock held"; exit 0; }

export PATH="$HOME/.dotnet:$PATH"
set -a; [ -f .env.local ] && . ./.env.local; set +a

# 模型候选 (auto_cycle.py 内亦有一份; 此处只为把 BGE_MODEL 显式化, 便于换机)
if [ -z "${BGE_MODEL:-}" ]; then
  for c in "$REPO/.agentframework/models/bge-q8.gguf" "$HOME/.agentframework/models/bge-q8.gguf" \
           "/tmp/models/bge-q8.gguf"; do
    [ -f "$c" ] && { export BGE_MODEL="$c"; break; }
  done
fi
if [ -z "${BGE_BASE_MODEL:-}" ] && [ -f /tmp/models/bge-base-zh-v1.5-q8.gguf ]; then
  export BGE_BASE_MODEL="/tmp/models/bge-base-zh-v1.5-q8.gguf"
fi

log "start (model=${BGE_MODEL:-?} base=${BGE_BASE_MODEL:-?})"
out=$(python3 eval/bge/auto_cycle.py 2>&1)
rc=$?
[ -n "$out" ] && { log "rc=$rc alert=${#out}B"; printf '%s\n' "$out"; } || log "rc=$rc silent-ok"
exit 0
