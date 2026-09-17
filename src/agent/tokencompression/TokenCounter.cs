using Microsoft.Extensions.Logging;
using System.Text.RegularExpressions;

namespace agent.tokencompression;


/// <summary>
/// Token 计数工具
/// </summary>
public static class TokenCounter
{
    private static bool IsPunctuation(char c)
    {
        return c == '.' || c == ',' || c == ';' || c == ':' || 
               c == '!' || c == '?' || c == '"' || c == '\'' ||
               c == '(' || c == ')' || c == '[' || c == ']' ||
               c == '{' || c == '}' || c == '-' || c == '_' ||
               c == '+' || c == '=' || c == '/' || c == '\\' ||
               c == '|' || c == '@' || c == '#' || c == '$' ||
               c == '%' || c == '^' || c == '&' || c == '*' ||
               c == '<' || c == '>' || c == '`' || c == '~';
    }
}
