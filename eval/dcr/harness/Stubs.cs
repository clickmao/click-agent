// 最小桩: 只满足 PlanNodeFormalGate.cs 的编译依赖 (PlanNode.Id / AgentTelemetry.Emit)。
// 不替代任何判定逻辑 —— Evaluate() 走的是仓库里的真实 PlanNodeFormalGate + 真实内核。
namespace agent.config
{
    public static class AgentTelemetry
    {
        public static void Emit(string point, string module, params (string Key, object? Value)[] kv) { }
    }
}

namespace agent.intent
{
    public class PlanNode
    {
        public string Id { get; set; } = "n0";
    }
}
