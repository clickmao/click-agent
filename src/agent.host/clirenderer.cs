namespace agent.host;

/// <summary>
/// CLI 输出渲染器 (v7.12): markdown 重点标记 + ANSI 颜色。
/// 用户可读性优先: 标题/加粗/代码块/列表都有视觉层次; 非 TTY 环境自动降级纯文本。
/// </summary>
public static class CliRenderer
{
    private static readonly bool Color = !Console.IsOutputRedirected;

    private static string Paint(string text, string code) => Color ? $"\x1b[{code}m{text}\x1b[0m" : text;

    public static string Bold(string s) => Paint(s, "1");
    public static string Dim(string s) => Paint(s, "2");
    public static string Green(string s) => Paint(s, "32");
    public static string Yellow(string s) => Paint(s, "33");
    public static string Red(string s) => Paint(s, "31");
    public static string Cyan(string s) => Paint(s, "36");

    /// <summary>标题条 (一级重点)</summary>
    public static void Banner(string title)
    {
        Console.WriteLine();
        Console.WriteLine(Bold($"╭─ {title} " + new string('─', Math.Max(4, 60 - title.Length))));
    }

    /// <summary>
    /// markdown 渲染到终端:
    /// ## 标题 → 反色行; **粗体** → ANSI 粗体; ```代码块 → 缩进+边框; - 列表 → 符号对齐。
    /// </summary>
    public static void WriteMarkdown(string text)
    {
        if (string.IsNullOrEmpty(text))
            return;

        var inCode = false;
        var codeLang = string.Empty;
        var codeBuf = new List<string>();

        foreach (var raw in text.Split('\n'))
        {
            var line = raw.TrimEnd('\r');

            if (line.TrimStart().StartsWith("```"))
            {
                if (!inCode)
                {
                    inCode = true;
                    codeLang = line.TrimStart()[3..].Trim();
                    codeBuf.Clear();
                }
                else
                {
                    inCode = false;
                    Console.WriteLine(Dim($"┌─{(codeLang.Length > 0 ? $" {codeLang} " : "")}" + new string('─', 46)));
                    foreach (var cl in codeBuf)
                        Console.WriteLine($"│ {cl}");
                    Console.WriteLine(Dim("└" + new string('─', 49)));
                }
                continue;
            }

            if (inCode)
            {
                codeBuf.Add(line);
                continue;
            }

            var trimmed = line.TrimStart();
            if (trimmed.StartsWith("## "))
                Console.WriteLine(Bold($"◆ {trimmed[3..]}"));
            else if (trimmed.StartsWith("# "))
                Console.WriteLine(Bold($"▣ {trimmed[2..]}"));
            else if (trimmed.StartsWith("### "))
                Console.WriteLine(Bold($"· {trimmed[4..]}"));
            else if (trimmed.StartsWith("- ") || trimmed.StartsWith("* "))
                Console.WriteLine($"  {Cyan("•")} {Inline(trimmed[2..])}");
            else if (trimmed.Length > 2 && trimmed[1] == '.' && char.IsDigit(trimmed[0]))
                Console.WriteLine($"  {Yellow(trimmed[..2])} {Inline(trimmed[2..].Trim())}");
            else
                Console.WriteLine(Inline(line));
        }

        if (inCode && codeBuf.Count > 0) // 未闭合代码块容错
        {
            foreach (var cl in codeBuf)
                Console.WriteLine($"│ {cl}");
        }
    }

    /// <summary>行内标记: **bold** → ANSI</summary>
    private static string Inline(string line)
    {
        if (!Color)
            return line.Replace("**", "");

        var parts = line.Split("**");
        for (var i = 1; i < parts.Length; i += 2)
            parts[i] = $"\x1b[1m{parts[i]}\x1b[0m";
        return string.Concat(parts);
    }

    /// <summary>步骤明细行 (任务执行过程可查询的终端呈现)</summary>
    public static void Step(int no, string what, string detail = "")
    {
        var line = $"  {Dim($"[{no:00}]")} {Bold(what)}";
        if (detail.Length > 0)
            line += $" {Dim(detail)}";
        Console.WriteLine(line);
    }
}

/// <summary>
/// 输出接口 (可扩展): CLI 终端之外, 其他前端 (IPC/文件/WebSocket) 实现此接口即可复用整个 CLI 会话逻辑。
/// </summary>
public interface IOutputSink
{
    void Write(string text);
    void WriteMarkdown(string text);
    void Step(int no, string what, string detail = "");
}

/// <summary>终端输出实现 (默认)</summary>
public sealed class ConsoleOutputSink : IOutputSink
{
    public void Write(string text) => Console.WriteLine(text);
    public void WriteMarkdown(string text) => CliRenderer.WriteMarkdown(text);
    public void Step(int no, string what, string detail = "") => CliRenderer.Step(no, what, detail);
}

/// <summary>文件输出实现 (--log 保存; 纯 markdown 原文, 无 ANSI)</summary>
public sealed class FileOutputSink : IOutputSink, IDisposable
{
    private readonly StreamWriter _writer;

    public FileOutputSink(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        _writer = new StreamWriter(File.Create(path)) { AutoFlush = true };
    }

    public void Write(string text) => _writer.WriteLine(text);

    public void WriteMarkdown(string text) => _writer.WriteLine(text); // log 存 markdown 原文

    public void Step(int no, string what, string detail = "") =>
        _writer.WriteLine($"[{no:00}] {what} {detail}".TrimEnd());

    public void Dispose() => _writer.Dispose();
}

/// <summary>双写输出 (终端 + 可选 log 文件)</summary>
public sealed class TeeOutputSink : IOutputSink, IDisposable
{
    private readonly IOutputSink _primary;
    private readonly FileOutputSink? _file;

    public TeeOutputSink(IOutputSink primary, FileOutputSink? file)
    {
        _primary = primary;
        _file = file;
    }

    public void Write(string text)
    {
        _primary.Write(text);
        _file?.Write(text);
    }

    public void WriteMarkdown(string text)
    {
        _primary.WriteMarkdown(text);
        _file?.WriteMarkdown(text);
    }

    public void Step(int no, string what, string detail = "")
    {
        _primary.Step(no, what, detail);
        _file?.Step(no, what, detail);
    }

    public void Dispose() => _file?.Dispose();
}
