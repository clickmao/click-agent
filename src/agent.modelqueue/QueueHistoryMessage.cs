using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.modelqueue;


public sealed class QueueHistoryMessage
{
    public string Role { get; set; } = "user";
    public string Content { get; set; } = string.Empty;
}
