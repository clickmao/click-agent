namespace agent.exploration;


internal static class ThinkNodeExtensions
{
    public static IReadOnlyList<(string RecordId, string Ref)> CitationsSafe(this ExploreNode node)
        => Array.Empty<(string, string)>(); // 引用由 ThinkStep.Citations 传入宿主后直接调 ThinkMemory — 节点不携带
}
