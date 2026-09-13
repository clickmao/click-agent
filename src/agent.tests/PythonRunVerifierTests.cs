using System;
using System.IO;
using System.Threading.Tasks;
using agent.registry;
using agent.skills;
using Xunit;

namespace agent.tests;

/// <summary>
/// L5 (t8–t12) 运行级验证 (PythonRunVerifier) 单测。
/// 铁律: 默认关闭必须可证 (不执行生成代码)、每一项都要真进程证据、超时必须真杀、
///       输出上限必须**排空** (否则子进程写满管道 → 假超时)。
/// </summary>
public class PythonRunVerifierTests : IDisposable
{
    private readonly string _dir;
    private readonly string? _env0;

    public PythonRunVerifierTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "pyrun_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_dir);
        _env0 = Environment.GetEnvironmentVariable(PythonRunVerifier.EnableEnvName);
    }

    public void Dispose()
    {
        Environment.SetEnvironmentVariable(PythonRunVerifier.EnableEnvName, _env0);
        try { if (Directory.Exists(_dir)) Directory.Delete(_dir, recursive: true); } catch { /* 清理失败不影响断言 */ }
    }

    private string Script(string name, string body)
    {
        var p = Path.Combine(_dir, name);
        File.WriteAllText(p, body);
        return p;
    }

    private static void SetGate(bool on) =>
        Environment.SetEnvironmentVariable(PythonRunVerifier.EnableEnvName, on ? "1" : null);

    [Fact]
    public async Task 默认关闭_拒绝执行_不产生任何进程副作用()
    {
        SetGate(false);
        var path = Script("nope.py", "open('SIDE_EFFECT.txt','w').write('x')\n");

        Assert.False(PythonRunVerifier.IsEnabled(), "默认必须是关");
        var r = await PythonRunVerifier.RunAsync(path);

        Assert.False(r.Ran);
        Assert.Equal(-1, r.ExitCode);
        Assert.Contains("未启用", r.Detail);
        Assert.False(File.Exists(Path.Combine(_dir, "SIDE_EFFECT.txt")), "关闭时绝不允许执行脚本");
    }

    [Fact]
    public void 闸门取值_只认显式开()
    {
        Assert.True(PythonRunVerifier.IsEnabled("1"));
        Assert.True(PythonRunVerifier.IsEnabled("TRUE"));
        Assert.True(PythonRunVerifier.IsEnabled(" on "));
        Assert.True(PythonRunVerifier.IsEnabled("yes"));
        Assert.False(PythonRunVerifier.IsEnabled("0"));
        Assert.False(PythonRunVerifier.IsEnabled("off"));
        Assert.False(PythonRunVerifier.IsEnabled(""));
        Assert.False(PythonRunVerifier.IsEnabled(null));
    }

    [Fact]
    public async Task 合法脚本_真跑_退出码与stdout可证()
    {
        SetGate(true);
        var path = Script("ok.py", "print('PYRUN-OK-4711')\n");

        var r = await PythonRunVerifier.RunAsync(path);

        Assert.True(r.Ran, r.Detail);
        Assert.Equal(0, r.ExitCode);
        Assert.Contains("PYRUN-OK-4711", r.StdOut);
        Assert.False(r.TimedOut);
        Assert.True(r.ElapsedMs >= 0);
    }

    [Fact]
    public async Task 非零退出_捕获stderr与退出码()
    {
        SetGate(true);
        var path = Script("bad.py", "import sys\nsys.stderr.write('BOOM-9\\n')\nsys.exit(3)\n");

        var r = await PythonRunVerifier.RunAsync(path);

        Assert.True(r.Ran);
        Assert.Equal(3, r.ExitCode);
        Assert.Contains("BOOM-9", r.StdErr);
        Assert.False(r.TimedOut);
    }

    [Fact]
    public async Task 超时_真杀进程树_不拖到脚本自然结束()
    {
        SetGate(true);
        var path = Script("slow.py", "import time\ntime.sleep(10)\nprint('never')\n");

        var r = await PythonRunVerifier.RunAsync(path, timeoutMs: 1200);

        Assert.True(r.Ran);
        Assert.True(r.TimedOut, r.Detail);
        Assert.Contains("超时", r.Detail);
        Assert.True(r.ElapsedMs < 6000, $"必须真被杀, 实测 {r.ElapsedMs}ms");
        Assert.DoesNotContain("never", r.StdOut);
    }

    [Fact]
    public async Task 输出上限_截断且排空管道_不误判为超时()
    {
        SetGate(true);
        // 300k 字符 >> 管道缓冲 (~64KB): 不排空就会死锁 → 假超时
        var path = Script("flood.py", "print('x' * 300000)\n");

        var r = await PythonRunVerifier.RunAsync(path, maxOutputChars: 500, timeoutMs: 15000);

        Assert.True(r.Ran);
        Assert.Equal(0, r.ExitCode);
        Assert.False(r.TimedOut, "排空失败会假超时");
        Assert.True(r.OutputTruncated);
        Assert.Equal(500, r.StdOut.Length);
    }

    [Fact]
    public async Task 路径含空格与引号_ArgumentList直连_无shell语义()
    {
        SetGate(true);
        var sub = Path.Combine(_dir, "we ird dir");
        Directory.CreateDirectory(sub);
        var path = Path.Combine(sub, "a b'c.py");
        File.WriteAllText(path, "print('QUOTED-OK')\n");

        var r = await PythonRunVerifier.RunAsync(path);

        Assert.True(r.Ran, r.Detail);
        Assert.Equal(0, r.ExitCode);
        Assert.Contains("QUOTED-OK", r.StdOut);
    }

    [Fact]
    public async Task 脚本不存在_拒绝_不抛异常()
    {
        SetGate(true);
        var r = await PythonRunVerifier.RunAsync(Path.Combine(_dir, "missing.py"));
        Assert.False(r.Ran);
        Assert.Contains("脚本不存在", r.Detail);
    }

    [Fact]
    public async Task 相对路径_子进程cwd被切换也必须解析正确_不产生假阴性()
    {
        SetGate(true);
        // 复现真机场景: 产物根是**相对 cwd 的路径** (插件用 "data/artifacts/..."), 而子进程 cwd 会被切到
        // 脚本所在目录 → 相对路径二次拼接 → 文件不存在 → python exit=2 秒退 (假阴性)。
        // 自持 cwd: 进程 cwd 是全局状态(其他用例也会改), 本用例不得依赖外部是否改动 cwd (否则 flaky)。
        var root = Path.Combine(Path.GetTempPath(), "r371rel_" + Guid.NewGuid().ToString("N"));
        var relDir = Path.Combine(root, "data", "artifacts");
        Directory.CreateDirectory(relDir);
        File.WriteAllText(Path.Combine(relDir, "rel.py"), "print('REL-OK')\n");
        var saved = Directory.GetCurrentDirectory();
        try
        {
            Directory.SetCurrentDirectory(root);   // 只在这段窗口内改 cwd (最小化并行干扰)
            var r = await PythonRunVerifier.RunAsync(Path.Combine("data", "artifacts", "rel.py"));

            Assert.True(r.Ran, r.Detail);
            Assert.Equal(0, r.ExitCode);           // 旧实现此处为 exit=2 (can't open file)
            Assert.Contains("REL-OK", r.StdOut);
            Assert.False(r.TimedOut);
        }
        finally
        {
            Directory.SetCurrentDirectory(saved);
            try { Directory.Delete(root, true); } catch { }
        }
    }

