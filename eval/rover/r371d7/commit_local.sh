#!/usr/bin/env bash
# R414 本轮本地提交（禁 push；推送闸门在 .git/PUSH_PAUSED + pre-push hook + pushurl 改向）
set -u
cd /home/agentuser/AgentFramework || exit 1

# 1) 产品代码
git add src/agent/IndustrialAgentV2.cs \
        src/agent.modelqueue/ModelQueueRouter.cs \
        src/agent/modelqueue/ModelQueueAdapter.cs \
        src/agent.tests/UserFacingFailureTests.cs || exit 1

# 2) 文档 + 台账 + 登记
git add docs/plans/v0.36.0-r414-failure-visibility.md \
        docs/plans/v0.22.0-r371-capability-probe-python-game.md \
        docs/improvements.md \
        docs/verification-registry.json \
        eval/capability/kpi.jsonl || exit 1

# 3) 证据（.gitignore 已兜底 run-*/ config-*/ *.key *.log）
git add eval/rover/.gitignore eval/rover/r371d7 || exit 1

echo "=== 将要提交的文件 ==="
git diff --cached --name-only
echo "=== 凭据自检（应为空）==="
git diff --cached --name-only | grep -Ei '\.key$|master|token|\.env' || echo "(无)"

git commit -q -F - <<'MSG'
R414: R371 断链真机验收(D7 优先) + 失败可见性缺陷闭合(Success=false 的降级文案不再被链侧丢弃)

验收(eval/rover/r371d7, 真链+确定性远端桩, 判据取外部真值):
- D7 截断续写: llm_call_continue before=102 added=58 after=144 recovered=true;
  after 与独立复刻的合并长度逐位相同(overlap=16); tail_before=断点原文
- D1 空正文: first_content_len=0 / first_reasoning_len=400 => recovered=true
- 负控: ok 臂远端仅 2 请求 / 恢复遥测 0 / truncated=true 0 (无病不治)
- AOT 发布形态复跑(-aot 后缀): empty_always reply_len=[66,73]; truncate=[144,151]
- verdict-r371d7.json = PASS (4 臂 / 24 项断言)

修复(验收暴露的真缺陷):
- IndustrialAgentV2 失败分支曾 `response.Content = string.Empty` 丢弃上游(ModelQueueRouter D1)写入的
  面向用户降级文案 => 用户看到空白(真机 empty_always 轮1 reply_len=0); 既有单测只在 router 层断言
- 契约位 ContentIsUserFacing (QueueResponse/LLMResponse/ModelQueueAdapter) + 链侧 UserFacingFailureContent 裁定
  只透出被显式标记的内容; 未标记 => 仍为空(原始报错正文不外泄); Success=false 语义不变
- 可见降级文案不再拼接 ex.Message (原文保留在 Error 字段)

测试: UserFacingFailureTests 5/5(含 2 条源级钉死); 全量 1164/0/0; 形式校验 13/13; AOT PUBLISH_EXIT=0 / IL 警告 0
MSG

echo "=== 结果 ==="
git log --oneline -1
git show --stat --oneline HEAD | tail -25
