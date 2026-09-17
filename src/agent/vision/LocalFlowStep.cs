namespace agent.vision;

/// <summary>
/// 本地视觉模型返回的**单步操作**（供 agent 侧确定性执行器消费）。
/// 坐标系: box_2d 为归一化整数 [0,1000]（x/width*1000, y/height*1000），换算像素 = v/1000*尺寸。
/// </summary>
public sealed record LocalFlowStep(string Op, string Target, int[] Box, string Text, string Verify)
{
    /// <summary>合法 op 白名单（与渲染进本地视觉 prompt 的枚举逐字一致）。</summary>
    public static readonly string[] Ops = { "click", "type", "key", "scroll", "wait", "assert" };

    /// <summary>需要 box 的 op（其余 op 带 box 视为违规 ⇒ 拒收）。</summary>
    public static readonly string[] BoxOps = { "click", "type", "scroll" };

    public static bool IsOp(string? v)
    {
        foreach (var o in Ops)
        {
            if (o == v)
            {
                return true;
            }
        }
        return false;
    }

    public static bool NeedsBox(string? v)
    {
        foreach (var o in BoxOps)
        {
            if (o == v)
            {
                return true;
            }
        }
        return false;
    }
}
