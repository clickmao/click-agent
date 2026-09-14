using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R413 机检: **前置门 (Local Turn Gate)** —— 本地 r1 判别「本轮是否携带新增诉求」,
/// 判 Skip ⇒ 链跳过远端主调用 (省整轮 prompt); 其余一切 ⇒ 降级远端。
///
/// 反空心纪律: 无法解析 / 失败 / 空回 / 记账违规 ⇒ <c>Decided=false</c> 且必须能被调用方看到降级
/// (「没测到」≠「假」; 增益不得建立在"猜"上)。取消必须上抛。
/// 计数与依据 (Judged/Skipped/Passed/Degraded/AccountingViolations/LastBasis) 全部可观测。
/// </summary>
public sealed class LocalTurnGateTests
{
    private const string KeyEnv = "R413_GATE_FAKE_KEY";
    static LocalTurnGateTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    // ---------- 假端口 ----------
    private sealed class FakePort : ILocalGenerationPort
    {
        public Func<LocalGenerationRequest, LocalGenerationOutcome> Behavior = _ => Ok("S");
        public int Calls;
        public LocalGenerationRequest? LastRequest;

        public bool IsAvailable => true;
        public string BackendId => "fake";

        public Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default)
        {
            Calls++;
            LastRequest = request;
            return Task.FromResult(Behavior(request));
        }

        public static LocalGenerationOutcome Ok(string content, int evaluated = 100, int cached = 84, int generated = 2)
            => new()
            {
                Success = true,
                Content = content,
                TokensEvaluated = evaluated,
                PromptNewTokens = evaluated - cached,
                CachedTokens = cached,
                GeneratedTokens = generated,
                Model = "local:fake",
            };

        public static LocalGenerationOutcome Failed(string error = "port_error")
            => new() { Success = false, Content = string.Empty, Error = error };

