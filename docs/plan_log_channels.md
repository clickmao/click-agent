# 子模块开发计划: 日志细分通道与前端思考流协议

> **[落地注记]** 本模块已落地 (LogFlags 四通道 + thinking 分片流 + IChatboxSink)。WebSocket 传输宿主为 v0.11.0 计划。

> 独立计划文档 — 阅读本文件即可开发。
> 状态: 待开发 (v7.15) · 来源: 用户需求 2026-09-06 (原文收录 §L.0)

## L.0 需求原文 (逐字)
"关于日志输出需要更多细分，应添加一个flags { 显示到控制台 ，显示到chatbox思考, 显示到chatbox输出, 记录到日志 } 记录到日志cli应该本身也处理到日志缓存内以便存档到文件，显示到chatbox思考应该有一个命令指示告诉前端应该切换思考显示页面，避免思考内容全部加载到前端过长，还需要一个指令提示前端思考结束了来关闭思考步骤显示"

## L.1 现状 (代码事实)
- 工业级日志通道只有 ILogger 控制台 (V2 内 15 处 _logger 调用); 无 flags 概念, 无日志缓存/存档
- V2 无思考流 (Thinking) 输出; 无 chatbox 协议; LocalCommand Known 集 = /stop /continue /pause /status /reset (LocalCommandResult.cs:27-30)
- 前端协议指令当前只有 /status 等查询类; 无"切换思考页/思考结束"推送指令
- v7.13 铁律衔接: "日志返回和问询等一切返回内容都需要有其内部底层格式" — 本模块即该铁律的日志侧落地

## L.2 设计
### L.2.1 日志 flags (四位独立开关, 每条日志按 flags 路由)
```yaml
# config/base/logging.yaml (分层配置, P1 已落地 ConfigSnapshot)
logging:
  default_flags:            # 全局默认, 模块可按通道覆盖
    console: true           # 显示到控制台
    chatbox_thinking: true  # 显示到 chatbox 思考页
    chatbox_output: true    # 显示到 chatbox 输出页
    file: true              # 记录到日志 (存档)
  file:
    dir: ./data/logs
    max_bytes_per_file: 10485760   # 10MB 滚动
    keep_files: 30
```
- LogFlags struct (AOT 纯数据): Console / ChatboxThinking / ChatboxOutput / File 四 bool
- 日志条目内部底层格式 LogEntry (JSON, 契约 v7.13): ts / level / channel(thinking|output|system) / module / msg / sessionId
- CLI 本身也写日志缓存: ConsoleLogSink 之外加 MemoryLogBuffer (环形, 上限 2000 条) — CLI 存档命令 /log dump 时落文件

### L.2.2 前端思考流协议 (2 个新推送指令, JSON)
- 指令 1 `{type:"thinking_page_switch", sessionId, seq}` — 告诉前端切换到思考显示页; 思考内容按 seq 分片推送, 前端只保留最近窗口, 避免全量加载
- 指令 2 `{type:"thinking_end", sessionId, summaryLength}` — 思考结束, 前端关闭思考步骤显示并折叠
- 触发点: V2 推理前发 switch; LLMResponse 回来/落地后发 end; 中途每步 (prompt 构建/检索/子任务) 发 thinking 分片
- 协议指令统一走 registry/LocalCommandResult 扩展或新 FrontendDirective 结构 (与 /status JSON 同构)

## L.3 关键约束
- AOT: LogEntry/指令结构全部进 JsonContext fast-path (v7.14 铁律)
- 四 flag 判定在一条路径上完成, 不允许"写了控制台忘了文件"的分叉实现
- chatbox 推送通道未实装前 (宿主只有 --cli), 指令仍生成并写入日志缓存, CLI 可见 (可测); 前端接线留待宿主 websocket/面板阶段
- 敏感配置 (key/token) 永不入日志 (凭据铁律); LogEntry 不含 Prompt 全文, 只有长度与摘要哈希

## L.4 验收标准
1. flags 四位可独立配置且全部生效 (关 file 后文件不增长, 关 console 后无控制台输出)
2. /log dump 存档文件含 CLI 期间全部 MemoryLogBuffer 条目 (JSON 行)
3. 推理一轮产生: 1 条 thinking_page_switch + ≥N 条思考分片 + 1 条 thinking_end (顺序正确)
4. 全部结构 JSON 化且 AOT publish 0 警

## L.5 明确排除项
- 不做日志远程上报/集中式收集; 不做前端 UI 本体; 不改既有 ILogger 使用点语义 (flags 路由在 sink 层)

## L.6 待确认 ⚠
- ~~chatbox 推送的实际传输通道~~ → **已定案 (v7.15)**: `IChatboxSink` 出口抽象 + CLI 默认
  `ConsoleChatboxSink` (`@chatbox:{json}` 单行协议行到 stdout, `AgentReportReaderBase` 按行解析);
  websocket/面板宿主实现同一接口注入 LogRouter, agent 层零改动。Directives 缓存保留 (回放/测试)。
