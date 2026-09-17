using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using agent.action;
using agent.modelqueue;
namespace agent.tests;

/// <summary>
/// R511: delete_file 工具 + 人工审批门 (真机审批通道闭环的单测面)。
/// 契约:
///   · 未接入审批通道 ⇒ 拒绝 (rc=125, fail-closed), 文件必须原封不动。
///   · 审批拒绝/取消/异常 ⇒ 未执行 (rc=124)。
///   · 审批通过 ⇒ 真删 (文件/目录递归)。
///   · 越界路径 / 不存在的路径 ⇒ 前置拒绝, **不得**进入审批面 (不把坏路径送给人)。
/// 声明面与执行面同源: <see cref="ActionToolDecl.DeleteFile"/> 必须在白名单与工具 JSON 中。
/// </summary>
public sealed class R511DeleteToolApprovalTests : IDisposable
{
    private readonly string _root;

    public R511DeleteToolApprovalTests()
    {
        _root = Path.Combine(Path.GetTempPath(), "r511-del-" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(_root);
    }

    public void Dispose()
    {
        try { if (Directory.Exists(_root)) Directory.Delete(_root, recursive: true); } catch { }
    }

    private WorkspaceActionPort Port(Func<string, bool, CancellationToken, Task<bool>>? gate)
        => new(_root, auditDir: null, approveDelete: gate);

    private static ActionToolCall Del(string path)
        => new() { Name = ActionToolDecl.DeleteFile, ArgumentsJson = "{\"path\":\"" + path + "\"}" };

    private string MakeFile(string rel, string content = "x")
    {
        var p = Path.Combine(_root, rel);
        Directory.CreateDirectory(Path.GetDirectoryName(p)!);
        File.WriteAllText(p, content);
        return p;
    }

    [Fact]
    public void DeleteFile_IsDeclared_AndAdvertisedInToolsJson()
    {
        Assert.Contains(ActionToolDecl.DeleteFile, ActionToolDecl.Names);
        Assert.True(ActionToolDecl.IsDeclared(ActionToolDecl.DeleteFile));
        Assert.Contains("\"name\":\"delete_file\"", ActionToolDecl.ToolsJson);
        // 声明面派生 (Chat 线格式) 与手写常量必须逐字节相同 —— 新增工具不得破坏该不变量。
        Assert.Equal(ActionToolDecl.ToolsJson, ActionToolSpec.ChatToolsJson);
        Assert.Equal(5, ActionToolSpec.All.Length);
    }

    [Fact]
    public async Task NoApprovalChannel_RefusesAndKeepsFile()
    {
        var f = MakeFile("a.txt");
        var r = await Port(gate: null).ExecuteAsync(Del("a.txt"), CancellationToken.None);
        Assert.False(r.Ok);
        Assert.Equal(WorkspaceActionPort.ApprovalUnavailableExitCode, r.ExitCode);
        Assert.True(File.Exists(f), "未接入审批通道时文件必须原封不动");
        Assert.Contains("fail-closed", r.Output);
    }

    [Fact]
    public async Task Approved_DeletesFile_AndReportsKindToApprover()
    {
        var f = MakeFile("a.txt");
        string? seenPath = null;
        bool? seenIsDir = null;
        var r = await Port(async (rel, isDir, ct) =>
        {
            seenPath = rel; seenIsDir = isDir;
            return await Task.FromResult(true);
        }).ExecuteAsync(Del("a.txt"), CancellationToken.None);

        Assert.True(r.Ok);
        Assert.Equal("a.txt", seenPath);
        Assert.False(seenIsDir);
        Assert.False(File.Exists(f));
    }

    [Fact]
    public async Task Denied_KeepsFile_AndReportsDeniedCode()
    {
        var f = MakeFile("a.txt");
        var r = await Port((_, _, _) => Task.FromResult(false)).ExecuteAsync(Del("a.txt"), CancellationToken.None);
        Assert.False(r.Ok);
        Assert.Equal(WorkspaceActionPort.ApprovalDeniedExitCode, r.ExitCode);
        Assert.True(File.Exists(f));
    }

    [Fact]
    public async Task ApproverThrows_FailsClosed()
    {
        var f = MakeFile("a.txt");
        var r = await Port((_, _, _) => throw new InvalidOperationException("channel down"))
            .ExecuteAsync(Del("a.txt"), CancellationToken.None);
        Assert.False(r.Ok);
        Assert.Equal(WorkspaceActionPort.ApprovalDeniedExitCode, r.ExitCode);
        Assert.True(File.Exists(f));
    }

    [Fact]
    public async Task ApproverCancelled_FailsClosed()
    {
        var f = MakeFile("a.txt");
        var r = await Port((_, _, _) => throw new OperationCanceledException())
            .ExecuteAsync(Del("a.txt"), CancellationToken.None);
        Assert.False(r.Ok);
        Assert.Equal(WorkspaceActionPort.ApprovalDeniedExitCode, r.ExitCode);
        Assert.True(File.Exists(f));
    }

    [Fact]
    public async Task Approved_DeletesDirectoryRecursively()
    {
        MakeFile("sub/inner/b.txt");
        bool? seenIsDir = null;
        var r = await Port((_, isDir, _) => { seenIsDir = isDir; return Task.FromResult(true); })
            .ExecuteAsync(Del("sub"), CancellationToken.None);
        Assert.True(r.Ok);
        Assert.True(seenIsDir);
        Assert.False(Directory.Exists(Path.Combine(_root, "sub")));
    }

    [Fact]
    public async Task BoundaryPath_IsRefusedBeforeApproval()
    {
        var calls = 0;
        var outside = Path.Combine(Path.GetTempPath(), "r511-outside-" + Guid.NewGuid().ToString("N")[..8] + ".txt");
        File.WriteAllText(outside, "keep");
        try
        {
            var r = await Port((_, _, _) => { calls++; return Task.FromResult(true); })
                .ExecuteAsync(Del("../" + Path.GetFileName(outside)), CancellationToken.None);
            Assert.False(r.Ok);
            Assert.Equal(0, calls); // 越界路径不得进入审批面
            Assert.True(File.Exists(outside));
        }
        finally { try { File.Delete(outside); } catch { } }
    }

    [Fact]
    public async Task MissingPath_IsRefusedBeforeApproval()
    {
        var calls = 0;
        var r = await Port((_, _, _) => { calls++; return Task.FromResult(true); })
            .ExecuteAsync(Del("nope.txt"), CancellationToken.None);
        Assert.False(r.Ok);
        Assert.Equal(0, calls);
    }

    [Fact]
    public async Task EmptyPath_IsRefused()
    {
        var r = await Port((_, _, _) => Task.FromResult(true))
            .ExecuteAsync(new ActionToolCall { Name = ActionToolDecl.DeleteFile, ArgumentsJson = "{}" },
                          CancellationToken.None);
        Assert.False(r.Ok);
    }
}
