using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R426 机检: **关系判官本地化** —— CorrectionDetector 的 L2 微判定 (C/A/N) 改走本地 r1,
/// 让「跳过轮」真正做到 0 次远端调用 (R425 证伪 C_c/C_g 的残留 = 每轮 ~45 tok 的远端判官调用)。
///
/// 反空心纪律: 本地不可用 / 空回 / 思考链截断 / 结论区无字母 / 记账违规 ⇒ 一律<b>未判定</b>
/// (返回 null, 调用方必须降级远端; 「没测到」≠"给个结论"), 并逐条计数可观测。
/// 取消必须上抛。开关默认关 ⇒ 逐位零回归。
/// </summary>
public sealed class RelationJudgeLocalizationTests
{
    private const string KeyEnv = "R426_RELJUDGE_FAKE_KEY";
    static RelationJudgeLocalizationTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    // ---------- 假端口 ----------
    private sealed class FakePort : ILocalGenerationPort
    {
        public Func<LocalGenerationRequest, LocalGenerationOutcome> Behavior = _ => Ok("<think>x</think>\n\nA");
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

        public static LocalGenerationOutcome Truncated()
            => new() { Success = true, Content = "<think>我正在想用户上一轮说……", TokensEvaluated = 100, PromptNewTokens = 16, CachedTokens = 84 };

        public static LocalGenerationOutcome BadAccounting()
            => new() { Success = true, Content = "<think>x</think>\n\nC", TokensEvaluated = 999, PromptNewTokens = 16, CachedTokens = 84 };
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
    private static ModelCatalog Catalog(bool relationJudge)
        => new()
        {
            Models =
            {
                new ModelCatalogEntry
                {
                    Id = "r426-remote", Provider = "deepseek", Endpoint = "http://127.0.0.1:1/v1",
                    ApiKeyEnv = KeyEnv, PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 5,
                    CodingScore = 5, ContextWindow = 64000, SuitedFor = { "chat" },
                },
            },
            LocalChannel = new LocalChannelConfig
            {
                ModelPath = "x.gguf",
                ContextSize = 4608,
                MaxTokens = 64,
                MaxPromptTokens = 2048,
                TurnGate = false,
                RelationJudge = relationJudge,
            },
        };

    private static ModelQueueRouter Router(ModelCatalog catalog, ILocalGenerationPort? port)
        => new(catalog, new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance, localPort: port);

    private const string Sys = "只输出一个字母。";
    private const string User = "判定用户消息相对上一轮回答: 上一轮回答: 收到。 / 用户消息: 好，知道了。 只输出一个字母。";

    // ---------- J1..J3 开关语义 (默认关 = 零回归) ----------
    [Fact]
    public void J1_配置relation_judge默认关_判官不本地化()
    {
        var router = Router(Catalog(relationJudge: false), new FakePort());
        Assert.False(router.RelationJudgeEnabled);
        Assert.Equal(0, router.RelationJudge.Attempts);
    }

    [Fact]
    public void J2_配置开但无端口_判官不本地化()
    {
        Assert.False(Router(Catalog(relationJudge: true), port: null).RelationJudgeEnabled);
    }

    [Fact]
    public void J3_配置开且有端口_判官本地化()
    {
        Assert.True(Router(Catalog(relationJudge: true), new FakePort()).RelationJudgeEnabled);
    }

    // ---------- J4 正常路径: 思考链里的 C 不得胜出 ----------
    [Fact]
    public async Task J4_本地判官_取思考链之后的结论字母()
    {
        var port = new FakePort { Behavior = _ => FakePort.Ok("<think>我看到选项有 C(纠正) 与 A(采纳)，用户说「好」所以是采纳</think>\n\nA", generated: 37) };
        var router = Router(Catalog(relationJudge: true), port);
        var r = await router.JudgeRelationLocalAsync(Sys, User);
        Assert.NotNull(r);
        Assert.Equal("A", r!.Letter);
        Assert.Equal(37, r.CompletionTokens);
        Assert.Equal(1, router.RelationJudge.Local);
        Assert.Equal(0, router.RelationJudge.Fallback);
    }

    [Fact]
    public async Task J5_本地判官_请求形态钉死_系统行与用户行与最大token()
    {
        var port = new FakePort();
        var router = Router(Catalog(relationJudge: true), port);
        await router.JudgeRelationLocalAsync(Sys, User);
        var req = port.LastRequest!;
        Assert.Equal("r426:relation-judge", req.SessionKey);     // 稳定会话键 ⇒ 前缀缓存可命中
        Assert.Equal(2, req.Turns.Count);
        Assert.Equal(Sys, req.Turns[0].Content);
        Assert.Equal(User, req.Turns[1].Content);
        Assert.Equal(512, req.MaxTokens);                        // 本地不受调用方 64/128 tok 微预算约束 (R413: 截断在推理中途 ⇒ 未判定)
    }

