using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.action;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

[Collection(ActionBoundaryEnvCollection.Name)]
public sealed class R498BoundaryPositiveControlTests : IDisposable
{
    private const string Secret = "R498-SECRET-9f3a";
    private readonly string _base = Path.Combine(Path.GetTempPath(), "r498_bnd_" + Guid.NewGuid().ToString("N"));
    private readonly string? _prevEnv;

    public R498BoundaryPositiveControlTests()
    {
        Directory.CreateDirectory(Path.Combine(_base, "ws"));
        File.WriteAllText(Path.Combine(_base, "secret.txt"), Secret);
        File.WriteAllText(Path.Combine(_base, "ws", "inside.txt"), "inside-ok");
        _prevEnv = Environment.GetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName);
    }

    public void Dispose()
    {
        Environment.SetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName, _prevEnv);
        try { Directory.Delete(_base, true); } catch (IOException) { /* 清理失败不影响判定 */ }
    }

    private static ActionToolCall Read(string path) => new()
    {
        Id = "r498",
        Name = ActionToolDecl.ReadFile,
        ArgumentsJson = "{\"path\":\"" + path + "\"}",
    };

    [Fact]
    public async Task 缺陷注入臂_闸关后越界读必须成功以证明拒绝断言是活的()
    {
        var port = new WorkspaceActionPort(Path.Combine(_base, "ws"));
        var call = Read("../secret.txt");

        // ── 处理组: 默认闸 (开) ⇒ 越界必拒, 且**不得回显任何字节**
        Environment.SetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName, "1");
        Assert.True(WorkspaceActionPort.BoundaryEnforced(), "闸默认开");
        var refused = await port.ExecuteAsync(call, CancellationToken.None);
        Assert.False(refused.Ok, "闸开: 越界读必须拒绝");
        Assert.DoesNotContain(Secret, refused.Output ?? string.Empty, StringComparison.Ordinal);
        Assert.Contains("越界", refused.Output ?? string.Empty, StringComparison.Ordinal);
        Assert.NotEqual(0, refused.ExitCode);   // 拒绝必须可观测 (非成功码)

        // ── 缺陷注入臂: 闸关 ⇒ 同一调用必须成功且回显 ⇒ 上一段的断言面被证明是活的
        Environment.SetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName, "0");
        Assert.False(WorkspaceActionPort.BoundaryEnforced(), "注入臂: 闸必须为关");
        var leaked = await port.ExecuteAsync(call, CancellationToken.None);
        Assert.True(leaked.Ok, "缺陷注入臂 (闸关): 越界读必须成功 —— 否则拒绝断言与机制无因果绑定");
        Assert.Contains(Secret, leaked.Output ?? string.Empty, StringComparison.Ordinal);
    }

    [Fact]
    public async Task 反向负控_闸开时区内读必须照常工作()
    {
        var port = new WorkspaceActionPort(Path.Combine(_base, "ws"));
        Environment.SetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName, "1");
        var ok = await port.ExecuteAsync(Read("inside.txt"), CancellationToken.None);
        Assert.True(ok.Ok, "闸开不得防碍区内正常读");
        Assert.Contains("inside-ok", ok.Output ?? string.Empty, StringComparison.Ordinal);
    }

    [Fact]
    public async Task 反向负控_闸开时区内写必须照常落盘()
    {
        var port = new WorkspaceActionPort(Path.Combine(_base, "ws"));
        Environment.SetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName, "1");
        var call = new ActionToolCall
        {
            Id = "r498w",
            Name = ActionToolDecl.WriteFile,
            ArgumentsJson = "{\"path\":\"out.txt\",\"content\":\"written-ok\"}",
        };
        var res = await port.ExecuteAsync(call, CancellationToken.None);
        Assert.True(res.Ok, res.Output);
        Assert.True(File.Exists(Path.Combine(_base, "ws", "out.txt")), "区内写必须真的落盘");
    }
}
