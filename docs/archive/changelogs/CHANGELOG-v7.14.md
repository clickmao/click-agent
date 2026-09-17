# v7.14 变更说明 (Evidence 问询闭环 × 会话记忆 × Agent 画像 × 能力探嗅 × 面板 JSON)

## ① EvidenceGate 裁定 → ClarificationBatch 真实问询
- `IndustrialAgentV2.OnProcessAsync` 步骤 1.5: 低置信子任务过 `EvidenceGate.Evaluate`,
  `ToAsk` 组逐组调 `ClarificationBatch.AskAsync` — CLI REPL 批量弹问题, 答案并入本轮任务描述。
- 答案回写偏好库 (只记模式, 绝不记凭据/原值); 问询链故障降级为直接执行, 不阻断。
- `IUserPromptService` 为可选构造参数, DI 未注册时跳过 (编排可独立测试)。

## ② GGML_VK_VISIBLE_DEVICES 自动设置 (真机判决修复)
- 发现: .NET `Environment.SetEnvironmentVariable` 只写托管 env block, **native getenv 读不到**
  (判决实验: libc getenv 返回 null) → v7.13.1 的进程内自动设置实际未生效 (外部 export 才有效)。
- 修复: `NativeEnv.Set` = libc `setenv` + 托管双写; 用户显式设置过不覆盖。
- 真机复验: unset 场景 `ggml_vulkan: Found 1 Vulkan devices` → offload → `VULKAN_E2E_OK`。

## ③ 会话长期记忆 + 任务目标画像
- `SessionMemory`: 滚动摘要 (默认 ≤1000 字符, 构造可调, 硬上限 10000), 目标条目最后裁;
  `GoalProfile` = 目标文本 + 关键实体 + 约束 + 里程碑; 写入前 `MemorySanitizer.StripSecrets` 净化。
- `JsonSessionMemoryStore`: `data/sessions/<sid>_memory.json` 落盘 (source-gen, AOT 安全)。
- 全链路闭环: V2 每轮 7.5 回写 (目标锚定首轮任务 + 轮次摘要 + 成功记里程碑) → 下一轮
  AssembleContextAsync 预渲染 `RenderForPrompt` 注入 (`DataSourceType.SessionMemory`, 相关性 0.95)。

## ④ AgentProfile (agent 任务处理倾向)
- 静态声明 (决策风格/输出风格/最大重试/先问询) + 动态学习 (任务类别胜率 + 工具亲和)。
- `AgentProfileStore` (`data/agent_profiles.json`) 落盘; V2 轮末自动 `RecordTaskOutcome` 回写。
- 注入上下文 (`DataSourceType.AgentContext`, 相关性 0.9), 与用户级 TendencyProfile 互补。

## ⑤ CapabilityScanner (skill/tools 自动探嗅)
- PATH + 常见安装目录 (~/.dotnet 等) 扫描, 幂等; 渲染为"可用工具清单"注入 Agent 上下文。

## ⑥ 上下文压缩优化 (③④驱动)
- 目标锚免压缩: SessionMemory/AgentContext 块跳过 CompressSnippetsAsync (自控体积, 压缩破坏结构)。
- PromptHeader: 数据源 3→5 席, pinned 源恒入选且不 200-token 截断 — 方向锚不因预算被挤掉。

## 面板 JSON 化 (程序可解析)
- `/status` 全局; `/status <agent_uid>` 画像+记忆+上下文长度; `/session <uid>` 会话数+摘要;
  `/session <uid> <index>` 指定会话详情 (含落盘兜底与索引越界结构化报错)。全部格式化 JSON。
- `/status <uid>` 记忆按该 uid 全部落盘会话聚合 (最近更新为主显示)。

## 基线
- 构建 0 错 0 警 (no-incremental); 测试 218/218 (206+12 新增 V714FeatureTests);
  AOT publish 0 IL 警告; vulkan 探针 VULKAN_E2E_OK (进程内自动 env 设置)。
