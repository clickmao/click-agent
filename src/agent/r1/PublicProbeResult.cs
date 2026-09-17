using System.Collections.Generic;

namespace agent.r1;

/// <summary>
/// R1 管道 · 公开用例回放结果（证据面）。
///
/// <see cref="Ran"/>=false 只表示「本次没跑」（题面抽不出用例 / 沙箱不存在 / 开关关闭），
/// 与「跑了且全过」严格分开 —— 前者禁当通过证据（缺项不得冒充零失败）。
/// </summary>
public sealed record PublicProbeResult(bool Ran, string Reason, int Total, int Failed, IReadOnlyList<string> Failures)
{
    public static PublicProbeResult Skipped(string reason) =>
        new(false, reason, 0, 0, new List<string>());

    /// <summary>台账/回复标记用的单行 JSON（手写，AOT 无反射）。</summary>
    public string MarkerJson()
    {
        var sb = new System.Text.StringBuilder(128);
        sb.Append("{\"ran\":").Append(Ran ? "true" : "false");
        sb.Append(",\"reason\":").Append(R1Json.Quote(Reason));
        sb.Append(",\"total\":").Append(R1Json.Num(Total));
        sb.Append(",\"failed\":").Append(R1Json.Num(Failed));
        sb.Append(",\"correctness_asserted\":").Append(Ran && Failed == 0 ? "1" : "0");
        sb.Append('}');
        return sb.ToString();
    }
}
