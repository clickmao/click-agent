using System.Text.RegularExpressions;

namespace agent.critique;

/// <summary>
/// v0.14.0 T1 (OutputCritic): LLM 输出代码反模式规则扫描器 — 纯静态/零额外 LLM 调用/AOT 安全。
/// 用户钦定主题: 思考链缺"输出后自审"。规则 = 评审反馈转正的改进点提醒 (命中≠失败)。
/// 设计: 每条规则 = (编号, 检测, 修法文案); 命中只**提示不改写** (与 L1 牵引同哲学: 不改答案本体);
/// 证据带行号 (误报可审计)。规则 R0 编号与缺陷台账同构。
/// </summary>
public static class OutputCritic
{
    public sealed record Finding(string RuleId, int Line, string Snippet, string Advice);

    private sealed record Rule(string Id, Func<string, IReadOnlyList<(int Line, string Snippet)>> Detect, string Advice);

    private static readonly Rule[] Rules =
    {
        // R01 堆分配替代取值 (用户实证案): 循环体内 new[] / new List<> 字面量 (≤4 元素)
        new("R01", m => FindLines(m, @"new\s*(\[\]\s*\{|List<[^>]+>\s*\{)"),
            "循环内 new[]/List 字面量每次迭代堆分配 — 双操作数取值用 ref 局部变量 "),
        // R02 字符串 += 进循环 (宽松: 行含 += 且含引号或 + 拼接; 循环上下文在 HasLoopContext 判)
        new("R02", m => FindLines(m, "\\+=\\s*[\\w\".]+"),
            "循环内字符串 += 产生中间串链 — 用 StringBuilder"),
        // R03 async void
        new("R03", m => FindLines(m, @"async\s+void\s+\w+\s*\("),
            "async void 只有事件处理器合法 — 用 async Task 保异常可观察"),
        // R04 .Result / .Wait() 死锁面
        new("R04", m => FindLines(m, @"\.Result\b|\.Wait\(\)"),
            "阻塞等待混用 async — 全链 async/await"),
        // R05 吞异常
        new("R05", m => FindLines(m, @"catch\s*(\([^)]*\))?\s*\{\s*\}"),
            "空 catch 吞异常 — 至少日志或注释豁免理由"),
        // R06 Count() > 0
        new("R06", m => FindLines(m, @"\.Count\(\)\s*[><]=?\s*0"),
            "Count()>0 全枚举 — 用 Any()"),
        // R07 double == 比较 (0d/0f/1d 字面量或 double 声明行 ==)
        new("R07", m => FindLines(m, @"\b(double|float)\s+\w+\s*==|==\s*\d+(\.\d+)?[dDfF]\b"),
            "浮点 == 精度陷阱 — 用容差比较 Math.Abs(a-b)<eps"),
        // R08 大对象未 using
        new("R08", m => FindLines(m, @"=\s*new\s+(FileStream|HttpClient|SqlConnection|MemoryStream)\s*\("),
            "Dispose 型对象未 using — using 声明或显式 Dispose"),
    };

    private static readonly Regex LineSplit = new("\r?\n", RegexOptions.Compiled);

    /// <summary>扫描代码块, 返回命中 (含规则/行号/片段)。空代码块返回空。</summary>
    public static IReadOnlyList<Finding> Review(string reply)
    {
        if (string.IsNullOrEmpty(reply))
            return Array.Empty<Finding>();
        var findings = new List<Finding>();
        foreach (var block in ExtractCodeBlocks(reply))
        {
            var lines = LineSplit.Split(block.Code);
            foreach (var rule in Rules)
            {
                foreach (var (relLine, snippet) in rule.Detect(block.Code))
                {
                    // R02 特例: += 循环上下文判定 (同块内含 for/while/foreach 才报)
                    if (rule.Id == "R02" && !HasLoopContext(lines))
                        continue;
                    findings.Add(new Finding(rule.Id, block.StartLine + relLine, snippet, rule.Advice));
                }
            }
        }
        return findings;
    }

    /// <summary>渲染为回复尾追加文案 (L1 同点位)。</summary>
    public static string Render(IReadOnlyList<Finding> findings, int max = 3)
    {
        if (findings.Count == 0)
            return string.Empty;
        var sb = new System.Text.StringBuilder("\n\n> ⚠ 自审: ");
        foreach (var f in findings.Take(max))
            sb.Append($"{f.RuleId} (行 {f.Line}) {f.Snippet} — {f.Advice}; ");
        if (findings.Count > max)
            sb.Append($"…另 {findings.Count - max} 处。");
        return sb.ToString();
    }

    private static bool HasLoopContext(string[] lines)
        => lines.Any(l => l.Contains("for") && (l.Contains("(") && (l.Contains("foreach") || l.Contains("for ")))
                          || l.Contains("while"));

    private static IReadOnlyList<(int Line, string Snippet)> FindLines(string code, string pattern)
    {
        var rx = new Regex(pattern, RegexOptions.None, TimeSpan.FromMilliseconds(200));
        var list = new List<(int, string)>();
        var lines = LineSplit.Split(code);
        for (var i = 0; i < lines.Length; i++)
        {
            var m = rx.Match(lines[i]);
            if (m.Success)
                list.Add((i + 1, lines[i].Trim()[..Math.Min(60, lines[i].Trim().Length)]));
        }
        return list;
    }

    private static IEnumerable<(string Code, int StartLine)> ExtractCodeBlocks(string reply)
    {
        // ``` 语言标记行后到 ``` 前; 简单配对 (奇数个围栏时忽略最后一个未闭合块)
        var fences = new List<int>();
        var idx = 0;
        while ((idx = reply.IndexOf("```", idx, StringComparison.Ordinal)) >= 0)
        {
            fences.Add(idx);
            idx += 3;
        }
        for (var i = 0; i + 1 < fences.Count; i += 2)
        {
            var open = fences[i];
            var nl = reply.IndexOf('\n', open);
            if (nl < 0 || nl >= fences[i + 1])
                continue;
            var startLine = 1 + reply.AsSpan(0, nl + 1).Count('\n');
            yield return (reply[(nl + 1)..fences[i + 1]], startLine);
        }
    }
}
