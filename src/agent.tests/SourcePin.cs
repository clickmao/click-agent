using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace agent.tests;

/// <summary>
/// R527: 结构不变式 R526 起把「单类型单文件」放宽为「单类型 = 主文件 + 同名分片 (&lt;Type&gt;.&lt;Suffix&gt;.cs)」。
/// 于是所有**源级钉死**断言 (读某类型源码断言字符串) 必须读「该类型的全部分片」——否则分片拆完断言就假阴性
/// (R527 实测: ModelQueueRouter / ContextAssembler 拆分 ⇒ 全量 1755 中 8 条失败, 全部属这一族)。
///
/// 本类是**唯一入口**; 分片匹配口径严格: `^&lt;Stem&gt;\..+\.cs$`, 即必须多一个点 ——
/// 因此 `LlamaCppClientText.cs` 这种**另一个类型**绝不会被吸进 `LlamaCppClient` 的读取里。
/// </summary>
internal static class SourcePin
{
    /// <summary>仓库根 (含 agent.sln 的目录)。</summary>
    public static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 12 && dir is not null; i++)
        {
            if (File.Exists(Path.Combine(dir.FullName, "agent.sln"))) return dir.FullName;
            dir = dir.Parent;
        }
        return ".";
    }

    /// <summary>某类型源码全量 = 主文件 + 同名分片 (按文件名序拼接)。</summary>
    public static string Text(string relativePath)
    {
        var main = Path.Combine(RepoRoot(), relativePath.Replace('/', Path.DirectorySeparatorChar));
        var dir = Path.GetDirectoryName(main);
        if (dir is null || !Directory.Exists(dir) || !File.Exists(main)) return File.ReadAllText(main!);

        var stem = Path.GetFileNameWithoutExtension(main);
        var rx = new Regex("^" + Regex.Escape(stem) + @"\..+\.cs$");
        var files = Directory.EnumerateFiles(dir, "*.cs")
            .Where(f => Path.GetFileName(f) == stem + ".cs" || rx.IsMatch(Path.GetFileName(f)))
            .OrderBy(f => Path.GetFileName(f), StringComparer.Ordinal)
            .ToArray();
        if (files.Length == 0) files = new[] { main };
        return string.Join("\n", files.Select(File.ReadAllText));
    }

    /// <summary>路径分段形式。</summary>
    public static string TextParts(params string[] parts) => Text(Path.Combine(parts).Replace(Path.DirectorySeparatorChar, '/'));
}
