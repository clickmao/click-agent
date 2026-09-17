using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.logging;


/// <summary>日志通道 (thinking=思考流 / output=结果输出 / system=框架系统)</summary>
public enum LogChannel
{
    Thinking,
    Output,
    System,
}
