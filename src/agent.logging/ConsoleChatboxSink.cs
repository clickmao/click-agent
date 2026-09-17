using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;

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
