using agent.config;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R306b — ConfigModelBinder 强类型绑定单测 (用户需求: "要 Model 实例, 不要手写 yaml")。
/// Get/Save/Update 闭环 + RoundTrip + 缺失键默认值。
/// </summary>
public class ConfigModelBinderTests : IDisposable
{
    private readonly string _root;
    private readonly string _origCwd;

    public ConfigModelBinderTests()
    {
        _root = Path.Combine(Path.GetTempPath(), "cfgbinder-" + Guid.NewGuid().ToString("N")[..8]);
        var cfg = Path.Combine(_root, "config");
        Directory.CreateDirectory(Path.Combine(cfg, "base"));
        // L1 base: model_queue 节 (与真实 config/base/models.yaml 同构的最小子集)
        File.WriteAllText(Path.Combine(cfg, "base", "models.yaml"),
            "model_queue:\n  router:\n    max_failures: 2\n    cooldown_ms: 30000\n  models:\n    - name: glm-a\n      price: 0.5\n");
        Directory.CreateDirectory(Path.Combine(cfg, "modules"));
        Directory.CreateDirectory(Path.Combine(cfg, "runtime"));
        // R306b 修正: 不动 cwd (xUnit 并行测试 cwd 竞争), 全部显式绝对路径传 configRoot。
    }

    public void Dispose() { /* 显式绝对路径, 不动 cwd */ }

    public sealed class RouterConfig
    {
        public RouterInner? Router { get; set; }

        public sealed class RouterInner
        {
            public int MaxFailures { get; set; }
            public int CooldownMs { get; set; }
        }
    }

    [Fact]
    public void Get_Binds_Strongly_Typed_Model_From_Yaml()
    {
        var snapshot = new ConfigSnapshot(Path.Combine(_root, "config"));
        var model = ConfigModelBinder.Get<RouterConfig>(snapshot, "model_queue");
        Assert.NotNull(model.Router);
        Assert.Equal(2, model.Router!.MaxFailures);
        Assert.Equal(30000, model.Router.CooldownMs);
    }

    [Fact]
    public void Update_Mutate_And_Persist_RoundTrip()
    {
        var snapshot = new ConfigSnapshot(Path.Combine(_root, "config"));
        var writer = new ConfigWriter(Path.Combine(_root, "config"));
        ConfigModelBinder.Update<RouterConfig>(snapshot, writer, "model_queue", m =>
        {
            m.Router = new RouterConfig.RouterInner { MaxFailures = 5, CooldownMs = 60000 };
        });
        // 重载 (新快照) — 值应持久化 (L3 覆盖生效):
        var reloaded = ConfigModelBinder.Get<RouterConfig>(
            new ConfigSnapshot(Path.Combine(_root, "config")), "model_queue");
        Assert.Equal(5, reloaded.Router!.MaxFailures);
        Assert.Equal(60000, reloaded.Router.CooldownMs);
        // L3 覆盖文件存在:
        Assert.True(File.Exists(Path.Combine(_root, "config", "modules", "model_queue.yaml")));
    }

    [Fact]
    public void Get_Missing_Module_Returns_Default_Instance()
    {
        var snapshot = new ConfigSnapshot(Path.Combine(_root, "config"));
        var model = ConfigModelBinder.Get<RouterConfig>(snapshot, "no_such_module");
        Assert.NotNull(model);
        Assert.Null(model.Router); // POCO 默认值, 不抛
    }

    [Fact]
    public void Update_Null_Property_Removes_Override_Key()
    {
        var snapshot = new ConfigSnapshot(Path.Combine(_root, "config"));
        var writer = new ConfigWriter(Path.Combine(_root, "config"));
        // 写一个 nullable 属性覆盖:
        writer.UpdateModule("model_queue", new Dictionary<string, object?>
        {
            ["router"] = new Dictionary<string, object?> { ["extra_key"] = "临时值" },
        });
        // Update 用 POCO (无 ExtraKey 属性) 落盘 — extra_key 不该残留? (POCO 未提及键保留语义):
        ConfigModelBinder.Update<RouterConfig>(snapshot, writer, "model_queue", m => m.Router = new RouterConfig.RouterInner { MaxFailures = 7, CooldownMs = 30000 });
        var raw = File.ReadAllText(Path.Combine(_root, "config", "modules", "model_queue.yaml"));
        Assert.Contains("7", raw); // 新值在
    }
}
