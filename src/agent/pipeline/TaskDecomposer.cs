namespace agent.pipeline;


/// <summary>
/// 任务分解器实现
/// </summary>
public class TaskDecomposer : ITaskDecomposer
{
    public Task<DecompositionResult> DecomposeAsync(string task, DecomposeOptions? options = null)
    {
        options ??= new DecomposeOptions();
        
        var result = new DecompositionResult();
        
        // 简单的任务分解逻辑
        var subTasks = task.Split(new[] { '\n', ';', ',' }, StringSplitOptions.RemoveEmptyEntries);
        var tokenBudget = options.MaxTokensPerTask;
        
        foreach (var subTask in subTasks.Take(options.MaxSubTasks))
        {
            var subTaskObj = new agent.core.SubAgentTask
            {
                Name = subTask.Trim(),
                Input = subTask.Trim(),
                Type = core.TaskType.General,
                TokenBudget = tokenBudget,
                TimeoutMs = 300000
            };
            result.Tasks.Add(subTaskObj);
        }
        
        result.EstimatedTotalTokens = result.Tasks.Count * tokenBudget;
        result.EstimatedDuration = TimeSpan.FromMinutes(result.Tasks.Count * 2);
        
        return Task.FromResult(result);
    }
    
    public Task<ComplexityAssessment> AssessComplexityAsync(string task)
    {
        var assessment = new ComplexityAssessment
        {
            Type = core.TaskType.General,
            ComplexityLevel = task.Length > 500 ? 4 : (task.Length > 200 ? 3 : 2),
            EstimatedTokens = task.Length * 2,
            EstimatedTime = TimeSpan.FromMinutes(task.Length > 500 ? 10 : 5)
        };
        
        return Task.FromResult(assessment);
    }
    
    public Task<DependencyGraph> AnalyzeDependenciesAsync(IEnumerable<string> tasks)
    {
        var graph = new DependencyGraph
        {
            TopologicalOrder = tasks.ToList()
        };
        
        return Task.FromResult(graph);
    }
}
