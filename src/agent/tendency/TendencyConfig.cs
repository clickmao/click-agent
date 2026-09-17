namespace agent.tendency;


/// <summary>
/// 倾向配置
/// </summary>
public class TendencyConfig
{
    public double DecayFactor { get; set; } = 0.95; // 旧数据衰减
    public int MinSampleSize { get; set; } = 10;
    public int MaxHistorySize { get; set; } = 100;
    public TimeSpan DataRetention { get; set; } = TimeSpan.FromDays(30);
}
