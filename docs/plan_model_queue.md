# 子模块开发计划: 模型队列 (Model Queue) + Token 余额查询

> 独立计划文档 — 阅读本文件即可开发, 不需加载全部项目上下文。
> 状态: 待开发 (v7.15 候选) · 前置基线: v7.14 (`953efef`)
>
> **半成品核查结论 (2026-09-06)**: 代码库中**无任何模型队列实现** —
> 工作树无 modelqueue 目录; `OpenAILLMCaller` (IndustrialAgentV2.cs 606) 的 model
> 为构造参数默认值 `"gpt-4"` 写死, DI 注册单例单模型; `LocalCommandRouter.Known`
> 无余额指令。本模块从零开始, 无返工。

---

## C.1 需求 (用户原话拆解)
### C.1.1 需求2 原文 (2026-09-06 补充, 逐字 — 意图选模)
"关于'自动'选择LLM时，应根据其意图选择不同模型，有的适合flash版本有的适合全量版，再用户填写模型配置时应该标注推理和编码任务能力，然后'自动'选择根据意图来预估总任务周期（大概会消费多少token)、和需要的推理能力以及配置内模型预估费用做综合判断选择使用哪个模型， ①【推理能力】需要一个标准值 ②需要一个基础配置覆盖大部分知名模型，并填入除了API-KEY 以外的参数，如模型名称、API请求地址，余额查询配置【注意该配置与/balance指令相关，不同模型提供商可能查询方案不同，需要总结后再设计该配置方案，如果全部都一致则不需要】，预估费用，推理能力，适合用途等，这些都将成为选择使用哪个模型的依据 ③添加的模型默认参数一定是要真实正确的，这个可以通过网络搜索并一定要做实际http请求校验是否合法，测试合法性的时候api-key可以随意填写，应该会返回失败状态也可以校验地址是否正确"
1. **单独写一个模块** — 不塞进 IndustrialAgentV2, 独立目录 `src/agent/modelqueue/`
2. **可用模型队列可配置, 本地 JSON config 储存** — `data/config/model_queue.json`
3. **分主/次模型** — Primary / Secondary 分级
4. **手动选择** — 用户可指定执行 agent 所用模型
5. **自动模式** — 先用主模型, 连续多次失败 → 自动切副模型
6. **计价策略路由** — 对模型性能差异不敏感的功能 (如上下文压缩) 自动先用价格便宜的模型
7. **新增本地指令: 查询 token 账户余额** — 输出 JSON (延续面板全 JSON 惯例)

## C.2 现状 (代码事实 — 开发前必读)
| 事实 | 位置 |
|---|---|
| LLM 调用接口 `ILLMCaller.CallAsync(Prompt) → LLMResponse` | IndustrialAgentV2.cs 540-546 |
| `OpenAILLMCaller`, model 构造默认 `"gpt-4"` 写死, 单例注册 | IndustrialAgentV2.cs 606-628; agent/Program.cs 97-109 |
| NullLLMCaller 兜底 (无 key 时) | agent/Program.cs 109 |
| DI 注册点 (要改成队列路由器) | agent/Program.cs 97 + extensions/ServiceCollectionExtensions.cs |
| 本地指令路由 `LocalCommandRouter.TryRoute`, Known 集合 | registry/LocalCommandResult.cs 33-36 |
| CLI 命令分流 (PanelDataService JSON 输出模式) | agent.host/Program.cs 108-129 |
| 宿主 Key 走 `AGENT_OPENAI_KEY` 环境变量 | agent/Program.cs (DI lambda 内) |
| 上下文压缩调用方 (计价路由的第一客户) | ContextAssembler.CompressSnippetsAsync |

## C.3 模块设计

### C.3.1 目录与文件 (独立模块, 命名空间 `agent.modelqueue`)
```
src/agent/modelqueue/
  ModelQueueConfig.cs      — 配置模型 + JSON 加载/保存 (source-gen, AOT)
  ModelQueueRouter.cs      — 核心路由器: ILLMCaller 实现, 内部持有多 caller
  ModelSelectionPolicy.cs  — 手动/自动/计价 三策略
  BalanceQueryService.cs   — 余额查询 (OpenAI 兼容 /dashboard/billing 或 /v1/dashboard)
```

