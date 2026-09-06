namespace agent.modelqueue;

/// <summary>
/// 本地推理协议 (v7.15 ①本地模型真接入混合调度): modelqueue 自持的最小调用协议 —
/// 与 ILLMCaller (agent 主程序集) 解耦, 由 agent 侧 LocalInferenceAdapter 桥接到
/// LocalLlamaCaller (llama.cpp/gguf)。Router 在本地通道 (优先级最高) 并发余量内直接实跑。
/// </summary>
public interface ILocalInference
{
    /// <summary>本地模型是否就绪 (模型文件存在且可加载)</summary>
    bool IsAvailable { get; }

    /// <summary>模型显示名 (审计/LastSelectionBasis)</summary>
    string ModelName { get; }

    /// <summary>执行一次本地推理 (QueuePrompt 已含 system/context/history/user 全量语义)</summary>
    Task<QueueResponse> CallAsync(QueuePrompt prompt, CancellationToken ct = default);
}
