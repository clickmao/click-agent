using System.Text.Json.Serialization;

namespace agent.session;


/// <summary>会话记忆持久化契约 (落盘由 SessionManager/宿主实现; 接口只管序列化往返)</summary>
public interface ISessionMemoryStore
{
    /// <summary>读回会话记忆 (不存在返回 null)</summary>
    SessionMemory? Load(string sessionId);

    /// <summary>落盘会话记忆 (JSON source-gen, AOT 安全)</summary>
    void Save(string sessionId, SessionMemory memory);
}
