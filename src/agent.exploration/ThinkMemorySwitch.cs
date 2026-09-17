namespace agent.exploration;


/// <summary>
/// R449: think-memory 总开关 — 最低面实现 (宿主零改动, 默认档零产品变更)。
/// 环境变量 <c>AGENTFRAMEWORK_THINK_MEMORY</c>:
///   未设 / "1" / "on" / "true" ⇒ On (现网行为, 默认)
///   "off"        ⇒ 全关: 不加载 / 不写入 / 不召回 / 不落盘 (库文件 mtime 不变)
///   "recall0"    ⇒ 禁召回 (仍写入): 用于 A/B 消融「召回是否有用」
///   "write0"     ⇒ 禁写入 (仍召回): 用于 A/B 消融「写入是否有用」
/// 取值在进程启动时读一次 (AOT 安全, 无反射); 测试可经 Mode 参数注入。
/// </summary>
public static class ThinkMemorySwitch
{
    public enum Mode { On = 0, Off = 1, RecallOff = 2, WriteOff = 3 }

    /// <summary>进程级档位 (env 读一次)。</summary>
    public static readonly Mode Current = Parse(Environment.GetEnvironmentVariable("AGENTFRAMEWORK_THINK_MEMORY"));

    /// <summary>未知取值 ⇒ On (fail-open: 开关本身不得成为主链故障点)。</summary>
    public static Mode Parse(string? raw) => (raw ?? string.Empty).Trim().ToLowerInvariant() switch
    {
        "off" or "0" or "false" or "disable" or "disabled" => Mode.Off,
        "recall0" or "recall-off" or "no-recall" => Mode.RecallOff,
        "write0" or "write-off" or "no-write" => Mode.WriteOff,
        _ => Mode.On,
    };

    public static string Name(Mode m) => m switch
    {
        Mode.Off => "off", Mode.RecallOff => "recall0", Mode.WriteOff => "write0", _ => "on",
    };
}
