using System;
using System.IO;
using System.Text;

namespace agent.r1;

/// <summary>
/// R1 管道 · role 额外数据挂载（用户令：判别时须挂 role 的额外数据）。
///
/// 铁律（与 R1-① 前缀恒定不冲突）：role 数据是**随调用变化**的，因此只允许进
/// user 轮尾块（<role_profile>），**禁止**进常量前缀；否则前缀 sha 漂移、缓存命中归零。
/// </summary>
public static class R1RoleMount
{
    public const int MaxChars = 1200;

    public static string? ReadNote(int maxChars = MaxChars)
    {
        var path = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R1_ROLE_FILE");
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
        {
            return null;
        }
        var text = File.ReadAllText(path, Encoding.UTF8).Trim();
        if (text.Length == 0)
        {
            return null;
        }
        return text.Length <= maxChars ? text : text[..maxChars];
    }

    /// <summary>user 轮尾块拼装（无 role ⇒ 原样返回，且不为空串）。</summary>
    public static string AppendTo(string userMessage, string? roleNote)
    {
        if (string.IsNullOrWhiteSpace(roleNote))
        {
            return userMessage;
        }
        return userMessage + "\n\n<role_profile>\n" + roleNote + "\n</role_profile>";
    }
}
