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
