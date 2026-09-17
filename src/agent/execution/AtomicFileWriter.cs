using System;
using System.IO;
using System.Text;
using System.Threading;

namespace agent.execution;


/// <summary>原子写: tmp 同目录写 + Flush(true) + Move(overwrite) — 读者永不见半写文件 (同卷 rename 原子)。</summary>
public static class AtomicFileWriter
{
    public static void WriteAllText(string path, string content)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(path))!;
        Directory.CreateDirectory(dir);
        var tmp = Path.Combine(dir,
            $".{Path.GetFileName(path)}.tmp-{Environment.ProcessId}-{Guid.NewGuid():N}");
        try
        {
            using (var fs = new FileStream(tmp, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096,
                       FileOptions.WriteThrough))
            {
                var buf = Encoding.UTF8.GetBytes(content);
                fs.Write(buf, 0, buf.Length);
                fs.Flush(true);
            }
            File.Move(tmp, path, overwrite: true);
        }
        finally
        {
            try { if (File.Exists(tmp)) File.Delete(tmp); } catch { /* 已 move 或清理竞争 */ }
        }
    }
}
