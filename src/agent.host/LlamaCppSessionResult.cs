using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;
using agent.modelqueue;

namespace agent.host;


/// <summary>R411 会话汇总（判据: ①长驻 ②跨轮复用 ③比值+绝对长度双条件不越线）。</summary>
public sealed class LlamaCppSessionResult
{
    public string Mode { get; set; } = "session";
    public string SessionId { get; set; } = "";
    public string Model { get; set; } = "";
    public string ReuseMode { get; set; } = "Session";
    public long ProcessStarts { get; set; }
    public long Turns { get; set; }
    public long Observations { get; set; }
    public long Violations { get; set; }
    public long NotApplicable { get; set; }
    /// <summary>弃权次数（命中 &gt; 可复用上限 ⇒ 口径不符，不出判决）。</summary>
    public long Abstained { get; set; }
    /// <summary>非首轮「前缀没被复用」轮次数（>0 = 长驻/前缀稳定任一不成立）。</summary>
    public long CacheMissTurns { get; set; }
    /// <summary>冷启首轮总长（≈ 稳定前缀 + 首轮输入 + 模板开销）。</summary>
    public int SystemTokens { get; set; }
    /// <summary>红线要求的前缀绝对长度（4224）。</summary>
    public int RequiredPrefixTokens { get; set; }
    public double CarryOverReuseLast { get; set; } = -1;
    public double SessionReuseRatioLast { get; set; } = -1;
    public double EffectiveHitRateLast { get; set; } = -1;
    public bool LongLived { get; set; }
    public bool CrossTurnReuse { get; set; }
    public List<LlamaCppSessionTurnResult> TurnResults { get; set; } = [];
}
