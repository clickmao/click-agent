// v0.22.0 exp9 D5: 计划事件 → 前端信封 (宿主侧适配器)
//
// 分层: 核心层 (agent.intent) 只认 IPlanEventSink, 不认识前端信封/传输。
//      宿主知道 FrontendApiContract + FrontendEventHub, 所以信封拼装放在这里。
// AOT: 载荷是 PlanRunner 手写的 JSON 片段, 由 FormatEvent 用 WriteRawValue 原样嵌入 — 零反射/零序列化器。
// 诚实边界: 只有 --frontend-api 模式才有前端连接; 无连接时 EmitAsync 只累加丢弃计数 (非静默失败)。

namespace agent.host;

/// <summary>把核心层的计划事件包成前端信封 (type=event) 并投递到出站枢纽。</summary>
internal sealed class PlanEventEnvelopeSink : agent.intent.IPlanEventSink
{
    private readonly agent.frontendapi.FrontendEventHub _hub;

    public PlanEventEnvelopeSink(agent.frontendapi.FrontendEventHub hub) => _hub = hub;

    public async Task EmitAsync(string @event, string payloadJson, CancellationToken ct = default)
    {
        // 注: hub.EmitAsync 自身永不抛、未挂接即计丢弃 (非阻塞) —— 这里再加一层 ct 检查只为早退。
        ct.ThrowIfCancellationRequested();
        var envelope = Wrap(@event, payloadJson);
        await _hub.EmitAsync(envelope).ConfigureAwait(false);
    }

    /// <summary>信封 = 前端契约的唯一拼装入口 (单一事实源, 不在这里另写一份格式)</summary>
    internal static string Wrap(string @event, string payloadJson) =>
        agent.frontendapi.FrontendApiContract.FormatEvent(
            @event, string.IsNullOrWhiteSpace(payloadJson) ? "{}" : payloadJson);
}
