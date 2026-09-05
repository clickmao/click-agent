using System.Reflection;

namespace agent.registry;

/// <summary>
/// 能力探嗅 (v7.14): 自动发现 agent 可用的 skill/tool, 生成能力清单。
/// 两个扫描面 (v7.14 AOT 安全版):
///   ①显式注册: RegisterCapability 由宿主/DI 在启动时登记 (代码级技能)
///   ②系统 PATH: 声明在 DesiredTools 里的可执行文件存在性 (系统级工具)
/// 扫描结果缓存 (启动时一次), RenderForPrompt 让 LLM 明确"我能用什么"。
/// </summary>

public sealed class CapabilityScanner
{
    private sealed record CapabilityInfo(string Name, string Description, string Source);

    private readonly List<CapabilityInfo> _capabilities = new();
    private readonly object _lock = new();
    private bool _scanned;

    /// <summary>期望存在的系统工具 (PATH 探嗅; 缺失如实标注 unavailable)</summary>
    private static readonly string[] DesiredTools = { "git", "dotnet", "curl", "python3", "vulkaninfo" };

    public void Scan()
    {
        lock (_lock)
        {
            if (_scanned)
                return;
            _scanned = true;
            try
            {
                // ① 显式注册通道 (AOT 安全): RegisterCapability 由宿主/DI 在启动时登记。
                // v7.14 真机判决: 程序集 GetTypes+Activator 反射扫描在 AOT trim 后类型图不全 → 漏报+IL 警告,
                // 已删除; 能力发现走显式注册 + PATH 探嗅双通道。
                // ② PATH 工具探嗅
                foreach (var tool in DesiredTools)
                {
                    var available = FindOnPath(tool) != null;
                    _capabilities.Add(new CapabilityInfo(
                        tool,
                        available ? $"系统工具 (PATH 可达)" : "系统工具 (不可用)",
                        available ? "path" : "path-missing"));
                }
            }
            catch
            {
                // 扫描失败不阻塞启动 — 能力清单可为空
            }
        }
    }

    /// <summary>已探嗅能力数 (诊断)</summary>
    public int Count { get { lock (_lock) { return _capabilities.Count; } } }

    /// <summary>能力清单 JSON (面板 /status 用, 程序可解析)</summary>
    public List<(string Name, string Description, string Source)> Snapshot()
    {
        Scan();
        lock (_lock)
            return _capabilities.Select(c => (c.Name, c.Description, c.Source)).ToList();
    }

    /// <summary>渲染注入 prompt 的能力块 (⑤核心输出)</summary>
    public string RenderForPrompt()
    {
        Scan();
        lock (_lock)
        {
            if (_capabilities.Count == 0)
                return string.Empty;
            var available = _capabilities.Where(c => c.Source != "path-missing").ToList();
            if (available.Count == 0)
                return string.Empty;
            return "【可用能力】" + string.Join(", ",
                available.Select(c => c.Source == "assembly" ? $"{c.Name}({c.Description})" : c.Name));
        }
    }

    private static string? FindOnPath(string name)
    {
        // PATH 优先, 附加常见安装目录 (工具装了但不在当前进程 PATH 的场景, 如 ~/.dotnet)
        var dirs = new List<string>();
        var pathEnv = Environment.GetEnvironmentVariable("PATH");
        if (!string.IsNullOrEmpty(pathEnv))
            dirs.AddRange(pathEnv.Split(':'));
        var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        dirs.Add(Path.Combine(home, ".dotnet"));
        dirs.Add("/usr/local/bin");
        dirs.Add("/usr/bin");
        foreach (var dir in dirs)
        {
            if (string.IsNullOrWhiteSpace(dir))
                continue;
            try
            {
                var p = Path.Combine(dir.Trim(), name);
                if (File.Exists(p))
                    return p;
                // ~/.dotnet 布局: 目录本体就是安装根
                if (Directory.Exists(dir) && name == "dotnet" && File.Exists(Path.Combine(dir.Trim(), "dotnet")))
                    return Path.Combine(dir.Trim(), "dotnet");
            }
            catch
            {
                // 路径异常忽略
            }
        }
        return null;
    }
}
