# AgentFramework 改进文档 (improvements.md)

> 每版本一节: 完成记录 (真实证据) + 下一版本计划。历史版本详情见 git log 与 readme.md 开发计划段。

---

## v0.11.0 (2026-09-06) — 统一命令协议 + 三传输 + Skill 脚本执行 (进行中)

### ✅ 已完成 (真实执行)
- **agent.io 统一命令协议**: `AgentCommand` 信封 (@cmd name key=value 行协议, 百分号转义手写编解码 — 零依赖 AOT 安全) + `AgentCommandWriter/Reader` 工具类 (组合 WriterBase/ReaderBase); AgentReportReaderBase 加 Command 事件分类
- **三种传输**: Console.IO (已有 Text 对) / 共享内存 (`SharedMemoryRequestWriter/ReportReader` — 文件-backed mmap 环形区, 背压可见) / TCP Socket (`SocketChannelServer/Connect` — 跨机)
- **LogRouter 双通道**: thinking/输出指令同时镜像 IChatboxSink + @cmd (前端二选一解析)
- **SkillScriptRunner**: SKILL.md 包 scripts/ 真进程调度 (python/bash/node PATH 探测; cwd=包目录沙箱; 环境变量白名单; 超时杀进程树; 退出码非 0 stderr 附加); 脚本 @cmd 命令 → AgentCommandWriter 转发 (skill 附参) — 脚本即最小前端, 与面板同契约
- **SkillDispatcher 接线**: executive 无显式 entry → 包脚本自动执行 (RegisterEntry 优先)
- **性能修复 (sync-over-async 清剿)**: ModelQueueRouter.OnTransientFailure → async 链; TriggerMatcher.MatchAsync (语义嵌入 await 化); ContextGradientCompressor.CompressCoreAsync
- **模型目录 6 → 18**: +Anthropic (sonnet-4.5/haiku-4.5) +Google (gemini-2.5-pro/flash) +xAI (grok-4/fast) +Moonshot (kimi-k2) +Qwen (qwen3-max/coder-plus) +DeepSeek v3.2 +OpenAI (gpt-5/o4-mini) +GLM-4.5 — 全部公开牌价, /model verify 可校验

### 📊 基线
- 测试: **351/351 全绿** (+10: 命令协议 6 + 脚本执行 4 — python 真进程实跑)
- AOT: publish 0 警 0 IL 警; /model list 18 模型真机确认

## v0.10.0 (2026-09-06) — Yamlify 换库 + Token 统计/余额联动 + Skill 语义 + 全链路实跑

### 🎯 主题 (用户指令): YAML 库换 Yamlify / Token 使用统计+余额不足切模 / Skill P3 语义匹配接 bge / 统一输出收口 / 指令补全

### ✅ 完成记录 (全部真实执行, 证据可复现)
1. **YAML 解析换 Yamlify** (`src/agent.config/MiniYaml.cs` 重写为门面)
   - Yamlify 1.8.0 (SwissLife-OSS, MIT, net10.0, 零依赖, SourceGenerator 级, 运行时零反射)
   - AOT 实测: PublishAot 零 IL 警告; 真实解析项目 models.yaml 全字段正确
   - `MiniYaml.Parse` API 签名不变 → 5 个消费者 (ConfigSnapshot/SkillRegistry/ConfigWriter/测试) 零改动
   - 修复历史 bug: 顶层列表键 (`models:`) 走 GetSection 返回空 → 新增 `TryGetTopLevel`; 运行时目录一直为空的真 bug 得以暴露与修复
   - 配置根解析: `AGENTFRAMEWORK_CONFIG` env 覆盖 + cwd/AppContext.BaseDirectory 向上 8 级探测
2. **Token 使用统计 + 余额联动** (`src/agent.modelqueue/TokenUsageService.cs` 新增, 143 行)
   - 契约: 初始化真实 API 同步一次 → 每次调用本地累计 → 阈值 (默认 10 万 token) 再同步
   - 余额预估: `remaining = api余额 - 本地累计×单价`; 不足 → 切换其他模型 + `model:xxx flags:余额不足` 提示 (LastBalanceFlag)
   - `/token stats` 指令: 总量/按模型/按 provider/预估成本/余额快照 全 JSON
   - DI: TokenUsageService → ModelQueueRouter (余额检查在 CallAsync 主链)
