using System.Text.Json;
using agent.config;

namespace agent.roles;

/// <summary>
/// R362 (v0.21.0): Role 注册中心 — roles/ 目录扫描加载 (对齐 SkillRegistry 包模式)。
/// 包结构: roleId/role.yaml (MiniYaml 头) + PROFILE.md (人格种子, 可空) + growth.jsonl (预留)。
/// 外挂原则 (用户钦定): Role 是外挂数据源, CLI --role <id> 可空加载 (缺省无角色, 行为与无 Role 完全一致);
/// 包坏只损失该包 (S.5 降级原则)。
/// 紧凑预算 (加载时强制): role.yaml ≤2KB / PROFILE.md ≤2KB — 超限拒载 (报错到字段)。
/// </summary>
public sealed class RoleRegistry
{
    private readonly Dictionary<string, RolePackage> _roles = new(StringComparer.OrdinalIgnoreCase);

    public sealed record RolePackage
    {
        public string Id { get; init; } = "";
        public string Name { get; init; } = "";
        /// <summary>人格种子语料 (PROFILE.md 原文; 可空 — 无种子时 Role 仅由赏罚动态构成)</summary>
        public string ProfileSeed { get; init; } = "";
        public string Dir { get; init; } = "";
        public int SizeBytes { get; init; }
    }

    public IReadOnlyDictionary<string, RolePackage> All => _roles;

    /// <summary>当前激活 Role id (可空 — CLI --role 注入; null = 无角色)。</summary>
    public string? ActiveId { get; set; }

    /// <summary>激活包 (可空)。</summary>
    public RolePackage? FindActive() => ActiveId is null ? null : Find(ActiveId);

    /// <summary>目录扫描加载 (rolesRoot 下每子目录一个 Role 包)。</summary>
    public static RoleRegistry LoadFromDirectory(string rolesRoot)
    {
        var reg = new RoleRegistry();
        if (!Directory.Exists(rolesRoot)) return reg;

        foreach (var dir in Directory.EnumerateDirectories(rolesRoot))
        {
            try
            {
                var pkg = LoadPackage(dir);
                if (pkg is not null && pkg.Id.Length > 0)
                    reg._roles[pkg.Id] = pkg;
            }
            catch
            {
                // 单包坏不阻断其他 Role 加载 (S.5 降级原则)
                AgentTelemetry.Emit("role_load_error", "RoleRegistry", ("dir", dir));
            }
        }
        AgentTelemetry.Emit("role_load", "RoleRegistry",
            ("root", Path.GetFullPath(rolesRoot)), ("count", reg._roles.Count));
        return reg;
    }

    /// <summary>加载单包。null = 无 role.yaml (非 Role 目录); 超预算 → 抛 (调用方 catch 计入坏包)。</summary>
    private static RolePackage? LoadPackage(string dir)
    {
        var yamlPath = Path.Combine(dir, "role.yaml");
        if (!File.Exists(yamlPath)) return null;

        var yaml = File.ReadAllText(yamlPath);
        if (yaml.Length > 2048)
            throw new InvalidDataException($"role.yaml 超预算: {yaml.Length}B > 2048B ({dir})");

        string? profileSeed = null;
        var mdPath = Path.Combine(dir, "PROFILE.md");
        if (File.Exists(mdPath))
        {
            profileSeed = File.ReadAllText(mdPath);
            if (profileSeed.Length > 2048)
                profileSeed = profileSeed[..2048]; // 种子超限截断 (yaml 超限才拒载 — 种子可容忍)
        }

        var id = Path.GetFileName(dir);
        var parsed = MiniYaml.Parse(yaml);
        var name = parsed.TryGetValue("name", out var nv) ? nv?.ToString() ?? id : id;
        var size = new FileInfo(yamlPath).Length + (profileSeed?.Length ?? 0);

        return new RolePackage
        {
            Id = id,
            Name = name,
            ProfileSeed = profileSeed ?? "",
            Dir = dir,
            SizeBytes = (int)size,
        };
    }

    public RolePackage? Find(string id) =>
        _roles.TryGetValue(id, out var p) ? p : null;
}
