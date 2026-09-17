using System.Text.Json.Serialization;

namespace agent;


/// <summary>/rag 查询载荷 (v0.13.0 用户钦定: RAG 数据文件路径可见化)</summary>
public sealed class RagInfoPayload
{
    public string CurrentPath { get; set; } = string.Empty;
    public string? Override { get; set; }
}
