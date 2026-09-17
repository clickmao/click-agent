namespace agent.modelqueue;


/// <summary>通道运行时状态 (并发计数 + 可用性)</summary>
public sealed class ChannelState
{
    public ModelChannel Channel { get; init; }
    public int Running { get; set; }

    /// <summary>通道可用 (远端 = 目录非空)</summary>
    public bool Available { get; set; }
}