[Fact]
public async Task 产物含selftest_运行级验证自动带_selftest_参数()
    {
        var python = PythonScriptValidator.ResolvePython();
        if (python is null)
            return;

        // 用退出码证明参数真的传进去了: 带 --selftest → 7; 不带 → 3
        const string src = "import sys\nsys.exit(7 if '--selftest' in sys.argv else 3)\n";

        var ledger = new PythonArtifactLedger();
        var plugin = new PythonArtifactPlugin(ledger, _dir, pythonResolver: () => python, runGate: () => true);
        await plugin.HandleAsync(new ResponseSegment
        {
            Kind = SegmentKind.Code, Content = src, Language = "python", StartIndex = 0, Length = src.Length,
        });

        var a = Assert.Single(ledger.Snapshot());
        Assert.True(a.CompileValid, a.Detail);
        Assert.True(a.Ran, a.Detail);
        Assert.Equal(7, a.RunExitCode);          // 关键: 自动带上了 --selftest
    }

    /// <summary>交互式产物 (无 --selftest 入口) 不得被自动带参。</summary>
    [Fact]
    public async Task 产物无selftest_运行级验证不附加参数()
    {
        var python = PythonScriptValidator.ResolvePython();
        if (python is null)
            return;

        var src = "import sys\nsys.exit(7 if '--selftest' in sys.argv else 3)\n".Replace("--selftest", "--x");

        var ledger = new PythonArtifactLedger();
        var plugin = new PythonArtifactPlugin(ledger, _dir, pythonResolver: () => python, runGate: () => true);
        await plugin.HandleAsync(new ResponseSegment
        {
            Kind = SegmentKind.Code, Content = src, Language = "python", StartIndex = 0, Length = src.Length,
        });

        var a = Assert.Single(ledger.Snapshot());
        Assert.True(a.Ran, a.Detail);
        Assert.Equal(3, a.RunExitCode);          // 无参运行
    }

    [Fact]
    public async Task 插件接线_闸门开启时报告含运行证据_关闭时不含()
    {
        var python = PythonScriptValidator.ResolvePython();
        if (python is null)
            return; // 本机无 python3 → 该断言不适用 (其他用例已覆盖解释器缺失路径)

        const string src = "print('ARTIFACT-RUN')\n";

        var onLedger = new PythonArtifactLedger();
        var onPlugin = new PythonArtifactPlugin(onLedger, _dir, pythonResolver: () => python, runGate: () => true);
        await onPlugin.HandleAsync(new ResponseSegment
        {
            Kind = SegmentKind.Code, Content = src, Language = "python", StartIndex = 0, Length = src.Length,
        });
        var a = Assert.Single(onLedger.Snapshot());
        Assert.True(a.CompileValid, a.Detail);
        Assert.True(a.Ran, $"闸门开启必须真跑, detail={a.Detail}");
        Assert.Equal(0, a.RunExitCode);
        Assert.Contains("run:", a.Detail);
        Assert.Contains("exit=0", a.Detail); // 运行证据 (退出码) 必须回写报告

        var offLedger = new PythonArtifactLedger();
        var offPlugin = new PythonArtifactPlugin(offLedger, _dir, pythonResolver: () => python, runGate: () => false);
        await offPlugin.HandleAsync(new ResponseSegment
        {
            Kind = SegmentKind.Code, Content = src, Language = "python", StartIndex = 0, Length = src.Length,
        });
        var b = Assert.Single(offLedger.Snapshot());
        Assert.True(b.CompileValid);
        Assert.False(b.Ran, "闸门关闭不得执行");
        Assert.Equal(-1, b.RunExitCode);
        Assert.DoesNotContain("run:", b.Detail);
    }
}
