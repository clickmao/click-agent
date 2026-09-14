using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R413 机检: **本地生成通道接线** —— 判据预注册 (配置→请求形态→端口), 端口可替换, 计数与降级可见。
///
/// 立规背景 (用户 2026-09-14 口径): R351 移除的是**旧的「本地 LLM 使用」路径**; 新增 r1 本地生成
/// 是「整理能力 → 精炼合理化链管道 → 提高 KPI」计划节点 ⇒ 必须有可替换执行面端口 + 数值对账 +
/// 被使用计数 + 无设备负控 (「没测到」≠「通过」)。
///
/// 反例纪律: 每个"不该走本地"的分支都必须断言 <c>Attempted==0</c> 且**远端真被调用**(真有 HTTP 往返),
/// 否则"拒绝"与"静默吞掉"无法区分。
/// </summary>
public sealed class LocalChannelDispatchTests
{
    private const string KeyEnv = "R413_FAKE_KEY";
    private const string RemoteReply = "远端答案";
    static LocalChannelDispatchTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    // ---------- 假端口 (可替换执行面; 记录调用) ----------
    private sealed class FakePort : ILocalGenerationPort
    {
        public bool Available = true;
        public Func<LocalGenerationRequest, LocalGenerationOutcome> Behavior = _ => Ok("本地产出");
        public int Calls;
        public LocalGenerationRequest? LastRequest;

        public bool IsAvailable => Available;
        public string BackendId => "fake";
        public Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default)
        {
            Calls++;
            LastRequest = request;
            return Task.FromResult(Behavior(request));
        }

