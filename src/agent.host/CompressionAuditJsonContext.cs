using agent.contextgradient;
using System.Text;
using System.Text.Json;
using agent.llamalocal;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using agent.core;
using agent.intent;
using agent.registry;
using agent.session;

namespace agent.host;


/// <summary>AOT source-gen (v0.13.3 audit — 禁反射铁律)</summary>
[System.Text.Json.Serialization.JsonSerializable(typeof(List<GtDoc>))]
[System.Text.Json.Serialization.JsonSerializable(typeof(List<AuditRow>))]
internal sealed partial class CompressionAuditJsonContext : System.Text.Json.Serialization.JsonSerializerContext
{
}
