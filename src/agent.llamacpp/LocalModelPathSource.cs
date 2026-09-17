namespace agent.llamacpp;


/// <summary>
/// R464: 本地通道权重路径的**来源判定** —— 三态分离（配置未声明 / 配置可用 / 配置错配）。
///
/// 立规背景（R463 现场）: 原接线 `lc.IsReady ? lc.ModelPath : baseOpts.ModelPath` 把三态压成两态，
/// 于是「配置指向不存在的文件」时产品**静默改用宿主默认权重**，既不告警也不留痕 ⇒ 任何以权重档位为
/// 单变量的测量在该配置下读数是错的且看不出来（R463 负控 BP 因此 VOID）。
/// 本类的唯一纪律: <b>Declared == true 时绝不把 fallback 写进 ModelPath</b>；错配 ⇒ 通道不可用
/// （门走既有 fail-open Pass，远端兜底），但配置意图不被改写，且告警必落。
/// </summary>
public enum LocalModelPathSource
{
    /// <summary>配置未声明 local 段 ⇒ 合法使用宿主默认（env / 内置权重）。</summary>
    Unconfigured = 0,

    /// <summary>配置声明的路径存在 ⇒ 按配置使用。</summary>
    Configured = 1,

    /// <summary>配置声明的路径缺失/为空 ⇒ **按配置意图置为不可用**，不替换、不静默兜底。</summary>
    ConfiguredMissing = 2,
}
