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
