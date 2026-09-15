using System.Text;
using agent.registry;

namespace agent.context;

/// <summary>
/// v0.23.0-exp12 · R391(C8): **形式化输出契约的静态前缀条件注入**。
///
/// 口径 (用户钦定): "都要做的, 主要是为了增加真机编排前置知识注入引导啊! 并且还要降低 TOKENS 使用, 不能全让 LLM"。
///   · 契约写进**静态前缀** (会话首轮焊进 system 前缀一次, 之后每轮命中缓存) ⇒ 增量成本 ≈ 0;
///   · **只在本地形式化验证器在场时注入** ⇒ 不在场时前缀**逐字不变** (零 token 负担, 不由 LLM 兜底);
///   · 不在场时绝不追问 LLM: 缺失 ≠ 错误 (与 FormalAssertionContract 同一条铁律)。
///
/// 本类的输出必须**恒定** (会话内不随轮次/工作区变化), 否则前缀缓存命中率必然劣化 —— 由机检保证。
/// 零 token / 零 shell / 零反射: 只拼字符串。
/// </summary>
public static class FormalPromptContract
{
    /// <summary>插件名 (与 ClickRoverSegmentPlugin.Name 同值, 由机检保证一致)。</summary>
    public const string PluginName = "agent.rover.formal";

    /// <summary>围栏语言标识 (单一事实源 = ClickProofFence.Language)。</summary>
    public const string FenceLanguage = ClickProofFence.Language;

    /// <summary>
    /// 在场判定: 任一插件名等于本插件名即视为"本地形式化验证器在场"。
    /// 判据是**真实装配结果** (DI 解析出的插件名), 不是配置里的一句声明 —— 避免"声明在场但没接上"的空心注入。
    /// </summary>
    public static bool IsPresent(IEnumerable<string>? pluginNames)
    {
        if (pluginNames is null) return false;
        foreach (var n in pluginNames)
            if (string.Equals(n, PluginName, StringComparison.Ordinal)) return true;
        return false;
    }

    /// <summary>契约正文 (恒定; 与工作区、轮次、会话历史无关)。</summary>
    public static string Build()
    {
        var sb = new StringBuilder(1200);
        sb.Append("十、形式化输出契约 (本会话已挂载本地形式化验证器: 零 token / 完全本地 / 可机检)\n");
        sb.Append("1. 当某一步骤的正确性可以用**整数算术断言**表达时, 在该步骤后面附一个 ").Append(FenceLanguage).Append(" 围栏块, 逐行写:\n");
        sb.Append("   premise <整数表达式> <关系> <整数表达式>\n");
        sb.Append("   goal <整数表达式> <关系> <整数表达式>\n");
        sb.Append("   关系取值: == != < <= > >= ; 断言至少一条 premise 与一条 goal。\n");
        sb.Append("2. 不提供断言时必须显式写一行: no_formal: <理由> 。缺失视为 absent —— **不算错误, 不会被追问**。\n");
        sb.Append("3. 断言由本地内核确定性裁决, 语义固定: Proved=放行(证毕); Refuted=阻断并回注精确反例; ");
        sb.Append("Vacuous=前提不可满足(空真), 拒绝; Unknown=片段外, 诚实弃权(不算通过)。\n");
        sb.Append("4. 禁止用断言凑数或绕过任务: 断言与任务无关时一律写 no_formal。写坏的断言 (残缺/自相矛盾) 会被判 Malformed 并阻断。\n");
        sb.Append("5. 若把\"验证\"本身作为一个计划节点, 该节点**正文**必须自带上文的 clickproof 围栏 (可直接把上游产出抄成 premise) —— ");
        sb.Append("路由据此把该节点判为本地执行: 零 token、无 LLM 调用、不执行 shell。\n");
        return sb.ToString();
    }

    /// <summary>条件拼装: 在场 ⇒ 前缀 + 契约段; 不在场 ⇒ **逐字原样返回**(负控判据: 一个字符都不许多)。</summary>
    public static string Apply(string baseline, bool formalPluginPresent)
        => formalPluginPresent ? baseline + Build() : baseline;

    /// <summary>
    /// token 量级估算 (诚实口径: 这是**估算**, 不是分词器实测值; 报告里必须与字符数并列给出)。
    /// 依据: 中文按 ~1 token/字, 非中文按 ~1 token/4 字符 —— 与仓库既有 KPI 脚本同口径。
    /// </summary>
    public static int EstimateTokens(string text)
    {
        var cjk = 0;
        foreach (var c in text)
            if (c >= '\u4e00' && c <= '\u9fff') cjk++;
        var rest = text.Length - cjk;
        return cjk + (int)Math.Ceiling(rest / 4.0);
    }