### C.3.2 配置文件 (本地 JSON, `data/config/model_queue.json`)

> **⚠ v7.15 更新**: 《全模块 YAML 配置开发规范》(见 plan_yaml_config.md) 生效后, 本配置改存
> `config/base/model_queue.yaml` (L1) + `config/modules/model_queue.yaml` (L3 同名覆盖),
> 读取走 ConfigSnapshot 分层契约 — 下述 JSON 结构仅保留为字段语义参考, 载体格式以 YAML 规范为准。
```jsonc
{
  "activeProfile": "default",
  "manualOverride": null,                // 手动模式: 直接指定模型 id (如 "deepseek-v3"), null=自动
  "primary": {
    "id": "gpt-4o-mini",
    "baseUrl": "https://api.openai.com/v1",
    "apiKeyEnv": "AGENT_OPENAI_KEY",     // 只存环境变量名, 永不存 key 本体 (v7.13 铁律)
    "maxConsecutiveFailures": 3,         // 连续失败 N 次切副模型
    "pricePer1kInput": 0.15,             // USD, 计价路由用
    "pricePer1kOutput": 0.60
  },
  "secondary": {
    "id": "deepseek-chat",
    "baseUrl": "https://api.deepseek.com/v1",
    "apiKeyEnv": "DEEPSEEK_KEY",
    "pricePer1kInput": 0.014,
    "pricePer1kOutput": 0.028
  },
  "cheapModelForLowSensitivity": {       // 计价策略路由 (C.3.4)
    "enabled": true,
    "preferSecondaryFor": ["context_compression", "keyword_tagging", "tendency_analysis"]
  }
}
```
- 加载失败/字段缺失 → 全部回退默认值 + 告警日志, 不抛异常 (配置坏不阻断对话)
- 保存时机: `/model` 切换指令写入 manualOverride 时

### C.3.3 路由器 (ModelQueueRouter : ILLMCaller)
```
CallAsync(prompt, ct):
    model = SelectModel(taskKind)            // 三策略见 C.3.4
    caller  = ResolveCaller(model)           // 懒建 OpenAILLMCaller (per baseUrl+key 缓存)
    try:
        resp = await caller.CallAsync(prompt, ct)
        RecordSuccess(model); return resp
    catch transient:
        RecordFailure(model)
        if 连续失败 ≥ maxConsecutiveFailures && 当前是 primary:
            切 secondary (告警日志 + 切换事件记 TaskPlanRun 审计)
            return await secondary.CallAsync(prompt, ct)
        throw
```
- **失败判定边界**: OperationCanceledException 永不触发切换 (用户取消≠模型故障)
- **切换粘性**: 切到 secondary 后持续用 secondary, 直到手动 `/model` 重置或 primary 探活恢复
  (每 N 次成功后试发一次探活, 可配, 默认关)
- DI: `services.AddSingleton<ILLMCaller>(sp => new ModelQueueRouter(...))` —
  消费方 (V2/ContextAssembler) 零改动, 接口不变

### C.3.4 模型选择三策略 (ModelSelectionPolicy)
```
SelectModel(taskKind):
    1. manualOverride 非空 → 直接用 (手动模式最高优先)
    2. taskKind ∈ preferSecondaryFor 且 enabled → secondary (计价策略:
       上下文压缩/关键词标注/倾向分析等"性能差异不敏感"功能用便宜模型)
    3. 否则 → 当前主模型 (自动模式含失败切换粘性)
```
- taskKind 来源: `TaskKindHint` — V2 主回答 = general;
  ContextAssembler 压缩调用时传 context_compression (需给 Prompt 加可选元数据字段或方法重载)

