#!/usr/bin/env bash
# R497: 把**作废的 B 臂读数**归档 (理由: 首次 run_all 用了对象型 turns ⇒ drive_task 抛异常, t16/t17 0 秒失败;
#   第二次 run_all 被 NS_COLLISION 闸拦 ⇒ rc=7)。归档不删, 便于复核「撞号=一等事件」。
set -u
cd /home/agentuser/AgentFramework/eval/rover/r497 || exit 1
V=void-r497-B-objturns
mkdir -p "$V"
cat > "$V/README.md" <<'EOF'
# R497 作废读数 (B 臂, 第一次 run_all)

- 时间: 2026-09-16 23:19:31 → 23:21 前后
- 原因: 网格 t16/t17 被写成对象 {i,text,family,note}, 而 drive_task.py 只接受字符串轮次 ⇒
  `t16/t17: The requested operation requires an element of type 'String', but the target element has type 'Object'` ⇒
  两轮 0 秒失败 (turns-B.jsonl stats ok=15/17)。
- 处置: 网格机派生器改为「turns 字符串数组 + 元数据进 expected[]」, 重新生成网格 (sha 变化);
  本目录为**作废读数**, 不参与任何判断 (判据器只读 $DIR 根下的 calls-*/usage-*/turns-*)。
- 第二次 run_all 触发 NS_COLLISION 闸 (calls-B.jsonl 已有读数, rc=7) ⇒ 归档后重跑 B 臂。
EOF
for f in calls-B.jsonl usage-B.jsonl turns-B.jsonl host-B.log relay-B.log server-B.txt flags-B.json preflight-B.json prov-B.json config-B run-B; do
  [ -e "$f" ] && mv "$f" "$V/" && echo "[archived] $f"
done
echo "[void] 余下: $(ls -1 "$V" | wc -l) 项"
