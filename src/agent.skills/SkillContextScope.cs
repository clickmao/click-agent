namespace agent.skills;

/// <summary>Skill 沙箱内写入 (暂存, 提交时校验)</summary>
public sealed class SkillWrite
{
    public string Field { get; init; } = string.Empty;
    public string Value { get; init; } = string.Empty;
}

/// <summary>
/// 上下文隔离沙箱 (P2, plan_skill_dispatch.md S.2 SkillContextScope; 原文 §5.3/§9.2):
/// - 白名单读: Skill 只能读 definition.Permissions 允许的全局字段, 越权返回 null (记录)
/// - 写回卷: Skill 对共享字段的写入先暂存, Commit 时逐条校验 (字段必须也在白名单内, 值非空), 校验不过的条目丢弃
/// - 中间数据不入历史: Write 中间暂存只存在本作用域, 会话历史永不见 (架构保证: 历史写入 API 不经过本类)
/// </summary>
public sealed class SkillContextScope
{
    private readonly IReadOnlyDictionary<string, string> _globalFields;
    private readonly IReadOnlyList<string> _allowedFields;
    private readonly List<SkillWrite> _pendingWrites = new();

    /// <summary>越权读取记录 (审计/测试断言)</summary>
    public List<string> DeniedReads { get; } = new();

    /// <summary>提交被拒的写入 (审计/测试断言)</summary>
    public List<SkillWrite> RejectedWrites { get; } = new();

    public SkillContextScope(SkillDefinition skill, IReadOnlyDictionary<string, string> globalFields)
    {
        _globalFields = globalFields;
        _allowedFields = skill.Permissions;
    }

    /// <summary>白名单读: 越权 → null + 记录</summary>
    public string? Read(string field)
    {
        if (!_allowedFields.Contains(field, StringComparer.OrdinalIgnoreCase))
        {
            DeniedReads.Add(field);
            return null;
        }
        return _globalFields.TryGetValue(field, out var v) ? v : null;
    }

    /// <summary>写暂存 (不直接改共享状态 — 回卷校验前只在本作用域)</summary>
    public void Write(string field, string value) =>
        _pendingWrites.Add(new SkillWrite { Field = field, Value = value });

    /// <summary>写回卷校验: 字段在白名单且值非空 → 生效; 否则拒绝。返回通过条目。</summary>
    public IReadOnlyList<SkillWrite> Commit(Action<string, string> apply)
    {
        var applied = new List<SkillWrite>();
        foreach (var w in _pendingWrites)
        {
            if (_allowedFields.Contains(w.Field, StringComparer.OrdinalIgnoreCase) &&
                !string.IsNullOrWhiteSpace(w.Value))
            {
                apply(w.Field, w.Value);
                applied.Add(w);
            }
            else
            {
                RejectedWrites.Add(w);
            }
        }
        _pendingWrites.Clear();
        return applied;
    }
}
