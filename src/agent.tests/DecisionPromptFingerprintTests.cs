using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R430 机检: **判定输入指纹** (LocalInputFingerprint) —— 门判的 prompt/请求体必须可机械指纹化。
///
/// 动机 (R429 遗留): 缓存钉死后判定结论恒定, 但生成文本仍逐轮不同 (raw_len 4 种取值)。
/// 要把「P5c 逐位复现」证到或证否, 必须先能区分两种可能:
///   ① 输入不同 (prompt 文本 / 请求字段被改动) —— 修在输入构造侧;
///   ② 引擎不确定 (llama.cpp 数值/调度漂移)   —— 修在引擎侧。
/// 反空心纪律: 指纹只观测, 不得影响判定; 无随机盐 (同一输入必同值); 缺失 ≠ 错误 (后端不报 ⇒ 空串)。
/// </summary>
public sealed class DecisionPromptFingerprintTests
{
    private const string KeyEnv = "R430_INPUT_FP_KEY";
    static DecisionPromptFingerprintTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    private sealed class FakePort : ILocalGenerationPort
    {
        public string Verdict = "P";
        public string PromptSha = "";
        public string RequestSha = "";
        public string Fields = "";
        public int Calls;
        public LocalGenerationRequest? LastRequest;

        public bool IsAvailable => true;
        public string BackendId => "fake";

        public Task<LocalGenerationOutcome> GenerateAsync(LocalGenerationRequest request, CancellationToken ct = default)
        {
            Calls++;
            LastRequest = request;
            return Task.FromResult(new LocalGenerationOutcome
            {
                Success = true,
                Content = Verdict,
                TokensEvaluated = 100,
                PromptNewTokens = 100,
                CachedTokens = 0,
                GeneratedTokens = 2,
                Model = "local:fake",
                PromptSha16 = PromptSha,
                RequestSha16 = RequestSha,
                RequestFields = Fields,
            });
        }
    }

