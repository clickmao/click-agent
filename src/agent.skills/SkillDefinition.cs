namespace agent.skills;

/// <summary>Skill 类型: normative=口径型 (模板+禁语) / executive=执行型 (entry 委托)</summary>
public enum SkillType
{
    Normative,
    Executive,
}

/// <summary>
/// Skill 元数据 (原文 §3.2/§7.1) — 技能定义文件 (skills/*.yaml) 解析产物。
/// 触发: 关键词 (一级) + 正则 (二级) + 领域词 (疑似命中)。
/// </summary>
public sealed class SkillDefinition
{
    public string SkillId { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Version { get; set; } = "1.0";
    public string Domain { get; set; } = string.Empty;
    public SkillType Type { get; set; } = SkillType.Normative;

    /// <summary>优先级 (冲突裁决: 排他 > 优先级 > 上下文度 > 精确度)</summary>
    public int Priority { get; set; } = 5;

    /// <summary>排他 (true = 命中后独占, 不与其他 Skill 并行)</summary>
    public bool Exclusive { get; set; }

    /// <summary>一级匹配关键词 (任一命中 = 进二级)</summary>
    public List<string> Keywords { get; set; } = new();

    /// <summary>二级精匹配正则 (命中 = 确认激活)</summary>
    public List<string> RegexPatterns { get; set; } = new();

    /// <summary>疑似命中领域词 (仅一级命中 → 疑似; enable_suspected_trigger 开启时激活)</summary>
    public List<string> DomainWords { get; set; } = new();

    /// <summary>口径模板 (normative: force_use 时原样承载; {input} 占位)</summary>
    public string? ForceTemplate { get; set; }

    /// <summary>禁语 (结果含任一 → 校验拦截)</summary>
    public List<string> ForbiddenWords { get; set; } = new();

    /// <summary>执行超时 (秒, 默认 30)</summary>
    public int TimeoutSeconds { get; set; } = 30;

    /// <summary>权限白名单 (P2 沙箱: 允许读写的共享字段; 空 = 无权限)</summary>
    public List<string> Permissions { get; set; } = new();

    /// <summary>幂等 (P2 执行调度: true 才允许重试)</summary>
    public bool Idempotent { get; set; }

    /// <summary>v0.10.0 开放规范包: 包目录绝对路径 (null = legacy 平文件 skill.yaml)</summary>
    public string? PackageDir { get; set; }

    /// <summary>开放规范包: scripts/ 目录存在 (可执行脚本)</summary>
    public bool HasScripts { get; set; }

    /// <summary>开放规范包: references/ 目录存在 (大段参考文档)</summary>
    public bool HasReferences { get; set; }

    /// <summary>开放规范包: assets/ 目录存在 (模板/静态资源)</summary>
    public bool HasAssets { get; set; }
}

/// <summary>标准化输出 (原文 §4.6)</summary>
public sealed class SkillResult
{
    public string SkillId { get; set; } = string.Empty;
    public bool Success { get; set; }
    public string Content { get; set; } = string.Empty;

    /// <summary>强制口径 (true = 内容直接承载回复口径, 模型只做合规润色)</summary>
    public bool ForceUse { get; set; }

    /// <summary>禁语命中 (校验拦截时 false)</summary>
    public string? ForbiddenHit { get; set; }

    /// <summary>执行耗时 ms</summary>
    public long ElapsedMs { get; set; }
}
