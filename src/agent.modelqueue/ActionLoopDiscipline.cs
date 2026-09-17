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
/// R528 追加第 6 条 (依据 = R525 w3 逐调用取证 `eval/rover/r525/run-0917-r525-w3/A1-on/g1/audit/action_loop.jsonl`):
///   该臂 8 次调用 / 3 步把 `games/` 包写到 `<工作根>/sols/games_pkg/games/`, 随后 `cd sols/games_pkg && python3 -m games life` 自验通过 ⇒ 自认完成;
///   而题面验收形态是**工作根**下 `python3 -m games <id>` ⇒ 前置器 0/58 全败 (代码本身 58/58, 见 `eval/rover/r528/layout-census.json`)。
///   ⇒ 失败源不是代码质量, 是**产物落位 + 自验位置** ⇒ 第 6 条把「工作根 + 题面相对路径 + 工作根自验」写成硬纪律。
/// </summary>
public static class ActionLoopDiscipline
{
    /// <summary>消融开关 (缺省开; off/0/false = 关 ⇒ 等价 R521 旧行为)。</summary>
    public const string EnvName = "AGENTFRAMEWORK_ACTION_DISCIPLINE";

    /// <summary>
    /// R531 合批轴 (缺省**关**; 只有 on/1/true/yes 才开)。依据 = R521/R525 逐调用取证里
    /// 「一条命令一轮 LLM」的往返项 (R525 w3 A1-on: 8 次调用里 3 步写完整个包, 单步承载多动作时
    /// 步数与调用数同步下降); 缺省关是保形要求: 未开时注入文本与 R528 逐字节相同 ⇒ 可作单变量臂。
    /// </summary>
    public const string MergeEnvName = "AGENTFRAMEWORK_ACTION_MERGE";

    /// <summary>六条纪律文本 (锚: 验证合并 / 探针不落盘 / 收尾从简 / 零过渡叙述 / 回执按需取全文 / 产物落位与自验)。</summary>
    public const string Text =
        "[上下文纪律 · 必守]\n" +
        "1. 验证合并: 把全部自测用例合并进**一次** run_command 执行 (用例多时先 write_file 一个用例脚本, 再一条命令跑完); " +
        "禁止为单条命令单独占用一步。\n" +
        "2. 探针不落盘: 临时检查用 python3 -c \"...\" 内联完成; 必须落盘时, 写入与删除在同一步内完成, 不留临时文件。\n" +
        "3. 收尾从简: 最后一条消息只给结论 + 证据 (命令与结果), 不复述代码、不写长篇说明。\n" +
        "4. 零过渡叙述: 除最后一条结论消息外, 每步 assistant 正文一律留空, 直接发工具调用; 禁止\"接下来我将…/现在让我…\"类过渡语。\n" +
        "5. 回执按需取全文: 工具回执默认被截断为摘要 (退出码 + 头部若干行); 若确需完整输出, 用工具显式再取一次, " +
        "禁止为了预防而整篇回读。\n" +
        "6. 产物落位与自验: 产出物一律落在**工作根**下、按题面给出的**相对路径**命名 (题面写 `x/`, 就写 `<工作根>/x/`, " +
        "不得另加 `sols/` 之类中间层); 收尾前的自验**必须在工作根**执行题面给出的验收命令 (禁 `cd` 到子目录后再验, " +
        "否则验的不是验收形态); 自验退出码非 0 不得收尾。";

    /// <summary>
    /// R531 第 7 条 (合批 / 一次成型) —— 只在 <see cref="MergeEnvName"/> 开时追加。
    /// 追加式设计: 第 1–6 条逐字节不变 ⇒ 与「合批关」臂的差异是本条全文, 单变量可归因。
    /// 依据: 动作环宿主逐调用 `foreach (var tc in calls)` ⇒ 单步承载多动作在器具上可行 (不是话术)。
    /// </summary>
    public const string MergeText =
        "\n7. 一次成型 (合批): 互不依赖的动作必须在**同一步**内一次发出 —— 多个 write_file、多条互不依赖的命令, " +
        "一律并进同一轮工具调用; 禁止「写一个文件一轮、跑一条命令一轮」的串行推进; " +
        "同一信息在一轮内不得分次索取 (同一步内一次取全)。\n";

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

    /// <summary>缺省**关**; 仅 on/1/true/yes 开 (保形轴: 未开 ⇒ 逐字节等于 R528 文本)。</summary>
    public static bool IsMergeEnabled()
    {
        var v = Environment.GetEnvironmentVariable(MergeEnvName);
        if (string.IsNullOrWhiteSpace(v)) return false;
        v = v.Trim();
        return v.Equals("on", StringComparison.OrdinalIgnoreCase)
               || v.Equals("1", StringComparison.Ordinal)
               || v.Equals("true", StringComparison.OrdinalIgnoreCase)
               || v.Equals("yes", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>当前生效文本 (合批轴开 ⇒ 6 条 + 第 7 条)。</summary>
    public static string CurrentText() => IsMergeEnabled() ? Text + MergeText : Text;

    /// <summary>尾部追加 (前缀逐字节不变); 空系统提示 ⇒ 退化为纪律块本身。</summary>
    public static string Apply(string systemPrompt)
    {
        var t = CurrentText();
        return string.IsNullOrEmpty(systemPrompt) ? t : systemPrompt + "\n\n" + t;
    }
}
