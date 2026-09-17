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
/// 空 LLM 调用器（未配置 API Key 时的 fallback）
/// 返回明确的提示而不是抛异常，保证 DI 图完整、程序可启动
/// </summary>
public class NullLLMCaller : ILLMCaller
{
    public Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
    {
        var response = new LLMResponse
        {
            Success = false,
            Content = string.Empty,
            Error = "LLM 未配置: 请设置环境变量 AGENT_OPENAI_KEY (或在 config/base/core.yaml 的 openai.api_key_env 指定变量名) 后重启。",
            Model = "none",
            TokensUsed = 0,
            LatencyMs = 0,
            Timestamp = DateTime.UtcNow
        };
        return Task.FromResult(response);
    }
}
