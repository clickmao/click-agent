using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using agent.llamacpp;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R429 机检: **决策路径缓存态钉死** —— 门判 (TurnGateJudge) 与关系判官 (RelationJudge) 一律关前缀缓存
/// (cache_prompt=false ⇒ CompletionReuse.Reconciliation)。
///
/// 依据 (R429 传输级实测, eval/rover/r429/decision_cache_probe.py): **同一 prompt** 在
/// 「全量评估 (cache_n=0)」与「部分前缀复用 (cache_n=213/226)」下 token 序列不等 (180 / 97 / 215),
/// 并可直接翻转 S/P 判定 ⇒ 判定结果不得依赖「上一次调用了什么」。
///
/// 反空心纪律: 计数必须绑定**真实发起的请求** (无端口 ⇒ 不计数); 非决策路径 (跳过轮本地回复)
/// 不受影响 (CacheReuse 默认 true = 逐位零回归)。
/// </summary>
public sealed class DecisionCachePinTests
{
    private const string KeyEnv = "R429_DECISION_CACHE_KEY";
    static DecisionCachePinTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    // 尖括号字面量按码点构造 (R413 铁律: 直接写标签字面量会被静默改写)
    private static readonly string OpenTag = ((char)60) + "think" + ((char)62);
    private static readonly string CloseTag = ((char)60) + "/think" + ((char)62);

    private sealed class FakePort : ILocalGenerationPort
    {
        public string Verdict = "P";
        public bool BadAccounting;
        public int Calls;
        public LocalGenerationRequest? LastRequest;

        public bool IsAvailable => true;
        public string BackendId => "fake";

