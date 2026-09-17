using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.config;
using agent.registry;
using agent.skills;

namespace agent.intent;


/// <summary>
/// 计划事件出站口 (v0.22.0 exp9 D5)。核心层只依赖这个接口; 具体信封与传输由宿主接
/// (host: `FrontendApiContract.FormatEvent` + `FrontendEventHub`)。
///
/// 契约: 实现方抛异常**不得**打断计划 (PlanRunner 仍会兜底), 也不得阻塞主链。
/// </summary>
public interface IPlanEventSink
{
    Task EmitAsync(string @event, string payloadJson, CancellationToken ct = default);
}
