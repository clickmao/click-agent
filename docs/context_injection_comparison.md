# AgentFramework 多数据源上下文注入对比报告

## V1 vs V2 核心区别

### V1 (IndustrialAgent.cs) - 有问题

```csharp
// ❌ 问题：上下文只是"展示"，没有注入到 LLM Prompt
var contextResult = await AssembleContextAsync(message, intent, ct);

// 上下文被放在 Metadata 里，只用于日志/调试
response.Metadata["ContextStats"] = new ContextStats { ... };

// Handler 只是读取 context.Snippets，拼接成字符串展示给用户
// 但 LLM 根本看不到这些上下文！
```

**实际效果**：
- 用户问："帮我修改上次写的代码"
- 系统召回："你上次写的代码在 session_123，是关于用户认证的..."
- LLM 收到："帮我修改上次写的代码"
- LLM 回复："请提供要修改的文件路径"
- 用户体验：❌ 很糟糕，LLM 不知道上下文

### V2 (IndustrialAgentV2.cs) - 正确实现

```csharp
// ✅ 正确：上下文被注入到 LLM Prompt
var contextResult = await AssembleContextAsync(message, intent, ct);

// 构建完整 Prompt（包含上下文）
var prompt = _promptBuilder.BuildWithHistory(
    message,           // 当前消息
    contextResult,     // 上下文
    systemPrompt,      // 系统指令
    history            // 对话历史
);

// 调用 LLM 时传入完整 Prompt
var llmResponse = await _llmCaller.CallAsync(prompt, ct);
```

**Prompt 结构**：
```
=== SYSTEM PROMPT ===
你是一个代码修改专家。请根据用户需求和相关上下文修改代码。

注意：
1. 参考上下文中提供的代码风格和模式
2. 保持与现有代码的一致性
...

=== CONTEXT ===
你上次写的代码（Session History）：
[Session]
[User]: 帮我写一个用户认证模块
[Assistant]: 已创建 UserAuth.cs，包含登录、注册等功能

相关记忆（Memory）：
[Memory]
上次认证模块使用 JWT token，有效期7天...

=== CONVERSATION HISTORY ===
[User]: 能改成永久登录吗？
[Assistant]: 可以，需要修改 token 过期逻辑...

=== CURRENT REQUEST ===
[User]: 帮我修改上次写的代码
```

**实际效果**：
- 用户问："帮我修改上次写的代码"
- LLM 收到：完整上下文（上次写的代码内容、历史对话、相关记忆）
- LLM 回复："好的，我来修改你上次的用户认证模块..."
- 用户体验：✅ 流畅，LLM 完全知道上下文

---

## 关键改进点

| 问题 | V1 | V2 |
|------|-----|-----|
| 上下文注入 | ❌ 只展示，不注入 | ✅ 真正注入 Prompt |
| LLM 调用 | ❌ 直接返回文本 | ✅ 传入完整 Prompt |
| 历史对话 | ❌ 不传给 LLM | ✅ 传入最近对话 |
| 意图模板 | ❌ 无 | ✅ 意图特定 System Prompt |

---

## 使用建议

### 短期：修复 V1

如果暂时不想迁移到 V2，可以在 V1 的 Handler 中直接构建 Prompt：

```csharp
// 在 Handler 中构建 Prompt 并传给 LLM
var prompt = BuildPromptFromContext(message, context);
var llmResponse = await _llmCaller.CallAsync(prompt, ct);
```

### 长期：使用 V2

V2 是更干净的实现，推荐迁移：

1. 实现 `ILLMCaller` 接口（对接你的 LLM 提供商）
2. 配置 DI：`services.AddSingleton<ILLMCaller, YourLLMCaller>()`
3. 替换 `IndustrialAgent` 为 `IndustrialAgentV2`

---

## 下一步优化方向

1. **缓存层**：避免重复调用 LLM
2. **流式输出**：支持流式响应
3. **多轮对话优化**：更智能地选择哪些历史传给 LLM
4. **上下文质量评估**：自动评估召回的上下文是否有帮助
