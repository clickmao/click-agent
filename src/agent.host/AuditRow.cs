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


/// <summary>audit 矩阵行</summary>
public sealed class AuditRow
{
    public string Level { get; set; } = string.Empty;
    public int BucketTokens { get; set; }
    public int Samples { get; set; }
    public double KeyKeepRate { get; set; }
    public double CausalKeepRate { get; set; }
    public double InstructionKeepRate { get; set; }
    public double CompressRatio { get; set; }
    public long AvgMs { get; set; }
}
