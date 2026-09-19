using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

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

    private static string ReadSrc(params string[] parts) => SourcePin.TextParts(parts);

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

    /// <summary>R575: 回补集合 (单条) —— 面标 + 签名, 与判定侧 (<c>NlpGate.IsPatched</c>) 看同一个键。</summary>
    private static HashSet<string> Patches(string face, params string[] texts)
    {
        var set = new HashSet<string>(StringComparer.Ordinal);
        foreach (var t in texts)
            set.Add(agent.nlp.NlpGate.Key(face, agent.nlp.NlpGate.SignatureOf(t)));
        return set;
    }

    /// <summary>「无补丁」的**确定性**形态 (显式空集, 不读进程级回补库 ⇒ 与执行顺序无关)。</summary>
    private static readonly HashSet<string> NoPatches = new(StringComparer.Ordinal);

    [Fact]
    public void R497D_WhitelistChars_Unchanged()
    {
        var src = ReadSrc("src", "agent.modelqueue", "TurnGateJudge.cs");
        var m = Regex.Match(src, @"RepeatFamilyChars\s*=\s*""([^""]*)"";");
        Assert.True(m.Success, "RepeatFamilyChars 未找到");
        Assert.Equal(R465FamilyChars, m.Groups[1].Value);   // R465 逐字节不变 ⇒ 字符集是**结构护栏**, 不变
    }

    [Fact]
    public void R497D_NewMarkers_OnlyWhitelistedChars()
    {
        // R575: 标记表已删 (零词表, 吸收面 = `agent.nlp.NlpGate` 回补库) ⇒ 本用例改为钉**同一不变式**的两侧:
        //   ① 产品侧不再有复述标记表 (旧断言「新标记的用字必须都在白名单里」失去对象);
        //   ② 回补**不能越过**白名单字符集 —— 含内容字的形状即便被回补也仍不吸收 (R434 硬线);
        //   ③ 反向: 白名单内的形状被回补 ⇒ 必须吸收 (表删了不等于机制没了)。
        var src = ReadSrc("src", "agent.modelqueue", "TurnGateJudge.cs");
        Assert.DoesNotContain("RepeatMarkers", src, StringComparison.Ordinal);
        foreach (var mk in new[] { "重做一遍。", "讲细一点。", "继续下一轮", "把代码再讲一遍。" })
        {
            Assert.False(TurnGateJudge.IsRepeatShape(mk), $"结构面本应否决 (含内容字): {mk}");
            Assert.False(TurnGateJudge.IsPureRepeat(mk, Patches(agent.nlp.NlpGate.FaceRepeat, mk)),
                $"回补越过了白名单 ⇒ 吸收了含内容字的形状: {mk}");
        }
        Assert.True(TurnGateJudge.IsPureRepeat("念一遍", Patches(agent.nlp.NlpGate.FaceRepeat, "念一遍")),
            "白名单内的形状被回补后必须吸收 (否则回补面是死代码)");
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
    // R575 语义变更 (如实登记, 不是放宽): 旧判据靠**标记表**排除这两句 (表外 ⇒ 不吸收);
    //   标记表删除后判据 = 白名单结构面 ∧ 回补命中 —— 两句都属白名单内形状 ⇒ **一旦被回补即吸收**
    //   (语义仍正确: 「重来一遍/再来一次」= 原样重来 ⇒ 本地回放即所需)。
    [InlineData("重来一遍。", true)]
    [InlineData("再来一次。", true)]
    // R434 硬线 + 白名单纪律: 一律不吸收 (含内容字/超族)
    [InlineData("讲细一点。", false)]
    [InlineData("换个说法。", false)]
    [InlineData("重做一遍。", false)]            // 含「做」(内容字, 不在白名单) ⇒ 结构面先否决
    [InlineData("把上一条说一遍，顺便改下代码", false)]
    [InlineData("继续下一轮", false)]
    public void R497D_SynonymRepeat_Face(string msg, bool expectRepeat)
    {
        // R575 (零词表): 吸收面 = 回补库 ⇒ 双侧断言 (无补丁 ⇒ 交远端 / 回补命中 ⇒ 吸收)。
        Assert.False(TurnGateJudge.IsPureRepeat(msg, NoPatches), "无补丁 ⇒ 必须交远端: " + msg);
        Assert.Equal(expectRepeat, TurnGateJudge.IsPureRepeat(msg, Patches(agent.nlp.NlpGate.FaceRepeat, msg)));
    }

    [Theory]
    // 优先级铁律: 前置门链是 MechanicalPass **先**、复述吸收**后**。
    // R575 (零词表): Pass 信号只剩**结构信号** (问号 / 路径符或反引号 / 数字 / ≥24 字) ⇒ 用这些构造。
    [InlineData("从头念一遍。", true)]
    [InlineData("念一遍。", true)]
    [InlineData("复述一次。", true)]
    [InlineData("重复一遍。", true)]
    [InlineData("把上面那句说一遍/", false)]              // 路径符 ⇒ 机械放行抢先 (白名单形状也吸不走)
    [InlineData("从头再说一遍，顺便看下第 2 点", false)]   // 数字 ⇒ 机械放行抢先
    [InlineData("换个说法，为什么？", false)]             // 问号 ⇒ 机械放行抢先
    public void R497D_AbsorbedFace_MechanicalPassWins(string msg, bool expectAbsorbed)
    {
        var patches = Patches(agent.nlp.NlpGate.FaceRepeat, msg);
        Assert.Equal(expectAbsorbed, !TurnGateJudge.MechanicalPass(msg) && TurnGateJudge.IsPureRepeat(msg, patches));
    }

    [Fact]
    public void R497D_OldFamily_NotNarrowed()
    {
        // R575: 旧族 7 句在**回补命中**时仍全部可吸收 (吸收面不因机制换代而收窄); 无补丁时一律交远端。
        foreach (var msg in new[] { "再讲一遍。", "从头再说。", "再说一遍", "重复一遍吧", "你再说一遍。", "重新讲一遍", "再说下" })
        {
            Assert.False(TurnGateJudge.IsPureRepeat(msg, NoPatches), "无补丁 ⇒ 交远端: " + msg);
            Assert.True(TurnGateJudge.IsPureRepeat(msg, Patches(agent.nlp.NlpGate.FaceRepeat, msg)), "旧族被收窄: " + msg);
        }
    }
}
