namespace agent.rag;

/// <summary>
/// 精排阶段的一条候选 (粗排输出)。<see cref="Content"/> 供精排打分器读取。
/// 精排只重排**池内**候选, 不扩召回 —— 池外候选一律不引入。
/// </summary>
public readonly record struct RerankCandidate(string Id, string Content, double CoarseScore);
