using System.Text.Json.Serialization;

namespace agent;


/// <summary>/model list 单条模型条目 (序号 = models.yaml 目录顺序)</summary>
public sealed class ModelListItem
{
    /// <summary>序号 (1-N, /model &lt;序号&gt; 即指定该模型)</summary>
    public int Index { get; set; }
    public string Id { get; set; } = string.Empty;

    /// <summary>人读描述 (v0.11.0: 一句话能力/定位)</summary>
    public string Description { get; set; } = string.Empty;

    public string Provider { get; set; } = string.Empty;
    public double PriceInPerM { get; set; }
    public double PriceOutPerM { get; set; }
    public int ReasoningScore { get; set; }
    public int CodingScore { get; set; }
    public int ContextWindow { get; set; }
    public bool IsActive { get; set; }
}
