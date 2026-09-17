using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 本地执行器登记条目 (v0.22.0 exp9 D2)。
/// 判定"这步能不能本地跑"只认这张表 —— 表外/未接线的执行器一律不许判 Local。
/// </summary>
/// <param name="Id">登记 Id (节点 LocalExecutorId 取值)</param>
/// <param name="DisplayName">给人看的名字 (前端显示)</param>
/// <param name="Intents">可承接的意图</param>
/// <param name="Hint">判定依据短句 (写进 PlanNode.LocalHint, 前端可见)</param>
/// <param name="Wired">是否已接线真实实现。false = 已声明未接线 → **永不路由** (负向控制, 拒"为编排而编排")</param>
/// <param name="PostActionMarkers">文本中命中即表示"远程生成后本地可立刻做这一段"的词 (Hybrid 判定用)</param>
public sealed record LocalExecutorDescriptor(
    string Id,
    string DisplayName,
    IReadOnlyList<string> Intents,
    string Hint,
    bool Wired,
    IReadOnlyList<string> PostActionMarkers);
