namespace agent.exploration;


/// <summary>探索执行器抽象 (URL/文件/目录 — 宿主侧实现 IO; 本库禁直接 IO 依赖)。</summary>
public interface IExploreExecutor
{
    Task<ExploreStepResult> ExecuteAsync(ExploreNode node, CancellationToken ct = default);
}
