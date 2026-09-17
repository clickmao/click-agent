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


/// <summary>回流修复结果 (诚实字段: Attempted/Fixed 分开, 未修好时不伪装)。</summary>
public sealed record ArtifactRepairResult(
    string Content,
    bool Attempted,
    bool Fixed,
    int Attempts,
    string ErrorKind,
    string Detail);
