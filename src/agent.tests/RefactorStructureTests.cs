using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Xunit;

namespace agent.tests;

/// <summary>
/// R526 完全重构 — 项目级结构不变式机检 (判据, 非说明):
///   I1 单类型单文件: 每个 .cs 至多 1 个顶层类型声明
///   I2 文件名=类型名: &lt;Type&gt;.cs 或 &lt;Type&gt;.&lt;片段&gt;.cs
///   I3 命名空间: 每个文件必须显式声明命名空间, 且同一目录内命名空间唯一
/// 豁免 (逐条登记, 新违规不豁免): Program.cs (顶层语句) / agent.core 下两个沿用旧命名空间的子目录
/// (收敛计划见 docs/reports/r526-project-refactor.md §6)。
/// 负控见 NC_结构自检器非恒绿: 注入 4 类缺陷必红 ⇒ 机检非恒绿。
/// </summary>
public class RefactorStructureTests
{
    private static readonly Regex RxType = new(
        @"^(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref|unsafe|file)\s+)*" +
        @"(?:record\s+struct|record\s+class|class|record|struct|interface|enum)\s+(?<n>\w+)",
        RegexOptions.Multiline | RegexOptions.Compiled);
    private static readonly Regex RxNsFile = new(@"^[ \t]*namespace\s+([\w.]+)\s*;", RegexOptions.Multiline | RegexOptions.Compiled);
    private static readonly Regex RxNsBlock = new(@"^[ \t]*namespace\s+([\w.]+)\s*$", RegexOptions.Multiline | RegexOptions.Compiled);

    /// <summary>豁免目录 (src 下相对路径) → 允许沿用的旧命名空间。逐条登记, 不得放行新违规。</summary>
    private static readonly Dictionary<string, string> NsExempt = new(StringComparer.Ordinal)
    {
        // R527 候选①: agent.core/{userinteraction,subagent} 已收敛 ⇒ 不再需要目录→命名空间豁免
    };

