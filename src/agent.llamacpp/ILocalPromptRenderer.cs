namespace agent.llamacpp;


/// <summary>
/// 本地 prompt 渲染端口。实现可替换（当前 = llama-server 内嵌 jinja；未来可换其它渲染器），
/// 但闸门只认 GgufJinja 凭证：换实现必须能证明模板来自模型元数据。
/// </summary>
public interface ILocalPromptRenderer
{
    ValueTask<RenderedPrompt> RenderAsync(IReadOnlyList<ChatTurn> turns, CancellationToken ct = default);
}