        public static LocalGenerationOutcome Empty()
            => new() { Success = true, Content = "   ", TokensEvaluated = 100, PromptNewTokens = 16, CachedTokens = 84 };
    }

    private sealed class CancelPort : ILocalGenerationPort
    {
        public bool IsAvailable => true;
        public string BackendId => "cancel";
        public Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default)
            => throw new OperationCanceledException("用户取消");
    }

    private sealed class BoomPort : ILocalGenerationPort
    {
        public bool IsAvailable => true;
        public string BackendId => "boom";
        public Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default)
            => throw new InvalidOperationException("端口崩了");
    }

    // ---------- 夹具 ----------
    private static string ReadyModelFile()
    {
        var path = Path.Combine(Path.GetTempPath(), $"r413-gate-{Guid.NewGuid():N}.gguf");
        File.WriteAllText(path, "stub");
        return path;
    }

    private static ModelCatalog Catalog(string localModelPath, bool turnGate)
        => new()
        {
            Models =
            {
                new ModelCatalogEntry
                {
                    Id = "r413-remote", Provider = "deepseek", Endpoint = "http://127.0.0.1:1/v1",
                    ApiKeyEnv = KeyEnv, PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 5,
                    CodingScore = 5, ContextWindow = 64000, SuitedFor = { "chat" },
                },
            },
            LocalChannel = new LocalChannelConfig
            {
                ModelPath = localModelPath,
                ContextSize = 4608,
                MaxTokens = 64,
                MaxPromptTokens = 2048,
                TurnGate = turnGate,
            },
        };

    private static ModelQueueRouter Router(ModelCatalog catalog, ILocalGenerationPort? port)
        => new(catalog, new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance, localPort: port);

    // ---------- 判据 1: 开关语义 (默认关 = 零回归) ----------
    [Fact]
    public void G1_配置turn_gate为假_门禁用()
    {
        var path = ReadyModelFile();
        try
        {
            var router = Router(Catalog(path, turnGate: false), new FakePort());
            Assert.False(router.TurnGateEnabled);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void G2_配置开启但无端口_门禁用()
    {
        var path = ReadyModelFile();
        try
        {
            var router = Router(Catalog(path, turnGate: true), port: null);
            Assert.False(router.TurnGateEnabled);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void G3_配置开启且有端口_门启用()
    {
        var path = ReadyModelFile();
        try
        {
            var router = Router(Catalog(path, turnGate: true), new FakePort());
            Assert.True(router.TurnGateEnabled);
        }
        finally { File.Delete(path); }
    }

    // ---------- 判据 2: 判别语义 ----------
    [Fact]
    public async Task G4_本地输出S_判无新增_计skip()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("S") };
            var router = Router(Catalog(path, turnGate: true), port);
            var outcome = await router.JudgeTurnAsync("好，按这个来。", "你是严谨的工程师", "【Role 成长经历】\nrag: 赏1/罚0 → 观察中");
            Assert.True(outcome.Decided);
            Assert.Equal(TurnGateVerdict.Skip, outcome.Verdict);
            Assert.Equal(1, router.TurnGate.Judged);
            Assert.Equal(1, router.TurnGate.Skipped);
            Assert.Equal(0, router.TurnGate.Passed);
            Assert.Equal(1, port.Calls);
            // 挂载 role 额外数据: prompt 必须真带上 (不是"接口有字段")
            var sent = port.LastRequest!.Turns[0].Content;
            Assert.Contains("你是严谨的工程师", sent);
            Assert.Contains("Role 成长经历", sent);
            Assert.Contains("好，按这个来。", sent);
            Assert.Equal(512, port.LastRequest.MaxTokens);   // 真链实测: 思考链可达 250-350 tok ⇒ 上限必须给足   // R413 实测: 思考链需要余量
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G5_本地输出P_判有新增_计pass()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("P") };
            var router = Router(Catalog(path, turnGate: true), port);
            var outcome = await router.JudgeTurnAsync("把结论压缩成一行给我", null, null);
            Assert.True(outcome.Decided);
            Assert.Equal(TurnGateVerdict.Pass, outcome.Verdict);
            Assert.Equal(1, router.TurnGate.Passed);
            Assert.Equal(0, router.TurnGate.Skipped);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G6_输出含解释_S仍被独立词规则认出()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("分析后判断: S") };
            var router = Router(Catalog(path, turnGate: true), port);
            var outcome = await router.JudgeTurnAsync("收到", null, null);
            Assert.True(outcome.Decided);
            Assert.Equal(TurnGateVerdict.Skip, outcome.Verdict);
        }
        finally { File.Delete(path); }
    }

    // ---------- 判据 3: 不确定性必须降级 (绝不猜) ----------
    [Fact]
    public async Task G7_输出无法解析_未决且计降级_不得当skip()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("无") };
            var router = Router(Catalog(path, turnGate: true), port);
            var outcome = await router.JudgeTurnAsync("收到", null, null);
            Assert.False(outcome.Decided);
            Assert.Equal(0, router.TurnGate.Skipped);
            Assert.Equal(1, router.TurnGate.Degraded);
            Assert.Contains("degraded", router.TurnGate.LastBasis);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G8_端口失败_未决且计降级()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Failed() };
            var router = Router(Catalog(path, turnGate: true), port);
            var outcome = await router.JudgeTurnAsync("收到", null, null);
            Assert.False(outcome.Decided);
            Assert.Equal(1, router.TurnGate.Degraded);
            Assert.Equal(0, router.TurnGate.Skipped);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G9_空内容_未决且计降级()
    {
        var path = ReadyModelFile();
        try
        {
            var router = Router(Catalog(path, turnGate: true), new FakePort { Behavior = _ => FakePort.Empty() });
            var outcome = await router.JudgeTurnAsync("收到", null, null);
            Assert.False(outcome.Decided);
            Assert.Equal(1, router.TurnGate.Degraded);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G10_记账违规_未决且单独计数()
    {
        var path = ReadyModelFile();
        try
        {
            // tokens_evaluated(100) != prompt_n(1) + cache_n(1) ⇒ 记账恒等破裂
            var bad = new LocalGenerationOutcome
            {
                Success = true, Content = "S", TokensEvaluated = 100, PromptNewTokens = 1, CachedTokens = 1,
            };
            var router = Router(Catalog(path, turnGate: true), new FakePort { Behavior = _ => bad });
            var outcome = await router.JudgeTurnAsync("收到", null, null);
            Assert.False(outcome.Decided);
            Assert.Equal(1, router.TurnGate.AccountingViolations);
            Assert.Equal(0, router.TurnGate.Skipped);
            Assert.Contains("accounting_violation", router.TurnGate.LastBasis);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G11_端口抛取消_必须上抛()
    {
        var path = ReadyModelFile();
        try
        {
            var router = Router(Catalog(path, turnGate: true), new CancelPort());
            await Assert.ThrowsAnyAsync<OperationCanceledException>(
                () => router.JudgeTurnAsync("收到", null, null));
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G12_端口抛其他异常_不抛穿且计降级()
    {
        var path = ReadyModelFile();
        try
        {
            var router = Router(Catalog(path, turnGate: true), new BoomPort());
            var outcome = await router.JudgeTurnAsync("收到", null, null);
            Assert.False(outcome.Decided);
            Assert.Equal(1, router.TurnGate.Degraded);
            Assert.Contains("InvalidOperationException", router.TurnGate.LastBasis);
        }
        finally { File.Delete(path); }
    }

    // ---------- 判据 4: 被跳过轮的回复 = 非 LLM 模板 (真机实证: LLM 生成会复读/反问) ----------
    [Fact]
    public async Task G13_被跳过轮_非LLM模板_且不发本地生成()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("不应被调用") };
            var router = Router(Catalog(path, turnGate: true), port);
            var reply = await router.ComposeLocalSkipReplyAsync("好，按这个来。");
            Assert.Equal(ModelQueueRouter.LocalSkipFallback, reply);
            Assert.Equal(0, port.Calls);                     // 纯确认轮不得过 LLM (零 token / 零幻觉)
            Assert.Equal(1, router.TurnGate.TemplateAcks);
            Assert.False(string.IsNullOrWhiteSpace(reply));  // 有回复不变式
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task G14_无端口_模板回复依然有回复()
    {
        var path = ReadyModelFile();
        try
        {
            var router = Router(Catalog(path, turnGate: true), port: null);
            var reply = await router.ComposeLocalSkipReplyAsync("好");
            Assert.Equal(ModelQueueRouter.LocalSkipFallback, reply);
        }
        finally { File.Delete(path); }
    }

    // ---------- 判据 5: 纯解析 (无端口依赖) ----------
    [Theory]
    [InlineData("S", true, TurnGateVerdict.Skip)]
    [InlineData("P", true, TurnGateVerdict.Pass)]
    [InlineData("  s \n", true, TurnGateVerdict.Skip)]       // R413 实测: r1 会输出小写 ⇒ 结论区小写同样认 (只在结论区)
    [InlineData("Skip it", false, TurnGateVerdict.Pass)]     // 单词内不认
    [InlineData("", false, TurnGateVerdict.Pass)]
    [InlineData("   ", false, TurnGateVerdict.Pass)]
    [InlineData("结论: P 因为用户提了新要求", true, TurnGateVerdict.Pass)]
    [InlineData("结论: S", true, TurnGateVerdict.Skip)]
    public void G15_解析规则_未决即降级(string raw, bool decided, TurnGateVerdict verdict)
    {
        var outcome = TurnGateJudge.Parse(raw);
        Assert.Equal(decided, outcome.Decided);
        if (decided) Assert.Equal(verdict, outcome.Verdict);
    }

    [Fact]
    public void G16_判别prompt_无role数据时不出现空块()
    {
        var prompt = TurnGateJudge.BuildPrompt("继续", null, null);
        Assert.Contains("继续", prompt);
        Assert.DoesNotContain("【角色设定】", prompt);
        Assert.Contains("答案:", prompt);
        var ack = TurnGateJudge.BuildAckPrompt("谢谢");
        Assert.Contains("谢谢", ack);
    }

    // ---------- 判据 2b: 推理正文不得当结论 (R413 真机实证: r1 思考链会同时吐出两类词) ----------
    [Fact]
    public void G17_思考链正文含无新增但结论为P_必须判P()
    {
        var raw = TurnGateJudge.ThinkOpen + "\n用户说「收到，谢谢」，属于无新增的确认，所以可能是 S。但用户还追问了……\n" +
                  new string('。', 60) + "\n" + TurnGateJudge.ThinkClose + "\nP";
        var o = TurnGateJudge.Parse(raw);
        Assert.True(o.Decided, $"必须可判, 实际={o.Error}");
        Assert.Equal(TurnGateVerdict.Pass, o.Verdict);
        Assert.True(o.Raw.Contains(TurnGateJudge.ThinkOpen), "未判定也必须带回原文");
    }

    [Fact]
    public void G18_思考链被max_tokens截断_未判定且降级()
    {
        var raw = TurnGateJudge.ThinkOpen + "\n好，我现在需要判断用户的消息“嗯。”是否携带新的诉求或新信息。";
        var o = TurnGateJudge.Parse(raw);
        Assert.False(o.Decided);
        Assert.Equal("thinking_truncated", o.Error);
        Assert.Equal(raw.Trim(), o.Raw);            // 未判定也必须带回原文 (对账纪律)
    }

    [Fact]
    public void G19_结论区为空_未判定()
    {
        var o = TurnGateJudge.Parse(TurnGateJudge.ThinkOpen + "\n想了想\n" + TurnGateJudge.ThinkClose + "\n   ");
        Assert.False(o.Decided);
        Assert.Equal("empty_conclusion", o.Error);
    }

    [Fact]
    public void G20_只看结论区_正文噪声不得穿透()
    {
        var skip = TurnGateJudge.Parse(TurnGateJudge.ThinkOpen + "\n分析了半天\n" + TurnGateJudge.ThinkClose + "\n无新增");
        Assert.True(skip.Decided);
        Assert.Equal(TurnGateVerdict.Skip, skip.Verdict);

        // 正文说「有新增」但思考链没闭合 (被截断) ⇒ 必须降级, 绝不把正文当结论
        var noise = TurnGateJudge.Parse(TurnGateJudge.ThinkOpen + "\n这条是有新增的诉求，应该是 P\n" + new string('x', 40) + "\n\n");
        Assert.False(noise.Decided);
        Assert.Equal("thinking_truncated", noise.Error);
    }

    // ---------- 出参净化: 思考链不得回显给用户 (R413 真机实证) ----------
    [Fact]
    public void G21_StripThinking_有闭合_只留结论()
    {
        var raw = "推理内容...\n" + TurnGateJudge.ThinkOpen + "\n用户只是确认, 记 S。\n" + TurnGateJudge.ThinkClose + "\n\nS";
        Assert.Equal("S", TurnGateJudge.StripThinking(raw));
    }

    [Fact]
    public void G22_StripThinking_截断在思考链中_返回空串()
    {
        var raw = TurnGateJudge.ThinkOpen + "\n好，我需要判断用户的消息是否……";
        Assert.Equal(string.Empty, TurnGateJudge.StripThinking(raw));
    }

    [Fact]
    public void G23_StripThinking_无思考块_原样返回()
    {
        Assert.Equal("收到。", TurnGateJudge.StripThinking("  收到。  "));
        Assert.Equal(string.Empty, TurnGateJudge.StripThinking(null));
    }

    // ---------- 真机原文回归 (R413 臂B 遥测实录, 2026-09-14) ----------
    // 这条原文在真机被判成 thinking_truncated —— 根因是源码里的尖括号字面量被写入通道吃掉
    // (文件里只剩开标记), 解析器实际在搜空串。本用例把它钉死: 原文必须判 Skip。
    [Fact]
    public void G24_真机原文_思考链闭合_必须判Skip()
    {
        var raw = TurnGateJudge.ThinkOpen + "\n判断用户的消息是否携带新的诉求或新信息。用户的消息是“嗯。”，这是一个简单的确认，" +
                  "没有提到任何新的问题或信息。根据规则，S代表无新增，所以这里应该标记为S。\n" + TurnGateJudge.ThinkClose + "\n\nS";
        var o = TurnGateJudge.Parse(raw);
        Assert.True(o.Decided, $"真机原文必须判得出来, 实际 error={o.Error}");
        Assert.Equal(TurnGateVerdict.Skip, o.Verdict);
    }

    // ---------- 常量形态自检 (字符码构造, 免疫任何写入通道) ----------
    [Fact]
    public void G25_思考链常量必须是ASCII闭合标记()
    {
        var tc = new string(new[] { (char)60, (char)47, 't', 'h', 'i', 'n', 'k', (char)62 });
        var to = new string(new[] { (char)60, 't', 'h', 'i', 'n', 'k', (char)62 });
        Assert.True(tc == TurnGateJudge.ThinkClose,
            $"ThinkClose 实际={string.Join(",", TurnGateJudge.ThinkClose.Select(c => (int)c))} len={TurnGateJudge.ThinkClose.Length}");
        Assert.True(to == TurnGateJudge.ThinkOpen,
            $"ThinkOpen 实际={string.Join(",", TurnGateJudge.ThinkOpen.Select(c => (int)c))} len={TurnGateJudge.ThinkOpen.Length}");
    }

    // ---------- 判据 6: 机械前置门 (零 token; 结构性消掉假阴性) ----------
    [Theory]
    [InlineData("另外，测试命令是什么？", true)]                    // 真机被误跳的那条
    [InlineData("不对，你上一条回答不准确，请重新确认后再回答一次。", true)]  // 真机被误跳的那条
    [InlineData("用一句话说明这个仓库的构建命令是什么。", true)]
    [InlineData("现在把结论压缩成一行给我。", true)]
    [InlineData("帮我加一个 R413 的验收用例", true)]
    [InlineData("路径 src/agent.tools 下有个报错", true)]
    [InlineData("跑一下 3 个用例", true)]
    [InlineData("好，按这个来。", false)]                    // 无信号 + 短 ⇒ 才交给 r1
    [InlineData("嗯。", false)]
    [InlineData("收到，谢谢。", false)]
    [InlineData("好，知道了。", false)]
    public void G26_机械前置门_信号族(string msg, bool expectPass)
        => Assert.Equal(expectPass, TurnGateJudge.MechanicalPass(msg));

    [Fact]
    public void G27_机械门_空或不认识的消息保守走远端()
    {
        Assert.True(TurnGateJudge.MechanicalPass("   "));
        Assert.True(TurnGateJudge.MechanicalPass(null));
        Assert.True(TurnGateJudge.MechanicalPass("这是一条足够长的消息，没有任何关键词但内容很长，应该保守走远端。"));  // ≥24 字符
    }

    [Fact]
    public void G28_机械门命中_计数可见且未询问r1()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("S") };
            var router = Router(Catalog(path, turnGate: true), port);
            router.TurnGate.RecordMechanicalPass();
            Assert.Equal(1, router.TurnGate.MechanicalPasses);
            Assert.Equal(0, router.TurnGate.Judged);        // 机械命中 ⇒ 零判别调用
            Assert.Equal("mechanical:pass→remote", router.TurnGate.LastBasis);
        }
        finally { File.Delete(path); }
    }

    // ---------- 判据 7: 链侧门入参 = 用户本轮原文 (真机事故回归: 判 enriched prompt ⇒ 门恒 Pass, 增益归零) ----------
    private static string FindRepoRootG29()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    [Fact]
    public void G29_链侧门入参必须是用户原文()
    {
        var src = File.ReadAllText(Path.Combine(FindRepoRootG29(), "src", "agent", "IndustrialAgentV2.cs"));
        var flat = string.Join(' ', src.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        // 正向: 机械门与 r1 判别都必须吃 message.Content (用户本轮原文)
        Assert.Contains("TurnGateJudge.MechanicalPass(message.Content)", flat);
        Assert.Contains("JudgeTurnAsync( message.Content,", flat);
        // 负向: 不得再吃到被追加过 role 块/计划续跑/微提示的 prompt.UserMessage
        Assert.DoesNotContain("MechanicalPass(prompt.UserMessage)", flat);
        Assert.DoesNotContain("JudgeTurnAsync( prompt.UserMessage", flat);
    }
}
