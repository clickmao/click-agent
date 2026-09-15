#!/usr/bin/env bash
# L2 负控: 伪造"另一写者持有轮号"的新鲜心跳 ⇒ pre-commit 必须拒绝(非零)。
# 用 AGENTFRAMEWORK_ROUND_CLAIM 指向临时心跳文件: 走同一代码路径, 不干扰真实占号。
set -u
TMP="$(mktemp)"
printf 'round=R444-NC\npid=%s\nwriter=other-agent\nts=%s\n' "$$" "$(date -u +%FT%TZ)" > "$TMP"
AGENTFRAMEWORK_ROUND_CLAIM="$TMP" AGENTFRAMEWORK_WRITER=me bash tools/hooks/pre-commit
rc=$?
rm -f "$TMP"
echo "[nc hook] rc=$rc (期望 1 = 第二写者被拒; 8 = 空心跳过(不合格))"
exit $rc
