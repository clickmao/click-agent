using System.Text;

namespace agent.context;

/// <summary>
/// R462 工作区文本探针 —— 语言无关的「可作代码逻辑文本处理」判定 (承 R447 语言无关令)。
///
/// 背景 (真缺陷): <see cref="ContextAssembler"/> 的工作区召回曾用**硬编码后缀白名单**
///   (源码里逐字列出若干语言后缀) 过滤候选文件 ⇒ 复用流程时噪声大、换语言即失效。
///   本类把该判定改为**结构与内容判定**, 后缀集只作为**可配数据** (默认空 = 全允许)。
///
/// 判据:
///   ① 空文件 ⇒ 不可用 (免开流的既有约定);
///   ② 头部含 0x00 ⇒ 二进制, 不可用;
///   ③ 头部不可打印字节占比 &gt; 10% ⇒ 二进制, 不可用;
///   ④ 后缀白名单仅在**显式配置**时生效 (env <see cref="AllowlistEnv"/>, 逗号分隔, 大小写不敏感);
///      未配置 ⇒ 一律允许 ⇒ 判定不依赖任何语言清单。
/// 纪律: 有界读 (头部 ≤ <see cref="HeadBytes"/> 字节), 零反射, 零异常外泄 (异常 ⇒ 不可用)。
/// </summary>
public static class WorkspaceTextProbe
{
    /// <summary>后缀白名单环境变量 (逗号分隔, 例: ".md,.txt"; 未设/空 ⇒ 全允许)。</summary>
    public const string AllowlistEnv = "AGENTFRAMEWORK_TEXT_SUFFIX_ALLOWLIST";

    /// <summary>头部探测字节数 (有界)。</summary>
    public const int HeadBytes = 512;

    /// <summary>不可打印字节占比上限 (超过视为二进制)。</summary>
    public const double MaxNonPrintableRatio = 0.10;

    /// <summary>候选文件是否可作文本/代码逻辑处理。</summary>
    public static bool IsUsableTextFile(string path)
    {
        if (string.IsNullOrWhiteSpace(path)) return false;
        if (!SuffixAllowed(path)) return false;
        try
        {
            var info = new FileInfo(path);
            if (!info.Exists || info.Length <= 0) return false; // 空文件跳过 (既有约定)

            var buf = new byte[HeadBytes];
            using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            var n = fs.Read(buf, 0, buf.Length);
            if (n <= 0) return false;
            var nonPrintable = 0;
            for (var i = 0; i < n; i++)
            {
                var b = buf[i];
                if (b == 0) return false; // NUL ⇒ 二进制
                var printable = b == 9 || b == 10 || b == 13 || (b >= 32 && b != 127);
                if (!printable) nonPrintable++;
            }
            return (double)nonPrintable / n <= MaxNonPrintableRatio;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>后缀是否被显式白名单允许 (未配置 ⇒ 全允许)。</summary>
    public static bool SuffixAllowed(string path)
    {
        var allow = Environment.GetEnvironmentVariable(AllowlistEnv);
        if (string.IsNullOrWhiteSpace(allow)) return true;

        var name = Path.GetFileName(path);
        var dot = name.LastIndexOf('.');
        if (dot <= 0 || dot == name.Length - 1) return false;
        var suffix = name[dot..];
        foreach (var part in allow.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            if (suffix.Equals(part, StringComparison.OrdinalIgnoreCase)) return true;
        }
        return false;
    }

    /// <summary>
    /// 结构判定 token 是否为「文件后缀样」—— 供机检/通用逻辑使用, **不依赖后缀清单**。
    /// 形如 <c>.abc</c> / <c>.abc-def</c>, 长度 ≤ 16, 全为字母数字或连字符, 且非纯数字。
    /// </summary>
    public static bool LooksLikeFileSuffix(string? token)
    {
        if (string.IsNullOrEmpty(token)) return false;
        if (token[0] != '.' || token.Length < 2 || token.Length > 16) return false;
        var digits = 0;
        for (var i = 1; i < token.Length; i++)
        {
            var ch = token[i];
            if (char.IsDigit(ch)) { digits++; continue; }
            if (char.IsLetter(ch) || ch == '-' || ch == '_') continue;
            return false;
        }
        return digits != token.Length - 1;
    }
}
