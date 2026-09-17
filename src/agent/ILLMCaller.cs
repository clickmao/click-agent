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
/// LLM 调用器接口
/// </summary>
public interface ILLMCaller
{
    /// <summary>
    /// 调用 LLM
    /// </summary>
    Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default);
}
