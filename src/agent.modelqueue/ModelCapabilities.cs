using agent.config;

namespace agent.modelqueue;


/// <summary>v0.12.0 模态能力矩阵 (yaml capabilities: 字段, 缺省全 false/text=true 保守值)</summary>
public sealed class ModelCapabilities
{
    public bool Text { get; set; } = true;
    public bool ImageInput { get; set; }
    public bool VideoInput { get; set; }
    public bool AudioInput { get; set; }
    public bool FilePdf { get; set; }
    public bool FileXlsx { get; set; }
    public bool ImageOutput { get; set; }
}
