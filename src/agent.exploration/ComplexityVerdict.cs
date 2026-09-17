namespace agent.exploration;


/// <summary>
/// v0.13.0 T3 M-A — 复杂度门: 判定是否展开思考链+探索 (用户钦定任务3 ①②)。
/// 纯逻辑可打点; 简单题直答省 token, 复杂题才展开。
/// </summary>
public sealed class ComplexityVerdict
{
    public bool IsComplex { get; set; }
    public int Score { get; set; }
    public List<string> Triggers { get; set; } = new();
}
