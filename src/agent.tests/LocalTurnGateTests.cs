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
        // R575 (零词表): 结论区只认**字母标记** S/P (Parse 内的中文词标记已删) ⇒ 三侧都要钉:
        //   ① 结论区字母标记生效; ② 词面回答 ⇒ no_marker (交远端, fail-safe — 不得猜);
        //   ③ 正文里的推理在思考链未闭合时一律不得穿透。
        var skip = TurnGateJudge.Parse(TurnGateJudge.ThinkOpen + "\n分析了半天\n" + TurnGateJudge.ThinkClose + "\nS");
        Assert.True(skip.Decided);
        Assert.Equal(TurnGateVerdict.Skip, skip.Verdict);

        var worded = TurnGateJudge.Parse(TurnGateJudge.ThinkOpen + "\n分析了半天\n" + TurnGateJudge.ThinkClose + "\n无新增");
        Assert.False(worded.Decided);                        // 词面 ⇒ 交远端 (R575: 零词表后不再认词面)
        Assert.Equal("no_marker", worded.Error);

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
    // R575 (零词表): 机械门的信号面只剩**结构信号** —— 问号 / 代码或路径符 / 数字 / 长度 ≥24。
    //   词面信号 (疑问词/请求词/纠正词) 已删 ⇒ 无结构信号的中长句落 r1 字母判官 (不是本地吸收),
    //   由下面的 G26b 钉死「这类真诉求必被认可族否决」。
    [InlineData("另外，测试命令是什么？", true)]                    // 真机被误跳的那条 (问号 ⇒ 结构性 Pass)
    [InlineData("不对，你上一条回答不准确，请重新确认后再回答一次。", true)]  // ≥24 字 ⇒ 结构性 Pass
    [InlineData("帮我加一个 R413 的验收用例", true)]                // 数字
    [InlineData("路径 src/agent.tools 下有个报错", true)]           // 路径符
    [InlineData("跑一下 3 个用例", true)]
    [InlineData("用一句话说明这个仓库的构建命令是什么。", false)]   // 无结构信号 ⇒ 交 r1 (G26b 兜底)
    [InlineData("现在把结论压缩成一行给我。", false)]
    [InlineData("好，按这个来。", false)]                    // 无信号 + 短 ⇒ 才交给 r1
    [InlineData("嗯。", false)]
    [InlineData("收到，谢谢。", false)]
    [InlineData("好，知道了。", false)]
    public void G26_机械前置门_信号族(string msg, bool expectPass)
        => Assert.Equal(expectPass, TurnGateJudge.MechanicalPass(msg));

    [Fact]
    public void G26b_无结构信号的真诉求_必被认可族否决()
    {
        // R575 安全方向 (零词表后**更强**, 不是放宽): 机械门不再用词面拦真诉求 ⇒ 这些句子会落到 r1,
        // 若 r1 误判 Skip, 后置否决 (认可族结构确认) 必须把它翻回 Pass —— 否则用户拿到空话 (R434 事故)。
        foreach (var msg in new[] { "用一句话说明这个仓库的构建命令是什么。", "现在把结论压缩成一行给我。" })
        {
            Assert.False(TurnGateJudge.MechanicalPass(msg), $"该走 r1 的句子: {msg}");
            Assert.False(TurnGateJudge.MechanicalAck(msg), $"认可族必须否决: {msg}");
        }
        // 反向 (否决面不得被误扩成「什么都否决」): 真正的认可短句仍走本地面
        Assert.True(TurnGateJudge.MechanicalAck("好，知道了。"));
        Assert.True(TurnGateJudge.MechanicalAck("收到，谢谢。"));
    }

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
        var src = SourcePin.TextParts("src", "agent", "IndustrialAgentV2.cs");
        var flat = string.Join(' ', src.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        // 正向: 机械门与 r1 判别都必须吃 message.Content (用户本轮原文)
        Assert.Contains("TurnGateJudge.MechanicalPass(message.Content)", flat);
        Assert.Contains("JudgeTurnAsync( message.Content,", flat);
        // 负向: 不得再吃到被追加过 role 块/计划续跑/微提示的 prompt.UserMessage
        Assert.DoesNotContain("MechanicalPass(prompt.UserMessage)", flat);
        Assert.DoesNotContain("JudgeTurnAsync( prompt.UserMessage", flat);
    }

    // ---------- 判据 R434: 门判示例必须落在「残余带」内 (否则该例在生产链里根本到不了本门) ----------
    [Fact]
    public void G30_门判示例必须全部能抵达本门()
    {
        var prompt = TurnGateJudge.BuildPrompt("【占位】", null, null);
        var ex = new List<(string Msg, string Tag)>();
        foreach (var line in prompt.Split('\n'))
        {
            var s = line.Trim();
            if (!s.StartsWith("用户: ", StringComparison.Ordinal)) continue;
            var i = s.LastIndexOf("→", StringComparison.Ordinal);
            if (i < 0) continue;
            ex.Add((s[3..i].Trim(), s[(i + 1)..].Trim()));
        }
        Assert.True(ex.Count >= 6, $"门判示例数过少: {ex.Count}");
        Assert.Contains(ex, e => e.Tag == "S");
        Assert.Contains(ex, e => e.Tag == "P");
        // 承重不变量 (R434 真机根因): **每个 tag 至少要有一条落在残余带内的示例** —— 否则该 tag 在
        // 生产链里对 r1 不可见 (带外示例必被 MechanicalPass 结构性拦下)。实测: 两条 P 例全带信号
        // (另外…/不对…) ⇒ 带内只剩 S 例 ⇒ r1 学到「残余带 ⇒ S」⇒ 恒 Skip ⇒ 3 个真诉求轮被跳成空话。
        foreach (var tag in new[] { "S", "P" })
        {
            Assert.Contains(ex, e => e.Tag == tag && !TurnGateJudge.MechanicalPass(e.Msg));
        }
    }

    // ---------- 判据 R434: 双条件 —— r1 的 Skip 必须再经「认可族」结构确认 ----------
    [Theory]
    [InlineData("谢谢，收到。", true)]
    [InlineData("好的，明白。", true)]
    [InlineData("嗯嗯，知道了。", true)]
    [InlineData("明白，多谢。", true)]
    [InlineData("收到", true)]
    [InlineData("再讲一遍。", false)]        // R434 真机被误跳的真诉求
    [InlineData("讲细一点。", false)]
    [InlineData("换个说法。", false)]
    [InlineData("从头再说。", false)]
    [InlineData("好，按这个来。", false)]    // 保守方向: 非纯认可字符集 ⇒ 走远端
    [InlineData("明白了先生，我要重新说一下需求", false)]
    [InlineData("", false)]
    [InlineData("   ", false)]
    public void G31_认可族结构确认(string msg, bool expectAck)
        => Assert.Equal(expectAck, TurnGateJudge.MechanicalAck(msg));

    [Fact]
    public void G32_链侧必须接双条件()
    {
        var src = SourcePin.TextParts("src", "agent", "IndustrialAgentV2.cs");
        var flat = string.Join(' ', src.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        Assert.Contains("TurnGateJudge.MechanicalAck(message.Content)", flat);
        Assert.Contains("TurnGateVerdict.Pass, \"gate:skip_rejected_nonack\"", flat);
    }

    // ---------- 判据 R444: 廉价必要条件前置 (¬Ack ⇒ 构造性 Pass) ----------
    [Fact]
    public void G33_前置门命中必须可观测()
    {
        var c = new TurnGateCounters();
        Assert.Equal(0, c.MechanicalNonAcks);
        Assert.Equal(0, c.PrefilterViolations);
        c.RecordMechanicalNonAck();
        Assert.Equal(1, c.MechanicalNonAcks);
        Assert.Equal("mechanical:nonack\u2192remote", c.LastBasis);
        Assert.Equal(0, c.Judged);                    // 前置门命中 ⇒ 零判别调用 (省钱的可观测证据)
        c.RecordPrefilterViolation();
        Assert.Equal(1, c.PrefilterViolations);
    }

    [Fact]
    public void G34_链侧Ack必须前置在r1调用之前()
    {
        var src = SourcePin.TextParts("src", "agent", "IndustrialAgentV2.cs");
        var flat = string.Join(' ', src.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        // 正向: 前置门开关存在, 且默认值即「非 0 即开」(默认 = 被测行为)
        Assert.Contains("AGENTFRAMEWORK_GATE_PREFILTER", flat);
        Assert.Contains("\"0\"", flat);
        // 承重: 廉价必要条件 (¬Ack) 的检查位置必须在 JudgeTurnAsync **之前** —
        // 否则省不掉任何 r1 调用, 前置门退化为后置否决 (R444 的增益来源就是这一行位置)。
        var iPre = flat.IndexOf("GatePrefilterOn && !agent.modelqueue.TurnGateJudge.MechanicalAck(message.Content)", StringComparison.Ordinal);
        var iR1 = flat.IndexOf("JudgeTurnAsync( message.Content", StringComparison.Ordinal);
        Assert.True(iPre > 0, "前置门分支缺失");
        Assert.True(iR1 > 0, "r1 判别调用缺失");
        Assert.True(iPre < iR1, "Ack 前置必须早于 r1 调用");
        // fail-closed: 后置否决若在前置门开启时命中, 必须落盘不变量破坏事件 (静默 = 读数反向)
        Assert.Contains("gate_prefilter_invariant_violation", flat);
    }

    // ================= R465: 纯复述族可跳面 + 嵌入通道三态 =================

    // ---------- 判据 R465-A: 纯复述族结构确认 (机械; 白名单字符集 + 回补面) ----------
    [Theory]
    [InlineData("再讲一遍。", true)]           // R434 曾判「真诉求」⇒ R465 起为合法 Skip 面 (回放原文)
    [InlineData("从头再说。", true)]
    [InlineData("再说一遍", true)]
    [InlineData("重复一遍吧", true)]
    [InlineData("你再说一遍。", true)]
    [InlineData("重新讲一遍", true)]
    [InlineData("讲细一点。", false)]          // 要新内容 ⇒ 必须走远端 (且不在白名单字符集内)
    [InlineData("换个说法。", false)]          // 要新内容 ⇒ 必须走远端
    [InlineData("继续", false)]               // 驱动类: 既不 Ack 也不复述 (R449 教训: 不得当采纳)
    [InlineData("继续下一轮", false)]
    [InlineData("你上一条说 3 加 5 等于 9，对吧？", false)]  // 含实体/问号
    [InlineData("把构建命令写成一行。", false)]
    [InlineData("再讲一遍，顺便把命令也写上", false)]        // 加料 ⇒ 不吸收
    [InlineData("", false)]
    [InlineData("   ", false)]
    public void G35_纯复述族结构确认(string msg, bool expectRepeat)
    {
        // R575 (零词表): 吸收面 = **回补库** (LLM 成功轮登记的形状) ⇒ 每行都双侧断言:
        //   · 无补丁 ⇒ 一律交远端 (保守方向; 不猜);
        //   · 该行形状被回补 ⇒ 阳性行必须吸收 (证回补机制**真的接进了判定面**, 不是孤岛)。
        var patches = Patches(agent.nlp.NlpGate.FaceRepeat, msg);
        Assert.False(TurnGateJudge.IsPureRepeat(msg, NoPatches), "无补丁 ⇒ 交远端: " + msg);
        Assert.Equal(expectRepeat, TurnGateJudge.IsPureRepeat(msg, patches));
    }

    // ---------- 判据 R465-B: 复述 Skip 的面必须窄于 Ack 面, 且两道前置都早于 r1 ----------
    [Fact]
    public void G36_复述前置门位置与窄面()
    {
        var src = SourcePin.TextParts("src", "agent", "IndustrialAgentV2.cs");
        var flat = string.Join(' ', src.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        // ① 复述分支必须存在, 且**在** MechanicalPass 之后 (Pass 优先 = 新诉求/疑问永不被复述规则吸收)
        var iPass = flat.IndexOf("TurnGateJudge.MechanicalPass(message.Content)", StringComparison.Ordinal);
        var iRep = flat.IndexOf("TurnGateJudge.IsPureRepeat(message.Content)", StringComparison.Ordinal);
        var iR1 = flat.IndexOf("JudgeTurnAsync( message.Content", StringComparison.Ordinal);
        Assert.True(iPass > 0 && iRep > 0 && iR1 > 0, "分支缺失");
        Assert.True(iPass < iRep, "MechanicalPass 必须优先于复述族 (否则疑问/新诉求会被复述规则吸走)");
        Assert.True(iRep < iR1, "复述前置必须早于 r1 调用 (否则省不掉 r1)");
        // ② 后置否决条件必须已含**每个**前置门 Skip 族 (复述 + 改写), 否则该族 Skip 会被当不变量破坏
        //    而翻 Pass ⇒ 功能静默失效。
        //    R500 真机实证 (3/3 P 臂): 改写族缺豁免 ⇒ 吸收支生效后立即被否决,
        //    t8 basis=gate:skip_rejected_nonack 且同轮落 gate_prefilter_invariant_violation ⇒ 通道成死代码。
        Assert.Contains("&& !agent.modelqueue.TurnGateJudge.IsPureRepeat(message.Content)", flat);
        Assert.Contains("&& !agent.modelqueue.LocalParaphraseChannel.ShouldAbsorb(", flat);
        // ③ 改写支必须早于 ¬Ack 前置支 (否则改写族被 else-if 链吞掉 ⇒ 静默不生效; R498 位置纪律)
        var iPara = flat.IndexOf("LocalParaphraseChannel.ShouldAbsorb(", StringComparison.Ordinal);
        var iNonAck = flat.IndexOf("mechanical:nonack", StringComparison.Ordinal);
        Assert.True(iPara > 0 && iNonAck > 0 && iPara < iNonAck, "改写支必须早于 ¬Ack 前置支");
        // ④ 计数可见
        Assert.Contains("RecordMechanicalRepeat", flat);
        Assert.Contains("prefilter_repeat", flat);
    }

    // ---------- 判据 R465-C: 复述 Skip 的本地消化 = 回放上一条答复原文 (非兜底串) ----------
    [Fact]
    public void G37_复述Skip必须回放上一条答复()
    {
        var src = SourcePin.TextParts("src", "agent", "IndustrialAgentV2.cs");
        var code = StripLineComments(src);
        Assert.Contains("GetConversationHistoryAsync(message.SessionId, ct)", code);
        // R466 口径单源: 主链只准**引用常量** (字面值只准出现在 ContinuationBrief)
        // —— 两处各写一份字符串必漂移, 漂移后优先级规则静默失效 (R466 收口面读同一口径)
        Assert.Contains("ContinuationBrief.SettleRepeatVerbatim", code);
        Assert.DoesNotContain("\"repeat_verbatim\"", code);
        var cb = StripLineComments(SourcePin.TextParts("src", "agent", "context", "ContinuationBrief.cs"));
        Assert.Contains("public const string SettleRepeatVerbatim = \"repeat_verbatim\";", cb);
        Assert.Contains("MessageRole.Assistant", code);
        // 兜底必须仍在 (取不到上一条答复时不得抛、不得走远端)
        Assert.Contains("ComposeLocalSkipReplyAsync", code);
    }

    private static string StripLineComments(string src)
    {
        var kept = new List<string>();
        foreach (var l in src.Split('\n'))
        {
            var s = l.TrimStart();
            if (s.StartsWith("//", StringComparison.Ordinal)) continue;
            kept.Add(l);
        }
        return string.Join(' ', kept);
    }

    // ---------- 判据 R465-D: 嵌入 (bge) 通道三态 (与生成通道同形纪律) ----------
    [Fact]
    public void G38_嵌入通道三态解析()
    {
        var missing = Path.Combine(Path.GetTempPath(), "r465-not-exist-bge.gguf");
        var r1 = agent.llamacpp.LocalChannelWiring.ResolveEmbedder(true, missing, missing);
        Assert.True(r1.ConfigMismatch, "声明却缺失必须判错配");
        Assert.StartsWith(agent.llamacpp.LocalChannelWiring.EmbedderMismatchMarker, r1.Warning ?? "");
        Assert.Equal(string.Empty, r1.ModelPath);                 // 不回退默认 = 不静默替换意图

        var r2 = agent.llamacpp.LocalChannelWiring.ResolveEmbedder(false, null, missing);
        Assert.False(r2.ConfigMismatch);
        Assert.StartsWith(agent.llamacpp.LocalChannelWiring.EmbedderDefaultMissingMarker, r2.Warning ?? "");

        var r3 = agent.llamacpp.LocalChannelWiring.ResolveEmbedder(false, null, null!);
        Assert.False(r3.ConfigMismatch);
        Assert.NotNull(r3.Warning);

        // 默认路径单一来源: FromEnvironment 的兜底 == DefaultModelPath (两处各写一份 ⇒ 会漂移)
        Assert.Equal(agent.llamacpp.LlamaCppEmbedderOptions.DefaultModelPath,
            agent.llamacpp.LlamaCppEmbedderOptions.FromEnvironment().ModelPath);
    }

    // ---------- 判据 R465-E: 接线侧必须真的调用同形解析器 (机检; 先剥注释 ⇒ 注释不可满足) ----------
    [Fact]
    public void G39_嵌入接线必须调用同形解析器()
    {
        var src = SourcePin.TextParts("src", "agent", "extensions", "ServiceCollectionExtensions.cs");
        var code = StripLineComments(src);
        var iEmb = code.IndexOf("ITextEmbedder", StringComparison.Ordinal);
        Assert.True(iEmb > 0, "嵌入注册缺失");
        var iResolve = code.IndexOf("LocalChannelWiring.ResolveEmbedder", StringComparison.Ordinal);
        Assert.True(iResolve > iEmb, "嵌入注册处没有调用三态解析器 (声明却缺失仍会静默空心)");
        Assert.Contains("EmbedderWiring", code);
    }

    // ---------- 判据 R466: 复述回放优先级必须在收口面被消费, 且结算类单源 ----------
    // 缺陷 (R465 实测): 收口面 `if (!grounded) → 承接反问` 无条件覆盖本地已结算的复述回放
    // (t6 应回放 21 字符, 实得 46 字符承接反问) ⇒ 预注册 C3 FAIL。修法 = 优先级判据单源 + 默认开。
    [Fact]
    public void G40_复述结算优先于承接反问且单源()
    {
        var src = SourcePin.TextParts("src", "agent", "IndustrialAgentV2.cs");
        var code = StripLineComments(src);
        var flat = string.Join(' ', code.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));

        // ① skip 支把结算类写入单一变量 (打点与收口面读同一处)
        var iWrite = flat.IndexOf("_localSettleKind = replyKind", StringComparison.Ordinal);
        Assert.True(iWrite > 0, "skip 支没有记录本地结算类 (收口面无从判定优先级)");
        Assert.DoesNotContain("(\"kind\", prevReply is null ?", flat);   // 旧的两处各写一份字面已消除

        // ② 收口面必须消费同源判据 (不得再无条件覆盖); 位置纪律: 写入早于消费
        var iUse = flat.IndexOf("ContinuationBrief.ShouldApplyFallback(", StringComparison.Ordinal);
        Assert.True(iUse > iWrite, "收口面没有消费优先级判据 ⇒ 复述回放仍会被承接反问覆盖");
        Assert.Contains("if (applyFallback)", flat);

        // ③ 消融开关可见 + 抑制必须落盘 (静默抑制 = 读数与真实走向相反)
        Assert.Contains("AGENTFRAMEWORK_CONTINUATION_REPEAT_PRIORITY", flat);
        Assert.Contains("(\"suppressed\",", flat);
        Assert.Contains("(\"priority\",", flat);

        // ④ 逐轮清零 (粘滞 ⇒ 下一轮的承接反问被误抑制)
        Assert.Contains("_localSettleKind = null", flat);
    }
}
