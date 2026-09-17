namespace agent.recall;


/// <summary>词表二级跳表条目: 常驻内存的只有这些 (每 stride 个 term 一条)。</summary>
public sealed class RecallTermTop
{
    public required long Offset { get; init; }
    public required byte[] Term { get; init; }
}