### C.3.5 余额查询指令 (双通道, 延续全 JSON 惯例)
- `LocalCommandRouter.Known` 增 `/balance`; CLI Program.cs 增同名单独分流
- `BalanceQueryService`: 调当前主模型 baseUrl 的账单端点, 响应 →
  `{"command":"balance","ok":true,"model":"gpt-4o-mini","total_granted":...,"total_used":...,"total_remaining":...}`
  - 非 OpenAI 兼容端点 (404/401) → `{"ok":false,"error":"provider_not_supported","model":...}` 诚实报错, 不编造数字
  - 响应 10s 超时; 失败不阻断 REPL
- **凭据零落盘**: key 只从 `apiKeyEnv` 指向的环境变量读, 与偏好库铁律一致

## C.4 验收标准
- [ ] 配置往返: 写 model_queue.json → Router 加载 → 主/次/价格字段全对; 坏 JSON → 默认值+告警不抛
- [ ] 自动切换: primary 连续 3 败 (mock caller) → 副模型接手, 审计记录切换事件
- [ ] 手动模式: `/model deepseek-chat` → 后续全部走该模型; `/model auto` 恢复
- [ ] 计价路由: 压缩类调用 (taskKind=context_compression) 走 secondary, 主回答走 primary
- [ ] `/balance` 双通道 JSON 输出可被 JsonDocument.Parse; 不支持端点诚实报错
- [ ] 取消永不触发模型切换
- [ ] 全量测试绿 + AOT 0 警 (source-gen JSON, 无反射)

## C.5 明确排除 (不做)
- 不做模型自动探活轮询 (默认关, 手动 /model 重置即可)
- 不做多模型并发竞速 (单队列主备即可, 竞速是 token 浪费)
- 不存任何 API key 到配置文件/代码 (只存环境变量名)

## C.6 模型目录与意图选模 (需求2 落地设计)
### C.6.1 推理能力标准值 (①)
- 统一量纲 `ReasoningScore`: 1-10 整数档 (10=最强推理), 另配 `CodingScore` 1-10 (用户原话: "标注推理和编码任务能力")
- 定档依据: 公开评测基准 (如 LMSYS Arena / MMLU / SWE-bench 公开数据) 归一化到 1-10; 目录中每个模型标注依据来源
### C.6.2 模型目录 (基础配置覆盖知名模型 — ②)
```yaml
# config/base/models.yaml — 每模型: 除 API-KEY 外全部参数 (key 只存环境变量名, 凭据铁律)
models:
  - id: gpt-4o
    provider: openai
    endpoint: https://api.openai.com/v1/chat/completions
    api_key_env: AGENT_OPENAI_KEY
    price_in_per_m: 2.50        # 每百万输入 token (USD)
    price_out_per_m: 10.00
    reasoning_score: 8          # C.6.1 标准值
    coding_score: 8
    context_window: 128000
    suited_for: [general, coding, reasoning]
    balance:
      scheme: openai            # 余额查询方案标识 (C.6.4)
      endpoint: https://api.openai.com/v1/dashboard/billing/credit_grants
  - id: glm-4-flash
    provider: zhipu
    endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
    reasoning_score: 5
    suited_for: [chat, summary, classify]   # flash 适合轻意图
```
- 目录 = "自动"选模的候选池; /model 手动指定 id 直用 (绕过自动)
### C.6.3 意图选模算法 (综合判断)
1. 输入: 意图 (IntentDecomposer 已产出) + 预估 token (Prompt.EstimatedTokens 已有) + 目录候选
2. 打分: `score = fitness(意图×suited_for) × w1 + reasoning_needed(意图) 匹配 × w2 - 预估费用 × w3`
   - 推理重意图 (planning/debug) → 高 reasoning_score 模型; 轻意图 (闲聊/摘要/分类) → flash 便宜模型
   - 预估总周期费用 = EstimatedTokens × price_in + 预估输出 × price_out
