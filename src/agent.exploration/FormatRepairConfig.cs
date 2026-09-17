namespace agent.exploration;


/// <summary>修复配置 (config format_repair 段 — 用户钦定)。</summary>
public sealed class FormatRepairConfig
{
    public bool Enabled { get; set; } = true;
    /// <summary>LLM 连续修复失败上限 (有校验机制所以可计数 — 用户钦定)</summary>
    public int MaxLlmRounds { get; set; } = 3;
    /// <summary>notify_user | agent_autonomous (托管权限 → 超限后静默探索新方案)</summary>
    public string OnExhaust { get; set; } = "notify_user";
    /// <summary>启用的修复插件 (skill-校验矩阵: 决定 ①是否进入/④是否可用)</summary>
    public string[] Plugins { get; set; } = { "json", "csv", "xml" };
}
