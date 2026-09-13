namespace agent.registry;

/// <summary>
/// v0.23.0-exp12 · S1(M4): 形式化断言契约 —— 执行链第 ② 段「计划 → 节点化 + 逐节点断言」的契约层。
///
/// 设计铁律(可证伪):
///  1) <b>缺失 ≠ 错误</b>: 节点未提供形式化断言 ⇒ NoFormal("absent"), 放行, 且<b>绝不为此追问 LLM</b>
///     (不要求 LLM 返回形式化数据 —— 插件/契约缺失时链必须能继续)。
///  2) <b>显式声明优先</b>: 节点以 no_formal 标记声明「本节点无可判定片段」⇒ NoFormal("declared")。
///  3) <b>残缺不放行</b>: 有断言意图但 premise/goal 不齐、裸关键字、或与 no_formal 自相矛盾 ⇒ Malformed,
///     不放行、不静默吞、不追问(模型不能靠"写坏断言"绕过闸门)。
///  4) <b>零 token / 零 shell / 零反射</b>: 本层只做语法与义务判定, 数学裁决交 click-rover 内核
///     (`click-rover check <file.assert>`), 语法与之严格同构。
///  5) 任何分支都不得触发 LLM 重试(<see cref="FormalContractResult.RequiresLlmRetry"/> 恒为 false)。
/// </summary>
public enum FormalContractDecision
{
    /// <summary>premise/goal 齐备 ⇒ 交 click-rover 内核裁决(本地, 零 token)。</summary>
    Assertion = 0,

    /// <summary>本次不提供形式化断言(缺失或显式声明) ⇒ 放行; 不追问 LLM。</summary>
    NoFormal = 1,

    /// <summary>有断言意图但残缺/自相矛盾 ⇒ 不放行(不静默吞), 亦不追问 LLM。</summary>
    Malformed = 2,
}

/// <summary>契约判定结果。不可变; 便于审计落盘与离线重放。</summary>
public sealed record FormalContractResult(
    FormalContractDecision Decision,
    string ReasonCode,
    string? AssertionText = null,
    string? Declaration = null)
{
    /// <summary>可放行(仅"不提供断言"这一种情形)。</summary>
    public bool IsPassable => Decision == FormalContractDecision.NoFormal;

    /// <summary>须交本地内核裁决(仅 Assertion)。</summary>
    public bool NeedsKernel => Decision == FormalContractDecision.Assertion;

    /// <summary>硬约束: 契约层永不触发 LLM 追问/重试。恒 false。</summary>
    public bool RequiresLlmRetry => false;
}

/// <summary>
/// 断言契约解析器。语法(与 click-rover `check` 同构, 逐行):
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