3. 主/次模型与 C.3 队列分级合一: 自动选中 = 主, 同 provider 更强者 = fallback 次
4. 选模结果入日志 (LogEntry, 通道 system) 与 /status JSON
### C.6.4 余额查询方案差异 (② /balance 前置调研 — 结论驱动设计)
- 先网络调研各 provider 余额接口: OpenAI(credit_grants)/DeepSeek(user/balance)/智普(open.bigmodel.cn)/Anthropic(admin api)…
- 若差异大 → balance.scheme 枚举 (openai/deepseek/zhipu/custom), 每方案一个查询实现
- 若用户确认全部一致 → 目录省略 balance 节, /balance 单一实现 (文档记录该裁定)
### C.6.5 目录真实性校验 (③ — 强制)
- 新增模型默认参数必须真实正确: 网络搜索确认 + **实际 http 请求校验**
- 校验法: 向 endpoint 发最小 chat completions 请求 (max_tokens=1), api-key 随意填 ("sk-invalid-probe") —
  期望 401/403 (地址正确+鉴权拒绝) = 合法; 404/DNS 失败/超时 = 参数错误
- 校验命令 /model verify <id> (JSON 输出), 结果写入目录校验时间戳


---

## C.7 "官方"模型通道与三通道混合调度 (需求1, v7.15 落地)

> 用户原话要点: "官方"模型=硬编码集合**不进 yaml**; api-key 由 CLI 启动参数或专用指令传递
> (指令名未定 → 代拟 `/official-key`, ⚠ 待用户确认); "自动"模式下多任务模型混合调用;
> 并发数可配; 优先级恒 本地 > 官方 > 远端; 子任务按 并发数/推理能力/推理速度/价格 综合选模。

### C.7.1 落点
- `src/agent.modelqueue/OfficialModels.cs`:
  - `OfficialModels.Models` — 硬编码官方模型集合 (official-gpt-4o / official-gpt-4o-mini),
    与目录同构 (`ModelCatalogEntry`) 但 provider="official"、不走 yaml
  - `OfficialKeyStore` — 官方 key 内存仓库 (Set/Get/IsAvailable), 进程退出即销毁, 永不落盘
- `src/agent.modelqueue/ChannelScheduler.cs`:
  - 三通道 (Local/Official/Remote) 并发数托管: `AcquireChannel()` 按优先级遍历, 未达上限即接任务
  - `RankCandidates()` 子任务综合打分: 推理能力 0.4 × 速度 0.3 × 价格 0.3
    (轻任务 kind — KeywordTagging/IntentClassification/ContextCompression/TendencyAnalysis —
    自动加大速度权重 1.5x, 减半推理权重)
- `ModelQueueRouter`:
  - `SetOfficialKey(key)` — 注入并同步官方通道可用性
  - `CallAsync` 选模链: 手动 > 粘性 > `SelectByChannelPriority()` (官方 key 在 → 官方 Rank;
    否则远端目录 Rank)
  - `CallEntryAsync`: provider=="official" → key 取自 `OfficialKeyStore`; 其余 → 环境变量

### C.7.2 传递通道
1. CLI 启动参数: `--official-key <key>` (agent.host/Program.cs 解析 → Router 注入 → 引用即释放)
2. 运行中指令: `/official-key <key>` 注入; `/official-key off` 清除; `/official-key` 查询状态
   (JSON 只回 `official_key_present: true/false`, **不回显 key 本身**)

### C.7.3 通道职责与本地模型
- 本地通道 (LocalLlamaCaller) 由 agent 侧 adapter 直接执行 — 不经 HTTP, 不占远端并发
- 官方/远端经 `CallEntryAsync` HTTP 调用, 并发数由 `ChannelScheduler` 托管
- 子任务分派顺序 (需求1 原文逐条落地):
  1. 本地模型满足推理能力与速度 → 本地跑
  2. 无本地且官方 key 在 → 官方
  3. 其他并行子任务 → 远端 API (目录)
  4. 无远端 → 全由本地/官方兜底

### C.7.4 验收
- [x] 官方模型硬编码不在 yaml (OfficialModels.Models)
- [x] key 仅 CLI/指令传递, 内存态 (OfficialKeyStore; /official-key 查询不回显)
- [x] 三通道并发托管 + 优先级本地>官方>远端 (ChannelScheduler.AcquireChannel)
- [x] 子任务综合选模 (RankCandidates: 并发余量前置 + 能力/速度/价格加权)
- [ ] 真实多通道并发调用 (待多 provider key 环境联调 — 目录 6 模型 verify 已过 4/6)
