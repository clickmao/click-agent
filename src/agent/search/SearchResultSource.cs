namespace agent.search;


/// <summary>
/// 搜索来源
/// </summary>
public enum SearchResultSource
{
    /// <summary>搜索插件 (博查/SearXNG/DDG/BingCN/百度等)</summary>
    Provider,
    
    /// <summary>缓存</summary>
    Cache,
    
    /// <summary>记忆</summary>
    Memory,
    
    /// <summary>WebReaper CLI 抓取</summary>
    WebReaper
}
