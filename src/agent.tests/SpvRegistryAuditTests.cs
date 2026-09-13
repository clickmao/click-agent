using Xunit;
using clickrover.gpu.spirv;

namespace agent.tests;

/// <summary>
/// v0.23.0 · vulkan: 手写 SPIR-V 常量表 vs Khronos 权威 registry 的机检 (独立 oracle)。
///
/// 为什么必须存在: 汇编器 (<see cref="Spv"/>) / 结构校验器 (<see cref="SpirvValidator"/>) / 反汇编器
/// (<see cref="SpvDisassembler"/>) **共用同一张手写常量表** —— 表里抄错一个号, 三者会互相印证同一个错误。
/// R389-vulkan 真机实证: <c>OpUGreaterThanEqual</c> 抄成 179 (规范 174)、<c>OpConvertUToF</c> 抄成 111
/// (规范 112): 结构校验报 valid、反汇编"逐字正确", 而设备执行的是另一条指令 (守卫退化为带符号比较 ⇒ 失效),
/// 表现为"dispatch 成功但动态索引写全部越界不可见"。
///
/// 判别力要求: 负向控制组必须红 (改错 opcode / 枚举 / GLSL.std.450 号各一例, 加一例伪造常量)。
/// 无判别力的审计 = 未验证。
/// </summary>
public sealed class SpvRegistryAuditTests
{
    const string SpvCs = "src/click-rover/Gpu/Spirv/Spv.cs";
    const string ValidatorCs = "src/click-rover/Gpu/Spirv/SpirvValidator.cs";
    const string CoreGrammar = "src/click-rover/Gpu/Spirv/registry/spirv.core.grammar.json";
    const string GlslGrammar = "src/click-rover/Gpu/Spirv/registry/extinst.glsl.std.450.grammar.json";

    static string RepoRoot()
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        for (int i = 0; i < 12 && d is not null; i++, d = d.Parent)
            if (Directory.Exists(Path.Combine(d.FullName, "src", "click-rover")) &&
                Directory.Exists(Path.Combine(d.FullName, "docs")))
                return d.FullName;
        throw new InvalidOperationException($"repo root not found from {AppContext.BaseDirectory}");
    }

    static (string Core, string Glsl, string Spv, string Validator) Load()
    {
        var root = RepoRoot();
        return (File.ReadAllText(Path.Combine(root, CoreGrammar)),
                File.ReadAllText(Path.Combine(root, GlslGrammar)),
                File.ReadAllText(Path.Combine(root, SpvCs)),
                File.ReadAllText(Path.Combine(root, ValidatorCs)));
    }

    static SpvRegistryAudit.Report Audit(string core, string glsl, string spv, string validator) =>
        SpvRegistryAudit.Run(core, glsl, (SpvCs, spv), (ValidatorCs, validator));

    // ── 正向: 现行常量表必须与权威 registry 完全一致, 且不留"无法核对"项 ────────────

    [Fact]
    public void Audit_CurrentConstants_MatchAuthoritativeRegistry()
    {
        var (core, glsl, spv, validator) = Load();
        var r = Audit(core, glsl, spv, validator);

        Assert.True(r.Unverified.Count == 0, "存在无法核对的常量 (未测到 ≠ 测过): " + string.Join(" | ", r.Unverified));
        Assert.True(r.Mismatches.Count == 0,
            "常量与权威 registry 不符: " + string.Join(" | ", r.Mismatches.Select(m => $"{m.File}:{m.Line} {m.Constant} ours={m.Ours} registry={m.Expected} ({m.Registry})")));
        // 覆盖度下限: 防止提取器静默失效 (提取不到任何常量也会"全绿")
        Assert.True(r.Checked >= 100, $"实际核对条数 {r.Checked} < 100 —— 常量块被漏扫 (下限同时是漂移告警: 常量增删须显式更新此数)");
    }

    // ── 负向控制 1: opcode 表抄错必须被抓 (R389-vulkan 真 bug 原样复现) ─────────────

    [Fact]
    public void Audit_CorruptedOpcode_IsDetected()
    {
        var (core, glsl, spv, validator) = Load();
        var broken = spv.Replace("OpUGreaterThanEqual = 174", "OpUGreaterThanEqual = 179", StringComparison.Ordinal);
        Assert.NotEqual(spv, broken);

        var r = Audit(core, glsl, broken, validator);

        var m = Assert.Single(r.Mismatches);
        Assert.Equal("OpUGreaterThanEqual", m.Constant);
        Assert.Equal(179u, m.Ours);
        Assert.Equal(174u, m.Expected);
    }

    // ── 负向控制 2: 枚举表抄错必须被抓 ────────────────────────────────────────

    [Fact]
    public void Audit_CorruptedDecoration_IsDetected()
    {
        var (core, glsl, spv, validator) = Load();
        var broken = spv.Replace("DecBinding = 33", "DecBinding = 34", StringComparison.Ordinal);
        Assert.NotEqual(spv, broken);

        var r = Audit(core, glsl, broken, validator);

        var m = Assert.Single(r.Mismatches);
        Assert.Equal("DecBinding", m.Constant);
        Assert.Equal("Decoration/Binding", m.Registry);
        Assert.Equal(33u, m.Expected);
    }

    // ── 负向控制 3: GLSL.std.450 扩展指令号抄错必须被抓 ────────────────────────

    [Fact]
    public void Audit_CorruptedGlslExtInst_IsDetected()
    {
        var (core, glsl, spv, validator) = Load();
        var broken = spv.Replace("GlslExp = 27", "GlslExp = 31", StringComparison.Ordinal);
        Assert.NotEqual(spv, broken);

        var r = Audit(core, glsl, broken, validator);

        var m = Assert.Single(r.Mismatches);
        Assert.Equal("GlslExp", m.Constant);
        Assert.Equal("GLSL.std.450/Exp", m.Registry);
        Assert.Equal(27u, m.Expected);
    }

    // ── 负向控制 4: 表外常量必须进"无法核对"而不是被静默放过 ──────────────────────

    [Fact]
    public void Audit_UnknownConstant_IsReportedUnverified()
    {
        var (core, glsl, spv, validator) = Load();
        var broken = spv.Replace("GlslExp = 27", "GlslExp = 27;\n    public const uint OpTotallyFake = 3;", StringComparison.Ordinal);
        Assert.NotEqual(spv, broken);

        var r = Audit(core, glsl, broken, validator);

        Assert.Empty(r.Mismatches);
        Assert.Contains(r.Unverified, u => u.Contains("OpTotallyFake", StringComparison.Ordinal));
    }

    // ── 提取器边界: 只扫常量声明块, 不吃局部变量 (否则噪声淹没真信号) ──────────────

    [Fact]
    public void Extract_ScansConstBlocksOnly_IgnoresLocalVariables()
    {
        const string snippet = """
            public const uint OpFoo = 1, Bar = 2;
            void M() { for (int i = 0; i < 3; i++) { int j = 9; } }
            """;
        var names = SpvRegistryAudit.Extract(snippet).Select(x => x.Name).ToList();

        Assert.Equal(["OpFoo", "Bar"], names);
    }
}
