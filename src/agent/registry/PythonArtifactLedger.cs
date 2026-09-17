using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.skills;

namespace agent.registry;


/// <summary>
/// Python 产物台账 (R368): 线程安全, 记录本进程内所有落盘+校验结果。
/// 宿主/CLI/前端快照可读 — 让"机器校验"成为可观测事实, 而不是隐式行为。
/// </summary>
public sealed class PythonArtifactLedger
{
    private readonly List<PythonArtifactReport> _items = new();
    private long _version;

    /// <summary>单调递增版本号 (变化 = 有新报告; 前端轮询增量用)。</summary>
    public long Version => Interlocked.Read(ref _version);
    public void Add(PythonArtifactReport r) { lock (_items) _items.Add(r); Interlocked.Increment(ref _version); }
    public IReadOnlyList<PythonArtifactReport> Snapshot() { lock (_items) return _items.ToArray(); }
}
