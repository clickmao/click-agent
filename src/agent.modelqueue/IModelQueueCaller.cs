using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;


/// <summary>模型队列调用端口 (adapter 在 agent 主程序集实现 ILLMCaller 时消费)</summary>
public interface IModelQueueCaller
{
    Task<QueueResponse> CallAsync(QueuePrompt prompt, TaskKindHint kind, string intent, CancellationToken ct = default);
}
