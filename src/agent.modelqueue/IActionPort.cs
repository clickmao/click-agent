using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>
/// 执行面端口 (R456 端口化纪律): 唯一允许产生文件/进程副作用的边界。
/// 替换实现 (沙箱/远程/回放) 不得改变链上其余部分。
/// </summary>
public interface IActionPort
{
    string Name { get; }
    /// <summary>R462: 会话工作区根 (供回灌面做「召回-现实一致性」机检); 无工作区概念的实现返回 null。</summary>
    string? WorkspaceRoot => null;
    Task<ActionExecutionResult> ExecuteAsync(ActionToolCall call, CancellationToken ct);
}
