using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.intent;

/// <summary>
/// 计划文件 (R515) —— 长任务编排器的**分解入口**: 把「长任务」写成节点清单, 每节点 = 一次真实执行单元。
///
/// 两种格式:
///   1) **行式 DSL** (默认, 零 JSON / 零反射 / 模型可直接写):
///        # 注释行; 每行一个节点, 字段以 | 分隔:
///        id | 依赖(逗号分隔, 可空) | 位置(remote|local|hybrid) | 执行器(可空) | 文本
///   2) **JSON** (`.json` 后缀): 与 <see cref="TaskPlanJsonContext"/> 同构 (PascalCase 键, Location 为枚举数值)。
///
/// 纪律: 校验 fail-closed —— 未知依赖 / 重复 id / 环 / 本地节点缺执行器 / 空文本 一律**拒绝**,
/// 不静默跳过 (静默跳过 = 节点消失 = 长任务"少做了"却看不出来)。
/// </summary>
public static class TaskPlanFile
{
    /// <summary>DSL 模板 (供模型照抄; 同时是自测夹具的输入形状)。</summary>
    public const string Template =
        "# 长任务计划: 每行一个节点\n" +
        "# id | 依赖(逗号分隔) | 位置(remote|local|hybrid) | 执行器(python.selftest|text.process) | 文本\n" +
        "n1 |          | remote |                 | 第一段工作的自足描述\n" +
        "n2 | n1       | remote |                 | 基于 n1 产出的第二段工作\n" +
        "n3 | n2       | local  | python.selftest | 产物路径 (相对工作区)\n";

    /// <summary>解析行式 DSL。返回 (计划, 问题清单); 问题非空 = 调用方必须拒绝。</summary>
    public static (TaskPlan? Plan, List<string> Problems) ParseText(string? text, string? planId = null)
    {
        var problems = new List<string>();
        var plan = new TaskPlan { PlanId = string.IsNullOrWhiteSpace(planId) ? "plan-" + Guid.NewGuid().ToString("N")[..8] : planId! };
        if (string.IsNullOrWhiteSpace(text))
        {
            problems.Add("计划文本为空");
            return (null, problems);
        }

        var lines = text!.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
        var seen = new HashSet<string>(StringComparer.Ordinal);
        for (var i = 0; i < lines.Length; i++)
        {
            var raw = lines[i].Trim();
            if (raw.Length == 0 || raw.StartsWith("#", StringComparison.Ordinal)) continue;
            // 只切前 4 个分隔符: 节点文本里允许出现 '|' (真实契约文本常含 open|done|expired|all)
            var parts = raw.Split('|', 5);
            if (parts.Length < 5)
            {
                problems.Add($"第 {i + 1} 行: 字段数 {parts.Length} < 5");
                continue;
            }
            var id = parts[0].Trim();
            var deps = parts[1].Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).ToList();
            var locText = parts[2].Trim().ToLowerInvariant();
            var executor = parts[3].Trim();
            var body = string.Join("|", parts.Skip(4)).Trim();

            if (id.Length == 0) { problems.Add($"第 {i + 1} 行: 节点 id 为空"); continue; }
            if (!seen.Add(id)) { problems.Add($"第 {i + 1} 行: 节点 id 重复 {id}"); continue; }
            if (body.Length == 0) { problems.Add($"第 {i + 1} 行: 节点 {id} 文本为空"); continue; }

            NodeExecutionLocation loc;
            switch (locText)
            {
                case "remote" or "": loc = NodeExecutionLocation.Remote; break;
                case "local": loc = NodeExecutionLocation.Local; break;
                case "hybrid": loc = NodeExecutionLocation.Hybrid; break;
                default: problems.Add($"第 {i + 1} 行: 未知位置 {locText}"); continue;
            }
            if (loc == NodeExecutionLocation.Remote && executor.Length > 0)
            { problems.Add($"第 {i + 1} 行: 远端节点 {id} 不应带执行器"); continue; }
            if (loc != NodeExecutionLocation.Remote && executor.Length == 0)
            { problems.Add($"第 {i + 1} 行: {locText} 节点 {id} 缺执行器"); continue; }

            plan.Nodes.Add(new PlanNode
            {
                Id = id,
                Text = body,
                DependsOn = deps,
                Location = loc,
                LocalExecutorId = executor.Length > 0 ? executor : null,
                Intent = IntentRecognizer.Intents.General,
            });
        }

        if (plan.Nodes.Count == 0) problems.Add("计划无任何节点");
        if (problems.Count > 0) return (null, problems);

        // 依赖存在性必须先于层级计算 (否则 unknown dep 会以 KeyNotFound 逸出 = 静默崩, 失 fail-closed 语义)
        var known = plan.Nodes.Select(n => n.Id).ToHashSet(StringComparer.Ordinal);
        foreach (var n in plan.Nodes)
            foreach (var dep in n.DependsOn)
                if (!known.Contains(dep)) problems.Add($"节点 {n.Id} 依赖未知节点 {dep}");
        if (problems.Count > 0) return (null, problems);

