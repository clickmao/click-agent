#!/usr/bin/env bash
# R413 提交 (仅本地; 推送暂停令在效 —— 不 push/不镜像/不 gh api 写)
set -u
cd /home/agentuser/AgentFramework || exit 1
R=eval/rover/r413

git add \
  src/agent.modelqueue/LocalGenerationPort.cs \
  src/agent.modelqueue/ModelCatalog.cs \
  src/agent.modelqueue/ModelQueueRouter.cs \
  src/agent.llamacpp/LlamaCppLocalGenerationPort.cs \
  src/agent.llamacpp/agent.llamacpp.csproj \
  src/agent/extensions/ServiceCollectionExtensions.cs \
  src/agent/IndustrialAgentV2.cs \
  src/agent.tests/LocalChannelDispatchTests.cs \
  src/agent.tests/LocalTurnGateTests.cs \
  src/agent.tests/LocalTurnGateProbeTests.cs \
  docs/plans/v0.35.0-r413-r1-local-verdict-token-budget.md \
  docs/plans/v0.34.0-r412-multi-session-slot-contention.md \
  docs/improvements.md \
  docs/reports/dynamic-telemetry-eval-rollback-strategy.md \
  eval/capability/kpi.jsonl \
  "$R/drive_task.py" "$R/run_arm.sh" "$R/stub_openai.py" "$R/task.json" \
  "$R/verdict.py" "$R/verdict-r413.json" "$R/publish_aot.sh" \
  "$R/budget-A.json" "$R/budget-B.json" \
  "$R/calls-A.jsonl" "$R/calls-B.jsonl" "$R/turns-B.jsonl" \
  "$R/probe-struct.jsonl" "$R/probe-struct.jsonl.summary.txt" \
  "$R/run-B/data/telemetry/host.jsonl"

echo "--- 已暂存 ---"
git diff --cached --name-only | sed 's/^/  /'
echo "--- 未暂存 (应为日志/密钥/残留) ---"
git status --porcelain | grep -v '^[MA] ' | head -12

git commit -q -m "R413: r1 本地真假判别接进链管道(端口化) + 机械 Pass 前置 + 非 LLM 模板 ack

- 端口: ILocalGenerationPort / LlamaCppLocalGenerationPort (进程+HTTP, 零 P/Invoke); DI 接线; 端口缺失⇒判据必拒⇒全走远端(零回归)
- 前置门 v2: 机械 Pass 前置(疑问句/新指令/纠正词/结构化实体/长文本⇒直接 Pass, 不问 r1) + 仅无信号短消息交 r1(二元 S/P, 192 上限, 只读思考块之后结论区) + 被跳过轮回复=非 LLM 模板
- 口径修正: 门判 message.Content(用户本轮原文), 不再判被追加过 role/计划块的 prompt.UserMessage ⇒ 修复门恒 Pass/增益归零
- 源码写入铁律: 尖括号字面量经工具写入通道被替换成 tokenizer 形态 ⇒ 改字符码常量 ThinkOpen/ThinkClose + 码点复核
- 遥测: local_turn_gate_config(门是否开可观测) / local_turn_gate(verdict+basis+raw_len)
- 读数(外部真值): 臂A 12 调用/16888 tok vs 臂B 8 调用/7007 tok ⇒ 调用 -33.3% / token -58.5%; 负控零误跳; C1-C4 全 PASS
- 机检: LocalTurnGateTests 46/46 (含 G24 真机原文 / G25 常量形态 / G29 链侧入参源级钉死); 全量 1158/0/0
- AOT: PUBLISH_EXIT=0, IL 警告 0, agenthost 15,138,848 B
- 未推送 (推送暂停令在效)"

echo "COMMIT_EXIT=$?"
git log --oneline -1
git status --porcelain | wc -l