        public Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default)
        {
            Calls++;
            LastRequest = request;
            var content = OpenTag + "想一下" + CloseTag + "\n\n" + Verdict;
            return Task.FromResult(new LocalGenerationOutcome
            {
                Success = true,
                Content = content,
                TokensEvaluated = BadAccounting ? 999 : 100,
                PromptNewTokens = 16,
                CachedTokens = 84,
                GeneratedTokens = 2,
                Model = "local:fake",
            });
        }
    }

    private static ModelCatalog Catalog(bool relationJudge = false, bool turnGate = false)
        => new()
        {
            Models =
            {
                new ModelCatalogEntry
                {
                    Id = "r429-remote", Provider = "deepseek", Endpoint = "http://127.0.0.1:1/v1",
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
                TurnGate = turnGate,
                RelationJudge = relationJudge,
            },
        };

    private static ModelQueueRouter Router(ILocalGenerationPort? port, bool relationJudge = false)
        => new(Catalog(relationJudge), new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance, localPort: port);

    // ---------- C1 口径映射 (纯函数) ----------
    [Fact]
    public void C1_映射_决策钉死_Reconciliation()
    {
        Assert.Equal(CompletionReuse.Session, CompletionProfiles.ReuseFor(true));
        Assert.Equal(CompletionReuse.Reconciliation, CompletionProfiles.ReuseFor(false));
        Assert.True(CompletionProfiles.Build("p", 8, true, CompletionProfiles.ReuseFor(true)).CachePrompt);
        Assert.False(CompletionProfiles.Build("p", 8, true, CompletionProfiles.ReuseFor(false)).CachePrompt);
    }

    [Fact]
    public void C2_请求默认_复用_零回归()
    {
        Assert.True(new LocalGenerationRequest().CacheReuse);
        Assert.False(new LocalGenerationRequest { CacheReuse = false }.CacheReuse);
    }

    // ---------- C3/C4 决策路径实际钉死 + 计数绑定 ----------
    [Fact]
    public async Task C3_门判_钉死缓存_计数与cache_n可观测()
    {
        var port = new FakePort { Verdict = "P" };
        var router = Router(port);
        var outcome = await router.JudgeTurnAsync("好，按这个来。", "skeptic|seed", null);

        Assert.True(outcome.Decided);
        Assert.NotNull(port.LastRequest);
        Assert.False(port.LastRequest!.CacheReuse);      // 决策路径必须钉死
        Assert.Equal(1, router.TurnGate.CachePinned);    // 被使用计数
        Assert.Equal(84, router.TurnGate.LastCachedTokens); // 最近一次 cache_n (fake 报 84; 真机应恒 0)
    }

    [Fact]
    public async Task C4_关系判官_钉死缓存_计数可观测()
    {
        var port = new FakePort { Verdict = "A" };
        var router = Router(port, relationJudge: true);
        var r = await router.JudgeRelationLocalAsync("只输出一个字母。", "判定用户消息相对上一轮回答: 上一轮: 收到。 用户: 好，知道了。");

        Assert.NotNull(r);
        Assert.Equal("A", r!.Letter);
        Assert.False(port.LastRequest!.CacheReuse);
        Assert.Equal(1, router.RelationJudge.CachePinned);
    }

    // ---------- C5 负控: 无设备 ⇒ 不计数 (计数绑定真实请求) ----------
    [Fact]
    public async Task C5_负控_无端口_不计数()
    {
        var router = Router(port: null);
        var outcome = await router.JudgeTurnAsync("好", "skeptic", null);

        Assert.False(outcome.Decided);
        Assert.Equal("no_local_port", outcome.Error);
        Assert.Equal(0, router.TurnGate.CachePinned);
        Assert.Equal(0, router.RelationJudge.CachePinned);
    }

    // ---------- C6 不变量: 全仓只有两个决策路径把 CacheReuse 置 false (零回归边界) ----------
    [Fact]
    public void C6_不变量_只有决策路径钉死缓存()
    {
        var root = FindRepoRoot();
        Assert.False(root is null, "找不到仓库根 (含 src 与 docs 的目录)");

        var offenders = new List<string>();
        foreach (var file in Directory.EnumerateFiles(root!, "*.cs", SearchOption.AllDirectories))
        {
            if (file.Contains("/obj/") || file.Contains("/bin/") || file.Contains("agent.tests")) continue;
            if (File.ReadAllText(file).Contains("CacheReuse = false")) offenders.Add(file);
        }
        var names = offenders.Select(Path.GetFileName).Distinct().OrderBy(x => x, StringComparer.Ordinal).ToArray();
        // R527: 单一类型允许分片 (ModelQueueRouter.<Suffix>.cs) ⇒ 判「全部落在该类型的分片上」, 禁别的类型
        Assert.All(names, n => Assert.True(
            n == "ModelQueueRouter.cs" || n.StartsWith("ModelQueueRouter.", StringComparison.Ordinal),
            $"缓存钉死泄漏到非决策路径文件: {n}"));
        Assert.NotEmpty(names);

        var routerSrc = SourcePin.TextParts("src/agent.modelqueue/ModelQueueRouter.cs");
        Assert.Equal(2, routerSrc.Split("CacheReuse = false").Length - 1);  // 门判 + 关系判官
    }

    private static string? FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 12 && dir is not null; i++)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "src")) &&
                Directory.Exists(Path.Combine(dir.FullName, "docs"))) return dir.FullName;
            dir = dir.Parent;
        }
        return null;
    }

    // ---------- C7 钉死不得掩盖记账违规 (反空心: 口径检查仍生效) ----------
    [Fact]
    public async Task C7_记账违规仍判未判定_计数照记()
    {
        var port = new FakePort { BadAccounting = true };
        var router = Router(port);
        var outcome = await router.JudgeTurnAsync("好", "skeptic", null);

        Assert.False(outcome.Decided);
        Assert.Equal("accounting_inconsistent", outcome.Error);
        Assert.Equal(1, router.TurnGate.CachePinned);        // 请求已发起 ⇒ 钉死计数照记
        Assert.Equal(1, router.TurnGate.AccountingViolations); // 违规仍被记录
    }
}
