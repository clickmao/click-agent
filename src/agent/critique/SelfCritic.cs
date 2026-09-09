using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.critique;

/// <summary>
/// v0.14.0 T2a (SelfCritic): LLM 自审调用器 — 评审反馈显式化的 LLM 实现 (用户钦定方向)。
/// 定位: 候选反馈源 (非已确认修法) — 产出必须过 Anchor 校验才入库。
/// 防幻觉锚: critique.quote 必须是原文逐字子串 (后处理校验, 不匹配即丢弃)。
/// AOT: STJ source-gen 上下文 (见 SelfCriticJson), 零反射。
/// </summary>
public static class SelfCritic
{
    public sealed record CandidateCritique(string Quote, string Mechanism, string Severity, string FixHint);

    public sealed record CritiqueResult(IReadOnlyList<CandidateCritique> Valid, int Rejected, int RawCount);

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    /// <summary>构建 critic 请求消息 (system 风格单轮)。checklist 传概念版反模式 (R01-R08 文案)。</summary>
    public static string BuildPrompt(string output, string domain, IEnumerable<string> antipatternChecklist)
    {
        var sb = new StringBuilder();
        sb.Append("你是代码评审员。审查下面这段输出中的代码, 找出【确定的、可解释机制的】改进点。\n");
        sb.Append("领域: ").Append(domain).Append('\n');
        sb.Append("关注方向 (非穷尽): ").AppendJoin(" / ", antipatternChecklist).Append('\n');
        sb.Append("硬性要求:\n");
        sb.Append("1. 只报你能给出【机制解释】的问题 (为何伤性能/正确性/可维护性) — 无机制解释不要报。\n");
        sb.Append("2. quote 必须是原文逐字子串 (可复制粘贴找到), 20 字符以内。\n");
        sb.Append("3. 宁缺毋滥: 没有确定问题就输出空数组。\n");
        sb.Append("4. 输出 JSON 数组: [{\"quote\":\"...\",\"mechanism\":\"...\",\"severity\":\"high|low\",\"fix_hint\":\"...\"}]\n\n");
        sb.Append("【输出原文开始】\n").Append(output).Append("\n【输出原文结束】");
        return sb.ToString();
    }

    /// <summary>解析 LLM 自审 JSON + 逐字子串校验。output 为被审原文 (quote 校验锚)。</summary>
    public static CritiqueResult Parse(string llmJsonReply, string output)
    {
        var rawArr = ExtractArray(llmJsonReply);
        var valid = new List<CandidateCritique>();
        var rejected = 0;
        if (rawArr is JsonElement raw)
        {
            foreach (var el in raw.EnumerateArray())
            {
                var quote = el.TryGetProperty("quote", out var q) ? q.GetString() : null;
                var mech = el.TryGetProperty("mechanism", out var m) ? m.GetString() : null;
                var sev = el.TryGetProperty("severity", out var s) ? s.GetString() : "low";
                var hint = el.TryGetProperty("fix_hint", out var h) ? h.GetString() : null;
                if (string.IsNullOrWhiteSpace(quote) || string.IsNullOrWhiteSpace(mech))
                {
                    rejected++;
                    continue;
                }
                // 防幻觉锚: quote 必须逐字出现在原文中
                if (!output.Contains(quote, StringComparison.Ordinal))
                {
                    rejected++;
                    continue;
                }
                valid.Add(new CandidateCritique(quote, mech, sev ?? "low", hint ?? ""));
            }
        }
        return new CritiqueResult(valid, rejected, valid.Count + rejected);
    }

    private static JsonElement? ExtractArray(string reply)
    {
        if (string.IsNullOrEmpty(reply))
            return null;
        var start = reply.IndexOf('[');
        var end = reply.LastIndexOf(']');
        if (start < 0 || end <= start)
            return null;
        try
        {
            var doc = JsonDocument.Parse(reply[start..(end + 1)]);
            return doc.RootElement.Clone();
        }
        catch (JsonException)
        {
            return null;
        }
    }
}
