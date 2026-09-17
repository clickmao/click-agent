using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text;
using Xunit;

namespace agent.tests;

/// <summary>
/// 重构判据⑤ — 公共 API 面基线 (证明「外部可见行为不变」的机器证据)。
/// 判据: 公共类型/成员的签名集合, 重构前后逐行相等 (排序后逐字节)。
/// 基线: docs/api-surface.baseline.txt   重生: AGENTFRAMEWORK_API_BASELINE_WRITE=1
/// 负控: 比较器对 增/删/改 三类差异必报 ⇒ 非恒绿 (NC_比较器非恒绿)。
/// </summary>
public class PublicApiSurfaceTests
{
    private const string BaselineName = "api-surface.baseline.txt";

    /// <summary>收集给定程序集的公共 API 签名 (排序, 逐行一个)。</summary>
    public static List<string> SignaturesOf(Assembly asm)
    {
        var outp = new List<string>();
        Type[] types;
        try { types = asm.GetTypes(); }
        catch (ReflectionTypeLoadException ex) { types = ex.Types.Where(t => t != null).Select(t => t!).ToArray(); }

        foreach (var t in types)
        {
            if (t == null) continue;
            if (!(t.IsPublic || t.IsNestedPublic)) continue;
            if (t.GetCustomAttribute<CompilerGeneratedAttribute>() != null) continue;
            outp.Add("T:" + Full(t));

            const BindingFlags Bf = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
                                  | BindingFlags.Static | BindingFlags.DeclaredOnly;

            foreach (var m in t.GetMethods(Bf))
            {
                if (m.IsSpecialName || m.GetCustomAttribute<CompilerGeneratedAttribute>() != null) continue;
                if (!Visible(m)) continue;
                outp.Add($"M:{Full(t)}.{m.Name}({string.Join(",", m.GetParameters().Select(p => Full(p.ParameterType)))}):{Full(m.ReturnType)}");
            }
            foreach (var p in t.GetProperties(Bf))
            {
                var acc = p.GetMethod ?? p.SetMethod;
                if (acc == null || !Visible(acc)) continue;
                outp.Add($"P:{Full(t)}.{p.Name}:{Full(p.PropertyType)}");
            }
            foreach (var f in t.GetFields(Bf))
            {
                if (!(f.IsPublic || f.IsFamily || f.IsFamilyOrAssembly)) continue;
                outp.Add($"F:{Full(t)}.{f.Name}:{Full(f.FieldType)}");
            }
            foreach (var e in t.GetEvents(Bf))
            {
                var acc = e.AddMethod ?? e.RemoveMethod;
                if (acc == null || !Visible(acc)) continue;
                outp.Add($"E:{Full(t)}.{e.Name}:{Full(e.EventHandlerType!)}");
            }
        }
        outp.Sort(StringComparer.Ordinal);
        return outp;
    }

    private static bool Visible(MethodBase m) => m.IsPublic || m.IsFamily || m.IsFamilyOrAssembly;

    private static string Full(Type t)
    {
        if (t.IsGenericParameter) return t.Name;
        if (t.IsByRef) return Full(t.GetElementType()!) + "&";
        if (t.IsArray) return Full(t.GetElementType()!) + "[" + new string(',', t.GetArrayRank() - 1) + "]";
        if (t.IsGenericType)
        {
            var name = t.GetGenericTypeDefinition().FullName ?? t.GetGenericTypeDefinition().Name;
            var tick = name.IndexOf('`');
            if (tick >= 0) name = name[..tick];
            return name + "<" + string.Join(",", t.GetGenericArguments().Select(Full)) + ">";
        }
        return t.FullName ?? t.Name;
    }

    /// <summary>比较器 (纯函数, 可注入 ⇒ 负控)。返回 缺失/新增 两类差异行。</summary>
    public static List<string> Diff(IEnumerable<string> expected, IEnumerable<string> actual)
    {
        var e = new HashSet<string>(expected, StringComparer.Ordinal);
        var a = new HashSet<string>(actual, StringComparer.Ordinal);
        var d = new List<string>();
        d.AddRange(e.Except(a, StringComparer.Ordinal).Select(x => "MISSING " + x));
        d.AddRange(a.Except(e, StringComparer.Ordinal).Select(x => "ADDED   " + x));
        return d;
    }

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln"))) dir = dir.Parent;
        Assert.True(dir != null, "未找到仓根 (agent.sln)");
        return dir!.FullName;
    }

    private static List<Assembly> ProductAssemblies()
    {
        var outp = new List<Assembly>();
        foreach (var f in Directory.GetFiles(AppContext.BaseDirectory, "agent*.dll").OrderBy(x => x, StringComparer.Ordinal))
        {
            var n = Path.GetFileNameWithoutExtension(f);
            if (n.Contains("test", StringComparison.OrdinalIgnoreCase)) continue;
            try { outp.Add(Assembly.LoadFrom(f)); } catch (Exception) { /* 非托管/依赖缺失: 跳过, 不计入面 */ }
        }
        return outp;
    }

    private static List<string> CurrentSurface()
    {
        var all = new List<string>();
        foreach (var a in ProductAssemblies())
        {
            var n = a.GetName().Name!;
            foreach (var s in SignaturesOf(a)) all.Add(n + "|" + s);
        }
        all.Sort(StringComparer.Ordinal);
        return all;
    }

    [Fact]
    public void I_公共API面与基线逐行相等()
    {
        var root = RepoRoot();
        var path = Path.Combine(root, "docs", BaselineName);
        var current = CurrentSurface();
        Assert.True(current.Count > 0, "未收集到任何公共 API 签名 (程序集加载失败?)");

        if (Environment.GetEnvironmentVariable("AGENTFRAMEWORK_API_BASELINE_WRITE") == "1")
        {
            File.WriteAllText(path, string.Join("\n", current) + "\n", new UTF8Encoding(false));
            return;
        }

        Assert.True(File.Exists(path), $"缺基线 {path}; 先以 AGENTFRAMEWORK_API_BASELINE_WRITE=1 生成");
        var expected = File.ReadAllLines(path).Where(l => l.Length > 0).ToList();
        var diff = Diff(expected, current);
        Assert.True(diff.Count == 0,
            $"公共 API 面变化 {diff.Count} 处 (重构=外部可见行为不变 ⇒ 应 0; 若有意变更须显式重生基线并标口径):\n"
            + string.Join("\n", diff.Take(40)));
    }

    [Fact]
    public void NC_比较器非恒绿()
    {
        var a = new[] { "agent.dll|T:a.A", "agent.dll|M:a.A.M():System.Void" };
        var b = new[] { "agent.dll|T:a.A", "agent.dll|M:a.A.M():System.Void" };
        Assert.Empty(Diff(a, b));                                                   // 同 ⇒ 静
        Assert.NotEmpty(Diff(a, b.Append("agent.dll|T:a.B").ToArray()));            // 增 ⇒ 红
        Assert.NotEmpty(Diff(a, b.Take(1).ToArray()));                              // 删 ⇒ 红
        Assert.NotEmpty(Diff(a, new[] { "agent.dll|T:a.A", "agent.dll|M:a.A.M():System.Int32" })); // 改 ⇒ 红
    }
}
