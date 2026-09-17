using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// RAG召回系统接口
/// </summary>
public interface IRAGRecall
{
    /// <summary>v0.13.0 (用户钦定): 当前 RAG 数据文件路径 (/rag 查询)</summary>
    string CurrentPersistPath();

    /// <summary>v0.13.0 (用户钦定): 运行时切换 RAG 数据文件 (/rag &lt;path&gt;)</summary>
    void SetPersistOverride(string path);

    /// <summary>
    /// 索引文档
    /// </summary>
    Task IndexAsync(RAGDocument document);
    
    /// <summary>
    /// 批量索引
    /// </summary>
    Task IndexBatchAsync(IEnumerable<RAGDocument> documents);
    
    /// <summary>
    /// 召回
    /// </summary>
    Task<List<RecallResult>> RecallAsync(RecallRequest request);
    
    /// <summary>
    /// 获取文档
    /// </summary>
    Task<RAGDocument?> GetAsync(string id);
    
    /// <summary>
    /// 更新文档
    /// </summary>
    Task UpdateAsync(RAGDocument document);
    
    /// <summary>
    /// 删除文档
    /// </summary>
    Task DeleteAsync(string id);
    
    /// <summary>
    /// 获取统计信息
    /// </summary>
    Task<RAGStats> GetStatsAsync();
  
}