    /// <summary>
    /// R461: **面向用户正文的契约声明剥离** —— 契约是"给本地验证器看的", 不该出现在用户读到的回复里。
    /// 实发证据 (R460 run): 模型有时不写围栏而写裸块 ⇒ 用户看到 5 行 clickproof/premise/goal 或 1 行 no_formal。
    ///
    /// 规则 (零正则、零反射, 逐行状态机):
    ///   · ```<FenceLanguage> … ``` 围栏块整块进 declaration;
    ///   · 独占一行且以 "no_formal:" 开头 ⇒ 进 declaration;
    ///   · 裸块: 出现独占一行等于 FenceLanguage 时, 其后紧跟的 premise/goal 行进 declaration, 遇到第一行非声明行即结束裸块;
    ///   · 其余行原样进 visible; 连续空行折叠为一行。
    /// 兜底 (fail-safe): 剥离后 visible 为空 ⇒ 返回**原文本**, 宁可少剥也不给用户空回复。
    /// </summary>
    public static (string Visible, string Declaration) SplitFacing(string? content)
    {
        if (string.IsNullOrEmpty(content))
            return (content ?? string.Empty, string.Empty);

        var normalized = content.Replace("\r\n", "\n").Replace('\r', '\n');
        var lines = normalized.Split('\n');
        var visible = new List<string>(lines.Length);
        var declaration = new List<string>();
        var inFence = false;
        var inBare = false;

        foreach (var raw in lines)
        {
            var line = raw.TrimEnd();
            var trimmed = line.Trim();

            if (inFence)
            {
                declaration.Add(line);
                if (trimmed.StartsWith("```", StringComparison.Ordinal))
                    inFence = false;
                continue;
            }

            if (trimmed.StartsWith("```", StringComparison.Ordinal))
            {
                var lang = trimmed.TrimStart('`').Trim();
                if (string.Equals(lang, FenceLanguage, StringComparison.OrdinalIgnoreCase))
                {
                    inFence = true;
                    declaration.Add(line);
                    continue;
                }
                visible.Add(line);   // 别的语言围栏 = 正常内容
                continue;
            }

            if (trimmed.StartsWith("no_formal:", StringComparison.OrdinalIgnoreCase))
            {
                declaration.Add(line);
                continue;
            }

            if (string.Equals(trimmed, FenceLanguage, StringComparison.OrdinalIgnoreCase))
            {
                inBare = true;
                declaration.Add(line);
                continue;
            }

            if (inBare)
            {
                if (IsBareDeclarationLine(trimmed))
                {
                    declaration.Add(line);
                    continue;
                }
                inBare = false;      // 裸块结束, 本行按正常内容处理
            }

            visible.Add(line);
        }

        var shown = CollapseBlankLines(visible);
        if (shown.Trim().Length == 0)
            return (normalized, string.Join("\n", declaration));   // fail-safe: 不产生空回复
        return (shown, string.Join("\n", declaration));
    }

    /// <summary>裸块里的声明行形态: premise/goal + 空格/制表符开头 (只此两种)。</summary>
    private static bool IsBareDeclarationLine(string trimmed)
    {
        if (trimmed.Length == 0) return true;   // 裸块内的空行也算块内
        return StartsWithWord(trimmed, "premise") || StartsWithWord(trimmed, "goal");
    }

    private static bool StartsWithWord(string s, string word)
        => s.Length > word.Length
           && s.StartsWith(word, StringComparison.OrdinalIgnoreCase)
           && (s[word.Length] == ' ' || s[word.Length] == '\t' || s[word.Length] == ':' || s[word.Length] == '=');

    /// <summary>连续空行折叠为一行 (精炼; 不改变非空行内容)。</summary>
    private static string CollapseBlankLines(List<string> lines)
    {
        var sb = new StringBuilder(lines.Sum(l => l.Length + 1));
        var blank = false;
        foreach (var l in lines)
        {
            var isBlank = l.Trim().Length == 0;
            if (isBlank && blank) continue;
            blank = isBlank;
            sb.Append(l).Append('\n');
        }
        return sb.ToString().TrimEnd('\n');
    }
}
