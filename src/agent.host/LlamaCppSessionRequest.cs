using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using agent.llamacpp;
using agent.modelqueue;

namespace agent.host;


/// <summary>R411 多轮会话请求（长驻进程内逐轮生成；K2b 观测用）。</summary>
public sealed class LlamaCppSessionRequest
{
    public string? SessionId { get; set; }
    /// <summary>稳定长前缀（system 文本）文件；与 <see cref="SystemText"/> 二者其一。</summary>
    public string? SystemFile { get; set; }
    public string? SystemText { get; set; }
    public List<string> Turns { get; set; } = [];
    public int? MaxTokens { get; set; }
}
