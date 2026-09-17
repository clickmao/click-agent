using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.config;
using agent.registry;
using agent.skills;

namespace agent.intent;


/// <summary>
/// 本地节点执行器 (v0.22.0 exp9 D3)。实现方契约:
///   ① 零 LLM 调用、零网络; ② 跨平台零 shell (ProcessStartInfo.ArgumentList / 纯内存计算);
///   ③ 失败必须给真实原因 (禁静默返回成功 —— "哑体"退化的反面判据)。
/// </summary>
public interface ILocalNodeExecutor
{
    /// <summary>登记 Id (与 LocalExecutorRegistry 一致)</summary>
    string Id { get; }

    Task<NodeExecutionResult> RunAsync(PlanNode node, LocalNodeContext ctx, CancellationToken ct);
}
