namespace agent.host;


/// <summary>双写输出 (终端 + 可选 log 文件)</summary>
public sealed class TeeOutputSink : IOutputSink, IDisposable
{
    private readonly IOutputSink _primary;
    private readonly FileOutputSink? _file;

    public TeeOutputSink(IOutputSink primary, FileOutputSink? file)
    {
        _primary = primary;
        _file = file;
    }

    public void Write(string text)
    {
        _primary.Write(text);
        _file?.Write(text);
    }

    public void WriteMarkdown(string text)
    {
        _primary.WriteMarkdown(text);
        _file?.WriteMarkdown(text);
    }

    public void Step(int no, string what, string detail = "")
    {
        _primary.Step(no, what, detail);
        _file?.Step(no, what, detail);
    }

    public void Dispose() => _file?.Dispose();
}
