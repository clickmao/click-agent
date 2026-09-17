using Microsoft.Extensions.Logging;

namespace agent.codegen;


/// <summary>
/// 代码变更
/// </summary>
public class CodeChange
{
    public string FilePath { get; set; } = string.Empty;
    public ChangeType Type { get; set; }
    public string? OldContent { get; set; }
    public string? NewContent { get; set; }
    public int OldLineStart { get; set; }
    public int OldLineEnd { get; set; }
    public int NewLineStart { get; set; }
    public int NewLineEnd { get; set; }
    public string? Description { get; set; }
}