    private static readonly string Root = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var d = new DirectoryInfo(AppContext.BaseDirectory);
        while (d is not null && !File.Exists(Path.Combine(d.FullName, "agent.sln")))
        {
            d = d.Parent;
        }
        Assert.False(d is null, "找不到仓库根 (agent.sln)");
        return d!.FullName;
    }

    private static IEnumerable<(string Rel, string Text)> SourceFiles()
    {
        var dir = Path.Combine(Root, "src");
        foreach (var f in Directory.EnumerateFiles(dir, "*.cs", SearchOption.AllDirectories)
                     .OrderBy(x => x, StringComparer.Ordinal))
        {
            var rel = Path.GetRelativePath(dir, f).Replace('\\', '/');
            if (rel.Contains("/obj/") || rel.Contains("/bin/"))
            {
                continue;
            }
            yield return (rel, File.ReadAllText(f));
        }
    }

    /// <summary>机检核心 — 对给定文件集合返回违规 (内存样本与真实树同算法 ⇒ 负控可注入)。</summary>
    internal static Dictionary<string, List<string>> Scan(IEnumerable<(string Rel, string Text)> files)
    {
        var viol = new Dictionary<string, List<string>>
        {
            ["I1"] = new(), ["I2"] = new(), ["I3a"] = new(), ["I3b"] = new(),
        };
        var perDir = new Dictionary<string, List<(string Ns, string Rel)>>(StringComparer.Ordinal);
        foreach (var (rel, text) in files)
        {
            var stem = Path.GetFileNameWithoutExtension(rel);
            // 顶层类型声明: 行首 (无前导空白) 的位置
            var types = new List<string>();
            foreach (Match m in RxType.Matches(text))
            {
                if (m.Index == 0 || text[m.Index - 1] == '\n')
                {
                    types.Add(m.Groups["n"].Value);
                }
            }
            if (types.Count > 1)
            {
                viol["I1"].Add($"{rel}: {string.Join(",", types)}");
            }
            else if (types.Count == 1 && stem != "Program"
                     && stem != types[0] && !stem.StartsWith(types[0] + ".", StringComparison.Ordinal))
            {
                viol["I2"].Add($"{rel}: 类型 {types[0]}");
            }

            var nsMatch = RxNsFile.Match(text);
            if (!nsMatch.Success)
            {
                nsMatch = RxNsBlock.Match(text);
            }
            var ns = nsMatch.Success ? nsMatch.Groups[1].Value : "<无>";
            if (ns == "<无>")
            {
                if (stem != "Program")
                {
                    viol["I3a"].Add($"{rel}: 无命名空间声明");
                }
                continue;
            }
            var dir = rel.Contains('/') ? rel[..rel.LastIndexOf('/')] : "";
            if (!perDir.TryGetValue(dir, out var lst))
            {
                perDir[dir] = lst = new List<(string, string)>();
            }
            lst.Add((ns, rel));
        }

        foreach (var (dir, lst) in perDir)
        {
            var distinct = lst.Select(x => x.Ns).Distinct(StringComparer.Ordinal).ToList();
            if (distinct.Count <= 1)
            {
                continue;
            }
            if (NsExempt.TryGetValue(dir, out var allowed) && distinct.Count == 2 && distinct.Contains(allowed))
            {
                continue;   // 已登记的遗产命名空间 (逐条, 新违规不豁免)
            }
            viol["I3b"].Add($"{dir}: 混用命名空间 [{string.Join(",", distinct)}]");
        }
        return viol;
    }

    [Fact]
    public void I1_单类型单文件()
    {
        var v = Scan(SourceFiles());
        Assert.True(v["I1"].Count == 0, "I1 违规 (一个文件含多个顶层类型):\n  " + string.Join("\n  ", v["I1"]));
    }

    [Fact]
    public void I2_文件名等于类型名()
    {
        var v = Scan(SourceFiles());
        Assert.True(v["I2"].Count == 0, "I2 违规 (文件名 ≠ 类型名):\n  " + string.Join("\n  ", v["I2"]));
    }

    [Fact]
    public void I3a_命名空间齐备()
    {
        var v = Scan(SourceFiles());
        Assert.True(v["I3a"].Count == 0, "I3a 违规 (缺命名空间声明):\n  " + string.Join("\n  ", v["I3a"]));
    }

    [Fact]
    public void I3b_目录内命名空间唯一()
    {
        var v = Scan(SourceFiles());
        Assert.True(v["I3b"].Count == 0, "I3b 违规 (同目录混用命名空间):\n  " + string.Join("\n  ", v["I3b"]));
    }

    /// <summary>负控: 4 类注入缺陷必须被同一机检器判红 (证明判据有判别力, 非恒绿)。</summary>
    [Fact]
    public void NC_结构自检器非恒绿()
    {
        var samples = new List<(string Rel, string Text)>
        {
            ("a/TwoTypes.cs", "namespace a;\npublic class TwoTypes { }\npublic class Extra { }\n"),
            ("a/WrongName.cs", "namespace a;\npublic class ActualType { }\n"),
            ("a/NoNs.cs", "public class NoNs { }\n"),
            ("a/Valid.cs", "namespace a;\npublic class Valid { }\n"),
            ("a/b/Mix.cs", "namespace other.ns;\npublic class Mix { }\n"),
            ("a/b/Ok.cs", "namespace a.b;\npublic class Ok { }\n"),
        };
        var v = Scan(samples);
        Assert.Contains(v["I1"], s => s.StartsWith("a/TwoTypes.cs", StringComparison.Ordinal));
        Assert.Contains(v["I2"], s => s.StartsWith("a/WrongName.cs", StringComparison.Ordinal));
        Assert.Contains(v["I3a"], s => s.StartsWith("a/NoNs.cs", StringComparison.Ordinal));
        Assert.Contains(v["I3b"], s => s.StartsWith("a/b:", StringComparison.Ordinal));
        Assert.DoesNotContain(v["I1"], s => s.StartsWith("a/Valid.cs", StringComparison.Ordinal));
        Assert.DoesNotContain(v["I2"], s => s.StartsWith("a/Valid.cs", StringComparison.Ordinal));
        Assert.DoesNotContain(v["I3a"], s => s.StartsWith("a/Valid.cs", StringComparison.Ordinal));
    }
}
