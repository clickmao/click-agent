# 子模块开发计划: 全模块 YAML 分层配置体系

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)
>
> **依据**: 《Agent 框架 全模块 YAML 配置开发规范 v1.0》(用户 2026-09-06 提供的强制开发规约, 原文要点已收录本文,
> 开发时以原文为准 — 本计划是落地适配, 不复制全文)。
> **用户补充约束 (指令原文)**: "注意模块应该调用 base 配置与同名 module 配置覆盖的 config" —
> 即 L1 base 兜底 + L3 同名模块配置覆盖的合并读取是本模块的核心接口契约。

---

## Y.1 现状裁定 (2026-09-06 代码核实)

| 事实 | 位置 | 与规范的冲突 |
|---|---|---|
| 配置/状态文件**全 JSON**: appsettings.json、search_slots.json、credentials.json、approval_cache.json、agent_profiles.json、*_memory.json、计划中的 model_queue.json | Program.cs 27、PromptPersistence.cs 14/18、SessionMemoryStore.cs 79 | 规范 1.2-2 "YAML 唯一格式" → 本模块落地时**定案**: 配置类全部转 YAML (JSON 配置废弃) |
| 无 config/ 分层目录、无 base/env/modules/runtime 结构 | 仓库根 | 规范 §2 目录结构 |
| 无分层覆盖加载器 (只有单文件读) | ServiceCollectionExtensions | 规范 §3 L1→L4 覆盖 |
| 无 YAML 依赖 (无 YamlDotNet 引用) | 无 nuget.config, NuGet 镜像 nuget.azure.cn | — |
| **NativeAOT=true** (TrimmerSingleWarn=false 逐程序集暴露警告) | agent.host.csproj | ⚠ YamlDotNet 是反射型库, AOT 下默认不可用 — 本计划最大技术风险, 见 Y.4 |
| 阈值/开关散在代码: EvidenceGate 最大疑问数 3、SessionMemory 滚动 1000 字符、搜索熔断 3 败 2 分钟、MaxParallelism=4、模型队列 maxConsecutiveFailures=3 | 各源文件 | 规范 7.1 硬编码禁令 |

**JSON 管辖边界 (重要澄清)**: 规范废弃的是**配置类 JSON**。运行时**数据落盘** (会话记忆 *_memory.json、画像 agent_profiles.json、节点状态) 不属于"配置", 不迁移 — 它们已走 source-gen JSON 且 AOT 验证过。仅以下转 YAML: appsettings、未来的 model_queue、skill、context_compression、core 全部配置项。

## Y.2 模块设计 (落点: `src/agent.config/` 新项目, 命名空间 `agent.config`)

```
src/agent.config/
  ConfigLayers.cs        — L1 base / L2 env / L3 modules / L4 runtime 层定义
  YamlConfigLoader.cs    — 分层加载 + 深合并 (同名 module 覆盖 base, 增量继承)
  ConfigSnapshot.cs      — 生效配置快照 (启动全量校验后冻结; source-gen 友好)
  ConfigValidator.cs     — 类型/范围/枚举/依赖 校验 (启动强校验, 失败即启动失败)
  HotReloader.cs         — FileSystemWatcher 监听 runtime/dynamic.yaml (仅 @dynamic 项生效)
  ConfigKeys.cs          — 唯一允许的键名字符串常量 (规范 7.1-2)
```

### Y.2.1 核心读取契约 (用户钦定, 验收核心)
```
模块取配置的唯一入口:
    var cfg = ConfigSnapshot.Get<SectionT>("skill");   // 类型化节读取

内部合并序 (规范 §6.1):
    base/skill.yaml (L1 兜底)
      ← env/{env}.yaml 中 skill: 节 (L2 全局覆盖)
      ← modules/skill.yaml (L3 同名模块覆盖)      ← 用户强调的"同名 module 配置"
      ← runtime/dynamic.yaml 中 skill: 节 (L4 动态, 仅 @dynamic 项)
    深合并规则: 字典递归合并, 标量/列表整体替换; 未定义字段自动继承低层值 (增量覆盖)
```
**模块消费方永远只调 ConfigSnapshot, 禁止自己 File.ReadAllText yaml** — 这是防止绕过分层覆盖的硬约束 (code review 检查项)。

