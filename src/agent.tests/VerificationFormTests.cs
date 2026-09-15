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

    /// <summary>R473: live 行 pin_status 的合法原因词表 (与 eval/capability/bind_evidence.py 同源)。</summary>
    private static readonly string[] PinReasons =
        { "archived-per-round", "append-only-ledger", "worktree-only", "directory-aggregate",
          "self-derived", "evidence-overtaken" };

    private static readonly Regex Hex12 = new("^[0-9a-f]{12}$", RegexOptions.Compiled);

    /// <summary>文件现盘字节的 sha256 前 12 位 (小写十六进制); 不可读返回 null。</summary>
    private static string? Sha12(string absPath)
    {
        if (!File.Exists(absPath)) return null;
        using var sha = System.Security.Cryptography.SHA256.Create();
        return Convert.ToHexString(sha.ComputeHash(File.ReadAllBytes(absPath)))[..12].ToLowerInvariant();
    }

    /// <summary>产物自证: JSON 顶层 provenance 对象 (否则 null)。</summary>
    private static JsonElement? ProvenanceOf(string absPath)
    {
        if (!absPath.EndsWith(".json", StringComparison.Ordinal) || !File.Exists(absPath)) return null;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(absPath, System.Text.Encoding.UTF8));
            if (doc.RootElement.ValueKind == JsonValueKind.Object
                && doc.RootElement.TryGetProperty("provenance", out var p) && p.ValueKind == JsonValueKind.Object)
                return p.Clone();
        }
        catch { }
        return null;
    }


    /// <summary>EXP1-Q27: 目录清单摘要 —— 目录聚合证据的字节闸
    /// (与 eval/capability/bind_evidence.py::dir_manifest **逐位同口径**, 两侧改动必须同步)。
    /// 文件集 = `git ls-files -- &lt;relDir&gt;` (索引来源: .gitignore 产物与未跟踪 scratch 天然不入闸)
    ///          ∩ 现盘存在, 按 relpath 序号排序;
    /// 摘要   = sha256[:12] over 拼接的 "relpath:size:sha12\n" (字节取自工作区);
    /// 无已跟踪文件 ⇒ null (空清单不是闸, 判红)。
    /// 目录内已跟踪文件被改写/增删 ⇒ 摘要变化 ⇒ 该行判红 (证据易主必须说话)。</summary>
    private static string? DirManifestSha12(string repoRoot, string relDir)
    {
        var psi = new System.Diagnostics.ProcessStartInfo("git")
        {
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        psi.ArgumentList.Add("ls-files");
        psi.ArgumentList.Add("--");
        psi.ArgumentList.Add(relDir);
        using var p = System.Diagnostics.Process.Start(psi);
        if (p == null) return null;
        var outp = p.StandardOutput.ReadToEnd();
        p.WaitForExit();
        if (p.ExitCode != 0) return null;

        var sb = new System.Text.StringBuilder();
        int n = 0;
        foreach (var rel in outp.Split('\n', StringSplitOptions.RemoveEmptyEntries)
                                .Select(s => s.Trim()).Where(s => s.Length > 0)
                                .Distinct(StringComparer.Ordinal).OrderBy(s => s, StringComparer.Ordinal))
        {
            var abs = Path.Combine(repoRoot, rel.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(abs)) continue;
            var bytes = File.ReadAllBytes(abs);
            sb.Append(rel).Append(':').Append(bytes.Length).Append(':')
              .Append(Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes))[..12].ToLowerInvariant())
              .Append('\n');
            n++;
        }
        if (n == 0) return null;
        var digest = System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(sb.ToString()));
        return Convert.ToHexString(digest)[..12].ToLowerInvariant();
    }


    /// <summary>EXP1-Q27: 目录沿革里是否出现过改写(M)/删除(D) —— 只看 M/D, 首见 A(加入) 不算。
    /// (与 eval/capability/bind_evidence.py::dir_rewritten 同口径。) 按设计会变的目录不该上清单闸:
    /// 上闸只会产恒红假警, 应留 live/evidence-overtaken —— 先量后定 (Q27 普查: eval/probe 10 提交/5 改写)。</summary>
    private static bool DirRewritten(string repoRoot, string relDir)
    {
        var psi = new System.Diagnostics.ProcessStartInfo("git")
        {
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        psi.ArgumentList.Add("log");
        psi.ArgumentList.Add("--no-renames");
        psi.ArgumentList.Add("--name-status");
        psi.ArgumentList.Add("--pretty=format:%H");
        psi.ArgumentList.Add("--");
        psi.ArgumentList.Add(relDir);
        using var p = System.Diagnostics.Process.Start(psi);
        if (p == null) return true;                 // fail-closed: 派生不了 ⇒ 不许上冻结闸
        var outp = p.StandardOutput.ReadToEnd();
        p.WaitForExit();
        // 仪器纪律 (Q27 自踩): 首版用非法格式 `--format=@` ⇒ git fatal, stdout 空 ⇒ 恒返回 false (空心闸)。
        //   ① 用合法格式; ② 检查退出码, 非 0 = 无法证明「沿革只有追加」⇒ fail-closed 返回 true。
        if (p.ExitCode != 0) return true;
        foreach (var raw in outp.Split('\n'))
        {
            var t = raw.Trim();
            if (t.Length == 0 || t.StartsWith("commit ", StringComparison.Ordinal)) continue;
            if (t[0] == 'M' || t[0] == 'D') return true;
        }
        return false;
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
            // R2e/R2f (R473): evidence_generated_with —— 证据 ↔ 器具/输入 版本绑定。
            //   覆盖 R2f: 产品面证据行 (eval/ 或 docs/reports/ 前缀, L1–L4) 必须有本字段 (L0=未验证 不强制)。
            //   闸门 R2e: frozen 行的 artifact_sha12 必须等于证据文件**现盘字节** sha256[:12]; instrument 非空的
            //     行 instrument_sha12 必须等于器具现盘字节 —— 证据/器具被改写即判红(重审信号)。这正是 Q24 缺陷族
            //     (r444 precheck 证据被控制臂静默覆盖) 在登记层的根因护栏: 证据换了主人, 登记表必须说话。
            //   live 行 (追加式台账/未入库产物/目录聚合/派生件) 不上字节闸, 原因入 pin_reason (不冒充冻结)。
            //   binding=self-attested 只在产物自带 provenance 且逐字段一致时成立; 产物已自证却登记成 audit-pin 亦判红。
            var gen = row.TryGetProperty("evidence_generated_with", out var ge) ? ge : default;
            var hasGen = gen.ValueKind == JsonValueKind.Object;
            var productFace = evPath.StartsWith("eval/", StringComparison.Ordinal)
                              || evPath.StartsWith("docs/reports/", StringComparison.Ordinal);
            if (!hasGen)
            {
                if (productFace && level is "L1" or "L2" or "L3" or "L4")
                    v.Add($"{id}: 产品面证据行缺 evidence_generated_with (R2f)");
            }
            else
            {
                string G(string k) => gen.TryGetProperty(k, out var e) && e.ValueKind == JsonValueKind.String ? e.GetString()! : "";
                foreach (var k in new[] { "evidence_kind", "pin_status", "pin_reason", "artifact_sha12",
                                          "instrument", "instrument_sha12", "binding", "audited_by_round" })
                    if (!gen.TryGetProperty(k, out _)) v.Add($"{id}: evidence_generated_with 缺键 {k} (R2e)");

                var kind = G("evidence_kind");
                var status = G("pin_status");
                var declared = G("artifact_sha12");
                if (kind != "artifact" && kind != "directory" && kind != "self-derived")
                    v.Add($"{id}: evidence_kind 非法 '{kind}' (R2e)");
                if (status != "frozen" && status != "live")
                    v.Add($"{id}: pin_status 非法 '{status}' (R2e)");
                if (!PinReasons.Contains(G("pin_reason")))
                    v.Add($"{id}: pin_reason 非法 '{G("pin_reason")}' (R2e)");
                if (G("binding") != "self-attested" && G("binding") != "audit-pin")
                    v.Add($"{id}: binding 非法 '{G("binding")}' (R2e)");
                // EXP1-Q27: 轮号命名段 —— 主线 R&lt;n&gt; 与能力自检作业 EXP1-Q&lt;n&gt; 互不占号
                //   (作业用**自己的命名段**, 不偷主线轮号; 见 unattended-job-reliability 命名空间碰撞铁律)。
                if (!Regex.IsMatch(G("audited_by_round"), @"^(?:R\d+|EXP1-Q\d+)$"))
                    v.Add($"{id}: audited_by_round 非法 '{G("audited_by_round")}' (R2e)");

                var evAbs = Path.Combine(repoRoot, evPath.Replace('/', Path.DirectorySeparatorChar));
                if (status == "frozen")
                {
                    if (kind != "artifact" && kind != "directory")
                        v.Add($"{id}: frozen 只允许 artifact/directory (实={kind}) (R2e)");
                    if (kind == "directory")
                    {
                        // EXP1-Q27: 目录聚合行的清单式闸 (文件集来自索引, 字节来自工作区)
                        var man = DirManifestSha12(repoRoot, evPath);
                        if (man == null)
                            v.Add($"{id}: frozen 但目录清单不可算 (无已跟踪文件或不可读) '{evPath}' (R2e)");
                        else if (!Hex12.IsMatch(declared) || declared != man)
                            v.Add($"{id}: 目录清单 pin 与现盘不符 (声明 {declared} / 实际 {man}) (R2e —— 目录内已跟踪文件被改写/增删, 证据已易主或未重审)");
                        if (DirRewritten(repoRoot, evPath))
                            v.Add($"{id}: 冻结但目录沿革含改写/删除 '{evPath}' (R2e —— 按设计会变的目录该留 live/evidence-overtaken, 上闸只会产恒红假警)");
                    }
                    else
                    {
                        var cur = Sha12(evAbs);
                        if (cur == null) v.Add($"{id}: frozen 但证据文件不可读 '{evPath}' (R2e)");
                        else if (!Hex12.IsMatch(declared) || declared != cur)
                            v.Add($"{id}: 冻结 pin 与现盘字节不符 (声明 {declared} / 实际 {cur}) (R2e 证据已被改写或未重审)");
                    }
                }
                else if (declared.Length > 0)
                    v.Add($"{id}: live 行不得带 artifact_sha12 (R2e)");

                var inst = G("instrument");
                var isha = G("instrument_sha12");
                if ((inst.Length == 0) != (isha.Length == 0))
                    v.Add($"{id}: instrument 与 instrument_sha12 必须同存同缺 (R2e)");
                if (inst.Length > 0)
                {
                    var cur = Sha12(Path.Combine(repoRoot, inst.Replace('/', Path.DirectorySeparatorChar)));
                    if (cur == null) v.Add($"{id}: instrument 路径不存在 '{inst}' (R2e)");
                    else if (!Hex12.IsMatch(isha) || isha != cur)
                        v.Add($"{id}: 器具绑定与现盘不符 (声明 {isha} / 实际 {cur}) (R2e 器具已改, 引用它的证据须重审)");
                }

                var prov = ProvenanceOf(evAbs);
                if (G("binding") == "self-attested")
                {
                    if (prov == null) v.Add($"{id}: binding=self-attested 但产物无 provenance 自证 (R2e)");
                    else
                    {
                        var pv = prov.Value;
                        var psha = pv.TryGetProperty("instrument_sha12", out var pe) && pe.ValueKind == JsonValueKind.String ? pe.GetString()! : "";
                        if (psha != isha)
                            v.Add($"{id}: 自证器具 sha 与声明不符 (产物 {psha} / 声明 {isha}) (R2e)");
                        var parm = pv.TryGetProperty("arm", out var pa) && pa.ValueKind == JsonValueKind.String ? pa.GetString()! : "";
                        if (parm.Length == 0) v.Add($"{id}: 产物 provenance 缺 arm, 不足以为自证 (R2e)");
                        var pinst = pv.TryGetProperty("instrument", out var pi) && pi.ValueKind == JsonValueKind.String ? pi.GetString()! : "";
                        if (pinst.Length > 0 && inst.Length > 0 && pinst != inst)
                            v.Add($"{id}: 自证器具路径与声明不符 (R2e)");
                    }
                }
                else if (prov != null)
                    v.Add($"{id}: 产物已自证来源, 登记行不得降级为 audit-pin (R2f)");
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
        var shaBind = Sha12(Path.Combine(RepoRoot, "eval/capability/bind_evidence.py"))!;
        var shaInstr = Sha12(Path.Combine(RepoRoot, "eval/capability/instruments.json"))!;
        var bad = ("""
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
            "evidence_cmd": "x", "evidence_path": "agent.sln", "owner_round": "R1" },
          { "id": "k.frozen_sha_mismatch", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/instruments.json", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
              "artifact_sha12": "000000000000", "instrument": "eval/capability/bind_evidence.py", "instrument_sha12": "SHA_BIND",
              "binding": "audit-pin", "audited_by_round": "R473" } },
          { "id": "l.instrument_sha_mismatch", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/kpi.jsonl", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "artifact", "pin_status": "live", "pin_reason": "append-only-ledger",
              "artifact_sha12": null, "instrument": "eval/capability/bind_evidence.py", "instrument_sha12": "000000000000",
              "binding": "audit-pin", "audited_by_round": "R473" } },
          { "id": "m.missing_binding", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/kpi.jsonl", "negative_control": "n", "owner_round": "R1" },
          { "id": "n.false_self_attested", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/instruments.json", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
              "artifact_sha12": "SHA_INSTR", "instrument": "eval/capability/bind_evidence.py", "instrument_sha12": "SHA_BIND",
              "binding": "self-attested", "audited_by_round": "R473" } },
          { "id": "o.bad_kind", "capability": "c", "level": "L1",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/kpi.jsonl", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "banana", "pin_status": "live", "pin_reason": "append-only-ledger",
              "artifact_sha12": null, "instrument": null, "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "R473" } },
          { "id": "q.instrument_without_sha", "capability": "c", "level": "L1",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/kpi.jsonl", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "artifact", "pin_status": "live", "pin_reason": "append-only-ledger",
              "artifact_sha12": null, "instrument": "eval/capability/bind_evidence.py", "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "R473" } },
          { "id": "r.dir_frozen_ok", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/rover/r415/", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "directory", "pin_status": "frozen", "pin_reason": "archived-per-round",
              "artifact_sha12": "SHA_DIR", "instrument": null, "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "EXP1-Q27" } },
          { "id": "s.dir_frozen_sha_mismatch", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/rover/r415/", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "directory", "pin_status": "frozen", "pin_reason": "archived-per-round",
              "artifact_sha12": "000000000000", "instrument": null, "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "R1" } },
          { "id": "t.dir_frozen_empty", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/probe/__pycache__", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "directory", "pin_status": "frozen", "pin_reason": "archived-per-round",
              "artifact_sha12": "000000000000", "instrument": null, "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "R1" } },
          { "id": "u.bad_round", "capability": "c", "level": "L1",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/kpi.jsonl", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "artifact", "pin_status": "live", "pin_reason": "append-only-ledger",
              "artifact_sha12": null, "instrument": null, "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "Q27" } },
          { "id": "v.dir_frozen_churny", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/probe/", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "directory", "pin_status": "frozen", "pin_reason": "archived-per-round",
              "artifact_sha12": "SHA_PROBE", "instrument": null, "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "R1" } },
          { "id": "w.ok_live_overtaken", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/probe/", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "directory", "pin_status": "live", "pin_reason": "evidence-overtaken",
              "artifact_sha12": null, "instrument": null, "instrument_sha12": null,
              "binding": "audit-pin", "audited_by_round": "EXP1-Q27" } },
          { "id": "p.ok_frozen_pin", "capability": "c", "level": "L3",
            "evidence_cmd": "python3 eval/capability/bind_evidence.py --check",
            "evidence_path": "eval/capability/instruments.json", "negative_control": "n", "owner_round": "R1",
            "evidence_generated_with": { "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
              "artifact_sha12": "SHA_INSTR", "instrument": "eval/capability/bind_evidence.py", "instrument_sha12": "SHA_BIND",
              "binding": "audit-pin", "audited_by_round": "R473" } }
        ] }
        """).Replace("SHA_BIND", shaBind).Replace("SHA_INSTR", shaInstr)
             .Replace("SHA_DIR", DirManifestSha12(RepoRoot, "eval/rover/r415/")!)
             .Replace("SHA_PROBE", DirManifestSha12(RepoRoot, "eval/probe/")!);
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
        // R473: evidence_generated_with 的六条注入缺陷 + 一条正控
        Assert.Contains(v, s => s.Contains("k.frozen_sha_mismatch") && s.Contains("冻结 pin"));
        Assert.Contains(v, s => s.Contains("l.instrument_sha_mismatch") && s.Contains("器具绑定"));
        Assert.Contains(v, s => s.Contains("m.missing_binding") && s.Contains("R2f"));
        Assert.Contains(v, s => s.Contains("n.false_self_attested") && s.Contains("自证"));
        Assert.Contains(v, s => s.Contains("o.bad_kind") && s.Contains("evidence_kind"));
        Assert.Contains(v, s => s.Contains("q.instrument_without_sha") && s.Contains("同存同缺"));
        Assert.DoesNotContain(v, s => s.Contains("p.ok_frozen_pin"));   // 正控: 正确冻结 pin 不得判红
        // EXP1-Q27: 目录清单 pin (frozen + evidence_kind=directory) 的两侧样例 + 轮号命名段
        Assert.DoesNotContain(v, s => s.Contains("r.dir_frozen_ok"));    // 正控: 清单摘要相符不得判红
        Assert.Contains(v, s => s.Contains("s.dir_frozen_sha_mismatch") && s.Contains("目录清单 pin"));
        Assert.Contains(v, s => s.Contains("t.dir_frozen_empty") && s.Contains("目录清单不可算"));
        Assert.Contains(v, s => s.Contains("u.bad_round") && s.Contains("audited_by_round"));
        Assert.Contains(v, s => s.Contains("v.dir_frozen_churny") && s.Contains("沿革含改写"));
        Assert.DoesNotContain(v, s => s.Contains("w.ok_live_overtaken"));   // 正控: 沿革会变的目录留 live 不判红
        Assert.True(v.Count >= 21, "注入缺陷未被完整捕获 (实测基线 21 条: 每条注入缺陷 ≥1, q 行同时命中 2 条): " + string.Join(" | ", v));
    }

    /// <summary>R473: 产品面证据的绑定覆盖率与分布 (实测读数; 覆盖由 Validate 判红, 本测试把"字段没退化成注释"钉住)。
    /// 分布 = frozen/live 的原因构成 —— live 行不是缺陷, 是"字节可变故不上闸"的显式声明, 但其条数必须可见。</summary>
    [Fact]
    public void Registry_EvidenceBindings_CoverProductFace()
    {
        var rows = LoadRealRegistry().GetProperty("rows").EnumerateArray().ToList();
        int product = 0, covered = 0, frozen = 0, live = 0, selfAttested = 0, noInstrument = 0;
        foreach (var row in rows)
        {
            var ep = row.GetProperty("evidence_path").GetString()!;
            var lv = row.GetProperty("level").GetString()!;
            var isProduct = ep.StartsWith("eval/", StringComparison.Ordinal) || ep.StartsWith("docs/reports/", StringComparison.Ordinal);
            if (!isProduct || lv == "L0") continue;
            product++;
            if (!row.TryGetProperty("evidence_generated_with", out var g) || g.ValueKind != JsonValueKind.Object) continue;
            covered++;
            var st = g.TryGetProperty("pin_status", out var s) ? s.GetString() : "";
            if (st == "frozen") frozen++; else if (st == "live") live++;
            if (g.TryGetProperty("binding", out var b) && b.GetString() == "self-attested") selfAttested++;
            if (g.TryGetProperty("instrument", out var i) && i.ValueKind == JsonValueKind.Null) noInstrument++;
        }
        Assert.True(product > 0 && covered == product, $"产品面证据绑定覆盖不完整: {covered}/{product} (R2f)");
        Assert.True(frozen > 0, "无任何冻结 pin —— 字段会退化成注释 (R2e 闸门空转)");
        Assert.True(selfAttested >= 1, "自证行消失 —— Q24 缺陷族 (证据静默易主) 的登记层护栏被移除");
        // r444 收口回归钉 (Q24/Q25): 分臂 + 产物自证 + 登记行自证三者仍一致。
        var r444 = rows.First(r => r.GetProperty("id").GetString() == "r444.separability-precheck")
                       .GetProperty("evidence_generated_with");
        Assert.Equal("self-attested", r444.GetProperty("binding").GetString());
        Assert.Equal("eval/rover/r444/precheck_prefilter.py", r444.GetProperty("instrument").GetString());
        // Q27: 轮号命名段扩展为两段 (主线 R<n> / 能力自检作业 EXP1-Q<n>) ⇒ 断言同步放宽为「两段之一」,
        //   而不是把 R 前缀写死 (写死会让作业轮的审计戳判红, 逼作业去偷主线轮号)。
        var r444Round = r444.GetProperty("audited_by_round").GetString()!;
        Assert.True(r444Round.StartsWith("R", StringComparison.Ordinal)
                    || r444Round.StartsWith("EXP1-Q", StringComparison.Ordinal),
            $"r444.separability-precheck 的 audited_by_round 轮号命名段非法: '{r444Round}'");
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
