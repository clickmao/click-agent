using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>路由判定结果 (纯函数输出; 可单测)</summary>
public sealed record RouteDecision(NodeExecutionLocation Location, string? ExecutorId, string Hint);
