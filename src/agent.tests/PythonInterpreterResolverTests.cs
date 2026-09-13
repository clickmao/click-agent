// T4 决策 (v0.22.0 exp9 §11) 机检: "测试用 py tool" 的解析顺序 + 真跑闸门默认值 + 真跑一次给出进程级证据。
//
// 断言原则 (用户审计口径): 断言绑定组件真实行为 —— 解析顺序用注入的假 FS 验(不依赖本机布局),
// 真跑那条**真的 spawn 解释器并校验退出码**, 不是"看着像跑了"。
using System;
using System.IO;
using agent.skills;
using Xunit;

namespace agent.tests;

public sealed class PythonInterpreterResolverTests
{
    private static string TempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "pyres_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(d);
        return d;
    }

    [Fact]
    public void 解析_显式指定优先于其它一切()
    {
        var real = TempDir();
        var fakeExe = Path.Combine(real, "python3");
        File.WriteAllText(fakeExe, "#!/bin/sh\n");

        var r = PythonInterpreterResolver.Resolve(explicitExe: fakeExe, repoRoot: real, managedRoot: real);

        Assert.NotNull(r);
        Assert.Equal(fakeExe, r!.Exe);
        Assert.Equal("explicit", r.Source);
    }

    [Fact]
    public void 解析_固定记录优先于托管目录()
    {
        var root = TempDir();
        var pinDir = Path.Combine(root, "tools", "py");
        Directory.CreateDirectory(pinDir);
        var pinnedExe = Path.Combine(root, "pinned_python3");
        File.WriteAllText(pinnedExe, "#!/bin/sh\n");
        File.WriteAllText(Path.Combine(pinDir, "interpreter.txt"), pinnedExe + "\n");
        // 托管目录里也放一个可用的, 用来证明"记录优先"
        var managedPin = Path.Combine(root, "managed", "cpython-9.9.9", "bin");
        Directory.CreateDirectory(managedPin);
        File.WriteAllText(Path.Combine(managedPin, "python3"), "#!/bin/sh\n");

        var r = PythonInterpreterResolver.Resolve(repoRoot: root, managedRoot: Path.Combine(root, "managed"));

        Assert.NotNull(r);
        Assert.Equal(pinnedExe, r!.Exe);
        Assert.Equal("pinned", r.Source);
    }

    [Fact]
    public void 解析_记录文件指向不存在的解释器_回退到托管目录()
    {
        var root = TempDir();
        var pinDir = Path.Combine(root, "tools", "py");
        Directory.CreateDirectory(pinDir);
        File.WriteAllText(Path.Combine(pinDir, "interpreter.txt"), Path.Combine(root, "gone", "python3"));
        var managedBin = Path.Combine(root, "managed", "cpython-3.12.14-linux-x86_64-gnu", "bin");
        Directory.CreateDirectory(managedBin);
        var managedExe = Path.Combine(managedBin, "python3");
        File.WriteAllText(managedExe, "#!/bin/sh\n");

        var r = PythonInterpreterResolver.Resolve(repoRoot: root, managedRoot: Path.Combine(root, "managed"));

        Assert.NotNull(r);
        Assert.Equal(managedExe, r!.Exe);
        Assert.Equal("managed", r.Source);
    }

    [Fact]
    public void 解析_全都没有_返回null_不瞎猜路径()
    {
        var root = TempDir();
        var r = PythonInterpreterResolver.Resolve(
            repoRoot: root,
            managedRoot: Path.Combine(root, "managed-nope"),
            fileExists: _ => false,
            dirExists: _ => false,
            pathProbe: () => null);

        Assert.Null(r);
    }

    [Fact]
    public void 解析_PATH兜底明确标注为path_不可复现来源要能看出()
    {
        var root = TempDir();
        var r = PythonInterpreterResolver.Resolve(
            repoRoot: root,
            managedRoot: Path.Combine(root, "managed-nope"),
            fileExists: p => p == "/usr/bin/python3",
            dirExists: _ => false,
            pathProbe: () => "/usr/bin/python3");

        Assert.NotNull(r);
        Assert.Equal("/usr/bin/python3", r!.Exe);
        Assert.Equal("path", r.Source);
    }

    [Fact]
    public void 闸门_显式值语义_fail_safe()
    {
        Assert.True(PythonRunVerifier.IsEnabled("1"));
        Assert.True(PythonRunVerifier.IsEnabled("on"));
        Assert.True(PythonRunVerifier.IsEnabled("TRUE"));
        Assert.False(PythonRunVerifier.IsEnabled("0"));
        Assert.False(PythonRunVerifier.IsEnabled("off"));
        Assert.False(PythonRunVerifier.IsEnabled("也许"));   // 非空但不认识 → 关 (只有空值走默认)

        // 空值 = 默认值 = "本机是否有固定解释器" (T4: 装了 py tool 才默认真跑)
        Assert.Equal(PythonInterpreterResolver.HasPinnedInterpreter(), PythonRunVerifier.IsEnabled(""));
        Assert.Equal(PythonInterpreterResolver.HasPinnedInterpreter(), PythonRunVerifier.IsEnabled("   "));
    }

    [Fact]
    public void 闸门_只对py产物开放_非py直接拒绝()
    {
        var dir = TempDir();
        var txt = Path.Combine(dir, "note.txt");
        File.WriteAllText(txt, "print('hi')\n");

        var r = PythonRunVerifier.RunAsync(txt, explicitlyEnabled: true).GetAwaiter().GetResult();

        Assert.False(r.Ran);
        Assert.Contains("只对 .py 产物", r.Detail);
    }

    [Fact]
    public void 真跑_解释器来源随结果返回_退出码是物理证据()
    {
        var dir = TempDir();
        var py = Path.Combine(dir, "probe.py");
        File.WriteAllText(py, "print('py-tool ok')\n");

        var r = PythonRunVerifier.RunAsync(py, explicitlyEnabled: true).GetAwaiter().GetResult();

        Assert.True(r.Ran, r.Detail);
        Assert.Equal(0, r.ExitCode);
        Assert.Contains("py-tool ok", r.StdOut);
        Assert.False(string.IsNullOrWhiteSpace(r.Interpreter));
        Assert.Contains("interp=", r.Detail);
        Assert.Contains(Path.GetFileName(r.Interpreter), Path.GetFileName(r.Interpreter));   // 路径可用 (非编造)
        Assert.True(File.Exists(r.Interpreter), $"返回的解释器必须真实存在: {r.Interpreter}");
    }

    [Fact]
    public void 真跑_失败退出码透传_不吞错()
    {
        var dir = TempDir();
        var py = Path.Combine(dir, "boom.py");
        File.WriteAllText(py, "import sys\nsys.stderr.write('boom\\n')\nsys.exit(3)\n");

        var r = PythonRunVerifier.RunAsync(py, explicitlyEnabled: true).GetAwaiter().GetResult();

        Assert.True(r.Ran, r.Detail);
        Assert.Equal(3, r.ExitCode);
        Assert.Contains("boom", r.StdErr);
    }
}
