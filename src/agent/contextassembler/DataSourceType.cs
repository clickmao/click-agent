using agent.core;
using agent.session;
using agent.rag;
using agent.tendency;
using agent.search;

namespace agent.context;

/// <summary>
/// 数据源类型枚举
/// </summary>
public enum DataSourceType
{
    /// <summary>持久化记忆 (RAG/Memory) </summary>
    Memory,
    
    /// <summary>当前会话历史</summary>
    Session,
    
    /// <summary>网络搜索结果</summary>
    WebSearch,
    
    /// <summary>用户倾向/偏好</summary>
    UserTendency,
    
    /// <summary>工作区文件</summary>
    WorkspaceFiles,
    
    /// <summary>外部工具输出</summary>
    ToolOutput,

    /// <summary>会话长期记忆 + 任务目标画像 (v7.14)</summary>
    SessionMemory,

    /// <summary>Agent 画像 + 能力清单 (v7.14)</summary>
    AgentContext,

    /// <summary>修法记忆 (v0.14.0 T2d — 输出侧经验: 反模式→修法, 评审反馈/自审锚定沉淀)</summary>
    FixMemory,

    /// <summary>警告/铁律记忆 (v0.15.2 — 用户主动警告的逻辑三元组, 领域性联想抑制)</summary>
    GuardrailMemory
}
