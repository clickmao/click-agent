namespace agent.exploration;


/// <summary>R449: 库形状快照 (只读; 供普查/遥测 — 不含内容)。</summary>
public sealed class ThinkMemoryShape
{
    public int Count { get; set; }
    public int Negative { get; set; }
    public int Unbacked { get; set; }
    public int ZeroDim { get; set; }
    public int HitPositive { get; set; }
    public int RefHitPositive { get; set; }
    public string Dimensions { get; set; } = string.Empty;
    public string Mode { get; set; } = "on";
}
