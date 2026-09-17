using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.config;
using agent.templates;

namespace agent.registry;


/// <summary>产物校验结论来源 (插件实现, 路由器聚合, 主链消费)。</summary>
public interface IArtifactCheckSource
{
    /// <summary>取走自上次调用以来新增的结论 (含通过项: 复检需要"通过"证据, 不只是失败)。</summary>
    IReadOnlyList<ArtifactCheck> DrainNewChecks();
}
