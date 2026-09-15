#!/usr/bin/env bash
# 轮号心跳 (L4 写者仲裁, R444) —— 取轮号前**先占**, 提交后释放。
#   bash tools/round_claim.sh claim R444 [路径glob]
#   bash tools/round_claim.sh status
#   bash tools/round_claim.sh release
# 取轮号前的占用序列 (R423 铁律) 仍须照跑: pgrep 活动执行体 + 锁 + 目标轮文件 mtime + 计划文档版本号。
set -u
GD="$(git rev-parse --git-dir 2>/dev/null || echo .git)"
CLAIM="$GD/ROUND_CLAIM"
cmd="${1:-status}"
# 心跳时效 (秒, 不可解析记 999999 = 陈旧): 防「helper shell 退出 ⇒ 误判陈旧」实测缺陷 (R444)
claim_age_s() {
  [ -f "$CLAIM" ] || { echo 999999; return; }
  ts="$(sed -n 's/^ts=//p' "$CLAIM" | head -1)"
  now="$(date -u +%s)"
  t="$(date -u -d "$ts" +%s 2>/dev/null || echo 0)"
  if [ "$t" -le 0 ]; then echo 999999; else echo $((now - t)); fi
}
case "$cmd" in
  claim)
    round="${2:-?}"; paths="${3:-}"
    if [ -f "$CLAIM" ]; then
      p="$(sed -n 's/^pid=//p' "$CLAIM" | head -1)"
      if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then
        echo "REFUSE: 轮 $round 未占 —— 心跳仍被 pid=$p 持有:" >&2; cat "$CLAIM" >&2; exit 3
      fi
      age="$(claim_age_s)"
      if [ "$age" -lt 5400 ]; then
        echo "REFUSE: 心跳仍新鲜 (pid=$p age=${age}s < TTL 5400s) ⇒ 不得覆盖 (用 status 查看 / release --force 强释放)" >&2; exit 3
      fi
      echo "WARN: 覆盖陈旧心跳 (pid=$p 不存活, age=${age}s)" >&2
    fi
    { echo "round=$round"; echo "pid=$$"; echo "writer=${AGENTFRAMEWORK_WRITER:-$(whoami)-$$}";
      echo "ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "paths=$paths"; echo "cwd=$PWD"; } > "$CLAIM"
    echo "CLAIMED round=$round pid=$$ -> $CLAIM"; cat "$CLAIM"
    ;;
  release)
    if [ -f "$CLAIM" ]; then
      p="$(sed -n 's/^pid=//p' "$CLAIM" | head -1)"
      fresh=0
      if [ -n "$p" ] && kill -0 "$p" 2>/dev/null; then fresh=1; fi
      if [ "$(claim_age_s)" -lt 5400 ]; then fresh=1; fi
      if [ "$fresh" = 1 ] && [ "${2:-}" != "--force" ]; then
        echo "REFUSE: 心跳仍新鲜 (pid=$p age=$(claim_age_s)s < TTL 5400s) ⇒ 不释放 (防抢; 确需释放用 --force)" >&2; exit 3
      fi
      a="$(claim_age_s)"; rm -f "$CLAIM"; echo "RELEASED (pid=$p age=${a}s force=${2:-无})"
    else
      echo "无心跳"
    fi
    ;;
  status|*)
    if [ -f "$CLAIM" ]; then cat "$CLAIM"; p="$(sed -n 's/^pid=//p' "$CLAIM" | head -1)"
      age="$(claim_age_s)"
      if { [ -n "$p" ] && kill -0 "$p" 2>/dev/null; } || [ "$age" -lt 5400 ]; then
        echo "state=FRESH age=${age}s (pid 存活 或 龄<TTL5400s)"
      else echo "state=STALE age=${age}s"; fi
    else echo "state=NONE"; fi
    ;;
esac
