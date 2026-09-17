using System;

namespace agent.modelqueue;

/// <summary>
/// R522 动作环上下文纪律 —— 依据 = R521 逐调用取证 (`eval/rover/r521/run-0917-154115/adapter/*.json`)。
/// 实测形状 (臂 A 单轮, 58/58 全对): 19 次调用, 名义 302,809 tok, 其中
///   ① 14 次 run_command 单命令往返 + 3 个临时探针落盘 + 3 次 delete ⇒ 20 步全用来「一条命令一轮 LLM」,
///      每轮重发 ~15k 前缀 ⇒ 名义量约 3/4 花在验证往返;
///   ② 收尾两段叙述共 16,540 字 (completion 5,071) —— 同题 codex 3,926 字 (completion 1,213)。
/// 同窗对照: codex 5 次调用 / 新算 3,757 / completion 3,063; 本侧 19 次 / 新算 18,432 / completion 14,169。
/// 命中率两侧同档 (91.3% vs 93.6%) ⇒ 差距不在缓存, 在**调用粒度与收尾冗余**。
/// 设计约束:
///   C1 只在动作环开时注入 (环关 ⇒ 请求体与旧版逐字节相同, 零回归);
///   C2 注入点在 SystemPrompt **尾部** ⇒ 环内各步前缀单调不变 (缓存命中不受影响);
///   C3 单变量可消融: env <see cref="EnvName"/>=off/0/false ⇒ 完全等价旧行为 ⇒ 可跑同窗消融臂。
/// </summary>
public static class ActionLoopDiscipline
{
    /// <summary>消融开关 (缺省开; off/0/false = 关 ⇒ 等价 R521 旧行为)。</summary>
    public const string EnvName = "AGENTFRAMEWORK_ACTION_DISCIPLINE";

    /// <summary>三条纪律文本 (锚: 验证合并 / 探针不落盘 / 收尾从简)。</summary>
    public const string Text =
        "[上下文纪律 · 必守]\n" +
        "1. 验证合并: 把全部自测用例合并进**一次** run_command 执行 (用例多时先 write_file 一个用例脚本, 再一条命令跑完); " +
        "禁止为单条命令单独占用一步。\n" +
        "2. 探针不落盘: 临时检查用 python3 -c \"...\" 内联完成; 必须落盘时, 写入与删除在同一步内完成, 不留临时文件。\n" +
        "3. 收尾从简: 最后一条消息只给结论 + 证据 (命令与结果), 不复述代码、不写长篇说明。";

    /// <summary>缺省开; 仅 off/0/false 关 (词形同既有开关约定)。</summary>
    public static bool IsEnabled()
    {
        var v = Environment.GetEnvironmentVariable(EnvName);
        if (string.IsNullOrWhiteSpace(v)) return true;
        v = v.Trim();
        return !(v.Equals("off", StringComparison.OrdinalIgnoreCase)
                 || v.Equals("0", StringComparison.Ordinal)
                 || v.Equals("false", StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>尾部追加 (前缀逐字节不变); 空系统提示 ⇒ 退化为纪律块本身。</summary>
    public static string Apply(string systemPrompt)
        => string.IsNullOrEmpty(systemPrompt) ? Text : systemPrompt + "\n\n" + Text;
}
