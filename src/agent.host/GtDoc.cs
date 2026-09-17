using agent.contextgradient;
using System.Text;
using System.Text.Json;
using agent.llamalocal;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using agent.core;
using agent.intent;
using agent.registry;
using agent.session;

namespace agent.host;


/// <summary>压缩 audit ground-truth 样本 (v0.13.3 A2)</summary>
/// <summary>压缩 audit ground-truth 样本 (v0.13.3 A2)</summary>
public sealed class GtDoc
{
    [System.Text.Json.Serialization.JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;
    [System.Text.Json.Serialization.JsonPropertyName("target_tokens")]
    public int TargetTokens { get; set; }
    [System.Text.Json.Serialization.JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
    [System.Text.Json.Serialization.JsonPropertyName("ground_truth")]
    public Dictionary<string, string> GroundTruth { get; set; } = new();
    [System.Text.Json.Serialization.JsonPropertyName("causal_sentence")]
    public string CausalSentence { get; set; } = string.Empty;
    [System.Text.Json.Serialization.JsonPropertyName("instruction_sentence")]
    public string InstructionSentence { get; set; } = string.Empty;
}
