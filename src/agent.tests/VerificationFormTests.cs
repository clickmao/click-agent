using System.Text.Json;
using System.Text.RegularExpressions;
using Xunit;

namespace agent.tests;

/// <summary>
/// R370 验证形式规范机检 (docs/验证形式规范.md + docs/verification-registry.json)。
/// 铁律:
///   R1 无登记=未验证      → SegmentPlugin 实现未登记必红
///   R2 证据可复现          → evidence_cmd 非空 + evidence_path 真实存在
///   R3 L≥2 必须有负向控制  → negative_control 非空
///   R4 禁止静态冒充运行    → L≥2 的 evidence_cmd 不得含静态工具
///   R6 表述纪律            → 规范文档必须含 L0–L4 阶梯与"无登记=未验证"
/// 负向控制: Validator_CatchesInjectedDefects 用合成坏表证明检查器真会红。
/// </summary>
public class VerificationFormTests
{
    private static readonly string RepoRoot = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static string RegistryPath => Path.Combine(RepoRoot, "docs", "verification-registry.json");
    private static string SpecPath => Path.Combine(RepoRoot, "docs", "验证形式规范.md");

    private static readonly string[] Levels = { "L0", "L1", "L2", "L3", "L4" };

    /// <summary>静态工具黑名单: 这些手段最高只能 L1 (R4)。</summary>
    private static readonly Regex StaticOnly = new(
        @"py_compile|csc\s+/t:|compilerserver|仅阅读|仅静态|静态扫描|纯静态",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>校验一份登记表, 返回违规列表 (空=通过)。合成坏表也走同一函数 → 检查器自身可被负向控制。</summary>
    private static List<string> Validate(JsonElement root, string repoRoot)
    {
        var v = new List<string>();
        if (!root.TryGetProperty("rows", out var rows) || rows.ValueKind != JsonValueKind.Array)
            return new List<string> { "登记表缺 rows 数组" };

        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var row in rows.EnumerateArray())
        {
            string S(string k) => row.TryGetProperty(k, out var e) && e.ValueKind == JsonValueKind.String ? e.GetString()! : "";
            var id = S("id");
            if (string.IsNullOrWhiteSpace(id)) { v.Add("存在缺 id 的登记行"); continue; }
            if (!ids.Add(id)) v.Add($"{id}: id 重复");
            if (string.IsNullOrWhiteSpace(S("capability"))) v.Add($"{id}: 缺 capability");
            var level = S("level");
            if (!Levels.Contains(level)) v.Add($"{id}: 等级非法 '{level}' (应 L0–L4)");
            if (string.IsNullOrWhiteSpace(S("evidence_cmd"))) v.Add($"{id}: 缺 evidence_cmd (R2)");
            if (string.IsNullOrWhiteSpace(S("owner_round"))) v.Add($"{id}: 缺 owner_round");

            var evPath = S("evidence_path");
            if (string.IsNullOrWhiteSpace(evPath))
                v.Add($"{id}: 缺 evidence_path (R2)");
            else
            {
                var abs = Path.Combine(repoRoot, evPath.Replace('/', Path.DirectorySeparatorChar));
                if (!File.Exists(abs) && !Directory.Exists(abs))
                    v.Add($"{id}: evidence_path 不存在 '{evPath}' (R2)");
            }

            var runLevel = level is "L2" or "L3" or "L4";
            if (runLevel && string.IsNullOrWhiteSpace(S("negative_control")))
                v.Add($"{id}: L{level[1..]} 缺 negative_control (R3)");
            if (runLevel && StaticOnly.IsMatch(S("evidence_cmd")))
                v.Add($"{id}: L{level[1..]} 用静态工具冒充运行级 '{S("evidence_cmd")}' (R4)");
        }
        return v;
    }

    private static JsonElement LoadRealRegistry()
        => JsonDocument.Parse(File.ReadAllText(RegistryPath, System.Text.Encoding.UTF8)).RootElement;

    [Fact]
    public void Registry_Exists_And_HasNoViolations()
    {
        Assert.True(File.Exists(RegistryPath), $"验证登记表缺失: {RegistryPath}");
        var v = Validate(LoadRealRegistry(), RepoRoot);
        Assert.True(v.Count == 0, "登记表违规:\n  " + string.Join("\n  ", v));
    }

    [Fact]
    public void Registry_HasMinimumCoverage_And_SelfCheckRow()
    {
        var root = LoadRealRegistry();
        var rows = root.GetProperty("rows").EnumerateArray().ToList();
        Assert.True(rows.Count >= 8, $"登记行过少({rows.Count}) — 覆盖面不足");
        Assert.Contains(rows, r => r.GetProperty("id").GetString() == "verification.registry.selfcheck");
        Assert.Equal("verification-registry/v1", root.GetProperty("schema").GetString());
    }

