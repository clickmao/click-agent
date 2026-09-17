using System;
using System.IO;

namespace agent.execution;


/// <summary>冲突合并策略 (LockedFileWriter.Write)。</summary>
public enum ConflictStrategy
{
    /// <summary>直接覆盖 (最后写者胜) — 适合幂等全量快照。</summary>
    Overwrite,
    /// <summary>目标已存在且内容不同 → 不覆盖 (先写者胜), 返回 merged=true 表示让位。防双写互踩。</summary>
    KeepExisting,
}
