using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.vectormemory;


/// <summary>
/// 记忆整合配置
/// </summary>
public class ConsolidationConfig
{
    public int MaxEntries { get; set; } = 10000;
    public int ConsolidationThreshold { get; set; } = 100;
    public TimeSpan ConsolidationInterval { get; set; } = TimeSpan.FromHours(1);
    public double SimilarityThreshold { get; set; } = 0.95;
}
