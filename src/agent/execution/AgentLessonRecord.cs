using System;
using System.IO;
using System.Threading;

namespace agent.execution;


/// <summary>教训记录轻桥 (避免 CollisionDetector 直接依赖具体 lesson 存储 — 用默认单例)。</summary>
internal static class AgentLessonRecord
{
    public static void Record(string pattern, string summary, string solution)
        => agent.execution.ExecutorLessonMemory.Default.Record(pattern, summary, solution, "CollisionDetector 时序撞车");
}
