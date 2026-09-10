# 脚本插件交互模式调研 (R352-d, 子代理调研 2026-09-10)

> 用户问题: 其他 agent 如何与脚本交互? 若业界从不在脚本执行过程内主动与 CLI 互动 → 移除现有相关功能。

## 结论 (8 家主流 agent 调研: Claude Code / OpenHands / Devin / Cursor CLI / Codex CLI / Aider / SWE-agent / Goose)

① **无一家实现**"脚本执行中主动向调用方提问并阻塞等待回复"的 stdin/stdout 持续双向对话。
② 业界主导模式 = **单向事件流**: stdout 输出进度/结果, stdin 仅控制信号 (timeout kill / cancel)。
   - Claude Code: 每条 Bash 独立进程, 无 stdin 参数; 交互式命令挂起到超时 (官方 issue 确认 stdin 透传是未实现 feature request)
   - Codex exec: 文档明示"进度流到 stderr、仅最终结果到 stdout"; stdin 非 TTY 管道会挂死 (bug 记录)
   - Cursor CLI: print 模式 = 单向 stream-json 事件流
   - Devin: 长命令自动转后台稍后查输出
   - Goose: shell 工具仅 timeout 参数 (300s 默认) 到点返回
   - SWE-agent: 超时模板明文"本环境不可能接收用户输入", 超时即 cancel+interrupt
③ 执行中向用户提问只发生在 tool call 之间 (AskUserQuestion / 权限审批), 从不在命令执行内部;
   结构化双向请求仅 MCP elicitation/sampling 有定义, 主流 coding agent 脚本执行未使用。

## 部分例外 (非反例)
- OpenHands: 10s 软超时后 agent 可 is_input=true 向**自己持久 shell 会话**注入 stdin (C-c/C-d) —
  agent→自身 shell 的回合制注入, 非调用方↔子进程对话, 用户无法参与。
- Aider /run: 有 pty 时人类用户直接操作终端 — headless/脚本模式无此能力。

## 对照本项目现状 → 判定: 保留 (无需改造)
- ScriptPluginRunner: **纯 stdout JSON Lines 单向事件流** ({progress|heartbeat|done|error}), 无 stdin 交互 ✓
- SkillScriptRunner: stdin 仅写一次任务载荷即 Close (RedirectStandardInput=true + WriteLineAsync + Close) —
  单次数据传递, 非交互通道, 符合业界 ✓
- ConditionalScriptScheduler: 无 stdin ✓
- 判据结论: **现有实现与业界主导模式一致, 不删除、不改造**。
- 未来演进参考: 若确需执行中提问, 业界方向是 MCP elicitation 式结构化请求 (可选能力), 而非裸 stdin 对话。
