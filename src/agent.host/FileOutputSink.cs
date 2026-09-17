namespace agent.host;


/// <summary>文件输出实现 (--log 保存; 纯 markdown 原文, 无 ANSI)</summary>
public sealed class FileOutputSink : IOutputSink, IDisposable
{
    private readonly StreamWriter _writer;

    public FileOutputSink(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        _writer = new StreamWriter(File.Create(path)) { AutoFlush = true };
    }

    public void Write(string text) => _writer.WriteLine(text);

    public void WriteMarkdown(string text) => _writer.WriteLine(text); // log 存 markdown 原文

    public void Step(int no, string what, string detail = "") =>
        _writer.WriteLine($"[{no:00}] {what} {detail}".TrimEnd());

    public void Dispose() => _writer.Dispose();
}
