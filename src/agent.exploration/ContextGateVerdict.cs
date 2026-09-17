using System.Text.Json;

namespace agent.exploration;


public sealed class ContextGateVerdict
{
    public ContextGateMode Mode { get; set; }
    public int EstimatedTokens { get; set; }
    public int WarnThreshold { get; set; }
    public int HardThreshold { get; set; }
    public string Reason { get; set; } = string.Empty;
}
