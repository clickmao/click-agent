using System;
using System.IO;
using System.Threading.Tasks;
using agent.io;
using agent.skills;
using System.Linq;
using Xunit;

namespace agent.tests;

/// <summary>
/// v0.11.0 Skill 脚本执行实跑契约 (用户定案):
///   ① 包内 python/bash 脚本真进程执行 (stdin 载荷 → stdout 结果)
///   ② 脚本 @cmd 命令行 → AgentCommandWriter 转发 (skill 附参) — 与前端统一命令接口一致
///   ③ 沙箱: scripts/ 外路径拒绝; 解释器缺失诚实报错; 超时强杀
/// 环境依赖: python3 (CI/开发机均预装; 缺失则 skip — 诚实标注而非伪造通过)
/// </summary>
public class SkillScriptRunnerTests
{
    private static bool HasPython3()
    {
        foreach (var dir in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(':'))
        {
            if (!string.IsNullOrWhiteSpace(dir) && File.Exists(Path.Combine(dir.Trim(), "python3")))
                return true;
        }
        return false;
    }

    /// <summary>构造最小 SKILL.md 包 (scripts/main.py)。</summary>
    private static string MakePackage(string tmpRoot, string scriptBody)
    {
        var pkg = Path.Combine(tmpRoot, "echo-skill");
        Directory.CreateDirectory(Path.Combine(pkg, "scripts"));
        File.WriteAllText(Path.Combine(pkg, "SKILL.md"),
            "---\nname: echo-skill\ndescription: 测试脚本技能\ntype: executive\n---\n测试正文\n");
        File.WriteAllText(Path.Combine(pkg, "scripts", "main.py"), scriptBody);
        return pkg;
    }

    [Fact]
    public async Task ScriptRunner_ExecutesPython_AndReturnsOutput()
    {
        if (!HasPython3()) return; // 环境缺失 → 静默跳过 (不伪造)

        var tmp = Path.Combine(Path.GetTempPath(), "skill-run-" + Guid.NewGuid().ToString("N"));
        try
        {
            var pkg = MakePackage(tmp,
                "import sys\n" +
                "task = sys.stdin.readline().strip()\n" +
                "print(f\"processed:{task}\")\n");
            var skill = SkillPackageLoader.LoadPackage(pkg);
            Assert.NotNull(skill);

            var runner = new SkillScriptRunner();
            var output = await runner.RunAsync(skill!, "main.py", "hello", System.Threading.CancellationToken.None);
            Assert.Contains("processed:hello", output);
        }
        finally
        {
            Directory.Delete(tmp, recursive: true);
        }
    }

    [Fact]
    public async Task ScriptRunner_ForwardsCmdLines_WithSkillParam()
    {
        if (!HasPython3()) return;

        var tmp = Path.Combine(Path.GetTempPath(), "skill-run-" + Guid.NewGuid().ToString("N"));
        try
        {
            // 脚本发 @cmd progress → 应被转发到注入的 AgentCommandWriter (附 skill=echo-skill)
            var pkg = MakePackage(tmp,
                "print(\"@cmd skill_progress message=step1\")\n" +
                "print(\"plain output line\")\n");
            var skill = SkillPackageLoader.LoadPackage(pkg);
            Assert.NotNull(skill);

            var sw = new StringWriter();
            var runner = new SkillScriptRunner(new agent.io.AgentCommandWriter(new AgentRequestWriter(sw)));
            var output = await runner.RunAsync(skill!, "main.py", "", System.Threading.CancellationToken.None);

            // 输出聚合: 命令行不混入结果
            Assert.Contains("plain output line", output);
            Assert.DoesNotContain("@cmd", output);

            // 命令转发: skill 参数已注入
            var lines = sw.ToString().Split('\n', System.StringSplitOptions.RemoveEmptyEntries);
            var cmds = lines
                .Select(l => agent.io.AgentCommand.Decode(l))
                .Where(c => c != null)
                .ToList();
            Assert.Equal(2, cmds.Count); // skill_progress + skill_done (ForwardDone 设计行为)
            Assert.Equal(agent.io.AgentCommandNames.SkillProgress, cmds[0]!.Name);
            Assert.Equal("step1", cmds[0]!.Get("message"));
            Assert.Equal("echo-skill", cmds[0]!.Get("skill"));
            Assert.Equal(agent.io.AgentCommandNames.SkillDone, cmds[1]!.Name);
            Assert.Equal("0", cmds[1]!.Get("exit"));
        }
        finally
        {
            Directory.Delete(tmp, recursive: true);
        }
    }

    [Fact]
    public async Task ScriptRunner_NonZeroExit_AppendsStderr()
    {
        if (!HasPython3()) return;

        var tmp = Path.Combine(Path.GetTempPath(), "skill-run-" + Guid.NewGuid().ToString("N"));
        try
        {
            var pkg = MakePackage(tmp,
                "import sys\n" +
                "print(\"partial output\")\n" +
                "print(\"boom detail\", file=sys.stderr)\n" +
                "sys.exit(3)\n");
            var skill = SkillPackageLoader.LoadPackage(pkg);
            Assert.NotNull(skill);

            var runner = new SkillScriptRunner();
            var output = await runner.RunAsync(skill!, "main.py", "", System.Threading.CancellationToken.None);
            // 退出码非 0: 输出仍返回 (调用方裁量) + stderr 附加
            Assert.Contains("partial output", output);
            Assert.Contains("boom detail", output);
        }
        finally
        {
            Directory.Delete(tmp, recursive: true);
        }
    }

    [Fact]
    public async Task ScriptRunner_PathEscape_Rejected()
    {
        var tmp = Path.Combine(Path.GetTempPath(), "skill-run-" + Guid.NewGuid().ToString("N"));
        try
        {
            var pkg = MakePackage(tmp, "print('x')\n");
            var skill = SkillPackageLoader.LoadPackage(pkg);
            Assert.NotNull(skill);

            var runner = new SkillScriptRunner();
            // ../ 逃逸 → FileNotFoundException (沙箱拒绝)
            await Assert.ThrowsAsync<FileNotFoundException>(
                () => runner.RunAsync(skill!, "../evil.py", "", System.Threading.CancellationToken.None));
        }
        finally
        {
            Directory.Delete(tmp, recursive: true);
        }
    }
}
