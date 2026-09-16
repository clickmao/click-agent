using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using agent.modelqueue;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R497 判据表 (两条产品面改动各一组正/负控, 全部只吃**结构量**)：
///   ① 打点面真值收口: `local_decision_ledger` 打点只准留指纹 (code8/key_id), 禁 raw 码;
///      —— R496 实测: raw 码写进 data/telemetry/host.jsonl ⇒ 臂可读工作区里就有真值 (nonrecompute Q4 命中)。
///   ④ 复述同义族扩面: 只加**语义等价**标记, 不动白名单字符集 (加字符会连带吸收「重来一遍/重做一遍」= 重做真诉求)。
/// </summary>
[Collection(AgentTelemetryStaticCollection.Name)]
public sealed class R497FingerprintAndSynonymTests
{
    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static string ReadSrc(params string[] parts) =>
        File.ReadAllText(Path.Combine(new[] { RepoRoot() }.Concat(parts).ToArray()));

    // ── ① 打点面: 只留指纹 ─────────────────────────────────────────────────────

    private static string LedgerEmitBlock()
    {
        var src = ReadSrc("src", "agent", "IndustrialAgentV2.cs");
        var i = src.IndexOf("AgentTelemetry.Emit(\"local_decision_ledger\"", StringComparison.Ordinal);
        Assert.True(i > 0, "找不到 local_decision_ledger 打点调用");
        var j = src.IndexOf(");", i, StringComparison.Ordinal);
        Assert.True(j > i, "打点调用未闭合");
        return src.Substring(i, j - i);
    }

    [Fact]
    public void R497A_Telemetry_OnlyFingerprints()
    {
        var block = LedgerEmitBlock();
        Assert.Contains("\"code8\"", block);                                   // 码的 sha8
        Assert.Contains("\"key_id\"", block);                                  // 进程密钥指纹
        Assert.DoesNotContain("\"code\",", block);                             // 旧: raw 码直写 (破口)
        Assert.Contains("LocalDecisionLedger.Code8(ledgerCode)", block);        // 必须**派生自真值**而非另算
        Assert.Contains("LocalDecisionLedger.KeyId()", block);
    }

    [Fact]
    public void R497A_NoRawCodeEmit_RepoWide()
    {
        // 全仓 .cs 扫描: 任何对 **账本 raw 码** 的打点/落盘直写都必须为 0 (定义处与测试自己的负控除外)。
        // R497 自抓: 初版正则 [A-Za-z_.]*[Cc]ode\b 过宽, 误伤无关字段 (FrontendApiContract.cs 的 errCode =
        //   HTTP 错误码, 与账本真值无关) ⇒ 收窄为「第二参名含 ledger/LCM」, 既覆盖旧写法 ("code", ledgerCode)
        //   又不再误伤无关 "code" 字段; 无关站点的清单见下方 allowlist (只增不改是禁的: 增了就要重审)。
        var root = Path.Combine(RepoRoot(), "src");
        var allowFiles = new[]
        {
            // 无关 "code" 字段 (语言标签 / HTTP 错误码 / upstream 错误对象 / JSON 属性名), 均为**非账本**语义
            "ModelQueueRouter.cs", "ResponsesWire.cs", "CogViewClient.cs", "Program.cs",
            "SpectreOutputRenderer.cs", "FrontendApiContract.cs", "TendencyData.cs", "BochaSearchProvider.cs",
        };
        var rx = new Regex("\"code\"\\s*,\\s*[A-Za-z_.]*(?:[Ll]edger|LCM)[A-Za-z_]*");
        var offenders = Directory.EnumerateFiles(root, "*.cs", SearchOption.AllDirectories)
            .Where(p => !p.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}"))
            .Where(p => !p.EndsWith("LocalDecisionLedger.cs", StringComparison.Ordinal))
            .Where(p => !p.EndsWith("R497FingerprintAndSynonymTests.cs", StringComparison.Ordinal))
            .Where(p => !allowFiles.Contains(Path.GetFileName(p)))
            .SelectMany(p => rx.Matches(File.ReadAllText(p)).Select(m => $"{Path.GetFileName(p)}:{m.Value}"))
            .ToList();
        Assert.True(offenders.Count == 0, "raw 码直写打点面: " + string.Join(" | ", offenders));
    }

    [Fact]
    public void R497A_Code8_IsFingerprintNotTruth()
    {
        LocalDecisionLedger.ResetForTests();
        var code = LocalDecisionLedger.CheckCode("s-497");
        Assert.StartsWith(LocalDecisionLedger.CodePrefix, code, StringComparison.Ordinal);
        var fp = LocalDecisionLedger.Code8(code);
        Assert.Equal(8, fp.Length);
        Assert.NotEqual(code, fp);
        Assert.False(code.Contains(fp, StringComparison.Ordinal), "指纹不得是码的子串 (否则等价于真值)");
        Assert.Equal(fp, LocalDecisionLedger.Code8(code));                      // 确定性
    }

