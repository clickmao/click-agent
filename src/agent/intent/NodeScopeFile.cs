using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace agent.intent;

/// <summary>
/// 节点写范围契约 (R516) —— 把 R515 的「提示词里写死文件范围」升级为 **fail-closed 机检机制**。
///
/// 起因 (R515 真机读数): 编排器 v1 的 n1∥n2 同层两写者各实现整包、**互相覆盖** (n1 写 3 文件 / n2 写 4 文件),
/// 全包 3/12; 约束只写在提示词里 ⇒ 模型不遵守时无任何机制拦下, 且失败在跑完之后才可见。
///
/// 本文件提供两段机检, 都在**起臂前**完成 (零 LLM 成本):
///   1) 声明合法性: 未知节点 / 路径越界 (绝对路径、`..`) / 空范围 一律拒绝;
///   2) **同层互斥**: 同一层 (并发执行) 的两个节点写范围若可能相交 ⇒ 直接拒收 —— 这是 v1 覆盖事故的**根因面**。
///
/// 语法 (行式, 零 JSON / 零反射):
///   <code>nodeId | 路径1,路径2,...</code>
///   路径相对工作区; 末尾 `/` = 目录前缀; 含 `*` = 字面前缀通配; 其余 = 精确文件; `#` 注释行。
/// </summary>
public static class NodeScopeFile
{
    /// <summary>范围文件模板 (供模型/人照抄; 同时是自测夹具的输入形状)。</summary>
    public const string Template =
        "# 节点写范围契约: 每行 `nodeId | 路径1,路径2`; 路径相对工作区; 末尾 / = 目录前缀, 含 * = 前缀通配; # 注释\n" +
        "n1 | tasksvc/model.py\n" +
        "n2 | tasksvc/cli.py\n";

    /// <summary>解析范围文件文本。返回 (范围表, 问题清单); 问题非空 ⇒ 调用方必须拒绝 (fail-closed)。</summary>
    public static (Dictionary<string, IReadOnlyList<string>>? Scopes, List<string> Problems) ParseText(string? text)
    {
        var problems = new List<string>();
        var scopes = new Dictionary<string, IReadOnlyList<string>>(StringComparer.Ordinal);
        if (string.IsNullOrWhiteSpace(text))
        {
            problems.Add("范围文件为空");
            return (null, problems);
        }

        var lines = text!.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
        for (var i = 0; i < lines.Length; i++)
        {
            var raw = lines[i].Trim();
            if (raw.Length == 0 || raw.StartsWith("#", StringComparison.Ordinal)) continue;
            var parts = raw.Split('|', 2);
            if (parts.Length < 2)
            {
                problems.Add($"第 {i + 1} 行: 字段数 {parts.Length} < 2 (需 `nodeId | 路径[,路径]`)");
                continue;
            }

            var id = parts[0].Trim();
            if (id.Length == 0) { problems.Add($"第 {i + 1} 行: 节点 id 为空"); continue; }
            if (scopes.ContainsKey(id)) { problems.Add($"第 {i + 1} 行: 节点 {id} 范围重复声明"); continue; }

            var rawPaths = parts[1].Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            if (rawPaths.Length == 0) { problems.Add($"第 {i + 1} 行: 节点 {id} 范围为空"); continue; }

            var norm = new List<string>();
            var bad = false;
            foreach (var p in rawPaths)
            {
                var n = Normalize(p);
                if (!IsInsideWorkspace(n))
                {
                    problems.Add($"第 {i + 1} 行: 节点 {id} 路径越界 `{p}` (须为工作区内相对路径)");
                    bad = true;
                    break;
                }
                norm.Add(n);
            }
            if (bad) continue;
            scopes[id] = norm;
        }

        if (problems.Count > 0) return (null, problems);
        if (scopes.Count == 0) { problems.Add("范围文件无任何有效声明"); return (null, problems); }
        return (scopes, problems);
    }

    /// <summary>读范围文件 (失败一律返回问题清单, 不抛)。</summary>
    public static (Dictionary<string, IReadOnlyList<string>>? Scopes, List<string> Problems) Load(string path)
    {
        string text;
        try
        {
            text = File.ReadAllText(path);
        }
        catch (Exception ex)
        {
            return (null, new List<string> { $"范围文件不可读 {path}: {ex.GetType().Name}" });
        }
        return ParseText(text);
    }

