namespace agent.llamacpp;


/// <summary>渲染产物。字段只放真实测得的东西：文本与来源凭证（token 数由 /completion 的 tokens_evaluated 提供）。</summary>
public sealed record RenderedPrompt(string Text, LocalPromptProvenance Provenance);
