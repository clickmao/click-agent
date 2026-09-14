using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R431 机检: **role 额外数据 (成长经历) 有界挂载进 r1 门判 + 挂载可机检**。
///
/// 缺陷原文 (R431 前置机检): 管道早已支持 growthBlock 且 BuildPrompt 内已 clip 300,
/// 但链侧调用点一直传 <c>null</c> ⇒ 用户令「记得挂载 role 的额外数据」在真实负载上是空操作。
///
/// 本文件的判据分三层:
///  ① **零回归**: 未挂载路径的判别 prompt 必须与 R430 发布的读数**逐位同一** (冻结基线 sha16)。
///  ② **负控**: 挂载与未挂载的 prompt 指纹必须不同 —— 否则「挂了」无法被读数区分 (自证空心)。
///  ③ **可机检**: 门判计数必须上报实发 prompt 形状 (长度/种子/成长块), 且形状取自实发文本。
/// </summary>
public sealed class TurnGateGrowthMountTests
{
    private const string KeyEnv = "R431_GATE_FAKE_KEY";
    static TurnGateGrowthMountTests() => Environment.SetEnvironmentVariable(KeyEnv, "k");

    // 真机臂 role (skeptic.rbin) 的人格种子 —— 口径 = RoleBinaryFile.Read → ProfileSeed (70 字符)。
    // 由 eval/rover/r431/precheck_rbin.py 机检导出, 不作手抄: 其 sha16("skeptic|"+seed) 必须 == 0aa656fa7eafd93a,
    // 正是 R430 真机遥测记录的 role_seed_sha (双端互证)。
    internal const string RealSeed =
        "你是一个低调但执着的追问者。\n回答前先检查用户问题里未证明的前提; 前提不牢, 先问再答。\n每轮最多 2 个问题, 问完仍给出当前最佳答案。";

    private const string AckMsg = "好，按这个来。";

    /// <summary>R430 发布读数冻结基线: BuildPrompt(AckMsg, "skeptic|"+seed, null)。</summary>
    private const string FrozenPromptSha16 = "8749b0a15f102f04";
    private const int FrozenPromptLen = 355;

