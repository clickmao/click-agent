using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>任务目标画像: 当前任务的总方向指示 (③)</summary>
public sealed class GoalProfile
{
    /// <summary>目标一句话 (用户最新钦定的总方向)</summary>
    public string GoalText { get; set; } = string.Empty;

    /// <summary>v0.11.0 R14: 锚定时的意图名 (相关性判定的 goalIntent 参数; 空串=未知不参与判定)</summary>
    public string GoalIntent { get; set; } = string.Empty;

    /// <summary>关键实体 (项目名/模块名/组件名, 12 上限)</summary>
    public List<string> KeyEntities { get; set; } = new();

    /// <summary>约束 (AOT/0警告/不过度设计等, 8 上限)</summary>
    public List<string> Constraints { get; set; } = new();

    /// <summary>已完成里程碑 (16 上限, 新的在尾)</summary>
    public List<string> Milestones { get; set; } = new();

    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
