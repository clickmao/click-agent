namespace agent.exploration;


/// <summary>
/// v0.13.2 G1 (用户钦定) — 格式修复插件契约。
/// 收敛环: ①块内检测 → ②独立查找 → ③程序校验 → ④本地修复 → ⑤LLM 重修 (循环)。
/// 与 ImageRenderPlugin 同构的注册表模式; 本地修复器只用确定性规则 (LLM 只在环入口)。
/// </summary>
public interface IFormatRepairPlugin
{
    /// <summary>格式名 (json/csv/xml/generic — skill 分派键)</summary>
    string Format { get; }

    /// <summary>能否识别该格式的候选内容 (格式头/结构特征)</summary>
    bool CanDetect(string text);

    /// <summary>
    /// ②独立查找: 从全文提取最合法候选区段 (括号配平/引号扫描)。
    /// 找到返回 (start, length); 找不到返回 null。
    /// </summary>
    (int Start, int Length)? FindCandidate(string text);

    /// <summary>③程序校验: 返回错误列表 (空=合法)。必须用平台原生 parser 当权威。</summary>
    IReadOnlyList<string> Validate(string text);

    /// <summary>④本地修复 (确定性规则)。返回修复后文本 + 修改点数。</summary>
    (string Fixed, int ChangedN) Repair(string text);
}
