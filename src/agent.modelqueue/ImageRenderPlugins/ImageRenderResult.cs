using System.Text;

namespace agent.modelqueue;


public sealed class ImageRenderResult
{
    public bool Ok { get; set; }
    public string? Path { get; set; }
    public long FileBytes { get; set; }
    public string? Error { get; set; }
    public int WallMs { get; set; }
}
