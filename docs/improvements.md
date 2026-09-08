# AgentFramework 改进文档 (improvements.md)

> **记录规则 (2026-09-08 重梳)**: 顶部 = 最新版本, 逐版本向下递减; 每节格式统一
> (版本 / 日期 / 状态 / 主题 / 完成记录 / 基线)。v7.x 为历史遗留版本号体系 (v0.x 前身),
> 原始记录见文末「历史遗留」区, 详情走 git log。

---

## v0.13.x (2026-09-08) — 底座能力与收敛环 (开发中)

### 主题 (用户钦定): 渐进式探索 / 思考链收敛 / 兜底粘性路由 / 格式修复收敛环 / 底座能力长期观察

### ✅ 完成记录 (真实执行)

**v0.13.0**
- 渐进式探索: ExplorationConfig (每上下文区/文本/URL/目录最大探索步 + 全局预算 + URL 深度) + ExplorationPlanner (优先级队列; 用户例: 上下文内 URL > 上下文外目录) — 7 单测
- 思考链 T3: ComplexityGate + EvidenceScorer (多源对比, 单源封顶 medium) + ThinkMemory RAG 联想 (相似问题优先历史高置信链接, 引用后 +0.05 置信, 负样本降权, 30 天衰减) + ThinkChainSession — 12 单测
- RAG 数据文件用户指定: CLI `-rag <path>` / 任务内 `/rag` / env 三入口 (真机三态验证)
- Baseline 换血 (用户钦定): L0-L5 分层; XL 大上下文族真机验证 (XL-01 实测 7010 tok, 回复含全部 ground truth; XL-04 10750 tok); ContextBudgetGate (WARN 6000/HARD 9000, 防抖首次跨越放行修复 — python 复现抓 bug) — 6 单测

**v0.13.1**
- 兜底粘性路由: FallbackConfig (config 开关 + cost_quality 性价比序 + 逐个兜底 + 回复校验, MinReplyChars=2 由 Router 测试实证) + Router 逐个兜底链 (fallback_attempt/fallback_verify_fail 打点) + StickyRouteMemory (三门判定: 相似+意图+实体指纹; 最近成功优先 0.01 容差; TTL 72h) — 11 单测

**v0.13.2**
- 格式修复收敛环: IFormatRepairPlugin + JsonRepairPlugin (栈感知括号修复; 用户破损 JSON 实例回放通过) + FormatRepairLoop (①块内检测→②查找→③校验→④本地修复→⑤LLM 循环; max_llm_rounds 可计数; 技能-校验矩阵硬规则) — 13 单测

**v0.13.3**
- 底座能力长期观察 (用户钦定, 入 master-plan §0-2): 压缩 audit (`--compression-audit`, 104 篇多样态 ground-truth × 4 档 × 3 级别)
- A3 关键句保护修复: TakeSentences 评分保留因果/指令句 — SummarySentences 因果/指令保留 0-20% → 单样式 100% / 多样态 99% (keys) / 85% (指令, 无标点样式待修)
- 429 感知调度: 限流跳过同模型重试直切备 (省 ~1000 tok/次重发)
- token-breakdown 每批观测行 (prompt/history/completion)
- 微步骤隔离设计 A6 (阈值门控, 更正2: 未达阈值走常规; 触发率基线 0%)

**缺陷修复 (本段)**: 真缺陷 65 (重试/切备成功路径 llm_call 打点缺失→429 后 token 全丢, 批187 假性 KPI_BREACH) / 66 (文本请求备选落视觉模型成本倒挂) / 67 (Text 能力硬过滤, cogview 误入文本备选) / 68 (C17 断言脆性 → neg_context_markers 推测围栏, 双向回放验证)

### 📊 基线
- 测试: **468/468 全绿** (404 → 468, 含探索 7/思考链 12/兜底粘性 11/格式修复 13/预算门 6/视觉族 3)
- AOT: publish 0 IL 警 (多次重发布); 批测: 批 174-217 带内 (600-1250 tok/case), full-23 23/23
- 文档: CLI 指令说明三表重构 (会话指令/本地命令/启动参数); docs/ 全量审计 (6 文档归档, 断链 0)

---

## v0.12.0 (2026-09-08) — 视觉理解 / 渲染插件 / 收敛环 (已验收)

