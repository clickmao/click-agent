namespace agent.registry;

/// <summary>
/// 断言契约解析器。语法(与 agent.rover `check` 同构, 逐行):
/// <code>
/// # 注释(可省略)
/// premise x + y == 10
/// premise x &gt; 4
/// goal x &lt; 100
/// </code>
/// 或显式声明: <c>no_formal: &lt;理由&gt;</c>
/// </summary>
public static class FormalAssertionContract
{
    /// <summary>显式弃权标记(大小写不敏感)。</summary>
    public const string NoFormalMarker = "no_formal";

    private const string ReasonAbsent = "absent";
    private const string ReasonDeclared = "declared";
    private const string ReasonIncomplete = "incomplete";
    private const string ReasonConflict = "no_formal_with_assertion";
    private const string ReasonAssertion = "assertion";

    /// <summary>解析节点/产物契约文本。空输入 ⇒ NoFormal("absent")。</summary>
    public static FormalContractResult Parse(string? contractText)
    {
        if (string.IsNullOrWhiteSpace(contractText))
            return new FormalContractResult(FormalContractDecision.NoFormal, ReasonAbsent);

        var premises = new List<string>();
        var goals = new List<string>();
        var brokenLine = false;
        string? declaration = null;

        foreach (var raw in contractText.Split('\n'))
        {
            var line = raw.Trim().TrimEnd('\r');
            if (line.Length == 0 || line[0] == '#') continue;

            if (TryNoFormal(line, out var reason))
            {
                declaration ??= reason;
                continue;
            }

            if (TryKeyword(line, "premise", out var premiseBody))
            {
                if (premiseBody.Length == 0) brokenLine = true;
                else premises.Add(premiseBody);
                continue;
            }

            if (TryKeyword(line, "goal", out var goalBody))
            {
                if (goalBody.Length == 0) brokenLine = true;
                else goals.Add(goalBody);
            }
        }

        var hasAssertionIntent = premises.Count > 0 || goals.Count > 0 || brokenLine;

        // 自相矛盾: 既声明 no_formal 又给出断言 ⇒ 不放行(不允许两头占)。
        if (declaration is not null && hasAssertionIntent)
            return new FormalContractResult(FormalContractDecision.Malformed, ReasonConflict);

        if (hasAssertionIntent)
        {
            if (brokenLine || premises.Count == 0 || goals.Count == 0)
                return new FormalContractResult(FormalContractDecision.Malformed, ReasonIncomplete);

            var text = string.Join(
                "\n",
                premises.Select(p => "premise " + p).Concat(goals.Select(g => "goal " + g)));

            return new FormalContractResult(FormalContractDecision.Assertion, ReasonAssertion, text);
        }

        return declaration is not null
            ? new FormalContractResult(FormalContractDecision.NoFormal, ReasonDeclared, Declaration: declaration)
            : new FormalContractResult(FormalContractDecision.NoFormal, ReasonAbsent);
    }

    /// <summary>取可交内核的 .assert 正文(非 Assertion 时为空串)。</summary>
    public static string ToKernelAssertText(FormalContractResult result) => result.AssertionText ?? string.Empty;

    private static bool TryNoFormal(string line, out string reason)
    {
        reason = string.Empty;
        if (!line.StartsWith(NoFormalMarker, StringComparison.OrdinalIgnoreCase))
            return false;

        var rest = line[NoFormalMarker.Length..];
        if (rest.Length > 0 && rest[0] == ':') rest = rest[1..];
        else if (rest.Length > 0 && !char.IsWhiteSpace(rest[0])) return false;

        reason = rest.Trim();
        return true;
    }

    /// <summary>关键字必须成词(后随空白或行尾), 否则 "premises are ..." 之类会被误判。</summary>
    private static bool TryKeyword(string line, string keyword, out string body)
    {
        body = string.Empty;
        if (!line.StartsWith(keyword, StringComparison.Ordinal))
            return false;

        var rest = line[keyword.Length..];
        if (rest.Length > 0 && !char.IsWhiteSpace(rest[0]))
            return false;

        body = rest.Trim();
        return true;
    }
}
