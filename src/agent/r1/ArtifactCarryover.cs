using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace agent.r1;

/// <summary>
/// R600 · 修复环「带现状」：把**盘上当前产物**按预算随附进回灌修复指令。
///
/// 定因（R592–R599 只读 + R600 定因）：产品默认档失败例次 100% 集中 wythoff 族，主桶 = 冷集构造层。
/// 实测失败臂的产物在**题面公开用例**上就已失败，而管道**已**机械抽取并独立回放这些用例、**已**花掉
/// 一次回灌修复 —— 却仍以同错类交付。代码级根因：R1 管道无状态（状态外置：模型只产契约、执行在管道），
/// 回灌修复轮的 user 轮**只带实测证据与题面**，不带模型上次写下的产物 ⇒ 模型须凭记忆重写整份计划
/// ⇒ 「盲修」。
///
/// 本件只做**字节搬运**：按执行器 write_file 步骤取 path、重读盘上原文、按预算随附。
/// 语言无关（不解析语义、不识别后缀、不读模型自述）；越界路径 / 盘上缺失 / 二进制（含 NUL）一律不随附
/// 但显式列出；生成物目录（段名以 `__` 开头，如 `__pycache__`）静默跳过，不占预算。
/// </summary>
public static class ArtifactCarryover
{
    /// <summary>单文件随附上限（字节）。超限按字节截断并留显式标记。</summary>
    public const int PerFileBytes = 4096;

    /// <summary>随附总量上限（字符）。超限文件列入「未随附」尾注，不静默丢弃。</summary>
    public const int TotalBytes = 16384;

    private const string Header =
        "[artifact] 盘上当前产物 = **管道写入的原文快照**（非模型自述；截断处有显式标记）。"
        + "修复必须以此为准：只改造成失败的部分，其余逐字保留；输出仍是完整 JSON。";

    public static IReadOnlyList<string> Render(string sandboxRoot, IReadOnlyList<StepOutcome> steps) =>
        Render(sandboxRoot, steps, PerFileBytes, TotalBytes);

    public static IReadOnlyList<string> Render(string sandboxRoot, IReadOnlyList<StepOutcome> steps, int perFileBytes, int totalBytes)
    {
        var lines = new List<string>();
        if (steps is null || steps.Count == 0 || string.IsNullOrWhiteSpace(sandboxRoot) || perFileBytes <= 0 || totalBytes <= 0)
        {
            return lines;
        }

        var root = Path.GetFullPath(sandboxRoot);

        // 同一 path 多次写盘 ⇒ 取**最后一次** write（盘上现状即最后一次写的结果），顺序按计划出现序。
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var order = new List<string>();
        for (var i = steps.Count - 1; i >= 0; i--)
        {
            var s = steps[i];
            if (s is null || s.Tool != "write_file" || string.IsNullOrEmpty(s.Path))
            {
                continue;
            }
            var rel = s.Path.Replace('\\', '/');
            if (seen.Add(rel))
            {
                order.Add(rel);
            }
        }
        order.Reverse();

        var used = 0;
        var skipped = new List<string>();
        foreach (var rel in order)
        {
            if (IsGenerated(rel))
            {
                continue;
            }
            string full;
            try
            {
                full = Path.GetFullPath(Path.Combine(root, rel));
            }
            catch (ArgumentException)
            {
                skipped.Add(rel + "(路径非法)");
                continue;
            }
            if (!IsInside(full, root))
            {
                skipped.Add(rel + "(越界, 未随附)");
                continue;
            }
            if (!File.Exists(full))
            {
                skipped.Add(rel + "(盘上不存在)");
                continue;
            }

            byte[] bytes;
            try
            {
                bytes = File.ReadAllBytes(full);
            }
            catch (IOException)
            {
                skipped.Add(rel + "(读失败)");
                continue;
            }
            catch (UnauthorizedAccessException)
            {
                skipped.Add(rel + "(读失败)");
                continue;
            }

            var body = Body(bytes, perFileBytes);
            var block = "--- " + rel + " (" + bytes.Length + " B, sha " + R1Hash.OfBytes(bytes).Substring(0, 12) + ") ---\n"
                + body + "\n--- end " + rel + " ---";
            if (used + block.Length > totalBytes)
            {
                skipped.Add(rel + "(预算用尽)");
                continue;
            }
            if (lines.Count == 0)
            {
                lines.Add(Header);
            }
            lines.Add(block);
            used += block.Length;
        }

        if (lines.Count > 0 && skipped.Count > 0)
        {
            lines.Add("（未随附: " + string.Join(", ", skipped) + "）");
        }
        return lines;
    }

    private static string Body(byte[] bytes, int perFileBytes)
    {
        if (bytes.Length == 0)
        {
            return "(空文件)";
        }
        var take = Math.Min(bytes.Length, perFileBytes);
        for (var i = 0; i < take; i++)
        {
            if (bytes[i] == 0)
            {
                return "(二进制内容含 NUL, 未随附; " + bytes.Length + " 字节)";
            }
        }
        var text = new UTF8Encoding(false).GetString(bytes, 0, take);
        if (take < bytes.Length)
        {
            text += "\n…(截断: 原文 " + bytes.Length + " 字节, 只随附前 " + take + " 字节)";
        }
        return text;
    }

    private static bool IsGenerated(string rel)
    {
        var parts = rel.Split('/');
        foreach (var p in parts)
        {
            if (p.StartsWith("__", StringComparison.Ordinal) || p == ".git" || p == "node_modules")
            {
                return true;
            }
        }
        return false;
    }

    private static bool IsInside(string full, string root)
    {
        if (string.Equals(full, root, StringComparison.Ordinal))
        {
            return true;
        }
        return full.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.Ordinal);
    }
}
