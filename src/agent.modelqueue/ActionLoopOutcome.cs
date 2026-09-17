using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>动作环终态 (KPI 归因: 步数/工具数/是否收敛)。</summary>
public sealed class ActionLoopOutcome
{
    public int Steps { get; set; }
    public int ToolCalls { get; set; }
    public int Executed { get; set; }
    public bool Converged { get; set; }
    public bool MaxStepsHit { get; set; }

    /// <summary>R508: 步数预算被自动续期的次数 (0 = 未续期)。</summary>
    public int BudgetExtensions { get; set; }
    public string LastError { get; set; } = string.Empty;
    public List<ActionCallRecord> Records { get; } = new();
}