    /// <summary>负向控制: 合成 4 类坏行, 检查器必须全部抓出 (R3/R4/R2)。</summary>
    [Fact]
    public void Validator_CatchesInjectedDefects()
    {
        const string bad = """
        { "schema": "verification-registry/v1", "rows": [
          { "id": "a.no_negctl", "capability": "c", "level": "L3",
            "evidence_cmd": "dotnet test x", "evidence_path": "agent.sln", "owner_round": "R1" },
          { "id": "b.static_as_run", "capability": "c", "level": "L2",
            "evidence_cmd": "python3 -m py_compile foo.py", "evidence_path": "agent.sln",
            "negative_control": "n", "owner_round": "R1" },
          { "id": "c.bad_path", "capability": "c", "level": "L2",
            "evidence_cmd": "dotnet test x", "evidence_path": "no/such/file.cs",
            "negative_control": "n", "owner_round": "R1" },
          { "id": "d.bad_level", "capability": "c", "level": "L9",
            "evidence_cmd": "dotnet test x", "evidence_path": "agent.sln",
            "negative_control": "n", "owner_round": "R1" },
          { "id": "a.no_negctl", "capability": "c", "level": "L1",
            "evidence_cmd": "x", "evidence_path": "agent.sln", "owner_round": "R1" }
        ] }
        """;
        var v = Validate(JsonDocument.Parse(bad).RootElement, RepoRoot);
        Assert.Contains(v, s => s.Contains("a.no_negctl") && s.Contains("negative_control"));
        Assert.Contains(v, s => s.Contains("b.static_as_run") && s.Contains("静态工具"));
        Assert.Contains(v, s => s.Contains("c.bad_path") && s.Contains("不存在"));
        Assert.Contains(v, s => s.Contains("d.bad_level") && s.Contains("等级非法"));
        Assert.Contains(v, s => s.Contains("id 重复"));
        Assert.True(v.Count >= 5, "注入缺陷未被完整捕获: " + string.Join(" | ", v));
    }

    /// <summary>R1: src/ 下每个 IResponseSegmentPlugin 实现文件必须在某行 covers[] 登记。</summary>
    [Fact]
    public void EverySegmentPlugin_Implementation_IsRegistered()
    {
        var root = LoadRealRegistry();
        var covered = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var row in root.GetProperty("rows").EnumerateArray())
            if (row.TryGetProperty("covers", out var c) && c.ValueKind == JsonValueKind.Array)
                foreach (var e in c.EnumerateArray())
                    if (e.ValueKind == JsonValueKind.String) covered.Add(e.GetString()!.Replace('\\', '/'));

        var impl = new Regex(@":\s*IResponseSegmentPlugin\b", RegexOptions.Compiled);
        var srcDir = Path.Combine(RepoRoot, "src");
        var found = new List<string>();
        foreach (var f in Directory.EnumerateFiles(srcDir, "*.cs", SearchOption.AllDirectories))
        {
            var rel = Path.GetRelativePath(RepoRoot, f).Replace('\\', '/');
            if (rel.Contains("/bin/") || rel.Contains("/obj/")) continue;
            if (impl.IsMatch(File.ReadAllText(f, System.Text.Encoding.UTF8))) found.Add(rel);
        }
        Assert.True(found.Count > 0, "未扫描到任何 IResponseSegmentPlugin 实现 — 覆盖度检查失效");
        var missing = found.Where(f => !covered.Contains(f)).ToList();
        Assert.True(missing.Count == 0,
            "以下插件实现未在 verification-registry.json 登记 (R1 无登记=未验证):\n  " + string.Join("\n  ", missing));
    }

    [Fact]
    public void SpecDoc_Exists_And_Declares_LevelLadder()
    {
        Assert.True(File.Exists(SpecPath), $"验证形式规范缺失: {SpecPath}");
        var text = File.ReadAllText(SpecPath, System.Text.Encoding.UTF8);
        foreach (var lv in Levels) Assert.Contains(lv, text);
        Assert.Contains("无登记", text);
        foreach (var r in new[] { "R1", "R2", "R3", "R4", "R5", "R6" }) Assert.Contains(r, text);
    }

    [Fact]
    public void SpecDoc_IsLinkedFrom_MasterPlanOrReadme()
    {
        var linked = new List<string>();
        foreach (var rel in new[] { "docs/reports/iteration-master-plan.md", "README.md" })
        {
            var p = Path.Combine(RepoRoot, rel.Replace('/', Path.DirectorySeparatorChar));
            if (File.Exists(p) && File.ReadAllText(p, System.Text.Encoding.UTF8).Contains("验证形式规范")) linked.Add(rel);
        }
        Assert.True(linked.Count > 0, "《验证形式规范》未被准则或 README 引用 (规范会漂成孤儿)");
    }
}
