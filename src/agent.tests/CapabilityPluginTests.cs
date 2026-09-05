using System.Linq;
using System.Threading.Tasks;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 需求6 测试: 能力插件接口 — 注册唯一性/分发/未注册与未提供能力裁决/插件内异常隔离。
/// </summary>
public class CapabilityPluginTests
{
    private sealed class FakePlugin : ICapabilityPlugin
    {
        public string Name => "workspace";
        public string Description => "测试插件";
        public System.Collections.Generic.IReadOnlyList<string> ProvidedCapabilities { get; } =
            new[] { "read_file", "write_file" };
        public bool ThrowOnExecute { get; set; }

        public Task InitializeAsync(System.Threading.CancellationToken ct = default) => Task.CompletedTask;

        public Task<PluginExecutionResult> ExecuteAsync(string capabilityId, string args,
            System.Threading.CancellationToken ct = default)
        {
            if (ThrowOnExecute)
                throw new System.InvalidOperationException("boom");
            return Task.FromResult(PluginExecutionResult.Ok($"{capabilityId}:{args}"));
        }
    }

    [Fact]
    public void Register_Is_Unique_And_Findable()
    {
        var registry = new CapabilityPluginRegistry();
        Assert.True(registry.Register(new FakePlugin()));
        Assert.False(registry.Register(new FakePlugin())); // 同名拒绝
        Assert.NotNull(registry.Find("workspace"));
        Assert.Null(registry.Find("nope"));
        Assert.Equal(new[] { "workspace" }, registry.Names);
    }

    [Fact]
    public async Task Execute_Dispatches_And_Validates_Capability()
    {
        var registry = new CapabilityPluginRegistry();
        registry.Register(new FakePlugin());

        var ok = await registry.ExecuteAsync("workspace.read_file", "a.txt");
        Assert.True(ok.Success);
        Assert.Equal("read_file:a.txt", ok.Output);

        var notProvided = await registry.ExecuteAsync("workspace.run_tests", "");
        Assert.False(notProvided.Success);
        Assert.Contains("capability_not_provided", notProvided.Error);

        var badFqn = await registry.ExecuteAsync("noplugin", "");
        Assert.Contains("invalid_capability_fqn", badFqn.Error);

        var unregistered = await registry.ExecuteAsync("tests.run", "");
        Assert.Contains("plugin_not_registered", unregistered.Error);
    }

    [Fact]
    public async Task Plugin_Fault_Is_Isolated_As_Failure()
    {
        var registry = new CapabilityPluginRegistry();
        registry.Register(new FakePlugin { ThrowOnExecute = true });

        var result = await registry.ExecuteAsync("workspace.read_file", "x");
        Assert.False(result.Success);
        Assert.Contains("plugin_fault", result.Error);
        Assert.Contains("boom", result.Error);
    }
}
