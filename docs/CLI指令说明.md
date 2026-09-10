# AgentFramework CLI 指令说明

> 需求2 (v7.15) 交付物: 全部可用指令汇总。宿主 = `agenthost` (agent.host)。
> 所有面板/CLI 指令输出**单行 JSON** (source-gen, PascalCase 键) — 前端 `Console.ReadLine()`
> 一次读一行即可快速解析; 流式/多行内容走 `@stream begin … @stream end` 定界块
> (读写协议见 `agent.io` 库, 下文 [IO 协议](#io-协议-agentio))。

## 会话指令总表 (repl 内 `/` 命令 — V2 拦截层)

| 指令 | 参数 | 功能 | 输出 | 实现层 |
|---|---|---|---|---|
| `/plan` | — | 任务计划 (影子计划/TaskPlan 状态) | JSON | V2 拦截 |
| `/model` | — | 当前活跃模型+选模依据+当前模式 (auto/manual) | JSON | V2 拦截 |
| `/model <id>` | 目录模型 id | 手动指定模型 | JSON | V2 拦截 |
| `/model <序号>` | 1-N 整数 | 按列表序号指定模型 (≡ /model <id>) | JSON | V2 拦截 |
| `/model list` | — | 可用模型列表 (序号 1-N + 价格/分数/上下文窗, IsActive 标注) | JSON | V2 拦截 |
| `/model auto` | — | 恢复自动 (清手动+清粘性) | JSON | V2 拦截 |
| `/model verify <id>` | 目录模型 id | 目录参数真机校验 (假 key 探测, 期待 401/403) | JSON | V2 拦截 |
| `/balance [id]` | 可选模型 id | token 余额查询 (scheme 分派) | JSON | V2 拦截 |
| `/official-key` | — | 官方通道 key 注入状态查询 (不回显 key) | JSON | V2 拦截 |
| `/official-key <key>` | key 字面量 | 注入官方通道 key (仅内存, 永不落盘) | JSON | V2 拦截 |
| `/official-key off` | — | 清除官方通道 key | JSON | V2 拦截 |
| `/token stats` | — | Token 用量统计 (总量/按模型/按 provider/预估成本/余额快照) | JSON | V2 拦截 |
| `/forecast` | — | 下轮预估读回 (上轮任务摘要/倾向/延续提示) | JSON | V2 拦截 |
| `/log dump` | — | 内存日志环形缓冲 (2000 条) 存档 JSON 行文件 | JSON | V2 拦截 |
| `/rag` | — | 当前 RAG 数据文件路径查询 | JSON | V2 拦截 (v0.13.0) |
| `/rag <path>` | 文件路径 | 切换 RAG 数据文件 (进程内生效; 历史重载需重启 — 诚实提示) | JSON | V2 拦截 (v0.13.0) |

### 本地命令 (LocalCommandRouter — 不进 LLM)

| 指令 | 功能 | 实现层 |
|---|---|---|
| `/help` | — | 本地命令帮助菜单 (R86: 原送 LLM 浪费一轮, 现本地应答) | 本地 | LocalCommandRouter |
| `/stop` | — | 停止当前执行 | 本地 | LocalCommandRouter |
| `/pause` | — | 暂停 | 本地 | LocalCommandRouter |
| `/continue` | — | 继续 | 本地 | LocalCommandRouter |
| `/reset` | — | 重置会话 | 本地/host | 双层 |
| `/exit` | — | 退出 CLI | — | host |
| `/skills` | — | 查询当前激活 (可匹配) 全部 skills: id/版本/类型/触发词 (v0.16.0-c) | 本地 | LocalCommandRouter + V2 渲染 |
| `/skills-only <id,...>` | 逗号分隔 | 动态 whitelist — 只允许这些 skill 参与匹配 (空 = 清除) (v0.16.0-b) | 本地 | 同上 |
| `/skills-exclude <id,...>` | 逗号分隔 | 动态 blacklist — 排除这些 skill (空 = 清除) (v0.16.0-b) | 本地 | 同上 |
| `/staged` | — / `--json` / `diff <id>` | 列出待审批离线变更批次 (JSON 供前端; diff 显示完整内容) (v0.17.1) | 本地 | 同上 |
| `/approve <id\|all>` | 批次 id | 应用变更到真实文件 — 锁内基线 sha256 比对, 目标被外部改过 → 冲突拒绝绝不覆盖 (v0.17.1) | 本地 | 同上 |
| `/reject <id>` | 批次 id | 标记批次 rejected (staging 保留, /cleanup 物理删) (v0.17.1) | 本地 | 同上 |
| `/cleanup` | — | 物理删除 reclaimable 批次 (v0.17.1) | 本地 | 同上 |
| `/activity` | — | 列出全部激活 agent/窗口/任务: pid/win/job_id/心跳龄 (含其他 CLI 实例) (v0.17.2-a) | 本地 | 同上 |

## 启动参数总表 (进程启动 CLI flags — host)

| 参数 | 参数值 | 功能 | 输出 | 实现层 |
|---|---|---|---|---|
| `-q "<msg>"` | 消息文本 | 单条模式 (不进 REPL) | 回复 | host |
| `-img <path>` | 图像路径 (可多次) | 附带图像走视觉理解链 (v0.12.0) | 回复 | host |
| `-rag <path>` | index.jsonl 路径 | 指定 RAG 数据文件 (v0.13.0 已落地; ≡ /rag 或 env AGENTFRAMEWORK_RAG_PATH) | — | host |
| `--log <path>` | 文件路径 | 输出 tee 到文件 | — | host |
| `--output-mode text\|markdown` | 模式 | 输出渲染模式 | — | host |
| `--official-key <key>` | key 字面量 | 启动注入官方通道 key (内存态; 命令行引用立即释放) | — | host |
| `--embed <text>` | 文本 | 直连 BgeEmbedder 输出向量 JSON (评测离线算 reply_rel, 不走 LLM/DI 全链) | stdout | host (R136) |
| `--compression-audit <path>` | groundtruth.json | 压缩底座 audit: 分档校验矩阵 (档×级别→关键信息保留率/压缩率/耗时), 落 eval/results/ | JSON | host (v0.13.3) |
| `--skills-dir <dir>` | 目录 (可多次) | 外挂 skills 目录 — 与内置 skills/ 合并匹配, 同 SkillId 外挂覆盖内置 (v0.16.0-a) | — | host |
| `--skills-blacklist <id或目录名>` | 值 (可多次) | 加载后从注册表移除指定 skill (精确 id + 包目录名双匹配) (v0.16.0-a) | — | host |
| `--skills-file <SKILL.md>` | 单 skill 文件 (可多次) | 外挂单 skill 文件 (目录包外) (v0.16.0-a) | — | host |
| `--smoke` | — | 冒烟自检 (全图 AOT 校验) | 日志 | host |
| `--llm-manager` | — | 启动 llm-manager 轻量常驻进程 (0 模型占用; worker 按需 lazy 拉起; 资源紧张 ∧ 无 CLI 实例 → kill worker 卸载) (v0.20.0) | 日志 | host |
| `--llm-service` | — | 启动 worker 进程 (真正加载 bge 嵌入服务; 通常由 manager 拉起, 也可手动/外部守护启动) (v0.20.0) | 日志 | host |

### LLM 服务独立进程 (v0.20.0 — llm-manager / worker, 用户钦定)

目标: 新 CLI 不再重复加载 LLM 到内存/显存 (bge 加载后 RSS ~157MB, LLM 更甚)。

```
CLI(s) ──UDS──→ llm-manager (轻量常驻, 0 模型, 不随 CLI 生死)
                   ├─ lazy:     首个使用请求 → 拉起 worker (真加载模型)
                   ├─ supervise: worker 崩溃/被杀 → 下次请求自动重拉
                   └─ unload:   资源紧张 ∧ 无 CLI 实例 ∧ 无进行中请求 → kill worker (OS 回收内存)
                            └──UDS──→ llm-service-host (worker, 可被杀)
```

| env | 默认 | 说明 |
|---|---|---|
| `AGENTFRAMEWORK_LLM_SERVICE_SOCK` | 系统临时目录 `af-llm.sock` | 客户端↔manager 通讯 socket (worker socket 同路径 + `.worker`) |
| `AGENTFRAMEWORK_LLM_SERVICE_BIN` | 当前 agenthost 进程路径 | 客户端/manager 拉起时的 agenthost 可执行路径 |
| `AGENTFRAMEWORK_LLM_SERVICE_LOG` | `<sock>.log` | daemon 自写日志 (跨平台, 不依赖 shell 重定向) |
| `AGENTFRAMEWORK_LLM_SERVICE_MEM_FLOOR_MB` | 512 | 可用内存低于此值 (且无 CLI 实例) → 卸载 worker |
| `AGENTFRAMEWORK_LLM_SERVICE_UNLOAD_CHECK_MS` | 15000 | 卸载巡检间隔 |
| `AGENTFRAMEWORK_BGE_MODE` | `local` | **opt-in** 嵌入后端: `remote` → 走本机 llm-service (CLI 进程免加载 bge, 首次调用 lazy 拉起 manager/worker); 其他/未设 → 原路径 (进程内 BgeEmbedder, 行为不变) (v0.20.1 P4-a) |

行为要点: ① **不按时间卸载** — 内存充足则 worker 常驻; ② 空闲长连接不阻止卸载 (下次请求自动重拉);
③ 客户端窗口 5min 内自启 ≥3 次 → 熔断 (防重启风暴); ④ manager 被 SIGKILL 后残留的孤儿 worker 由新 manager 启动时清理。
⑤ 客户端调用入口 (库): `agent.llamalocal.RemoteEmbedder` (ITextEmbedder 实现; 现有 DI 路径默认不变)。

### 探索/思考链环境开关 (v0.13.3 R287)

| 环境变量 | 值 | 语义 |
|---|---|---|
| `AGENTFRAMEWORK_EXPLORE` | 未设/`1` = 开 (默认) / `0` = 全关 | 思考链探索总开关 (RunThinkChainAsync 入口短路; explore_eval A/B 对照组语义) |
| `AGENTFRAMEWORK_RAG_PATH` | index.jsonl 路径 | RAG 数据文件 (≡ -rag / /rag) |
| `AGENTFRAMEWORK_LOCAL_DISABLED` | `1` | 批测禁本地模型 (qwen 路径) |
| `AGENTFRAMEWORK_BGE_MODEL` | gguf 路径 | bge 嵌入模型路径 |
| `AGENTFRAMEWORK_TELEMETRY` | 目录 | telemetry jsonl 输出目录 (run_round per-case 隔离) |

## /model list 与序号选择 (v0.10.0)

```bash
/model list        # 输出: Models[] 数组, Index=1..N (目录顺序), 含价格/推理分/编码分/上下文窗, IsActive 标注当前
/model 3           # 等价 /model deepseek-chat (目录第 3 项) — 越界诚实报错 index_out_of_range
/model auto        # 回到自动模式 (Mode: auto)
/model             # 查询当前状态 (含 Mode: auto|manual)
```

执行双模式: **auto** (默认, 内部智能选模: 能力 0.4 + 速度 0.3 + 价格 0.3) / **manual** (`/model <id|序号>` 进入)。

## /token stats 与余额联动 (v0.10.0)

```bash
/token stats       # TotalTokens / TokensByModel / TokensByProvider / EstimatedCostUsd / Balances / BalanceFlag
```

余额联动契约 (models.yaml `balance_schemes` + `proxy` 段): 初始化真实 API 同步一次 →
每次调用本地累计 → 阈值 (默认 10 万 token) 再同步。余额预估不足时自动切换其他模型,
`BalanceFlag` 字段携带 `model:xxx flags:余额不足` 协议行 (前端展示用)。

## /forecast 下轮预估 (v0.10.0 新需求4)

```bash
/forecast          # AgentUid / TaskSummary / LastIntent / Tendency / ContinuationHint / LikelyContinues / TurnCount / UpdatedAt
```

每轮任务完成后 agent 规则式生成下轮预估 (落 `data/agents/<uid>/forecast.json`),
下轮对话自动拼入 prompt header 指示 LLM 延续; 本指令随时读回查看。
无记录时返回 `{"forecast": null, "hint": "尚无下轮预估 — 完成一轮任务后自动生成"}`。

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

## -img 图像输入 (v0.12.0)

```
agenthost -img /path/to/image.png "你的问题"
```

- 作用: 附带本地图像文件启动对话, 走视觉理解链 (glm-5.3-flash v4 端点, data URL base64)。
- 约束: 带图请求强制云端 (本地 qwen 不支持); text-only 模型自动重路由。
- 多轮: repl 会话内图像仅首轮生效; 目录/链接探索见 v0.13.0 计划文档。

## /rag RAG 数据文件 (v0.13.0, 用户钦定)

```
/rag            # 查询当前 RAG 数据文件路径 (JSON)
/rag <path>     # 切换 RAG 数据文件 (进程内生效; 历史索引重载需重启 — 诚实提示)
```

CLI 启动参数 (等价):

```
agenthost -rag /path/to/index.jsonl -q "问题"
agenthost -rag /path/to/index.jsonl   # repl 会话
```

- 作用: 指定 RAG 索引落盘/恢复文件 (默认 `data/rag/index.jsonl`), 支持多库隔离 (评测/项目/个人)。
- 语义: 切换后新文档落新路径; 历史索引恢复按启动时路径 (诚实提示, 不静默重载)。
- env 等价: `AGENTFRAMEWORK_RAG_PATH=<path>` (CLI/任务内都落到此钩子)。
## /plan /log /balance 快查 (V2 拦截)

| 指令 | 功能 | 备注 |
|---|---|---|
| `/plan` | 最近一次影子计划 TaskPlanRun JSON (面板惯例) | 无记录 → `{"plan": null}` 诚实提示 |
| `/log dump` | 内存日志环形缓冲 (2000 条) 存档 JSON 行文件 | 路径见返回 JSON |
| `/balance [id]` | token 余额查询 (provider scheme 分派: openai=subscription, deepseek=balance) | 智谱无公开余额 API → 诚实报错 |

