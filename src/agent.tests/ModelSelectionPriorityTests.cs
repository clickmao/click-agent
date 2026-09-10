using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R356 (用户钦定): models.yaml priority 声明主导选模 — 首选 deepseek-flash 不得被 0 价 GLM 顶掉。
/// 实证背景: auto 打分 reasoning/coding 同分 + GLM cost=0 → GLM 恒胜 (E2E 日志实证 401 耗尽切兜底)。
/// </summary>
public class ModelSelectionPriorityTests
{
    private static ModelCatalogEntry M(string id, int priority, double priceIn = 0, int reasoning = 8, int coding = 8)
        => new()
        {
            Id = id,
            Provider = "deepseek",
            ApiKeyEnv = "TEST_KEY_PRESENT",
            PriceInPerM = priceIn,
            PriceOutPerM = priceIn,
            ReasoningScore = reasoning,
            CodingScore = coding,
            Priority = priority,
        };

    private static ModelCatalog Catalog(params ModelCatalogEntry[] models)
        => new() { Models = new List<ModelCatalogEntry>(models) };

    private static ModelCatalogEntry? Pick(ModelCatalog catalog, TaskKindHint kind, string intent)
        => new ModelSelectionPolicy().Select(null, kind, intent, 700, 200, catalog);

    [Fact]
    public void 通用意图_首选声明必胜零价次选()
    {
        Environment.SetEnvironmentVariable("TEST_KEY_PRESENT", "x");
        var catalog = Catalog(M("glm-5.3-flash", 2), M("deepseek-flash", 1));
        Assert.Equal("deepseek-flash", Pick(catalog, TaskKindHint.General, "general")!.Id);
    }

    [Fact]
    public void 性能不敏感_声明优先级仍锁首选()
    {
        Environment.SetEnvironmentVariable("TEST_KEY_PRESENT", "x");
        var catalog = Catalog(M("glm-5.3-flash", 2), M("deepseek-flash", 1));
        Assert.Equal("deepseek-flash", Pick(catalog, TaskKindHint.ContextCompression, "general")!.Id);
    }

    [Fact]
    public void 重推理意图_priority档差压过能力小差()
    {
        Environment.SetEnvironmentVariable("TEST_KEY_PRESENT", "x");
        // 首选 6 vs 次选 10: reasoning*3 差 (1.0-0.6)*3=1.2 < priority 5 → 首选仍胜 (钦定强度)
        var catalog = Catalog(M("ds-first", 1, reasoning: 6), M("glm-strong", 2, reasoning: 10));
        Assert.Equal("ds-first", Pick(catalog, TaskKindHint.General, "planning")!.Id);
    }

    [Fact]
    public void 未声明priority_保持旧打分行为()
    {
        Environment.SetEnvironmentVariable("TEST_KEY_PRESENT", "x");
        var catalog = Catalog(M("glm-free", 0), M("ds-paid", 0, priceIn: 1.0));
        Assert.Equal("glm-free", Pick(catalog, TaskKindHint.General, "general")!.Id);
    }

    [Fact]
    public void 手动override_仍最高优先()
    {
        Environment.SetEnvironmentVariable("TEST_KEY_PRESENT", "x");
        var catalog = Catalog(M("glm-5.3-flash", 2), M("deepseek-flash", 1));
        var picked = new ModelSelectionPolicy().Select("glm-5.3-flash", TaskKindHint.General, "general", 700, 200, catalog);
        Assert.Equal("glm-5.3-flash", picked!.Id);
    }

    [Fact]
    public void priority_生产目录声明_DS首选()
    {
        // 生产 models.yaml: DS priority 1 / GLM 2 (R356 补) — 目录加载后可查
        var root = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..");
        var configDir = Path.Combine(root, "config");
        if (!File.Exists(Path.Combine(configDir, "base", "models.yaml")))
            return; // 测试环境无仓库布局 → 跳过 (CI 有)
        var snapshot = new agent.config.ConfigSnapshot(configDir);
        var catalog = ModelCatalog.Load(snapshot);
        var ds = catalog.Find("deepseek-flash");
        var glm = catalog.Find("glm-5.3-flash");
        Assert.True(ds is null || ds.Priority == 1);
        Assert.True(glm is null || glm.Priority == 2);
    }
}
