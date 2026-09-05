using System.Text.Json;
using agent.intent;
using agent.userinteraction;

namespace agent.registry;

/// <summary>
/// 偏好存储 (v7.13): 落盘 + 读回 + 复用排序。
/// 存储文件: 工作目录 clarification_preferences.json (JSON source-gen)。
/// 写入路径: RecordAnswer — 在 ClarificationBatch 收到合法答案后调用;
/// 读取路径: ApplyTo — 在组问询前调用, 把偏好映射为 SuggestedValues 排序 (复用而非强填)。
/// 凭据隔离: Sensitive/ApiKey 的答案在本层就被拒收 (双保险, 上层 ClarificationBatch 也不调这里)。
/// </summary>
public sealed class ClarificationPreferenceStore
{
    private readonly string _filePath;
    private readonly object _lock = new();
    private Dictionary<string, ClarificationPreference> _byFingerprint = new();

    /// <param name="dataStoragePath">框架数据目录 (与 AgentRegistry/ForecastRecord 同一落盘根)</param>
    public ClarificationPreferenceStore(string dataStoragePath = "data")
    {
        _filePath = Path.Combine(dataStoragePath, "clarification_preferences.json");
        Load();
    }

    /// <summary>工作目录 (复用框架既有落盘位置约定)</summary>
    public string FilePath => _filePath;

    /// <summary>
    /// 记录一次问询结果 → 更新偏好 (凭据/敏感答案被拒绝, 返回 false)。
    /// 只记模式特征: choice 记选项序, 其他记 ExtractPattern 的规范化特征。
    /// </summary>
    public bool RecordAnswer(ClarificationItem item, string normalizedAnswer)
    {
        // 铁律①: 凭据绝不入偏好
        if (item.Kind == ClarificationKinds.ApiKey)
            return false;

        var pattern = ClarificationFingerprint.ExtractPattern(item.DataType, normalizedAnswer);
        if (pattern == null)
            return false; // 无稳定模式 (自由文本/一次性值) 不入库

        var fingerprint = ClarificationFingerprint.Build(item.Question, item.ParameterName, item.DataType);

        lock (_lock)
        {
            if (!_byFingerprint.TryGetValue(fingerprint, out var pref))
                _byFingerprint[fingerprint] = pref = new ClarificationPreference
                {
                    Fingerprint = fingerprint,
                    DataType = item.DataType,
                };

            pref.PreferredPattern = pattern;
            pref.UpdatedAt = DateTime.UtcNow.Ticks;

            // Choice: 选项偏好序 (选中的移到最前 — 只动顺序, 选项列表本身来自 item.Choices)
            if (item.DataType is PromptDataType.Choice or PromptDataType.MultiChoice && item.Choices.Count > 0)
            {
                var picked = normalizedAnswer.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
                foreach (var p in picked.Reverse<string>())
                {
                    pref.ChoiceOrder.Remove(p);
                    pref.ChoiceOrder.Insert(0, p);
                }
                // 新选项追加在尾部 (保持完整选项面)
                foreach (var c in item.Choices)
                    if (!pref.ChoiceOrder.Contains(c))
                        pref.ChoiceOrder.Add(c);
            }

            pref.HitCount++;
            Save();
        }
        return true;
    }

    /// <summary>
    /// 把已有偏好套到问询条目上 (复用): 调整 SuggestedValues 排序 —
    /// Choice → 偏好序重排选项; 其他 → 偏好特征作首建议 (仅供展示/代答, 不强改用户输入)。
    /// 返回 true = 有偏好被应用。
    /// </summary>
    public bool ApplyTo(ClarificationItem item)
    {
        if (item.Kind == ClarificationKinds.ApiKey)
            return false; // 凭据永远不复用偏好

        ClarificationPreference? pref;
        lock (_lock)
        {
            var fingerprint = ClarificationFingerprint.Build(item.Question, item.ParameterName, item.DataType);
            if (!_byFingerprint.TryGetValue(fingerprint, out pref) || pref.HitCount == 0)
                return false;
        }

        if (item.DataType is PromptDataType.Choice or PromptDataType.MultiChoice && pref.ChoiceOrder.Count > 0)
        {
            // 选项偏好序: 库里记过的顺序优先, 未记过的保持原序
            var ordered = pref.ChoiceOrder
                .Where(item.Choices.Contains)
                .Concat(item.Choices.Where(c => !pref.ChoiceOrder.Contains(c)))
                .ToList();
            item.Choices.Clear();
            item.Choices.AddRange(ordered);
            item.SuggestedValues.Clear();
            item.SuggestedValues.Add(ordered[0]);
            return true;
        }

        // 非选择类: 偏好特征注入为首选建议 (如 path→absolute 提示绝对路径)
        if (pref.PreferredPattern.Length > 0)
        {
            item.SuggestedValues.Insert(0, $"偏好: {Describe(item.DataType, pref.PreferredPattern)}");
            return true;
        }
        return false;
    }

    /// <summary>偏好概览 (CLI /status 展示)</summary>
    public IReadOnlyList<ClarificationPreference> Snapshot()
    {
        lock (_lock)
            return _byFingerprint.Values.OrderBy(p => p.Fingerprint).ToList();
    }

    private static string Describe(PromptDataType type, string pattern) => type switch
    {
        PromptDataType.Path => pattern == "absolute" ? "绝对路径" : "相对路径",
        PromptDataType.Boolean => pattern == "prefer-yes" ? "倾向确认" : "倾向取消",
        PromptDataType.Number or PromptDataType.Integer => pattern switch
        {
            "magnitude:large" => "较大的数值 (≥1000)",
            "magnitude:medium" => "中等数值 (10-999)",
            _ => "较小的数值 (<10)",
        },
        _ => pattern,
    };

    private void Load()
    {
        try
        {
            if (!File.Exists(_filePath))
                return;
            var list = JsonSerializer.Deserialize(File.ReadAllText(_filePath),
                ClarificationPreferenceJsonContext.Default.ListClarificationPreference);
            lock (_lock)
                _byFingerprint = list?.ToDictionary(p => p.Fingerprint) ?? new();
        }
        catch
        {
            // 损坏文件不阻塞启动 — 空库重建 (下次 RecordAnswer 覆写)
            lock (_lock)
                _byFingerprint = new();
        }
    }

    private void Save()
    {
        try
        {
            var dir = Path.GetDirectoryName(_filePath);
            if (!string.IsNullOrEmpty(dir))
                Directory.CreateDirectory(dir);
            List<ClarificationPreference> snapshot;
            lock (_lock)
                snapshot = _byFingerprint.Values.OrderBy(p => p.Fingerprint).ToList();
            File.WriteAllText(_filePath, JsonSerializer.Serialize(snapshot,
                ClarificationPreferenceJsonContext.Default.ListClarificationPreference));
        }
        catch (IOException)
        {
            // 磁盘问题不阻塞问询主流程
        }
    }
}
