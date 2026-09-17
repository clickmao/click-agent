namespace agent.userinteraction;


/// <summary>R375 (exp2 P0-3): 选项条目 —— 值与显示分离 (前端渲染 label, 回填 value)。</summary>
public class CredentialChoice
{
    /// <summary>回填值 (校验用; 必须命中 DataType=choice 的合法集)</summary>
    public string Value { get; set; } = string.Empty;

    /// <summary>给用户看的文本 (默认同 Value)</summary>
    public string Label { get; set; } = string.Empty;

    /// <summary>是否推荐项 (菜单高亮/预选)</summary>
    public bool Recommended { get; set; }
}
