# AgentFramework CLI 指令说明

> 需求2 (v7.15) 交付物: 全部可用指令汇总。宿主 = `agenthost` (agent.host)。
> 所有面板/CLI 指令输出**单行 JSON** (source-gen, PascalCase 键) — 前端 `Console.ReadLine()`
> 一次读一行即可快速解析; 流式/多行内容走 `@stream begin … @stream end` 定界块
> (读写协议见 `agent.io` 库, 下文 [IO 协议](#io-协议-agentio))。

## 指令总表

| 指令 | 参数 | 功能 | 输出 | 实现层 |
|---|---|---|---|---|
| `/status [agent_uid]` | 可选 uid | 会话/模型/通道状态总览 | JSON | host (PanelDataService) |
| `/session <agent_uid> [index]` | uid, 可选序号 | 会话详情/历史遍历 | JSON | host (PanelDataService) |
| `/plan` | — | 任务计划 (影子计划/TaskPlan 状态) | JSON | V2 拦截 |
| `/model` | — | 当前活跃模型+选模依据 | JSON | V2 拦截 |
| `/model <id>` | 目录模型 id | 手动指定模型 | JSON | V2 拦截 |
| `/model auto` | — | 恢复自动 (清手动+清粘性) | JSON | V2 拦截 |
| `/model verify <id>` | 目录模型 id | 目录参数真机校验 (假 key 探测, 期待 401/403) | JSON | V2 拦截 |
| `/balance [id]` | 可选模型 id | token 余额查询 (scheme 分派) | JSON | V2 拦截 |
| `/official-key` | — | 官方通道 key 注入状态查询 (不回显 key) | JSON | V2 拦截 |
| `/official-key <key>` | key 字面量 | 注入官方通道 key (仅内存, 永不落盘) | JSON | V2 拦截 |
| `/official-key off` | — | 清除官方通道 key | JSON | V2 拦截 |
| `/log dump` | — | 内存日志环形缓冲 (2000 条) 存档 JSON 行文件 | JSON | V2 拦截 |
| `/stop` | — | 停止当前执行 | 本地 | LocalCommandRouter |
| `/pause` | — | 暂停 | 本地 | LocalCommandRouter |
| `/continue` | — | 继续 | 本地 | LocalCommandRouter |
| `/reset` | — | 重置会话 | 本地/host | 双层 |
| `/exit` | — | 退出 CLI | — | host |

### CLI 启动参数 (非指令)

| 参数 | 说明 |
|---|---|
| `--smoke` | 冒烟自检 (全图 AOT 校验) |
| `--log <path>` | 输出 tee 到文件 |
| `-q "<msg>"` | 单条模式 (不进 REPL) |
| `--output-mode text\|markdown` | 输出渲染模式 |
| `--official-key <key>` | 启动时注入官方通道 key (内存态; 需求1; 注入后命令行引用立即释放) |

## IO 协议 (agent.io)

独立库 `src/agent.io/` (**netstandard2.1**, 零依赖, 兼容任意 .NET 宿主/前端):

### 写入 (前端 → agent)

```csharp
AgentRequestWriterBase writer = new AgentRequestWriter(Console.Out);
writer.WriteRequest("/status");          // 单行指令直写
writer.WriteRequest("多行\n内容");        // 自动升级为流式块包裹
writer.WriteStreamBlock("行1", "行2");    // 显式 @stream begin/end 块
```

- `AgentRequestWriterBase` — 抽象基类 (写一行核心抽象, 协议逻辑全在基类)
- `AgentRequestWriter` — TextWriter 实现

### 读取 (agent → 前端)

```csharp
AgentReportReaderBase reader = new TextReportReader(Console.In);
ReportEvent e = reader.ReadEvent();       // 阻塞读下一个语义事件
List<string>? block = reader.ReadStreamBlock(); // 聚合下一个流式块
```

`ReportEventKind` 分类:

| Kind | 识别规则 | 载荷 |
|---|---|---|
| `Text` | 其他 | 整行 |
| `ChatboxDirective` | `@chatbox:{json}` 前缀 | 前缀后的 JSON |
| `StreamBegin` | `@stream begin` | — |
| `StreamChunk` | 块模式内任意行 | 原文行 |
| `StreamEnd` | `@stream end` | — |
| `Json` | `{` 开头 `}` 结尾单行 (fast-path, 完整校验交 JSON 库) | 整行 |
| `Eof` | 流结束 | — |

设计要点: 前端每次 `Console.ReadLine()` 一整行 → `ReadEvent()` 一次聚合一个完整语义事件;
多行流式返回由基类内部状态机 (`_inStreamBlock`) 跨行聚合, 单行指令零开销直通 —
满足"指令单行、内容多行"的双态要求。