### Y.2.2 首批迁移清单 (按模块, 每模块交付 base 默认配置 — 规范 7.3-1)
| 配置文件 | 收编的现有硬编码 | 来源 |
|---|---|---|
| `base/core.yaml` | MaxTokenBudget 8000、源配额 (Memory 2000/Session 3000/Web 1500)、全局超时 | DataSourceType.cs 96-115 |
| `base/skill.yaml` | (新模块, 见 plan_skill_dispatch.md 全量参数表) | — |
| `base/model_queue.yaml` | maxConsecutiveFailures=3、MaxParallelism=4、/balance 超时 10s | plan_model_queue.md C.3 |
| `base/context_compression.yaml` | SessionMemory 滚动 1000 字符、pinned 免压缩开关 | SessionMemory.cs |
| `base/search.yaml` | 熔断 3 败/2 分钟、槽序 | SearchFailoverService |
| `base/evidence.yaml` | 最大疑问数 3、置信阈值 | EvidenceGate.cs |

规范原文的 context_compression.yaml 示例 (L0-L3 分层/防漂移/弹性校正/异常降级全参数) 是**目标态**,
对应"上下文梯度压缩与防漂移子系统"——该子系统当前只有雏形 (SessionMemory 滚动), 其完整参数表随该子系统开发时收编,
首期只落已有真实参数, **不预写没有代码对应的配置节** (防配置漂移成摆设)。

## Y.3 YAML 解析技术选型 (AOT 硬约束下的决策 — **POC 已完成, 2026-09-06**)
- **YamlDotNet POC 结论 (实测)**: 16.3.0/18.1.0 反射 DeserializerBuilder 均报 IL3050
  ("builder configures the deserializer to use reflection which is not compatible with AOT");
  18.1.0 的 StaticDeserializerBuilder/StaticContext 是抽象类, 需配套 source generator,
  但**主包无 analyzers 目录, 官方/第三方 generator 包均不存在** (Vecc.YamlDotNet.Analyzer 经官方
  search API 验证 totalHits=0, 系 search 截断排版误导; 镜像源 BlobNotFound)。
  **YamlDotNet 路线判死**。
- **定案: 自研 YAML 子集解析器** (零反射, AOT 安全) — 只支持规范用到的特性: 2 空格缩进映射、
  标量 (string/int/double/bool)、`-` 列表、`#` 注释与行内注释、同文件锚点不需要 (规范 4.4 禁跨文件,
  本项目连同文件锚点也不实现)、**不支持**多行块/流式集合 (行内数组规范 4.3 已禁)。
  解析目标: yaml 文本 → Dictionary<string, object> (字典/列表/标量), 合并与校验在其上做。
- 新增依赖: **零** (POC 中 YamlDotNet 18.1.0 已还原到本机, 但不进项目)

## Y.4 关键约束
1. **@dynamic 标注语义**: `@dynamic immediate` 仅对已在内存的 ConfigSnapshot 可变节生效 (FileSystemWatcher 回调重载后原地替换节对象);
   `next-turn` 由 V2 主链轮次边界调 `ConfigSnapshot.PromotePending()`; 静态项热改 → 告警日志不生效 (规范 §6.3)
2. **默认值兜底**: 任何 yaml 文件缺失/格式错/非法项 → 回退内置默认 (ConfigKeys 默认表), 告警不崩溃 (规范 §6.4);
   与 v7.14 AgentProfileStore 教训一致 — 目录不存在先 CreateDirectory
3. **appsettings.json 处置**: 宿主现有的 appsettings.json (日志/连接类) 迁到 `base/core.yaml` + `env/` 覆盖;
   迁移期保留 JsonConfigurationFile 读取一版, 打弃用告警 (规范 7.3-3: 禁止直接删除)
4. **AOT**: source-gen 不适用于 YAML (无 System.Text.Json 等价物) — 绑定必须显式; 新增 csproj 进 sln 后跑 publish 0 警验证
5. **测试配置隔离**: 测试用 `modules/` 定制层覆盖 base (验证 L3 覆盖逻辑本身), 不污染仓库 base/

## Y.5 验收标准
- [ ] 分层覆盖: base 定义 → modules 同名覆盖 → 快照生效值 = 覆盖值; 未覆盖字段继承 base (核心契约, 用户钦定)
- [ ] 四级优先级测试: L4 > L3 > L2 > L1 同字段四层各设不同值, 快照取 L4
- [ ] 启动强校验: 类型错/越界值 → 启动失败 + 明确错误信息 (指到文件:行)
- [ ] 缺失兜底: 删掉 base/skill.yaml → 内置默认值生效 + 告警日志, 不崩溃
- [ ] @dynamic immediate: 改 runtime/dynamic.yaml → 下一次 Get 立即新值; 静态项改 → 告警不生效
- [ ] AOT publish 0 IL 警 (含新 agent.config 程序集)
- [ ] 现有硬编码收编后: 全量测试绿 (现有测试若因配置化导致默认值变化 → 同步修正测试, 保持 221/221+)
- [ ] 消费方改线: EvidenceGate/SessionMemory/SearchFailoverService 等至少 3 处真实改为 ConfigSnapshot 读取 (证明接线, 非空壳)