    /// <summary>
    /// 范围表 vs 计划的机检 (起臂前):
    ///   U 未知节点 (范围声明指向计划里不存在的 id);
    ///   O **同层重叠** (同层 = 并发; 两节点写范围可能相交 ⇒ 互相覆盖, 拒收)。
    /// </summary>
    public static List<string> Validate(TaskPlan plan, IReadOnlyDictionary<string, IReadOnlyList<string>>? scopes)
    {
        var problems = new List<string>();
        if (scopes is null || scopes.Count == 0) return problems;

        var ids = plan.Nodes.Select(n => n.Id).ToHashSet(StringComparer.Ordinal);
        foreach (var id in scopes.Keys.OrderBy(k => k, StringComparer.Ordinal))
            if (!ids.Contains(id)) problems.Add($"范围声明指向未知节点 {id}");

        foreach (var level in plan.Nodes.GroupBy(n => n.Level).OrderBy(g => g.Key))
        {
            var scoped = level.Where(n => scopes.ContainsKey(n.Id)).ToList();
            for (var i = 0; i < scoped.Count; i++)
            {
                for (var j = i + 1; j < scoped.Count; j++)
                {
                    var a = scoped[i].Id;
                    var b = scoped[j].Id;
                    foreach (var pa in scopes[a])
                    {
                        foreach (var pb in scopes[b])
                        {
                            if (!Overlaps(pa, pb)) continue;
                            problems.Add($"同层节点 {a}/{b} 写范围重叠: `{pa}` ∩ `{pb}` (L{level.Key} 并发执行会互相覆盖 ⇒ fail-closed 拒绝)");
                        }
                    }
                }
            }
        }
        return problems;
    }

    /// <summary>计划里未声明写范围的节点 id (信息项, 供报告如实标注「未声明」而非默认合规)。</summary>
    public static List<string> Undeclared(TaskPlan plan, IReadOnlyDictionary<string, IReadOnlyList<string>>? scopes)
        => plan.Nodes.Where(n => scopes is null || !scopes.ContainsKey(n.Id))
            .Select(n => n.Id)
            .OrderBy(x => x, StringComparer.Ordinal)
            .ToList();

    /// <summary>路径是否落在任一声明范围内 (A/M/D 三态都用同一判定)。</summary>
    public static bool InScope(IReadOnlyList<string> scope, string relativePath)
    {
        for (var i = 0; i < scope.Count; i++)
            if (Matches(scope[i], relativePath)) return true;
        return false;
    }

    /// <summary>单条声明 vs 单个相对路径 (工作区内, 统一 `/` 分隔)。</summary>
    public static bool Matches(string pattern, string relativePath)
    {
        if (pattern.Length == 0 || relativePath.Length == 0) return false;
        if (pattern.EndsWith("/", StringComparison.Ordinal))
        {
            var dir = pattern[..^1];
            return relativePath.Equals(dir, StringComparison.Ordinal) || relativePath.StartsWith(pattern, StringComparison.Ordinal);
        }
        var star = pattern.IndexOf('*');
        if (star >= 0) return relativePath.StartsWith(pattern[..star], StringComparison.Ordinal);
        return relativePath.Equals(pattern, StringComparison.Ordinal);
    }

    /// <summary>两条声明是否可能相交 (保守: 前缀相容即视为相交 ⇒ 宁可拒收不可放过)。</summary>
    public static bool Overlaps(string a, string b)
    {
        var pa = Prefix(a);
        var pb = Prefix(b);
        if (pa.Length == 0 || pb.Length == 0) return true;   // 通配到根 ⇒ 与一切相交
        return Compat(pa, pb) || Compat(pb, pa);
    }

    private static bool Compat(string x, string y)
        => x.Equals(y, StringComparison.Ordinal)
           || y.StartsWith(x + "/", StringComparison.Ordinal)
           || x.StartsWith(y + "/", StringComparison.Ordinal);

    private static string Prefix(string pattern)
    {
        var p = pattern;
        if (p.EndsWith("/", StringComparison.Ordinal)) p = p[..^1];
        var star = p.IndexOf('*');
        if (star >= 0) p = p[..star];
        return p.TrimEnd('/');
    }

    /// <summary>规范化: 反斜杠→`/`, 去 `./` 前缀, 折叠重复分隔符 (保留末尾 `/` 与 `*` 语义标记)。</summary>
    public static string Normalize(string path)
    {
        if (string.IsNullOrWhiteSpace(path)) return string.Empty;
        var s = path.Trim().Replace('\\', '/');
        while (s.StartsWith("./", StringComparison.Ordinal)) s = s[2..];
        while (s.Contains("//", StringComparison.Ordinal)) s = s.Replace("//", "/", StringComparison.Ordinal);
        return s;
    }

    private static bool IsInsideWorkspace(string normalized)
    {
        if (normalized.Length == 0) return false;
        if (normalized.StartsWith("/", StringComparison.Ordinal)) return false;
        if (normalized.Equals("..", StringComparison.Ordinal)) return false;
        if (normalized.StartsWith("../", StringComparison.Ordinal)) return false;
        if (normalized.Contains("/../", StringComparison.Ordinal)) return false;
        if (normalized.EndsWith("/..", StringComparison.Ordinal)) return false;
        return true;
    }
}
