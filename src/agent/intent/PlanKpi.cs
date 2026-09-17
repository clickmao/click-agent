using System.Text.Json.Serialization;

namespace agent.intent;


/// <summary>
/// 计划级 KPI (v0.22.0 exp9 D6)。单位: ms / 个 / token。
/// 语义:
/// - LocalFirstNodes/LocalFirstMs: **无依赖本地节点**的个数与其自身墙钟耗时 (远程产物未就绪前就跑完的部分);
/// - OverlapMs: 本地先行与"远程等待期"的**真重叠**时长 (0 = 假并行, 只是先后排列);
/// - RemoteWaitMs: 远程等待期总长 (计划构建 → 产物就绪);
/// - LocalTokens: 本地节点消耗的模型 token (恒 0 —— 这是"省 token"的原始证据, 不是估计值)。
/// </summary>
public sealed record PlanKpi(
    int Nodes,
    int LocalNodes,
    int RemoteNodes,
    int HybridNodes,
    int LocalFirstNodes,
    int LocalFirstMs,
    int OverlapMs,
    int RemoteWaitMs,
    long LocalFirstUs,
    long OverlapUs,
    long RemoteWaitUs,
    long LocalTokens,
    int WaitNodes,
    long WaitUs,
    int ElapsedMs);
