using Microsoft.Extensions.Logging;
using agent.core;
using agent.workspace;
using agent.codegen;
using agent.recovery;
using agent.vectormemory;
using agent.memory;
using agent.templates;
using agent.search;
using agent.subagent;
using agent.session;
using agent.userinteraction;
using agent.context;
using agent.rag;
using agent.tendency;
using agent.tokencompression;
using agent.registry;

using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text;

using agent.intent;

namespace agent;


/// <summary>
/// 改进版工业Agent - 真正将上下文注入到 LLM Prompt
/// 
/// 核心改进：
/// 1. 使用 PromptBuilder 构建真正发给 LLM 的 Prompt
/// 2. 上下文被整合到 System Prompt 中，而非只是展示
/// 3. 支持带历史的对话 Prompt
/// </summary>
/// <summary>
/// R379: 缓存前缀治理 — 会话 → (冻结的系统提示, 冻结时意图)。
/// messages[0] 必须会话内恒定字节, 否则 provider 的缓存前缀自字节 0 失配。
/// </summary>
public sealed class FrozenSystemPromptTable
{
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, (string Prompt, string Intent)> _map =
        new(StringComparer.Ordinal);

    public int Count => _map.Count;
    public void Clear() => _map.Clear();

    public (string Prompt, string Intent) GetOrAdd(string sessionId, (string Prompt, string Intent) seed)
        => _map.GetOrAdd(sessionId, seed);

    public bool TryGet(string sessionId, out (string Prompt, string Intent) value)
        => _map.TryGetValue(sessionId, out value);

    public void Set(string sessionId, (string Prompt, string Intent) value) => _map[sessionId] = value;
}
