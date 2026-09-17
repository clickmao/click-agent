namespace agent.host;


/// <summary>终端输出实现 (默认)</summary>
public sealed class ConsoleOutputSink : IOutputSink
{
    public void Write(string text) => Console.WriteLine(text);
    public void WriteMarkdown(string text) => CliRenderer.WriteMarkdown(text);
    public void Step(int no, string what, string detail = "") => CliRenderer.Step(no, what, detail);
}
