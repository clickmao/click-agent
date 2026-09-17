namespace agent.exploration;


/// <summary>修复单步结果 (打点 format_repair 源数据)。</summary>
public sealed class FormatRepairStep
{
    public string Stage { get; set; } = string.Empty;   // fenced|found|validate|local_fix|llm_round
    public bool Ok { get; set; }
    public int RoundsN { get; set; }
    public int ChangedN { get; set; }
    public string? Error { get; set; }
}
