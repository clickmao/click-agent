using System;

namespace agent.modelqueue;

/// <summary>
/// R491 回放配对剪裁闸 (env <c>AGENTFRAMEWORK_REPLAY_PAIR_TRIM</c>)。
///
/// 语义: R490 只把「本地模板答复」(零远端调用 Skip 轮的产物) 剔出远端回放 (assistant 侧缺口已补)。
/// 该轮的 **user 侧** 同样从未随任何远端请求发出过 —— 留在回放里只会造成 user→user 相邻
/// (上游把两段用户文本当成一轮的新输入) + 逐轮白付 token。
///
/// 闸默认 **关** ⇒ 回放面与 R490/R489 逐字节相同 (零回归); 只有显式置位才做配对剪裁。
/// 判据全部来自产品自身常量 (<see cref="ModelQueueRouter.LocalSkipFallback"/>), 不吃关键词表 (R458 铁律)。
/// </summary>
public static class ReplayPairTrim
{
    public const string EnvName = "AGENTFRAMEWORK_REPLAY_PAIR_TRIM";

    /// <summary>闸是否开启。取值 "1"/"true"(忽略大小写) 为开; 其余 (含未设/空) 为关。</summary>
    public static bool IsEnabled() => Decide(Environment.GetEnvironmentVariable(EnvName));

    /// <summary>取值判别 (单一事实源, 判据表直接消费)。</summary>
    public static bool Decide(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return false;
        var v = value.Trim();
        return v == "1" || string.Equals(v, "true", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>打点值 (0/1), 便于逐调用机检门态。</summary>
    public static string Stamp() => IsEnabled() ? "1" : "0";
}
