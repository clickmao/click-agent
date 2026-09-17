using agent.config;

namespace agent.modelqueue;


public sealed class ModelCatalogEntry
{
    public string Id { get; set; } = string.Empty;

    /// <summary>人读描述 (v0.11.0: 一句话能力/定位 — /model list 展示)</summary>
    public string Description { get; set; } = string.Empty;

    public string Provider { get; set; } = string.Empty;

    /// <summary>chat completions 完整 URL</summary>
    public string Endpoint { get; set; } = string.Empty;

    /// <summary>API Key 的环境变量名 (永不存 key 本体)</summary>
    public string ApiKeyEnv { get; set; } = string.Empty;

    /// <summary>输入价格 USD / 每百万 token</summary>
    public double PriceInPerM { get; set; }

    /// <summary>输出价格 USD / 每百万 token</summary>
    public double PriceOutPerM { get; set; }

    /// <summary>推理能力 1-10 (C.6.1 标准值, 依据公开评测归一化)</summary>
    public int ReasoningScore { get; set; }

    /// <summary>R356 (用户钦定): 目录声明优先级 — 1=最高 (首选)。0=未声明 (按旧打分逻辑)。</summary>
    public int Priority { get; set; }

    /// <summary>编码能力 1-10</summary>
    public int CodingScore { get; set; }

    /// <summary>上下文窗口 (token)</summary>
    public int ContextWindow { get; set; }

    /// <summary>适合用途 (意图匹配: general/coding/reasoning/planning/chat/summary/classify/debug)</summary>
    public List<string> SuitedFor { get; set; } = new();

    /// <summary>
    /// v0.12.0 模态能力矩阵 (计划1 §2) — 路由层消费: 文本模型收图 → 明确报错;
    /// image_output=true → CogView 生图通道。
    /// </summary>
    public ModelCapabilities Capabilities { get; set; } = new();
}
