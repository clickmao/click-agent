namespace agent.llamacpp;


/// <summary>
/// 本地 prompt 的来源凭证。闸门只承认 <see cref="GgufJinja"/>：模板取自 GGUF 元数据、由服务端内嵌 jinja 渲染，
/// 调用方物理上无法绕过模板。 <see cref="Literal"/> 仅由诊断入口产生，一律被闸门拒收（负控锚点）。
/// </summary>
public enum LocalPromptProvenance
{
    /// <summary>模板来自模型元数据（服务端 /apply-template）。</summary>
    GgufJinja = 0,

    /// <summary>调用方手拼字面 prompt（诊断/对账专用；生产路径必须被闸门拒收）。</summary>
    Literal = 1,
}
