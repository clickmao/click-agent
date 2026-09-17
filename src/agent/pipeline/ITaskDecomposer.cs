namespace agent.pipeline;


/// <summary>
/// 任务分解器接口
/// </summary>
public interface ITaskDecomposer
{
    Task<DecompositionResult> DecomposeAsync(string task, DecomposeOptions? options = null);
    Task<ComplexityAssessment> AssessComplexityAsync(string task);
    Task<DependencyGraph> AnalyzeDependenciesAsync(IEnumerable<string> tasks);
}
