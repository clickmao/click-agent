using agent.exploration;
using Xunit;
using Xunit.Abstractions;

namespace agentframework.tests;

/// <summary>
/// v0.13.2 G1 — 格式修复收敛环单测。
/// 核心回放: 用户提供的破损 JSON 实例; 循环语义 (①→⑤); 技能-校验矩阵; LLM 轮数上限。
/// </summary>
public class FormatRepairTests
{
    private readonly ITestOutputHelper _out;
    public FormatRepairTests(ITestOutputHelper output) => _out = output;

    private static JsonRepairPlugin NewJson() => new();

    // ── 修复器规则族 ──
    [Fact]
    public void User_Instance_Repaired()
    {
        // 用户钦定实例: {"cmd": "exec", "args": [null, undefined, {"nested": }}} 
        var p = NewJson();
        var broken = "{\"cmd\": \"exec\", \"args\": [null, undefined, {\"nested\": }}}";
        var (fixedText, changed) = p.Repair(broken);
        _out.WriteLine(fixedText);
        Assert.Empty(p.Validate(fixedText)); // 修复后必须过原生 parser
        Assert.True(changed >= 2);
        // 语义断言: undefined→null, nested→{}, 多余}删除:
        Assert.Contains("\"nested\":{}", fixedText.Replace(" ", "")); // 语义断言: nested 值为空对象 (空白不敏感)
        Assert.DoesNotContain("undefined", fixedText);
    }

    [Fact]
    public void Single_Quotes_And_Python_Literals()
    {
        var p = NewJson();
        var (fixedText, _) = p.Repair("{'a': True, 'b': None}");
        Assert.Empty(p.Validate(fixedText));
    }

    [Fact]
    public void Trailing_Comma_Removed()
    {
        var p = NewJson();
        var (fixedText, _) = p.Repair("{\"a\": 1,}");
        Assert.Empty(p.Validate(fixedText));
    }

    [Fact]
    public void Valid_Json_Untouched()
    {
        var p = NewJson();
        var (fixedText, changed) = p.Repair("{\"a\": [1, 2]}");
        Assert.Equal("{\"a\": [1, 2]}", fixedText);
        Assert.Equal(0, changed);
    }

    // ── ①块提取 ──
    [Fact]
    public void Fenced_Block_Extracted()
    {
        var reply = "修复后的 JSON：\n\n```json\n{\"cmd\": \"exec\"}\n```\n以上是修复点。";
        var block = FormatRepairLoop.ExtractFenced(reply, "json");
        Assert.Equal("{\"cmd\": \"exec\"}", block);
    }

    [Fact]
    public void No_Fence_Returns_Null()
    {
        Assert.Null(FormatRepairLoop.ExtractFenced("修复了但没放块内 {\"a\":1}", "json"));
    }

    // ── ②独立查找 ──
    [Fact]
    public void FindCandidate_In_Prose()
    {
        var p = NewJson();
        var r = p.FindCandidate("根据分析 结果如下 {\"a\": 1, \"b\": [2]} 请查收");
        Assert.NotNull(r);
        var slice = "根据分析 结果如下 {\"a\": 1, \"b\": [2]} 请查收".Substring(r!.Value.Start, r.Value.Length);
        Assert.Equal("{\"a\": 1, \"b\": [2]}", slice);
    }

    // ── 收敛环 (LLM 模拟注入) ──
    [Fact]
    public async Task Loop_First_Round_Fenced_Pass()
    {
        var reg = new FormatRepairRegistry(new IFormatRepairPlugin[] { NewJson() });
        var loop = new FormatRepairLoop(reg);
        var llmReply = "```json\n{\"a\": undefined}\n```";
        var llmCalls = 0;
        var (text, passed, trail) = await loop.RunAsync("json", "", llmReply, (_, _) =>
        {
            llmCalls++;
            return Task.FromResult("");
        });
        Assert.True(passed);
        Assert.Equal(0, llmCalls); // 本地修复一步到位, 无需 LLM
        Assert.Empty(new JsonRepairPlugin().Validate(text));
    }

    [Fact]
    public async Task Loop_Llm_Retry_Then_Pass()
    {
        var reg = new FormatRepairRegistry(new IFormatRepairPlugin[] { NewJson() });
        var loop = new FormatRepairLoop(reg);
        var llmReply = "这个格式我没法放进代码块 直接告诉你吧"; // 无块无候选 → LLM 轮
        var (text, passed, trail) = await loop.RunAsync("json", "", llmReply, (_, _) =>
            Task.FromResult("```json\n{\"ok\": true}\n```"));
        Assert.True(passed);
        Assert.Contains("\"ok\"", text);
        Assert.Contains(trail, s => s.Stage == "llm_round");
    }

    [Fact]
    public async Task Loop_Exhausts_After_MaxRounds()
    {
        var reg = new FormatRepairRegistry(new IFormatRepairPlugin[] { NewJson() });
        var loop = new FormatRepairLoop(reg, new FormatRepairConfig { MaxLlmRounds = 2 });
        var calls = 0;
        var (_, passed, trail) = await loop.RunAsync("json", "", "没有任何格式内容", (_, _) =>
        {
            calls++;
            return Task.FromResult("还是没有");
        });
        Assert.False(passed);
        Assert.Equal(2, calls); // 恰好 max 轮 (用户钦定可计数)
        Assert.Contains(trail, s => s.Stage == "exhaust");
    }

    // ── 技能-校验矩阵 (用户钦定硬性) ──
    [Fact]
    public void Matrix_No_Plugin_No_Repair()
    {
        var reg = new FormatRepairRegistry(Array.Empty<IFormatRepairPlugin>());
        Assert.Null(reg.Get("yaml"));
        Assert.False(reg.HasValidator("yaml"));
        Assert.False(reg.HasLocalRepairer("yaml"));
    }

    [Fact]
    public void Matrix_Generic_Only_Means_No_Local_Repairer()
    {
        // ✓技能+✓校验(经 generic)+✗本地程序 → 全程 LLM (④不可用):
        var reg = new FormatRepairRegistry(new IFormatRepairPlugin[] { new JsonRepairPlugin() });
        Assert.True(reg.HasLocalRepairer("json"));
        Assert.False(reg.HasLocalRepairer("yaml")); // 无 yaml 专用 → 通用降级无④
    }

    [Fact]
    public async Task Matrix_No_Validation_Skips_Repair_Entirely()
    {
        // 用户钦定: 找到技能但没有校验机制 → 不进入循环修复步骤①:
        var reg = new FormatRepairRegistry(Array.Empty<IFormatRepairPlugin>());
        var loop = new FormatRepairLoop(reg);
        var llmCalls = 0;
        var (text, passed, trail) = await loop.RunAsync("yaml", "", "key: value", (_, _) =>
        {
            llmCalls++;
            return Task.FromResult("");
        });
        Assert.False(passed);
        Assert.Equal(0, llmCalls); // 未进入修复
        Assert.Contains(trail, s => s.Stage == "matrix");
    }
}
