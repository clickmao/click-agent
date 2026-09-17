using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace agent.execution;


/// <summary>
/// v0.17.0 T3 (R334, 用户钦定): 执行层失败教训临时记忆 — 失败(IO 冲突/锁超时/占用) → 获取原因 →
/// 记入临时记忆, **随教训频率提高记忆越长** (count 升级内容: 1 行摘要 → 补解决方案 → 补触发上下文),
/// 下次同类操作前注入避免重复失败。TTL 衰减: 24h 无命中降级, 7d 无命中移除。
/// 持久化: data/executor-lessons.json (经 AtomicFileWriter 原子写)。AOT 兼容 (STJ source-gen 手动 JSON 亦可 — 用 JsonDocument 手写往返防反射)。
/// </summary>
public sealed class ExecutorLesson
{
    public string Pattern { get; set; } = "";       // 教训键: "file-lock:data/guardrails.json"
    public string Summary { get; set; } = "";       // 失败原因摘要 (首次记入)
    public int Count { get; set; }
    public long FirstSeenUnixMs { get; set; }
    public long LastSeenUnixMs { get; set; }
    public string? Solution { get; set; }            // 解决方案 (count≥3 记入)
    public string? ContextTail { get; set; }         // 触发上下文 (count≥8 记入)
}
