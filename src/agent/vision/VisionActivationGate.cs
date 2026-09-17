namespace agent.vision;

/// <summary>
/// 本地视觉模型的**按需加载闸**（内存硬约束: 本机可用 ≈2.7GB, VLM 常驻 ≈2.0GB ⇒ 禁常驻、禁并发）。
/// 判定依据只有两件事: ① 远端给出的 <see cref="ScreenTaskSignal"/>（真假判定不在本地）
/// ② 本地模型文件是否在位 + 当前是否已有其它本地推理进程占用。
/// 任何一项不满足 ⇒ 不加载（fail-closed，管道照常推进，只是没有视觉能力）。
/// </summary>
public static class VisionActivationGate
{
    /// <summary>允许起视觉服务（当前无视觉进程）。</summary>
    public const string CodeLoad = "LOAD";

    /// <summary>视觉服务已在跑 ⇒ 复用，不重复起。</summary>
    public const string CodeReuse = "REUSE";

    /// <summary>远端未判定为屏幕任务 ⇒ 不加载。</summary>
    public const string CodeSkipNoSignal = "SKIP_NO_SIGNAL";

    /// <summary>kind=none/非屏幕类 ⇒ 不加载。</summary>
    public const string CodeSkipNotScreenKind = "SKIP_NOT_SCREEN_KIND";

    /// <summary>模型/投影器文件不在位 ⇒ 不加载。</summary>
    public const string CodeSkipModelMissing = "SKIP_MODEL_MISSING";

    /// <summary>已有其它本地推理进程（生成/嵌入）⇒ 不加载（内存硬约束，必须串行）。</summary>
    public const string CodeSkipBusy = "SKIP_BUSY";

    /// <summary>判定结果: 是否加载 + 机器可读原因码。</summary>
    public sealed record Decision(bool Load, string ReasonCode);

    public static Decision Decide(ScreenTaskSignal? signal, bool modelPresent, bool visionRunning, bool otherLocalProcessRunning)
    {
        if (signal is null || !signal.Needed)
        {
            return new Decision(false, CodeSkipNoSignal);
        }
        if (signal.Kind == "none" || System.Array.IndexOf(ScreenTaskSignal.Kinds, signal.Kind) < 0)
        {
            return new Decision(false, CodeSkipNotScreenKind);
        }
        if (!modelPresent)
        {
            return new Decision(false, CodeSkipModelMissing);
        }
        if (visionRunning)
        {
            return new Decision(true, CodeReuse);
        }
        if (otherLocalProcessRunning)
        {
            return new Decision(false, CodeSkipBusy);
        }
        return new Decision(true, CodeLoad);
    }
}