    // ---------- J6..J9 失败可见 (「没测到」≠ 给结论) ----------
    [Fact]
    public async Task J6_端口失败_未判定且计数可见()
    {
        var router = Router(Catalog(relationJudge: true), new FakePort { Behavior = _ => FakePort.Failed() });
        Assert.Null(await router.JudgeRelationLocalAsync(Sys, User));
        Assert.Equal(1, router.RelationJudge.Fallback);
        Assert.Equal(0, router.RelationJudge.Local);
        Assert.Contains("failed_or_empty", router.RelationJudge.LastSource!);
    }

    [Fact]
    public async Task J7_空回_未判定且计数可见()
    {
        var router = Router(Catalog(relationJudge: true), new FakePort { Behavior = _ => FakePort.Empty() });
        Assert.Null(await router.JudgeRelationLocalAsync(Sys, User));
        Assert.Equal(1, router.RelationJudge.Fallback);
    }

    [Fact]
    public async Task J8_思考链截断_未判定_绝不猜()
    {
        var router = Router(Catalog(relationJudge: true), new FakePort { Behavior = _ => FakePort.Truncated() });
        Assert.Null(await router.JudgeRelationLocalAsync(Sys, User));
        Assert.Equal(1, router.RelationJudge.Fallback);
        Assert.Contains("unparsed", router.RelationJudge.LastSource!);
    }

    [Fact]
    public async Task J9_记账违规_未判定且单独计数()
    {
        var router = Router(Catalog(relationJudge: true), new FakePort { Behavior = _ => FakePort.BadAccounting() });
        Assert.Null(await router.JudgeRelationLocalAsync(Sys, User));
        Assert.Equal(1, router.RelationJudge.AccountingViolations);
        Assert.Equal(0, router.RelationJudge.Fallback);   // 违规单列; 调用方因 null 而落远端兜底
        Assert.Equal(0, router.RelationJudge.Local);
    }

    [Fact]
    public async Task J10_取消上抛_不得吞()
    {
        var router = Router(Catalog(relationJudge: true), new CancelPort());
        await Assert.ThrowsAsync<OperationCanceledException>(() => router.JudgeRelationLocalAsync(Sys, User));
    }

    [Fact]
    public async Task J11_端口异常_未判定且带原因()
    {
        var router = Router(Catalog(relationJudge: true), new BoomPort());
        Assert.Null(await router.JudgeRelationLocalAsync(Sys, User));
        Assert.Contains("InvalidOperationException", router.RelationJudge.LastSource!);
    }

    // ---------- J12..J13 纯函数规范化 (语言/形态无关铁律: 只在闭合思考链后的结论区找独立字母) ----------
    [Theory]
    [InlineData("<think>我先想想 C 还是 A</think>\n\nN", "N")]
    [InlineData("A", "A")]
    [InlineData("  n  ", "N")]
    [InlineData("答案：C", "C")]
    [InlineData("所以用户是采纳，应输出 A。", "A")]
    public void J12_规范化_取结论区字母(string raw, string expect)
    {
        Assert.True(RelationLetterJudge.TryNormalize(raw, out var letter));
        Assert.Equal(expect, letter);
    }

    [Theory]
    [InlineData("这是采纳")]              // 结论区无独立字母 (中文) ⇒ 未判定, 交远端
    [InlineData("<think>用户说好，我应该输出 A")] // 有开无闭 = 截断 ⇒ 未判定
    [InlineData("neither")]                // 英文词内字母不得命中
    [InlineData("")]
    [InlineData("   ")]
    [InlineData(null)]
    public void J13_规范化_不确定就说不确定(string? raw)
    {
        Assert.False(RelationLetterJudge.TryNormalize(raw, out var letter));
        Assert.Equal(string.Empty, letter);
    }

    // ---------- J14 配置解析 ----------
    [Fact]
    public void J14_配置解析relation_judge()
    {
        var root = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..");
        var src = Path.Combine(root, "config");
        if (!File.Exists(Path.Combine(src, "base", "models.yaml"))) return; // 无仓库布局 ⇒ 跳过
        var dir = Path.Combine(Path.GetTempPath(), "r426-cfg-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(dir, "base"));
        foreach (var f in Directory.GetFiles(Path.Combine(src, "base")))
            File.Copy(f, Path.Combine(dir, "base", Path.GetFileName(f)), overwrite: true);
        var models = Path.Combine(dir, "base", "models.yaml");
        var baseYaml = File.ReadAllText(models);

        File.WriteAllText(models, baseYaml + "\nlocal:\n  model_path: /tmp/x.gguf\n  turn_gate: true\n  relation_judge: true\n");
        Assert.True(ModelCatalog.Load(new agent.config.ConfigSnapshot(dir)).LocalChannel.RelationJudge);

        File.WriteAllText(models, baseYaml + "\nlocal:\n  model_path: /tmp/x.gguf\n  turn_gate: true\n");
        Assert.False(ModelCatalog.Load(new agent.config.ConfigSnapshot(dir)).LocalChannel.RelationJudge);
        Directory.Delete(dir, recursive: true);
    }
}
