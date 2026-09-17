using agent.config;

namespace agent.modelqueue;


/// <summary>余额查询方案 (C.6.4 — provider 差异大, scheme 枚举分派)</summary>
/// <summary>本地推理通道配置 (models.yaml local 段 — gguf 路径/上下文/GPU 层数)</summary>
public sealed class LocalChannelConfig
{
    /// <summary>gguf 对话模型路径 (空/文件缺失 → 本地通道不可用)</summary>
    public string ModelPath { get; set; } = string.Empty;

    /// <summary>上下文窗口大小</summary>
    public int ContextSize { get; set; } = 4096;

    /// <summary>vulkan offload 层数 (0 = 纯 CPU)</summary>
    public int GpuLayers { get; set; }

    /// <summary>R413: 本地单轮生成上限 token (0 = 用端口默认)</summary>
    public int MaxTokens { get; set; } = 256;

    /// <summary>
    /// R430: 本地服务端总槽位 (config `local.parallel`)。默认 1 = 真串行。
    /// 该构建 llama.cpp 的 `-np` 默认 = 4 ⇒ 并发在途请求进同一批 ⇒ 判定不可复现;
    /// 显式 1 才保证决策路径逐位可复现 (R430 传输级坐实)。
    /// </summary>
    public int Parallel { get; set; } = 1;

    /// <summary>R413: 本地通道可承接的 prompt 预估 token 上限 (超限 → 走远端)</summary>
    public int MaxPromptTokens { get; set; } = 2048;

    /// <summary>R413: 允许本地化的任务种类名 (空 = 用 LocalChannelPolicy.DefaultAllowedKinds)</summary>
    public List<string> AllowedKinds { get; set; } = new();

    /// <summary>R413: 是否允许主回答 (General) 也走本地 (默认 false — 质量风险)</summary>
    public bool AllowGeneral { get; set; }

    /// <summary>R413 前置门: 允许链在「本轮无新增诉求」时跳过远端主调用 (默认 false = 零回归)。</summary>
    public bool TurnGate { get; set; }

    /// <summary>
    /// R426: 关系判官 (CorrectionDetector L2 微判定) 本地优先 (默认 false = 零回归)。
    /// 开 = 该次微判定先问 r1; 本地不可用/未判定 ⇒ **远端兜底**(绝不静默给结论)。
    /// </summary>
    public bool RelationJudge { get; set; }

    /// <summary>配置路径非空且文件存在 = 通道就绪</summary>
    public bool IsReady => !string.IsNullOrEmpty(ModelPath) && File.Exists(ModelPath);

    /// <summary>
    /// R464: 配置里是否**声明**了 `local:` 段。声明即「配置意图」——与「路径此刻是否可用」分离;
    /// 二者混用会导致「配置错配」被当成「未配置」而静默回退默认权重（R463 负控 VOID 的根因）。
    /// </summary>
    public bool Declared { get; set; }
}