    private static ModelCatalog Catalog() => new()
    {
        Models =
        {
            new ModelCatalogEntry
            {
                Id = "r430-remote", Provider = "deepseek", Endpoint = "http://127.0.0.1:1/v1",
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
            TurnGate = true,
            RelationJudge = false,
        },
    };

    private static ModelQueueRouter Router(ILocalGenerationPort? port)
        => new(Catalog(), new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance, localPort: port);

    // ---------- F1 指纹本原: 定长 / 同输入同值 / 不同输入不同值 ----------
    [Fact]
    public void F1_指纹_定长且确定性()
    {
        var a1 = LocalInputFingerprint.Sha16("判别: 好，按这个来。");
        var a2 = LocalInputFingerprint.Sha16("判别: 好，按这个来。");
        var b = LocalInputFingerprint.Sha16("判别: 好，按这个来。 ");
        Assert.Equal(a1, a2);                       // 无随机盐
        Assert.NotEqual(a1, b);                     // 敏感 (尾随空格)
        Assert.Equal(16, a1.Length);
        Assert.All(a1, c => Assert.True((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'), $"非小写 hex: {c}"));
        Assert.Equal(16, LocalInputFingerprint.Sha16(null).Length);   // null 安全
    }

    // ---------- F2 Unicode 稳定 (UTF-8 固定编码, 不随 locale) ----------
    [Fact]
    public void F2_指纹_Unicode稳定()
    {
        Assert.Equal(LocalInputFingerprint.Sha16("中文🙂"), LocalInputFingerprint.Sha16("中文🙂"));
        Assert.NotEqual(LocalInputFingerprint.Sha16("中文🙂"), LocalInputFingerprint.Sha16("中文 🙂"));
    }

    // ---------- F3 字段摘要: 只在该字段变化时变化 ----------
    [Fact]
    public void F3_字段摘要_定位到具体字段()
    {
        string D(bool cache, int np) => LocalInputFingerprint.Describe(
            np, 0f, new[] { "temperature" }, cache, 0, 0, 1f, 0f, 1f);

        var baseline = D(false, 512);
        Assert.Contains("np=512", baseline);
        Assert.Contains("cp=0", baseline);
        Assert.Contains("sp=temperature", baseline);
        Assert.NotEqual(baseline, D(true, 512));     // cache_prompt 变 ⇒ 摘要变
        Assert.NotEqual(baseline, D(false, 256));    // n_predict 变 ⇒ 摘要变
        Assert.Equal(baseline, D(false, 512));       // 不变 ⇒ 逐字符相同
    }

    // ---------- F4 门判: 指纹贯通到 TurnGate (被使用计数绑定真实请求) ----------
    [Fact]
    public async Task F4_门判_指纹贯通可观测()
    {
        var port = new FakePort { Verdict = "P", PromptSha = "0123456789abcdef", RequestSha = "fedcba9876543210", Fields = "np=512;t=0;sp=temperature;cp=0;seed=0;tk=0;tp=1;mp=0;rp=1" };
        var router = Router(port);
        var outcome = await router.JudgeTurnAsync("好，按这个来。", "skeptic|seed", null);

        Assert.True(outcome.Decided);
        Assert.Equal(1, port.Calls);
        Assert.Equal("0123456789abcdef", router.TurnGate.LastPromptSha);
        Assert.Equal("fedcba9876543210", router.TurnGate.LastRequestSha);
        Assert.Contains("cp=0", router.TurnGate.LastRequestFields!);
        Assert.Equal(1, router.TurnGate.CachePinned);
    }

    // ---------- F5 角色种子指纹: 不同种子必不同 (防「恒定值」空心实现) ----------
    [Fact]
    public async Task F5_角色种子指纹_可变且必须匹配()
    {
        var port = new FakePort();
        var router = Router(port);
        await router.JudgeTurnAsync("好", "skeptic|AAA", null);
        var s1 = router.TurnGate.LastRoleSeedSha;
        await router.JudgeTurnAsync("好", "skeptic|BBB", null);

        Assert.NotNull(s1);
        Assert.Equal(LocalInputFingerprint.Sha16("skeptic|AAA"), s1);
        Assert.NotEqual(s1, router.TurnGate.LastRoleSeedSha);
    }

    // ---------- F6 负控: 后端不报指纹 ⇒ 缺失不报错 (缺失≠错误) ----------
    [Fact]
    public async Task F6_负控_后端不报指纹_不报错()
    {
        var port = new FakePort();   // 三个指纹全空
        var router = Router(port);
        var outcome = await router.JudgeTurnAsync("好", "skeptic", null);

        Assert.True(outcome.Decided);
        Assert.Equal(TurnGateVerdict.Pass, outcome.Verdict);
        Assert.True(string.IsNullOrEmpty(router.TurnGate.LastPromptSha));
        Assert.True(string.IsNullOrEmpty(router.TurnGate.LastRequestSha));
    }

    // ---------- F7 纯观测: 指纹值不改变判定结论 (含 raw) ----------
    [Fact]
    public async Task F7_指纹_不改变判定()
    {
        var withFp = Router(new FakePort { Verdict = "S", PromptSha = "aaaaaaaaaaaaaaaa" });
        var without = Router(new FakePort { Verdict = "S" });
        var a = await withFp.JudgeTurnAsync("好，按这个来。", "skeptic", null);
        var b = await without.JudgeTurnAsync("好，按这个来。", "skeptic", null);

        Assert.Equal(b.Verdict, a.Verdict);
        Assert.Equal(b.Raw, a.Raw);
        Assert.Equal(b.Decided, a.Decided);
    }

    // ---------- F8 机检不变量: 四层贯通 (防半贯通/空心) + 无随机盐 ----------
    [Fact]
    public void F8_不变量_四层贯通且无随机源()
    {
        var root = FindRepoRoot();
        Assert.False(root is null, "找不到仓库根");

        // ① 四层文件都必须出现指纹字段 (只在一层做 = 观测断链)
        var layers = new[]
        {
            "src/agent.llamacpp/LlamaCppClient.cs",
            "src/agent.llamacpp/LlamaCppTextGenerator.cs",
            "src/agent.llamacpp/LlamaCppLocalGenerationPort.cs",
            "src/agent.modelqueue/LocalGenerationOutcome.cs",   // R526: 原 LocalGenerationPort.cs 多类型已单文件化
            "src/agent.modelqueue/ModelQueueRouter.cs",
            "src/agent/IndustrialAgentV2.cs",
        };
        foreach (var rel in layers)
        {
            var src = File.ReadAllText(Path.Combine(root!, rel));
            Assert.True(src.Contains("Sha16") || src.Contains("PromptSha"), $"指纹未贯通: {rel}");
        }

        // ② 指纹实现不得含随机源/时钟 (有 ⇒ 同一输入不同值 ⇒ 指纹失效)
        var impl = File.ReadAllText(Path.Combine(root!, "src/agent.modelqueue/LocalInputFingerprint.cs"));
        Assert.DoesNotContain("Random", impl);
        Assert.DoesNotContain("Guid", impl);
        Assert.DoesNotContain("DateTime", impl);
        Assert.Contains("SHA256", impl);
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
}
