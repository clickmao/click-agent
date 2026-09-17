namespace agent.exploration;


/// <summary>
/// 格式修复插件注册表 — 技能-校验矩阵判定 (用户钦定硬性规则):
/// ✓技能+✓校验+✓程序 → 完整收敛环; ✓技能+✓校验+✗程序 → 全程 LLM 修复;
/// ✓技能+✗校验 → 不进入循环修复; ✗技能 → 通用降级。
/// </summary>
public sealed class FormatRepairRegistry
{
    private readonly List<IFormatRepairPlugin> _plugins;
    public FormatRepairRegistry(IEnumerable<IFormatRepairPlugin> plugins) => _plugins = plugins.ToList();

    public IFormatRepairPlugin? Get(string format) =>
        _plugins.FirstOrDefault(p => string.Equals(p.Format, format, StringComparison.OrdinalIgnoreCase));

    /// <summary>该格式是否有本地校验能力 (非 Generic 专用插件存在 = 有)</summary>
    public bool HasValidator(string format) => Get(format) is not null;

    /// <summary>是否有本地修复程序 (专用插件存在 = 有; 只有 generic = 无④)</summary>
    public bool HasLocalRepairer(string format) =>
        _plugins.Any(p => string.Equals(p.Format, format, StringComparison.OrdinalIgnoreCase)
                          && !string.Equals(p.Format, "generic", StringComparison.OrdinalIgnoreCase));
}
