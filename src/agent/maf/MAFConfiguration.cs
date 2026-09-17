using Microsoft.Extensions.Logging;
using System.Net.Http.Json;

namespace agent.maf;

/// <summary>
/// MAF配置
/// </summary>
public class MAFConfiguration
{
    public string Endpoint { get; set; } = "http://localhost:5000";
    public string? ApiKey { get; set; }
    public int MaxRetries { get; set; } = 3;
    public int RetryDelayMs { get; set; } = 1000;
    public int TimeoutMs { get; set; } = 30000;
    public bool Enabled { get; set; } = true;
}
