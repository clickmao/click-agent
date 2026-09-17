namespace agent.host;


/// <summary>
/// 输出接口 (可扩展): CLI 终端之外, 其他前端 (IPC/文件/WebSocket) 实现此接口即可复用整个 CLI 会话逻辑。
/// </summary>
public interface IOutputSink
{
    void Write(string text);
    void WriteMarkdown(string text);
    void Step(int no, string what, string detail = "");
}
