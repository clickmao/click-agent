using System.Collections.Generic;

namespace agent.r1;

/// <summary>
/// R1 管道 · 公开用例回放结果（证据面）。
///
/// <see cref="Ran"/>=false 只表示「本次没跑」（题面抽不出用例 / 沙箱不存在 / 零写盘 / 开关关闭），
/// 与「跑了且全过」严格分开 —— 前者禁当通过证据（缺项不得冒充零失败）。
///
/// R545: <see cref="TriggerRc"/> = 触发本次回放时的**执行器出口 rc**（-1 = 未触发）。
/// 它是「触发面已从 `rc==0` 扩到全部产物在盘出口」的机读证据：同一字段族里
/// `ran=1 ∧ trigger_rc=5` 即证明旧触发面外的出口真被覆盖（R544 预注册 J1 的修法）。
/// 注意它记的是**触发那一刻**的值：链的后置升级（如 rc=5→8 self_test_unmet）发生在其后。
/// </summary>
public sealed record PublicProbeResult(
    bool Ran,
    string Reason,
    int Total,
    int Failed,
    IReadOnlyList<string> Failures,
    int TriggerRc = -1)
{
    public static PublicProbeResult Skipped(string reason, int triggerRc = -1) =>
        new(false, reason, 0, 0, new List<string>(), triggerRc);

    /// <summary>台账/回复标记用的单行 JSON（手写，AOT 无反射）。</summary>
    public string MarkerJson()
    {
        var sb = new System.Text.StringBuilder(128);
        sb.Append("{\"ran\":").Append(Ran ? "true" : "false");
        sb.Append(",\"reason\":").Append(R1Json.Quote(Reason));
        sb.Append(",\"total\":").Append(R1Json.Num(Total));
        sb.Append(",\"failed\":").Append(R1Json.Num(Failed));
        sb.Append(",\"trigger_rc\":").Append(R1Json.Num(TriggerRc));
        sb.Append(",\"correctness_asserted\":").Append(Ran && Failed == 0 ? "1" : "0");
        sb.Append('}');
        return sb.ToString();
    }
}
