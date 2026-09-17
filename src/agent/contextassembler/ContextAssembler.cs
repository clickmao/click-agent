using Microsoft.Extensions.Logging;
using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;
using agent.tokencompression;

namespace agent.context;

/// <summary>
/// 上下文组装器实现
/// 
/// 参考了以下工业级框架的最佳实践：
/// - Microsoft Semantic Kernel: Context 变量和组装机制
/// - LangChain: Retrieval 和 Composable Memory
/// - Anthropic Claude Code: Context 压缩和优先级机制
/// </summary>
public partial class ContextAssembler : IContextAssembler
{
    /// <summary>
    /// R461: Memory (RAG) 源的 per-source token 预算 (R117 起 500)。
    /// 口径: 每轮注入的召回块是**新内容**, 直接吃 prompt 缓存命中率; 500 tok 与 97% 命中红线算术不相容。
    /// 诚实边界: 这是质量↔命中率的显式取舍点, 不是"免费优化"。
    /// </summary>
    public const int MemorySourceBudgetTokens = 120;

    private readonly ILogger<ContextAssembler> _logger;
    private readonly IRAGRecall _ragRecall;
    private readonly ISessionManager _sessionManager;
    private readonly ITendencyAnalyzer _tendencyAnalyzer;
    private readonly ISearchService _searchService;
    private readonly ITokenCompressor _tokenCompressor;
    
    // 缓存：snippetId -> ContextSnippet
    private readonly Dictionary<string, ContextSnippet> _snippetCache = new();
    private readonly Dictionary<string, List<string>> _sessionSnippetCache = new();
    
    // 统计
    private long _totalAssemblies;
    private long _totalSnippets;
    private long _totalTokensAssembled;
    private long _totalRecallTimeMs;
    private readonly System.Collections.Concurrent.ConcurrentDictionary<DataSourceType, long> _recallCountBySource = new();

    private sealed record CachedResult(ContextAssemblyResult Result, DateTime CachedAt);
    // R326 (P17): Dictionary 无锁并发写不安全 (DI 单例 + subagent/多会话并发装配) → ConcurrentDictionary
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, CachedResult> _resultCache = new();
    private static readonly TimeSpan CacheTtl = TimeSpan.FromMinutes(5);

    // P4 (R330): 工作区召回防慢预算 — 单文件整读阈值 (≤200KB 语义保留) + 整轮累计字节预算。
    // 预算与 Take(300) 同类扫描窗口 (文件按修改时间降序 → 超预算丢的是最旧文件), 防单轮最多 ~60MB 全量读入。
    // 非 readonly: 单测反射注入小预算验证截断路径 (产品代码只读, 无并发写路径)。
    private static long WorkspaceMaxFileBytes = 200 * 1024;
    private static long WorkspaceRecallBytesBudget = 4 * 1024 * 1024;

    private static string ComputeCacheKey(ContextAssemblyRequest request)
    {
        var sources = string.Join(",", request.EnabledSources.OrderBy(s => s.ToString()));
        return $"{request.UserMessage.GetHashCode():X}|{request.SessionId}|{sources}";
    }

    private long _cacheHits;
    private long _cacheMisses;
    
    private readonly object _lock = new();
    
    public ContextAssembler(
        ILogger<ContextAssembler> logger,
        IRAGRecall ragRecall,
        ISessionManager sessionManager,
        ITendencyAnalyzer tendencyAnalyzer,
        ISearchService searchService,
        ITokenCompressor tokenCompressor,
        agent.contextgradient.ITextEmbedder? embedder = null)
    {
        _logger = logger;
        _ragRecall = ragRecall;
        _sessionManager = sessionManager;
        _tendencyAnalyzer = tendencyAnalyzer;
        _searchService = searchService;
        _tokenCompressor = tokenCompressor;
        _gradientCompressor = new agent.contextgradient.ContextGradientCompressor(embedder);

        // 初始化统计计数器
        foreach (DataSourceType source in Enum.GetValues<DataSourceType>())
        {
            _recallCountBySource[source] = 0;
        }
    }
    
}