        var (levels, levelProblems) = ComputeLevels(plan);
        if (levelProblems.Count > 0) return (null, levelProblems);
        foreach (var n in plan.Nodes) n.Level = levels[n.Id];
        plan.SourceText = text!;
        return (plan, new List<string>());
    }

    /// <summary>读文件: `.json` → TaskPlanJsonContext; 其余 → 行式 DSL。失败一律返回问题清单。</summary>
    public static (TaskPlan? Plan, List<string> Problems) Load(string path)
    {
        string text;
        try
        {
            text = File.ReadAllText(path);
        }
        catch (Exception ex)
        {
            return (null, new List<string> { $"计划文件不可读 {path}: {ex.GetType().Name}" });
        }

        if (path.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
        {
            try
            {
                var plan = JsonSerializer.Deserialize(text, TaskPlanJsonContext.Default.TaskPlan);
                if (plan is null || plan.Nodes.Count == 0)
                    return (null, new List<string> { "JSON 计划为空或节点缺失 (键须为 PascalCase: PlanId/Nodes/Id/Text/DependsOn/Level/Location)" });
                var problems = Validate(plan, 24);
                if (problems.Count > 0) return (null, problems);
                return (plan, new List<string>());
            }
            catch (JsonException ex)
            {
                return (null, new List<string> { $"JSON 计划解析失败: {ex.Message}" });
            }
        }

        return ParseText(text, Path.GetFileNameWithoutExtension(path));
    }

    /// <summary>结构校验 (DSL 与 JSON 共用): 依赖存在性 / 环 / 一致的位置-执行器 / 节点数上限。</summary>
    public static List<string> Validate(TaskPlan plan, int maxNodes)
    {
        var problems = new List<string>();
        if (plan.Nodes.Count == 0) { problems.Add("计划无任何节点"); return problems; }
        if (plan.Nodes.Count > maxNodes) problems.Add($"节点数 {plan.Nodes.Count} 超上限 {maxNodes}");

        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var n in plan.Nodes)
        {
            if (n.Id.Length == 0) problems.Add("存在空 id 节点");
            else if (!ids.Add(n.Id)) problems.Add($"节点 id 重复 {n.Id}");
            if (string.IsNullOrWhiteSpace(n.Text)) problems.Add($"节点 {n.Id} 文本为空");
            if (n.Location == NodeExecutionLocation.Remote && !string.IsNullOrEmpty(n.LocalExecutorId))
                problems.Add($"远端节点 {n.Id} 不应带执行器");
            if (n.Location != NodeExecutionLocation.Remote && string.IsNullOrEmpty(n.LocalExecutorId))
                problems.Add($"{n.LocationText} 节点 {n.Id} 缺执行器");
        }

        foreach (var n in plan.Nodes)
            foreach (var dep in n.DependsOn)
                if (!ids.Contains(dep)) problems.Add($"节点 {n.Id} 依赖未知节点 {dep}");

        if (problems.Count > 0) return problems;
        var (_, levelProblems) = ComputeLevels(plan);
        problems.AddRange(levelProblems);
        return problems;
    }

    /// <summary>按依赖深度重算 level (拓扑序); 检出环即报错 (不做静默降级)。</summary>
    public static (Dictionary<string, int> Levels, List<string> Problems) ComputeLevels(TaskPlan plan)
    {
        var problems = new List<string>();
        var byId = plan.Nodes.ToDictionary(n => n.Id, n => n, StringComparer.Ordinal);
        var levels = new Dictionary<string, int>(StringComparer.Ordinal);
        var visiting = new HashSet<string>(StringComparer.Ordinal);

        int Depth(string id)
        {
            if (levels.TryGetValue(id, out var cached)) return cached;
            if (!visiting.Add(id))
            {
                problems.Add($"依赖成环: {id}");
                return 0;
            }
            var max = 0;
            foreach (var dep in byId[id].DependsOn)
            {
                if (!byId.ContainsKey(dep)) { problems.Add($"节点 {id} 依赖未知节点 {dep}"); continue; }
                max = Math.Max(max, Depth(dep) + 1);
            }
            visiting.Remove(id);
            levels[id] = max;
            return max;
        }

        foreach (var n in plan.Nodes)
        {
            Depth(n.Id);
            if (problems.Count > 0) return (levels, problems);
        }
        return (levels, problems);
    }

    /// <summary>把计划渲染回 DSL (遥测/报告用)。</summary>
    public static string Render(TaskPlan plan)
    {
        var sb = new StringBuilder();
        foreach (var n in plan.Nodes.OrderBy(n => n.Level).ThenBy(n => n.Id, StringComparer.Ordinal))
        {
            sb.Append(n.Id).Append(" | ")
              .Append(string.Join(",", n.DependsOn)).Append(" | ")
              .Append(n.LocationText).Append(" | ")
              .Append(n.LocalExecutorId ?? "").Append(" | ")
              .Append(n.Text.Replace('\n', ' ')).Append('\n');
        }
        return sb.ToString();
    }

    /// <summary>单行摘要 (每个节点一行, 供汇报表直接粘贴)。</summary>
    public static string Summary(TaskPlan plan, IEnumerable<TaskOrchestrator.NodeTelemetry> telemetry)
    {
        var byId = telemetry.ToDictionary(t => t.NodeId, t => t, StringComparer.Ordinal);
        var sb = new StringBuilder();
        foreach (var n in plan.Nodes.OrderBy(n => n.Level).ThenBy(n => n.Id, StringComparer.Ordinal))
        {
            if (!byId.TryGetValue(n.Id, out var t))
            {
                sb.Append(CultureInfo.InvariantCulture, $"{n.Id}\tL{n.Level}\t{n.LocationText}\t(未执行)\t\t\t\n");
                continue;
            }
            sb.Append(CultureInfo.InvariantCulture,
                $"{n.Id}\tL{n.Level}\t{n.LocationText}\t{t.State}\t{t.ElapsedMs}ms\tout={t.OutputChars}\t{t.Error}\n");
        }
        return sb.ToString();
    }
}
