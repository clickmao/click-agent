using agent.core;
using agent.context;

namespace agent.templates;


/// <summary>
/// Prompt 消息
/// </summary>
public class PromptMessage
{
    public MessageRole Role { get; set; }
    public string Content { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; }
}