    // ---------- 夹具 (与 LocalTurnGateTests 同形; 该文件的夹具是 private ⇒ 本文件自带) ----------
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
        public static LocalGenerationOutcome Ok(string content, int evaluated = 100, int cached = 0, int generated = 2)
            => new()
            {
                Success = true, Content = content, TokensEvaluated = evaluated,
                PromptNewTokens = evaluated - cached, CachedTokens = cached, GeneratedTokens = generated,
                Model = "local:fake",
            };
    }

    private static string ReadyModelFile()
    {
        var path = Path.Combine(Path.GetTempPath(), $"r431-gate-{Guid.NewGuid():N}.gguf");
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
                    Id = "r431-remote", Provider = "deepseek", Endpoint = "http://127.0.0.1:1/v1",
                    ApiKeyEnv = KeyEnv, PriceInPerM = 0, PriceOutPerM = 0, ReasoningScore = 5,
                    CodingScore = 5, ContextWindow = 64000, SuitedFor = { "chat" },
                },
            },
            LocalChannel = new LocalChannelConfig
            {
                ModelPath = localModelPath, ContextSize = 4608, MaxTokens = 64,
                MaxPromptTokens = 2048, TurnGate = turnGate,
            },
        };

    private static ModelQueueRouter Router(ModelCatalog catalog, ILocalGenerationPort? port)
        => new(catalog, new StubHttpClientFactory(),
            Microsoft.Extensions.Logging.Abstractions.NullLogger.Instance, localPort: port);

    private static string Seed() => "skeptic|" + RealSeed;

    // ---------- 判据 ①: 零回归 (冻结基线逐位同一) ----------

    [Fact]
    public void H1_未挂载_判别prompt逐位等于R430冻结基线()
    {
        var prompt = TurnGateJudge.BuildPrompt(AckMsg, Seed(), null);
        Assert.Equal(FrozenPromptLen, prompt.Length);
        Assert.Equal(FrozenPromptSha16, LocalInputFingerprint.Sha16(prompt));
        // 种子口径自证: 与 R430 真机遥测 role_seed_sha 一致
        Assert.Equal("0aa656fa7eafd93a", LocalInputFingerprint.Sha16(Seed()));
    }

    [Fact]
    public void H1b_空成长块与null_逐位同一()
    {
        // 域 = 0 时 RenderForPrompt 返回 ""; 传 "" 不得比传 null 多出任何字符 (否则挂载在空负载上会引入噪声)
        Assert.Equal(TurnGateJudge.BuildPrompt(AckMsg, Seed(), null),
                     TurnGateJudge.BuildPrompt(AckMsg, Seed(), ""));
    }

    // ---------- 判据 ②: 挂载可见 + 有界 (R413 教训: 长 prompt ⇒ 判定被截断 ⇒ 增益归零) ----------

    [Fact]
    public void H2_挂载可见_且限制在300字符内()
    {
        var block = "rag: 赏1/罚0 → 观察中";                       // 与真机渲染同形的域行
        var huge = "【Role 成长经历】\n" + block + new string('长', 5000);
        var prompt = TurnGateJudge.BuildPrompt(AckMsg, Seed(), huge);

        Assert.Contains("Role 成长经历", prompt);
        Assert.Contains(block, prompt);                              // 前段必须真的进去了
        Assert.DoesNotContain(new string('长', 301), prompt);        // 超长部分必须被 clip
        Assert.True(prompt.Length <= FrozenPromptLen + 302,
            $"挂载后 prompt 必须有界, 实际 len={prompt.Length} (基线 {FrozenPromptLen})");
    }

    [Fact]
    public void H3_负控_挂载改变判别输入()
    {
        var mounted = TurnGateJudge.BuildPrompt(AckMsg, Seed(), "【Role 成长经历】\nrag: 赏1/罚0 → 观察中");
        var bare = TurnGateJudge.BuildPrompt(AckMsg, Seed(), null);
        Assert.NotEqual(LocalInputFingerprint.Sha16(bare), LocalInputFingerprint.Sha16(mounted));
    }

    // ---------- 判据 ③: 挂载可机检 (计数形状取自实发 prompt) ----------

    [Fact]
    public async Task H4_挂载臂_计数形状等于实发prompt()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("S") };
            var router = Router(Catalog(path, turnGate: true), port);
            const string growth = "【Role 成长经历】\nrag: 赏1/罚0 → 观察中\ndocker: 赏0/罚2 → ⚠先怀疑";

            var outcome = await router.JudgeTurnAsync(AckMsg, Seed(), growth);

            Assert.True(outcome.Decided);
            Assert.Equal(TurnGateVerdict.Skip, outcome.Verdict);
            // 实发文本 == 本侧按同一函数重建的文本 ⇒ 计数无漂移
            var sent = port.LastRequest!.Turns[0].Content;
            Assert.Equal(sent.Length, router.TurnGate.LastPromptChars);
            Assert.Equal(Seed().Length, router.TurnGate.LastRoleSeedChars);
            Assert.Equal(growth.Length, router.TurnGate.LastGrowthChars);
            Assert.Equal(2, router.TurnGate.LastGrowthLines);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task H5_未挂载臂_成长读数为零且prompt等于基线()
    {
        var path = ReadyModelFile();
        try
        {
            var port = new FakePort { Behavior = _ => FakePort.Ok("S") };
            var router = Router(Catalog(path, turnGate: true), port);

            await router.JudgeTurnAsync(AckMsg, Seed(), null);

            Assert.Equal(0, router.TurnGate.LastGrowthChars);        // 负控读数: 未挂载必须看得见
            Assert.Equal(0, router.TurnGate.LastGrowthLines);
            Assert.Equal(FrozenPromptLen, router.TurnGate.LastPromptChars);
            Assert.Equal(FrozenPromptSha16, LocalInputFingerprint.Sha16(port.LastRequest!.Turns[0].Content));
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task H6_挂载臂与未挂载臂_prompt长度差等于成长块长度()
    {
        var path = ReadyModelFile();
        try
        {
            var growth = "【Role 成长经历】\nrag: 赏1/罚0 → 观察中";
            var p1 = new FakePort { Behavior = _ => FakePort.Ok("S") };
            var r1 = Router(Catalog(path, turnGate: true), p1);
            await r1.JudgeTurnAsync(AckMsg, Seed(), null);

            var p2 = new FakePort { Behavior = _ => FakePort.Ok("S") };
            var r2 = Router(Catalog(path, turnGate: true), p2);
            await r2.JudgeTurnAsync(AckMsg, Seed(), growth);

            // 挂载 = 块 + 一个换行 (BuildPrompt 内 Append(growth).Append('\n')) ⇒ 差值恒为 len+1
            Assert.Equal(growth.Length + 1, r2.TurnGate.LastPromptChars - r1.TurnGate.LastPromptChars);
        }
        finally { File.Delete(path); }
    }

    // ---------- 判据 ④a: 账本侧前置条件可机检 (域 = 0 ⇒ 成长块恒空) ----------

    [Fact]
    public void H7_账本_空域渲染为空串且计数为0()
    {
        var dir = Path.Combine(Path.GetTempPath(), $"r431-ledger-{Guid.NewGuid():N}");
        try
        {
            var ledger = new agent.roles.RoleGrowthLedger("r431-probe", dir);
            Assert.Equal(0, ledger.DomainCount);
            Assert.Equal(string.Empty, ledger.RenderForPrompt());

            ledger.SeedFrom(new[]
            {
                new KeyValuePair<string, (int Reward, int Penalty)>("rag", (1, 0)),
                new KeyValuePair<string, (int Reward, int Penalty)>("docker", (0, 2)),
            });
            Assert.Equal(2, ledger.DomainCount);
            var block = ledger.RenderForPrompt();
            Assert.Contains("Role 成长经历", block);
            Assert.True(block.Length <= 400, $"成长块自身必须有界 (≤400), 实际 {block.Length}");
        }
        finally { if (Directory.Exists(dir)) Directory.Delete(dir, true); }
    }

    // ---------- 判据 ④b: 源码守卫 (防再次静默改回 null) ----------

    [Fact]
    public void H8_链侧必须实际挂载成长块()
    {
        var src = File.ReadAllText(Path.Combine(FindRepoRoot(), "src", "agent", "IndustrialAgentV2.cs"));
        var flat = string.Join(' ', src.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        // 正向: 门判第三参必须来自账本渲染 (而不是字面量 null)
        Assert.Contains("gateGrowthBlock = GrowthLedger?.RenderForPrompt();", flat);
        Assert.Contains("JudgeTurnAsync( message.Content, gateRoleSeed, gateGrowthBlock, ct)", flat);
        // 负向: 不得回到「接口有字段但传 null」
        Assert.DoesNotContain("JudgeTurnAsync( message.Content, gateRoleSeed, null", flat);
        // 挂载形状必须上报 (否则挂没挂不可机检)
        Assert.Contains("(\"growth_chars\",", flat);
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }
}
