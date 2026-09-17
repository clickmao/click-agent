using agent.session;
using Microsoft.Extensions.Logging;

namespace agent.subagent;


/// <summary>隔离执行专用 LLM 端口 — 与主链 ILLMCaller 同签名; DI 绑定同一实现但隔离器绕过 V2 会话状态。</summary>
public interface ILLMCallerForIsolated
{
    Task<LLMResponse> CallAsync(agent.templates.Prompt prompt, CancellationToken ct = default);
}
