using System;
using System.Collections.Generic;

namespace agent.r1;

/// <summary>
/// R1 管道 · 公开用例抽取器（**纯文本、确定性、零模型参与**）。
///
/// 抽取形态（只认题面里显式写出的两种结构，其余一律判「抽不出」⇒ 探针不启用）：
///   ① 命令模板：任意一行里出现反引号包裹、且含 <c>&lt;占位符&gt;</c> 的命令片段
///      （如 <c>`python3 -m games &lt;game_id&gt;`</c>）⇒ 前缀 = 占位符之前的字面量。
///   ② 用例块：以 <c>### </c> 开头且含反引号词元的行为**分组**（如 <c>### 游戏 `life`（…）</c>）；
///      分组内 <c>输入:</c> 行 → 直到 <c>期望输出:</c> 行为输入正文，其后直到空行/分级标题/
///      「请把…」类指示行/下一个 <c>输入:</c> 为期望正文。输入与期望成对才收。
///
/// 纪律：抽不出 = 返回 false + 原因（调用方据此**不启用**探针）；不做猜测性补全，
/// 不把模型自述的期望当输入。抽取结果是**证据面**（进修复轮与台账），故必须是可复算的。
/// </summary>
public static class PublicExampleExtractor
{
    public const int MaxExamples = 16;

    public static bool TryExtract(string? taskText, out PublicExampleSet set, out string reason)
    {
        set = null!;
        reason = string.Empty;
        if (string.IsNullOrWhiteSpace(taskText))
        {
            reason = "empty_task";
            return false;
        }

        var lines = taskText!.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
        var prefix = FindCommandPrefix(lines);
        if (prefix is null)
        {
            reason = "no_command_placeholder";
            return false;
        }

        var examples = new List<PublicExample>();
        string? groupId = null;
        for (var i = 0; i < lines.Length; i++)
        {
            var line = lines[i];
            if (IsSectionHead(line))
            {
                groupId = SectionId(line);
                continue;
            }
            if (groupId is null || line.Trim() != "输入:")
            {
                continue;
            }

            var input = new List<string>();
            var j = i + 1;
            for (; j < lines.Length && !IsBlockEnd(lines[j]) && lines[j].Trim() != "期望输出:"; j++)
            {
                input.Add(lines[j]);
            }
            if (j >= lines.Length || lines[j].Trim() != "期望输出:")
            {
                // 回退一格再自增 ⇒ 终止行本身仍会被下一轮评估（分级标题必须能更新分组 id, 否则
                // 后续用例会被错挂到上一个分组 —— 归属错误会被直接读成结论）。
                i = j - 1;
                continue;
            }

            var expected = new List<string>();
            var k = j + 1;
            for (; k < lines.Length && !IsBlockEnd(lines[k]); k++)
            {
                expected.Add(lines[k]);
            }
            i = k - 1;

            if (input.Count == 0 || expected.Count == 0)
            {
                continue;
            }
            examples.Add(new PublicExample(groupId, string.Join("\n", input), string.Join("\n", expected)));
            if (examples.Count >= MaxExamples)
            {
                break;
            }
        }

        if (examples.Count == 0)
        {
            reason = "no_example_blocks";
            return false;
        }

        set = new PublicExampleSet(prefix, examples);
        reason = "ok";
        return true;
    }

    /// <summary>命令前缀 = 首个「反引号包裹 ∧ 含 &lt;…&gt; 占位符」片段去掉占位符后的字面量（补一个分隔空格）。</summary>
    private static string? FindCommandPrefix(IReadOnlyList<string> lines)
    {
        foreach (var line in lines)
        {
            for (var i = 0; i < line.Length; i++)
            {
                if (line[i] != '`')
                {
                    continue;
                }
                var close = line.IndexOf('`', i + 1);
                if (close < 0)
                {
                    break;
                }
                var span = line.Substring(i + 1, close - i - 1);
                var lt = span.IndexOf('<');
                var gt = span.IndexOf('>');
                if (lt > 0 && gt > lt + 1)
                {
                    var head = span.Substring(0, lt).TrimEnd();
                    if (head.Length > 0)
                    {
                        return head + " ";
                    }
                }
                i = close;
            }
        }
        return null;
    }

    private static bool IsSectionHead(string line) =>
        line.StartsWith("### ", StringComparison.Ordinal);

    /// <summary>分组 id = 标题行里第一个反引号词元（无则取「### 」后首个非空词元）。</summary>
    private static string SectionId(string line)
    {
        var i0 = line.IndexOf('`');
        var i1 = i0 >= 0 ? line.IndexOf('`', i0 + 1) : -1;
        if (i0 >= 0 && i1 > i0 + 1)
        {
            return line.Substring(i0 + 1, i1 - i0 - 1).Trim();
        }
        var rest = line.Substring(3).TrimStart();
        var sp = rest.IndexOf(' ');
        return sp > 0 ? rest.Substring(0, sp) : rest;
    }

    /// <summary>块终止判据：空行 / 分级标题 / 指示行（「请把…」）/ 下一个 <c>输入:</c>。</summary>
    private static bool IsBlockEnd(string line)
    {
        var t = line.Trim();
        if (t.Length == 0)
        {
            return true;
        }
        if (IsSectionHead(line))
        {
            return true;
        }
        return t.StartsWith("请把", StringComparison.Ordinal) || t == "输入:";
    }
}