    [Fact]
    public void R497A_KeyId_KeyFingerprintOnly()
    {
        var a = new byte[32];
        var b = new byte[32];
        for (var i = 0; i < 32; i++) { a[i] = (byte)(3 + i); b[i] = (byte)(200 - i); }
        LocalDecisionLedger.SetKeyForTests(a);
        var ka = LocalDecisionLedger.KeyId();
        LocalDecisionLedger.SetKeyForTests(b);
        var kb = LocalDecisionLedger.KeyId();
        Assert.Equal(8, ka.Length);
        Assert.NotEqual(ka, kb);                                               // 密钥变 ⇒ 指纹变
        Assert.DoesNotContain(Convert.ToHexString(a).ToLowerInvariant(), ka);   // 指纹 ≠ 密钥字节
    }

    // ── ④ 复述同义族扩面: 加标记, 不加字符 ──────────────────────────────────────

    private const string R465FamilyChars = "再讲遍次重复述从头说要你上面那条这句话的来回新下念看给把一吧哦嗯啊呀啦哇";

    private static string[] RepeatMarkersOfProduct()
    {
        var src = ReadSrc("src", "agent.modelqueue", "LocalGenerationPort.cs");
        var m = Regex.Match(src, @"string\[\]\s+RepeatMarkers\s*=\s*\{(.*?)\};", RegexOptions.Singleline);
        Assert.True(m.Success, "RepeatMarkers 未找到");
        return Regex.Matches(m.Groups[1].Value, "\"((?:[^\"\\\\]|\\\\.)*)\"").Select(x => x.Groups[1].Value).ToArray();
    }

    [Fact]
    public void R497D_WhitelistChars_Unchanged()
    {
        var src = ReadSrc("src", "agent.modelqueue", "LocalGenerationPort.cs");
        var m = Regex.Match(src, @"RepeatFamilyChars\s*=\s*""([^""]*)"";");
        Assert.True(m.Success, "RepeatFamilyChars 未找到");
        Assert.Equal(R465FamilyChars, m.Groups[1].Value);   // R465 逐字节不变 ⇒ 吸收面只增标记
    }

    [Fact]
    public void R497D_NewMarkers_OnlyWhitelistedChars()
    {
        foreach (var mk in new[] { "复述一次", "说一遍", "讲一遍", "念一遍" })
        {
            Assert.Contains(mk, RepeatMarkersOfProduct());
            foreach (var ch in mk)
                Assert.True(R465FamilyChars.IndexOf(ch) >= 0, $"标记 {mk} 用字 {ch} 不在 R465 白名单内 ⇒ 必须改白名单");
        }
    }

    [Theory]
    // 新增吸收面 (语义 = 把上一条答复原样给我 ⇒ 本地回放正确)
    [InlineData("把上一条说一遍。", true)]
    [InlineData("从头讲一遍", true)]
    [InlineData("念一遍", true)]
    [InlineData("复述一次吧", true)]
    [InlineData("把上面那句说一遍", true)]
    // R497 自抓: 「重」**本来就在** R465 白名单里 (字面 "遍次重复述" 含「重」), 故新标记「念一遍」上线后
    //   「重念一遍」被吸收 —— 语义正确 (原样再来一遍 ⇒ 本地回放即所需), 把它从负控改为正控。
    [InlineData("重念一遍。", true)]
    [InlineData("重说一遍", true)]
    // R434 硬线 + 白名单纪律: 一律不吸收 (真诉求 / 重做 / 新内容)
    [InlineData("讲细一点。", false)]
    [InlineData("换个说法。", false)]
    [InlineData("重来一遍。", false)]            // 标记表内无「重来一遍」⇒ 不因白名单而误吸收
    [InlineData("重做一遍。", false)]
    [InlineData("再来一次。", false)]
    [InlineData("把上一条说一遍，顺便改下代码", false)]
    [InlineData("继续下一轮", false)]
    public void R497D_SynonymRepeat_Face(string msg, bool expectRepeat)
        => Assert.Equal(expectRepeat, TurnGateJudge.IsPureRepeat(msg));

    [Theory]
    // 优先级铁律 (R497 自抓): 前置门链是 MechanicalPass **先**、复述吸收**后** ⇒ 含请求信号(把/说/请/给我…)、
    //   数字、问号、`/`、反引号、≥24 字的复述同义句**不会**被本地消化, 照旧走远端。
    //   ⇒ ④「同义重复轮本地生成扩面」的**可用**吸收面 = 不含上述信号的复述句 (下面的 true 行)。
    [InlineData("从头念一遍。", true)]
    [InlineData("念一遍。", true)]
    [InlineData("复述一次。", true)]
    [InlineData("重复一遍。", true)]
    [InlineData("把上一条说一遍。", false)]     // 「把」= 请求信号 ⇒ 机械放行抢先 (初版 t17 就踩在这上面)
    [InlineData("把上一句讲一遍", false)]
    [InlineData("从头再说一遍，顺便看下第 2 点", false)]
    public void R497D_AbsorbedFace_MechanicalPassWins(string msg, bool expectAbsorbed)
        => Assert.Equal(expectAbsorbed, !TurnGateJudge.MechanicalPass(msg) && TurnGateJudge.IsPureRepeat(msg));

    [Fact]
    public void R497D_OldFamily_NotNarrowed()
    {
        foreach (var msg in new[] { "再讲一遍。", "从头再说。", "再说一遍", "重复一遍吧", "你再说一遍。", "重新讲一遍", "再说下" })
            Assert.True(TurnGateJudge.IsPureRepeat(msg), "旧族被收窄: " + msg);
    }
}
