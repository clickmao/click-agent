using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// R368: Python 段落盘 + py_compile 机器校验 (用户钦定 "内置个PY和PY执行插件")。
/// 断言绑定真实行为: 磁盘上确有文件 + py_compile 真实结论 (好代码过 / 坏代码挂)。
/// </summary>
public class PythonArtifactPluginTests : IDisposable
{
    private readonly string _dir;

    public PythonArtifactPluginTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "pyart_" + Guid.NewGuid().ToString("N"));
    }

    public void Dispose()
    {
        try { if (Directory.Exists(_dir)) Directory.Delete(_dir, recursive: true); } catch { /* 清理失败不影响断言 */ }
    }

    private static ResponseSegment Code(string content, string? lang = "python") => new()
    {
        Kind = SegmentKind.Code,
        Content = content,
        Language = lang,
        StartIndex = 0,
        Length = content.Length,
    };

    [Fact]
    public async Task 合法python段_落盘且py_compile通过_内容恒等返回()
    {
        var ledger = new PythonArtifactLedger();
        var plugin = new PythonArtifactPlugin(ledger, _dir);
        const string src = "def add(a, b):\n    return a + b\n";

        var output = await plugin.HandleAsync(Code(src));

        Assert.Equal(src, output);                       // 输出恒等 (不污染围栏)
        var r = Assert.Single(ledger.Snapshot());
        Assert.True(r.CompileValid, $"py_compile 应通过, 实际 detail={r.Detail} exit={r.ExitCode}");
        Assert.Equal(0, r.ExitCode);
        Assert.True(File.Exists(r.Path), "产物必须真实落盘");
        Assert.Equal(src, await File.ReadAllTextAsync(r.Path));
        Assert.Equal(src.Length > 0 ? 8 : 0, r.Sha256Short.Length);
    }

    [Fact]
    public async Task 语法错误的python段_校验失败且不静默()
    {
        var ledger = new PythonArtifactLedger();
        var plugin = new PythonArtifactPlugin(ledger, _dir);

        await plugin.HandleAsync(Code("def broken(:\n    pass\n"));

        var r = Assert.Single(ledger.Snapshot());
        Assert.False(r.CompileValid, "坏语法必须判失败 — 不许静默通过");
        Assert.NotEqual(0, r.ExitCode);
        Assert.False(string.IsNullOrWhiteSpace(r.Detail), "失败必须带原因 (stderr 截断)");
        Assert.True(File.Exists(r.Path), "失败也要留下产物供人工查看");
    }

    [Fact]
    public async Task 非python段_零损耗透传_不产生台账()
    {
        var ledger = new PythonArtifactLedger();
        var plugin = new PythonArtifactPlugin(ledger, _dir);

        var outCsharp = await plugin.HandleAsync(Code("int y = 1;", "csharp"));
        var outPlain = await plugin.HandleAsync(Code("hello", null));

        Assert.Equal("int y = 1;", outCsharp);
        Assert.Equal("hello", outPlain);
        Assert.Empty(ledger.Snapshot());
        Assert.False(Directory.Exists(_dir), "非 python 段不应创建产物目录");
    }

    [Fact]
    public async Task 同内容重复产出_幂等同名()
    {
        var ledger = new PythonArtifactLedger();
        var plugin = new PythonArtifactPlugin(ledger, _dir);
        const string src = "x = 1\n";

        await plugin.HandleAsync(Code(src));
        await plugin.HandleAsync(Code(src));

        var reports = ledger.Snapshot();
        Assert.Equal(2, reports.Count);                       // 两次都记账 (可观测)
        Assert.Equal(reports[0].Sha256Short, reports[1].Sha256Short);
        Assert.Equal(1, Directory.GetFiles(_dir, "*.py").Length); // 内容寻址 → 只一个文件
    }

    [Fact]
    public void 台账版本单调递增_前端增量可读()
    {
        var ledger = new PythonArtifactLedger();
        Assert.Equal(0, ledger.Version);
        ledger.Add(new PythonArtifactReport("p", "python", 1, "abcd1234", true, 0, "ok", 0));
        ledger.Add(new PythonArtifactReport("p2", "python", 2, "abcd1235", false, 1, "boom", 1));
        Assert.Equal(2, ledger.Version);
        Assert.Equal(2, ledger.Snapshot().Count);
    }

    [Fact]
    public async Task 路由器集成_python段经插件后原文还原且台账有记录()
    {
        var ledger = new PythonArtifactLedger();
        var router = new ResponseSegmentRouter(new IResponseSegmentPlugin[]
        {
            new UiCapturePlugin(),
            new PythonArtifactPlugin(ledger, _dir),
        });
        var text = "给你脚本：\n```python\nprint('hi')\n```\n直接跑。";

        var output = await router.ProcessAsync(text);

        Assert.Equal(text, output);                        // 围栏/文本原样还原
        var r = Assert.Single(ledger.Snapshot());
        Assert.True(r.CompileValid);
        Assert.Contains("python-artifact", router.PluginNames);
    }
}
