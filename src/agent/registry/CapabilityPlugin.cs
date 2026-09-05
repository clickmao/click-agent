using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.registry;

/// <summary>
/// 能力插件接口 (v7.15 需求6): 工作区管理/测试集成/代码审查等能力 — 框架只定义契约,
/// 内部功能由开发者按接口实现后注册 (同 WebSearch 数据源模式: 接口在框架, 实现在外部)。
/// 线程安全注册表 + 统一分发。
/// </summary>
public interface ICapabilityPlugin
{
    /// <summary>插件名 (注册表唯一键)</summary>
    string Name { get; }

    /// <summary>能力描述 (/status capabilities 可读)</summary>
    string Description { get; }

    /// <summary>本插件提供的能力 id 清单 (如 workspace.read_file / tests.run / review.static)</summary>
    IReadOnlyList<string> ProvidedCapabilities { get; }

    /// <summary>初始化 (DI/配置就绪后调用一次)</summary>
    Task InitializeAsync(CancellationToken ct = default);

    /// <summary>执行能力。capabilityId ∈ ProvidedCapabilities; args 由插件自定义语义。</summary>
    Task<PluginExecutionResult> ExecuteAsync(string capabilityId, string args, CancellationToken ct = default);
}

/// <summary>插件执行结果 (成功/失败 + 输出; 失败必须给可读原因, 不静默)</summary>
public sealed class PluginExecutionResult
{
    public bool Success { get; set; }

    /// <summary>输出内容 (文本/JSON 单行 — 遵循 CLI 单行 JSON 契约)</summary>
    public string Output { get; set; } = string.Empty;

    /// <summary>失败原因 (Success=false 时必填)</summary>
    public string? Error { get; set; }

    public static PluginExecutionResult Ok(string output) =>
        new() { Success = true, Output = output };

    public static PluginExecutionResult Fail(string error) =>
        new() { Success = false, Error = error };
}

/// <summary>
/// 能力插件注册表: 开发者实现 ICapabilityPlugin → Register → Execute 统一分发。
/// 全线程安全; 同名重复注册拒绝 (返回 false, 不覆盖)。
/// </summary>
public sealed class CapabilityPluginRegistry
{
    private readonly Dictionary<string, ICapabilityPlugin> _plugins =
        new(StringComparer.OrdinalIgnoreCase);

    /// <summary>已注册插件名 (快照, /status 可读)</summary>
    public IReadOnlyList<string> Names
    {
        get
        {
            lock (_plugins)
                return _plugins.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
        }
    }

    /// <summary>注册插件 (同名 → false 不覆盖; InitializeAsync 失败 → 移除并抛回调用方裁决)</summary>
    public bool Register(ICapabilityPlugin plugin)
    {
        lock (_plugins)
        {
            if (_plugins.ContainsKey(plugin.Name))
                return false;
            _plugins[plugin.Name] = plugin;
            return true;
        }
    }

    /// <summary>按名获取</summary>
    public ICapabilityPlugin? Find(string name)
    {
        lock (_plugins)
            return _plugins.TryGetValue(name, out var p) ? p : null;
    }

    /// <summary>
    /// 统一分发: name.capabilityId (如 "workspace.read_file") → 定位插件执行。
    /// 未注册 → Fail (不抛 — 分发面是外部输入)。
    /// </summary>
    public async Task<PluginExecutionResult> ExecuteAsync(string capabilityFqn, string args, CancellationToken ct = default)
    {
        var dot = capabilityFqn.IndexOf('.');
        if (dot <= 0)
            return PluginExecutionResult.Fail($"invalid_capability_fqn: {capabilityFqn} (期望 插件名.能力id)");
        var pluginName = capabilityFqn[..dot];
        var capabilityId = capabilityFqn[(dot + 1)..];

        var plugin = Find(pluginName);
        if (plugin is null)
            return PluginExecutionResult.Fail($"plugin_not_registered: {pluginName}");
        if (!plugin.ProvidedCapabilities.Contains(capabilityId, StringComparer.OrdinalIgnoreCase))
            return PluginExecutionResult.Fail($"capability_not_provided: {capabilityFqn}");
        try
        {
            return await plugin.ExecuteAsync(capabilityId, args, ct);
        }
        catch (OperationCanceledException)
        {
            throw; // 取消语义保留
        }
        catch (Exception ex)
        {
            return PluginExecutionResult.Fail($"plugin_fault: {ex.Message}");
        }
    }
}