### ✅ 完成记录 (真实执行)
- **视觉理解链**: CLI `-img` → Message.ImageAttachments → data URL base64 → glm-5.3-flash v4 端点; text-only 模型自动重路由 + coding 端点改写 (真缺陷 63/64); OpenAIMultimodalMessage 双形态 DTO (string|parts[], AOT-safe 手写 converter)
- **图像渲染插件体系** (用户钦定收敛环服务化): IImageRenderPlugin 契约 + SkiaSharpRenderPlugin (默认 PNG, 边缘选项 `-p:DisableSkiaRenderer=true` 停编) + SvgTextRenderPlugin (零依赖兜底) + ImageRenderPluginRegistry (HasRenderer=false → 跳过后续环节); LocalSvgRenderer DSL (rect/circle/line/text, XML 转义, 栈感知)
- **收敛环 E2E**: LLM 生成 DSL → 渲染 → 5.3-flash 视觉校验 → FAIL 重生成 → PASS (真机一轮 PASS: DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)
- **能力矩阵**: models.yaml 25/25 模型 capabilities 回填; CogViewClient 保留 (生成路径按用户钦定 R210 弃用)
- **验收**: T-V01~04 视觉用例族 full-23 23/23 (含负样本诱饵识破: 模型拒绝"右下角苹果"假预设); 四问真机复证; 基线 docs/reports/v012-acceptance-baseline.md

### 📊 基线
- 测试: 415+ 绿 (视觉 DTO 5 + 渲染器 3 + 插件 4); AOT 0 IL 警

---

## v0.11.0 (2026-09-06) — 统一命令协议 + 三传输 + Skill 脚本执行

### ✅ 已完成 (真实执行)
- **agent.io 统一命令协议**: `AgentCommand` 信封 (@cmd name key=value 行协议, 百分号转义手写编解码 — 零依赖 AOT 安全) + `AgentCommandWriter/Reader`; AgentReportReaderBase 加 Command 事件分类
- **三种传输**: Console.IO / 共享内存 (文件-backed mmap 环形区, 背压可见) / TCP Socket (跨机)
- **LogRouter 双通道**: thinking/输出指令同时镜像 IChatboxSink + @cmd
- **SkillScriptRunner**: SKILL.md 包 scripts/ 真进程调度 (python/bash/node PATH 探测; cwd=包目录沙箱; 环境变量白名单; 超时杀进程树; 脚本 @cmd → AgentCommandWriter 转发)
- **SkillDispatcher 接线**: executive 无显式 entry → 包脚本自动执行
- **性能修复 (sync-over-async 清剿)**: ModelQueueRouter.OnTransientFailure → async 链; TriggerMatcher.MatchAsync; ContextGradientCompressor.CompressCoreAsync
- **模型目录 6 → 18**: +Anthropic/Google/xAI/Moonshot/Qwen/DeepSeek v3.2/OpenAI/GLM-4.5 — 全部公开牌价, /model verify 可校验

### 📊 基线
- 测试: **351/351 全绿** (+10: 命令协议 6 + 脚本执行 4)
- AOT: publish 0 IL 警; /model list 18 模型真机确认

---

## v0.10.0 (2026-09-06) — Yamlify 换库 + Token 统计/余额联动 + Skill 语义

### ✅ 完成记录 (全部真实执行)
1. **YAML 解析换 Yamlify 1.8.0** (MiniYaml 重写为门面): AOT 零 IL 警; `TryGetTopLevel` 修复顶层列表键真 bug; API 签名不变 → 5 消费者零改动
2. **Token 使用统计 + 余额联动** (TokenUsageService): 真实 API 同步 → 本地累计 → 阈值再同步; 余额不足切模 + flags 提示; `/token stats` 全 JSON
3. **Skill P3 语义匹配接 bge** (TriggerMatcher): 词面全未命中 → bge 余弦 ≥0.45 疑似判定; 失败静默回退词面
4. **官方端点可配置代理** + **统一输出收口** (host 8 处 Console → IOutputSink; 库内零 Console 直写) + **/forecast 指令** + **/model list 序号选择** + **LocalLlamaCaller DI 修复** + **版本号统一 15 csproj → 0.10.0**

### 📊 基线
- 测试: **341/341 全绿**; NativeAOT publish 0 IL 警 (agenthost 12MB ELF); AOT 冒烟 4 项通过; GitHub 推送 387bfb1

---

## 历史遗留 (v7.x — v0.x 前身版本号体系)

> 以下为 v0.x 统一编号前的历史记录, 原文保留; 详情见 git log 与 docs/changelogs/CHANGELOG-v7.14.md。

### v7.15 (2026-09-05) — 十节点全落地
十节点: ①Skill 调度 P1 ②模型队列与意图选模 ③日志四通道 ④上下文梯度压缩 ⑤影子计划 ⑥问询打通 ⑦会话恢复 ⑧公开配置读写 ⑨agent.io 协议库 ⑩能力插件接口。需求四项: ①官方通道混合调度 ②agent.io ③会话中断恢复 ④公开配置读写。基线: 276→325 测试全绿 / AOT 0 IL 警 / 双冒烟通过。

### v7.14 (2026-09-05)
EvidenceGate→ClarificationBatch 接入 V2 主链 / vulkan setenv 双写 / SessionMemory 滚动 / AgentProfile 动态学习 / CapabilityScanner 重构 / 目标锚免压缩 / 面板全 JSON。基线 218/218。