3. **Skill P3 语义匹配接 bge** (`src/agent.skills/TriggerMatcher.cs`)
   - 词面 (关键词/正则/领域词) 全未命中 → bge 余弦相似度疑似判定 (cos ≥ 0.45)
   - 嵌入器不可用/失败 → 静默回退词面匹配 (行为兼容); 4 个新测试锁定语义契约
   - DI: SkillDispatcher 注入 ITextEmbedder (BgeEmbedder 真机 384 维)
4. **官方端点可配置代理** (`ServiceCollectionExtensions.cs` + `models.yaml proxy 段`)
   - `ConfigurePrimaryHttpMessageHandler` 正确形态; 留空直连
   - modelqueue 命名客户端全走代理 (主调用/余额/verify 共用)
5. **统一输出收口** (新需求3)
   - host 8 处 Console.WriteLine → IOutputSink/ILogger; agent 库死代码 Program.cs (23 处直写) 删除
   - 库内零 Console 直写 (CliRenderer 本体除外 — 它就是 sink 实现)
6. **/forecast 指令** (新需求4): v7.11 内部机制前端可见化; 无记录诚实返回 null 提示
7. **/model list + 序号选择** (上轮): 序号 1-N = 目录顺序; `/model 3` ≡ `/model deepseek-chat`; auto/manual 双模式
8. **LocalLlamaCaller DI 修复**: 真实注册 (models.yaml local 段); gguf 缺失 → 诚实降级不可用
9. **版本号统一**: 15 个 csproj → 0.10.0

### 📊 基线 (真实执行输出)
- 测试: **341/341 全绿** (含 4 个语义匹配 + 4 个 SKILL.md 包格式 + 4 个本地通道 + 4 个 /model list 新测试)
- Release 编译: 0 错 0 警
- NativeAOT publish: 0 IL 警; agenthost 12MB ELF 真机运行
- AOT 冒烟: `/model list` (6 模型目录加载 ✓) / `/model 3` (序号→manual ✓) / `/token stats` (全 JSON ✓) / `/forecast` (null 提示 ✓)
- GitHub 推送: ✓ main → clickmao/click-agent @ 387bfb1 (经 ghproxy 通道; upload-github.sh 已改为环境变量取 token)

### 📋 下一版本 (v0.11.0) 计划
1. **Skill 全球通用开放规范落地** (新需求5): skills/ 目录按 Anthropic Agent-Skills Open Standard 重构 — SKILL.md 包格式 (yaml front-matter + scripts/references/assets 目录), 兼容 OpenAI 等 Agent 框架; SkillRegistry 加载器适配 + 用例改造
2. **readme 双语页内切换完善**: 初始化中文 + 锚点切换交互优化
3. **余额阈值切模实战验证**: 真实 API key 环境下 E2E (当前无 key, 逻辑测试覆盖)
4. **Chatbox websocket 宿主**: IChatboxSink 已就绪, 补一个真实 websocket 宿主实现 (面板对接)

---

## v7.15 (2026-09-05) — 十节点全落地 (归档)

> 开发计划 (v7.15 — 全部节点已落地): 详见 readme.md「开发计划」段与 git log。
> 十节点: ①Skill 调度 P1 ②模型队列与意图选模 ③日志四通道 ④上下文梯度压缩 ⑤影子计划 ⑥问询打通 ⑦会话恢复 ⑧公开配置读写 ⑨agent.io 协议库 ⑩能力插件接口。
> 需求四项: ①官方通道混合调度 ②agent.io ③会话中断恢复 ④公开配置读写。
> 基线: 276→325 测试全绿 / AOT 0 IL 警 / 双冒烟通过。

---

## v7.14 (2026-09-05) — 归档
EvidenceGate→ClarificationBatch 接入 V2 主链 / vulkan setenv 双写 / SessionMemory 滚动 / AgentProfile 动态学习 / CapabilityScanner 重构 / 目标锚免压缩 / 面板全 JSON。基线 218/218。