        public static LocalGenerationOutcome Ok(string content, int evaluated = 4340, int cached = 4322, int generated = 18)
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
    }

    private sealed class ThrowingPort : ILocalGenerationPort
    {
        public bool IsAvailable => true;
        public string BackendId => "throwing";
        public Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default)
            => throw new OperationCanceledException("用户取消");
    }

    // ---------- 夹具 ----------
    private static string ReadyModelFile()
    {
        var path = Path.Combine(Path.GetTempPath(), $"r413-{Guid.NewGuid():N}.gguf");
        File.WriteAllText(path, "stub");
        return path;
    }

    private static ModelCatalog Catalog(string endpoint, string? localModelPath, bool allowGeneral = false,
        int maxPromptTokens = 2048)
    {
        var catalog = new ModelCatalog
        {
            Models =
            {
                new ModelCatalogEntry
                {
                    Id = "r413-remote", Provider = "deepseek", Endpoint = endpoint, ApiKeyEnv = KeyEnv,
                    PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 5, CodingScore = 5, ContextWindow = 64000,
                    SuitedFor = { "chat", "summary", "classify" },
                },
            },
        };
        if (localModelPath is not null)
        {
            catalog.LocalChannel = new LocalChannelConfig
            {
                ModelPath = localModelPath,
                ContextSize = 4608,
                MaxTokens = 128,
                MaxPromptTokens = maxPromptTokens,
                AllowGeneral = allowGeneral,
            };
        }
        return catalog;
    }

    private static ModelQueueRouter Router(FakeLlmEndpoint fake, ModelCatalog catalog, ILocalGenerationPort? port)
        => new(catalog, new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance, localPort: port);

    private static QueuePrompt Prompt(string user = "把这段标注一下", int estimated = 300)
        => new() { UserMessage = user, EstimatedTokens = estimated, SessionId = "s1", TurnIndex = 2 };

    // ---------- 判据: 配置层 ----------
    [Fact]
    public void J2a_通道未配置_拒绝channel_disabled_且未尝试()
    {
        var decision = LocalChannelPolicy.Evaluate(Prompt(), TaskKindHint.KeywordTagging,
            new LocalChannelConfig(), port: null);
        Assert.False(decision.Allowed);
        Assert.Equal(LocalChannelRejectReason.ChannelDisabled, decision.Reason);
    }

    [Fact]
    public void J2b_配置就绪但无端口_拒绝port_missing()
    {
        var path = ReadyModelFile();
        try
        {
            var decision = LocalChannelPolicy.Evaluate(Prompt(), TaskKindHint.KeywordTagging,
                new LocalChannelConfig { ModelPath = path }, port: null);
            Assert.False(decision.Allowed);
            Assert.Equal(LocalChannelRejectReason.PortMissing, decision.Reason);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void J2c_端口存在但真实探测不可用_拒绝port_unavailable()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Available = false };
            var decision = LocalChannelPolicy.Evaluate(Prompt(), TaskKindHint.KeywordTagging,
                new LocalChannelConfig { ModelPath = path }, port);
            Assert.False(decision.Allowed);
            Assert.Equal(LocalChannelRejectReason.PortUnavailable, decision.Reason);
            Assert.Equal(0, port.Calls);   // 探不到 ⇒ 绝不发起
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void J2d_主回答默认不走本地_kind_not_allowed()
    {
        var path = ReadyModelFile();
        try
        {
            var decision = LocalChannelPolicy.Evaluate(Prompt(), TaskKindHint.General,
                new LocalChannelConfig { ModelPath = path }, new FakePort());
            Assert.False(decision.Allowed);
            Assert.Equal(LocalChannelRejectReason.KindNotAllowed, decision.Reason);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void J2e_allow_general开_主回答可走本地()
    {
        var path = ReadyModelFile();
        try
        {
            var decision = LocalChannelPolicy.Evaluate(Prompt(), TaskKindHint.General,
                new LocalChannelConfig { ModelPath = path, AllowGeneral = true }, new FakePort());
            Assert.True(decision.Allowed);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void J2f_带图请求不走本地_image_request()
    {
        var path = ReadyModelFile();
        try
        {
            var prompt = Prompt();
            prompt.ImageUrls.Add("data:image/png;base64,AAAA");
            var decision = LocalChannelPolicy.Evaluate(prompt, TaskKindHint.KeywordTagging,
                new LocalChannelConfig { ModelPath = path }, new FakePort());
            Assert.False(decision.Allowed);
            Assert.Equal(LocalChannelRejectReason.ImageRequest, decision.Reason);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void J2g_prompt超限不走本地_prompt_too_long()
    {
        var path = ReadyModelFile();
        try
        {
            var decision = LocalChannelPolicy.Evaluate(Prompt(estimated: 5000), TaskKindHint.KeywordTagging,
                new LocalChannelConfig { ModelPath = path, MaxPromptTokens = 2048 }, new FakePort());
            Assert.False(decision.Allowed);
            Assert.Equal(LocalChannelRejectReason.PromptTooLong, decision.Reason);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void J2h_记账恒等校验本身有效_负控()
    {
        Assert.True(FakePort.Ok("x").AccountingConsistent);
        // 反例: 总长 != 新算 + 命中 ⇒ 不一致 (这一条失效 ⇒ J2m 的防线就形同虚设)
        Assert.False(new LocalGenerationOutcome { TokensEvaluated = 4340, PromptNewTokens = 18, CachedTokens = 100 }
            .AccountingConsistent);
    }

    // ---------- 端到端: 路由行为 ----------
    [Fact]
    public async Task J2i_端口可用_本地直接承接_远端零调用()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            var port = new FakePort();
            var router = Router(fake, Catalog(fake.Endpoint, path), port);

            var resp = await router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify");

            Assert.True(resp.Success);
            Assert.Equal("本地产出", resp.Content);
            Assert.Equal("local:fake", resp.Model);
            Assert.Equal(4340, resp.PromptTokens);
            Assert.Equal(4322, resp.CacheHitTokens);
            Assert.Equal(18, resp.CompletionTokens);
            Assert.Equal(0, fake.Hits);                       // 关键证据: 没触网
            Assert.Equal(1, router.LocalChannel.Attempted);
            Assert.Equal(1, router.LocalChannel.Succeeded);
            Assert.Equal(0, router.LocalChannel.Degraded);
            Assert.StartsWith("local:", router.LastSelectionBasis);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task J2j_通道未配置_拒绝可见_且远端照常承接()
    {
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        var port = new FakePort();
        var router = Router(fake, Catalog(fake.Endpoint, localModelPath: null), port);

        var resp = await router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify");

        Assert.True(resp.Success);
        Assert.Equal(RemoteReply, resp.Content);
        Assert.Equal(1, fake.Hits);
        Assert.Equal(0, router.LocalChannel.Attempted);        // 未尝试
        Assert.Equal(1, router.LocalChannel.Rejected);
        Assert.Equal("channel_disabled", router.LocalChannel.LastRejectReason);
        Assert.Equal("local:rejected:channel_disabled", router.LocalChannelLastBasis);
        Assert.Equal(0, port.Calls);
    }

    [Fact]
    public async Task J2k_端口缺失_拒绝port_missing_且远端照常承接()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            var router = Router(fake, Catalog(fake.Endpoint, path), port: null);
            var resp = await router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify");

            Assert.Equal(RemoteReply, resp.Content);
            Assert.Equal(1, fake.Hits);
            Assert.Equal(0, router.LocalChannel.Attempted);
            Assert.Equal("port_missing", router.LocalChannel.LastRejectReason);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task J2l_探测不可用_拒绝port_unavailable_远端照常()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            var port = new FakePort { Available = false };
            var router = Router(fake, Catalog(fake.Endpoint, path), port);
            var resp = await router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify");

            Assert.Equal(RemoteReply, resp.Content);
            Assert.Equal(1, fake.Hits);
            Assert.Equal(0, router.LocalChannel.Attempted);
            Assert.Equal("port_unavailable", router.LocalChannel.LastRejectReason);
            Assert.Equal(0, port.Calls);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task J2m_本地失败_降级远端_且降级可见()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            var port = new FakePort { Behavior = _ => new LocalGenerationOutcome { Success = false, Error = "local_failed:Timeout" } };
            var router = Router(fake, Catalog(fake.Endpoint, path), port);

            var resp = await router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify");

            Assert.Equal(RemoteReply, resp.Content);           // 真的降级到远端
            Assert.Equal(1, fake.Hits);
            Assert.Equal(1, router.LocalChannel.Attempted);
            Assert.Equal(0, router.LocalChannel.Succeeded);
            Assert.Equal(1, router.LocalChannel.Degraded);
            Assert.Equal("local_failed:Timeout", router.LocalChannel.LastDegradeReason);
            Assert.Equal("local:degraded:local_failed:Timeout→remote", router.LocalChannelLastBasis);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task J2n_记账违规_结果不采信_降级远端()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            // 自算错而自洽的形态: 总长 4340 却报 命中 100 ⇒ 恒等不成立
            var port = new FakePort { Behavior = _ => new LocalGenerationOutcome { Success = true, Content = "本地", TokensEvaluated = 4340, PromptNewTokens = 18, CachedTokens = 100 } };
            var router = Router(fake, Catalog(fake.Endpoint, path), port);

            var resp = await router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify");

            Assert.Equal(RemoteReply, resp.Content);           // 本地结果被作废
            Assert.Equal(1, fake.Hits);
            Assert.Equal(1, router.LocalChannel.AccountingViolations);
            Assert.Equal(0, router.LocalChannel.Succeeded);
            Assert.Equal("local:degraded:accounting_inconsistent→remote", router.LocalChannelLastBasis);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task J2o_本地空回_不算成功_降级远端()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("   ") };
            var router = Router(fake, Catalog(fake.Endpoint, path), port);

            var resp = await router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify");

            Assert.Equal(RemoteReply, resp.Content);
            Assert.Equal(1, router.LocalChannel.Degraded);
            Assert.Equal("empty_content", router.LocalChannel.LastDegradeReason);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task J2p_取消_上抛不当降级()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            var router = Router(fake, Catalog(fake.Endpoint, path), new ThrowingPort());
            await Assert.ThrowsAsync<OperationCanceledException>(
                () => router.CallAsync(Prompt(), TaskKindHint.KeywordTagging, "classify"));

            Assert.Equal(0, router.LocalChannel.Degraded);     // 取消不是降级
            Assert.Equal(0, fake.Hits);                        // 取消后不得继续走远端
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task J2q_会话键与轮次透传到端口()
    {
        var path = ReadyModelFile();
        using var fake = new FakeLlmEndpoint(new[] { FakeLlmEndpoint.Reply(RemoteReply) });
        try
        {
            var port = new FakePort();
            var router = Router(fake, Catalog(fake.Endpoint, path), port);
            var prompt = Prompt();
            prompt.SystemPrompt = "sys";
            prompt.ContextPrompt = "ctx";
            prompt.History.Add(new QueueHistoryMessage { Role = "assistant", Content = "之前" });

            await router.CallAsync(prompt, TaskKindHint.KeywordTagging, "classify");

            Assert.NotNull(port.LastRequest);
            Assert.Equal("s1", port.LastRequest!.SessionKey);
            Assert.Equal(2, port.LastRequest.TurnIndex);
            Assert.Equal(128, port.LastRequest.MaxTokens);
            Assert.Equal(4, port.LastRequest.Turns.Count);
            Assert.Equal("system", port.LastRequest.Turns[0].Role);
            Assert.Equal("assistant", port.LastRequest.Turns[2].Role);
            Assert.Equal("把这段标注一下", port.LastRequest.Turns[3].Content);
        }
        finally { File.Delete(path); }
    }
}
