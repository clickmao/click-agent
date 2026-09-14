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

    /// <summary>evidence_cmd 里的仓库相对路径 (跳过省略号占位与构建产物 bin/obj)。</summary>
    private static readonly Regex CmdPath = new(
        @"(?<![\w/.-])((?:src|scripts|eval|docs|tests|website)/[A-Za-z0-9_./-]+)", RegexOptions.Compiled);

    /// <summary>--filter FullyQualifiedName~X 里的 X (含中文测试名)。</summary>
    private static readonly Regex FilterToken = new(
        @"FullyQualifiedName~([\w\u4e00-\u9fff.]+)", RegexOptions.Compiled);

    private static readonly Regex TestClassName = new(@"class\s+([\w\u4e00-\u9fff]+)", RegexOptions.Compiled);
    private static readonly Regex TestMethodName = new(
        @"(?:void|Task|Task<[^>]*>)\s+([\w\u4e00-\u9fff]+)\s*\(", RegexOptions.Compiled);

    /// <summary>测试工程里的类名 + 方法名 (R2d 过滤器可解析性的语料)。</summary>
    private static List<string> TestNames(string repoRoot)
    {
        var names = new List<string>();
        var dir = Path.Combine(repoRoot, "src", "agent.tests");
        if (!Directory.Exists(dir)) return names;
        foreach (var f in Directory.EnumerateFiles(dir, "*.cs", SearchOption.AllDirectories))
        {
            var s = f.Replace('\\', '/');
            if (s.Contains("/bin/") || s.Contains("/obj/")) continue;
            var t = File.ReadAllText(f, System.Text.Encoding.UTF8);
            foreach (Match m in TestClassName.Matches(t)) names.Add(m.Groups[1].Value);
            foreach (Match m in TestMethodName.Matches(t)) names.Add(m.Groups[1].Value);
        }
        return names;
    }

    private static bool Exists(string repoRoot, string rel)
    {
        var abs = Path.Combine(repoRoot, rel.Replace('/', Path.DirectorySeparatorChar));
        return File.Exists(abs) || Directory.Exists(abs);
    }

    /// <summary>校验一份登记表, 返回违规列表 (空=通过)。合成坏表也走同一函数 → 检查器自身可被负向控制。</summary>
    private static List<string> Validate(JsonElement root, string repoRoot)
    {
        var v = new List<string>();
        if (!root.TryGetProperty("rows", out var rows) || rows.ValueKind != JsonValueKind.Array)
            return new List<string> { "登记表缺 rows 数组" };

        var ids = new HashSet<string>(StringComparer.Ordinal);
        var testNames = TestNames(repoRoot);
        if (testNames.Count == 0) v.Add("R2d 检查失效: 未扫描到任何测试类/方法名 (测试工程路径或解析器失效)");
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

            // R2b (R411): evidence_cmd 引用的仓库路径必须存在 —— "可直接复制执行"而不是纸上命令。
            //   构建产物 (bin/obj) 不在此列: 干净检出下本就不存在, 其源码侧存活由 covers[] 钉住。
            //   退役/反证类命令 (断言"某物已不存在") 必须显式声明 cmd_expect_absent, 且声明项必须真的不存在。
            var declaredAbsent = new HashSet<string>(StringComparer.Ordinal);
            if (row.TryGetProperty("cmd_expect_absent", out var ca) && ca.ValueKind == JsonValueKind.Array)
                foreach (var e in ca.EnumerateArray())
                    if (e.ValueKind == JsonValueKind.String) declaredAbsent.Add(e.GetString()!);

            foreach (Match m in CmdPath.Matches(S("evidence_cmd")))
            {
                var tok = m.Groups[1].Value;
                if (tok.Contains("..") || tok.Contains("/bin/") || tok.Contains("/obj/")) continue;
                if (declaredAbsent.Contains(tok))
                {
                    if (Exists(repoRoot, tok))
                        v.Add($"{id}: cmd_expect_absent 声明不存在的路径实际存在 '{tok}' (R2b 声明与仓库事实矛盾)");
                }
                else if (!Exists(repoRoot, tok))
                    v.Add($"{id}: evidence_cmd 引用不存在的路径 '{tok}' (R2b 命令不可执行 —— 退役/反证场景须登记 cmd_expect_absent)");
            }

            // R2d (R411): --filter FullyQualifiedName~X 必须解析到真实测试类/方法。
            //   被删测试留下的过滤器会让整行"看起来有证据"(实测: RoverProcIo 随 R408 退役后登记行照旧)。
            foreach (Match m in FilterToken.Matches(S("evidence_cmd")))
            {
                var f = m.Groups[1].Value;
                if (!testNames.Any(n => n.Contains(f, StringComparison.Ordinal)))
                    v.Add($"{id}: evidence_cmd 的测试过滤器解析不到测试 '{f}' (R2d)");
            }

            // R2c (R411): covers[] 登记的路径必须存在 (覆盖声称必须指向真实源码; 括号内说明先剥离)。
            if (row.TryGetProperty("covers", out var cov) && cov.ValueKind == JsonValueKind.Array)
                foreach (var e in cov.EnumerateArray())
                {
                    if (e.ValueKind != JsonValueKind.String) continue;
                    var p = e.GetString()!.Split('(')[0].Trim();
                    if (p.Length == 0 || !p.Contains('/')) continue;
                    if (!Exists(repoRoot, p)) v.Add($"{id}: covers 登记的路径不存在 '{p}' (R2c)");
                }
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

    /// <summary>负向控制: 合成坏行覆盖 R2/R2b/R2c/R2d/R3/R4/重复 id, 检查器必须全部抓出;
    /// 同时验证 cmd_expect_absent 的正向豁免 (声明→放行, 声明与事实矛盾→必红)。</summary>
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
          { "id": "e.dead_cmd_path", "capability": "c", "level": "L3",
            "evidence_cmd": "dotnet test src/agent.tests/deleted-suite.tests.csproj --filter FullyQualifiedName~VerificationFormTests",
            "evidence_path": "agent.sln",
            "negative_control": "n", "owner_round": "R1" },
          { "id": "f.retired_no_decl", "capability": "c", "level": "L3",
            "evidence_cmd": "src/agent.rover/bin/Release/net10.0/agent.rover tokenize eval/nope/deleted.jsonl",
            "evidence_path": "agent.sln", "negative_control": "n", "owner_round": "R1" },
          { "id": "g.dead_filter", "capability": "c", "level": "L3",
            "evidence_cmd": "dotnet test x --filter FullyQualifiedName~NoSuchTestClassZzz",
            "evidence_path": "agent.sln", "negative_control": "n", "owner_round": "R1" },
          { "id": "h.dead_cover", "capability": "c", "level": "L1",
            "evidence_cmd": "x", "evidence_path": "agent.sln",
            "covers": ["src/agent/NoSuchPluginZzz.cs", "(整段括号说明, 非路径)", "no-slash-entry"],
            "owner_round": "R1" },
          { "id": "i.absent_decl_ok", "capability": "c", "level": "L1",
            "evidence_cmd": "test ! -d src/agent.retired_zzz_absent && echo OK",
            "evidence_path": "agent.sln", "cmd_expect_absent": ["src/agent.retired_zzz_absent"],
            "owner_round": "R1" },
          { "id": "j.absent_decl_contradiction", "capability": "c", "level": "L1",
            "evidence_cmd": "test ! -d src/agent && echo OK",
            "evidence_path": "agent.sln", "cmd_expect_absent": ["src/agent"],
            "owner_round": "R1" },
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
        Assert.Contains(v, s => s.Contains("e.dead_cmd_path") && s.Contains("R2b"));
        Assert.Contains(v, s => s.Contains("f.retired_no_decl") && s.Contains("R2b"));
        Assert.Contains(v, s => s.Contains("g.dead_filter") && s.Contains("R2d"));
        Assert.Contains(v, s => s.Contains("h.dead_cover") && s.Contains("R2c"));
        Assert.Contains(v, s => s.Contains("j.absent_decl_contradiction") && s.Contains("声明与仓库事实矛盾"));
        Assert.DoesNotContain(v, s => s.Contains("i.absent_decl_ok"));   // 正向豁免: 声明缺位路径不判红
        Assert.True(v.Count >= 10, "注入缺陷未被完整捕获: " + string.Join(" | ", v));
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
