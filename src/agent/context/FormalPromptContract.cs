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
}
