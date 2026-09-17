using System;
using System.IO;
using System.Threading.Tasks;
using agent.action;
using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R520 影子路径闸的两侧样例 (R519 真机实证的缺陷族)。
///
/// 实证 (R519 编排臂, 真实产物):
///   节点把工作区**自身的绝对路径裁成仓根相对串**当工具 path 用
///   (`eval/rover/r519/run-0917-144416/orch/ws/games/life.py`), 端口按「相对根」解析 ⇒
///   文件落到 `&lt;ws&gt;/eval/rover/.../ws/games/life.py` (影子副本), 而 write_file 回 `ok` +
///   回显**请求串** ⇒ 节点读 `games/life.py` 得到另一份, 自述「环境预置的另一版实现, 我的内容未持久化」,
///   随后范围闸判 `out_of_scope` ⇒ 整条编排 fail-closed (n1 失败, n2–n5 未执行, 臂 0/58)。
///
/// 本文件的四类样例 (缺一则「拒绝」不可判):
///   ① 正控 (形态 b): 影子路径必拒, 且**不得**产生影子文件, 报文须给出落点与建议改写;
///   ② 正控 (形态 a): 以根完整路径开头的相对串同拒;
///   ③ 消融臂 (缺陷注入): 闸关 ⇒ 同一影子写必须**成功** (证明拒绝断言是活的, 非恒真);
///   ④ 负控: 区内正常 / 深层嵌套 / **单段同名目录** 都必须照常通过 (防「一刀切全拒」);
///      另: `../` 越界语义逐位不变 (本闸不动 P1)。
/// 环境变量为进程级 ⇒ 复用 R498 的非并行集合。
/// </summary>
[Collection(ActionBoundaryEnvCollection.Name)]
public sealed class R520ShadowPathTests : IDisposable
{
    private readonly string _base = Path.Combine(Path.GetTempPath(), "r520_shadow_" + Guid.NewGuid().ToString("N"));
    private readonly string _root;
    private readonly string _rootName;
    private readonly string _parentName;
    private readonly string? _prevEnv;

    public R520ShadowPathTests()
    {
        _root = Path.Combine(_base, "ws");
        Directory.CreateDirectory(_root);
        _rootName = Path.GetFileName(_root);
        _parentName = Path.GetFileName(_base);
        _prevEnv = Environment.GetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName);
    }

    public void Dispose()
    {
        Environment.SetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName, _prevEnv);
        try { Directory.Delete(_base, true); } catch (IOException) { /* 清理失败不影响判定 */ }
    }

    private WorkspaceActionPort Port() => new(_root);

    private static ActionToolCall Write(string path) => new()
    {
        Id = "r520",
        Name = ActionToolDecl.WriteFile,
        ArgumentsJson = "{\"path\":\"" + path + "\",\"content\":\"r520-body\"}",
    };

    private static ActionToolCall Read(string path) => new()
    {
        Id = "r520",
        Name = ActionToolDecl.ReadFile,
        ArgumentsJson = "{\"path\":\"" + path + "\"}",
    };

    /// <summary>形态 b: 相对串的前 k 段 (k≥2) == 根路径的后 k 段 (机取, 不手抄)。</summary>
    private string ShadowByTailSuffix() => _parentName + "/" + _rootName + "/games/life.py";

    /// <summary>形态 a: 相对串以根的完整路径 (去前导分隔符) 开头。</summary>
    private string ShadowByFullPath() =>
        _root.Replace('\\', '/').TrimStart('/') + "/games/life.py";

    [Fact]
    public async Task 正控_形态b影子路径必拒且不产生影子文件()
    {
        var shadow = ShadowByTailSuffix();
        var port = Port();
        var r = await port.ExecuteAsync(Write(shadow), default);

        Assert.False(r.Ok);
        Assert.Contains("影子路径", r.Output);
        // 报文须给出**落点**与**建议改写** (否则操作者/节点无从纠正)
        Assert.Contains("会落到", r.Output);
        Assert.Contains("games/life.py", r.Output);
        // 影子文件不得被创建
        Assert.False(File.Exists(Path.Combine(_root, shadow)));
    }

    [Fact]
    public async Task 正控_形态a以根完整路径开头同样必拒()
    {
        var shadow = ShadowByFullPath();
        var r = await Port().ExecuteAsync(Write(shadow), default);

        Assert.False(r.Ok);
        Assert.Contains("影子路径", r.Output);
        Assert.False(File.Exists(Path.Combine(_root, shadow)));
    }

    [Fact]
    public async Task 正控_读面同拒_共用同一闸()
    {
        var r = await Port().ExecuteAsync(Read(ShadowByTailSuffix()), default);
        Assert.False(r.Ok);
        Assert.Contains("影子路径", r.Output);
    }

    [Fact]
    public async Task 消融臂_闸关后同一影子写必须成功以证明拒绝是活的()
    {
        Environment.SetEnvironmentVariable(WorkspaceActionPort.BoundaryEnvName, "0");
        var shadow = ShadowByTailSuffix();
        var r = await Port().ExecuteAsync(Write(shadow), default);

        Assert.True(r.Ok);
        // 闸关 ⇒ 确实落到影子位置 (缺陷形态可复现, 且与真机实证的位置形态一致)
        Assert.True(File.Exists(Path.Combine(_root, shadow)), "消融臂应复现影子落盘");
    }

    [Fact]
    public async Task 负控_区内正常路径照常通过()
    {
        var r = await Port().ExecuteAsync(Write("games/life.py"), default);
        Assert.True(r.Ok);
        Assert.True(File.Exists(Path.Combine(_root, "games", "life.py")));
    }

    [Fact]
    public async Task 负控_深层嵌套与非根名目录不得被误杀()
    {
        var port = Port();
        Assert.True((await port.ExecuteAsync(Write("a/b/c.py"), default)).Ok);
        // 单段同名目录 (仅与根**末段**同名) ⇒ 不判 (防一刀切)
        Assert.True((await port.ExecuteAsync(Write(_rootName + "/games/life.py"), default)).Ok);
        // 与根尾相似的**不同**路径 ⇒ 不判
        Assert.True((await port.ExecuteAsync(Write(_parentName + "/other/games/life.py"), default)).Ok);
    }

    [Fact]
    public async Task 负控_越界语义逐位不变()
    {
        var r = await Port().ExecuteAsync(Read("../outside.txt"), default);
        Assert.False(r.Ok);
        Assert.Contains("越界", r.Output);
    }
}
