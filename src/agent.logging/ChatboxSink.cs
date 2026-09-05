using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;

/// <summary>
/// chatbox 推送传输通道 (L.6 定案 v7.15): FrontendDirective 的出口抽象。
/// CLI 宿主 → ConsoleChatboxSink (单行 JSON 协议行到 stdout, AgentReportReaderBase 按行解析);
/// 未来 websocket/面板宿主 → 各自实现本接口注入 LogRouter, agent 层零改动。
/// 实现要求: 线程安全 + 不抛异常 (推送失败只影响前端显示, 不得打断主链)。
/// </summary>
public interface IChatboxSink
{
    /// <summary>推送一条前端指令 (thinking_page_switch / 分片 / thinking_end / output_append)</summary>
    void Push(FrontendDirective directive);
}

/// <summary>
/// 控制台推送实现 (CLI 宿主默认): 单行 JSON 协议行 `@chatbox:{json}` 到 stdout。
/// `@chatbox:` 前缀与普通日志行/流式内容互斥 — AgentReportReaderBase.ReadChatboxEvent 专行识别。
/// JsonSerializerOptions: source-gen (ChatboxJsonContext), PascalCase — 全库前端协议契约一致。
/// </summary>
public sealed class ConsoleChatboxSink : IChatboxSink
{
    private readonly TextWriter _writer;

    public ConsoleChatboxSink(TextWriter? writer = null) => _writer = writer ?? Console.Out;

    public void Push(FrontendDirective directive)
    {
        try
        {
            var json = JsonSerializer.Serialize(directive, ChatboxJsonContext.Default.FrontendDirective);
            _writer.WriteLine("@chatbox:" + json);
        }
        catch
        {
            // 推送失败不打断主链 (接口契约)
        }
    }
}

[JsonSourceGenerationOptions(DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull)]
[JsonSerializable(typeof(FrontendDirective))]
public partial class ChatboxJsonContext : JsonSerializerContext
{
}
