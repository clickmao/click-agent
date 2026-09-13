using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace agent.roles;

/// <summary>
/// 教训通用化机检 (exp5 §4-7 / A8, R369 用户钦定铁律)。
///
/// 语义: 教训必须是**语言无关的通用工程经验** —— `Id`/`Pattern`/`Kind` 中不得出现
///       语言名、文件扩展名、专有工具/API 名; 语言与工具只能出现在 `Instances[]`。
/// 判据: 黑名单词表 + 词法边界检查 (纯字母短词要求两侧非字母数字边界, 避免误杀)。
/// 命中即视为**未抽象** → 调用方拒绝入库 (LessonTable.Submit)。
/// </summary>
public static class LessonGeneralization
{
    /// <summary>
    /// 黑名单 (全部小写, 匹配 OrdinalIgnoreCase)。
    /// 刻意**不含** `go` / `c`: 纯字母超短词误杀率过高 (如 algorithm 含 "go"), 宁可漏检不可误杀。
    /// </summary>
    public static readonly IReadOnlyList<string> Blacklist = new[]
    {
        // 语言名
        "python", "rust", "java", "javascript", "typescript", "csharp", "cpp", "kotlin", "swift",
        "scala", "ruby", "php", "perl", "lua", "haskell", "elixir", "erlang", "ocaml", "julia",
        "dart", "fortran", "cobol", "golang", "bash", "powershell", "sql", "c#", "c++",
        // 文件扩展名
        ".py", ".cs", ".cpp", ".cc", ".cxx", ".hpp", ".java", ".js", ".ts", ".tsx", ".jsx",
        ".rs", ".rb", ".php", ".sh", ".ps1", ".bat", ".lua", ".pl", ".kt", ".swift", ".scala",
        // 工具 / 专有 API
        "py_compile", "dotnet", "msbuild", "clang", "gcc", "g++", "llvm", "csc", "msvc",
        "cmake", "ninja", "gradle", "maven", "npm", "deno", "pip", "conda", "venv",
        "pytest", "unittest", "jest", "junit", "nunit", "xunit", "numpy", "pandas",
        "torch", "pytorch", "tensorflow", "onnx", "gguf", "stringbuilder",
        "gethashcode", "system.text.json", "fts5", "sqlite", "redis", "postgres", "mysql",
        "docker", "kubernetes", "puppeteersharp", "llamasharp", "tensorprimitives",
    };

    /// <summary>返回命中的黑名单词 (空列表 = 通过通用化机检)。</summary>
    public static IReadOnlyList<string> Screen(string? text)
    {
        var hits = new List<string>();
        if (string.IsNullOrEmpty(text)) return hits;

        foreach (var token in Blacklist)
        {
            if (ContainsToken(text, token)) hits.Add(token);
        }
        return hits;
    }

    public static bool IsGeneralized(string? text) => Screen(text).Count == 0;

    /// <summary>给拒绝理由用的可读摘要 (最多 5 个命中词, 保留原文以便修正)。</summary>
    public static string? Violation(string? text)
    {
        var hits = Screen(text);
        if (hits.Count == 0) return null;
        var shown = hits.Count <= 5
            ? string.Join(", ", hits)
            : string.Join(", ", hits.Take(5)) + $", …(+{hits.Count - 5})";
        return $"教训未通用化: Pattern 含语言/工具专名 [{shown}] —— 语言与工具只能出现在 Instances[]";
    }

    /// <summary>
    /// 词法命中判定:
    ///   - 以 '.' 开头的词 (扩展名): 直接子串匹配 (如 "a.py" 命中 ".py"; "py_compile" 不命中 ".py")。
    ///   - 含非字母数字字符的词 (如 "c#", "c++"): 直接子串匹配。
    ///   - 纯字母数字词: 要求两侧均为非字母数字边界 (避免 "go"/"java" 命中 "javaxxx" 之类误杀)。
    /// </summary>
    private static bool ContainsToken(string text, string token)
    {
        var strict = true;
        foreach (var c in token)
        {
            if (!char.IsLetterOrDigit(c)) { strict = false; break; }
        }

        var idx = text.IndexOf(token, StringComparison.OrdinalIgnoreCase);
        while (idx >= 0)
        {
            if (!strict) return true;

            var beforeOk = idx == 0 || !IsWordChar(text[idx - 1]);
            var end = idx + token.Length;
            var afterOk = end >= text.Length || !IsWordChar(text[end]);
            if (beforeOk && afterOk) return true;

            idx = text.IndexOf(token, idx + 1, StringComparison.OrdinalIgnoreCase);
        }
        return false;
    }

    private static bool IsWordChar(char c) => char.IsLetterOrDigit(c) || c == '_';

    /// <summary>归一化: 去首尾空白 + 内部连续空白压成一个空格 (指纹输入稳定化)。</summary>
    public static string Normalize(string? text)
    {
        if (string.IsNullOrWhiteSpace(text)) return string.Empty;
        var sb = new StringBuilder(text.Length);
        var pendingSpace = false;
        foreach (var c in text.Trim())
        {
            if (char.IsWhiteSpace(c)) { pendingSpace = true; continue; }
            if (pendingSpace && sb.Length > 0) sb.Append(' ');
            pendingSpace = false;
            sb.Append(c);
        }
        return sb.ToString();
    }
}
