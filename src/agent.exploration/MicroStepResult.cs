namespace agent.exploration;


/// <summary>微步骤执行结果。</summary>
public sealed class MicroStepResult
{
    public string MicroId { get; set; } = string.Empty;
    public bool Ok { get; set; }
    public string Answer { get; set; } = string.Empty;
    public int TokensUsed { get; set; }
    public List<string> SkillHits { get; set; } = new();
    public int Ms { get; set; }
    public string? Error { get; set; }
}
