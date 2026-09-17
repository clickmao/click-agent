namespace agent.llamacpp;


/// <summary>R464: 解析输入（**纯数据** —— 文件存在性由调用方探测，便于单测与确定性）。</summary>
public readonly record struct LocalChannelWiringInput(
    bool Declared,
    string? ConfiguredPath,
    string FallbackPath,
    bool ConfiguredFileExists,
    bool FallbackFileExists);
